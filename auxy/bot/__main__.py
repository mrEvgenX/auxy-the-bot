import logging
import json
from datetime import datetime
import asyncio
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from dateutil.relativedelta import relativedelta
import pytz
from auxy.settings import TELEGRAM_BOT_API_TOKEN, WHITELISTED_USERS
from auxy.db import OrmSession
from auxy.db.models import BotSettings, User, DailyTodoList, TodoItem
from .middleware import WhitelistMiddleware
from .utils import next_working_day, parse_todo_list_message


logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_BOT_API_TOKEN)
dp = Dispatcher(bot)


workday_begin_config = dict()
workday_end_config = dict()
notification_time_cache = dict()


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='start')
async def start(message: types.Message):
    """
    Регистрация пользователя, приветствие, краткое руководство для начала работы
    """
    sender = message['from']
    dt = message['date']
    async with OrmSession() as session:
        user = await session.get(User, sender['id'])
        if not user:
            user = User(
                id=sender['id'],
                username=sender['username'],
                first_name=sender['first_name'],
                last_name=sender['last_name'],
                lang=sender['language_code'],
                joined_dt=dt
            )
            session.add(user)
            await session.commit()
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


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='help')
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


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='todo')
async def todo_for_today(message: types.Message):
    sender = message['from']
    dt = message['date']
    async with OrmSession() as session:
        user = await session.get(User, sender['id'])
        if user:
            select_stmt = select(DailyTodoList) \
                .options(selectinload(DailyTodoList.items)) \
                .where(
                    DailyTodoList.user_id == user.id,
                    DailyTodoList.for_day == dt.date(),
                ) \
                .order_by(DailyTodoList.created_dt.desc())
            todo_lists_result = await session.execute(select_stmt)
            todo_list = todo_lists_result.scalars().first()
            if todo_list:
                message_content = [
                    text('Вот, что вы на сегодня планировали:'),
                    text('')
                ] + [
                    text(':pushpin: ' + item.text) for item in todo_list.items
                ] + [
                    text(''),
                    text('Все точно получится!')
                ]
            else:
                message_content = [
                    text('Никаких планов нет.'),
                    # TODO предложение создать план и описание способа
                ]
            await message.answer(emojize(text(*message_content, sep='\n')))


@dp.message_handler(chat_type=types.ChatType.PRIVATE, commands='planned')
async def todo_for_next_time(message: types.Message):
    # TODO почти copy-paste, разобраться
    sender = message['from']
    dt = message['date']
    async with OrmSession() as session:
        user = await session.get(User, sender['id'])
        if user:
            select_stmt = select(DailyTodoList) \
                .options(selectinload(DailyTodoList.items)) \
                .where(
                    DailyTodoList.user_id == user.id,
                    DailyTodoList.for_day == next_working_day(dt).date(),
                ) \
                .order_by(DailyTodoList.created_dt.desc())
            todo_lists_result = await session.execute(select_stmt)
            todo_list = todo_lists_result.scalars().first()
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


@dp.message_handler(chat_type=types.ChatType.PRIVATE)
async def create_todo_list_for_tomorrow(message: types.Message):
    # TODO use reply_to_message https://core.telegram.org/bots/api#message
    sender = message.from_user
    dt = message.date
    todo_list_for_day = next_working_day(dt).date()
    async with OrmSession() as session:
        user = await session.get(User, sender.id)
        parsed_todo_items = parse_todo_list_message(message)
        if user and parsed_todo_items:
            reply_message_content = []
            select_stmt = select(DailyTodoList) \
                .options(selectinload(DailyTodoList.items)) \
                .where(
                    DailyTodoList.user_id == user.id,
                    DailyTodoList.for_day == todo_list_for_day,
                ) \
                .order_by(DailyTodoList.created_dt.desc())
            todo_lists_result = await session.execute(select_stmt)
            tomorrow_todo_list = todo_lists_result.scalars().first()
            if tomorrow_todo_list:
                reply_message_content += [text('К тому, что вы уже запланировали я добавлю:'), text('')]
            else:
                tomorrow_todo_list = DailyTodoList(
                    user_id=user.id,
                    created_dt=dt,
                    for_day=todo_list_for_day
                )
                session.add(tomorrow_todo_list)
                reply_message_content += [text('Я запишу, что вы запланировали:'), text('')]
            for parsed_item in parsed_todo_items:
                todo_item = TodoItem(
                    user_id=user.id,
                    text=parsed_item,
                    created_dt=dt
                )
                session.add(todo_item)
                tomorrow_todo_list.items.append(todo_item)
                reply_message_content.append(text(':pushpin: ' + parsed_item))
            reply_message_content += [
                text(''),
                text('Завтра я напомню об этом. Чтобы посмотреть планы в любой момент, можно набрать /planned')
            ]
            await session.commit()
            await message.reply(emojize(text(*reply_message_content, sep='\n')))


