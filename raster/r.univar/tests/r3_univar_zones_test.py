"""Test that r3.univar refuses a zones map whose values are not whole numbers"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools, ToolError

NUMBER = "(depth() - 1) * 6 + (row() - 1) * 3 + col()"


@pytest.fixture
def tools(tmp_path):
    """Tools in an XY project with a region of 2 rows, 3 columns, 2 layers"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.g_region(s=0, n=2, w=0, e=3, b=0, t=2, res=1, res3=1)
        tools.r3_mapcalc(expression=f"values = {NUMBER}")
        yield tools


def test_zones_with_whole_numbers_in_a_double_map_are_used(tools):
    # Every 3D raster map has a floating point type; whole numbers in it
    # are zones.
    tools.r3_mapcalc(expression="column_zones = col() * 1.0")

    stats = tools.r3_univar(map="values", zones="column_zones", format="json").json

    assert [(zone["zone"], zone["n"], zone["sum"]) for zone in stats] == [
        (1, 4, 1 + 4 + 7 + 10),
        (2, 4, 2 + 5 + 8 + 11),
        (3, 4, 3 + 6 + 9 + 12),
    ]


def test_zones_that_are_no_whole_numbers_are_refused(tools, tmp_path):
    tools.r3_mapcalc(expression=f"half_zones = ({NUMBER}) / 2.0")
    output = tmp_path / "stats.csv"

    with pytest.raises(ToolError) as error:
        tools.r3_univar(map="values", zones="half_zones", output=output)

    assert (
        "3D raster map <half_zones> used for zoning holds the value 0.5; "
        "zones must be whole numbers"
    ) in " ".join(str(error.value).split())
    assert not output.exists()


def test_a_value_that_is_no_whole_number_is_found_anywhere_in_the_region(tools):
    tools.r3_mapcalc(expression="one_half = if(depth() == 2 && col() == 3, 2.5, 1)")

    with pytest.raises(ToolError) as error:
        tools.r3_univar(map="values", zones="one_half")

    assert "holds the value 2.5" in str(error.value)


def test_a_value_outside_the_region_is_not_checked(tools):
    # Only the cells of the current region are read, as for the statistics.
    tools.r3_mapcalc(expression="upper_half = if(depth() == 2, 2.5, 1)")
    tools.g_region(b=0, t=1)

    stats = tools.r3_univar(map="values", zones="upper_half", format="json").json

    assert [(zone["zone"], zone["n"]) for zone in stats] == [(1, 6)]
