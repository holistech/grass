"""Tests for the options of the relations and operations of the algebra core

The options give the classic algebra its rules (partners in written order,
no deduplication, fold over all partners, stop at the first failure). Their
defaults are the rules of the core, which the other tests of the core pin.

The expected values of the classic rules come from the classic algebra:
the partners are visited as _related_maps() of temporal_algebra.py does,
once per relation name in the written order of the expression
(_check_topology() keeps order and repetitions); the stop at the first
partner that does not combine is set_temporal_extent_list() with
overlay_map_extent(), the selection with a temporal operator is
set_granularity(). Where a probe was run, the comment says so.
"""

import datetime
from dataclasses import replace

import pytest

from grass.exceptions import FatalError
from grass.temporal.algebra.content import Call, Const, MapRef
from grass.temporal.algebra.operations import (
    choose,
    gather,
    merge,
    pair_equal_times,
    pairs,
    select,
)
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import (
    Relation,
    contains,
    equal,
    inverse,
    related,
    relation,
)
from grass.temporal.algebra.series import Series, Space


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
    assert pair_equal_times(target, matches, other) == [[0, 1, 2]]
    assert pair_equal_times(target, matches, other, order="written") == [[0, 2, 1]]


def test_pairing_error_is_raised_as_the_class_asked_for(make_series):
    """gather() refuses counts that cannot be paired with a ValueError;
    pair_equal_times() takes the class, as the classic algebra stops with a
    FatalError"""
    two = make_series("x", (1, 2), (1, 2))
    three = make_series("y", (1, 2), (1, 2), (1, 2))
    message = r"2 maps of the time stamp .* cannot be paired with 3 maps"
    with pytest.raises(ValueError, match=message):
        gather(two, equal, three, reduce="first", equal_times="pairwise")
    matches = [[0, 1, 2], [0, 1, 2]]
    with pytest.raises(FatalError, match=message):
        pair_equal_times(two.slots, matches, three.slots, error=FatalError)


# The probes below were run on 2026-10-16 against the classic algebra: the
# maps are RasterDataset objects with the extents of the cases, related with
# SpatioTemporalTopologyBuilder, and set_temporal_extent_list() of
# TemporalAlgebraParser (bool_op "and", relations CONTAINS and PRECEDES) or
# set_granularity() (selections) combines them. l is [1, 3] with the box
# N10 S0 E10 W0, x1 is [1, 2] and x2 [2, 3] with the same box, x3 is [3, 4].
# Each step is overlay_map_extent(): the spatial and the temporal overlay
# both run, whether the other one failed or not, and both change the same
# map object. Results of the probe, as (time stamp, box E and W):
#
#   x3 box E6 W2 meets, time fails after the instant:  instant day 2, E6 W2
#   x3 box E30 W20 fails, time union combines:          [1, 4], E10 W0
#   x3 box E30 W20 fails, time intersection combines:   instant day 2, E10 W0
#   first partner box fails, time combines:             no result map


def stepped(make_series, extent, last):
    """l [1, 3] and the partners x1 [1, 2], x2 [2, 3] and x3 [3, 4] with the
    box last in the classic probe; l contains x1 and x2 and precedes x3"""
    whole = Space(10, 0, 10, 0, 0, 0)
    target = make_series("l", (1, 3), space=whole)
    other = make_series("x", (1, 2), (2, 3), (3, 4), space=whole)
    slots = (*other.slots[:2], replace(other.slots[2], space=last))
    other = replace(other, slots=slots)
    return gather(
        target,
        relation("contains|precedes"),
        other,
        reduce="count",
        order="written",
        extent=extent,
        box="intersection",
        failure="stop",
    )


def test_a_partner_whose_time_fails_still_applies_its_box(make_series):
    result = stepped(make_series, "intersection", Space(10, 0, 6, 2, 0, 0))
    assert result.times() == [(day(2), None)]
    assert [slot.space for slot in result] == [Space(10, 0, 6, 2, 0, 0)]


def test_a_partner_whose_box_fails_still_applies_its_union_time(make_series):
    result = stepped(make_series, "union", Space(10, 0, 30, 20, 0, 0))
    assert result.times() == [(day(1), day(4))]
    assert [slot.space for slot in result] == [Space(10, 0, 10, 0, 0, 0)]


def test_a_partner_whose_box_fails_still_applies_its_intersection(make_series):
    result = stepped(make_series, "intersection", Space(10, 0, 30, 20, 0, 0))
    assert result.times() == [(day(2), None)]
    assert [slot.space for slot in result] == [Space(10, 0, 10, 0, 0, 0)]


