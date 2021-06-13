from auxy.utils import PeriodBucket, DailyBucket, WeeklyBucket, MonthlyBucket, YearlyBucket, PerpetualBucket
from datetime import datetime


def test_bucket_key():
    assert 'day-2021-01-01' == DailyBucket(datetime(2021, 1, 1, 12, 30, 15)).key()
    assert 'week-2020-53' == WeeklyBucket(datetime(2021, 1, 1, 12, 30, 15)).key()
    assert 'week-2021-1' == WeeklyBucket(datetime(2021, 1, 4, 12, 30, 15)).key()
    assert 'month-2021-1' == MonthlyBucket(datetime(2021, 1, 1, 12, 30, 15)).key()
    assert 'month-2021-12' == MonthlyBucket(datetime(2021, 12, 1, 12, 30, 15)).key()
    assert 'year-2021' == YearlyBucket(datetime(2021, 1, 1, 12, 30, 15)).key()
    assert 'perpetual' == PerpetualBucket('').key()


def test_bucket_from_key():
    assert PeriodBucket.get_by_key('day-2021-01-01').start() == datetime(2021, 1, 1)
    assert PeriodBucket.get_by_key('week-2020-53').start() == datetime(2020, 12, 28)
    assert PeriodBucket.get_by_key('week-2021-1').start() == datetime(2021, 1, 4)
    assert PeriodBucket.get_by_key('month-2021-1').start() == datetime(2021, 1, 1)
    assert PeriodBucket.get_by_key('year-2021').start() == datetime(2021, 1, 1)
    assert PeriodBucket.get_by_key('perpetual').start() is None
