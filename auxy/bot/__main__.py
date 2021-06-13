import logging
import enum
import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta, WE
from sqlalchemy.future import select
from aiogram import executor, types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters import Text, HashTag
from aiogram.dispatcher import FSMContext
from auxy.settings import WHITELISTED_USERS, WHITELISTED_CHATS
from auxy.db import OrmSession
from auxy.db.models import User, Chat, Project
from .middleware import WhitelistMiddleware, GetOrCreateChatMiddleware, GetOrCreateUserMiddleware
from auxy.utils import get_bulleted_items_list_from_message, generate_grid, PeriodBucket
from .blueprints.projects import updateprojectsettings, newproject
from .background_tasks import notification_processing_loop
from .blueprints.item_logging import item_logging
from . import dp


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class TodoListFor(enum.Enum):
    today = 1
    tomorrow = 2


@dp.message_handler(commands='start')
async def start(message: types.Message, user: User, is_new_user: bool):
    """
    Регистрация пользователя, приветствие, краткое руководство для начала работы
    """
    if is_new_user:
        await message.answer(
            f'Привет {user.first_name}, будем знакомы! Меня назвали Окси, или Auxy по-английски.'
            'Это идет от слова auxilary - вспомогательный.\n'
            'Мое призвание - помогать поддерживать ваши дела в порядке.\n'
            'Сейчас я учусь напоминать об окончании рабочего дня и необходимости составить план на следующий день. '
            'В будущем, планируется много другого функционала, но об этом будет рассказано позже.\n'
            'Чтобы узнать более подробно, что я умею, наберите, пожалуйста, команду /help.'
        )
    else:
        await message.answer(
            f'Привет {user.first_name}, очень приятно вас снова слышать!\n'
            'Чтобы узнать более подробно, что я умею, наберите, пожалуйста, команду /help.'
        )


@dp.message_handler(commands='help')
async def help_(message: types.Message):
    """
    Подробное пользовательское руководство по использованию функций бота
    """
    await message.answer(
        'Меня назвали Окси, или Auxy по-английски. Это идет от слова auxilary - вспомогательный.\n'
        'Мое призвание - помогать поддерживать ваши дела в порядке.\n'
        'Сейчас я учусь напоминать об окончании рабочего дня и необходимости составить план на следующий день. '
        'В будущем, планируется много другого функционала, но об этом будет рассказано позже.'
    )


@dp.message_handler(commands='todo')
async def todo_for_today(message: types.Message, user: User, chat: Chat):
    dt = message.date
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
            Project.owner_user_id == user.id,
            Project.chat_id == chat.id
        ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()

        bucket = PeriodBucket.new(project.period_bucket_mode, dt)
        todo_list = await project.get_for_period(session, bucket, with_log_messages=True)
        if todo_list:
            message_content = [
                text('Вот, что вы на сегодня планировали:'),
                text('')
            ]
            for item in sorted(todo_list.items, key=lambda i: i.id):
                message_content.append(text(':pushpin:', item.text))
                for log_message in item.notes:
                    message_content.append(text('    :paperclip:', log_message.text))
            message_content += [
                text(''),
                text('Все точно получится!')
            ]
        else:
            message_content = [
                text('Никаких планов нет.'),
                # TODO предложение создать план и описание способа
            ]
        await message.answer(emojize(text(*message_content, sep='\n')))


@dp.message_handler(commands='planned')
async def todo_for_next_time(message: types.Message, user: User, chat: Chat):
    # TODO почти copy-paste, разобраться
    dt = message.date
    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
            Project.owner_user_id == user.id,
            Project.chat_id == chat.id
        ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()

        bucket = PeriodBucket.new(project.period_bucket_mode, dt)
        todo_list = await project.get_for_period(session, bucket.get_next())
        if todo_list:
            message_content = [
                text('Вот, что запланировано вами на следующий рабочий день:'),
                text('')
            ] + [
                text(':pushpin: ' + item.text) for item in sorted(todo_list.items, key=lambda i: i.id)
            ] + [
                text(''),
                text('Но не отвлекайтесь, пожалуйста.')
            ]
        else:
            message_content = [
                text('Никаких планов нет.'),
                # TODO предложение создать план и описание способа
            ]
        await message.answer(emojize(text(*message_content, sep='\n')))


