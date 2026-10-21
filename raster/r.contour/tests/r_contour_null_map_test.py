"""Test r.contour on a map that has no valid cell"""

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
        tools.r_mapcalc(expression="empty = float(null())")
        yield tools


@pytest.mark.parametrize("option", [{"step": 1}, {"levels": [1, 2]}])
def test_a_map_without_values_gives_an_empty_map(tools, option):
    # The step used to ask G_malloc() for an absurd size, because the range of
    # the map is null and the number of levels was taken from it.
    tools.r_contour(input="empty", output="lines", **option)

    info = tools.v_info(map="lines", flags="t").keyval
    assert info["lines"] == 0
    assert info["points"] == 0


def test_a_step_on_a_map_without_values_warns(tools):
    result = tools.r_contour(input="empty", output="lines", step=1)

    assert "Raster map has no values" in result.stderr
