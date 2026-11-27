"""Tests for the order of the partners, the combination of their time stamps
and the refusal of mixed times in the relations and operations of the core
"""

import datetime

import pytest

from grass.temporal.algebra.content import Call, MapRef
from grass.temporal.algebra.operations import gather, merge, pairs, select
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import contains, equal, related, relation
from grass.temporal.algebra.series import Series


def partners(left, text, other):
    return related(left.slots, relation(text), other.slots)


@pytest.fixture
def around(make_series):
    """One long map and its parts: x1 [1, 2] starts with it, x2 and x3 lie inside"""
    return make_series("l", (1, 10)), make_series("x", (1, 2), (2, 3), (3, 4))


@pytest.fixture
def neighbours(make_series):
    """The map [3, 4] follows x1 [2, 3] and precedes x2 [4, 5]"""
    return make_series("l", (3, 4)), make_series("x", (2, 3), (4, 5))


def test_the_order_of_the_names_does_not_change_a_relation():
    assert relation("follows|precedes") == relation("precedes|follows")


def test_partners_are_sorted_by_default(neighbours):
    left, other = neighbours
    assert partners(left, "precedes|follows", other) == [[0, 1]]
    assert partners(left, "follows|precedes", other) == [[0, 1]]


def test_partners_are_unique_by_default(around):
    left, other = around
    # The builder files x1 under started and under contains, as contains
    # includes started.
    assert partners(left, "contains|started", other) == [[0, 1, 2]]


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


def test_pairing_error_names_the_counts(make_series):
    two = make_series("x", (1, 2), (1, 2))
    three = make_series("y", (1, 2), (1, 2), (1, 2))
    message = r"2 maps of the time stamp .* cannot be paired with 3 maps"
    with pytest.raises(ValueError, match=message):
        gather(two, equal, three, reduce="first", equal_times="pairwise")


def test_a_partner_that_does_not_intersect_empties_the_intersection(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 3), (5, 6))
    result = gather(target, contains, other, reduce=fold("-"), extent="intersection")
    assert result.times() == []


def test_the_intersection_of_all_partners(make_series):
    target = make_series("t", (1, 10))
    other = make_series("x", (2, 5), (3, 6))
    result = gather(target, contains, other, reduce=fold("-"), extent="intersection")
    assert result.times() == [(day(3), day(5))]


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


def test_pairs_make_one_pair_per_partner(around):
    left, other = around
    both = relation("contains|started")
    assert len(pairs(left, both, other, extent="right")) == 3


def test_selection_without_partner_is_not_kept_and_keeps_its_origin(make_series):
    target = make_series("l", (1, 10), (20, 30))
    other = make_series("x", (2, 3))
    same = select(target, contains, other)
    assert same.times() == [(day(1), day(10))]
    assert same.slots[0].origin == target.slots[0].origin


def test_intersection_of_an_interval_with_an_instant_is_the_instant(make_series):
    """The classic algebra set the instant on the map as well, through
    _set_temporal_extent() for the plain extent that the intersection with an
    instant returns (_overlay_temporal_extent() in temporal_algebra.py)."""
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


def test_merge_drops_repeats_of_the_first_series(make_series):
    one = make_series("a", (1, 2))
    twice = Series(one.slots * 2)
    assert len(merge(twice, one).slots) == 1
