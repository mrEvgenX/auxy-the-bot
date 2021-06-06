import logging
from datetime import datetime
import asyncio
import json
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from dateutil.relativedelta import relativedelta
import pytz
from auxy.db import OrmSession
from auxy.db.models import BotSettings, User, DailyTodoList, TodoItem
from . import bot


workday_begin_config = dict()
workday_end_config = dict()
weekly_status_report_config = dict()
notification_time_cache = dict()


async def _send_end_of_work_day_reminder(now):
    async with OrmSession() as session:
        select_stmt = select(DailyTodoList) \
            .options(
                selectinload(DailyTodoList.items).selectinload(TodoItem.log_messages)
            ) \
            .where(
                DailyTodoList.for_day == now.date(),
            ) \
            .order_by(DailyTodoList.created_dt.desc())
        todo_lists_result = await session.execute(select_stmt)
        today_reports = dict()
        for todo_list in todo_lists_result.scalars():
            report_message_part = [text('Напомню, что было сегодня:')]
            for item in todo_list.items:
                report_message_part.append(text(':pushpin:', item.text))
                for log_message in item.log_messages:
                    report_message_part.append(text('    :paperclip:', log_message.text))
            report_message_part.append(text('Чтобы сохранить важные замечания, можете напечатать следующее:'))
            report_message_part.append(text('/log <порядковый номер сегодняшней задачи> '
                                            '<краткое сообщение о проделанной работе>'))
            today_reports[todo_list.user_id] = report_message_part

        users_rows = await session.stream(select(User).order_by(User.id))
        async for user in users_rows.scalars():
            reminder_text_lines = workday_end_config['reminder_text'].split('\n')
            message_content = [
                text(reminder_text_lines[0]),
                text(''),
                *today_reports.get(user.id, [text('Списка дел на сегодня не было')]),
                text(''),
                *list(map(text, reminder_text_lines[1:])),
            ]
            await bot.send_message(
                user.id,
                emojize(text(*message_content, sep='\n'))
            )


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


async def _send_weekly_status_report(now):
    async with OrmSession() as session:
        select_stmt = select(User) \
            .options(
                selectinload(User.daily_todo_lists)
                .selectinload(DailyTodoList.items)
                .selectinload(TodoItem.log_messages)
            ) \
            .where(
                DailyTodoList.for_day == now.date(),
            ) \
            .order_by(DailyTodoList.created_dt.desc())
        users_result = await session.execute(select_stmt)
        for user in users_result.scalars():
            # TODO Сгрести в кучу все пункты за неделю с их заметками и отправить
            pass



def get_next_notification_time(now, timings):
    possible_times = [now + relativedelta(**timing) for timing in timings]
    return min(*[possible_time for possible_time in possible_times if possible_time > now])


async def send_reminder():
    global notification_time_cache, workday_begin_config, workday_end_config, weekly_status_report_config
    async with OrmSession() as session:
        workday_begin_settings_obj = await session.get(BotSettings, 'workday_begin')
        workday_end_settings_obj = await session.get(BotSettings, 'workday_end')
        weekly_status_report_settings_obj = await session.get(BotSettings, 'weekly_status_report')
        if workday_begin_settings_obj and workday_end_settings_obj:
            workday_begin_config = workday_begin_settings_obj.content
            workday_end_config = workday_end_settings_obj.content
            weekly_status_report_config = weekly_status_report_settings_obj.content
            logging.info(json.dumps(workday_begin_config, indent=4, sort_keys=True))
            logging.info(json.dumps(workday_end_config, indent=4, sort_keys=True))
            logging.info(json.dumps(weekly_status_report_config, indent=4, sort_keys=True))
        else:
            logging.error('Sections "workday_begin", "workday_end" and "weekly_status_report" must be present in db')
            exit(1)
    nsktz = pytz.timezone('Asia/Novosibirsk')
    now = datetime.now(nsktz)
    notification_time_cache['workday_begin'] = get_next_notification_time(
        now, workday_begin_config['reminder_timings']
    )
    notification_time_cache['workday_end'] = get_next_notification_time(
        now, workday_end_config['reminder_timings']
    )
    notification_time_cache['weekly_status_report'] = get_next_notification_time(
        now, weekly_status_report_config['reminder_timings']
    )
    logging.info('workday_begin_notification_time %s', notification_time_cache['workday_begin'])
    logging.info('workday_end_notification_time %s', notification_time_cache['workday_end'])
    logging.info('weekly_status_report_notification_time %s', notification_time_cache['weekly_status_report'])
    while True:
        now = datetime.now(nsktz)

        next_notification_time = notification_time_cache.get('workday_begin')
        if next_notification_time and now >= next_notification_time:
            await send_todo_for_today_notification(now)
            logging.info('new workday_begin_notification_time %s', next_notification_time)
        notification_time_cache['workday_begin'] = get_next_notification_time(
            now, workday_begin_config['reminder_timings']
        )

        next_notification_time = notification_time_cache.get('workday_end')
        if next_notification_time and now >= next_notification_time:
            await _send_end_of_work_day_reminder(now)
            logging.info('new workday_begin_notification_time %s', next_notification_time)
        notification_time_cache['workday_end'] = get_next_notification_time(
            now, workday_end_config['reminder_timings']
        )

        next_notification_time = notification_time_cache.get('weekly_status_report')
        if next_notification_time and now >= next_notification_time:
            await _send_weekly_status_report(now)
            logging.info('new weekly_status_report_notification_time %s', next_notification_time)
        notification_time_cache['weekly_status_report'] = get_next_notification_time(
            now, weekly_status_report_config['reminder_timings']
        )

        await asyncio.sleep(10)
