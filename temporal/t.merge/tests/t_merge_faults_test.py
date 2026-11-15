"""Test the messages of t.merge that follow a refusal of the library"""

import pytest

from grass.temporal.testing.data import MapSpec, make_map, register_stds
from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError


def test_unit_error_message(tools, prefix):
    make_map(tools, "raster", f"{prefix}_d", 1)
    make_map(tools, "raster", f"{prefix}_y", 2)
    register_stds(
        tools,
        "strds",
        f"{prefix}_days",
        [MapSpec(f"{prefix}_d", 1, 0, 1)],
        temporaltype="relative",
        unit="days",
    )
    register_stds(
        tools,
        "strds",
        f"{prefix}_years",
        [MapSpec(f"{prefix}_y", 2, 1, 2)],
        temporaltype="relative",
        unit="years",
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_merge(inputs=f"{prefix}_days,{prefix}_years", output=f"{prefix}_out")

    text = message(error.value)
    assert "Relative time units of space time dataset" in text
    # The cleanup after the error sends messages to the server that the error
    # ended; that is no fault to warn about.
    assert "restart the messenger server" not in text
    assert inventory(tools) == before
