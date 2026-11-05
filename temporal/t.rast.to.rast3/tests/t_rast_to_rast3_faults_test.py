"""Test the layers that t.rast.to.rast3 makes of a month series from a month end

The series from 31 January has the granularity "1 month", so the cube has a
layer per month, not per day. A dataset of a single time instance has no
granularity and is refused with a message.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

D = datetime


def test_month_end_series_has_a_layer_per_month(tools):
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    tools.t_rast_to_rast3(input="month_ends", output="month_cube")
    info = tools.r3_info(map="month_cube", flags="g").keyval
    assert (info["depths"], info["tbres"]) == (3, 1)


@pytest.mark.parametrize(
    ("name", "start", "options"),
    [
        ("absolute_instant", D(2026, 3, 1), {}),
        # Before 05.11.2026 this ended in a TypeError: the stored granularity
        # 0 gave no granule.
        ("relative_instant", 5, {"temporaltype": "relative", "unit": "days"}),
    ],
    ids=["absolute", "relative"],
)
def test_single_instant_is_refused_with_a_message(tools, name, start, options):
    create_stds(tools, "strds", name, [MapSpec(f"{name}_1", 1, start)], **options)
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_to_rast3(input=name, output=f"{name}_cube")
    text = message(error.value)
    assert f"Space time dataset <{name}@" in text
    assert "has no granularity" in text
    assert "granule" not in text
    assert "Traceback" not in text
    assert inventory(tools) == before
