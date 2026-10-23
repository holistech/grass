"""Test the suffix option of t.rast.algebra

suffix takes gran, time, num and num%NN; any other text is refused before a
map, a dataset or an entry of the temporal database is written. The default
of this tool is num. A result of a single time instant is numbered also with
gran, as in the classic algebra, which numbers a result without
granularity.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError


@pytest.mark.parametrize("suffix", [None, "gran"])
def test_a_single_time_instant_is_numbered(tools, prefix, suffix):
    # One result map: the number from zero with one digit.
    create_stds(tools, "strds", f"{prefix}_in", [MapSpec(f"{prefix}_m", 5, day(1))])
    options = {} if suffix is None else {"suffix": suffix}

    tools.t_rast_algebra(
        expression=f"{prefix} = {prefix}_in * 2",
        basename=f"{prefix}_b",
        **options,
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [f"{prefix}_b_0"]


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
        tools.t_rast_algebra(
            expression=f"{prefix} = {prefix}_in * 2",
            basename=f"{prefix}_b",
            suffix="gram",
        )

    text = message(error.value)
    assert "Invalid suffix <gram>, use gran, time, num or num%NN" in text
    assert "Traceback" not in text
    assert inventory(tools) == before
