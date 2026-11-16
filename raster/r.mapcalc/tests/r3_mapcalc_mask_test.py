"""Test that r3.mapcalc applies the 3D raster mask when it reads a map

The manual promises the behaviour of the 2D mask in r.mapcalc: the mask hides
cells of the maps that are read, so an expression of a constant is not
masked. The 2D raster mask does not apply to 3D maps.
"""

import pytest

from grass.tools import Tools

# 3 columns, 2 rows, 2 layers numbered 1 to 12, the lower layer holds 1 to 6.
REGION = {"s": 0, "n": 2, "w": 0, "e": 3, "b": 0, "t": 2, "res": 1, "res3": 1}
NUMBER = "6 * (depth() - 1) + 3 * (row() - 1) + col()"


@pytest.fixture
def tools(session_in_mapset):
    with Tools(session=session_in_mapset, consistent_return_value=True) as tools:
        tools.g_region(**REGION)
        tools.r3_mapcalc(expression=f"values = {NUMBER}")
        yield tools


def _counts(tools, name):
    """(cells, null cells, sum) of a 3D map, read without any mask

    r3.univar applies the 3D mask itself, so the mask is removed first.
    """
    tools.g_remove(type="raster_3d", name="RASTER3D_MASK", flags="f")
    stats = tools.r3_univar(map=name, format="json").json
    return stats["n"], stats["null_cells"], stats["sum"]


def test_existing_map_is_masked(tools):
    tools.r3_mask(map="values", maskvalues="7-12")
    tools.r3_mapcalc(expression="result = values * 1")
    assert _counts(tools, "result") == (6, 6, 21)


def test_constant_is_not_masked(tools):
    tools.r3_mask(map="values", maskvalues="7-12")
    tools.r3_mapcalc(expression="result = 5")
    assert _counts(tools, "result") == (12, 0, 60)


def test_constant_limited_to_the_mask_with_if(tools):
    # The example of the manual: the mask holds null in the masked cells and
    # 0 in the others.
    tools.r3_mask(map="values", maskvalues="7-12")
    tools.r3_mapcalc(expression="result = if(isnull(RASTER3D_MASK), null(), 200.0)")
    assert _counts(tools, "result") == (6, 6, 1200)


def test_2d_mask_has_no_effect(tools):
    tools.r_mapcalc(expression="first_column = if(col() == 1, null(), 1)")
    tools.r_mask(raster="first_column")
    tools.r3_mapcalc(expression="result = values * 1")
    tools.r_mask(flags="r")
    assert _counts(tools, "result") == (12, 0, 78)
