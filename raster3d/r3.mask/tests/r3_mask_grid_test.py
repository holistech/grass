"""Test that the 3D raster mask applies at the location of each value read

A tool reads a 3D raster map either in the cells of the current region,
resampled from the map, or at a location (r3.cross.rast). A value read in a
cell of the current region is masked when the mask is null at the centre of
that cell; a value read at a location is masked when the mask is null at
that location. When the mask lies on the grid of the map, this masks the
same cells as the mask at the centres of the cells of the map, which the
library used before. When it lies on another grid, finer or offset, the two
differ inside a cell of the map.
"""

import os
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

DATA = Path(__file__).parent / "data"


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
    """The values of r3.out.ascii -h or r.out.ascii -h output, None for a
    null cell
    """
    return [None if word == "*" else float(word) for word in text.split()]


def _layer_centres(region):
    """The heights of the centres of the layers of a region, from the bottom"""
    layers = round((region["t"] - region["b"]) / region["tbres"])
    return [region["b"] + (layer + 0.5) * region["tbres"] for layer in range(layers)]


def _read_r3_out_ascii(tools, region):
    return _cells(tools.r3_out_ascii(input="values", flags="hm").text)


def _read_r3_to_rast(tools, region):
    tools.r3_to_rast(input="values", output="slice", flags="m")
    layers = len(_layer_centres(region))
    cells = []
    for layer in range(1, layers + 1):
        cells += _cells(tools.r_out_ascii(input=f"slice_{layer:05d}", flags="h").text)
    return cells


def _read_r3_mapcalc(tools, region):
    tools.r3_mapcalc(expression="copied = values")
    return _cells(tools.r3_out_ascii(input="copied", flags="h").text)


def _read_r3_cross_rast(tools, region):
    # One cross section at the height of the centre of each layer of the
    # region, so that its cells lie where the cells of the region lie.
    cells = []
    for layer, height in enumerate(_layer_centres(region)):
        tools.r_mapcalc(expression=f"height_{layer} = {height}")
        tools.r3_cross_rast(
            input="values",
            elevation=f"height_{layer}",
            output=f"cross_{layer}",
            flags="m",
        )
        cells += _cells(tools.r_out_ascii(input=f"cross_{layer}", flags="h").text)
    return cells


def _read_r3_univar(tools, region):
    info = tools.r3_univar(map="values", flags="g").keyval
    return (info["n"], info["null_cells"], info["sum"])


# The tools that read a 3D raster map with the mask, and how to get the
# cells they show in the order of r3.out.ascii: layers from the bottom, rows
# from the north, columns from the west. r3.univar applies the mask on its
# own; it shows its statistics of these cells instead.
READERS = {
    "r3.out.ascii": _read_r3_out_ascii,
    "r3.to.rast": _read_r3_to_rast,
    "r3.mapcalc": _read_r3_mapcalc,
    "r3.cross.rast": _read_r3_cross_rast,
    "r3.univar": _read_r3_univar,
}


def _shown(tool, cells):
    """What the tool shows for these cells"""
    if tool != "r3.univar":
        return cells
    values = [cell for cell in cells if cell is not None]
    return (len(values), len(cells) - len(values), sum(values))


# A map of one cell with two layers, 1 in z 0-1 and 2 in z 1-2, and a mask
# from a map of four layers of 0.5 that is null only in its third layer,
# z 1.0-1.5. The region has the four layers of 0.5.
FINER_MAP = {"s": 0, "n": 1, "w": 0, "e": 1, "b": 0, "t": 2, "res": 1, "res3": 1}
FINER_REGION = {**FINER_MAP, "tbres": 0.5}


