"""Test the suffix option of t.rast.aggregate.ds

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. The
granularity of gran is that of the sampler, which has only intervals, so a
dataset of a single time instant gets the date of its sampler interval.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def _inventory(tools):
    """The maps of the mapset and the space time datasets of the project"""
    return (
        tools.g_list(type="all", mapset=".").stdout.split(),
        [
            tools.t_list(type=stds_type, columns="id").stdout.split()
            for stds_type in ("strds", "str3ds", "stvds")
        ],
    )


def test_a_single_time_instant_gets_the_date_of_its_sampler_interval(tools, prefix):
    # The sampler has one interval, 2001-01-01 to 2001-01-04, and with it the
    # granularity of three days; gran cuts the start of the interval to the
    # day.
    create_stds(tools, "strds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])
    create_stds(
        tools, "strds", f"{prefix}_sampler", [MapSpec(f"{prefix}_s", 0, day(0), day(3))]
    )

    tools.t_rast_aggregate_ds(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        sample=f"{prefix}_sampler",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [f"{prefix}_b_2001_01_01"]


def test_an_unknown_suffix_is_refused_before_anything_is_written(tools, prefix):
    # Three maps in the one sampler interval, so that a run that took gram as
    # num would write their aggregate.
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m{k}", k, day(k), day(k + 1)) for k in range(3)],
    )
    create_stds(
        tools, "strds", f"{prefix}_sampler", [MapSpec(f"{prefix}_s", 0, day(0), day(3))]
    )
    before = _inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            output=prefix,
            basename=f"{prefix}_b",
            sample=f"{prefix}_sampler",
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert _inventory(tools) == before
