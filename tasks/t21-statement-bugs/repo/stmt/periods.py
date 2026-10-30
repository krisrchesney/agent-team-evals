"""Statement periods and local time."""
import calendar
import datetime

UTC = datetime.timezone.utc


def month_period(year, month, utc_offset_minutes=0):
    """The statement period for a month as (start, end), aware UTC datetimes, end exclusive."""
    start = datetime.datetime(year, month, 1, tzinfo=UTC)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime.datetime(year, month, last_day, tzinfo=UTC)
    return start, end


def local_date(moment, utc_offset_minutes):
    """The calendar date of an aware datetime in a fixed-offset time zone."""
    zone = datetime.timezone(datetime.timedelta(minutes=utc_offset_minutes))
    return moment.astimezone(zone).date()
