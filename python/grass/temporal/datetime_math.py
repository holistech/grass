"""
Functions for mathematical datetime operations

SPDX-FileCopyrightText: 2011-2025 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import calendar
import copy
import re
from datetime import datetime, timedelta
from typing import TypedDict

from .core import get_tgis_message_interface

try:
    from dateutil import parser

    has_dateutil = True
except (ImportError, ModuleNotFoundError):
    has_dateutil = False


DAY_IN_SECONDS = 86400
SECOND_AS_DAY = 1.1574074074074073e-05


def relative_time_to_time_delta(value: float) -> timedelta:
    """Convert the double value representing days into a timedelta object."""
    days = int(value)
    seconds = value % 1
    seconds = round(seconds * DAY_IN_SECONDS)
    return timedelta(days, seconds)


def time_delta_to_relative_time(delta: timedelta) -> float:
    """Convert the time delta into a double value, representing days."""
    return float(delta.days) + float(delta.seconds * SECOND_AS_DAY)


def relative_time_to_time_delta_seconds(value: float) -> timedelta:
    """Convert the double value representing seconds into a timedelta object."""
    days = value / 86400
    seconds = int(value % 86400)
    return timedelta(days, seconds)


def time_delta_to_relative_time_seconds(delta: timedelta) -> float:
    """Convert the time delta into a double value, representing seconds."""

    return float(delta.days * DAY_IN_SECONDS) + float(delta.seconds)


###############################################################################


def decrement_datetime_by_string(
    mydate: datetime, increment: str, mult=1
) -> datetime | None:
    """Return a new datetime object decremented with the provided
    relative dates specified as string.
    Additional a multiplier can be specified to multiply the increment
    before adding to the provided datetime object.

    Usage:

    .. code-block:: pycon

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "31 days"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 12, 1, 0, 0)

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "1 month"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 12, 1, 0, 0)

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "2 month"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 11, 1, 0, 0)

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "24 months"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(1999, 1, 1, 0, 0)

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "48 months"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(1997, 1, 1, 0, 0)

         >>> dt = datetime(2001, 6, 1, 0, 0, 0)
         >>> string = "5 months"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2001, 1, 1, 0, 0)

         >>> dt = datetime(2001, 6, 1, 0, 0, 0)
         >>> string = "7 months"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 11, 1, 0, 0)

         >>> dt = datetime(2001, 1, 1, 0, 0, 0)
         >>> string = "1 year"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 1, 1, 0, 0)


    :param mydate: A datetime object to incremented
    :param increment: A string providing increment information:
                      The string may include comma separated values of type
                      seconds, minutes, hours, days, weeks, months and years
                      Example: Increment the datetime 2001-01-01 00:00:00
                      with "60 seconds, 4 minutes, 12 hours, 10 days,
                      1 weeks, 5 months, 1 years" will result in the
                      datetime 2003-02-18 12:05:00
    :param mult: A multiplier, default is 1
    :return: The new datetime object or none in case of an error
    """
    return modify_datetime_by_string(mydate, increment, mult, sign=-1)


def increment_datetime_by_string(
    mydate: datetime, increment: str, mult=1
) -> datetime | None:
    """Return a new datetime object incremented with the provided
    relative dates specified as string.
    Additional a multiplier can be specified to multiply the increment
    before adding to the provided datetime object.

    Usage:

    .. code-block:: pycon

        >>> dt = datetime(2001, 9, 1, 0, 0, 0)
        >>> string = (
        ...     "60 seconds, 4 minutes, 12 hours, 10 days, 1 weeks, 5 months, 1 years"
        ... )
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2003, 2, 18, 12, 5)

        >>> dt = datetime(2001, 11, 1, 0, 0, 0)
        >>> string = "1 months"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 12, 1, 0, 0)

        >>> dt = datetime(2001, 11, 1, 0, 0, 0)
        >>> string = "13 months"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2002, 12, 1, 0, 0)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "72 months"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2007, 1, 1, 0, 0)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "72 months"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2007, 1, 1, 0, 0)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "5 minutes"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 1, 1, 0, 5)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "49 hours"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 1, 3, 1, 0)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "3600 seconds"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 1, 1, 1, 0)

        >>> dt = datetime(2001, 1, 1, 0, 0, 0)
        >>> string = "30 days"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 1, 31, 0, 0)


    :param mydate: A datetime object to incremented
    :param increment: A string providing increment information:
                      The string may include comma separated values of type
                      seconds, minutes, hours, days, weeks, months and years
                      Example: Increment the datetime 2001-01-01 00:00:00
                      with "60 seconds, 4 minutes, 12 hours, 10 days,
                      1 weeks, 5 months, 1 years" will result in the
                      datetime 2003-02-18 12:05:00
    :param mult: A multiplier, default is 1
    :return: The new datetime object or none in case of an error
    """
    return modify_datetime_by_string(mydate, increment, mult, sign=1)


def modify_datetime_by_string(
    mydate: datetime, increment: str, mult=1, sign: int = 1
) -> datetime | None:
    """Return a new datetime object incremented with the provided
    relative dates specified as string.
    Additional a multiplier can be specified to multiply the increment
    before adding to the provided datetime object.

    :param mydate: A datetime object to incremented
    :param increment: A string providing increment information:
                      The string may include comma separated values of type
                      seconds, minutes, hours, days, weeks, months and years
                      Example: Increment the datetime 2001-01-01 00:00:00
                      with "60 seconds, 4 minutes, 12 hours, 10 days,
                      1 weeks, 5 months, 1 years" will result in the
                      datetime 2003-02-18 12:05:00
    :param mult: A multiplier, default is 1
    :param sign: Choose 1 for positive sign (incrementing) or -1 for
                 negative sign (decrementing).
    :return: The new datetime object or none in case of an error
    """
    sign = int(sign)
    if sign not in {1, -1}:
        return None

    if increment:
        seconds = 0
        minutes = 0
        hours = 0
        days = 0
        weeks = 0
        months = 0
        years = 0

        inclist = []
        # Split the increment string
        incparts = increment.split(",")
        for incpart in incparts:
            inclist.append(incpart.strip().split(" "))

        for inc in inclist:
            msgr = get_tgis_message_interface()
            if len(inc) < 2:
                msgr.error(_("Wrong increment format: %s") % (increment))
                return None
            if inc[1].find("seconds") >= 0 or inc[1].find("second") >= 0:
                seconds = sign * mult * int(inc[0])
            elif inc[1].find("minutes") >= 0 or inc[1].find("minute") >= 0:
                minutes = sign * mult * int(inc[0])
            elif inc[1].find("hours") >= 0 or inc[1].find("hour") >= 0:
                hours = sign * mult * int(inc[0])
            elif inc[1].find("days") >= 0 or inc[1].find("day") >= 0:
                days = sign * mult * int(inc[0])
            elif inc[1].find("weeks") >= 0 or inc[1].find("week") >= 0:
                weeks = sign * mult * int(inc[0])
            elif inc[1].find("months") >= 0 or inc[1].find("month") >= 0:
                months = sign * mult * int(inc[0])
            elif inc[1].find("years") >= 0 or inc[1].find("year") >= 0:
                years = sign * mult * int(inc[0])
            else:
                msgr.error(_("Wrong increment format: %s") % (increment))
                return None

        return modify_datetime(
            mydate, years, months, weeks, days, hours, minutes, seconds
        )

    return mydate


###############################################################################


def _replace_year_month(mydate: datetime, year: int, month: int) -> datetime:
    """Return mydate moved to the given year and month

    A day behind the last day of the target month (31 January + 1 month,
    29 February + 1 year) is set to that last day. Raising instead would make
    every series that starts on day 29 to 31 unusable.
    """
    last_day = calendar.monthrange(year, month)[1]
    return mydate.replace(year=year, month=month, day=min(mydate.day, last_day))


def modify_datetime(
    mydate: datetime, years=0, months=0, weeks=0, days=0, hours=0, minutes=0, seconds=0
) -> datetime:
    """Return a new datetime object incremented with the provided
    relative dates and times

    A month or year step that ends behind the last day of the target month
    ends on that last day. Years and months form one calendar step of
    12 * years + months months with one cut, so "1 years, 11 months" and
    "23 months" end on the same day:

    .. code-block:: pycon

        >>> modify_datetime(datetime(2001, 1, 31), months=1)
        datetime.datetime(2001, 2, 28, 0, 0)
        >>> modify_datetime(datetime(2003, 3, 31), months=23)
        datetime.datetime(2005, 2, 28, 0, 0)
        >>> modify_datetime(datetime(2003, 3, 31), years=1, months=11)
        datetime.datetime(2005, 2, 28, 0, 0)
        >>> modify_datetime(datetime(2003, 12, 1), months=-24)
        datetime.datetime(2001, 12, 1, 0, 0)

    :raises ValueError: If the result lies beyond the year 9999 or before the
                        year 1, which datetime cannot hold
    """

    total_months = 12 * int(years) + int(months)
    if total_months != 0:
        target_year, target_month = divmod(
            mydate.year * 12 + mydate.month - 1 + total_months, 12
        )
        mydate = _replace_year_month(mydate, target_year, target_month + 1)

    step = timedelta(
        weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds
    )
    try:
        return mydate + step
    except OverflowError:
        # Callers catch ValueError, which the month and year step raises
        # beyond the same limits; OverflowError passed them and ended tools
        # with a traceback. "from None" drops the bare "date value out of range".
        if step < timedelta(0):
            msg = _("The date {date} minus {step} is before the year 1").format(
                date=mydate, step=-step
            )
        else:
            msg = _("The date {date} plus {step} is beyond the year 9999").format(
                date=mydate, step=step
            )
        raise ValueError(msg) from None


def datetime_after_steps(anchor: datetime, step: str, count: int) -> datetime | None:
    """Return the time stamp that lies count steps after the anchor

    A series that is built from a start time counts from this start: the n-th
    time stamp is the anchor plus n steps, with one cut per time stamp. Adding
    one step to the previous time stamp instead lets a cut at the end of a
    short month carry over into all later time stamps (31 January, 28 February,
    28 March, 28 April).

    Only a pure month or year step is counted from the anchor. A composite step
    such as "1 months, 1 days" stays chained, because counting it from the
    anchor would give other dates even without a cut (28 January plus two
    times "1 months, 1 days" is 2 April chained, but 30 March counted from the
    anchor). Steps in seconds to weeks give the same result either way and are
    multiplied, so that a loop which asks for every time stamp of a long
    series of days or hours takes one step per time stamp, not count steps.

    Usage:

    .. code-block:: pycon

        >>> anchor = datetime(2001, 1, 31)
        >>> for n in range(4):
        ...     print(datetime_after_steps(anchor, "1 months", n))
        2001-01-31 00:00:00
        2001-02-28 00:00:00
        2001-03-31 00:00:00
        2001-04-30 00:00:00

        >>> datetime_after_steps(datetime(2001, 1, 28), "1 months, 1 days", 2)
        datetime.datetime(2001, 4, 2, 0, 0)

        >>> datetime_after_steps(anchor, "1 months", 0)
        datetime.datetime(2001, 1, 31, 0, 0)

    :param anchor: The first time stamp of the series
    :param step: An increment string as for increment_datetime_by_string()
    :param count: The number of steps, 0 or more
    :return: The new datetime object or None if the step cannot be read
    :raises ValueError: If count is negative. A month step would go back in
                        time while a chained step would return the anchor.
    """
    if count < 0:
        msg = f"The number of steps must be 0 or more, not {count}"
        raise ValueError(msg)
    if count == 0:
        return anchor
    parts = step.split(",")
    calendar_part = any(
        len(words) == 2 and words[1].rstrip("s") in {"month", "year"}
        for words in (part.split() for part in parts)
    )
    if len(parts) == 1 or not calendar_part:
        return increment_datetime_by_string(anchor, step, mult=count)
    current = anchor
    for _i in range(count):
        current = increment_datetime_by_string(current, step)
        if current is None:
            return None
    return current


###############################################################################


def adjust_datetime_to_granularity(mydate: datetime, granularity):
    """Modify the datetime object to fit the given granularity

    - Years will start at the first of January
    - Months will start at the first day of the month
    - Days will start at the first Hour of the day
    - Hours will start at the first minute of an hour
    - Minutes will start at the first second of a minute

    Usage:

    .. code-block:: pycon

        >>> dt = datetime(2001, 8, 8, 12, 30, 30)
        >>> adjust_datetime_to_granularity(dt, "5 seconds")
        datetime.datetime(2001, 8, 8, 12, 30, 30)

        >>> adjust_datetime_to_granularity(dt, "20 minutes")
        datetime.datetime(2001, 8, 8, 12, 30)

        >>> adjust_datetime_to_granularity(dt, "20 minutes")
        datetime.datetime(2001, 8, 8, 12, 30)

        >>> adjust_datetime_to_granularity(dt, "3 hours")
        datetime.datetime(2001, 8, 8, 12, 0)

        >>> adjust_datetime_to_granularity(dt, "5 days")
        datetime.datetime(2001, 8, 8, 0, 0)

        >>> adjust_datetime_to_granularity(dt, "2 weeks")
        datetime.datetime(2001, 8, 6, 0, 0)

        >>> adjust_datetime_to_granularity(dt, "6 months")
        datetime.datetime(2001, 8, 1, 0, 0)

        >>> adjust_datetime_to_granularity(dt, "2 years")
        datetime.datetime(2001, 1, 1, 0, 0)

        >>> adjust_datetime_to_granularity(
        ...     dt, "2 years, 3 months, 5 days, 3 hours, 3 minutes, 2 seconds"
        ... )
        datetime.datetime(2001, 8, 8, 12, 30, 30)

        >>> adjust_datetime_to_granularity(dt, "3 months, 5 days, 3 minutes")
        datetime.datetime(2001, 8, 8, 12, 30)

        >>> adjust_datetime_to_granularity(dt, "3 weeks, 5 days")
        datetime.datetime(2001, 8, 8, 0, 0)

    """

    if granularity:
        has_seconds = False
        has_minutes = False
        has_hours = False
        has_days = False
        has_weeks = False
        has_months = False
        has_years = False

        seconds = mydate.second
        minutes = mydate.minute
        hours = mydate.hour
        days = mydate.day
        weekday = mydate.weekday()
        months = mydate.month
        years = mydate.year

        granlist = []
        # Split the increment string
        granparts = granularity.split(",")
        for granpart in granparts:
            granlist.append(granpart.strip().split(" "))

        for inc in granlist:
            if inc[1].find("seconds") >= 0 or inc[1].find("second") >= 0:
                has_seconds = True
            elif inc[1].find("minutes") >= 0 or inc[1].find("minute") >= 0:
                has_minutes = True
            elif inc[1].find("hours") >= 0 or inc[1].find("hour") >= 0:
                has_hours = True
            elif inc[1].find("days") >= 0 or inc[1].find("day") >= 0:
                has_days = True
            elif inc[1].find("weeks") >= 0 or inc[1].find("week") >= 0:
                has_weeks = True
            elif inc[1].find("months") >= 0 or inc[1].find("month") >= 0:
                has_months = True
            elif inc[1].find("years") >= 0 or inc[1].find("year") >= 0:
                has_years = True
            else:
                msgr = get_tgis_message_interface()
                msgr.error(_("Wrong granularity format: %s") % (granularity))
                return None

        if has_seconds:
            pass
        elif has_minutes:  # Start at 0 seconds
            seconds = 0
        elif has_hours:  # Start at 0 minutes and seconds
            seconds = 0
            minutes = 0
        elif has_days:  # Start at 0 hours, minutes and seconds
            seconds = 0
            minutes = 0
            hours = 0
        elif has_weeks:  # Start at the first day of the week (Monday) at 00:00:00
            seconds = 0
            minutes = 0
            hours = 0
            if days > weekday:
                days -= weekday  # this needs to be fixed
            else:
                days += weekday  # this needs to be fixed
        elif has_months:  # Start at the first day of the month at 00:00:00
            seconds = 0
            minutes = 0
            hours = 0
            days = 1
        elif has_years:  # Start at the first day of the first month at 00:00:00
            seconds = 0
            minutes = 0
            hours = 0
            days = 1
            months = 1

        dt = copy.copy(mydate)
        return dt.replace(
            year=years,
            month=months,
            day=days,
            hour=hours,
            minute=minutes,
            second=seconds,
        )


###############################################################################


class datetime_delta(TypedDict):
    """Typed dictionary to return the accumulated delta in year, month, day,
    hour, minute and second as well as max_days. At runtime, it is a plain dict."""

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    max_days: int


def compute_datetime_delta(start: datetime, end: datetime) -> datetime_delta:
    """Return a dictionary with the accumulated delta in year, month, day,
    hour, minute and second

    Usage:

    .. code-block:: pycon

        >>> start = datetime(2001, 1, 1, 0, 0, 0)
        >>> end = datetime(2001, 1, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 0}

        >>> start = datetime(2001, 1, 1, 0, 0, 14)
        >>> end = datetime(2001, 1, 1, 0, 0, 44)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0, 'second': 30, 'max_days': 0}

        >>> start = datetime(2001, 1, 1, 0, 0, 44)
        >>> end = datetime(2001, 1, 1, 0, 1, 14)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 1, 'second': 30, 'max_days': 0}

        >>> start = datetime(2001, 1, 1, 0, 0, 30)
        >>> end = datetime(2001, 1, 1, 0, 5, 30)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 5, 'second': 300, 'max_days': 0}

        >>> start = datetime(2001, 1, 1, 0, 0, 0)
        >>> end = datetime(2001, 1, 1, 0, 1, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 1, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 10, 31, 0, 45, 0)
        >>> end = datetime(2011, 10, 31, 1, 45, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 1, 'minute': 60, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 10, 31, 0, 45, 0)
        >>> end = datetime(2011, 10, 31, 1, 15, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 1, 'minute': 30, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 10, 31, 0, 45, 0)
        >>> end = datetime(2011, 10, 31, 12, 15, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 12, 'minute': 690, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 10, 31, 0, 0, 0)
        >>> end = datetime(2011, 10, 31, 1, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 1, 'minute': 0, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 10, 31, 0, 0, 0)
        >>> end = datetime(2011, 11, 1, 1, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 1, 'hour': 25, 'minute': 0, 'second': 0, 'max_days': 1}

        >>> start = datetime(2011, 10, 31, 12, 0, 0)
        >>> end = datetime(2011, 11, 1, 6, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 18, 'minute': 0, 'second': 0, 'max_days': 0}

        >>> start = datetime(2011, 11, 1, 0, 0, 0)
        >>> end = datetime(2011, 12, 1, 1, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 1, 'day': 0, 'hour': 721, 'minute': 0, 'second': 0, 'max_days': 30}

        >>> start = datetime(2011, 11, 1, 0, 0, 0)
        >>> end = datetime(2011, 11, 5, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 4, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 4}

        >>> start = datetime(2011, 10, 6, 0, 0, 0)
        >>> end = datetime(2011, 11, 5, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 30, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 30}

        >>> start = datetime(2011, 12, 2, 0, 0, 0)
        >>> end = datetime(2012, 1, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 0, 'day': 30, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 30}

        >>> start = datetime(2011, 1, 1, 0, 0, 0)
        >>> end = datetime(2011, 2, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 1, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 31}

        >>> start = datetime(2011, 12, 1, 0, 0, 0)
        >>> end = datetime(2012, 1, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 1, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 31}

        >>> start = datetime(2011, 12, 1, 0, 0, 0)
        >>> end = datetime(2012, 6, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 6, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 183}

        >>> start = datetime(2011, 6, 1, 0, 0, 0)
        >>> end = datetime(2021, 6, 1, 0, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 10, 'month': 120, 'day': 0, 'hour': 0, 'minute': 0, 'second': 0, 'max_days': 3653}

        >>> start = datetime(2011, 6, 1, 0, 0, 0)
        >>> end = datetime(2012, 6, 1, 12, 0, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 12, 'day': 0, 'hour': 8796, 'minute': 0, 'second': 0, 'max_days': 366}

        >>> start = datetime(2011, 6, 1, 0, 0, 0)
        >>> end = datetime(2012, 6, 1, 12, 30, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 12, 'day': 0, 'hour': 8796, 'minute': 527790, 'second': 0, 'max_days': 366}

        >>> start = datetime(2011, 6, 1, 0, 0, 0)
        >>> end = datetime(2012, 6, 1, 12, 0, 5)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 12, 'day': 0, 'hour': 8796, 'minute': 0, 'second': 31665605, 'max_days': 366}

        >>> start = datetime(2011, 6, 1, 0, 0, 0)
        >>> end = datetime(2012, 6, 1, 0, 30, 0)
        >>> compute_datetime_delta(start, end)
        {'year': 1, 'month': 12, 'day': 0, 'hour': 0, 'minute': 527070, 'second': 0, 'max_days': 366}

    :return: A dictionary with year, month, day, hour, minute, second and max_days as keys()
    """  # noqa: E501
    # TODO: set default values here, and ensure processing below covers all situations,
    # not leaking these default values
    comp = datetime_delta(
        year=0,
        month=0,
        day=0,
        hour=0,
        minute=0,
        second=0,
        max_days=(end - start).days,
    )

    day_diff = comp["max_days"]

    # Date
    # Count full years
    comp["year"] = end.year - start.year

    # Count full months
    if start.month == 1 and end.month == 1:
        comp["month"] = 0
    elif start.day == 1 and end.day == 1:
        d = end.month - start.month
        if d < 0:
            d += 12 * comp["year"]
        elif d == 0:
            d = 12 * comp["year"]
        comp["month"] = d

    # Count full days
    comp["day"] = 0 if start.day == 1 and end.day == 1 else day_diff

    # Time
    # Hours
    if start.hour == 0 and end.hour == 0:
        comp["hour"] = 0
    else:
        d = end.hour - start.hour
        if d < 0:
            d += 24 + 24 * day_diff
        else:
            d += 24 * day_diff
        comp["hour"] = d

    # Minutes
    if start.minute == 0 and end.minute == 0:
        comp["minute"] = 0
    else:
        d = end.minute - start.minute
        if d != 0:
            if comp["hour"]:
                d += 60 * comp["hour"]
            else:
                d += 24 * 60 * day_diff
        elif d == 0:
            d = 60 * comp["hour"] if comp["hour"] else 24 * 60 * day_diff

        comp["minute"] = d

    # Seconds
    if start.second == 0 and end.second == 0:
        comp["second"] = 0
    else:
        d = end.second - start.second
        if d != 0:
            if comp["minute"]:
                d += 60 * comp["minute"]
            elif comp["hour"]:
                d += 3600 * comp["hour"]
            else:
                d += 24 * 60 * 60 * day_diff
        elif d == 0:
            if comp["minute"]:
                d = 60 * comp["minute"]
            elif comp["hour"]:
                d = 3600 * comp["hour"]
            else:
                d = 24 * 60 * 60 * day_diff
        comp["second"] = d

    return comp


def check_datetime_string(time_string: str, use_dateutil: bool = True):
    """Check if  a string can be converted into a datetime object and return the object

    In case dateutil is not installed the supported ISO string formats are:

    - YYYY-mm-dd
    - YYYY-mm-dd HH:MM:SS
    - YYYY-mm-ddTHH:MM:SS
    - YYYY-mm-dd HH:MM:SS.s
    - YYYY-mm-ddTHH:MM:SS.s

    Time zones are not supported

    If dateutil is installed, all string formats of the dateutil module
    are supported, as well as time zones
    Time zones are not supported

    :param time_string: The time string to be checked for conversion
    :param use_dateutil: Use dateutil if available for datetime string parsing
    :return: datetime: object or an error message string in case of an error

    .. code-block:: pycon

        >>> s = "2000-01-01"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 0, 0)
        >>> s = "2000-01-01T10:00:00"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 10, 0)
        >>> s = "2000-01-01 10:00:00"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 10, 0)
        >>> s = "2000-01-01T10:00:00.000001"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 10, 0, 0, 1)
        >>> s = "2000-01-01 10:00:00.000001"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 10, 0, 0, 1)

        # using native implementation, ignoring dateutil
        >>> s = "2000-01-01"
        >>> check_datetime_string(s, False)
        datetime.datetime(2000, 1, 1, 0, 0)
        >>> s = "2000-01-01T10:00:00"
        >>> check_datetime_string(s, False)
        datetime.datetime(2000, 1, 1, 10, 0)
        >>> s = "2000-01-01 10:00:00"
        >>> check_datetime_string(s, False)
        datetime.datetime(2000, 1, 1, 10, 0)
        >>> s = "2000-01-01T10:00:00.000001"
        >>> check_datetime_string(s, False)
        datetime.datetime(2000, 1, 1, 10, 0, 0, 1)
        >>> s = "2000-01-01 10:00:00.000001"
        >>> check_datetime_string(s, False)
        datetime.datetime(2000, 1, 1, 10, 0, 0, 1)

    """

    global has_dateutil

    if has_dateutil and use_dateutil is True:
        # First check if there is only a single number, which specifies
        # relative time. dateutil will interpret a single number as a valid
        # time string, so we have to catch this case beforehand
        try:
            int(time_string)
            return _("Time string seems to specify relative time")
        except ValueError:
            pass

        try:
            time_object = parser.parse(time_string)
        except Exception as inst:
            time_object = str(inst)
        return time_object

    # BC is not supported
    if "bc" in time_string:
        return _("Dates Before Christ (BC) are not supported")

    # Time zones are not supported
    if "+" in time_string:
        return _("Time zones are not supported")

    if ":" in time_string or "T" in time_string:
        # Check for microseconds
        if "." in time_string:
            if "T" in time_string:
                time_format = "%Y-%m-%dT%H:%M:%S.%f"
            else:
                time_format = "%Y-%m-%d %H:%M:%S.%f"
        else:  # noqa: PLR5501
            if "T" in time_string:
                time_format = "%Y-%m-%dT%H:%M:%S"
            else:
                time_format = "%Y-%m-%d %H:%M:%S"
    else:
        time_format = "%Y-%m-%d"

    try:
        return datetime.strptime(time_string, time_format)
    except (ValueError, TypeError):
        return _("Unable to parse time string: %s") % time_string


def string_to_datetime(time_string: str) -> datetime | None:
    """Convert a string into a datetime object

    In case datutil is not installed the supported ISO string formats are:

    - YYYY-mm-dd
    - YYYY-mm-dd HH:MM:SS
    - YYYY-mm-ddTHH:MM:SS
    - YYYY-mm-dd HH:MM:SS.s
    - YYYY-mm-ddTHH:MM:SS.s

    Time zones are not supported

    If dateutil is installed, all string formats of the dateutil module
    are supported, as well as time zones

    :param time_string: The time string to convert
    :return: datetime object or None in case the string
             could not be converted
    """

    if not isinstance(time_string, str):
        return None

    time_object = check_datetime_string(time_string)
    if not isinstance(time_object, datetime):
        msgr = get_tgis_message_interface()
        msgr.error(str(time_object))
        return None

    return time_object


def datetime_to_grass_datetime_string(dt: datetime | None) -> str:
    """Convert a python datetime object into a GRASS datetime string

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> import dateutil.parser as parser
        >>> dt = parser.parse("2011-01-01 10:00:00 +01:30")
        >>> tgis.datetime_to_grass_datetime_string(dt)
        '01 jan 2011 10:00:00 +0130'
        >>> dt = parser.parse("2011-01-01 10:00:00 +02:30")
        >>> tgis.datetime_to_grass_datetime_string(dt)
        '01 jan 2011 10:00:00 +0230'
        >>> dt = parser.parse("2011-01-01 10:00:00 +12:00")
        >>> tgis.datetime_to_grass_datetime_string(dt)
        '01 jan 2011 10:00:00 +1200'
        >>> dt = parser.parse("2011-01-01 10:00:00 -01:30")
        >>> tgis.datetime_to_grass_datetime_string(dt)
        '01 jan 2011 10:00:00 -0130'

    """
    # GRASS datetime month names
    month_names = [
        "",
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]

    if dt is None:
        msg = "Empty datetime object in datetime_to_grass_datetime_string"
        raise Exception(msg)

    # Check for time zone info in the datetime object
    if dt.tzinfo is not None:
        # GRASS reads the offset as hours and minutes (+0545 is 5:45), so the
        # minutes of the offset must not be written as one number.
        offset_minutes = int(dt.utcoffset().total_seconds() // 60)
        tz = "%s%02i%02i" % (
            "-" if offset_minutes < 0 else "+",
            abs(offset_minutes) // 60,
            abs(offset_minutes) % 60,
        )

        string = "%.2i %s %.2i %.2i:%.2i:%.2i %s" % (
            dt.day,
            month_names[dt.month],
            dt.year,
            dt.hour,
            dt.minute,
            dt.second,
            tz,
        )
    else:
        string = "%.2i %s %.4i %.2i:%.2i:%.2i" % (
            dt.day,
            month_names[dt.month],
            dt.year,
            dt.hour,
            dt.minute,
            dt.second,
        )

    return string


###############################################################################


def create_suffix_from_datetime(start_time: datetime, granularity: str) -> str:
    """Create a datetime string based on a datetime object and a provided
    granularity that can be used as suffix for map names. The largest
    granularity determines the suffix. E.g.:

    datetime=2001-01-01 00:00:00, granularity="1 month" returns "2001_01"
    datetime=2001-01-01 00:00:00, granularity="1 year 1 month" returns "2001"

    :param start_time: The datetime object
    :param granularity: The granularity for example "1 month" or "100 seconds"
    :return: A string

    .. code-block:: pycon

        >>> from datetime import datetime
        >>> import grass.temporal as tgis
        >>> start_time = datetime(2001, 1, 1, 10, 4, 12)
        >>> tgis.create_suffix_from_datetime(start_time, "1 month")
        '2001_01'
        >>> tgis.create_suffix_from_datetime(start_time, "1 year 1 month")
        '2001'
        >>> tgis.create_suffix_from_datetime(start_time, "6 seconds")
        '2001_01_01_10_04_12'

    """
    suffix_units = {
        "years": "%Y",
        "year": "%Y",
        "months": "%Y_%m",
        "month": "%Y_%m",
        "weeks": "%Y_%m_%d",
        "week": "%Y_%m_%d",
        "days": "%Y_%m_%d",
        "day": "%Y_%m_%d",
        "hours": "%Y_%m_%d_%H",
        "hour": "%Y_%m_%d_%H",
        "minutes": "%Y_%m_%d_%H_%M",
        "minute": "%Y_%m_%d_%H_%M",
        "seconds": "%Y_%m_%d_%H_%M_%S",
        "second": "%Y_%m_%d_%H_%M_%S",
    }

    return start_time.strftime(suffix_units[granularity.split(" ", 2)[1]])


def create_time_suffix(mapp, end: bool = False) -> str:
    """Create a datetime string based on a map datetime object

    :param mapp: a temporal map dataset
    :param end: True if you want add also end time to the suffix
    """
    start = mapp.temporal_extent.get_start_time()
    sstring = start.isoformat().replace(":", "_").replace("-", "_")
    if end:
        end = mapp.temporal_extent.get_end_time()
        estring = end.isoformat().replace(":", "_").replace("-", "_")
        return "{st}_{en}".format(st=sstring, en=estring)
    return sstring


def create_numeric_suffix(base, count: int, zeros: str) -> str:
    """Create a string based on count and number of zeros decided by zeros

    :param base: the basename for new map
    :param count: a number
    :param zeros: a string containing the expected number, coming from suffix option
                  like "%05"
    """
    spli = zeros.split("%")
    if len(spli) == 2:
        suff = spli[1]
        if suff.isdigit():
            zero = suff if int(suff[0]) == 0 else "0{nu}".format(nu=suff)
        else:
            zero = "05"
    else:
        zero = "05"
    s = "{ba}_{i:" + zero + "d}"
    return s.format(ba=base, i=count)


def check_suffix(suffix: str) -> None:
    """Refuse a value of the suffix option other than gran, time, num or num%NN

    The tools used to take any other text as num, so that a typing error such
    as "gram" silently gave numbered maps instead of dated ones.

    :param suffix: The value of the suffix option
    :raises ValueError: for any other value
    """
    if suffix in {"gran", "time", "num"} or re.fullmatch(r"num%\d+", suffix):
        return
    msg = _("Invalid suffix <{}>, use gran, time, num or num%NN").format(suffix)
    raise ValueError(msg)


def map_name_suffix(map, suffix: str, granularity: str | None, number: int) -> str:
    """Return the part of a new map name after the basename and an underscore

    gran cuts the start time of map to the largest unit of granularity, time
    takes the full start time, num and num%NN the number with five or NN
    digits. In relative time every suffix gives the number, because a
    relative time stamp has no calendar date. A dataset of a single time
    instant has no granularity; gran then gives the full start time like
    time, because there is no unit to cut it to and the full time is unique.

    :param map: The map whose start time names the new map; its temporal type
                must be set (selected from the temporal database or set with
                set_absolute_time() or set_relative_time())
    :param suffix: The value of the suffix option
    :param granularity: The granularity for gran, None if there is none
    :param number: The number for num and for relative time
    :raises ValueError: for a suffix that check_suffix() refuses
    """
    check_suffix(suffix)
    if suffix in {"gran", "time"} and map.is_time_absolute():
        if suffix == "gran" and granularity is not None:
            return create_suffix_from_datetime(
                map.temporal_extent.get_start_time(), granularity
            )
        return create_time_suffix(map)
    # The name with an empty basename starts with the underscore.
    return create_numeric_suffix("", number, suffix)[1:]


if __name__ == "__main__":
    import doctest

    doctest.testmod()
