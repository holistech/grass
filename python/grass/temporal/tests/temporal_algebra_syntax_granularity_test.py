"""Sampling of a series with a common granularity, as the granularity mode
of the algebra does

The expected maps were computed on 2026-10-13 with
AbstractSpaceTimeDataset.resample_maplist_by_granularity() on the same time
stamps, in a temporary XY project.
"""

import pytest

from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.parser.granularity import sample_by_granularity
from grass.temporal.algebra.series import Series, Space


def triples(series):
    """(map name, first day, end day) of each slot, for January 2001"""
    return [
        (slot.content.ident.split("@")[0], slot.extent.start.day, slot.extent.end.day)
        for slot in series.slots
    ]


@pytest.mark.parametrize(
    ("spans", "granularity", "expected"),
    [
        pytest.param(
            [(1, 5)],
            "1 day",
            [("m1", 1, 2), ("m1", 2, 3), ("m1", 3, 4), ("m1", 4, 5)],
            id="granules within one map",
        ),
        pytest.param(
            [(1, 2), (2, 3)], "2 days", [("m1", 1, 3)], id="first of two maps"
        ),
        pytest.param(
            [(1, 3), (4, 6)],
            "2 days",
            [("m1", 1, 3), ("m2", 3, 5), ("m2", 5, 7)],
            id="maps overlapping a granule",
        ),
        pytest.param(
            [1, 3], "1 day", [("m1", 1, 2), ("m2", 3, 4)], id="time instances"
        ),
        pytest.param(
            [(1, 2), 3],
            "1 day",
            [("m1", 1, 2), ("m2", 3, 4)],
            id="intervals and instances",
        ),
        pytest.param(
            [(1, 3), (4, 5), (6, 8)],
            "3 days",
            [("m1", 1, 4), ("m3", 4, 7), ("m3", 7, 10)],
            id="an overlapping map before a map within the granule",
        ),
    ],
)
def test_samples_as_the_classic_algebra(make_series, spans, granularity, expected):
    sampled = sample_by_granularity(make_series("m", *spans), granularity)
    assert triples(sampled) == expected


def test_relative_time(make_series):
    sampled = sample_by_granularity(make_series("r", (0, 4), unit="days"), 2)
    assert [(slot.extent.start, slot.extent.end) for slot in sampled.slots] == [
        (0, 2),
        (2, 4),
    ]
    assert {slot.extent.unit for slot in sampled.slots} == {"days"}
    assert {slot.content for slot in sampled.slots} == {MapRef("r1@PERMANENT")}


def test_relative_time_instances_get_a_granule_at_the_end(make_series):
    sampled = sample_by_granularity(make_series("r", 0, 2, unit="days"), 1)
    assert [(slot.extent.start, slot.extent.end) for slot in sampled.slots] == [
        (0, 1),
        (2, 3),
    ]


def test_sampled_maps_keep_their_spatial_extent(make_series):
    space = Space(3, 0, 3, 0, 1, 0)
    sampled = sample_by_granularity(make_series("m", (1, 3), space=space), "1 day")
    assert [slot.space for slot in sampled.slots] == [space, space]


def test_map_type_and_sort_are_kept(make_series):
    sampled = sample_by_granularity(make_series("m", (1, 3), kind="raster3d"), "1 day")
    assert (sampled.kind, sampled.sort) == ("raster3d", "field")


def test_an_empty_series_stays_empty():
    sampled = sample_by_granularity(Series(kind="raster3d"), "1 day")
    assert sampled.slots == ()
    assert sampled.kind == "raster3d"
