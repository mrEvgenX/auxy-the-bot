from dateutil.relativedelta import relativedelta, MO


def next_working_day(dt, **kwargs):
    next_day = dt + relativedelta(days=+1, **kwargs)
    if next_day.isoweekday() in [6, 7]:
        return next_day + relativedelta(weekday=MO)
    return next_day
