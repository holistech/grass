"""Test that the 3D raster mask hides the cells at its location in any region

The tools read a 3D raster map tile by tile in the cells of the map and
resample them into the current region. The mask has to be looked up at the
location of the cells of the map, so that the current region changes which
cells are shown but not which are masked.
"""

import math
import os
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

DATA = Path(__file__).parent / "data"

# The map of the reproduction: 3 columns, 2 rows, 2 layers numbered 1 to 12,
# the lower layer holds 1 to 6.
SMALL_REGION = {"s": 0, "n": 2, "w": 0, "e": 3, "b": 0, "t": 2, "res": 1, "res3": 1}
SMALL_NUMBER = "6 * (depth() - 1) + 3 * (row() - 1) + col()"

# A map of 4 columns, 4 rows, 3 layers whose value tells its cell, and a
# mask over it, so that a wrong cell of the mask shows. A chequered mask
# looks the same from the other side along an odd number of cells, so one
# more cell is masked: a lookup with north and south, east and west, or top
# and bottom swapped finds other cells (checked 2026-11-05 with three builds
# of the library that each mirror one axis of the lookup: four of the five
# tests fail with each).
GRID = {"s": 0, "n": 4, "w": 0, "e": 4, "b": 0, "t": 3, "res": 1, "res3": 1}
GRID_NUMBER = "100 * depth() + 10 * row() + col()"
MASKED = "(row() + col() + depth()) % 2 || (row() == 1 && col() == 2 && depth() == 1)"

# The same numbers and mask on a map of 8 columns, 8 rows, 6 layers, whose
# mask is cut into eight tiles of 4 x 4 x 3 cells that zlib shrinks (the
# mask did not read back with the library before 2026-11-06), so that a
# region of another resolution looks the mask up across the borders of
# compressed tiles.
LARGE_GRID = {"s": 0, "n": 8, "w": 0, "e": 8, "b": 0, "t": 6, "res": 1, "res3": 1}
LARGE_GRID_TILES = "4x4x3"

# Regions whose cell centres lie inside the cells of the map, never on their
# edges, where the cell that a lookup finds would depend on rounding.
OTHER_REGIONS = {
    "finer": {"s": 0, "n": 4, "w": 0, "e": 4, "b": 0, "t": 3, "res": 0.5, "res3": 0.5},
    "coarser": {
        "s": 0,
        "n": 4.5,
        "w": 0,
        "e": 4.5,
        "b": 0,
        "t": 3,
        "res": 1.5,
        "res3": 1.5,
    },
    "shifted": {
        "s": -0.75,
        "n": 4.25,
        "w": -0.75,
        "e": 4.25,
        "b": -0.75,
        "t": 3.25,
        "res": 1,
        "res3": 1,
    },
}


