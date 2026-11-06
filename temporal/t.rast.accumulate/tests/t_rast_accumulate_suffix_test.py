"""Test the suffix option of t.rast.accumulate

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. A dataset of a
single time instant has no granularity, but gran follows the option
granularity of the tool, so it names the new map by the day of its granule.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError


def test_a_single_time_instant_is_named_by_the_day_of_its_granule(tools, prefix):
    # The input dataset of one instant has no granularity. gran cuts the
    # start of the granule to the unit of the option granularity, here a day,
    # so the granule that holds the instant 2001-01-02 is named by that day.
    # stop is set because the end of the dataset is the instant itself, and
    # a cycle ends before its stop.
    create_stds(tools, "strds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])

    tools.t_rast_accumulate(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        start="2001-01-01",
        stop="2001-01-10",
        cycle="12 months",
        limits="0,100",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [f"{prefix}_b_2001_01_02"]


def test_an_unknown_suffix_is_refused_before_anything_is_written(tools, prefix):
    # Three maps, so that a run that took gram as num would write three.
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m{k}", k, day(k), day(k + 1)) for k in range(3)],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(
            input=f"{prefix}_in",
            output=prefix,
            basename=f"{prefix}_b",
            start="2001-01-01",
            cycle="12 months",
            limits="0,100",
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert inventory(tools) == before