@dp.message_handler(commands='cancel', state='*')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_command(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('В данный момент мне нечего отменять')
    else:
        await state.finish()
        await message.reply('Ладно, не в этот раз')


@dp.message_handler(commands=['wsr', 'msr'])
async def status_report(message: types.Message, user: User, chat: Chat):
    if message.get_command() == '/wsr':
        start_dt = message.date + relativedelta(weekday=WE(-1), hour=0, minute=0, second=0, microsecond=0)
        end_dt = message.date + relativedelta(weekday=WE, hour=0, minute=0, second=0, microsecond=0) \
                 - relativedelta(days=1)
    else:
        start_dt = message.date + relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_dt = message.date + relativedelta(months=1, day=1, hour=0, minute=0, second=0, microsecond=0, days=-1)
    grid = generate_grid(start_dt, end_dt)
    grid = [[[i[0], i[1]] for i in week] for week in grid]

    async with OrmSession() as session:
        select_stmt = select(Project) \
            .where(
            Project.owner_user_id == user.id,
            Project.chat_id == chat.id
        ) \
            .order_by(Project.id)
        projects_result = await session.execute(select_stmt)
        project = projects_result.scalars().first()
        from_period = PeriodBucket.new(project.period_bucket_mode, start_dt)

        todo_lists = await project.get_since(session, from_period, with_log_messages=True)
        message_content = []
        for todo_list in todo_lists:
            bucket = PeriodBucket.get_by_key(todo_list.period_bucket_key)
            for todo_item in todo_list.items:
                message_content.append(text(
                    ':spiral_calendar_pad:', str(bucket),
                    ':pushpin:', todo_item.text
                ))
                for log_message in todo_item.notes:
                    message_content.append(text(':paperclip:', log_message.text))
                message_content.append(text(''))

            if bucket.start():
                for week in grid:
                    for i in week:
                        if i[1].date() == bucket.start().date():
                            i[0] = i[0].replace('white', 'purple')

        import io
        file = io.StringIO(emojize(text(*message_content, sep='\n')))
        for week in grid:
            for i in week:
                if i[1].date() == datetime.now().date():
                    if 'white' in i[0] or 'black' in i[0]:
                        i[0] = i[0].replace('circle', 'large_square')
                    else:
                        i[0] = i[0].replace('circle', 'square')
        grid = [[i[0] for i in week] for week in grid]
        await message.answer_document(file, caption=emojize(text(
            text('Пн Вт Ср Чт Пт Сб Вс'),
            *[text(*week, sep='') for week in grid],
            sep='\n'
        )))


@dp.message_handler(HashTag(hashtags=['сегодня', 'Сегодня', 'today', 'Today']))
async def create_today_todo_list(message: types.Message, user: User, chat: Chat):
    dt = message.date
    async with OrmSession() as session:
        parsed_todo_items = get_bulleted_items_list_from_message(message)
        if parsed_todo_items:
            select_stmt = select(Project) \
                .where(
                Project.owner_user_id == user.id,
                Project.chat_id == chat.id
            ) \
                .order_by(Project.id)
            projects_result = await session.execute(select_stmt)
            project = projects_result.scalars().first()

            bucket = PeriodBucket.new(project.period_bucket_mode, dt)
            new_todo_list = await project.create_new_for_day_with_items_or_append_to_existing(
                session, bucket, dt, parsed_todo_items
            )
            await session.commit()
            reply_message_text = text(
                text('План составлен не с вечера, но и день в день - тоже замечательно. Вот, пожалуйста:')
                if new_todo_list else text('К вашим сегодняшним планам я добавлю:'),
                text(''),
                *[text(':inbox_tray:', parsed_item) for parsed_item in parsed_todo_items],
                text(''),
                text('Чтобы свериться со списком запланированных дел, можно набрать /todo'),
                sep='\n'
            )
            await message.reply(emojize(reply_message_text))


item_logging.apply_registration(dp)
updateprojectsettings.apply_registration(dp)
newproject.apply_registration(dp)


@dp.message_handler()
async def create_tomorrow_todo_list(message: types.Message, user: User, chat: Chat):
    dt = message.date
    async with OrmSession() as session:
        parsed_todo_items = get_bulleted_items_list_from_message(message)
        if parsed_todo_items:
            select_stmt = select(Project) \
                .where(
                Project.owner_user_id == user.id,
                Project.chat_id == chat.id
            ) \
                .order_by(Project.id)
            projects_result = await session.execute(select_stmt)
            project = projects_result.scalars().first()

            bucket = PeriodBucket.new(project.period_bucket_mode, dt)
            new_todo_list = await project.create_new_for_day_with_items_or_append_to_existing(
                session, bucket.get_next(), dt, parsed_todo_items
            )
            await session.commit()
            reply_message_text = text(
                text('Я запишу, что вы запланировали:')
                if new_todo_list else text('К тому, что вы уже запланировали я добавлю:'),
                text(''),
                *[text(':inbox_tray: ', parsed_item) for parsed_item in parsed_todo_items],
                text(''),
                text('Завтра я напомню об этом. Чтобы посмотреть планы в любой момент, можно набрать /planned'),
                sep='\n'
            )
            await message.reply(emojize(reply_message_text))


async def on_startup(_):
    asyncio.create_task(notification_processing_loop())


if __name__ == '__main__':
    dp.middleware.setup(LoggingMiddleware(log))
    dp.middleware.setup(WhitelistMiddleware(WHITELISTED_USERS, WHITELISTED_CHATS))
    dp.middleware.setup(GetOrCreateChatMiddleware())
    dp.middleware.setup(GetOrCreateUserMiddleware())
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
