"""Tests for the options of the relations and operations of the algebra core

The options give the classic algebra its rules (partners in written order,
no deduplication, fold over all partners, stop at the first failure). Their
defaults are the rules of the core, which the other tests of the core pin.

The expected values of the classic rules come from the classic algebra:
the partners are visited as _related_maps() of temporal_algebra.py (line
1369) does, once per relation name in the written order of the expression
(_check_topology(), line 1530, keeps order and repetitions); the fold and
the stop at the first partner that does not combine are
set_temporal_extent_list() (line 1253).
"""

import datetime
from dataclasses import replace

import pytest

from grass.exceptions import FatalError
from grass.temporal.algebra.content import Call, Const, MapRef
from grass.temporal.algebra.operations import _pair_equal_times, gather
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import (
    Relation,
    contains,
    equal,
    inverse,
    related,
    relation,
)
from grass.temporal.algebra.series import Space


def partners(left, text, other, **options):
    return related(left.slots, relation(text), other.slots, **options)


@pytest.fixture
def around(make_series):
    """One long map and its parts: x1 [1, 2] starts with it, x2 and x3 lie inside"""
    return make_series("l", (1, 10)), make_series("x", (1, 2), (2, 3), (3, 4))


@pytest.fixture
def neighbours(make_series):
    """The map [3, 4] follows x1 [2, 3] and precedes x2 [4, 5]"""
    return make_series("l", (3, 4)), make_series("x", (2, 3), (4, 5))


def test_relation_remembers_the_written_names():
    assert relation("precedes|follows|precedes").written == (
        "precedes",
        "follows",
        "precedes",
    )


def test_written_names_do_not_change_the_identity_of_a_relation():
    assert relation("follows|precedes") == relation("precedes|follows")
    assert relation("follows|precedes").written != relation("precedes|follows").written


def test_written_names_must_be_the_temporal_names():
    with pytest.raises(ValueError, match="written names"):
        Relation(frozenset({"equal"}), written=("during",))


def test_written_names_survive_or_and_inverse():
    both = relation("precedes|follows") | relation("equal")
    assert both.written == ("precedes", "follows", "equal")
    assert inverse(relation("precedes|equal")).written == ("follows", "equal")


def test_partners_are_sorted_by_default(neighbours):
    left, other = neighbours
    assert partners(left, "precedes|follows", other) == [[0, 1]]
    assert partners(left, "follows|precedes", other) == [[0, 1]]


def test_written_order_lists_the_partners_name_by_name(neighbours):
    left, other = neighbours
    assert partners(left, "precedes|follows", other, order="written") == [[1, 0]]
    assert partners(left, "follows|precedes", other, order="written") == [[0, 1]]


def test_written_order_without_written_names_is_sorted_by_name(neighbours):
    left, other = neighbours
    # The constants such as equal or the relations built from sets carry no
    # written order; their names are visited in alphabetical order.
    both = Relation(frozenset({"precedes", "follows"}))
    assert related(left.slots, both, other.slots, order="written") == [[0, 1]]


def test_partners_are_unique_by_default(around):
    left, other = around
    # The builder files x1 under started and under contains, as contains
    # includes started.
    assert partners(left, "contains|started", other) == [[0, 1, 2]]


def test_without_unique_a_partner_is_listed_for_every_name(around):
    left, other = around
    assert partners(left, "contains|started", other, order="written", unique=False) == [
        [0, 1, 2, 0]
    ]
    assert partners(left, "started|contains", other, order="written", unique=False) == [
        [0, 0, 1, 2]
    ]


def test_a_name_written_twice_lists_its_partners_twice(around):
    left, other = around
    assert partners(left, "started|started", other, order="written", unique=False) == [
        [0, 0]
    ]
    assert partners(left, "started|started", other, order="written") == [[0]]


def test_unique_keeps_the_first_position(around):
    left, other = around
    assert partners(left, "contains|started", other, order="written") == [[0, 1, 2]]
    assert partners(left, "started|contains", other, order="written") == [[0, 1, 2]]


def test_sorted_order_without_unique_keeps_the_repetitions(around):
    left, other = around
    assert partners(left, "contains|started", other, unique=False) == [[0, 0, 1, 2]]


