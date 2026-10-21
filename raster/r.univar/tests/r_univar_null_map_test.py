"""Test r.univar on a map that has no valid cell"""

import math
import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def tools(tmp_path):
    """Tools in a session of an XY project with a 3 by 3 region"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.g_region(s=0, n=3, w=0, e=3, res=1)
        yield tools


@pytest.mark.parametrize("expression", ["null()", "float(null())", "double(null())"])
def test_a_map_without_valid_cells_has_no_minimum_and_maximum(tools, expression):
    tools.r_mapcalc(expression=f"empty = {expression}")

    stats = tools.r_univar(map="empty", flags="g").keyval

    # DBL_MAX and -DBL_MAX are the values that the minimum and maximum start
    # from; they are no statistics of a map without cells.
    assert stats["n"] == 0
    assert math.isnan(stats["min"]), stats
    assert math.isnan(stats["max"]), stats