def test_a_first_step_that_fails_leaves_the_target_out(make_series):
    whole = Space(10, 0, 10, 0, 0, 0)
    target = make_series("l", (1, 3), space=whole)
    other = make_series("x", (1, 2), space=Space(10, 0, 30, 20, 0, 0))
    kept = {"reduce": "count", "extent": "union", "box": "intersection"}
    for failure in ("empty", "stop"):
        assert len(gather(target, contains, other, **kept, failure=failure)) == 0
    # skip passes over the partner and keeps the target with the half step
    skipped = gather(target, contains, other, **kept, failure="skip")
    assert skipped.times() == [(day(1), day(3))]


def test_the_reducer_sees_the_partners_after_a_failing_step(make_series):
    result = stepped(make_series, "union", Space(10, 0, 30, 20, 0, 0))
    assert contents(result) == [Const(3)]


def test_a_partner_that_does_not_intersect_empties_the_intersection(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 3), (5, 6))
    result = gather(target, contains, other, reduce=fold("-"), extent="intersection")
    assert result.times() == []


def test_stop_keeps_the_intersection_so_far(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 3), (5, 6), (7, 8))
    result = gather(
        target,
        contains,
        other,
        reduce=fold("-"),
        extent="intersection",
        failure="stop",
    )
    assert result.times() == [(day(2), day(3))]
    # The reducer sees the partners after the failing one as well.
    assert contents(result) == [folded("t1", "x1", "x2", "x3")]


def test_skip_passes_over_the_partner_that_does_not_combine(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5), (3, 9), (7, 8))
    options = {"reduce": "count", "extent": "intersection"}
    # [2, 5] and [3, 9] intersect in [3, 5]; [7, 8] has no time with it.
    skipped = gather(target, contains, other, **options, failure="skip")
    assert skipped.times() == [(day(3), day(5))]
    assert len(gather(target, contains, other, **options)) == 0


def test_failure_changes_nothing_if_all_partners_combine(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5), (3, 6))
    options = {"reduce": fold("-"), "extent": "intersection"}
    default = gather(target, contains, other, **options)
    for failure in ("stop", "skip"):
        assert gather(target, contains, other, **options, failure=failure).slots == (
            default.slots
        )
    assert default.times() == [(day(3), day(5))]


def test_failure_must_be_known(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5))
    with pytest.raises(ValueError, match="failure must be one of empty, stop, skip"):
        gather(target, contains, other, reduce="count", failure="ignore")


def test_box_replaces_space(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5))
    with pytest.raises(ValueError, match="box replaces space"):
        gather(target, contains, other, reduce="count", box="union", space="union")


def test_the_union_box_is_the_box_around_both(make_series):
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 5), space=Space(20, 5, 30, 20, 0, 0))
    result = gather(target, contains, other, reduce="count", box="union")
    assert [slot.space for slot in result] == [Space(20, 0, 30, 0, 0, 0)]


def test_a_slot_without_box_combines(make_series):
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 3), (3, 4))
    result = gather(target, contains, other, reduce="count", box="intersection")
    assert contents(result) == [Const(2)]
    assert [slot.space for slot in result] == [Space(10, 0, 10, 0, 0, 0)]


def test_the_box_ignores_the_height_of_2d_boxes(make_series):
    flat = Space(10, 0, 10, 0, 0, 0)
    target = make_series("t", (1, 10), space=flat)
    other = make_series("x", (2, 3), space=flat)
    result = gather(target, contains, other, reduce="count", box="intersection")
    assert contents(result) == [Const(1)]


def test_the_box_of_3d_boxes_of_no_height_does_not_combine(make_series):
    # Measured 2026-10-16: SpatialExtent.intersect() finds no common box for
    # two 3D boxes of no height, as the classic raster3d algebra asks.
    flat = Space(10, 0, 10, 0, 0, 0)
    target = make_series("t", (1, 10), space=flat, kind="raster3d")
    other = make_series("x", (2, 3), space=flat, kind="raster3d")
    result = gather(target, contains, other, reduce="count", box="intersection")
    assert len(result) == 0
    tall = Space(10, 0, 10, 0, 5, 0)
    target = make_series("t", (1, 10), space=tall, kind="raster3d")
    other = make_series("x", (2, 3), space=tall, kind="raster3d")
    result = gather(target, contains, other, reduce="count", box="intersection")
    assert contents(result) == [Const(1)]


@pytest.fixture
def boxes(make_series):
    """t [1, 10] has a box over the whole area; x1 and x3 lie in the north
    east, x2 far away in the north east corner and has no common box with t"""
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 3), (3, 4), (4, 5), space=Space(10, 5, 10, 5, 0, 0))
    far = Space(30, 20, 30, 20, 0, 0)
    slots = (other.slots[0], replace(other.slots[1], space=far), other.slots[2])
    return target, replace(other, slots=slots)


