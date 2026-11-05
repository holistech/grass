"""Test the gaps that t.rast.gapfill fills and the granules of a month series

A gap is time that no map covers: a map that ends inside a longer one leaves
no gap behind it. A month series from 31 January has the granularity
"1 month", so a missing month is filled by one map, not by a map per day.
"""

from datetime import datetime

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps

D = datetime


def test_gap_inside_longer_map_is_not_filled(tools):
    """cover_1 1 to 11 January covers 5 to 8 January; no map is made"""
    create_stds(
        tools,
        "strds",
        "cover",
        [
            MapSpec("cover_1", 1, D(2026, 1, 1), D(2026, 1, 11)),
            MapSpec("cover_2", 2, D(2026, 1, 3), D(2026, 1, 5)),
            MapSpec("cover_3", 3, D(2026, 1, 8), D(2026, 1, 13)),
        ],
    )
    result = tools.t_rast_gapfill(input="cover", basename="cover_fill")
    assert "No gaps found" in result.stderr
    assert [row.name for row in list_maps(tools, "strds", "cover")] == [
        "cover_1",
        "cover_2",
        "cover_3",
    ]


def test_missing_month_of_month_end_series_is_one_map(tools):
    """28 February to 31 March is missing; one map fills it with the mean"""
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec("month_end_1", 10, D(2026, 1, 31), D(2026, 2, 28)),
            MapSpec("month_end_3", 30, D(2026, 3, 31), D(2026, 4, 30)),
        ],
    )
    tools.t_rast_gapfill(input="month_ends", basename="month_fill")
    rows = list_maps(tools, "strds", "month_ends")
    assert [(row.start, row.end, row.min) for row in rows] == [
        ("2026-01-31 00:00:00", "2026-02-28 00:00:00", 10),
        ("2026-02-28 00:00:00", "2026-03-31 00:00:00", 20),
        ("2026-03-31 00:00:00", "2026-04-30 00:00:00", 30),
    ]
