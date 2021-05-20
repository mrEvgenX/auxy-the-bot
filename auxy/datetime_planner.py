from datetime import datetime
from dateutil.relativedelta import relativedelta, MO

"""
>>> datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=MO)
datetime.datetime(2021, 5, 24, 17, 0)
>>> datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=TU)
datetime.datetime(2021, 5, 25, 17, 0)
>>> datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=WE)
datetime.datetime(2021, 5, 26, 17, 0)
>>> datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=TH)
datetime.datetime(2021, 5, 20, 17, 0)
>>> datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=FR)
datetime.datetime(2021, 5, 21, 17, 0)

Take minimal dt not in past
>>> datetime(2021, 5, 20, 23) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=TH)
datetime.datetime(2021, 5, 20, 17, 0)
or something like
>>> datetime(2021, 5, 20, 23) > datetime(2021, 5, 20, 23) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=TH)
True
>>> datetime(2021, 5, 20, 16, 40, 3) > datetime(2021, 5, 20, 16, 40, 3) + relativedelta(hour=17, minute=0, second=0, microsecond=0, weekday=TH)
False
>>>

Или запоминать следующее время для нотификации
А обновлять только после отправки
Все равно там везде хардкод (если менять в базе, то релоадить приложение полностью)
"""


def next_working_day(dt, **kwargs):
    next_day = dt + relativedelta(days=+1, **kwargs)
    if next_day.isoweekday() in [6, 7]:
        return next_day + relativedelta(weekday=MO)
    return next_day
