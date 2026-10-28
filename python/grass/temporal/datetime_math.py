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

from .state import get_tgis_message_interface

try:
    from dateutil import parser

    has_dateutil = True
except (ImportError, ModuleNotFoundError):
    has_dateutil = False


DAY_IN_SECONDS = 86400
SECOND_AS_DAY = 1.1574074074074073e-05


def time_delta_to_relative_time(delta: timedelta) -> float:
    """Convert the time delta into a double value, representing days."""
    return float(delta.days) + float(delta.seconds * SECOND_AS_DAY)


def time_delta_to_relative_time_seconds(delta: timedelta) -> float:
    """Convert the time delta into a double value, representing seconds."""

    return float(delta.days * DAY_IN_SECONDS) + float(delta.seconds)


# The units of an increment or a granularity from the finest to the coarsest
_GRANULARITY_UNITS = ("second", "minute", "hour", "day", "week", "month", "year")


def _unit_of(word: str) -> str | None:
    """Return the first unit of _GRANULARITY_UNITS that the word contains

    So "days" names a day and "minutesecond" a second; None if there is none.
    """
    return next((name for name in _GRANULARITY_UNITS if name in word), None)


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
         >>> string = "1 month"
         >>> decrement_datetime_by_string(dt, string)
         datetime.datetime(2000, 12, 1, 0, 0)

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

        >>> dt = datetime(2001, 11, 1, 0, 0, 0)
        >>> string = "1 months"
        >>> increment_datetime_by_string(dt, string)
        datetime.datetime(2001, 12, 1, 0, 0)

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

    if not increment:
        return mydate

    steps = dict.fromkeys(_GRANULARITY_UNITS, 0)
    for part in increment.split(","):
        inc = part.strip().split(" ")
        unit = _unit_of(inc[1]) if len(inc) >= 2 else None
        if unit is None:
            msgr = get_tgis_message_interface()
            msgr.error(_("Wrong increment format: %s") % (increment))
            return None
        # A unit that appears twice keeps its last number.
        steps[unit] = sign * mult * int(inc[0])

    return modify_datetime(mydate, **{f"{unit}s": step for unit, step in steps.items()})


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

        >>> modify_datetime(datetime(2003, 3, 31), months=23)
        datetime.datetime(2005, 2, 28, 0, 0)
        >>> modify_datetime(datetime(2003, 3, 31), years=1, months=11)
        datetime.datetime(2005, 2, 28, 0, 0)

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


# The fields that restart when the finest unit of a granularity is given
_START_VALUES = {
    "second": {},
    "minute": {"second": 0},
    "hour": {"second": 0, "minute": 0},
    "day": {"second": 0, "minute": 0, "hour": 0},
    "week": {"second": 0, "minute": 0, "hour": 0},
    "month": {"second": 0, "minute": 0, "hour": 0, "day": 1},
    "year": {"second": 0, "minute": 0, "hour": 0, "day": 1, "month": 1},
}


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
        >>> adjust_datetime_to_granularity(dt, "6 months")
        datetime.datetime(2001, 8, 1, 0, 0)

    """

    if not granularity:
        return None

    # Split the granularity string; the finest unit in it decides where the
    # adjusted time starts.
    granlist = [granpart.strip().split(" ") for granpart in granularity.split(",")]
    units = set()
    for inc in granlist:
        unit = _unit_of(inc[1])
        if unit is None:
            msgr = get_tgis_message_interface()
            msgr.error(_("Wrong granularity format: %s") % (granularity))
            return None
        units.add(unit)
    finest = next(name for name in _GRANULARITY_UNITS if name in units)

    fields = {
        "year": mydate.year,
        "month": mydate.month,
        "day": mydate.day,
        "hour": mydate.hour,
        "minute": mydate.minute,
        "second": mydate.second,
    }
    # Everything below the finest unit starts at its first value.
    fields.update(_START_VALUES[finest])
    if finest == "week":
        # Start at the first day of the week (Monday) at 00:00:00
        weekday = mydate.weekday()
        if fields["day"] > weekday:
            fields["day"] -= weekday  # this needs to be fixed
        else:
            fields["day"] += weekday  # this needs to be fixed

    return copy.copy(mydate).replace(**fields)


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

        >>> start = datetime(2001, 1, 1, 0, 0, 14)
        >>> end = datetime(2001, 1, 1, 0, 0, 44)
        >>> compute_datetime_delta(start, end)
        {'year': 0, 'month': 0, 'day': 0, 'hour': 0, 'minute': 0, 'second': 30, 'max_days': 0}

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

    # Time. Each unit counts the whole interval in that unit, from the next
    # coarser unit that is not zero: the difference of the field plus all of
    # the interval before it.
    # Hours
    if start.hour == 0 and end.hour == 0:
        comp["hour"] = 0
    else:
        d = end.hour - start.hour
        comp["hour"] = d + 24 + 24 * day_diff if d < 0 else d + 24 * day_diff

    # Minutes
    if start.minute == 0 and end.minute == 0:
        comp["minute"] = 0
    else:
        before = 60 * comp["hour"] if comp["hour"] else 24 * 60 * day_diff
        comp["minute"] = end.minute - start.minute + before

    # Seconds
    if start.second == 0 and end.second == 0:
        comp["second"] = 0
    else:
        if comp["minute"]:
            before = 60 * comp["minute"]
        elif comp["hour"]:
            before = 3600 * comp["hour"]
        else:
            before = 24 * 60 * 60 * day_diff
        comp["second"] = end.second - start.second + before

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

        >>> s = "2000-01-01T10:00:00"
        >>> check_datetime_string(s)
        datetime.datetime(2000, 1, 1, 10, 0)

    """

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
        except (ValueError, OverflowError) as inst:
            # The parser reports a text it cannot read as a ParserError, a
            # ValueError, and a number out of range as an OverflowError.
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


