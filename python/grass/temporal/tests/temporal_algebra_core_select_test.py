"""Tests for select() and pairs() of the algebra core

A has the daily intervals [1, 2] .. [4, 5] of January 2001, B the
intervals [1, 3] and [3, 5].
"""

import datetime

import pytest

from grass.temporal.algebra.content import Call, MapRef, call
from grass.temporal.algebra.operations import pairs, select
from grass.temporal.algebra.relations import contains, during, equal, relation
from grass.temporal.algebra.series import Extent, Series, Space


def day(number):
    return datetime.datetime(2001, 1, number)


def days(*spans):
    return [(day(start), day(end)) for start, end in spans]


def ref(name):
    return MapRef(f"{name}@PERMANENT")


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))


@pytest.fixture
def b(make_series):
    return make_series("b", (1, 3), (3, 5))


def test_select_keeps_related_slots_unchanged(a, b):
    assert select(a, during, b).slots == a.slots
    assert select(b, contains, a).slots == b.slots


def test_select_without_related_slots(a, b):
    assert select(a, equal, b).slots == ()
    assert select(a, equal, b, related=False).slots == a.slots


def test_select_partitions_the_series(a, make_series):
    c = make_series("c", (2, 4))
    kept = select(a, during, c)
    dropped = select(a, during, c, related=False)
    assert kept.times() == days((2, 3), (3, 4))
    assert sorted(
        kept.slots + dropped.slots, key=lambda s: s.extent.sort_key()
    ) == list(a.slots)


def test_select_of_empty_series(a):
    assert select(Series(), equal, a).slots == ()
    assert select(a, equal, Series()).slots == ()


def test_series_of_different_temporal_types_cannot_be_related(a, make_series):
    relative = make_series("r", (1, 2), unit="days")
    with pytest.raises(ValueError, match="temporal types"):
        select(a, equal, relative)
    with pytest.raises(ValueError, match="temporal types"):
        pairs(a, equal, relative)


def test_series_of_different_units_cannot_be_related(make_series):
    days_ = make_series("d", (1, 2), unit="days")
    weeks = make_series("w", (1, 2), unit="weeks")
    with pytest.raises(ValueError, match="units"):
        select(days_, equal, weeks)
    with pytest.raises(ValueError, match="units"):
        pairs(days_, equal, weeks)


def test_series_of_different_map_types_meet_only_in_time(make_series, a, b):
    # A selection reads only the time stamps of the other series; pairs()
    # with a content function would put maps of both types into one result.
    vectors = make_series("v", (1, 3), (3, 5), kind="vector")
    assert select(a, during, vectors).slots == select(a, during, b).slots
    paired = pairs(vectors, contains, a)
    assert paired.kind == "vector"
    assert [slot.extent for slot in paired.slots] == [
        slot.extent for slot in pairs(b, contains, a).slots
    ]
    with pytest.raises(ValueError, match="vector"):
        pairs(vectors, contains, a, content=lambda mine, theirs: mine)


def test_spatial_relation_marks_the_result(make_series):
    a = make_series("a", (1, 2), space=Space(1, 0, 1, 0))
    assert not select(a, equal, a).spatial
    assert select(a, relation("equal", spatial=True), a).spatial
    assert not pairs(a, equal, a).spatial
    assert pairs(a, relation("equal", spatial=True), a).spatial


def test_pairs_with_time_stamps_of_the_right_map(a, b):
    result = pairs(a, during, b, extent="right")
    assert result.times() == days((1, 3), (1, 3), (3, 5), (3, 5))
    assert [slot.content for slot in result] == [ref(f"a{i}") for i in range(1, 5)]
    assert all(slot.origin is None for slot in result)


def test_pairs_with_content_of_both(a, b):
    result = pairs(b, contains, a, content=lambda x, y: call("+", x, y))
    assert result.times() == days((1, 3), (1, 3), (3, 5), (3, 5))
    assert [slot.content for slot in result] == [
        Call("+", (ref("b1"), ref("a1"))),
        Call("+", (ref("b1"), ref("a2"))),
        Call("+", (ref("b2"), ref("a3"))),
        Call("+", (ref("b2"), ref("a4"))),
    ]


@pytest.mark.parametrize(
    ("extent", "expected"),
    [
        ("left", (1, 3)),
        ("right", (2, 4)),
        ("union", (1, 4)),
        ("intersection", (2, 3)),
        ("disjoint", (1, 4)),
    ],
)
def test_pairs_extents_of_overlapping_maps(make_series, extent, expected):
    x = make_series("x", (1, 3))
    y = make_series("y", (2, 4))
    assert pairs(x, relation("overlaps"), y, extent=extent).times() == days(expected)


def test_pairs_keeps_the_origin_of_an_unchanged_slot(a):
    assert pairs(a, equal, a).slots == a.slots


def test_unknown_extent_is_rejected(a, b):
    with pytest.raises(ValueError, match="extent must be one of"):
        pairs(a, during, b, extent="target")


def test_select_refuses_target(a, b):
    """The time stamp of the left operand is "left" in every relating
    operation, so "target" is refused by name"""
    with pytest.raises(
        ValueError,
        match=r"^extent must be one of left, right, union, intersection, "
        r"disjoint, got 'target'$",
    ):
        select(a, during, b, extent="target")


# Expected values observed 2026-10-11 by calling temporal_union,
# temporal_intersection and temporal_disjoint_union of map objects on these
# extents (an instant is written with end None):
#   [1, 3] and instant 2: union [1, 3], intersection instant 2, disjoint [1, 3]
#   [1, 3] and [3, 5]:    union [1, 5], intersection instant 3, disjoint [1, 5]
#   instant 2 and 2:      union and disjoint instant 2, intersection instant 2
# The same holds for relative time, with the unit kept.
@pytest.mark.parametrize("unit", [None, "days"])
@pytest.mark.parametrize(
    ("left", "name", "right", "union", "intersection", "disjoint"),
    [
        ((1, 3), "contains", 2, (1, 3), 2, (1, 3)),
        (2, "during", (1, 3), (1, 3), 2, (1, 3)),
        ((1, 3), "precedes", (3, 5), (1, 5), 3, (1, 5)),
        (2, "equal", 2, 2, 2, 2),
    ],
)
def test_pairs_combine_the_time_stamps_with_an_instant(
    make_series, unit, left, name, right, union, intersection, disjoint
):
    def extent(span):
        start, end = span if isinstance(span, tuple) else (span, None)
        if unit is None:
            return Extent(day(start), None if end is None else day(end))
        return Extent(start, end, unit)

    x = make_series("x", left, unit=unit)
    y = make_series("y", right, unit=unit)
    for mode, expected in [
        ("union", union),
        ("intersection", intersection),
        ("disjoint", disjoint),
    ]:
        result = pairs(x, relation(name), y, extent=mode)
        assert [slot.extent for slot in result] == [extent(expected)], mode
