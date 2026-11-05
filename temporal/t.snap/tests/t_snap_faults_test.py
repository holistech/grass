"""Test the end that t.snap gives the last instant of a month series

The instants 31 January, 28 February and 31 March have the granularity
"1 month", so the last one ends a month later, on 30 April. The month is
counted on the series of the first map: an instant on 30 April in a series
from 31 January ends on 31 May, and the snapped dataset keeps the granularity
"1 month".
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps

D = datetime


def test_last_instant_of_month_end_series_ends_a_month_later(tools):
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec("month_end_1", 1, D(2026, 1, 31)),
            MapSpec("month_end_2", 2, D(2026, 2, 28)),
            MapSpec("month_end_3", 3, D(2026, 3, 31)),
        ],
    )
    tools.t_snap(input="month_ends")
    assert [
        (row.start, row.end) for row in list_maps(tools, "strds", "month_ends")
    ] == [
        ("2026-01-31 00:00:00", "2026-02-28 00:00:00"),
        ("2026-02-28 00:00:00", "2026-03-31 00:00:00"),
        ("2026-03-31 00:00:00", "2026-04-30 00:00:00"),
    ]


@pytest.mark.parametrize(
    ("starts", "last_end"),
    [
        (
            [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)],
            D(2026, 5, 31),
        ),
        ([D(2026, 1, 31), D(2026, 2, 28)], D(2026, 3, 31)),
    ],
    ids=["to 30 April", "to 28 February"],
)
def test_last_instant_ends_on_the_month_series_of_the_first(tools, starts, last_end):
    # One month added to 30 April would end on 30 May, and to 28 February on
    # 28 March; the dataset then had the granularity "1 day" or "28 days".
    name = f"series_{len(starts)}"
    create_stds(
        tools,
        "strds",
        name,
        [MapSpec(f"{name}_{n}", n, start) for n, start in enumerate(starts, 1)],
    )
    tools.t_snap(input=name)
    ends = [*starts[1:], last_end]
    assert [(row.start, row.end) for row in list_maps(tools, "strds", name)] == [
        (f"{start:%Y-%m-%d %H:%M:%S}", f"{end:%Y-%m-%d %H:%M:%S}")
        for start, end in zip(starts, ends, strict=True)
    ]
    assert tools.t_info(input=name, flags="g").keyval["granularity"] == "'1 month'"