def option_to_datetime(text: str, option: str) -> datetime:
    """Convert the value of a tool option to a datetime

    For text that string_to_datetime() cannot read, string_to_datetime()
    reports its own message first.

    :param text: The value of the option
    :param option: The name of the option, for the message
    :return: The datetime
    :raises ValueError: "Invalid date <text> of the option <option>" for
                        text that string_to_datetime() cannot read
    """
    # Without a message interface (no init()) string_to_datetime() ends in
    # an AttributeError for text it cannot read instead of returning None.
    try:
        converted = string_to_datetime(text)
    except (AttributeError, ValueError):
        converted = None
    if converted is None:
        raise ValueError(_("Invalid date <{}> of the option <{}>").format(text, option))
    return converted


def datetime_to_grass_datetime_string(dt: datetime | None) -> str:
    """Convert a python datetime object into a GRASS datetime string

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> import dateutil.parser as parser
        >>> dt = parser.parse("2011-01-01 10:00:00 +01:30")
        >>> tgis.datetime_to_grass_datetime_string(dt)
        '01 jan 2011 10:00:00 +0130'

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
        sign = "-" if offset_minutes < 0 else "+"
        tz = f"{sign}{abs(offset_minutes) // 60:02d}{abs(offset_minutes) % 60:02d}"

        string = (
            f"{dt.day:02d} {month_names[dt.month]} {dt.year:02d} "
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d} {tz}"
        )
    else:
        string = (
            f"{dt.day:02d} {month_names[dt.month]} {dt.year:04d} "
            f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
        )

    return string


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
        >>> tgis.datetime_math.create_suffix_from_datetime(start_time, "1 month")
        '2001_01'

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
        return f"{sstring}_{estring}"
    return sstring


def create_numeric_suffix(base, count: int, zeros: str) -> str:
    """Create a string based on count and number of zeros decided by zeros

    :param base: the basename for new map
    :param count: a number
    :param zeros: a string containing the expected number, coming from suffix option
                  like "%05"
    """
    spli = zeros.split("%")
    suff = spli[1] if len(spli) == 2 else ""
    zero = "05"
    if suff.isdigit():
        zero = suff if int(suff[0]) == 0 else f"0{suff}"
    s = "{ba}_{i:" + zero + "d}"
    return s.format(ba=base, i=count)


def _months_of_step(step: str) -> int | None:
    """Return the length of a month or year step in months, None for other units"""
    number, unit = step.split()
    factor = {"month": 1, "year": 12}.get(unit.rstrip("s"))
    return None if factor is None else factor * int(number)


def next_cycle(
    origin: datetime | float,
    number: int,
    end: datetime | float,
    cycle: str | float,
    offset: str | float | None,
    absolute: bool,
) -> tuple[datetime | float, datetime | float]:
    """Return the start and end of cycle number, which follows the one ending at end

    The first cycle, number 0, starts at origin. A cycle without maps is
    skipped through the same call, so that the loop advances however a cycle
    ends.

    Month and year steps count from origin, so that a cut at the end of a
    short month does not carry over: monthly cycles from January 31 start on
    February 28 and March 31, not on February 28 and March 28. A cycle and an
    offset of different kinds, such as a month and a day, do not add up to
    one step that could be counted from origin; they count from end.

    :param origin: The start of the first cycle
    :param number: The number of the cycle to return
    :param end: The end of the previous cycle
    :param cycle: The length of a cycle, a granularity string in absolute
                  time, a number in relative time
    :param offset: The gap between a cycle and the next, same kind as cycle,
                   None for no gap (absolute time only)
    :param absolute: True for absolute time, False for relative time
    :return: The tuple (start, end) of the cycle
    """
    if not absolute:
        start = end + offset
        return start, start + cycle
    months = (_months_of_step(cycle), _months_of_step(offset) if offset else 0)
    if None not in months:
        period = number * (months[0] + months[1])
        return (
            modify_datetime(origin, months=period),
            modify_datetime(origin, months=period + months[0]),
        )
    start = increment_datetime_by_string(end, offset) if offset else end
    return start, increment_datetime_by_string(start, cycle)


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
