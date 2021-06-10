import logging
from datetime import datetime
import asyncio
import json
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.future import select
from dateutil.relativedelta import relativedelta, WE
import pytz
from auxy.db import OrmSession
from auxy.db.models import BotSettings, User, DailyTodoList, TodoItem
from . import bot
from .utils import generate_grid

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
            report_message_part.append(text('Чтобы сохранить важные замечания, воспользуйтесь командой /log'))
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
    start_dt = now + relativedelta(weekday=WE(-1), hour=0, minute=0, second=0, microsecond=0)
    end_dt = now + relativedelta(weekday=WE, hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=1)
    grid = generate_grid(start_dt, end_dt)
    grid = [[[i[0], i[1]] for i in week] for week in grid]
    async with OrmSession() as session:
        select_stmt = select(User) \
            .options(
                selectinload(User.daily_todo_lists.and_(DailyTodoList.for_day >= start_dt.date()))
                .selectinload(DailyTodoList.items)
                .selectinload(TodoItem.log_messages)
            ) \
            .where(
                DailyTodoList.for_day >= start_dt.date(),
            ) \
            .order_by(DailyTodoList.for_day)
        users_result = await session.execute(select_stmt)
        for user in users_result.scalars():
            message_content = []
            for todo_list in user.daily_todo_lists:
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
            await bot.send_document(user.id, file, caption=emojize(text(
                text(f'Отчет о проделанной работе с {start_dt.date()} по {end_dt.date()}'),
                text(''),
                text('Пн Вт Ср Чт Пт Сб Вс'),
                *[text(*week, sep='') for week in grid],
                sep='\n'
            )))


def get_next_notification_time(now, timings):
    possible_times = [now + relativedelta(**timing) for timing in timings]
    possible_times = list(filter(lambda possible_time: possible_time > now, possible_times))
    if len(possible_times) == 1:
        return possible_times[0]
    return min(*possible_times)


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
        notification_time_cache['workday_end'] = get_next_notification_time(
            now, workday_end_config['reminder_timings']
        )

        next_notification_time = notification_time_cache.get('weekly_status_report')
        if next_notification_time and now >= next_notification_time:
            await _send_weekly_status_report(now)
        notification_time_cache['weekly_status_report'] = get_next_notification_time(
            now, weekly_status_report_config['reminder_timings']
        )

        await asyncio.sleep(10)