def minus(first, second):
    return Call("-", (first, second))


def test_pairs_make_one_slot_per_partner_with_the_pair_content(around):
    left, other = around
    result = pairs(left, contains, other, extent="right", content=minus)
    assert contents(result) == [
        minus(ref("l1"), ref("x1")),
        minus(ref("l1"), ref("x2")),
        minus(ref("l1"), ref("x3")),
    ]


def test_fold_all_gives_every_pair_the_fold_of_all_partners(around):
    left, other = around
    result = pairs(left, contains, other, extent="right", content=minus, fold_all=True)
    whole = minus(minus(minus(ref("l1"), ref("x1")), ref("x2")), ref("x3"))
    assert contents(result) == [whole, whole, whole]
    assert result.times() == other.times()


def test_fold_all_folds_in_written_order(neighbours):
    left, other = neighbours
    both = relation("precedes|follows")
    result = pairs(
        left, both, other, extent="right", content=minus, fold_all=True, order="written"
    )
    whole = minus(minus(ref("l1"), ref("x2")), ref("x1"))
    assert contents(result) == [whole, whole]


def test_fold_all_needs_a_content_function(around):
    left, other = around
    with pytest.raises(ValueError, match="fold_all needs a content function"):
        pairs(left, contains, other, fold_all=True)


def test_last_only_keeps_the_last_partner_of_each_slot(around):
    left, other = around
    result = pairs(left, contains, other, extent="right", last_only=True)
    assert result.times() == [other.times()[-1]]


def test_last_only_follows_the_written_order(neighbours):
    left, other = neighbours
    both = relation("precedes|follows")
    kept = pairs(left, both, other, extent="right", last_only=True)
    assert kept.times() == [other.times()[1]]
    written = pairs(left, both, other, extent="right", last_only=True, order="written")
    assert written.times() == [other.times()[0]]


def test_pairs_without_unique_make_a_pair_for_every_name(around):
    left, other = around
    both = relation("contains|started")
    assert len(pairs(left, both, other, extent="right")) == 3
    assert len(pairs(left, both, other, extent="right", unique=False)) == 4


def test_pairs_box_ends_at_the_first_partner_without_common_box(boxes):
    target, other = boxes
    assert len(pairs(target, contains, other, extent="right")) == 3
    kept = pairs(target, contains, other, extent="right", box="intersection")
    assert kept.times() == [other.times()[0]]
    assert [slot.space for slot in kept] == [Space(10, 5, 10, 5, 0, 0)]


def test_pairs_box_combines_each_pair_on_its_own(make_series):
    # A copy of the target is combined with each partner in the classic
    # algebra, so the second pair does not see the box of the first.
    target = make_series("t", (1, 10), space=Space(10, 0, 10, 0, 0, 0))
    other = make_series("x", (2, 3), (3, 4))
    slots = (
        replace(other.slots[0], space=Space(10, 0, 4, 0, 0, 0)),
        replace(other.slots[1], space=Space(10, 0, 10, 6, 0, 0)),
    )
    result = pairs(
        target,
        contains,
        replace(other, slots=slots),
        extent="right",
        box="intersection",
    )
    assert [slot.space for slot in result] == [
        Space(10, 0, 4, 0, 0, 0),
        Space(10, 0, 10, 6, 0, 0),
    ]


def test_pairs_box_still_folds_all_partners(boxes):
    target, other = boxes
    kept = pairs(
        target,
        contains,
        other,
        extent="right",
        content=minus,
        fold_all=True,
        box="intersection",
    )
    assert contents(kept) == [
        minus(minus(minus(ref("t1"), ref("x1")), ref("x2")), ref("x3"))
    ]


def test_pairs_box_replaces_space(boxes):
    target, other = boxes
    with pytest.raises(ValueError, match="box replaces space"):
        pairs(target, contains, other, box="union", space="union")


# Selections with a temporal operator, probe of 2026-10-16 with
# set_granularity() of the classic algebra: l [1, 10] with the relation names
# FINISHED, STARTED, CONTAINS in this order and the partners x1 [1, 3], x2
# [5, 10] and x3 [6, 7]. FINISHED lists x2, STARTED x1, CONTAINS all three.
# The time stamp of l after the operator: l unchanged, r [6, 7] (the last
# partner), i [6, 7], u and d [1, 10]. The intersection passes over x1 after
# x2 (they share no time) and takes up again with the next partners.


@pytest.fixture
def selected(make_series):
    target = make_series("l", (1, 10))
    other = make_series("x", (1, 3), (5, 10), (6, 7))
    both = relation("finished|started|contains")
    return target, both, other


