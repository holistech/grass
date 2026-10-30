"""Helpers of the core operations that variants of the algebra use as well

These functions are for variants of the algebra, not for users. The classic
profile (parser/classic.py) judges operands, pairs maps of equal time stamps,
combines boxes and warns with them, so that it does exactly what the core
does; a change here must therefore be checked against that profile too.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import warnings
from collections import defaultdict

from grass.temporal.spatial_extent import SpatialExtent
from grass.temporal.state import get_tgis_message_interface

from ._checks import check_option
from .content import NULL, Call, Const, MapRef, SeriesAggregate, SeriesReduce
from .series import Series, Space

MIXED_TIMES = ("error", "unrelated")


def describe_extent(extent):
    """The text of a time stamp in messages, "no slot" for None"""
    if extent is None:
        return "no slot"
    # The unit tells apart relative times that read alike, e.g. series in
    # days and in hours.
    unit = "" if extent.unit is None else f" {extent.unit}"
    if extent.end is None:
        return f"{extent.start}{unit}"
    return f"{extent.start} .. {extent.end}{unit}"


def check_comparable(first, second, mixed_times="error", *, times_only=False):
    """Relations exist only between series of one temporal type, and of one
    map type where their contents meet

    related() does not check this itself: on mixed absolute and relative
    time, or on different units, it finds no relation instead of failing.
    mixed_times="unrelated" leaves it at that, as the classic algebra does.
    times_only says that no map of second enters the result, only its time
    stamps and boxes or its numbers, so that its map type does not matter:
    t.select relates a vector series to a raster series.
    """
    check_option("mixed_times", mixed_times, MIXED_TIMES)
    if first.kind != second.kind and not times_only:
        msg = f"A {first.kind} series cannot be related to a {second.kind} series"
        raise ValueError(msg)
    if mixed_times == "unrelated":
        return
    units = {
        slot.extent.unit
        for slot in (*first.slots, *second.slots)
        if slot.extent is not None
    }
    if len(units) > 1:
        msg = "Series of different temporal types or units cannot be related"
        raise ValueError(msg)


def content_at(operand, index):
    """The content of operand in the slot at index of an operation

    A series without time stamps gives its only slot, None gives null and a
    number a constant.
    """
    if isinstance(operand, Series):
        return operand.slots[0 if operand.timeless else index].content
    if operand is None:
        return NULL
    if isinstance(operand, (Const, MapRef, Call, SeriesReduce, SeriesAggregate)):
        return operand
    return Const(operand)


def pair_equal_times(targets, matches, others, *, order="sorted", error=ValueError):
    """Pair maps of equal time stamps like numpy broadcasting

    A single map on one side goes with all maps of its time on the other
    side, n maps go with n maps one to one in the order of the series, and
    other counts are an error of the class error. With order="sorted" the
    partners are in the order of others; with "written" the maps of one time
    stay together, the times in the order in which they first occur in the
    matches, as the classic algebra pairs them.
    """
    positions = {}
    counts = defaultdict(int)
    for index, slot in enumerate(targets):
        positions[index] = counts[slot.extent]
        counts[slot.extent] += 1
    paired = []
    for index, found in enumerate(matches):
        size = counts[targets[index].extent]
        groups = defaultdict(list)
        for other_index in found:
            groups[others[other_index].extent].append(other_index)
        chosen = []
        for time, members in groups.items():
            if size == 1 or len(members) == 1:
                chosen.extend(members)
            elif len(members) == size:
                chosen.append(members[positions[index]])
            else:
                msg = (
                    f"{size} maps of the time stamp "
                    f"{describe_extent(targets[index].extent)} cannot be paired with "
                    f"{len(members)} maps of the time stamp {describe_extent(time)}"
                )
                raise error(msg)
        paired.append(sorted(chosen) if order == "sorted" else chosen)
    return paired


def combine_boxes(first, second, operation, three_d):
    """The common box ("intersection") or the box around both ("union") of
    two boxes, as SpatialExtent computes them; None if there is no common box

    The classic algebra asks its map objects for these boxes, which is not
    the test of operations._combined_space(). Measured 2026-10-16 by calling
    SpatialExtent.intersect_2d() and intersect() on such boxes: boxes that
    share only an edge or a corner have no common box, and neither have two
    3D boxes of no height, where _combined_space() finds one. A box around
    both always exists.
    """
    boxes = [
        SpatialExtent(
            north=box.north,
            south=box.south,
            east=box.east,
            west=box.west,
            top=box.top,
            bottom=box.bottom,
        )
        for box in (first, second)
    ]
    if operation == "intersection":
        found = (
            boxes[0].intersect(boxes[1]) if three_d else boxes[0].intersect_2d(boxes[1])
        )
    else:
        found = (
            boxes[0].disjoint_union(boxes[1])
            if three_d
            else boxes[0].disjoint_union_2d(boxes[1])
        )
    if found is None:
        return None
    return Space(
        found.get_north(),
        found.get_south(),
        found.get_east(),
        found.get_west(),
        found.get_top() or 0.0,
        found.get_bottom() or 0.0,
    )


def warn(message):
    """Warn through grass.temporal, or through Python before tgis.init()"""
    # The messenger of grass.temporal exists only after init(), but the
    # operations on series need no session.
    messenger = get_tgis_message_interface()
    if messenger is None:
        warnings.warn(message, stacklevel=3)
    else:
        messenger.warning(message)
