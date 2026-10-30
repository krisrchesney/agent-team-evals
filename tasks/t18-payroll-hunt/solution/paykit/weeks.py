"""Pay weeks run from Monday to Sunday."""
import datetime


def week_start(day):
    """The Monday of the week that contains `day`."""
    return day - datetime.timedelta(days=day.weekday())


def week_key(day):
    """A value that is equal for all days of one pay week and different for different weeks."""
    return week_start(day)