def test_written_order_with_spatial_names(make_series):
    box = Space(10, 0, 10, 0, 0, 0)
    left = make_series("l", (3, 4), space=box)
    other = make_series("x", (2, 3), (4, 5), space=box)
    both = relation("precedes|follows|equivalent")
    assert related(left.slots, both, other.slots, order="written") == [[1, 0]]


def test_unknown_order(neighbours):
    left, other = neighbours
    with pytest.raises(ValueError, match="order must be one of sorted, written"):
        partners(left, "precedes", other, order="reverse")


def day(number):
    return datetime.datetime(2001, 1, number)


def ref(name):
    return MapRef(f"{name}@PERMANENT")


def folded(*names):
    return Call("-", tuple(ref(name) for name in names))


def contents(series):
    return [slot.content for slot in series]


def test_gather_folds_in_the_order_of_the_other_series_by_default(neighbours):
    left, other = neighbours
    result = gather(left, relation("precedes|follows"), other, reduce=fold("-"))
    assert contents(result) == [folded("l1", "x1", "x2")]


def test_gather_folds_in_written_order(neighbours):
    left, other = neighbours
    result = gather(
        left, relation("precedes|follows"), other, reduce=fold("-"), order="written"
    )
    assert contents(result) == [folded("l1", "x2", "x1")]


def test_gather_folds_a_partner_once_per_name_without_unique(around):
    left, other = around
    result = gather(
        left,
        relation("contains|started"),
        other,
        reduce=fold("-"),
        order="written",
        unique=False,
    )
    assert contents(result) == [folded("l1", "x1", "x2", "x3", "x1")]


def test_gather_counts_a_partner_once_per_name_without_unique(around):
    left, other = around
    counted = gather(
        left, relation("contains|started"), other, reduce="count", unique=False
    )
    assert contents(counted) == [Const(4)]


def test_gather_rejects_an_unknown_order(neighbours):
    left, other = neighbours
    with pytest.raises(ValueError, match="order must be one of"):
        gather(left, equal, other, reduce="count", order="reverse")


def test_pairing_keeps_the_maps_of_one_time_together_in_written_order(make_series):
    """The slots of a series are ordered by start and end, so the maps of one
    time stamp are always adjacent in it; only a list that is ordered by
    start alone, as the classic algebra orders its maps, interleaves them."""
    target = make_series("t", (1, 10)).slots
    # y1 and y3 have the time stamp [1, 2], y2 has [1, 3]; the list is in the
    # order y1, y2, y3.
    slots = make_series("y", (1, 2), (1, 3), (1, 2)).slots
    other = sorted(slots, key=lambda slot: slot.content.ident)
    matches = [[0, 1, 2]]
    assert _pair_equal_times(target, matches, other) == [[0, 1, 2]]
    assert _pair_equal_times(target, matches, other, order="written") == [[0, 2, 1]]


def test_pairing_error_is_raised_as_the_class_asked_for(make_series):
    two = make_series("x", (1, 2), (1, 2))
    three = make_series("y", (1, 2), (1, 2), (1, 2))
    with pytest.raises(
        FatalError, match=r"2 maps of the time stamp .* cannot be paired with 3 maps"
    ):
        gather(
            two,
            equal,
            three,
            reduce="first",
            equal_times="pairwise",
            pairing_error=FatalError,
        )
    with pytest.raises(
        ValueError, match=r"2 maps of the time stamp .* cannot be paired with 3 maps"
    ):
        gather(two, equal, three, reduce="first", equal_times="pairwise")


# The combination of time stamps stops at the first partner that does not
# combine, as set_temporal_extent_list() of the classic algebra does when
# overlay_map_extent() fails (temporal_algebra.py line 1300): the map keeps
# what the partners before had given it.


def test_a_partner_that_does_not_intersect_empties_the_intersection(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 3), (5, 6))
    result = gather(target, contains, other, reduce=fold("-"), extent="intersection")
    assert result.times() == []