@pytest.mark.parametrize("tool", READERS)
def test_finer_mask_grid(tools, tool):
    # The centres of the cells of the region lie at z 0.25, 0.75, 1.25 and
    # 1.75, in the map cells of value 1, 1, 2 and 2. Only z 1.25 lies in the
    # null of the mask: 1 1 * 2. The mask at the centre of the upper cell of
    # the map, z 1.5, is not null, so before nothing was masked: 1 1 2 2.
    tools.g_region(**FINER_MAP, tbres=1, flags="3")
    tools.r3_mapcalc(expression="values = depth()")
    tools.g_region(**FINER_REGION, flags="3")
    tools.r3_mapcalc(expression="fine = depth()")
    tools.r3_mask(map="fine", maskvalues=3)

    shown = READERS[tool](tools, FINER_REGION)

    assert shown == _shown(tool, [1.0, 1.0, None, 2.0])


# A map of one row of two cells, 1 in x 0-1 and 2 in x 1-2, and a mask from
# a map of the same resolution shifted west by 0.7, so that its second cell,
# x 0.3-1.3, is the null of the mask. The region has cells of 0.5: two rows
# of four.
OFFSET_MAP = {"s": 0, "n": 1, "w": 0, "e": 2, "b": 0, "t": 1, "res": 1, "res3": 1}
OFFSET_MASK = {**OFFSET_MAP, "w": -0.7, "e": 2.3}
OFFSET_REGION = {**OFFSET_MAP, "res": 0.5, "res3": 0.5, "tbres": 1}


@pytest.mark.parametrize("tool", READERS)
def test_offset_mask_grid(tools, tool):
    # The centres of the cells of a row lie at x 0.25, 0.75, 1.25 and 1.75,
    # in the map cells of value 1, 1, 2 and 2. x 0.75 and 1.25 lie in the
    # null of the mask: 1 * * 2 in each row. The mask at the centres of the
    # cells of the map, x 0.5 and 1.5, is null only in the first, so before
    # each row showed * * 2 2.
    tools.g_region(**OFFSET_MAP, tbres=1)
    tools.r3_mapcalc(expression="values = col()")
    tools.g_region(**OFFSET_MASK, tbres=1)
    tools.r3_mapcalc(expression="shifted = col()")
    tools.r3_mask(map="shifted", maskvalues=2)
    tools.g_region(**OFFSET_REGION)

    shown = READERS[tool](tools, OFFSET_REGION)

    assert shown == _shown(tool, [1.0, None, None, 2.0] * 2)


# A map of 4 rows, 5 columns and 3 layers whose value tells its cell, under
# a chequered mask on the grid of the map, in tiles of 2 x 2 x 2 cells.
SAME_GRID = {"s": 0, "n": 4, "w": 0, "e": 5, "b": 0, "t": 3, "res": 1, "res3": 1}
SAME_GRID_REGIONS = {
    "map": {**SAME_GRID, "tbres": 1},
    "half": {**SAME_GRID, "res": 0.5, "res3": 0.5, "tbres": 0.5},
}


def same_grid_output(tools, name):
    """The output of each tool that reads the map of SAME_GRID with the
    mask in the region of the given name, as one text
    """
    tools.g_region(**SAME_GRID, tbres=1, flags="3")
    tools.r3_mapcalc(expression="whole = 100 * depth() + 10 * row() + col()")
    tools.r3_retile(input="whole", output="values", tiledimension="2x2x2")
    tools.r3_mapcalc(expression="whole_masked = (row() + col() + depth()) % 2")
    tools.r3_retile(input="whole_masked", output="masked", tiledimension="2x2x2")
    tools.r3_mask(map="masked", maskvalues=1)
    region = SAME_GRID_REGIONS[name]
    tools.g_region(**region, flags="3")

    parts = [
        "r3.out.ascii -m",
        tools.r3_out_ascii(input="values", flags="m").stdout,
        "r3.univar -g",
        tools.r3_univar(map="values", flags="g").stdout,
    ]
    for tool in ("r3.to.rast", "r3.mapcalc", "r3.cross.rast"):
        cells = READERS[tool](tools, region)
        parts += [
            tool,
            " ".join("*" if cell is None else f"{cell:g}" for cell in cells),
        ]
    return "\n".join(parts) + "\n"


