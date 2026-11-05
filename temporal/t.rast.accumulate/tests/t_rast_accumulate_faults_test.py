"""Test the week granules of t.rast.accumulate

A start that does not lie on the granularity "1 weeks" moves back to the
Monday on or before it, also into the year before, so the first granule
holds the first map.
"""

from datetime import datetime

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps, message

D = datetime


def test_week_cycles(tools, prefix):
    """Maps of the value 10 on 3, 4 (Saturday, Sunday) and 8 January 2026

    The start 3 January moves to Monday, 29 December 2025. The first week
    holds the maps of 3 and 4 January, whose mean is 10; the second week the
    map of 8 January, so the accumulation reaches 20.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_d{day}", 10, D(2026, 1, day), D(2026, 1, day + 1))
            for day in (3, 4, 8)
        ],
    )
    result = tools.t_rast_accumulate(
        input=f"{prefix}_in",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        start="2026-01-03",
        cycle="4 weeks",
        granularity="1 weeks",
        limits="0,100",
    )
    assert (
        "The start <2026-01-03 00:00:00> is moved to <2025-12-29 00:00:00>"
        in message(result)
    )
    rows = list_maps(tools, "strds", f"{prefix}_out")
    assert [(row.name, row.start, row.end, row.min) for row in rows] == [
        (
            f"{prefix}_out_2025_12_29",
            "2025-12-29 00:00:00",
            "2026-01-05 00:00:00",
            10.0,
        ),
        (
            f"{prefix}_out_2026_01_05",
            "2026-01-05 00:00:00",
            "2026-01-12 00:00:00",
            20.0,
        ),
    ]
