"""Test that r.contour refuses a minlevel above maxlevel"""

import os

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.tools import Tools


@pytest.fixture
def tools(tmp_path):
    """Tools in a session of an XY project"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        yield tools


def test_minlevel_above_maxlevel_is_an_error(tools):
    # Values 1 to 9. Before 2026-11-04 r.contour created an empty map
    # without a message; the refusal comes before the vector map is opened.
    tools.g_region(n=3, s=0, w=0, e=9, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    with pytest.raises(CalledModuleError) as error:
        tools.r_contour(input="m", output="lines", step=1, minlevel=7, maxlevel=3)

    assert error.value.returncode != 0
    assert "<minlevel> (7)" in str(error.value)
    assert "<maxlevel> (3)" in str(error.value)
    assert tools.g_list(type="vector").text.split() == []


def test_equal_minlevel_and_maxlevel_give_one_level(tools):
    tools.g_region(n=3, s=0, w=0, e=9, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    tools.r_contour(input="m", output="lines", step=1, minlevel=4, maxlevel=4)

    table = tools.v_db_select(map="lines", columns="level", flags="c").text
    assert [float(level) for level in table.split()] == [4]
    assert tools.v_info(map="lines", flags="t").keyval["lines"] == 1


def test_limits_are_not_checked_with_a_list_of_levels(tools):
    # With levels, minlevel and maxlevel are ignored, as the step is.
    tools.g_region(n=3, s=0, w=0, e=9, res=1)
    tools.r_mapcalc(expression="m = float(col())")

    tools.r_contour(input="m", output="lines", levels=5, minlevel=7, maxlevel=3)

    assert tools.v_info(map="lines", flags="t").keyval["lines"] == 1
