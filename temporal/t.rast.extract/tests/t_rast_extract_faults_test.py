"""Test the time suffix gran of t.rast.extract on a month series from a month end

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month.
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

    tools.t_rast_extract(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        expression=f"{prefix}_in * 2",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]
