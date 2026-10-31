"""Expanding an event into its occurrences."""
import calendar as _calendar
from datetime import datetime, timedelta


def _month_day(year, month, day):
    return min(day, _calendar.monthrange(year, month)[1])


def rule_dates(rule, first, limit):
    """Dates the rule generates from `first` on, up to `limit`, ignoring skips."""
    produced = 0

    def room():
        return rule.count is None or produced < rule.count

    if rule.freq == "daily":
        day = first
        while day <= limit and room() and (rule.until is None or day <= rule.until):
            yield day
            produced += 1
            day += timedelta(days=rule.interval)
    elif rule.freq == "weekly":
        wanted = rule.weekdays or (first.weekday(),)
        week_start = first - timedelta(days=first.weekday())
        while week_start <= limit and room():
            for number in wanted:
                day = week_start + timedelta(days=number)
                if day < first:
                    continue
                if day > limit or not room() or (rule.until is not None and day > rule.until):
                    return
                yield day
                produced += 1
            week_start += timedelta(weeks=rule.interval)
    else:
        index = 0
        while room():
            months = first.year * 12 + first.month - 1 + index * rule.interval
            year, month = divmod(months, 12)
            day = first.replace(year=year, month=month + 1, day=_month_day(year, month + 1, first.day))
            if day > limit or (rule.until is not None and day > rule.until):
                return
            yield day
            produced += 1
            index += 1


def expand(event, lo, hi):
    """(start, end) of every occurrence that overlaps [lo, hi), oldest first."""
    if event.rule is None:
        starts = [event.start]
    else:
        starts = [datetime.combine(day, event.start.time())
                  for day in rule_dates(event.rule, event.start.date(), hi.date())
                  if day not in event.skips]
    return [(s, s + event.duration) for s in starts if s < hi and s + event.duration > lo]
