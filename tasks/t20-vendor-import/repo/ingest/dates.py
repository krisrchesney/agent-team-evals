"""Date parsing with explicit, per-supplier formats."""
import datetime


def parse(text, fmt):
    """Parse with a strptime format; raises ValueError for a wrong shape or an impossible date."""
    return datetime.datetime.strptime(text.strip(), fmt).date()


def add_days(date, days):
    return date + datetime.timedelta(days=days)
