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


def generate_grid(start_dt, end_dt):
    grid = []
    dt_cursor = start_dt + relativedelta(weekday=MO(-1))
    while dt_cursor < end_dt:
        days_b = (start_dt - dt_cursor).days
        days_a = (end_dt - dt_cursor).days + 1
        grid.append(
            list(zip(
                [':minus:'] * days_b +
                [':white_circle:'] * (min(5, days_a) - max(days_b, 0)) +
                [':black_circle:'] * min(2, days_a - 5, max(0, 7 - days_b)) +
                [':minus:'] * (7 - days_a)
                ,
                [dt_cursor+relativedelta(days=i) for i in range(7)]
            ))
        )
        dt_cursor += relativedelta(weeks=1, weekday=MO(-1))
    return grid