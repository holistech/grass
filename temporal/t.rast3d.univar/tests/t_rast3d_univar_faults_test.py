"""Test zones and the 3D raster mask in t.rast3d.univar

The maps uv3_1 to uv3_3 of the dataset uv3_a are listed in conftest.py:
uv3_1 holds the voxel number 1 to 12, 1 to 6 in the lower layer.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import small_region
from grass.temporal.testing.readback import message
from grass.tools import ToolError

FIRST_MAP = "start_time < '2001-01-02'"


def _rows(result):
    lines = result.stdout.splitlines()
    header = lines[0].split("|")
    return [dict(zip(header, line.split("|"), strict=True)) for line in lines[1:]]


def _maps_and_datasets(tools):
    return (
        tools.g_list(type="raster_3d", flags="m").stdout,
        tools.t_list(type="str3ds").stdout,
    )


def test_zone_labels(tools, values):
    # r3.support copies the category table of a 2D raster map to the zones
    # map; t.rast3d.univar prints the labels in the column label.
    tools.r3_mapcalc(expression="uv3_named_zones = depth()", overwrite=True)
    tools.r_mapcalc(expression="uv3_zone_names = 1", overwrite=True)
    tools.r_category(
        map="uv3_zone_names", separator=":", rules=StringIO("1:lower\n2:upper\n")
    )
    tools.r3_support(map="uv3_named_zones", raster="uv3_zone_names")

    rows = _rows(
        tools.t_rast3d_univar(input=values, zones="uv3_named_zones", where=FIRST_MAP)
    )
    data = tools.t_rast3d_univar(
        input=values, zones="uv3_named_zones", where=FIRST_MAP, format="json"
    ).json

    assert [(row["zone"], row["label"], row["sum"]) for row in rows] == [
        ("1", "lower", "21"),
        ("2", "upper", "57"),
    ]
    assert [(item["zone"], item["zone_label"]) for item in data] == [
        (1, "lower"),
        (2, "upper"),
    ]


def test_float_zones_are_refused(tools, values, tmp_path):
    # uv3_3 holds the voxel number divided by 2, so half of its values are
    # no whole numbers. Like t.rast.univar with a zones map that is not of
    # type CELL, the tool ends before it opens the output file, where the
    # column names would be the first line.
    before = _maps_and_datasets(tools)
    output = tmp_path / "stats.txt"

    with pytest.raises(ToolError) as error:
        tools.t_rast3d_univar(input=values, zones="uv3_3", output=output)

    text = message(error.value)
    assert "Zoning 3D raster map <uv3_3> must hold whole numbers" in text
    assert "3D raster map <uv3_3> used for zoning holds the value 0.5" in text
    assert not output.exists()
    assert _maps_and_datasets(tools) == before


def test_zones_of_whole_numbers_in_a_double_map_are_accepted(tools, values):
    tools.r3_mapcalc(expression="uv3_column_zones = col() * 1.0", overwrite=True)

    rows = _rows(
        tools.t_rast3d_univar(input=values, zones="uv3_column_zones", where=FIRST_MAP)
    )

    assert [(row["zone"], row["sum"]) for row in rows] == [
        ("1", "22"),
        ("2", "26"),
        ("3", "30"),
    ]


def test_zone_without_cell_gets_no_line(tools, values):
    # The zones map has three layers, the region the lower two of them: zone
    # 3 has no cell in the region and gets no line.
    previous = small_region(tools, 2, 3, depths=3)
    try:
        tools.r3_mapcalc(expression="uv3_deep_zones = depth()", overwrite=True)
    finally:
        tools.g_region(**previous)

    rows = _rows(
        tools.t_rast3d_univar(input=values, zones="uv3_deep_zones", where=FIRST_MAP)
    )

    assert [(row["zone"], row["non_null_cells"]) for row in rows] == [
        ("1", "6"),
        ("2", "6"),
    ]


def test_the_3d_mask_is_respected(tools, values):
    # The mask removes the upper layer (maskvalues=2), so only the voxels 1
    # to 6 of the lower layer are counted; the others are null cells.
    tools.r3_mapcalc(expression="uv3_layers = depth()", overwrite=True)
    tools.r3_mask(map="uv3_layers", maskvalues=2)
    try:
        rows = _rows(tools.t_rast3d_univar(input=values, where=FIRST_MAP))
    finally:
        tools.g_remove(type="raster_3d", name="RASTER3D_MASK", flags="f")

    assert [(row["non_null_cells"], row["null_cells"], row["sum"]) for row in rows] == [
        ("6", "6", "21")
    ]
