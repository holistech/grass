"""Test the week granules and the refused names of t.rast.accumulate

A start that does not lie on the granularity "1 weeks" moves back to the
Monday on or before it, also into the year before, so the first granule
holds the first map. A result map name that another dataset holds, or that
more than one granule gets, is refused before a map is computed.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import (
    cell_values,
    inventory,
    list_maps,
    message,
)
from grass.tools import ToolError

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


def test_overwrite_keeps_map_of_other_dataset(tools, prefix):
    """Overwrite replaces the maps of the old output, not those of another dataset

    The first result map name belongs to the dataset "kept". The run is
    refused before it computes a map, and kept keeps its map with its value.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_d{day}", 1, D(2026, 1, day), D(2026, 1, day + 1))
            for day in (1, 2, 3)
        ],
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_kept",
        [MapSpec(f"{prefix}_out_2026_01_01", 7, D(2026, 6, 1), D(2026, 6, 2))],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            start="2026-01-01",
            cycle="3 days",
            limits="0,100",
            overwrite=True,
        )

    assert (
        f"Map <{prefix}_out_2026_01_01@PERMANENT> is registered in the space time "
        f"dataset <{prefix}_kept@PERMANENT>, not in the output "
        f"<{prefix}_out@PERMANENT>, and is not replaced" in message(error.value)
    )
    assert inventory(tools) == before
    assert [row.name for row in list_maps(tools, "strds", f"{prefix}_kept")] == [
        f"{prefix}_out_2026_01_01"
    ]
    assert cell_values(tools, f"{prefix}_out_2026_01_01") == [7.0]


@pytest.mark.parametrize(
    ("ends", "month"),
    [
        ([D(2026, 1, 1), D(2026, 2, 1), D(2026, 3, 1)], "2026_01"),
        # 31 January alone has the name of January; the second granule, 1
        # February, is the first to repeat a name.
        ([D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)], "2026_02"),
    ],
    ids=["from the first of the month", "from the end of the month"],
)
def test_default_granularity_message(tools, prefix, ends, month):
    """The default granularity of a day gives all days of a month one name

    The suffix gran names a map by the month for a monthly input, so the
    granules of one day collide. The message names the granularity that
    cuts the names, and the run is refused before it writes a map.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            start=str(ends[0].date()),
            cycle="2 months",
            limits="0,100",
        )

    text = message(error.value)
    assert f"<{prefix}_out_{month}>" in text
    assert "granularity <1 month> of the input dataset" in text
    assert "exists" not in text
    assert inventory(tools) == before
