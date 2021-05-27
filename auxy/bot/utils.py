from aiogram import types
from dateutil.relativedelta import relativedelta, MO


def next_working_day(dt, **kwargs):
    next_day = dt + relativedelta(days=+1, **kwargs)
    if next_day.isoweekday() in [6, 7]:
        return next_day + relativedelta(weekday=MO)
    return next_day


def parse_todo_list_message(message: types.Message):
    todo_items = []
    for message_line in message['text'].split('\n'):
        if message_line.startswith('-') or message_line.startswith('*'):
            todo_items.append(message_line[1:].strip())
    return todo_items
