"""Statement periods and local time."""
import datetime

UTC = datetime.timezone.utc


def month_period(year, month, utc_offset_minutes=0):
    """The statement period for a month as (start, end), aware UTC datetimes, end exclusive.

    The month is a calendar month in the account's local time (docs/STATEMENTS.md, rule 1).
    """
    zone = datetime.timezone(datetime.timedelta(minutes=utc_offset_minutes))
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    start = datetime.datetime(year, month, 1, tzinfo=zone).astimezone(UTC)
    end = datetime.datetime(next_year, next_month, 1, tzinfo=zone).astimezone(UTC)
    return start, end


def local_date(moment, utc_offset_minutes):
    """The calendar date of an aware datetime in a fixed-offset time zone."""
    zone = datetime.timezone(datetime.timedelta(minutes=utc_offset_minutes))
    return moment.astimezone(zone).date()
