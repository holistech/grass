"""Test sampling=related of t.rast.aggregate

The maps and granules are chosen so that the maps that share only part of
their time with a granule decide the result. The expected values are
derived in the comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message

# Every test makes maps and datasets with tools, which takes more than a
# second (measured 2026-11-10 with the other tests of this directory).
pytestmark = pytest.mark.slow


def _rows(tools, name):
    return [(row.start, row.end, row.min) for row in list_maps(tools, "strds", name)]


def _stamp(offset):
    return day(offset).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture(scope="module")
def weekly(tools):
    """m0=7 over 1 to 8 January 2001, m1=14 over 8 to 15, m2=21 over 15 to 22"""
    maps = [
        MapSpec(f"rw{k}", 7.0 * (k + 1), day(7 * k), day(7 * k + 7)) for k in range(3)
    ]
    create_stds(tools, "strds", "rel_weekly", maps)
    return "rel_weekly"


@pytest.fixture(scope="module")
def long_map(tools):
    """re1=3 over 1 to 21 January 2001, twice as long as a granule of 10 days"""
    create_stds(tools, "strds", "rel_long", [MapSpec("re1", 3.0, day(0), day(20))])
    return "rel_long"


def test_sampling_related_takes_partly_overlapping_maps(tools, weekly):
    # Granules of 10 days from 1 January: [1, 11), [11, 21), [21, 31) (the
    # grid ends behind the last map, which ends on 22 January, and a granule
    # is added while its start is before that). Maps: m0 [1, 8), m1 [8, 15),
    # m2 [15, 22).
    # [1, 11): m0 lies inside, m1 starts inside and ends behind it, so the
    #   average is (7 + 14) / 2 = 10.5.
    # [11, 21): m1 and m2 both reach into it: (14 + 21) / 2 = 17.5.
    # [21, 31): only m2, which started earlier: 21.
    tools.t_rast_aggregate(
        input=weekly,
        output="rel_out",
        basename="rel_out",
        granularity="10 days",
        method="average",
        sampling="related",
    )
    assert _rows(tools, "rel_out") == [
        (_stamp(0), _stamp(10), 10.5),
        (_stamp(10), _stamp(20), 17.5),
        (_stamp(20), _stamp(30), 21.0),
    ]


def test_sampling_contains_takes_only_maps_inside(tools, weekly):
    # With contains only m0 lies wholly inside a granule ([1, 11)). m1 and m2
    # are inside none of them, so the other granules give no map.
    tools.t_rast_aggregate(
        input=weekly,
        output="rel_contains",
        basename="rel_contains",
        granularity="10 days",
        method="average",
        sampling="contains",
    )
    assert _rows(tools, "rel_contains") == [(_stamp(0), _stamp(10), 7.0)]


def test_sampling_related_counts_starts_and_finishes(tools, long_map, has_dataset):
    # Granules of 10 days from 1 January: [1, 11) and [11, 21). re1 [1, 21)
    # is longer than either. The first granule shares the start of re1
    # (relation "starts"), the second shares its end ("finishes"). "contains"
    # reads from the granule, which would have to lie around the map, so it
    # finds no map; "during" would hold the granule, but it is not named.
    # With related both granules relate to re1 and copy its 3.
    tools.t_rast_aggregate(
        input=long_map,
        output="edge_related",
        basename="edge_related",
        granularity="10 days",
        method="average",
        sampling="related",
    )
    assert _rows(tools, "edge_related") == [
        (_stamp(0), _stamp(10), 3.0),
        (_stamp(10), _stamp(20), 3.0),
    ]
    result = tools.t_rast_aggregate(
        input=long_map,
        output="edge_contains",
        basename="edge_contains",
        granularity="10 days",
        method="average",
        sampling="contains",
    )
    assert "No map is related to any granule" in message(result)
    assert not has_dataset("edge_contains")


def test_sampling_related_with_other_names_is_union(tools, weekly):
    # related already holds contains, so the union is related.
    tools.t_rast_aggregate(
        input=weekly,
        output="rel_union",
        basename="rel_union",
        granularity="10 days",
        method="average",
        sampling="related,contains",
    )
    assert _rows(tools, "rel_union") == [
        (_stamp(0), _stamp(10), 10.5),
        (_stamp(10), _stamp(20), 17.5),
        (_stamp(20), _stamp(30), 21.0),
    ]
