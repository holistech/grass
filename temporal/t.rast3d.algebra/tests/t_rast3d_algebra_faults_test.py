"""Test the granularity mode of t.rast3d.algebra on a month series from a month end

The core algebra takes the granularity of the library: the series from
31 January (28 February, 31 March) has the granularity "1 month", so the
granularity mode (-g) has a granule per month. The classic algebra (-c) keeps
the granularity "1 day" of the releases before GRASS 8.6.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import list_maps
from grass.tools import Tools

D = datetime
ENDS = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]

# The test chooses its algebra itself: the core by the variable, the classic
# algebra by -c.
pytestmark = pytest.mark.fixed_algebra


@pytest.mark.parametrize(
    ("flags", "count"), [("", 3), ("c", 89)], ids=["core", "classic"]
)
def test_granularity_mode_of_month_end_series(xy_module_session, flags, count):
    env = {**xy_module_session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tools = Tools(env=env, consistent_return_value=True, quiet=True, overwrite=True)
    tools.g_region(n=1, s=0, e=1, w=0, t=1, b=0, res=1, res3=1)
    create_stds(
        tools,
        "str3ds",
        "MON",
        [
            MapSpec(f"mon_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
        overwrite=True,
    )
    tools.t_rast3d_algebra(
        expression=f"G{flags} = MON * 1", basename=f"g{flags}", flags=f"g{flags}"
    )
    rows = list_maps(tools, "str3ds", f"G{flags}")
    assert len(rows) == count
    assert (rows[0].start, rows[-1].end) == (
        "2026-01-31 00:00:00",
        "2026-04-30 00:00:00",
    )
