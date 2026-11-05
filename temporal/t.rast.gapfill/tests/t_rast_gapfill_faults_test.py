"""Test the gaps that t.rast.gapfill fills and the granules of a month series

A gap is time that no map covers: a map that ends inside a longer one leaves
no gap behind it. A month series from 31 January has the granularity
"1 month", so a missing month is filled by one map, not by a map per day. Maps
that start and end at the same time of the day other than midnight have a
granularity in days, so the suffix gran names a gap map by the day.
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


# Two maps of ten days that start and end at 10:30, with a gap of ten days:
# the time of the day is the same at both ends of each step, so the
# granularity is "10 days" and the suffix gran names a map by the day. Before
# 05.11.2026 the granularity was "14400 minutes" and the names ended with the
# hour and the minute, such as _2026_06_11_10_30.
AT_HALF_PAST_TEN = [
    (D(2026, 6, 1, 10, 30), D(2026, 6, 11, 10, 30)),
    (D(2026, 6, 21, 10, 30), D(2026, 7, 1, 10, 30)),
]


def half_past_ten_series(tools, name):
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{number}", number, start, end)
            for number, (start, end) in enumerate(AT_HALF_PAST_TEN, start=1)
        ],
    )


def test_gap_map_between_maps_at_the_same_time_of_day_is_named_by_the_day(
    tools, prefix
):
    half_past_ten_series(tools, f"{prefix}_in")
    tools.t_rast_gapfill(input=f"{prefix}_in", basename=f"{prefix}_gap")
    assert [
        (row.name, row.start, row.end)
        for row in list_maps(tools, "strds", f"{prefix}_in")
    ] == [
        (f"{prefix}_in_1", "2026-06-01 10:30:00", "2026-06-11 10:30:00"),
        (f"{prefix}_gap_2026_06_11", "2026-06-11 10:30:00", "2026-06-21 10:30:00"),
        (f"{prefix}_in_2", "2026-06-21 10:30:00", "2026-07-01 10:30:00"),
    ]
