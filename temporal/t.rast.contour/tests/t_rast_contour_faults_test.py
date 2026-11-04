"""Test the changes of r.contour as t.rast.contour shows them"""

import pytest

from grass.temporal.testing.readback import message
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
