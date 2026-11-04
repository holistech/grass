"""Test that r3.support copies the category table of a 2D raster map"""

import os
from io import StringIO
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import ToolError, Tools


@pytest.fixture
def session(tmp_path):
    """A session in an XY project of its own"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        yield session


@pytest.fixture
def tools(session):
    """Tools with a region of 2 rows, 3 columns, 2 layers

    The 3D map layers holds the number of the layer, the 2D map names holds
    the labels lower and upper for the categories 1 and 2.
    """
    with Tools(session=session, consistent_return_value=True) as tools:
        tools.g_region(s=0, n=2, w=0, e=3, b=0, t=2, res=1, res3=1)
        tools.r3_mapcalc(expression="layers = depth()")
        tools.r3_mapcalc(expression="values = col()")
        tools.r_mapcalc(expression="names = 1")
        tools.r_category(
            map="names", separator=":", rules=StringIO("1:lower\n2:upper\n")
        )
        yield tools


def _labels(tools):
    """Return the zones of layers with their labels, as r3.univar reads them"""
    stats = tools.r3_univar(map="values", zones="layers", format="json").json
    return [(zone["zone"], zone["zone_label"]) for zone in stats]


def test_without_categories_the_labels_are_empty(tools):
    assert _labels(tools) == [(1, ""), (2, "")]


def test_r3_support_sets_categories(tools):
    result = tools.r3_support(map="layers", raster="names")

    assert "cats table for [layers] set to names" in result.stderr
    assert _labels(tools) == [(1, "lower"), (2, "upper")]


def test_the_category_table_is_written_to_the_3d_map(tools, session):
    tools.r3_support(map="layers", raster="names")

    env = gs.gisenv(env=session.env)
    cats = Path(env["GISDBASE"], env["LOCATION_NAME"], env["MAPSET"])
    lines = (cats / "grid3" / "layers" / "cats").read_text().splitlines()

    assert lines[0] == "# 2 categories"
    assert lines[-2:] == ["1:lower", "2:upper"]


def test_an_unknown_raster_map_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.r3_support(map="layers", raster="no_such_map")

    assert "no_such_map" in str(error.value)
    assert _labels(tools) == [(1, ""), (2, "")]


def test_a_3d_map_of_the_name_is_no_raster_map(tools):
    # The option names a 2D raster map; a 3D map of the name is not found.
    with pytest.raises(ToolError) as error:
        tools.r3_support(map="layers", raster="values")

    assert "values" in str(error.value)
    assert _labels(tools) == [(1, ""), (2, "")]
