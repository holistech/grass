"""r.mapcalc tests for the region option (union and intersect)"""

import pytest

from grass.tools import Tools

# The two input maps overlap in the square from (2, 2) to (4, 4). The region
# of the mapset differs from both in extent and resolution, so a result that
# depends on it is told apart from one that depends on the maps.
MAPSET_REGION = {"n": 10, "s": 0, "w": 0, "e": 10, "res": 2}
EXTENTS = {
    "union": {"north": 6, "south": 0, "west": 0, "east": 6},
    "intersect": {"north": 4, "south": 2, "west": 2, "east": 4},
}
# Every input map is part of the expression, so that it enters the region,
# and isnull() keeps the cells outside the overlap.
USE_BOTH = "0 * (isnull(a) + isnull(b))"


@pytest.fixture
def tools(session_in_mapset):
    with Tools(session=session_in_mapset) as tools:
        tools.g_region(n=4, s=0, w=0, e=4, res=1)
        tools.r_mapcalc(expression="a = 1")
        tools.g_region(n=6, s=2, w=2, e=6, res=1)
        tools.r_mapcalc(expression="b = 2")
        tools.g_region(**MAPSET_REGION)
        yield tools


@pytest.mark.parametrize("region", ["union", "intersect"])
def test_region_of_the_mapset_is_kept(tools, region):
    """The manual says that the region of the mapset is not modified"""
    before = tools.g_region(flags="g").keyval
    tools.r_mapcalc(expression="result = a + b", region=region)
    assert tools.g_region(flags="g").keyval == before


@pytest.mark.parametrize("region", ["union", "intersect"])
def test_result_has_the_computed_extent(tools, region):
    tools.r_mapcalc(expression="result = a + b", region=region)
    info = tools.r_info(map="result", format="json")
    assert {key: info[key] for key in EXTENTS[region]} == EXTENTS[region]
    assert (info["nsres"], info["ewres"]) == (1, 1)


@pytest.mark.parametrize("region", ["union", "intersect"])
def test_coordinate_functions_use_the_computed_region(tools, region):
    """x(), ewres() and area() refer to the computed region, not to the mapset
    region

    area() reads the window of the gis library, the others the window of the
    raster library, so both have to hold the computed region.
    """
    tools.r_mapcalc(expression=f"west = x() + {USE_BOTH}", region=region)
    tools.r_mapcalc(expression=f"resolution = ewres() + {USE_BOTH}", region=region)
    tools.r_mapcalc(expression=f"cell_area = area() + {USE_BOTH}", region=region)
    assert tools.r_info(map="west", format="json")["min"] == (
        EXTENTS[region]["west"] + 0.5
    )
    assert tools.r_info(map="resolution", format="json")["max"] == 1
    assert tools.r_info(map="cell_area", format="json")["max"] == 1
