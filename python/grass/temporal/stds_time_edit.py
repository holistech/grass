"""Shifting and snapping the time of the maps of a space time dataset

The functions with ``_map_list`` in their name change the time of map objects
in memory and touch no database; the algebra uses them. shift() and snap()
compute the same new times for the registered maps of a dataset and write
them to the temporal database with update_map_timestamps().

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

from itertools import pairwise

from .abstract_dataset import AbstractDatasetComparisonKeyStartTime
from .datetime_math import increment_datetime_by_string
from .db import connection
from .state import get_current_mapset
from .temporal_granularity import (
    check_granularity_string,
    compute_absolute_time_granularity,
    compute_relative_time_granularity,
)


def _shifted(start, end, gran, absolute: bool):
    """Return start and end moved by the granularity; end may be None"""
    if absolute:
        start = increment_datetime_by_string(start, gran)
        if end is not None:
            end = increment_datetime_by_string(end, gran)
    else:
        start += int(gran)
        if end is not None:
            end += int(gran)
    return start, end


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


def shift_map_list(maps, gran):
    """Temporally shift each map in the list with the provided granularity

    This method does not perform any temporal database operations.

    :param maps: A list of maps  with initialized temporal extent
    :param gran: The granularity to be used for shifting
    :return: The modified map list, None if nothing to shift or wrong
            granularity

    .. code-block:: pycon

        >>> import grass.temporal as tgis
    >>> from grass.temporal.stds_time_edit import shift_map_list
        >>> maps = []
        >>> for i in range(5):
        ...     map = tgis.RasterDataset(None)
        ...     if i % 2 == 0:
        ...         check = map.set_relative_time(i, i + 1, "years")
        ...     else:
        ...         check = map.set_relative_time(i, None, "years")
        ...     maps.append(map)
        >>> for map in maps:
        ...     map.temporal_extent.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 0
         | End time:................... 1
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 1
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 2
         | End time:................... 3
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 3
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 4
         | End time:................... 5
         | Relative time unit:......... years
        >>> maps = shift_map_list(maps, 5)
        >>> for map in maps:
        ...     map.temporal_extent.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 5
         | End time:................... 6
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 6
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 7
         | End time:................... 8
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 8
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 9
         | End time:................... 10
         | Relative time unit:......... years

    """  # noqa: E501
    if maps is None:
        return None

    if not check_granularity_string(gran, maps[-1].get_temporal_type()):
        return None

    for map in maps:
        start, end = map.get_temporal_extent_as_tuple()
        if map.is_time_absolute():
            start, end = _shifted(start, end, gran, absolute=True)
            map.set_absolute_time(start, end)
        elif map.is_time_relative():
            start, end = _shifted(start, end, gran, absolute=False)
            map.set_relative_time(start, end, map.get_relative_time_unit())

    return maps


def snap_map_list(maps):
    """For each map in the list snap the end time to the start time of its
    temporal nearest neighbor in the future.

    Maps with equal time stamps are not snapped.

    The granularity of the map list will be used to create the end time
    of the last map in case it has a time instance as timestamp.

    This method does not perform any temporal database operations.

    :param maps: A list of maps with initialized temporal extent
    :return: The modified map list, None nothing to shift or wrong
            granularity

    Usage:

    .. code-block:: pycon

        >>> import grass.temporal as tgis
    >>> from grass.temporal.stds_time_edit import snap_map_list
        >>> maps = []
        >>> for i in range(5):
        ...     map = tgis.RasterDataset(None)
        ...     if i % 2 == 0:
        ...         check = map.set_relative_time(i, i + 1, "years")
        ...     else:
        ...         check = map.set_relative_time(i, None, "years")
        ...     maps.append(map)
        >>> for map in maps:
        ...     map.temporal_extent.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 0
         | End time:................... 1
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 1
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 2
         | End time:................... 3
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 3
         | End time:................... None
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 4
         | End time:................... 5
         | Relative time unit:......... years
        >>> maps = snap_map_list(maps)
        >>> for map in maps:
        ...     map.temporal_extent.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 0
         | End time:................... 1
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 1
         | End time:................... 2
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 2
         | End time:................... 3
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 3
         | End time:................... 4
         | Relative time unit:......... years
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 4
         | End time:................... 5
         | Relative time unit:......... years

    """  # noqa: E501
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


def _check_mapset(stds, message: str) -> None:
    """Stop with a fatal error unless the dataset is in the current mapset

    The message is given whole and translated by the caller, because a
    translation can not put a verb into a sentence.
    """
    if stds.get_mapset() != get_current_mapset():
        stds.msgr.fatal(message % {"ds": stds.get_id(), "type": stds.get_type()})


def update_map_timestamps(stds, maps, date_list, dbif) -> None:
    """Write the start and end times of date_list to the maps

    The datasets that the maps are registered in are updated as well.

    :param stds: The space time dataset whose temporal type and relative
                 time unit the new times have
    :param maps: A list of map objects
    :param date_list: A list of (start_time, end_time) tuples, one for each map
    :param dbif: The database interface to be used
    """
    # A dict keeps the order, in which the datasets of the maps are met
    datasets_to_modify = {}
    for map, (start, end) in zip(maps, date_list, strict=True):
        map.select(dbif)

        if stds.is_time_absolute():
            map.update_absolute_time(start_time=start, end_time=end, dbif=dbif)
        elif stds.is_time_relative():
            map.update_relative_time(
                start_time=start,
                end_time=end,
                unit=stds.get_relative_time_unit(),
                dbif=dbif,
            )

        datasets_to_modify.update(dict.fromkeys(map.get_registered_stds(dbif) or []))

    stds.update_from_registered_maps(dbif)

    for dataset in datasets_to_modify:
        if dataset != stds.get_id():
            other = stds.get_new_instance(ident=dataset)
            other.select(dbif)
            other.update_from_registered_maps(dbif)


def shift(stds, gran, dbif=None) -> bool:
    """Temporally shift each registered map of the dataset by the granularity

    :param stds: The space time dataset
    :param gran: The granularity to be used for shifting
    :param dbif: The database interface to be used
    :return: True something to shift, False if nothing to shift or wrong
             granularity
    """
    _check_mapset(
        stds,
        _(
            "Unable to shift dataset <%(ds)s> of type "
            "%(type)s in the temporal database. The mapset "
            "of the database does not match the current "
            "mapset"
        ),
    )

    if not check_granularity_string(gran, stds.get_temporal_type()):
        stds.msgr.error(_("Wrong granularity format: %s") % (gran))
        return False

    with connection(dbif) as dbif:
        maps = stds.get_registered_maps_as_objects(dbif=dbif)

        if maps is None:
            return False

        # All new times are computed before the first map is written: a
        # shift that gives a wrong number of days in a month must not stop in
        # the middle of the update.
        absolute = stds.is_time_absolute()
        date_list = [
            _shifted(*map.get_temporal_extent_as_tuple(), gran, absolute)
            for map in maps
        ]

        update_map_timestamps(stds, maps, date_list, dbif)

        return True


def snap(stds, dbif=None) -> None:
    """For each registered map snap the end time to the start time of its
    temporal nearest neighbor in the future

    Maps with equal time stamps are not snapped. The last map gets the
    granularity of the dataset as length if it is a time instance.

    :param stds: The space time dataset
    :param dbif: The database interface to be used
    """
    _check_mapset(
        stds,
        _(
            "Unable to snap dataset <%(ds)s> of type "
            "%(type)s in the temporal database. The mapset "
            "of the database does not match the current "
            "mapset"
        ),
    )

    with connection(dbif) as dbif:
        maps = stds.get_registered_maps_as_objects(dbif=dbif)

        if maps is None:
            return

        extents = [item.get_temporal_extent_as_tuple() for item in maps]
        date_list = _closed_times(extents)

        # Last map
        start, end = extents[-1]
        if end is None:
            if stds.is_time_absolute():
                end = increment_datetime_by_string(start, stds.get_granularity())
            elif stds.is_time_relative():
                end = start + stds.get_granularity()

        date_list.append((start, end))

        update_map_timestamps(stds, maps, date_list, dbif)
