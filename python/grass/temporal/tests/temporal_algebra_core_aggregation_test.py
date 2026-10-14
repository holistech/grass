"""Tests for the output names of the aggregation helper

The slots are built by hand, so no session is needed.
"""

import datetime

from grass.temporal.aggregation_core import _names
from grass.temporal.algebra.content import NULL
from grass.temporal.algebra.series import Extent, Series, Slot


def day(number):
    return datetime.datetime(2001, 1, number)


def series(*extents):
    return Series(tuple(Slot(Extent(*extent), NULL) for extent in extents), "raster")


def test_numeric_suffix_tells_apart_slots_with_one_start_time():
    """Sampler maps may share a start time and differ in their end time; each
    keeps its own position, and a dropped slot leaves a gap"""
    target = series((day(1), day(2)), (day(1), day(3)), (day(1), day(4)))
    surviving = Series((target.slots[0], target.slots[2]), "raster")
    names = _names(target, surviving, "agg", "1 day", "num%02", 10)
    assert names == ["agg_11", "agg_13"]


def test_numeric_suffix_counts_target_slots_that_were_dropped():
    target = series((day(1), day(2)), (day(2), day(3)), (day(3), day(4)))
    surviving = Series((target.slots[1], target.slots[2]), "raster")
    assert _names(target, surviving, "agg", "1 day", "num%02", 0) == [
        "agg_02",
        "agg_03",
    ]


def test_numeric_suffix_numbers_slots_of_equal_extent_in_order():
    """Two sampler maps with one extent are related to the same input maps, so
    both survive; the third slot has no partner and is dropped"""
    target = series((day(1), day(2)), (day(1), day(2)), (day(2), day(3)))
    surviving = Series(target.slots[:2], "raster")
    assert _names(target, surviving, "b", None, "num%02", 0) == ["b_01", "b_02"]
