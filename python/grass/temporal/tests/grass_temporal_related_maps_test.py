"""The classic per-relation sampling of grass.temporal.related_maps

The method expansion, the order of the related maps, the closed 2D box
filter, the gap slots and the two sampler guards are pure computations on
slots, so they are checked here without a GRASS session. The tools that use
them are compared with sample_by_dataset() in their own tests.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.relations import (
    contains,
    during,
    equal,
    overlapped,
    overlaps,
    relation,
)
from grass.temporal.algebra.series import Extent, Series, Slot, Space
from grass.temporal.related_maps import (
    boxes_intersect,
    method_relations,
    related_per_granule,
    sampler_refused,
    with_gaps,
)

BOX = Space(north=80, south=0, east=120, west=0)


def union(method):
    return relation("|".join(method_relations(method)))


def slot(name, start, end, space=BOX):
    return Slot(Extent(start, end, "days"), MapRef(f"{name}@PERMANENT"), space, name)


def series(*slots):
    return Series(slots, "raster")


def ids(row):
    return [found.origin for found in row]


def test_method_names_map_to_relations_without_inverse():
    assert union(["equal"]) == equal
    assert union(["during"]) == during
    assert union(["contain"]) == contains
    assert union(["overlap"]) == overlaps | overlapped
    assert union(["equal", "during"]) == equal | during


def test_start_method_omits_equal():
    """The 'start' union leaves equal out, so the method never matches a map of
    equal time, as sample_by_dataset() does not (its EQUALS key is never filed)"""
    rel = union(["start"])
    assert rel.temporal == {"overlapped", "starts", "started", "finishes", "contains"}
    assert "equal" not in rel.temporal


def test_relations_are_tried_in_the_order_of_sample_by_dataset():
    """Plain method names first in list order, then the groups start, overlap
    and contain, each without what the list has already. The map used is the
    first of the first relation with a map, so this order is observable."""
    assert method_relations(["equal", "during"]) == ["equal", "during"]
    assert method_relations(["during", "equal"]) == ["during", "equal"]
    assert method_relations(["start", "equal"]) == [
        "equal",
        "overlapped",
        "starts",
        "started",
        "finishes",
        "contains",
    ]
    assert method_relations(["contain", "overlap", "during"]) == [
        "during",
        "overlapped",
        "overlaps",
        "contains",
    ]
    assert method_relations(["start", "overlap", "contain"]) == [
        "overlapped",
        "starts",
        "started",
        "finishes",
        "contains",
        "overlaps",
    ]


def test_a_repeated_method_name_gives_its_relation_once():
    assert method_relations(["equal", "equal", "during"]) == ["equal", "during"]


def test_unknown_method_is_an_error():
    with pytest.raises(ValueError, match="nonsense"):
        method_relations(["nonsense"])


def test_relation_names_are_no_method_names():
    """The option lists methods, not relations; "contains" is a relation"""
    with pytest.raises(ValueError, match="contains"):
        method_relations(["contains"])


def test_maps_come_relation_by_relation_not_in_time_order():
    """The granule [10, 20] contains a and overlaps b and is overlapped by c.
    The maps follow the order of the names, which time order would not give"""
    granules = series(slot("g", 10, 20))
    inputs = series(slot("c", 5, 12), slot("a", 12, 14), slot("b", 15, 25))
    row = related_per_granule(granules, ["overlaps", "contains", "overlapped"], inputs)
    assert [ids(maps) for maps in row] == [["b", "a", "c"]]


def test_a_map_is_listed_once():
    granules = series(slot("g", 10, 20))
    inputs = series(slot("a", 12, 14))
    row = related_per_granule(granules, ["contains", "contains"], inputs)
    assert [ids(maps) for maps in row] == [["a"]]


def test_equal_start_times_come_in_map_id_order():
    """Three maps start together and lie in one granule. By end time they
    would come b, c, a, which is the order the core would number them; the
    classic order, by id, is a, b, c"""
    granules = series(slot("g", 0, 10))
    inputs = series(slot("b", 1, 2), slot("c", 1, 3), slot("a", 1, 4))
    row = related_per_granule(granules, ["contains"], inputs)
    assert [ids(maps) for maps in row] == [["a", "b", "c"]]


def test_the_result_does_not_depend_on_the_order_of_the_inputs():
    granules = series(slot("g", 0, 10))
    maps = [slot("a", 1, 4), slot("b", 1, 2), slot("c", 3, 5)]
    expected = [["a", "b", "c"]]
    for order in ([0, 1, 2], [2, 1, 0], [1, 2, 0]):
        inputs = Series(tuple(maps[i] for i in order), "raster")
        row = related_per_granule(granules, ["contains"], inputs)
        assert [ids(found) for found in row] == expected


def test_a_granule_without_partner_gives_an_empty_list():
    granules = series(slot("g", 0, 10), slot("h", 20, 30))
    inputs = series(slot("a", 22, 24))
    assert related_per_granule(granules, ["contains"], inputs) == [
        [],
        [inputs.slots[0]],
    ]


def test_no_inputs_give_empty_lists():
    granules = series(slot("g", 0, 10))
    assert related_per_granule(granules, ["contains"], Series((), "raster")) == [[]]


@pytest.mark.parametrize(
    ("other", "expected"),
    [
        (Space(north=40, south=-40, east=180, west=60), True),
        (Space(north=160, south=80, east=240, west=120), True),  # corner contact
        (Space(north=160, south=80, east=100, west=20), True),  # edge contact
        (Space(north=160, south=81, east=240, west=120), False),
        (Space(north=80, south=0, east=240, west=121), False),
    ],
)
def test_boxes_intersect_includes_contact(other, expected):
    assert boxes_intersect(BOX, other) is expected
    assert boxes_intersect(other, BOX) is expected


def test_spatial_keeps_the_maps_whose_box_touches_the_granule():
    """A map that shares only a corner with the granule stays, as in the
    classic R-tree search; one clear of it goes"""
    granules = series(slot("g", 0, 10))
    corner = Space(north=160, south=80, east=240, west=120)
    apart = Space(north=160, south=81, east=240, west=121)
    inputs = series(
        slot("a", 1, 2, BOX), slot("b", 3, 4, corner), slot("c", 5, 6, apart)
    )
    row = related_per_granule(granules, ["contains"], inputs, spatial=True)
    assert [ids(found) for found in row] == [["a", "b"]]
    row = related_per_granule(granules, ["contains"], inputs)
    assert [ids(found) for found in row] == [["a", "b", "c"]]


def test_gap_slots_lie_between_granules_with_a_hole():
    granules = series(slot("g1", 0, 5), slot("g2", 5, 8), slot("g3", 10, 12))
    result = with_gaps(granules)
    assert [found.origin for found in result.slots] == ["g1", "g2", None, "g3"]
    gap = result.slots[2]
    assert (gap.extent.start, gap.extent.end, gap.extent.unit) == (8, 10, "days")
    assert gap.space == Space(0, 0, 0, 0, 0, 0)


def test_a_gap_relates_to_the_maps_of_its_hole():
    granules = with_gaps(series(slot("g1", 0, 5), slot("g2", 10, 14)))
    inputs = series(slot("a", 6, 7), slot("b", 11, 12))
    row = related_per_granule(granules, ["contains"], inputs)
    assert [ids(found) for found in row] == [[], ["a"], ["b"]]


def test_gap_slots_need_no_hole_to_stay_the_same():
    granules = series(slot("g1", 0, 5), slot("g2", 5, 8))
    assert with_gaps(granules).slots == granules.slots


class _Dataset:
    def __init__(self, temporal_type, map_time="interval"):
        self.temporal_type = temporal_type
        self.map_time = map_time

    def get_temporal_type(self):
        return self.temporal_type

    def get_map_time(self):
        return self.map_time


class _Messenger:
    def __init__(self):
        self.errors = []

    def error(self, message):
        self.errors.append(message)


def test_sampler_of_the_same_type_with_intervals_is_accepted():
    msgr = _Messenger()
    assert not sampler_refused(_Dataset("absolute"), _Dataset("absolute"), msgr)
    assert msgr.errors == []


def test_sampler_of_another_temporal_type_is_refused():
    msgr = _Messenger()
    assert sampler_refused(_Dataset("absolute"), _Dataset("relative"), msgr)
    assert msgr.errors == ["The space time datasets must be of the same temporal type"]


def test_sampler_with_points_is_refused():
    msgr = _Messenger()
    sampler = _Dataset("absolute", "point")
    assert sampler_refused(sampler, _Dataset("absolute"), msgr)
    assert msgr.errors == [
        "The temporal map type of the sample dataset must be interval"
    ]


def test_the_temporal_type_is_checked_before_the_map_time():
    msgr = _Messenger()
    sampler_refused(_Dataset("absolute", "point"), _Dataset("relative"), msgr)
    assert msgr.errors == ["The space time datasets must be of the same temporal type"]
