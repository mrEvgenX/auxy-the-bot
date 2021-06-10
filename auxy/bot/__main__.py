import logging
import enum
import asyncio
from datetime import datetime
from dateutil.relativedelta import relativedelta, WE
from aiogram import executor, types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters import Text, HashTag
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from auxy.settings import WHITELISTED_USERS
from auxy.db import OrmSession
from auxy.db.models import User, TodoItemLogMessage
from .middleware import WhitelistMiddleware, PrivateChatOnlyMiddleware, GetOrCreateUserMiddleware
from .utils import next_working_day, parse_todo_list_message, generate_grid
from .background_tasks import send_reminder
from . import dp


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class TodoListFor(enum.Enum):
    today = 1
    tomorrow = 2


class LogMessageForm(StatesGroup):
    todo_item_id = State()
    log_message_text = State()


@dp.message_handler(commands='start')
async def start(message: types.Message, user: User, is_new_user: bool):
    """
    Регистрация пользователя, приветствие, краткое руководство для начала работы
    """
    if not is_new_user:
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
async def todo_for_today(message: types.Message, user: User):
    dt = message.date
    async with OrmSession() as session:
        todo_list = await user.get_for_day(session, dt.date(), with_log_messages=True)
        if todo_list:
            message_content = [
                text('Вот, что вы на сегодня планировали:'),
                text('')
            ]
            for item in todo_list.items:
                message_content.append(text(':pushpin:', item.text))
                for log_message in item.log_messages:
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
async def todo_for_next_time(message: types.Message, user: User):
    # TODO почти copy-paste, разобраться
    dt = message.date
    async with OrmSession() as session:
        todo_list = await user.get_for_day(session, next_working_day(dt).date())
        if todo_list:
            message_content = [
                text('Вот, что запланировано вами на следующий рабочий день:'),
                text('')
            ] + [
                text(':pushpin: ' + item.text) for item in todo_list.items
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
async def cancel_newrecord(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer('В данный момент мне нечего отменять')
    else:
        await state.finish()
        await message.reply('Ладно, не в этот раз')


@dp.message_handler(commands='log')
async def log_message_about_work(message: types.Message, user: User, state: FSMContext):
    dt = message.date
    async with OrmSession() as session:
        todo_list = await user.get_for_day(session, dt.date())
        items_num = len(todo_list.items) if todo_list else 0
        if items_num > 0:
            items_texts = [todo_item.text for todo_item in todo_list.items]
            await state.update_data(todo_items_num=items_num)
            await state.update_data(todo_items_texts=items_texts)
            await state.update_data(todo_items_ids=[todo_item.id for todo_item in todo_list.items])
            if items_num > 1:
                await LogMessageForm.todo_item_id.set()
                await message.reply(f'Напишите, пожалуйста, порядковый номер сегодняшней задачи от 1 до {items_num}')
            else:
                await state.update_data(todo_item_in_list_pos=0)
                await LogMessageForm.log_message_text.set()
                await message.reply(emojize(text(
                    text('В плане один единственный пункт:'),
                    text('    :pushpin:', items_texts[0]),
                    text('Напишите свое сообщение и я его сохраню'),
                    sep='\n')))
        else:
            await message.answer('Извините, записи можно вести пока только по сегодняшним планам, '
                                 'а у вас ничего не запланировано')


@dp.message_handler(lambda message: message.text.isdigit() and int(message.text) >= 1, state=LogMessageForm.todo_item_id)
async def process_todo_item_id(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        items_num = data['todo_items_num']
        item_pos = int(message.text) - 1
        if item_pos >= items_num:
            await message.reply(f'В вашем сегодняшнем плане нет столько пунктов, апишите число от 1 до {items_num}')
        else:
            data['todo_item_in_list_pos'] = item_pos
            item_text = data['todo_items_texts'][item_pos]
            await LogMessageForm.next()
            await message.reply(emojize(text(
                text('Выбранный вами пункт:'),
                text('    :pushpin:', item_text),
                text('Теперь напишите само сообщение'),
                sep='\n')))


@dp.message_handler(lambda message: not message.text.isdigit() or int(message.text) < 1,
                    state=LogMessageForm.todo_item_id)
async def process_todo_item_id_invalid(message: types.Message):
    await message.reply('Мне нужна цифра больше единицы')


@dp.message_handler(state=LogMessageForm.log_message_text)
async def process_log_message_text(message: types.Message, state: FSMContext):
    dt = message.date
    async with state.proxy() as data:
        async with OrmSession() as session:
            item_in_list_pos = data['todo_item_in_list_pos']
            item_id = data['todo_items_ids'][item_in_list_pos]
            log_message = TodoItemLogMessage(
                todo_item_id=item_id,
                text=message.text,
                created_dt=dt
            )
            logging.info(log_message)
            session.add(log_message)
            await session.commit()
    await message.reply(emojize(text(
        text('Все, так и запишу:'),
        text('    :pencil2:', message.text),
        sep='\n')))
    await state.finish()


@dp.message_handler(commands=['wsr', 'msr'])
async def status_report(message: types.Message, user: User):
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
        todo_lists = await user.get_since(session, start_dt.date(), with_log_messages=True)
        message_content = []
        for todo_list in todo_lists:
            for todo_item in todo_list.items:
                message_content.append(text(
                    ':spiral_calendar_pad:', todo_list.for_day,
                    ':pushpin:', todo_item.text
                ))
                for log_message in todo_item.log_messages:
                    message_content.append(text(':paperclip:', log_message.text))
                message_content.append(text(''))

            for week in grid:
                for i in week:
                    if i[1].date() == todo_list.for_day:
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
async def create_today_todo_list(message: types.Message, user: User):
    dt = message.date
    async with OrmSession() as session:
        parsed_todo_items = parse_todo_list_message(message)
        if parsed_todo_items:
            todo_list_for_day = dt.date()
            new_todo_list = await user.create_new_for_day_with_items_or_append_to_existing(
                session, todo_list_for_day, dt, parsed_todo_items
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


@dp.message_handler()
async def create_tomorrow_todo_list(message: types.Message, user: User):
    dt = message.date
    async with OrmSession() as session:
        parsed_todo_items = parse_todo_list_message(message)
        if parsed_todo_items:
            todo_list_for_day = next_working_day(dt).date()
            new_todo_list = await user.create_new_for_day_with_items_or_append_to_existing(
                session, todo_list_for_day, dt, parsed_todo_items
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
    asyncio.create_task(send_reminder())


if __name__ == '__main__':
    dp.middleware.setup(LoggingMiddleware(log))
    dp.middleware.setup(PrivateChatOnlyMiddleware())
    dp.middleware.setup(WhitelistMiddleware(WHITELISTED_USERS))
    dp.middleware.setup(GetOrCreateUserMiddleware())
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
