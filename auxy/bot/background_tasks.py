import logging
from datetime import datetime
import asyncio
import io
from aiogram import types
from aiogram.utils.emoji import emojize
from aiogram.utils.markdown import text
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from dateutil.relativedelta import relativedelta, WE
import pytz
from auxy.db import OrmSession
from auxy.db.models import Project, ItemsList, Item
from . import bot
from auxy.utils import generate_grid
from auxy.utils import PeriodBucket


notification_time_cache = dict()


async def notification_processing_loop():
    nsktz = pytz.timezone('Asia/Novosibirsk')
    while True:
        async with OrmSession() as session:
            select_stmt = select(Project)
            projects_result = await session.execute(select_stmt)
            for project in projects_result.scalars():
                await process_project_settings_and_send_messages(session, project, datetime.now(nsktz))
        await asyncio.sleep(10)


async def process_project_settings_and_send_messages(session, project, now):
    for func, config in project.settings.items():
        action = actions.get(func)
        if action:
            notification_settings = config['notification_settings']
            await schedule_notification(session, action, project, notification_settings, now)
            await asyncio.sleep(.05)


async def schedule_notification(session, action, project, notification_settings, now):
    global notification_time_cache
    cache_key = f'{project.id}-{action.__name__}'

    if cache_key not in notification_time_cache:
        notification_time_cache[cache_key] = get_next_notification_time(now, notification_settings)
        logging.info(
            'Notification "%s" for project#%s have been scheduled to %s',
            action.__name__, project.id,
            notification_time_cache[cache_key]
        )

    next_notification_time = notification_time_cache.get(cache_key)
    if now >= next_notification_time:
        await action(session, project, now)
        notification_time_cache.pop(cache_key)


def get_next_notification_time(now, timings):
    possible_times = [now + relativedelta(**timing) for timing in timings]
    possible_times = list(filter(lambda possible_time: possible_time > now, possible_times))
    if len(possible_times) == 1:
        return possible_times[0]
    return min(*possible_times)


async def todo_for_today(session, project, now):
    config = project.settings['todo_for_today']
    logging.info('Calling at %s todo_for_today for project%s %s', now, project.id, config)
    bucket = PeriodBucket.new(project.period_bucket_mode, now.date())
    select_stmt = select(ItemsList) \
        .options(selectinload(ItemsList.items)) \
        .where(
        ItemsList.project_id == project.id,
        ItemsList.period_bucket_key == bucket.key(),
        ) \
        .order_by(ItemsList.created_dt.desc())
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
                              text('Все точно получится!'),
                          ]
        await bot.send_message(
            project.chat_id,
            emojize(text(*message_content, sep='\n')),
            disable_web_page_preview=True,
        )
    else:
        await bot.send_message(
            project.chat_id,
            text('У вас с вечера не составлены планы.', 'Предлагаю составить их прямо сейчас.'),
        )


async def end_of_work_day(session, project, now):
    config = project.settings['end_of_work_day']
    logging.info('Calling at %s end_of_work_day for project%s %s', now, project.id, config)
    bucket = PeriodBucket.new(project.period_bucket_mode, now.date())
    select_stmt = select(ItemsList) \
        .options(
            selectinload(ItemsList.items).selectinload(Item.notes)
        ) \
        .where(
        ItemsList.project_id == project.id,
        ItemsList.period_bucket_key == bucket.key(),
        ) \
        .order_by(ItemsList.created_dt.desc())
    todo_lists_result = await session.execute(select_stmt)
    todo_list = todo_lists_result.scalars().first()
    if todo_list:
        today_report = [text('Напомню, что было сегодня:')]
        for item in todo_list.items:
            today_report.append(text(':pushpin:', item.text))
            for log_message in item.notes:
                today_report.append(text('    :paperclip:', log_message.text))
        today_report.append(text('Чтобы сохранить важные замечания, воспользуйтесь командой /log'))
    else:
        today_report = [text('Списка дел на сегодня не было')]

    reminder_text_lines = config['reminder_text'].split('\n')
    message_content = [
        text(reminder_text_lines[0]),
        text(''),
        *today_report,
        text(''),
        *list(map(text, reminder_text_lines[1:])),
    ]
    await bot.send_message(
        project.chat_id,
        emojize(text(*message_content, sep='\n')),
        disable_web_page_preview=True,
    )


async def weekly_status_report(session, project, now):
    config = project.settings['weekly_status_report']
    logging.info('Calling at %s weekly_status_report for project%s %s', now, project.id, config)
    start_dt = now + relativedelta(weekday=WE(-1), hour=0, minute=0, second=0, microsecond=0)
    end_dt = now + relativedelta(weekday=WE, hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=1)
    grid = generate_grid(start_dt, end_dt)
    grid = [[[i[0], i[1]] for i in week] for week in grid]
    bucket = PeriodBucket.new(project.period_bucket_mode, start_dt.date())
    select_stmt = select(ItemsList) \
        .options(
            selectinload(ItemsList.items)
            .selectinload(Item.notes)
        ) \
        .where(
        ItemsList.project_id == project.id,
        ItemsList.period_bucket_key >= bucket.key(),
        ) \
        .order_by(ItemsList.period_bucket_key)
    project_daily_todo_lists = await session.execute(select_stmt)

    message_content = []
    for todo_list in project_daily_todo_lists.scalars():
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

    for week in grid:
        for i in week:
            if i[1].date() == datetime.now().date():
                if 'white' in i[0] or 'black' in i[0]:
                    i[0] = i[0].replace('circle', 'large_square')
                else:
                    i[0] = i[0].replace('circle', 'square')
    grid = [[i[0] for i in week] for week in grid]
    if message_content:
        file = io.StringIO(emojize(text(*message_content, sep='\n')))
        await bot.send_document(project.chat_id, file, caption=emojize(text(
            text(f'Отчет о проделанной работе с {start_dt.date()} по {end_dt.date()}'),
            text(''),
            text('Пн Вт Ср Чт Пт Сб Вс'),
            *[text(*week, sep='') for week in grid],
            sep='\n'
        )))
    else:
        await bot.send_message(
            project.chat_id,
            emojize(text(
                text(f'В период с {start_dt.date()} по {end_dt.date()} получается пустой отчет о проделанной работе'),
                text(''),
                text('Пн Вт Ср Чт Пт Сб Вс'),
                *[text(*week, sep='') for week in grid],
                sep='\n'
            )),
            disable_web_page_preview=True,
        )

actions = {
    'todo_for_today': todo_for_today,
    'end_of_work_day': end_of_work_day,
    'weekly_status_report': weekly_status_report,
}
