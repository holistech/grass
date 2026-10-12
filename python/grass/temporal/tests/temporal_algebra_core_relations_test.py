"""Tests for the relations of the algebra core

The oracle is a table of probe intervals around the reference [10, 20] of
January 2001, one per relation "probe R reference", as in Allen and
Ferguson 1994 which grass.temporal.temporal_extent cites. during includes
starts and finishes, contains includes started and finished.
"""

import datetime
import random

import pytest

from grass.temporal.algebra import relations
from grass.temporal.algebra._adapters import as_map, extent_from, extent_of, space_of
from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.relations import (
    Relation,
    during,
    equal,
    inverse,
    related,
    relation,
)
from grass.temporal.algebra.series import Extent, Slot, Space

PROBES = {
    "equal": (10, 20),
    "during": (12, 18),
    "contains": (5, 25),
    "starts": (10, 15),
    "started": (10, 25),
    "finishes": (15, 20),
    "finished": (5, 20),
    "precedes": (5, 10),
    "follows": (20, 25),
    "overlaps": (5, 15),
    "overlapped": (15, 25),
    "before": (1, 3),
    "after": (27, 30),
}
EXPECTED = {
    "equal": {"equal"},
    "during": {"during", "starts", "finishes"},
    "contains": {"contains", "started", "finished"},
    "starts": {"starts"},
    "started": {"started"},
    "finishes": {"finishes"},
    "finished": {"finished"},
    "precedes": {"precedes"},
    "follows": {"follows"},
    "overlaps": {"overlaps"},
    "overlapped": {"overlapped"},
}


@pytest.fixture
def probes(make_series):
    return make_series("p", *PROBES.values())


@pytest.mark.parametrize("name", relations.TEMPORAL_RELATIONS)
def test_relation_table(make_series, probes, name):
    """The series sorts its slots by time, so each hit is named by the
    number in the identifier of its map (p1@PERMANENT is the first probe)"""
    reference = make_series("ref", (10, 20))
    found = related(probes.slots, relation(name), reference.slots)
    names = list(PROBES)
    hits = {
        names[int(probes.slots[i].origin.split("@")[0][1:]) - 1]
        for i, hit in enumerate(found)
        if hit
    }
    assert hits == EXPECTED[name]


def test_instants(make_series):
    """Measured 2026-10-11 with the topology builder: an instant inside an
    interval is during it, one at its end follows it"""
    reference = make_series("ref", (10, 20))
    inside, at_end = make_series("i", 15, 20).slots
    assert related([inside], during, reference.slots) == [[0]]
    assert related([at_end], relation("follows"), reference.slots) == [[0]]


def test_indices_are_in_the_order_of_the_other_series(make_series):
    a = make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))
    b = make_series("b", (1, 3), (3, 5))
    assert related(b.slots, relation("contains"), a.slots) == [[0, 1], [2, 3]]
    assert related(a.slots, during, b.slots) == [[0], [0], [1], [1]]


def test_empty_series_relate_nothing(make_series):
    a = make_series("a", (1, 2))
    assert related(a.slots, equal, ()) == [[]]
    assert related((), equal, a.slots) == []


def test_relation_text_and_union():
    assert relation("during|starts") == Relation(frozenset({"during", "starts"}))
    assert (equal | during).temporal == frozenset({"equal", "during"})
    assert relation("equal|overlap").spatial == frozenset({"overlap"})
    assert relation("equal", spatial=True).spatial == frozenset()
    assert relation("equal").spatial is None
    assert str(relation("starts|equal")) == "equal|starts"


def test_spatial_name_alone_is_not_a_relation():
    with pytest.raises(ValueError, match=r"spatial relation.*equal\|overlap"):
        relation("overlap")


def test_relation_rejects_wrong_types():
    with pytest.raises(TypeError):
        equal | "during"
    with pytest.raises(TypeError):
        Relation("equal")
    with pytest.raises(TypeError):
        Relation(frozenset({"equal"}), "in")


def test_unknown_relation_is_rejected():
    with pytest.raises(ValueError, match="Unknown relations: inside"):
        relation("inside")


def test_inverse():
    assert inverse(relation("during|precedes")) == relation("contains|follows")
    assert inverse(relation("equal|in")).spatial == frozenset({"contain"})


def random_series(make_series, name, rng, count=40):
    spans = []
    for _ in range(count):
        start = rng.randint(1, 26)
        spans.append(
            (start, rng.randint(start + 1, 28)) if rng.random() < 0.8 else start
        )
    return make_series(name, *spans)


@pytest.mark.parametrize("name", relations.TEMPORAL_RELATIONS)
def test_inverse_law(make_series, name):
    """l R x if and only if x inverse(R) l"""
    rng = random.Random(name)
    left = random_series(make_series, "l", rng)
    other = random_series(make_series, "x", rng)
    forward = {
        (i, j)
        for i, found in enumerate(related(left.slots, relation(name), other.slots))
        for j in found
    }
    backward = {
        (i, j)
        for j, found in enumerate(
            related(other.slots, inverse(relation(name)), left.slots)
        )
        for i in found
    }
    assert forward == backward


def test_random_series_meet_most_relations(make_series):
    """The inverse law is only as strong as the pairs it sees; with 40 maps
    of whole days in January most relations occur"""
    rng = random.Random("coverage")
    left = random_series(make_series, "l", rng)
    other = random_series(make_series, "x", rng)
    seen = {
        name
        for name in relations.TEMPORAL_RELATIONS
        if any(related(left.slots, relation(name), other.slots))
    }
    assert len(seen) >= 8, seen


