"""Map objects for the slots of a series

The temporal relations, the time arithmetic and the granularity of
grass.temporal are methods of map objects. The core hands them throw-away
RasterDataset objects that live in memory only, so that each rule exists
once, in the existing code, and no slot is ever changed. Checked 2026-10-11
with SpatioTemporalTopologyBuilder, temporal_buffer(), shift_map_list() and
snap_map_list() on such objects: neither a temporal database nor a session
is needed.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from grass.temporal.space_time_datasets import RasterDataset

from .series import Extent, Space

# The objects are never stored; the mapset only makes the identifier valid.
# Measured 2026-10-11: without "@mapset" the constructor raises "Wrong
# identifier, the mapset is missing".
_MAPSET = "slot"


def as_map(extent, space=None, ident="slot"):
    """Return a map object with the time stamp and the spatial extent

    Relative time of grass.temporal is integral. A fractional stamp raises
    ValueError, because the map object would truncate it silently and
    relate [0.2, 0.8] as equal to [0.5, 0.9].
    """
    map_ = RasterDataset(f"{ident}@{_MAPSET}")
    if extent.unit is None:
        map_.set_absolute_time(extent.start, extent.end)
    else:
        map_.set_relative_time(extent.start, extent.end, extent.unit)
        if map_.get_temporal_extent_as_tuple() != (extent.start, extent.end):
            msg = f"Relative time must be integral, not {extent.start}, {extent.end}"
            raise ValueError(msg)
    if space is not None:
        map_.set_spatial_extent_from_values(
            north=space.north,
            south=space.south,
            east=space.east,
            west=space.west,
            top=space.top,
            bottom=space.bottom,
        )
    return map_


def extent_of(map_):
    """Return the time stamp of a map object"""
    start, end = map_.get_temporal_extent_as_tuple()
    unit = None if map_.is_time_absolute() else map_.get_relative_time_unit()
    return Extent(start, end, unit)


def extent_from(temporal_extent, unit):
    """Return a temporal extent object of grass.temporal as Extent

    None, which the extent methods return for an empty intersection, stays
    None. An interval whose end equals its start is an instant and gets
    end None: union and intersection of grass.temporal return such
    intervals, while as_map() rejects them for relative time. Observed
    2026-10-11 by calling temporal_union() and temporal_intersection() on
    map objects made by as_map() in a plain Python process: the union of two
    equal instants gave start == end == 2 January, and the intersection of
    [1, 3] and [3, 5] gave 3 .. 3 for absolute and for relative time.
    """
    if temporal_extent is None:
        return None
    start = temporal_extent.get_start_time()
    end = temporal_extent.get_end_time()
    return Extent(start, None if end == start else end, unit)


def space_of(map_):
    """Return the spatial extent of a map object"""
    north, south, east, west, top, bottom = map_.get_spatial_extent_as_tuple()
    return Space(north, south, east, west, top, bottom)
