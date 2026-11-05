"""Test the week granules and the refused names of t.rast.accumulate

A start that does not lie on the granularity "1 weeks" moves back to the
Monday on or before it, also into the year before, so the first granule
holds the first map. A result map name that another dataset or a raster holds
is refused before a map is computed; the suffix gran follows the granularity.
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
from grass.temporal.testing.session import project_session, run_with_timeout
from grass.tools import ToolError, Tools

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
    ("ends", "first", "last"),
    [
        ([D(2026, 1, 1), D(2026, 2, 1), D(2026, 3, 1)], "2026_01_01", "2026_02_28"),
        # The series from the end of the month counts as one of months; its
        # granules of one day start on 31 January.
        ([D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)], "2026_01_31", "2026_03_30"),
    ],
    ids=["from the first of the month", "from the end of the month"],
)
def test_suffix_gran_follows_granularity_option(tools, prefix, ends, first, last):
    """The suffix gran names the maps by the granularity of the accumulation

    A monthly input and granules of one day: cut to the unit of the input,
    all days of a month would get the name of the month and the run would be
    refused. Cut to the unit of the option granularity, each day has a name.
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

    tools.t_rast_accumulate(
        input=f"{prefix}_in",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        start=str(ends[0].date()),
        cycle="2 months",
        granularity="1 day",
        limits="0,100",
    )

    names = [row.name for row in list_maps(tools, "strds", f"{prefix}_out")]
    assert len(names) == len(set(names)) == 59
    assert names[0] == f"{prefix}_out_{first}"
    assert names[-1] == f"{prefix}_out_{last}"


@pytest.mark.parametrize(
    "ends",
    [
        [D(2026, 1, 1), D(2026, 2, 1), D(2026, 3, 1)],
        [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)],
    ],
    ids=["from the first of the month", "from the end of the month"],
)
def test_default_granularity_message(tools, prefix, ends):
    """Without the option granularity, a monthly input gets one name per day

    The default granularity is one day, so the run goes through and every
    day of the cycle has a map of its own.
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

    result = tools.t_rast_accumulate(
        input=f"{prefix}_in",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        start=str(ends[0].date()),
        cycle="2 months",
        limits="0,100",
    )

    names = [row.name for row in list_maps(tools, "strds", f"{prefix}_out")]
    assert len(names) == len(set(names)) == 59
    assert "exists" not in message(result)


def three_days(tools, prefix):
    """Three daily maps of the value 1 from 2026-01-01, the input dataset"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_d{day}", 1, D(2026, 1, day), D(2026, 1, day + 1))
            for day in (1, 2, 3)
        ],
    )


@pytest.mark.parametrize("overwrite", [False, True], ids=["refused", "overwrite"])
def test_unregistered_raster_with_a_later_name_is_refused_first(
    tools, prefix, overwrite
):
    """A raster that no dataset holds blocks the third granule, not the first

    Without overwrite the run is refused before the first granule is
    computed, so no map of the earlier granules is left behind. With
    overwrite the raster is replaced and the run goes through.
    """
    three_days(tools, prefix)
    tools.r_mapcalc(expression=f"{prefix}_out_2026_01_03 = 9")
    before = inventory(tools)

    arguments = {
        "input": f"{prefix}_in",
        "output": f"{prefix}_out",
        "basename": f"{prefix}_out",
        "start": "2026-01-01",
        "cycle": "3 days",
        "limits": "0,100",
    }
    if overwrite:
        tools.t_rast_accumulate(overwrite=True, **arguments)
        assert [row.min for row in list_maps(tools, "strds", f"{prefix}_out")] == [
            1.0,
            2.0,
            3.0,
        ]
        return

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(**arguments)

    assert (
        f"Raster map <{prefix}_out_2026_01_03@PERMANENT> exists. To overwrite, "
        "use the --overwrite flag." in message(error.value)
    )
    assert inventory(tools) == before
    assert cell_values(tools, f"{prefix}_out_2026_01_03") == [9.0]


@pytest.mark.parametrize("suffix", ["gran", "time"])
def test_overlapping_cycles_with_the_same_name_are_refused_before_writing(
    tools, prefix, suffix
):
    """A negative offset makes cycles overlap and names repeat

    The cycles are January-February, February-March and March-April; the
    granule of February lies in two of them, so with gran and with time two
    result maps would get its name. The run is refused before it computes a
    map; with num the names differ and the run goes through.
    """
    ends = [D(2026, 1, 1), D(2026, 2, 1), D(2026, 3, 1), D(2026, 4, 1)]
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
    arguments = {
        "input": f"{prefix}_in",
        "output": f"{prefix}_out",
        "basename": f"{prefix}_out",
        "start": "2026-01-01",
        "cycle": "2 months",
        "offset": "-1 month",
        "granularity": "1 month",
        "limits": "0,100",
    }

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(suffix=suffix, **arguments)

    assert f"get the same map name <{prefix}_out_2026_02" in message(error.value)
    assert inventory(tools) == before

    tools.t_rast_accumulate(suffix="num", **arguments)
    # Two granules in the first two cycles, two in the next, one in the last.
    assert len(list_maps(tools, "strds", f"{prefix}_out")) == 5


def test_a_negative_offset_of_another_unit_than_the_cycle_is_refused(tmp_path):
    """The cycles of a month and an offset of -29 days stop moving forward

    Each cycle starts two days after the one before until the month is cut at
    the end of February; then the start repeats. The run is refused before it
    writes a map instead of running on forever.
    """
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools,
            "strds",
            "mix_in",
            [
                MapSpec("mix_1", 20, D(2026, 1, 1), D(2026, 1, 31)),
                MapSpec("mix_2", 20, D(2026, 1, 31), D(2026, 3, 5)),
            ],
        )
        before = inventory(tools)

        result = run_with_timeout(
            session,
            [
                "t.rast.accumulate",
                "input=mix_in",
                "output=mix_out",
                "basename=mix_out",
                "start=2026-01-01",
                "cycle=1 month",
                "offset=-29 days",
                "limits=0,100",
                "suffix=num",
            ],
            30,
        )

        assert result is not None, "the tool did not end"
        code, messages = result
        assert code != 0
        assert (
            "The offset must not move the next cycle back to or before the "
            "start of this one" in " ".join(messages.split())
        )
        assert "Traceback" not in messages
        assert inventory(tools) == before


@pytest.mark.parametrize(
    ("cycle", "granularity", "name"),
    [("36 hours", "1 day", "2026_01_02"), ("1 day", "1 month", "2026_01")],
    ids=["cycle shorter than two granules", "cycle shorter than the unit"],
)
def test_cycles_that_do_not_overlap_can_repeat_a_name(
    tools, prefix, cycle, granularity, name
):
    """Granules of different cycles that start in one unit get one name

    The cycles do not overlap and there is no offset, yet the second granule
    of the cycle of 36 hours and the first of the next cycle both start on
    2 January, which gran cuts to the day. The message tells so and the run
    is refused before it writes a map.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_m{number}",
                number,
                D(2026, 1, number),
                D(2026, 1, number + 1),
            )
            for number in (1, 2, 3, 4)
        ],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            start="2026-01-01",
            cycle=cycle,
            granularity=granularity,
            limits="0,100",
        )

    text = message(error.value)
    assert f"get the same map name <{prefix}_out_{name}> from the suffix gran" in text
    assert "overlapping" not in text
    assert inventory(tools) == before