def test_spatial_relations(make_series):
    square = Space(10, 0, 10, 0)
    near = Space(15, 5, 15, 5)
    far = Space(30, 20, 30, 20)
    a = make_series("a", (1, 2), space=square)
    others = [
        make_series("e", (1, 2), space=square).slots[0],
        make_series("n", (1, 2), space=near).slots[0],
        make_series("f", (1, 2), space=far).slots[0],
    ]
    assert related(a.slots, equal, others) == [[0, 1, 2]]
    assert related(a.slots, relation("equal", spatial=True), others) == [[0, 1]]
    assert related(a.slots, relation("equal|overlap"), others) == [[1]]
    assert related(a.slots, relation("equal|equivalent"), others) == [[0]]


def test_space_without_names_needs_a_spatial_relation(make_series):
    """Boxes that share only a corner have no spatial relation (they are
    disjoint), although the search of the topology builder finds them; boxes
    that share an edge meet. The classic algebra relates only the second."""
    square = Space(10, 0, 10, 0)
    others = [
        make_series("c", (1, 2), space=Space(20, 10, 20, 10)).slots[0],
        make_series("e", (1, 2), space=Space(20, 10, 10, 0)).slots[0],
    ]
    a = make_series("a", (1, 2), space=square)
    assert related(a.slots, relation("equal", spatial=True), others) == [[1]]


def test_spatial_relation_needs_spatial_extents(make_series):
    a = make_series("a", (1, 2))
    with pytest.raises(ValueError, match="spatial extent"):
        related(a.slots, relation("equal", spatial=True), a.slots)


def test_map_without_time_stamp_has_no_relation(make_series):
    timeless = Slot(None, MapRef("m@PERMANENT"))
    with pytest.raises(ValueError, match="without time stamp"):
        related([timeless], equal, make_series("a", (1, 2)).slots)


def boxes(count, rng):
    """Boxes on a grid of 0 to 6, so that edges often coincide"""
    result = []
    for _ in range(count):
        west, south = rng.randint(0, 4), rng.randint(0, 4)
        result.append(
            Space(rng.randint(south + 1, 6), south, rng.randint(west + 1, 6), west)
        )
    return result


@pytest.mark.parametrize("name", ["equivalent", "in", "contain", "overlap", "meet"])
def test_spatial_inverse_law(make_series, name):
    """l R x if and only if x inverse(R) l, for the spatial names except
    cover and covered (see test_cover_is_not_antisymmetric)"""
    rng = random.Random(name)
    left = [make_series("l", (1, 2), space=space).slots[0] for space in boxes(25, rng)]
    other = [make_series("x", (1, 2), space=space).slots[0] for space in boxes(25, rng)]
    rel = relation(f"equal|{name}")
    forward = {
        (i, j) for i, found in enumerate(related(left, rel, other)) for j in found
    }
    backward = {
        (i, j)
        for j, found in enumerate(related(other, inverse(rel), left))
        for i in found
    }
    assert forward
    assert forward == backward


def test_spatial_direction(make_series):
    """The small box is in the big one and the big one contains it"""
    small = make_series("s", (1, 2), space=Space(4, 2, 4, 2))
    big = make_series("b", (1, 2), space=Space(9, 0, 9, 0))
    assert related(small.slots, relation("equal|in"), big.slots) == [[0]]
    assert related(small.slots, relation("equal|contain"), big.slots) == [[]]
    assert related(big.slots, relation("equal|contain"), small.slots) == [[0]]


def test_cover_is_not_antisymmetric(make_series):
    """Measured 2026-10-11: the spatial classification of grass.temporal
    reports "covered" in both directions for these boxes, although only the
    second box is covered by the first. The pair is pinned so that a fix of
    the classification shows up here; inverse() does not hold for cover
    and covered until then."""
    first = make_series("a", (1, 2), space=Space(9, 8, 7, 5))
    second = make_series("b", (1, 2), space=Space(9, 6, 7, 6))
    covered = relation("equal|covered")
    assert related(first.slots, covered, second.slots) == [[0]]
    assert related(second.slots, covered, first.slots) == [[0]]


def test_relative_time(make_series):
    a = make_series("a", (1, 2), (2, 3), unit="days")
    b = make_series("b", (1, 3), unit="days")
    assert related(b.slots, relation("contains"), a.slots) == [[0, 1]]
    assert related(a.slots, relation("precedes"), a.slots) == [[1], []]


@pytest.mark.parametrize(
    "extent",
    [
        Extent(datetime.datetime(2001, 1, 1), None),
        Extent(
            datetime.datetime(2001, 1, 1),
            datetime.datetime(2001, 1, 3),
        ),
        Extent(3, None, "days"),
        Extent(1, 3, "seconds"),
    ],
)
def test_adapter_round_trip(extent):
    map_ = as_map(extent, Space(10, 0, 9, 1, 5, 2))
    assert extent_of(map_) == extent
    assert space_of(map_) == Space(10, 0, 9, 1, 5, 2)
    assert extent_from(map_.temporal_extent, extent.unit) == extent
    assert extent_from(None, extent.unit) is None


@pytest.mark.parametrize(
    "extent", [Extent(datetime.datetime(2001, 1, 2), None), Extent(2, None, "days")]
)
def test_extent_from_turns_an_empty_interval_into_an_instant(extent):
    """The union of two equal instants is [t, t] in grass.temporal"""
    union = as_map(extent).temporal_union(as_map(extent))
    assert union.get_start_time() == union.get_end_time()
    assert extent_from(union, extent.unit) == extent


@pytest.mark.parametrize(
    "extent",
    [Extent(0.2, 0.8, "seconds"), Extent(1, 2.5, "days"), Extent(0.5, None, "days")],
)
def test_fractional_relative_time_is_rejected(extent):
    """Relative time of grass.temporal is integral; truncating would make
    [0.2, 0.8] and [0.5, 0.9] equal"""
    with pytest.raises(ValueError, match="integral"):
        as_map(extent)
