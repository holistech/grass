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


def check_granularity_string(granularity, temporal_type) -> bool:
    """Check if the granularity string is valid

    :param granularity: The granularity string
    :param temporal_type: The temporal type of the granularity relative or
                          absolute
    :return: True if valid, False if invalid

    .. code-block:: pycon

        >>> check_granularity_string("1 year", "absolute")
        True

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

    """
    if end1 is None:
        return start > start1

    return start > end1


def _intervals_and_gaps(maps, is_interval):
    """Yield the (start, end) of every interval and every gap of a map list

    A gap lies between a map and the next one that starts after it. It begins
    at the end of the earlier map, or at its start if that end is false (None,
    or 0 in relative time).

    A map without a start time is left out. The reading of a dataset leaves a
    map so when it refuses the stored times, for example an end before the
    start, and names the map; the time it would have covered is unknown, so
    a gap reaches from the map before it to the map after it.

    :param maps: A list of map objects or database rows, ordered by start time
    :param is_interval: A function of start and end that tells whether a map
                        is an interval; the temporal types differ in it
    """
    get_time_tuple = get_time_tuple_function(maps)
    times = [
        (start, end) for start, end in map(get_time_tuple, maps) if start is not None
    ]
    if not times:
        return
    previous_start, previous_end = times[0]
    for start, end in times:
        if is_interval(start, end):
            yield start, end
        if _is_after(start, previous_start, previous_end):
            yield previous_end or previous_start, start
        previous_start, previous_end = start, end


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

    """

    if not maps:
        return None

    # A start of 0 counts, an end of 0 does not: such a map is taken as a time
    # instance.
    delta = {
        int(abs(end - start))
        for start, end in _intervals_and_gaps(
            maps, lambda start, end: (start == 0 or start) and end
        )
    }
    return gcd_list(delta) if delta else 0


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

    for start, end in _intervals_and_gaps(maps, lambda start, end: end):
        _add_delta(granularity_units, compute_datetime_delta(start, end))

    # The smallest unit with a value is the unit of the granularity. max_days,
    # the days of a whole delta, never names it; its values join the others
    # below as days.
    assigned_time_unit = next(
        (
            time_unit
            for time_unit, values in granularity_units.items()
            if values and time_unit != "max_days"
        ),
        None,
    )
    if assigned_time_unit is None:
        return None

    dlist = set(granularity_units[assigned_time_unit])
    for unit, values in granularity_units.items():
        unit_factor = _unit_factor(assigned_time_unit, unit)
        if unit != assigned_time_unit and unit_factor and values:
            dlist.update({time_value * unit_factor for time_value in values})

    # Find greatest common divisor to get a single time unit
    granularity = gcd_list(dlist)
    plural = "s" if granularity > 1 else ""
    return f"{granularity} {assigned_time_unit}{plural}"


def compute_common_relative_time_granularity(gran_list):
    """Compute the greatest common granule from a list of relative time granules

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = [1, 2, 30]
        >>> tgis.temporal_granularity.compute_common_relative_time_granularity(grans)
        1
    """
    return gcd_list(gran_list)


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


def compute_common_absolute_time_granularity_simple(gran_list):
    """Compute the greatest common granule from a list of absolute time granules

    :param gran_list: List of granularities
    :return: The common granularity

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> grans = ["2 hours", "4 hours", "8 hours"]
        >>> tgis.temporal_granularity.compute_common_absolute_time_granularity_simple(
        ...     grans
        ... )
        '2 hours'
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


def gran_singular_unit(gran):
    """Return the absolute granularity unit in its singular term

    :param gran: input granularity
    :return: granularity unit

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> tgis.gran_singular_unit("1 month")
        'month'
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


def gcd_list(list):
    """Finds the GCD of numbers in a list.

    :param list: List of numbers you want to find the GCD of
                 E.g. [8, 24, 12]
    :return: GCD of all numbers

    """
    return reduce(gcd, list)