@pytest.fixture
def session(tmp_path):
    """A session in an XY project of its own"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        yield session


@pytest.fixture
def tools(session):
    with Tools(session=session, consistent_return_value=True) as tools:
        yield tools


def _cells(text):
    """The values of r3.out.ascii -h output, None for a null cell"""
    return [None if word == "*" else float(word) for word in text.split()]


def _region_cells(region):
    """The centres (x, y, z) of the cells of a region in the order of
    r3.out.ascii: layers from the bottom, rows from the north, columns from
    the west
    """
    columns = round((region["e"] - region["w"]) / region["res"])
    rows = round((region["n"] - region["s"]) / region["res"])
    layers = round((region["t"] - region["b"]) / region["res3"])
    return [
        (
            region["w"] + (column + 0.5) * region["res"],
            region["n"] - (row + 0.5) * region["res"],
            region["b"] + (layer + 0.5) * region["res3"],
        )
        for layer in range(layers)
        for row in range(rows)
        for column in range(columns)
    ]


def _expected_cell(grid, x, y, z):
    """The value shown at (x, y, z) over a map of GRID_NUMBER on the grid:
    null outside the map and where MASKED is true, else the value of the
    cell of the map there
    """
    column = math.floor(x - grid["w"]) + 1
    row = math.floor(grid["n"] - y) + 1
    depth = math.floor(z - grid["b"]) + 1
    columns = round(grid["e"] - grid["w"])
    rows = round(grid["n"] - grid["s"])
    layers = round(grid["t"] - grid["b"])
    if not (1 <= column <= columns and 1 <= row <= rows and 1 <= depth <= layers):
        return None
    if (row + column + depth) % 2 or (row, column, depth) == (1, 2, 1):
        return None
    return float(100 * depth + 10 * row + column)


def _expected_grid_cell(x, y, z):
    """The value shown at (x, y, z) over the map of GRID"""
    return _expected_cell(GRID, x, y, z)


def _grid_maps(tools, tiledimension=None):
    """Create the map values and the mask in the current region

    Both maps get tiles of the given dimension, or the default tiles of the
    library, one tile for maps this small.
    """
    if tiledimension:
        tools.r3_mapcalc(expression=f"whole = {GRID_NUMBER}")
        tools.r3_retile(input="whole", output="values", tiledimension=tiledimension)
        tools.r3_mapcalc(expression=f"whole_masked = {MASKED}")
        tools.r3_retile(
            input="whole_masked", output="masked", tiledimension=tiledimension
        )
    else:
        tools.r3_mapcalc(expression=f"values = {GRID_NUMBER}")
        tools.r3_mapcalc(expression=f"masked = {MASKED}")
    tools.r3_mask(map="masked", maskvalues=1)


def test_mask_with_shifted_depth_region(tools):
    # Two layers of 0.5 in the region in each layer of the map: the upper
    # two lie in the masked layer of the map. Before, the layer numbers 0
    # and 1 of the map were read as layers of the region to look up the
    # mask, so both found the lower layer of the mask and nothing was masked.
    tools.g_region(**SMALL_REGION)
    tools.r3_mapcalc(expression=f"values = {SMALL_NUMBER}")
    tools.r3_mask(map="values", maskvalues="7-12")
    tools.g_region(tbres=0.5, flags="3")

    text = tools.r3_out_ascii(input="values", flags="hm").text

    lower = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert _cells(text) == lower + lower + [None] * 12

    tools.r3_to_rast(input="values", output="slice", flags="m")
    slices = [
        tools.r_univar(map=f"slice_0000{layer}", format="json").json
        for layer in range(1, 5)
    ]
    assert [(info["n"], info["null_cells"]) for info in slices] == [
        (6, 0),
        (6, 0),
        (0, 6),
        (0, 6),
    ]
    assert [(info["min"], info["max"]) for info in slices[:2]] == [(1, 6), (1, 6)]


def test_mask_with_region_equal_to_map_is_unchanged(tools):
    # The output was recorded before the mask was looked up at the cells of
    # the map instead of the cells of the region; with the region equal to
    # the map both are the same cells. The tiles of 2 x 2 x 2 cells cut the
    # map of 5 x 3 x 3 cells into tiles of every size, so the loop over the
    # cells of a tile that the map clips is part of the comparison.
    tools.g_region(**{**GRID, "n": 3, "e": 5})
    _grid_maps(tools, tiledimension="2x2x2")

    text = tools.r3_out_ascii(input="values", flags="m").stdout

    assert text == (DATA / "region_equal_to_map.ascii").read_text()


@pytest.mark.parametrize("name", OTHER_REGIONS)
def test_mask_with_other_resolution(tools, name):
    region = OTHER_REGIONS[name]
    tools.g_region(**GRID)
    _grid_maps(tools)
    tools.g_region(**region)

    text = tools.r3_out_ascii(input="values", flags="hm").text

    assert _cells(text) == [
        _expected_grid_cell(*cell) for cell in _region_cells(region)
    ]


# Regions of another resolution over LARGE_GRID, with cell centres inside
# the cells of the map as in OTHER_REGIONS.
LARGE_REGIONS = {
    "finer": {**LARGE_GRID, "res": 0.5, "res3": 0.5},
    "coarser": {**LARGE_GRID, "n": 9, "e": 9, "res": 1.5, "res3": 1.5},
}


@pytest.mark.parametrize("name", LARGE_REGIONS)
def test_mask_of_several_compressed_tiles_with_other_resolution(tools, name):
    region = LARGE_REGIONS[name]
    tools.g_region(**LARGE_GRID)
    _grid_maps(tools, tiledimension=LARGE_GRID_TILES)
    tools.g_region(**region)

    text = tools.r3_out_ascii(input="values", flags="hm").text

    assert _cells(text) == [
        _expected_cell(LARGE_GRID, *cell) for cell in _region_cells(region)
    ]
