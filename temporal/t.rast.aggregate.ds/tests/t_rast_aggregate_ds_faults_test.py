"""Test the time suffix gran of t.rast.aggregate.ds on a month series from a month end

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month. The granularity is that of the
sampler, here the month series.
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

    create_stds(
        tools,
        "strds",
        f"{prefix}_days",
        [
            MapSpec(f"{prefix}_d{k}", k, datetime(2026, 2, k), datetime(2026, 2, k + 1))
            for k in (1, 2)
        ]
        + [MapSpec(f"{prefix}_d3", 3, datetime(2026, 3, 5), datetime(2026, 3, 6))]
        + [MapSpec(f"{prefix}_d4", 4, datetime(2026, 4, 5), datetime(2026, 4, 6))],
    )
    tools.t_rast_aggregate_ds(
        input=f"{prefix}_days",
        output=prefix,
        basename=f"{prefix}_b",
        sample=f"{prefix}_in",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]
