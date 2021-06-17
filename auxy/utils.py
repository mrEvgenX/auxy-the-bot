import enum
import typing
from abc import abstractmethod
from datetime import datetime
from aiogram import types
from dateutil.relativedelta import relativedelta, MO


class ItemStatus(enum.Enum):
    active = 1
    done = 2
    rejected = 3


def get_bulleted_items_list_from_message(message: types.Message):
    items = []
    for message_line in message['text'].split('\n'):
        if message_line.startswith('-') or message_line.startswith('*'):
            items.append(message_line[1:].strip())
    return items


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


class PeriodBucket:

    @classmethod
    def new(cls, mode: 'PeriodBucketModes', dt: datetime):
        return mode.value(dt)

    @classmethod
    def get_by_key(cls, period_bucket_key):
        try:
            if period_bucket_key == 'perpetual':
                mode_name, key = period_bucket_key, ''
            else:
                mode_name, key = period_bucket_key.split('-', 1)
            ConcreteBucket = bucket_classes[mode_name]
            return ConcreteBucket(key)
        except ValueError:
            raise ValueError('wrong period bucket key')

    @abstractmethod
    def key(self):
        raise NotImplemented

    @abstractmethod
    def start(self) -> typing.Optional[datetime]:
        raise NotImplemented

    @abstractmethod
    def end(self) -> typing.Optional[datetime]:
        raise NotImplemented

    def is_valid(self):
        return True

    @abstractmethod
    def get_next(self) -> 'PeriodBucket':
        raise NotImplemented

    def __str__(self):
        start = self.start()
        end = self.end()
        if start and end:
            end_str = (end + relativedelta(days=-1)).date().isoformat()
            return f'{start.date().isoformat()} / {end_str}'
        return ''


class DailyBucket(PeriodBucket):

    def __init__(self, dt: typing.Union[str, datetime]):
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                raise ValueError('wrong period bucket key')
        self._day_start = dt + relativedelta(hour=0, minute=0, second=0, microsecond=0)

    def key(self) -> str:
        return 'day-' + self._day_start.date().isoformat()

    def start(self) -> typing.Optional[datetime]:
        return self._day_start

    def end(self) -> typing.Optional[datetime]:
        return self._day_start + relativedelta(days=1)

    def get_next(self) -> 'DailyBucket':
        return DailyBucket(self._day_start + relativedelta(days=1))

    def __str__(self):
        return self._day_start.date().isoformat()


class WorkingDaysBucket(DailyBucket):

    def is_valid(self):
        return self._day_start.isoweekday() not in [6, 7]

    def get_next(self) -> 'WorkingDaysBucket':
        new_day_start = self._day_start + relativedelta(days=1)
        if new_day_start.isoweekday() in [6, 7]:
            new_day_start += relativedelta(weekday=MO)
        return WorkingDaysBucket(new_day_start)


class WeeklyBucket(PeriodBucket):

    def __init__(self, dt: typing.Union[str, datetime]):
        if isinstance(dt, str):
            try:
                year, week = dt.split('-')
                dt = datetime.strptime(f'{year} {week} 1', '%G %V %u')
            except ValueError:
                raise ValueError('wrong period bucket key')
        self._week_start = dt + relativedelta(weekday=MO(-1), hour=0, minute=0, second=0, microsecond=0)

    def key(self) -> str:
        year, week, _ = self._week_start.isocalendar()
        return 'week-{}-{}'.format(year, week)

    def start(self) -> typing.Optional[datetime]:
        return self._week_start

    def end(self) -> typing.Optional[datetime]:
        return self._week_start + relativedelta(weeks=1)

    def get_next(self) -> 'WeeklyBucket':
        return WeeklyBucket(self._week_start + relativedelta(weeks=1))


class MonthlyBucket(PeriodBucket):

    def __init__(self, dt: typing.Union[str, datetime]):
        if isinstance(dt, str):
            try:
                year, month = dt.split('-')
                dt = datetime(int(year), int(month), 1)
            except ValueError:
                raise ValueError('wrong period bucket key')
        self._month_start = dt + relativedelta(day=1, hour=0, minute=0, second=0, microsecond=0)

    def key(self) -> str:
        return 'month-{}-{}'.format(self._month_start.year, self._month_start.month)

    def start(self) -> typing.Optional[datetime]:
        return self._month_start

    def end(self) -> typing.Optional[datetime]:
        return self._month_start + relativedelta(months=1)

    def get_next(self) -> 'MonthlyBucket':
        return MonthlyBucket(self._month_start + relativedelta(months=1))


class YearlyBucket(PeriodBucket):

    def __init__(self, dt: typing.Union[str, datetime]):
        if isinstance(dt, str):
            try:
                dt = datetime(int(dt), 1, 1)
            except ValueError:
                raise ValueError('wrong period bucket key')
        self._year_start = dt + relativedelta(day=1, month=1, hour=0, minute=0, second=0, microsecond=0)

    def key(self) -> str:
        return 'year-{}'.format(self._year_start.year)

    def start(self) -> typing.Optional[datetime]:
        return self._year_start

    def end(self) -> typing.Optional[datetime]:
        return self._year_start + relativedelta(months=1)

    def get_next(self) -> 'YearlyBucket':
        return YearlyBucket(self._year_start + relativedelta(months=1))


class PerpetualBucket(PeriodBucket):

    def __init__(self, dt: typing.Union[str, datetime]):
        pass

    def key(self) -> str:
        return 'perpetual'

    def start(self) -> typing.Optional[datetime]:
        return None

    def end(self) -> typing.Optional[datetime]:
        return None

    def get_next(self) -> 'PerpetualBucket':
        return self


class PeriodBucketModes(enum.Enum):
    daily = DailyBucket
    onworkingdays = WorkingDaysBucket
    weekly = WeeklyBucket
    monthly = MonthlyBucket
    yearly = YearlyBucket
    perpetual = PerpetualBucket


bucket_classes = {
    'day': DailyBucket,
    'week': WeeklyBucket,
    'month': MonthlyBucket,
    'year': YearlyBucket,
    'perpetual': PerpetualBucket,
}
