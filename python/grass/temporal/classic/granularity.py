"""The granularity of a map list as the classic algebra computes it

The classic algebra computes what the releases computed that scientific
publications cite. It takes the granularity of a map list in three places:
the time suffix "gran" of the result maps, the end of the last time instant in
tsnap() and the common granularity of the datasets in the granularity mode
(-g). The temporal library computes the granularity for all other tools and
may change its rules, for example for a month series that starts on the last
day of a month. So the classic algebra, the reference implementation in this
package and the classic profile of the algebra core alike, keeps these copies
of the functions of the library:

- ``compute_absolute_time_granularity()`` and
  ``compute_relative_time_granularity()`` with their helpers from
  ``grass.temporal.temporal_granularity``, and ``compute_datetime_delta()``
  from ``grass.temporal.datetime_math``, as they were on 04.11.2026;
- ``snap_map_list()`` from ``grass.temporal.stds_time_edit``, which calls
  them for the end of the last instant, as it was on 04.11.2026;
- ``compute_common_absolute_time_granularity()`` with
  ``compute_common_absolute_time_granularity_simple()`` and their helpers
  from ``grass.temporal.temporal_granularity``, as they were on 06.11.2026,
  after the common granule compared the finer fields of the start dates.
  The algebra core calls the function of the library, the granularity mode
  of the classic algebra this copy, so that a later change of the library
  does not change the classic results. The relative common granularity is
  only gcd_list() and comes from the library.

``dataset_granularity()`` computes the granularity of a dataset from its maps
with these copies, in place of the granularity stored in the temporal
database, which the library computed when the maps were registered.

The code of the copies is that of the library; only the calls between them
are switched to the copies. Fix an error of the classic algebra here only
with an explicit decision, as for every change of its results. One such
decision, of 05.11.2026, brought the correction of compute_datetime_delta()
of that day into the copy: it counts the months between two firsts of a
month over more than a year in full and a unit of the time of the day only
where the two times differ in it or a finer unit. The copy computes the
delta as the library does.

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING

from grass.temporal.abstract_dataset import AbstractDatasetComparisonKeyStartTime
from grass.temporal.abstract_map_dataset import AbstractMapDataset
from grass.temporal.datetime_math import datetime_delta, increment_datetime_by_string
from grass.temporal.temporal_granularity import check_granularity_string, gcd_list

if TYPE_CHECKING:
    from datetime import datetime

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

    The units of a datetime delta are second, minute, hour, day, month, year
    and max_days, the number of days of the whole delta. Only units of a fixed
    length can be counted in a smaller one, and the year in months.
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


def _get_time_tuple_function(maps):
    """Return the function that reads (start, end) of a map object or a row

    :param maps: a list of AbstractDataset objects or database rows
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
    """
    if end1 is None:
        return start > start1

    return start > end1


def _intervals_and_gaps(maps, is_interval):
    """Yield the (start, end) of every interval and every gap of a map list

    A gap lies between a map and the next one that starts after it. It begins
    at the end of the earlier map, or at its start if that end is false (None,
    or 0 in relative time).

    A map without a start time is left out. The reading of a dataset gives a
    map no time when it refuses the stored times, for example an end before
    the start, and names the map; the time it would have covered is unknown, so
    a gap reaches from the map before it to the map after it.

    :param maps: A list of map objects or database rows, ordered by start time
    :param is_interval: A function of start and end that tells whether a map
                        is an interval; the temporal types differ in it
    """
    get_time_tuple = _get_time_tuple_function(maps)
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


def compute_datetime_delta(start: datetime, end: datetime) -> datetime_delta:
    """Return a dictionary with the accumulated delta in year, month, day,
    hour, minute and second, and max_days, the days of the whole delta"""
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
        comp["month"] = 12 * comp["year"] + end.month - start.month

    # Count full days
    comp["day"] = 0 if start.day == 1 and end.day == 1 else day_diff

    # Time. Each unit counts the whole interval in that unit, from the next
    # coarser unit that is not zero: the difference of the field plus all of
    # the interval before it. A unit in which the two times of the day and all
    # finer units are equal does not count, or two instants at 10:30 ten days
    # apart would have a granularity in minutes. An hour or a minute that is 0
    # at both ends does not count either, as it never did, even where a finer
    # unit differs (00:30 to 00:45 ten days later has no hours): the minutes
    # then hold the whole delta, so the granularity is the same.
    start_time = (start.hour, start.minute, start.second)
    end_time = (end.hour, end.minute, end.second)
    # Hours
    if (start.hour == 0 and end.hour == 0) or start_time == end_time:
        comp["hour"] = 0
    else:
        d = end.hour - start.hour
        comp["hour"] = d + 24 + 24 * day_diff if d < 0 else d + 24 * day_diff

    # Minutes
    if (start.minute == 0 and end.minute == 0) or start_time[1:] == end_time[1:]:
        comp["minute"] = 0
    else:
        before = 60 * comp["hour"] if comp["hour"] else 24 * 60 * day_diff
        comp["minute"] = end.minute - start.minute + before

    # Seconds
    if start.second == end.second:
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


def compute_relative_time_granularity(maps):
    """Compute the relative time granularity

    The computation is only correct for maps that do not overlap, so a
    correct temporal topology is required.

    :param maps: a ordered by start_time list of map objects or database rows
    :return: An integer, None for no maps
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

    The computation is only correct for maps that do not overlap, so a
    correct temporal topology is required.

    The computed granularity is returned as number of seconds or minutes
    or hours or days or months or years.

    :param maps: a ordered by start_time list of map objects or database rows
    :return: The granularity as string "integer unit"; None for no maps and
             for maps without any time difference, such as a single time point
    """

    if not maps:
        return None

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


def compute_common_absolute_time_granularity(gran_list, start_date_list=None):
    """Compute the greatest common granule from a list of absolute time granules,
    considering the start times of the related space time datasets in the
    common granularity computation.

    The list of start dates is optional. If you use this function to compute a common
    granularity between space time datasets, then you should provide their start times
    to avoid wrong synchronization: if the start times differ in the unit of the
    common granule or in a finer one, the result is one unit of the finest unit in
    which they differ ("1 hour" for "1 day" with starts at midnight and at noon).
    The years of the start times are not compared.

    :param gran_list: List of granularities
    :param start_date_list: List of the start times of related space time datasets
    :return: The common granularity, None for an empty list of granules and
             False if a granule is invalid
    """

    common_granule = compute_common_absolute_time_granularity_simple(gran_list)

    if not common_granule or start_date_list is None:
        return common_granule

    num, granule = common_granule.split()
    unit = _singular_unit(granule)

    if unit in _UNITS:
        # A granule has to start with the maps of each dataset. Start dates
        # that differ in the field of the unit allow no longer granule than
        # one unit; the same holds for a finer field, where only a granule of
        # that finer unit fits both: daily maps from midnight and daily maps
        # from noon share no day, but the hour. The year itself is not
        # compared, as it never was.
        finer = _UNITS[: _UNITS.index(unit)]
        compared = (*finer, unit) if unit in _HIERARCHY_LIMIT else finer
        for field in compared:
            first = getattr(start_date_list[0], field)
            if any(getattr(start, field) != first for start in start_date_list):
                return f"1 {field}"

    if unit in _HIERARCHY_LIMIT:
        limit = _HIERARCHY_LIMIT[unit]
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


def _closed_times(extents):
    """Return (start, end) for all but the last of the (start, end) extents

    The end is the start of the next extent. An extent that starts together
    with the next one keeps its own end, because the end of the next map must
    not replace it and equal time stamps can not be snapped.
    """
    return [
        (start, start_next) if start != start_next else (start, end)
        for (start, end), (start_next, _end_next) in pairwise(extents)
    ]


def snap_map_list(maps):
    """For each map in the list snap the end time to the start time of its
    temporal nearest neighbor in the future.

    Maps with equal time stamps are not snapped. The granularity of the map
    list gives the end time of the last map if it is a time instance. No
    temporal database operation is performed.

    :param maps: A list of maps with initialized temporal extent
    :return: The modified map list, None for an empty list
    """
    if maps is None or len(maps) == 0:
        return None

    # We need to sort the maps temporally by start time
    maps = sorted(maps, key=AbstractDatasetComparisonKeyStartTime)

    extents = [item.get_temporal_extent_as_tuple() for item in maps]
    for item, (start, end) in zip(maps, _closed_times(extents), strict=False):
        if item.is_time_absolute():
            item.set_absolute_time(start, end)
        elif item.is_time_relative():
            item.set_relative_time(start, end, item.get_relative_time_unit())

    # Last map
    start, end = maps[-1].get_temporal_extent_as_tuple()
    # We increment the start time with the dataset
    # granularity if the end time is None
    if end is None:
        if maps[-1].is_time_absolute():
            gran = compute_absolute_time_granularity(maps)
            end = increment_datetime_by_string(start, gran)
            maps[-1].set_absolute_time(start, end)
        elif maps[-1].is_time_relative():
            gran = compute_relative_time_granularity(maps)
            end = start + gran
            maps[-1].set_relative_time(start, end, maps[-1].get_relative_time_unit())

    return maps


def dataset_granularity(stds, dbif):
    """Return the granularity of a dataset, computed from its maps

    The temporal library stores the granularity of a dataset when maps are
    registered, with its rules of that time. This function computes it with
    the copies above from the same rows (all registered maps by start time)
    that the library reads for it, and decides from the rows when there is
    none, as update_from_registered_maps() of the library did on 04.11.2026:
    None for a dataset without maps or with a map without start time (the
    map time "invalid"); the stored value is not read.

    :param stds: The space time dataset, read from the database
    :param dbif: The database interface
    """
    maps = stds.get_registered_maps(order="start_time", dbif=dbif)
    if not maps:
        return None
    get_time_tuple = _get_time_tuple_function(maps)
    if any(get_time_tuple(row)[0] is None for row in maps):
        return None
    if stds.is_time_absolute():
        return compute_absolute_time_granularity(maps)
    return compute_relative_time_granularity(maps)