@pytest.mark.parametrize(
    ("extent", "expected"),
    [
        ("left", (day(1), day(10))),
        ("right", (day(6), day(7))),
        ("intersection", (day(6), day(7))),
        ("union", (day(1), day(10))),
        ("disjoint", (day(1), day(10))),
    ],
)
def test_selection_takes_the_time_of_the_partners(selected, extent, expected):
    target, both, other = selected
    result = select(target, both, other, extent=extent, order="written", unique=False)
    assert result.times() == [expected]
    assert contents(result) == contents(target)


def test_selection_stops_or_empties_like_gather(selected):
    target, both, other = selected
    options = {"extent": "intersection", "order": "written", "unique": False}
    # x1 does not intersect the [5, 10] of x2.
    stopped = select(target, both, other, failure="stop", **options)
    assert stopped.times() == [(day(5), day(10))]
    assert len(select(target, both, other, failure="empty", **options)) == 0


def test_selection_without_partner_is_not_kept_and_keeps_its_origin(make_series):
    target = make_series("l", (1, 10), (20, 30))
    other = make_series("x", (2, 3))
    kept = select(target, contains, other, extent="intersection")
    assert kept.times() == [(day(2), day(3))]
    assert kept.slots[0].origin is None
    same = select(target, contains, other)
    assert same.slots[0].origin == target.slots[0].origin


def test_inverse_selection_takes_no_extent(selected):
    target, both, other = selected
    with pytest.raises(ValueError, match="extent must be left"):
        select(target, both, other, related=False, extent="union")


def test_pairs_reject_an_unknown_order(around):
    left, other = around
    with pytest.raises(ValueError, match="order must be one of"):
        pairs(left, contains, other, order="reverse")


def test_intersection_of_an_interval_with_an_instant_is_the_instant(make_series):
    """The classic algebra sets the instant on the map as well, through
    _set_temporal_extent() for the plain extent that the intersection with an
    instant returns (_overlay_temporal_extent() in temporal_algebra.py), so no option selects
    another rule."""
    interval = make_series("i", (1, 10))
    instant = make_series("p", 5)
    gathered = gather(
        interval, contains, instant, reduce="first", extent="intersection"
    )
    paired = pairs(interval, contains, instant, extent="intersection")
    for result in (gathered, paired):
        assert [slot.extent for slot in result] == [instant.slots[0].extent]
        assert result.slots[0].extent.end is None


@pytest.fixture
def mixed(make_series):
    """Maps of absolute time, of relative days, and of relative hours"""
    return (
        make_series("a", (1, 2)),
        make_series("d", (0, 1), unit="days"),
        make_series("h", (0, 1), unit="hours"),
    )


@pytest.mark.parametrize("other", [1, 2])
@pytest.mark.parametrize("function", [select, pairs, gather])
def test_mixed_times_are_refused_by_default(mixed, function, other):
    options = {"reduce": "count"} if function is gather else {}
    with pytest.raises(ValueError, match="different temporal types or units"):
        function(mixed[0], equal, mixed[other], **options)


@pytest.mark.parametrize("other", [1, 2])
def test_mixed_times_relate_nothing_if_asked(mixed, other):
    """The classic algebra finds no relation between maps of absolute and
    relative time or of different units (probed 2026-10-16 with RT + RH and
    RT : tmap(sinst) in the classic algebra: empty results, no error)"""
    first, second = mixed[0], mixed[other]
    options = {"mixed_times": "unrelated"}
    assert not select(first, equal, second, **options).slots
    assert select(first, equal, second, related=False, **options).slots == (first.slots)
    assert not pairs(first, equal, second, **options).slots
    assert not gather(first, equal, second, reduce="count", **options).slots


def test_a_branch_of_other_times_is_left_out_if_asked(mixed):
    condition = replace(mixed[0], sort="scalar")
    condition = replace(
        condition,
        slots=tuple(replace(slot, content=Const(True)) for slot in condition.slots),
    )
    with pytest.raises(ValueError, match="different temporal types or units"):
        choose(condition, mixed[1])
    assert not choose(condition, mixed[1], mixed_times="unrelated").slots


def test_the_mixed_times_option_is_checked(mixed):
    with pytest.raises(ValueError, match="mixed_times must be one of"):
        select(mixed[0], equal, mixed[0], mixed_times="ignore")


def test_merge_keeps_repeats_of_the_first_series_if_asked(make_series):
    """Computed slots lose the map they came from, so two different maps can
    look identical in the first series"""
    one = make_series("a", (1, 2))
    twice = Series(one.slots * 2)
    assert len(merge(twice, one).slots) == 1
    assert len(merge(twice, one, keep_first_repeats=True).slots) == 2
    assert len(merge(one, twice, keep_first_repeats=True).slots) == 1
