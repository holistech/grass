"""Sampling the maps of a space time dataset by granules

A granule is one step of a granularity between a start and an end time. The
maps that lie in a granule, or contain or overlap it, are what the
granularity mode of the temporal algebra and the tools that aggregate by
granule work on.

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import copy

from .datetime_math import (
    anchor_and_count,
    datetime_after_steps,
    increment_datetime_by_string,
)
from .db import connection
from .temporal_granularity import check_granularity_string
from .topology import SpatioTemporalTopologyBuilder

# The relation of the granule to a map, in the order in which the first one
# present decides which maps a granule gets. An equal map comes before a map
# that contains the granule ("during" seen from the granule), then maps that
# overlap it, and maps that lie in the granule come last. The granularity
# mode of the algebra relies on this order.
_RELATION_ORDER = ("EQUAL", "DURING", "OVERLAPS", "OVERLAPPED", "CONTAINS")


def resample_maplist_by_granularity(maps, start, end, gran, anchor=None):
    """Resample a list of AbstractMapDatasets by a given granularity

    The provided map list must be sorted by start time.
    A valid temporal topology (no overlapping or inclusion allowed)
    is needed to receive correct results.

    Maps with interval time, time instances and mixed
    time are supported.

    The temporal topology search order is as follows:

    1. Maps that are equal to the actual granule are used
    2. If no equal found then maps that contain the actual granule
       are used
    3. If no maps are found that contain the actual granule then maps
       are used that overlaps the actual granule
    4. If no overlaps maps found then overlapped maps are used
    5. If no overlapped maps are found then maps are used that are
       during the actual granule


    Each entry in the resulting list is a list of
    AbstractMapDatasets objects.
    Hence for each granule a list of AbstractMapDatasets can be
    expected.

    Gaps between maps are identified as unregistered maps with id==None.

    :param maps: An ordered list (by start time) of AbstractMapDatasets
            objects. All maps must have the same temporal type
            and the same unit in case of relative time.
    :param start: The start time of the provided map list
    :param end:   The end time of the provided map list
    :param gran: The granularity string to be used, if None the
            granularity of the space time dataset is used.
            Absolute time has the format "number unit", relative
            time has the format "number".
            The unit in case of absolute time can be one of "second,
            seconds, minute, minutes, hour, hours, day, days, week,
            weeks, month, months, year, years". The unit of the
            relative time granule is always the space time dataset
            unit and can not be changed.

    :param anchor: The start of the series the granules belong to, for an
            absolute granule of months or years: the granules count from it,
            so that a cut to the end of a shorter month does not carry over
            (from the anchor 31 January, the granule after 28 February ends
            on 31 March, not on 28 March). start must lie a whole number of
            granules after the anchor; otherwise, and without anchor, the
            granules count from start.
    :return: ordered list of map lists. Each list represents a single
        granule, or None in case nothing found

    Usage:

    .. code-block:: pycon

        >>> import grass.temporal as tgis
    >>> from grass.temporal.granule_sampling import resample_maplist_by_granularity
        >>> maps = []
        >>> for i in range(3):
        ...     map = tgis.RasterDataset("map%i@PERMANENT" % i)
        ...     check = map.set_relative_time(i + 2, i + 3, "days")
        ...     maps.append(map)
        >>> grans = resample_maplist_by_granularity(maps, 0, 8, 1)
        >>> for map_list in grans:
        ...     print(
        ...         map_list[0].get_id(),
        ...         map_list[0].get_temporal_extent_as_tuple(),
        ...     )
        None (0, 1)
        None (1, 2)
        map0@PERMANENT (2, 3)
        map1@PERMANENT (3, 4)
        map2@PERMANENT (4, 5)
        None (5, 6)
        None (6, 7)
        None (7, 8)

        >>> maps = []
        >>> map1 = tgis.RasterDataset("map1@PERMANENT")
        >>> check = map1.set_relative_time(2, 6, "days")
        >>> maps.append(map1)
        >>> map2 = tgis.RasterDataset("map2@PERMANENT")
        >>> check = map2.set_relative_time(7, 13, "days")
        >>> maps.append(map2)
        >>> grans = resample_maplist_by_granularity(maps, 0, 16, 2)
        >>> for map_list in grans:
        ...     print(
        ...         map_list[0].get_id(),
        ...         map_list[0].get_temporal_extent_as_tuple(),
        ...     )
        None (0, 2)
        map1@PERMANENT (2, 4)
        map1@PERMANENT (4, 6)
        map2@PERMANENT (6, 8)
        map2@PERMANENT (8, 10)
        map2@PERMANENT (10, 12)
        map2@PERMANENT (12, 14)
        None (14, 16)

        >>> maps = []
        >>> map1 = tgis.RasterDataset("map1@PERMANENT")
        >>> check = map1.set_relative_time(2, None, "days")
        >>> maps.append(map1)
        >>> map2 = tgis.RasterDataset("map2@PERMANENT")
        >>> check = map2.set_relative_time(7, None, "days")
        >>> maps.append(map2)
        >>> grans = resample_maplist_by_granularity(maps, 0, 16, 2)
        >>> for map_list in grans:
        ...     print(
        ...         map_list[0].get_id(),
        ...         map_list[0].get_temporal_extent_as_tuple(),
        ...     )
        None (0, 2)
        map1@PERMANENT (2, 4)
        None (4, 6)
        map2@PERMANENT (6, 8)
        None (8, 10)
        None (10, 12)
        None (12, 14)
        None (14, 16)

        >>> maps = []
        >>> map1 = tgis.RasterDataset("map1@PERMANENT")
        >>> check = map1.set_absolute_time(datetime(2000, 4, 1), datetime(2000, 6, 1))
        >>> maps.append(map1)
        >>> map2 = tgis.RasterDataset("map2@PERMANENT")
        >>> check = map2.set_absolute_time(datetime(2000, 8, 1), datetime(2000, 12, 1))
        >>> maps.append(map2)
        >>> grans = resample_maplist_by_granularity(
        ...     maps, datetime(2000, 1, 1), datetime(2001, 4, 1), "1 month"
        ... )
        >>> for map_list in grans:
        ...     print(
        ...         map_list[0].get_id(),
        ...         map_list[0].get_temporal_extent_as_tuple(),
        ...     )
        None (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 2, 1, 0, 0))
        None (datetime.datetime(2000, 2, 1, 0, 0), datetime.datetime(2000, 3, 1, 0, 0))
        None (datetime.datetime(2000, 3, 1, 0, 0), datetime.datetime(2000, 4, 1, 0, 0))
        map1@PERMANENT (datetime.datetime(2000, 4, 1, 0, 0), datetime.datetime(2000, 5, 1, 0, 0))
        map1@PERMANENT (datetime.datetime(2000, 5, 1, 0, 0), datetime.datetime(2000, 6, 1, 0, 0))
        None (datetime.datetime(2000, 6, 1, 0, 0), datetime.datetime(2000, 7, 1, 0, 0))
        None (datetime.datetime(2000, 7, 1, 0, 0), datetime.datetime(2000, 8, 1, 0, 0))
        map2@PERMANENT (datetime.datetime(2000, 8, 1, 0, 0), datetime.datetime(2000, 9, 1, 0, 0))
        map2@PERMANENT (datetime.datetime(2000, 9, 1, 0, 0), datetime.datetime(2000, 10, 1, 0, 0))
        map2@PERMANENT (datetime.datetime(2000, 10, 1, 0, 0), datetime.datetime(2000, 11, 1, 0, 0))
        map2@PERMANENT (datetime.datetime(2000, 11, 1, 0, 0), datetime.datetime(2000, 12, 1, 0, 0))
        None (datetime.datetime(2000, 12, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0))
        None (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2001, 2, 1, 0, 0))
        None (datetime.datetime(2001, 2, 1, 0, 0), datetime.datetime(2001, 3, 1, 0, 0))
        None (datetime.datetime(2001, 3, 1, 0, 0), datetime.datetime(2001, 4, 1, 0, 0))

    """  # noqa: E501
    if not maps:
        return None

    first = maps[0]

    # Build the gaplist. An absolute granule counts from the first one, or
    # from the anchor, so that a cut to the end of a shorter month does not
    # carry over: from 31 January the granules start on 28 February and
    # 31 March, not on 28 February and 28 March.
    gap_list = []
    count = 0
    if first.is_time_absolute():
        anchor, count = anchor_and_count(anchor, start, gran)
    while start < end:
        count += 1
        if first.is_time_absolute():
            next_start = datetime_after_steps(anchor, gran, count)
        else:
            next_start = start + gran

        gap = first.get_new_instance(None)
        gap.set_spatial_extent_from_values(0, 0, 0, 0, 0, 0)
        if first.is_time_absolute():
            gap.set_absolute_time(start, next_start)
        else:
            gap.set_relative_time(start, next_start, first.get_relative_time_unit())

        gap_list.append(copy.copy(gap))
        start = next_start

    SpatioTemporalTopologyBuilder().build(gap_list, maps)

    gran_list = []
    for gap in gap_list:
        relations = gap.get_temporal_relations()

        # The first relation present decides, also when its list is empty;
        # a granule without a related map stays a gap.
        map_list = []
        if relations:
            for relation in _RELATION_ORDER:
                if relation in relations:
                    map_list = relations[relation]
                    break

        if not map_list:
            gran_list.append([gap])
            continue

        new_maps = []
        for item in map_list:
            new_map = item.get_new_instance(item.get_id())
            new_map.set_temporal_extent(gap.get_temporal_extent())
            new_map.set_spatial_extent(item.get_spatial_extent())
            new_maps.append(new_map)
        gran_list.append(new_maps)

    return gran_list or None


def _relative_granule(granule, unit):
    """Return a relative granule given as text as a number of units, or None

    A relative granule is a whole number of at least 1 in the unit of the
    dataset, optionally followed by that unit, singular or plural: "12",
    "12 hours" and "12 hour" are the same granule of a dataset in hours.

    :param granule: The granule as text, as a tool option gives it
    :param unit: The relative time unit of the dataset, such as "hours"
    :return: The number, None if the text is no such granule
    """
    words = granule.split()
    if (
        len(words) == 2
        and unit
        and words[1].removesuffix("s") == unit.removesuffix("s")
    ):
        words = words[:1]
    if len(words) != 1:
        return None
    try:
        number = int(words[0])
    except ValueError:
        return None
    return number if number >= 1 else None


def registered_maps_by_granularity(stds, gran=None, where=None, dbif=None):
    """Return the registered maps of the dataset as a list of granules

    Each entry is the list of maps of one granule, see
    :func:`resample_maplist_by_granularity`. A granule without a map is a
    list of one gap object (id None). Maps that overlap a granule only are
    ignored. A valid temporal topology (no overlapping or inclusion) is
    needed to get correct results. The granules start with the earliest map
    and reach the latest end of the maps.

    :param stds: The space time dataset
    :param gran: The granularity string; absolute time has the format
                 "number unit", relative time a whole number in the unit of
                 the dataset, optionally followed by that unit ("12" or
                 "12 hours" for a dataset in hours). If None, the
                 granularity of the dataset is used.
    :param where: The SQL where statement to select a subset of
                  the registered maps without "WHERE"
    :param dbif: The database interface to be used
    :return: The ordered list of map lists, None if nothing is found
    """
    with connection(dbif) as dbif:
        if gran is None:
            gran = stds.get_granularity()
            # A dataset of a single time instance has no time difference to
            # take a granularity from: absolute time stores None, relative
            # time 0.
            if not gran:
                stds.msgr.fatal(
                    _(
                        "Space time dataset <{}> has no granularity, for example "
                        "because it holds a single time instance."
                    ).format(stds.get_id())
                )

        # A relative granule given as a number is taken as it is, as the
        # granularity of the dataset and the classic algebra give it; only a
        # text, as from a tool option, is read here.
        if stds.is_time_relative() and isinstance(gran, str):
            unit = stds.get_relative_time_unit()
            granule = _relative_granule(gran, unit)
            if granule is None:
                stds.msgr.fatal(
                    _(
                        "Invalid granule <{granule}>: space time dataset <{name}> "
                        "has relative time, its granule is a whole number of at "
                        "least 1 in the unit <{unit}>, optionally followed by "
                        "this unit"
                    ).format(granule=gran, name=stds.get_id(), unit=unit)
                )
            gran = granule
        elif not check_granularity_string(gran, stds.get_temporal_type()):
            stds.msgr.fatal(_('Wrong granularity: "%s"') % str(gran))
        elif stds.is_time_absolute() and int(gran.split()[0]) < 1:
            # A granule of 0 never moves on and would run without end; a
            # negative one makes the end time precede the start time. A
            # relative number is taken as it is, see above. The split is safe:
            # check_granularity_string() above accepted the text, so it has a
            # whole number as its first word.
            stds.msgr.fatal(
                _("Invalid granule <{granule}>: the number must be positive").format(
                    granule=gran
                )
            )

        maps = stds.get_registered_maps_as_objects(
            dbif=dbif, order="start_time", where=where
        )

        if not maps:
            return None

        start = maps[0].get_temporal_extent_as_tuple()[0]
        # The maps are ordered by their start, so the last one may end before
        # another one that starts earlier and lasts longer.
        ends = [
            map_end if map_end is not None else map_start
            for map_start, map_end in (
                map_.get_temporal_extent_as_tuple() for map_ in maps
            )
            if map_start is not None
        ]
        if start is None or not ends:
            return None
        end = max(ends)
        # The end of a dataset without interval time moves on by one
        # granule, so that the instants at the end are caught
        if stds.get_map_time() != "interval":
            if stds.is_time_absolute():
                end = increment_datetime_by_string(end, gran)
            else:
                end += gran

        # A selection by where may start inside a month series from a month
        # end. Its granules count from the start of the dataset when the first
        # selected map lies whole granules after it, otherwise from the first
        # selected map.
        anchor = stds.get_temporal_extent_as_tuple()[0]
        return resample_maplist_by_granularity(maps, start, end, gran, anchor)
