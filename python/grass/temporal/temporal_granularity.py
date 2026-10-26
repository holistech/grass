"""
Functions to compute the temporal granularity of a map list

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.compute_relative_time_granularity(maps)


SPDX-FileCopyrightText: 2012-2024 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import ast
from collections import OrderedDict
from functools import reduce

from .abstract_map_dataset import AbstractMapDataset
from .datetime_math import compute_datetime_delta

SINGULAR_GRAN = ["second", "minute", "hour", "day", "week", "month", "year"]
PLURAL_GRAN = ["seconds", "minutes", "hours", "days", "weeks", "months", "years"]
SUPPORTED_GRAN = SINGULAR_GRAN + PLURAL_GRAN
CONVERT_GRAN = OrderedDict()
CONVERT_GRAN["year"] = "12 month"
CONVERT_GRAN["month"] = "30.436875 day"
CONVERT_GRAN["day"] = "24 hour"
CONVERT_GRAN["hour"] = "60 minute"
CONVERT_GRAN["minute"] = "60 second"

# The units a granularity is computed in, from the smallest to the largest.
# Weeks are valid in a granularity string but not in a computation: a week is
# neither a unit the algebra counts in nor does the result use it.
_UNITS = ("second", "minute", "hour", "day", "month", "year")

# Seconds in the units of a fixed length
_SECONDS_PER_UNIT = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}

# A month and a year have no fixed number of days. A granule that holds for a
# month or a year must hold for each length, so each one is a value of its own.
_DAYS_PER_UNIT = {"month": (28, 29, 30, 31), "year": (365, 366)}

_MONTHS_PER_YEAR = 12

# How many units of a smaller kind make the next larger one, as the common
# granule of start dates may reach: seconds in a minute, minutes in an hour,
# hours in a day, days in a year, months in a year.
_HIERARCHY_LIMIT = {"second": 60, "minute": 60, "hour": 24, "day": 365, "month": 12}


def _singular_unit(unit):
    """Return the unit of a granularity string without the plural s"""
    return unit.removesuffix("s")


def _unit_factor(base_unit, unit):
    """Return how many base units are in a unit of the datetime delta, or None

    The units of a datetime delta are the _UNITS and max_days, the number of
    days of the whole delta. Only units of a fixed length can be counted in a
    smaller one, and the year in months.
    """
    unit = "day" if unit == "max_days" else unit
    if base_unit in _SECONDS_PER_UNIT and unit in _SECONDS_PER_UNIT:
        if _SECONDS_PER_UNIT[unit] >= _SECONDS_PER_UNIT[base_unit]:
            return _SECONDS_PER_UNIT[unit] // _SECONDS_PER_UNIT[base_unit]
    elif base_unit == "month" and unit == "year":
        return _MONTHS_PER_YEAR
    return None


def _add_delta(granularity_units, delta):
    """Add the value of a datetime delta to the set of its smallest unit

    The keys of granularity_units are in the order of increasing length, so the
    first unit with a value above zero is the smallest one. The days of the
    whole delta, max_days, are added besides the unit.
    """
    for time_unit, values in granularity_units.items():
        if time_unit in delta and delta[time_unit] > 0:
            values.add(delta[time_unit])
            if time_unit != "max_days":
                break


def _gcd_in_unit(units, base_unit):
    """Return the greatest common divisor of the counts in the base unit

    The counts of the base unit are used as they are. Of each larger unit that
    is present the smallest count is converted into the base unit, because a
    larger count of the same unit is a multiple of it and changes nothing.

    :param units: A dictionary of the units that are present with the list of
                  their counts
    :param base_unit: The smallest unit that is present, one of _UNITS
    :return: The greatest common divisor in the base unit
    """
    values = list(units[base_unit])
    for unit in _UNITS[_UNITS.index(base_unit) + 1 :]:
        if unit not in units:
            continue
        smallest = min(units[unit])
        if base_unit in _SECONDS_PER_UNIT:
            per_unit = _SECONDS_PER_UNIT[base_unit]
            if unit in _SECONDS_PER_UNIT:
                values.append(smallest * (_SECONDS_PER_UNIT[unit] // per_unit))
            else:
                values.extend(
                    smallest * days * (_SECONDS_PER_UNIT["day"] // per_unit)
                    for days in _DAYS_PER_UNIT[unit]
                )
        else:
            # The base unit is the month, the only larger one is the year.
            values.append(smallest * _MONTHS_PER_YEAR)
    return gcd_list(values)


###############################################################################


def check_granularity_string(granularity, temporal_type) -> bool:
    """Check if the granularity string is valid

    :param granularity: The granularity string
    :param temporal_type: The temporal type of the granularity relative or
                          absolute
    :return: True if valid, False if invalid

    .. code-block:: pycon

        >>> check_granularity_string("1 year", "absolute")
        True
        >>> check_granularity_string("1 month", "absolute")
        True
        >>> check_granularity_string("1 day", "absolute")
        True
        >>> check_granularity_string("1 minute", "absolute")
        True
        >>> check_granularity_string("1 hour", "absolute")
        True
        >>> check_granularity_string("1 second", "absolute")
        True
        >>> check_granularity_string("5 months", "absolute")
        True
        >>> check_granularity_string("5 days", "absolute")
        True
        >>> check_granularity_string("5 minutes", "absolute")
        True
        >>> check_granularity_string("5 years", "absolute")
        True
        >>> check_granularity_string("5 hours", "absolute")
        True
        >>> check_granularity_string("2 seconds", "absolute")
        True
        >>> check_granularity_string("1 secondo", "absolute")
        False
        >>> check_granularity_string("bla second", "absolute")
        False
        >>> check_granularity_string("bla", "absolute")
        False
        >>> check_granularity_string(1, "relative")
        True
        >>> check_granularity_string("bla", "relative")
        False

    """

    if granularity is None:
        return False

    if temporal_type == "absolute":
        try:
            num, unit = granularity.split(" ")
        except (ValueError, AttributeError):
            return False
        if unit not in SUPPORTED_GRAN:
            return False

        try:
            int(num)
        except ValueError:
            return False
    elif temporal_type == "relative":
        try:
            int(granularity)
        except ValueError:
            return False
    else:
        return False

    return True


###############################################################################


def get_time_tuple_function(maps):
    """Helper function to return the appropriate function to get
        time tuple from either TGIS DB rows or AbstractDataset object

    :param maps: a list of AbstractDataset objects or database rows
    :return: A function

    .. code-block:: pycon

        >>> from grass.temporal.space_time_datasets import RasterDataset
        >>> maps = [RasterDataset("a@PERMANENT")]
        >>> get_time_tuple_function(maps).__name__
        '_get_map_time_tuple'
        >>> get_time_tuple_function([{"start_time": 1, "end_time": 2}]).__name__
        '_get_row_time_tuple'

    """

    def _get_map_time_tuple(map_object):
        """Sub-function to return time tuple
        from AbstractDataset object"""
        if map_object.is_time_absolute():
            time_tuple = map_object.get_absolute_time()
        if map_object.is_time_relative():
            time_tuple = map_object.get_relative_time()
        return time_tuple[0:2]

    def _get_row_time_tuple(db_table_row):
        """Sub-function to return time tuple
        from database row"""
        return db_table_row["start_time"], db_table_row["end_time"]

    # Check if input is list of MapDataset objects or SQLite rows
    if issubclass(maps[0].__class__, AbstractMapDataset):
        return _get_map_time_tuple
    return _get_row_time_tuple


def _is_after(start, start1, end1) -> bool:
    """Helper function that checks if start timestamp is
    temporally after the start1 and end1, where start1 and end1
    represent a temporal extent.

    :param start: datetime object to check if it is after start1 and end1
    :param start1: datetime object for comparison
    :param end1: datetime object (>= start1) or None for comparison
    :return: bool

    .. code-block:: pycon

        >>> from datetime import datetime
        >>> start = datetime(2024, 1, 1)
        >>> start1 = datetime(2023, 12, 12)
        >>> end1 = None
        >>> _is_after(start, start1, end1)
        True

        >>> start = datetime(2023, 12, 14)
        >>> start1 = datetime(2023, 12, 12)
        >>> end1 = datetime(2023, 12, 24)
        >>> _is_after(start, start1, end1)
        False

    """
    if end1 is None:
        return start > start1

    return start > end1


def compute_relative_time_granularity(maps):
    """Compute the relative time granularity

    Attention: The computation of the granularity
    is only correct in case of not overlapping intervals.
    Hence a correct temporal topology is required for computation.

    :param maps: a ordered by start_time list of map objects
    :return: An integer


    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> maps = []
        >>> for i in range(5):
        ...     map = tgis.RasterDataset("a%i@P" % i)
        ...     check = map.set_relative_time(i, i + 1, "seconds")
        ...     if check:
        ...         maps.append(map)
        >>> tgis.compute_relative_time_granularity(maps)
        1

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, 3), (3, 6), (6, 9))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "years")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        3

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, 3), (4, 6), (8, 11))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "years")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        1

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, 8), (2, 6), (5, 9))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "months")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        4

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, 8), (8, 12), (12, 18))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "days")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        2

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, None), (8, None), (12, None), (24, None))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "minutes")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        4

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, None), (8, 14), (18, None), (24, None))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "hours")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        2

        >>> maps = []
        >>> count = 0
        >>> timelist = ((0, 21),)
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_relative_time(t[0], t[1], "hours")
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_relative_time_granularity(maps)
        21

    """

    if not maps:
        return None

    get_time_tuple = get_time_tuple_function(maps)

    # The interval time must be scaled to days resolution
    granularity = None
    delta = set()
    previous_start, previous_end = get_time_tuple(maps[0])
    # First we compute the timedelta of the intervals
    for stds_map in maps:
        start, end = get_time_tuple(stds_map)
        if (start == 0 or start) and end:
            t = abs(end - start)
            delta.add(int(t))

        # Compute the timedelta of the gaps
        if _is_after(start, previous_start, previous_end):
            # Gaps are between intervals, intervals and
            # points, points and points
            # start time is required in TGIS and expected to be present
            if previous_end:
                # Gap between previous end and current start
                t = abs(start - previous_end)
                delta.add(int(t))
            else:
                # Gap between previous start and current start
                t = abs(start - previous_start)
                delta.add(int(t))
        previous_start, previous_end = start, end

    if len(delta) > 1:
        # Find greatest common divisor
        granularity = gcd_list(delta)
    elif len(delta) == 1:
        granularity = delta.pop()
    else:
        granularity = 0

    return granularity


###############################################################################


def compute_absolute_time_granularity(maps):
    """Compute the absolute time granularity

    Attention: The computation of the granularity
    is only correct in case of not overlapping intervals.
    Hence a correct temporal topology is required for computation.

    The computed granularity is returned as number of seconds or minutes
    or hours or days or months or years.

    :param maps: a ordered by start_time list of map objects or database rows
    :return: The temporal topology as string "integer unit"

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> import datetime
        >>> dt = datetime.datetime
        >>> tgis.init()
        >>> maps = []
        >>> count = 0
        >>> timelist = ((dt(2000, 1, 1), None), (dt(2000, 2, 1), None))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_absolute_time(t[0], t[1])
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_absolute_time_granularity(maps)
        '1 month'

        >>> maps = []
        >>> count = 0
        >>> timelist = (
        ...     (dt(2000, 1, 1), None),
        ...     (dt(2000, 1, 2), None),
        ...     (dt(2000, 1, 3), None),
        ... )
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_absolute_time(t[0], t[1])
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_absolute_time_granularity(maps)
        '1 day'

        >>> maps = []
        >>> count = 0
        >>> timelist = (
        ...     (dt(2000, 1, 1), None),
        ...     (dt(2000, 1, 2), None),
        ...     (dt(2000, 5, 4, 0, 5, 30), None),
        ... )
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_absolute_time(t[0], t[1])
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_absolute_time_granularity(maps)
        '30 seconds'

        >>> maps = []
        >>> count = 0
        >>> timelist = ((dt(2000, 1, 1), dt(2000, 5, 2)), (dt(2000, 5, 4, 2), None))
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_absolute_time(t[0], t[1])
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_absolute_time_granularity(maps)
        '2 hours'

        >>> maps = []
        >>> count = 0
        >>> timelist = (
        ...     (dt(2000, 1, 1), dt(2000, 2, 1)),
        ...     (dt(2005, 5, 4, 12), dt(2007, 5, 20, 6)),
        ... )
        >>> for t in timelist:
        ...     map = tgis.RasterDataset("a%i@P" % count)
        ...     check = map.set_absolute_time(t[0], t[1])
        ...     if check:
        ...         maps.append(map)
        ...     count += 1
        >>> tgis.compute_absolute_time_granularity(maps)
        '6 hours'

    """

    # Create a granularity dict with time units of increasing length
    # that covers all possible keys in the result of compute_datetime_delta
    # The order of the keys is important so that loops over the dictionary
    # can be aborted as soon as a non-zero value is encountered
    granularity_units = {
        "second": set(),
        "minute": set(),
        "hour": set(),
        "max_days": set(),
        "day": set(),
        "month": set(),
        "year": set(),
    }

    get_time_tuple = get_time_tuple_function(maps)

    previous_start, previous_end = get_time_tuple(maps[0])

    # First we compute the timedelta of the intervals
    for stds_map in maps:
        start, end = get_time_tuple(stds_map)
        # start time is required in TGIS and expected to be present
        if end:
            _add_delta(granularity_units, compute_datetime_delta(start, end))
        # Compute the timedelta of the gaps
        if _is_after(start, previous_start, previous_end):
            # Gaps are between intervals, intervals and
            # points, points and points
            # start time is required in TGIS and expected to be present
            if previous_end:
                gap_datetime_delta = compute_datetime_delta(previous_end, start)
            else:
                gap_datetime_delta = compute_datetime_delta(previous_start, start)
            _add_delta(granularity_units, gap_datetime_delta)
        # Keep the temporal extent to compare to the following/next map
        previous_start, previous_end = start, end

    # Create a set with a single time unit only
    dlist = set()
    assigned_time_unit = None

    for time_unit, granularity_set in granularity_units.items():
        # The smallest granularity unit is used so as soon as a non-zero
        # value / set is encountered, the loop can be aborted
        if granularity_set:
            # Skip max_days
            if time_unit == "max_days":
                continue
            assigned_time_unit = time_unit
            break

    if assigned_time_unit is None:
        return None

    dlist.update(granularity_units[assigned_time_unit])
    for unit, values in granularity_units.items():
        unit_factor = _unit_factor(assigned_time_unit, unit)
        if unit != assigned_time_unit and unit_factor and values:
            dlist.update({time_value * unit_factor for time_value in values})

    if not dlist:
        return None

    # Find greatest common divisor to get a single time unit
    granularity = gcd_list(dlist) if len(dlist) > 1 else dlist.pop()

    if granularity is None:
        return None

    plural = ""
    if granularity > 1:
        plural = "s"

    return f"{granularity} {assigned_time_unit}{plural}"


###############################################################################


def compute_common_relative_time_granularity(gran_list):
    """Compute the greatest common granule from a list of relative time granules

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = [1, 2, 30]
        >>> tgis.temporal_granularity.compute_common_relative_time_granularity(grans)
        1

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = [10, 20, 30]
        >>> tgis.temporal_granularity.compute_common_relative_time_granularity(grans)
        10
    """
    return gcd_list(gran_list)


###############################################################################


def compute_common_absolute_time_granularity(gran_list, start_date_list=None):
    """Compute the greatest common granule from a list of absolute time granules,
    considering the start times of the related space time datasets in the
    common granularity computation.

    The list of start dates is optional. If you use this function to compute a common
    granularity between space time datasets, then you should provide their start times
    to avoid wrong synchronization.

    :param gran_list: List of granularities
    :param start_date_list: List of the start times of related space time datasets
    :return: The common granularity, None for an empty list of granules and
             False if a granule is invalid

    .. code-block:: pycon

        >>> from datetime import datetime
        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = ["20 second", "10 minutes", "2 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '20 seconds'

        >>> grans = ["20 second", "10 minutes", "2 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 20),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 second'

        >>> grans = ["7200 second", "240 minutes", "1 year"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 10),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 second'

        >>> grans = ["7200 second", "89 minutes", "1 year"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '60 seconds'

        >>> grans = ["120 minutes", "2 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '60 minutes'

        >>> grans = ["120 minutes", "2 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 30, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 minute'

        >>> grans = ["360 minutes", "3 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '60 minutes'

        >>> grans = ["2 hours", "4 hours", "8 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '2 hours'

        >>> grans = ["2 hours", "4 hours", "8 hours"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 2, 0, 0),
        ...     datetime(2001, 1, 1, 4, 0, 0),
        ...     datetime(2001, 1, 1, 8, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 hour'

        >>> grans = ["8 hours", "2 days"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '8 hours'

        >>> grans = ["8 hours", "2 days"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 10, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 hour'

        >>> grans = ["120 months", "360 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '12 months'

        >>> grans = ["30 days", "10 days", "5 days"]
        >>> dates = [
        ...     datetime(2001, 2, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '5 days'

        >>> grans = ["30 days", "10 days", "5 days"]
        >>> dates = [
        ...     datetime(2001, 2, 2, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 day'

        >>> grans = ["2 days", "360 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '2 days'

        >>> grans = ["2 days", "360 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 1, 2, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 day'

        >>> grans = ["120 months", "360 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 2, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 month'

        >>> grans = ["120 months", "361 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '1 month'

        >>> grans = ["120 months", "360 months", "4 years"]
        >>> dates = [
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ...     datetime(2001, 1, 1, 0, 0, 0),
        ... ]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(
        ...     grans, dates
        ... )
        '12 months'

    ..

    """

    common_granule = compute_common_absolute_time_granularity_simple(gran_list)

    if not common_granule or start_date_list is None:
        return common_granule

    num, granule = common_granule.split()
    unit = _singular_unit(granule)

    if unit in _HIERARCHY_LIMIT:
        limit = _HIERARCHY_LIMIT[unit]
        # If the start dates differ in the field of the unit, the granule
        # cannot be longer than one unit
        for start_time in start_date_list:
            if getattr(start_time, unit) != getattr(start_date_list[0], unit):
                return f"1 {unit}"
        # Make sure the granule does not exceed the hierarchy limit
        if int(num) > limit:
            if int(num) % limit == 0:
                return f"{limit} {unit}s"
            return f"1 {unit}"

    return common_granule


###############################################################################


def compute_common_absolute_time_granularity_simple(gran_list):
    """Compute the greatest common granule from a list of absolute time granules

    :param gran_list: List of granularities
    :return: The common granularity

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = ["1 second", "2 seconds", "30 seconds"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '1 second'

        >>> grans = ["3 second", "6 seconds", "30 seconds"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '3 seconds'

        >>> grans = ["12 second", "18 seconds", "30 seconds", "10 minutes"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '6 seconds'

        >>> grans = ["20 second", "10 minutes", "2 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '20 seconds'

        >>> grans = ["7200 second", "240 minutes", "1 year"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '7200 seconds'

        >>> grans = ["7200 second", "89 minutes", "1 year"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '60 seconds'

        >>> grans = ["10 minutes", "20 minutes", "30 minutes", "40 minutes", "2 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '10 minutes'

        >>> grans = ["120 minutes", "2 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '120 minutes'

        >>> grans = ["360 minutes", "3 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '180 minutes'

        >>> grans = ["2 hours", "4 hours", "8 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '2 hours'

        >>> grans = ["8 hours", "2 days"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '8 hours'

        >>> grans = ["48 hours", "1 month"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '24 hours'

        >>> grans = ["48 hours", "1 year"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '24 hours'

        >>> grans = ["2 months", "4 months", "1 year"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '2 months'

        >>> grans = ["120 months", "360 months", "4 years"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '24 months'

        >>> grans = ["120 months", "361 months", "4 years"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '1 month'

        >>> grans = ["2 years", "3 years", "4 years"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity(grans)
        '1 year'
    """

    units = {}
    for entry in gran_list:
        if not check_granularity_string(entry, "absolute"):
            return False

        num, gran = entry.split()
        unit = _singular_unit(gran)
        if unit in _UNITS:
            units.setdefault(unit, []).append(int(num))

    for unit in _UNITS:
        if unit in units:
            num = _gcd_in_unit(units, unit)
            return f"{num} {unit}{'s' if num > 1 else ''}"

    return None


#######################################################################


def gran_singular_unit(gran):
    """Return the absolute granularity unit in its singular term

    :param gran: input granularity
    :return: granularity unit

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> tgis.gran_singular_unit("1 month")
        'month'

        >>> tgis.gran_singular_unit("2 months")
        'month'

        >>> tgis.gran_singular_unit("6 seconds")
        'second'

        >>> tgis.gran_singular_unit("1 year")
        'year'
    """
    if check_granularity_string(gran, "absolute"):
        output, unit = gran.split(" ")
        if unit in PLURAL_GRAN:
            return unit[:-1]
        if unit in SINGULAR_GRAN:
            return unit
        lists = f"{SUPPORTED_GRAN}".replace("[", "").replace("]", "")
        print(
            _(
                "Output granularity seems not to be valid. Please use "
                "one of the following values : {gr}"
            ).format(gr=lists)
        )
        return False
    print(_("Invalid absolute granularity"))
    return False


#######################################################################


########################################################################


def gran_to_gran(from_gran, to_gran="days", shell: bool = False):
    """Converts the computed absolute granularity of a STDS to a smaller
    granularity based on the Gregorian calendar hierarchy that 1 year
    equals 12 months or 365.2425 days or 24 * 365.2425 hours or 86400 *
    365.2425 seconds.

    :param from_gran: input granularity, this should be bigger than to_gran
    :param to_gran: output granularity
    :return: The output granularity

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> tgis.gran_to_gran("1 month", "1 day")
        '30.436875 days'

        >>> tgis.gran_to_gran("1 month", "1 day", True)
        30.436875

        >>> tgis.gran_to_gran("10 year", "1 hour")
        '87658.20000000001 hours'

        >>> tgis.gran_to_gran("10 year", "1 minute")
        '5259492.000000001 minutes'

        >>> tgis.gran_to_gran("6 months", "1 day")
        '182.62125 days'

        >>> tgis.gran_to_gran("1 months", "1 second")
        '2629746.0 seconds'

        >>> tgis.gran_to_gran("1 month", "1 second", True)
        2629746.0

        >>> tgis.gran_to_gran("30 month", "1 month", True)
        30
    """

    def _return(output, tounit, shell):
        """Function to return the output"""
        if shell:
            return output

        if output == 1:
            return f"{output} {tounit}"
        return f"{output} {tounit}s"

    # TODO check the leap second
    if check_granularity_string(from_gran, "absolute"):
        output, unit = from_gran.split(" ")
        if unit in PLURAL_GRAN:
            unit = unit[:-1]
        myunit = unit
        tounit = gran_singular_unit(to_gran)

        output = ast.literal_eval(output)
        for k, v in CONVERT_GRAN.items():
            if myunit == tounit:
                return _return(output, tounit, shell)
            if k == myunit:
                num, myunit = v.split(" ")
                output *= ast.literal_eval(num)
            if tounit == "second" and myunit == tounit:
                return _return(output, tounit, shell)
        print(_("Probably you need to invert 'from_gran' and 'to_gran'"))
        return False
    print(_("Invalid absolute granularity"))
    return False


###############################################################################
# http://akiscode.com/articles/gcd_of_a_list.shtml
# Copyright (c) 2010 Stephen Akiki
# MIT License (Means you can do whatever you want with this)
#  See http://www.opensource.org/licenses/mit-license.php
# Error Codes:
#   None


def gcd(a, b):
    """The Euclidean Algorithm"""
    a = abs(a)
    b = abs(b)
    while a:
        a, b = b % a, a
    return b


###############################################################################


def gcd_list(list):
    """Finds the GCD of numbers in a list.

    :param list: List of numbers you want to find the GCD of
                 E.g. [8, 24, 12]
    :return: GCD of all numbers

    """
    return reduce(gcd, list)


###############################################################################

if __name__ == "__main__":
    import doctest

    doctest.testmod()
