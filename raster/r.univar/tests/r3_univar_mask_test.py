"""Test that r3.univar respects the 3D raster mask set with r3.mask"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools

NUMBER = "(depth() - 1) * 6 + (row() - 1) * 3 + col()"


@pytest.fixture
def tools(tmp_path):
    """Tools in an XY project with a region of 2 rows, 3 columns, 2 layers

    The map values holds the voxel number 1 to 12 (1 to 6 in the lower
    layer), the map layers the number of the layer.
    """
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.g_region(s=0, n=2, w=0, e=3, b=0, t=2, res=1, res3=1)
        tools.r3_mapcalc(expression=f"values = {NUMBER}")
        tools.r3_mapcalc(expression="layers = depth()")
        yield tools


def _stats(tools, **options):
    return tools.r3_univar(map="values", format="json", **options).json


def test_without_a_mask_every_cell_counts(tools):
    stats = _stats(tools)

    assert (stats["n"], stats["null_cells"], stats["sum"]) == (12, 0, 78)


def test_r3_univar_respects_3d_mask(tools):
    tools.r3_mask(map="layers", maskvalues=2)

    stats = _stats(tools)

    # The upper layer (7 to 12) is masked out and counts as null cells.
    assert (stats["n"], stats["null_cells"], stats["cells"]) == (6, 6, 12)
    assert (stats["min"], stats["max"], stats["sum"]) == (1, 6, 21)


def test_the_shell_style_counts_masked_cells_as_null_cells(tools):
    tools.r3_mask(map="layers", maskvalues=2)

    out = tools.r3_univar(map="values", flags="g").stdout

    assert "n=6\n" in out
    assert "null_cells=6\n" in out


def test_with_zones_a_masked_cell_belongs_to_no_zone(tools):
    # As in r.univar, where the mask makes the zone of the cell null: the
    # zone of the masked layer gets no line, the other zone has no null cell.
    tools.r3_mask(map="layers", maskvalues=2)

    stats = _stats(tools, zones="layers")

    assert [(zone["zone"], zone["n"], zone["cells"]) for zone in stats] == [(1, 6, 6)]


def test_the_mask_follows_the_cells_of_the_current_region(tools):
    # The region covers only the upper layer of the maps, so its one layer
    # is the masked one; in the lower layer nothing is masked.
    tools.r3_mask(map="layers", maskvalues=2)

    tools.g_region(b=1, t=2)
    upper = _stats(tools)
    tools.g_region(b=0, t=1)
    lower = _stats(tools)

    assert (upper["n"], upper["null_cells"]) == (0, 6)
    assert (lower["n"], lower["null_cells"]) == (6, 0)


def test_the_mask_follows_a_finer_layer_resolution(tools):
    # Four layers of 0.5 in the region, two in each layer of the maps: the
    # upper two are masked out, the lower two hold 1 to 6 twice. Masking whole
    # tiles in the cell coordinates of the map would miss them.
    tools.r3_mask(map="layers", maskvalues=2)

    tools.g_region(tbres=0.5)
    stats = _stats(tools)

    assert (stats["n"], stats["null_cells"], stats["sum"]) == (12, 12, 42)


def test_removing_the_mask_counts_every_cell_again(tools):
    tools.r3_mask(map="layers", maskvalues=2)
    tools.g_remove(type="raster_3d", name="RASTER3D_MASK", flags="f")

    stats = _stats(tools)

    assert (stats["n"], stats["null_cells"]) == (12, 0)