async def send_end_of_work_day_reminder():
    async with OrmSession() as session:
        users_rows = await session.stream(select(User).order_by(User.id))
        async for user in users_rows.scalars():
            await bot.send_message(
                user.id,
                workday_end_config['reminder_text']
            )  # TODO force reply


async def send_todo_for_today_notification(now):
    async with OrmSession() as session:
        select_stmt = select(DailyTodoList) \
            .options(selectinload(DailyTodoList.items)) \
            .where(
                DailyTodoList.for_day == now.date(),
            ) \
            .order_by(DailyTodoList.created_dt.desc())
        todo_lists_result = await session.execute(select_stmt)
        for todo_list in todo_lists_result.scalars():
            logging.info('processing todo list user_id=%s list_id=%s', todo_list.user_id, todo_list.id)
            message_content = [
                text('Вот, что вы на сегодня планировали:'),
                text('')
            ] + [
                text(':pushpin: ' + item.text) for item in todo_list.items
            ] + [
                text(''),
                text('Все точно получится!'),
            ]
            await bot.send_message(todo_list.user_id, emojize(text(*message_content, sep='\n')))


def get_next_notification_time(now, timings):
    possible_times = [now + relativedelta(**timing) for timing in timings]
    return min(*[possible_time for possible_time in possible_times if possible_time > now])


async def send_reminder():
    global notification_time_cache
    nsktz = pytz.timezone('Asia/Novosibirsk')
    now = datetime.now(nsktz)
    notification_time_cache['workday_begin'] = get_next_notification_time(now, workday_begin_config['reminder_timings'])
    notification_time_cache['workday_end'] = get_next_notification_time(now, workday_end_config['reminder_timings'])
    logging.info('workday_begin_notification_time %s', notification_time_cache['workday_begin'])
    logging.info('workday_end_notification_time %s', notification_time_cache['workday_end'])
    while True:
        now = datetime.now(nsktz)

        next_notification_time = notification_time_cache.get('workday_begin')
        if next_notification_time and now >= next_notification_time:
            await send_todo_for_today_notification(now)
            logging.info('new workday_begin_notification_time %s', next_notification_time)
        notification_time_cache['workday_begin'] = get_next_notification_time(now, workday_begin_config['reminder_timings'])

        next_notification_time = notification_time_cache.get('workday_end')
        if next_notification_time and now >= next_notification_time:
            await send_end_of_work_day_reminder()
            logging.info('new workday_begin_notification_time %s', next_notification_time)
        notification_time_cache['workday_end'] = get_next_notification_time(now, workday_end_config['reminder_timings'])
        await asyncio.sleep(10)


async def on_startup(_):
    global workday_begin_config, workday_end_config
    async with OrmSession() as session:
        workday_begin_settings_obj = await session.get(BotSettings, 'workday_begin')
        workday_end_settings_obj = await session.get(BotSettings, 'workday_end')
        if workday_begin_settings_obj and workday_end_settings_obj:
            workday_begin_config = workday_begin_settings_obj.content
            workday_end_config = workday_end_settings_obj.content
            logging.info(json.dumps(workday_begin_config, indent=4, sort_keys=True))
            logging.info(json.dumps(workday_end_config, indent=4, sort_keys=True))
        else:
            logging.error('Both sections "workday_begin" and "workday_end" must be present in db')
            exit(1)
    asyncio.create_task(send_reminder())


if __name__ == '__main__':
    dp.middleware.setup(WhitelistMiddleware(WHITELISTED_USERS))
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)