@pytest.mark.parametrize("name", SAME_GRID_REGIONS)
def test_same_grid_output_is_unchanged(tools, name):
    # The output was recorded before the mask applied at the location of
    # each value read; on the grid of the map the mask is null at the
    # location of a value exactly where it is null at the centre of the
    # cell of the map that holds it.
    text = same_grid_output(tools, name)

    assert text == (DATA / f"same_grid_{name}.ascii").read_text()


# A map of one row of ten cells of 0.1 whose value is its column, 1 to 10,
# and a region of the same resolution shifted east by half a cell, so that
# the centres of the cells of the region lie on the borders of the cells of
# the map. Which cell of the map a centre falls into then depends on the
# rounding of the arithmetic: 0.3 falls into the cell of value 3 and 0.4
# into the cell of value 5, so the region shows 3 twice and never 4.
BORDER_MAP = {"s": 0, "n": 0.1, "w": 0, "e": 1, "b": 0, "t": 0.1, "res": 0.1}
BORDER_REGION = {**BORDER_MAP, "w": 0.05, "e": 1.05}
BORDER_SHOWN = [2.0, 3.0, 3.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, None]


@pytest.mark.parametrize("tool", ["r3.out.ascii", "r3.mapcalc", "r3.univar"])
@pytest.mark.parametrize("masked", [4, 5])
def test_mask_on_the_map_grid_with_centres_on_cell_borders(tools, tool, masked):
    # The mask lies on the grid of the map and is null in the cell of the
    # value masked. The value and the mask of a cell of the region come from
    # the same location, so exactly the cells of the region that show that
    # value are hidden: none for 4, the fourth for 5. Before, the mask was
    # asked at a centre computed another way, which fell into the
    # neighbouring cell on a border and hid the fourth cell for 4 and none
    # for 5 (measured 2026-11-06).
    tools.g_region(**BORDER_MAP, res3=0.1, tbres=0.1)
    tools.r3_mapcalc(expression="values = col()")
    tools.r3_mask(map="values", maskvalues=masked)
    tools.g_region(**BORDER_REGION, res3=0.1, tbres=0.1)
    assert _cells(tools.r3_out_ascii(input="values", flags="h").text) == BORDER_SHOWN

    shown = READERS[tool](tools, BORDER_REGION)

    hidden = [None if cell == masked else cell for cell in BORDER_SHOWN]
    assert shown == _shown(tool, hidden)


def test_map_open_for_writing_is_read_back_without_the_mask(tools):
    # r.to.rast3elev -m reads back the values of its output, a map open for
    # writing, to keep them where a later pair of maps leaves a cell alone.
    # The library applies the mask only to the values of a map open for
    # reading, as before; applying it here would write the chequered mask
    # into the cells of the lower layer that the second pair keeps.
    # 2 rows, 3 columns, 4 layers; the first pair writes 11 12 13 into the
    # layer z 1-2 that holds its height 1.5, the second 21 22 23 into the
    # layer z 2-3, and keeps the layers below by reading them back.
    tools.g_region(s=0, n=2, w=0, e=3, b=0, t=4, res=1, res3=1, tbres=1, flags="3")
    tools.r3_mapcalc(expression="chequered = (row() + col() + depth()) % 2")
    tools.r3_mask(map="chequered", maskvalues=1)
    tools.r_mapcalc(expression="in1 = 10 + col()")
    tools.r_mapcalc(expression="height1 = 1.5")
    tools.r_mapcalc(expression="in2 = 20 + col()")
    tools.r_mapcalc(expression="height2 = 2.5")

    tools.r_to_rast3elev(
        input="in1,in2", elevation="height1,height2", output="filled", flags="m"
    )

    cells = _cells(tools.r3_out_ascii(input="filled", flags="h").text)
    assert cells == (
        [None] * 6 + [11.0, 12.0, 13.0] * 2 + [21.0, 22.0, 23.0] * 2 + [None] * 6
    )
