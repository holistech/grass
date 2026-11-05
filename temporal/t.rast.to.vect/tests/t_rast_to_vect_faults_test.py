"""Test the time suffix gran of t.rast.to.vect on a month series from a month end

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month. Maps that start
and end at the same time of the day other than midnight are named by the day.
"""

from datetime import datetime
from itertools import pairwise

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps

ENDS = [
    datetime(2026, 1, 31),
    datetime(2026, 2, 28),
    datetime(2026, 3, 31),
    datetime(2026, 4, 30),
]


def month_end_series(tools, name):
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
    )


def test_gran_suffix_of_month_end_series_names_the_month(tools, prefix):
    month_end_series(tools, f"{prefix}_in")

    tools.t_rast_to_vect(
        input=f"{prefix}_in", output=prefix, basename=f"{prefix}_b", type="point"
    )

    names = [row.name for row in list_maps(tools, "stvds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]


# Two maps of ten days that start and end at 10:30, with a gap of ten days:
# the time of the day is the same at both ends of each step, so the
# granularity is "10 days" and the suffix gran names a map by the day. Before
# 05.11.2026 the granularity was "14400 minutes" and the names ended with the
# hour and the minute, such as _2026_06_11_10_30.
AT_HALF_PAST_TEN = [
    (datetime(2026, 6, 1, 10, 30), datetime(2026, 6, 11, 10, 30)),
    (datetime(2026, 6, 21, 10, 30), datetime(2026, 7, 1, 10, 30)),
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


def test_gran_suffix_of_maps_at_the_same_time_of_day_names_the_day(tools, prefix):
    half_past_ten_series(tools, f"{prefix}_in")
    tools.t_rast_to_vect(
        input=f"{prefix}_in", output=prefix, basename=f"{prefix}_b", type="point"
    )
    assert [row.name for row in list_maps(tools, "stvds", prefix)] == [
        f"{prefix}_b_2026_06_01",
        f"{prefix}_b_2026_06_21",
    ]
