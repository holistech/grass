"""Test the suffix option of t.rast.contour

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. A dataset of a
single time instant has no granularity, so gran, the default, names the new
map like time.
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


def test_a_single_time_instant_gets_the_time_suffix(tools, prefix):
    # The instant 2001-01-02 has no granularity; gran then takes the full
    # start time as time does. The map of a single cell has no contour line,
    # so -n keeps the empty vector map.
    create_stds(tools, "strds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])

    tools.t_rast_contour(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        levels=1,
        flags="n",
    )

    names = [row.name for row in list_maps(tools, "stvds", prefix)]
    assert names == [f"{prefix}_b_2001_01_02T00_00_00"]


def test_an_unknown_suffix_is_refused_before_anything_is_written(tools, prefix):
    # Three maps, so that a run that took gram as num would write three.
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m{k}", k, day(k), day(k + 1)) for k in range(3)],
    )
    before = _inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_contour(
            input=f"{prefix}_in",
            output=prefix,
            basename=f"{prefix}_b",
            levels=1,
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert _inventory(tools) == before
