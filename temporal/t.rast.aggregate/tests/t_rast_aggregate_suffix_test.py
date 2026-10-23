"""Test the suffix option of t.rast.aggregate

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. The
granularity of gran is the granularity option, so a dataset of a single time
instant gets the date of its granule.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError


def test_a_single_time_instant_gets_the_date_of_its_granule(tools, prefix):
    # The granule of one day that holds the instant 2001-01-02 starts with
    # it; gran cuts its start to the day of the granularity option.
    create_stds(tools, "strds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])

    tools.t_rast_aggregate(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        granularity="1 day",
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
        tools.t_rast_aggregate(
            input=f"{prefix}_in",
            output=prefix,
            basename=f"{prefix}_b",
            granularity="1 day",
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert inventory(tools) == before
