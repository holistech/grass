"""Test the suffix option of t.vect.extract

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. A dataset of a
single time instant has no granularity, so gran, the default, names the new
map like time.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError


def test_a_single_time_instant_gets_the_time_suffix(tools, prefix):
    # The instant 2001-01-02 has no granularity; gran then takes the full
    # start time as time does.
    create_stds(tools, "stvds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])

    tools.t_vect_extract(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        expression="value > 0",
    )

    names = [row.name for row in list_maps(tools, "stvds", prefix)]
    assert names == [f"{prefix}_b_2001_01_02T00_00_00"]


def test_an_unknown_suffix_is_refused_before_anything_is_written(tools, prefix):
    # Three maps, so that a run that took gram as num would write three.
    create_stds(
        tools,
        "stvds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m{k}", k, day(k), day(k + 1)) for k in range(3)],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_vect_extract(
            input=f"{prefix}_in",
            output=prefix,
            basename=f"{prefix}_b",
            expression="value > 0",
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


def _value(tools, name):
    lines = tools.v_db_select(map=name, columns="value").stdout.split()
    return int(lines[-1])


def test_two_maps_of_one_time_are_numbered(tools, prefix):
    # Both maps cover January 2001, so the time suffix of both is 2001_01.
    # The maps run in the order of start time and id: _a before _b, so _a
    # keeps the name and _b becomes the second. Both points have value > 0 and stay.
    create_stds(
        tools,
        "stvds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", 3, day(0), day(31)),
            MapSpec(f"{prefix}_b", 7, day(0), day(31)),
        ],
    )

    tools.t_vect_extract(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        expression="value > 0",
    )

    names = [row.name for row in list_maps(tools, "stvds", prefix)]
    assert sorted(names) == [f"{prefix}_b_2001_01", f"{prefix}_b_2001_01_2"]
    assert _value(tools, f"{prefix}_b_2001_01") == 3
    assert _value(tools, f"{prefix}_b_2001_01_2") == 7
