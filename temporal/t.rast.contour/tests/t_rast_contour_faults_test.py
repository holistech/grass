"""Test the changes of r.contour as t.rast.contour shows them, and the suffix
gran on a month series from a month end"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def test_minlevel_above_maxlevel_is_refused(tools, ramps, prefix):
    # Before 2026-11-04 r.contour gave empty maps, and t.rast.contour
    # created no map without -n. Now the first r.contour run fails, and
    # nothing is left behind.
    with pytest.raises(ToolError) as error:
        tools.t_rast_contour(
            input=ramps, output=prefix, basename=prefix, step=1, minlevel=3, maxlevel=2
        )

    assert "Option <minlevel> (3.0) is greater than option <maxlevel> (2.0)" in (
        message(error.value)
    )
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0
    assert prefix not in tools.g_list(type="vector").stdout


def test_gran_suffix_of_month_end_series_names_the_month(tools, prefix):
    # A month step that is cut to the end of a shorter month counts as a
    # month, so the series from 31 January (28 February, 31 March) has the
    # granularity "1 month" and the suffix gran names the new maps by the
    # month. Before GRASS 8.6 the granularity was "1 day" and the names
    # carried the day.
    small_region(tools, 4, 4)
    ends = [datetime(2026, 1, 31), datetime(2026, 2, 28), datetime(2026, 3, 31)]
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_in_{number}", "double(col())", start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )

    tools.t_rast_contour(
        input=f"{prefix}_in", output=prefix, basename=f"{prefix}_b", step=1
    )

    names = [row.name for row in list_maps(tools, "stvds", prefix)]
    assert names == [f"{prefix}_b_2026_01", f"{prefix}_b_2026_02"]