def test_stop_at_failure_keeps_the_intersection_so_far(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 3), (5, 6), (7, 8))
    result = gather(
        target,
        contains,
        other,
        reduce=fold("-"),
        extent="intersection",
        stop_at_failure=True,
    )
    assert result.times() == [(day(2), day(3))]
    # The reducer sees the partners after the failing one as well.
    assert contents(result) == [folded("t1", "x1", "x2", "x3")]


def test_stop_at_failure_changes_nothing_if_all_partners_combine(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5), (3, 6))
    options = {"reduce": fold("-"), "extent": "intersection"}
    stopped = gather(target, contains, other, **options, stop_at_failure=True)
    assert stopped.slots == gather(target, contains, other, **options).slots
    assert stopped.times() == [(day(3), day(5))]


# The box filter follows set_temporal_extent_list() as well: with bool_op
# "and" overlay_map_extent() intersects the box of the result map with the
# box of each partner and stops at the first partner without a common box,
# whether the expression names a spatial relation or not.


@pytest.fixture
def boxes(make_series):
    """t [1, 10] has a box over the whole area; x1 and x3 lie in the north
    east, x2 in the south west and has no common box with x1"""
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 3), (3, 4), (4, 5), space=Space(10, 5, 10, 5, 0, 0))
    far = Space(4, 0, 4, 0, 0, 0)
    slots = (other.slots[0], replace(other.slots[1], space=far), other.slots[2])
    return target, replace(other, slots=slots)


def test_without_box_filter_all_partners_count(boxes):
    target, other = boxes
    result = gather(target, contains, other, reduce=fold("-"), extent="union")
    assert result.times() == [(day(1), day(10))]
    assert contents(result) == [folded("t1", "x1", "x2", "x3")]


def test_box_filter_stops_at_the_first_box_that_does_not_meet(boxes):
    target, other = boxes
    result = gather(
        target,
        contains,
        other,
        reduce=fold("-"),
        extent="intersection",
        space="intersection",
        box_filter=True,
    )
    # Only x1 gives time and box; x2 has no common box with it, x3 is not
    # looked at, but the fold sees all three.
    assert result.times() == [(day(2), day(3))]
    assert [slot.space for slot in result] == [Space(10, 5, 10, 5, 0, 0)]
    assert contents(result) == [folded("t1", "x1", "x2", "x3")]


def test_box_filter_drops_a_target_whose_first_partner_does_not_meet(make_series):
    target = make_series("t", (1, 10), space=Space(10, 5, 10, 5, 0, 0))
    other = make_series("x", (2, 3), space=Space(4, 0, 4, 0, 0, 0))
    options = {"reduce": fold("-"), "missing": "null"}
    assert len(gather(target, contains, other, **options)) == 1
    assert len(gather(target, contains, other, **options, box_filter=True)) == 0


def test_box_filter_lets_slots_without_box_meet(make_series):
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 3), (3, 4))
    result = gather(target, contains, other, reduce="count", box_filter=True)
    assert contents(result) == [Const(2)]


def test_box_filter_ignores_the_height_of_2d_boxes(make_series):
    flat = Space(10, 0, 10, 0, 0, 0)
    target = make_series("t", (1, 10), space=flat)
    other = make_series("x", (2, 3), space=flat)
    result = gather(target, contains, other, reduce="count", box_filter=True)
    assert contents(result) == [Const(1)]


def test_box_filter_judges_3d_boxes_of_no_height_as_not_meeting(make_series):
    # Measured 2026-10-16: SpatialExtent.intersect() finds no common box for
    # two 3D boxes of no height, as the classic raster3d algebra asks.
    flat = Space(10, 0, 10, 0, 0, 0)
    target = make_series("t", (1, 10), space=flat, kind="raster3d")
    other = make_series("x", (2, 3), space=flat, kind="raster3d")
    result = gather(target, contains, other, reduce="count", box_filter=True)
    assert len(result) == 0
    tall = Space(10, 0, 10, 0, 5, 0)
    target = make_series("t", (1, 10), space=tall, kind="raster3d")
    other = make_series("x", (2, 3), space=tall, kind="raster3d")
    result = gather(target, contains, other, reduce="count", box_filter=True)
    assert contents(result) == [Const(1)]
