"""Test the files that t.rast.out.vtk writes

The VTK legacy format was measured on 18.10.2026 by exporting the maps of
conftest.py and reading the files: a header of four lines ("# vtk DataFile
Version 3.0", a title, ASCII and the dataset type), the dimensions, spacing and
origin of the grid, a CELL_DATA or POINT_DATA line with the number of values,
and the values in rows. The dimensions, the origin, the number of values and
the values themselves are derived from the region (two rows and three
columns of size 1 at the origin) and the maps.
"""

import re

import pytest

NULL = -99999.99


def _export(tools, name, directory, **options):
    directory.mkdir(exist_ok=True)
    return tools.t_rast_out_vtk(input=name, directory=str(directory), **options)


def _lines(directory, index):
    return (directory / f"{index:06d}_vt_in.vtk").read_text().splitlines()


def _values(lines):
    """The numbers after LOOKUP_TABLE, in file order"""
    start = lines.index("LOOKUP_TABLE default") + 1
    return [round(float(word), 6) for line in lines[start:] for word in line.split()]


def test_there_is_a_file_per_map_in_the_order_of_time(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out")

    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == [
        "000000_vt_in.vtk",
        "000001_vt_in.vtk",
        "000002_vt_in.vtk",
    ]


def test_the_header_describes_a_grid_of_cells(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out")

    lines = _lines(tmp_path / "out", 0)
    assert lines[:8] == [
        "# vtk DataFile Version 3.0",
        "GRASS 8 Export",
        "ASCII",
        "DATASET STRUCTURED_POINTS",
        "DIMENSIONS 4 3 1",
        "SPACING 1.000000 1.000000 0.000000",
        "ORIGIN 0.000000 0.000000 0.000000",
        "CELL_DATA 6",
    ]
    assert re.fullmatch(r"SCALARS vt_in_\d+ float 1", lines[8])


def test_the_values_are_those_of_the_maps(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out")

    assert _values(_lines(tmp_path / "out", 0)) == [10.0] * 6
    assert _values(_lines(tmp_path / "out", 1)) == [1.5, NULL, NULL] * 2
    assert _values(_lines(tmp_path / "out", 2)) == [3.0] * 6


def test_null_sets_the_value_of_cells_without_data(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out", null=-5)

    assert _values(_lines(tmp_path / "out", 1)) == [1.5, -5.0, -5.0] * 2


def test_where_selects_the_maps(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out", where="start_time < '2001-03-01'")

    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == [
        "000000_vt_in.vtk",
        "000001_vt_in.vtk",
    ]


def test_the_g_flag_fills_a_gap_with_a_map_without_data(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out", flags="g")

    directory = tmp_path / "out"
    assert len(list(directory.iterdir())) == 4
    assert _values(_lines(directory, 1)) == [1.5, NULL, NULL] * 2
    assert _values(_lines(directory, 2)) == [NULL] * 6
    assert _values(_lines(directory, 3)) == [3.0] * 6


def test_the_g_flag_ignores_where(tools, vtk_input, tmp_path):
    _export(
        tools, vtk_input, tmp_path / "out", flags="g", where="start_time < '2001-02-01'"
    )

    assert len(list((tmp_path / "out").iterdir())) == 4


def test_the_p_flag_writes_point_data(tools, vtk_input, tmp_path):
    _export(tools, vtk_input, tmp_path / "out", flags="p")

    lines = _lines(tmp_path / "out", 0)
    # One point per cell, at the cell centre: the grid has 3 x 2 points and
    # starts at the centre of the first cell
    assert lines[:8] == [
        "# vtk DataFile Version 3.0",
        "GRASS 8 Export",
        "ASCII",
        "DATASET STRUCTURED_POINTS",
        "DIMENSIONS 3 2 1",
        "SPACING 1.000000 1.000000 0.000000",
        "ORIGIN 0.500000 0.500000 0.000000",
        "POINT_DATA 6",
    ]
    assert _values(lines) == [10.0] * 6


@pytest.mark.parametrize(
    ("flags", "origin"),
    [
        ("", "ORIGIN 1000.000000 2000.000000 0.000000"),
        ("c", "ORIGIN 999.500000 1999.500000 0.000000"),
        ("p", "ORIGIN 1000.500000 2000.500000 0.000000"),
        ("pc", "ORIGIN 1000.000000 2000.000000 0.000000"),
    ],
)
def test_the_c_flag_subtracts_the_centre_of_the_default_region(
    tools, vtk_input, tmp_path, flags, origin
):
    # r.out.vtk (writeascii.c, main.c): the origin is the south-west corner
    # of the region, with -p the centre of that cell (+ 0.5), and -c
    # subtracts the centre of the default region of the project. The default
    # region of the test project is the one cell (0, 0) to (1, 1), so -c
    # subtracts 0.5 in both directions.
    tools.g_region(n=2002, s=2000, w=1000, e=1003, res=1)
    try:
        _export(
            tools,
            vtk_input,
            tmp_path / "out",
            flags=flags or None,
            where="start_time < '2001-02-01'",
        )
    finally:
        tools.g_region(n=2, s=0, w=0, e=3, res=1)

    assert origin in _lines(tmp_path / "out", 0)


def test_an_elevation_map_makes_a_surface_of_polygons(tools, vtk_input, tmp_path):
    _export(
        tools,
        vtk_input,
        tmp_path / "out",
        elevation="vt_e",
        where="start_time >= '2001-04-01'",
    )

    lines = _lines(tmp_path / "out", 0)
    assert lines[3] == "DATASET POLYDATA"
    # A point on each cell centre with the elevation as z, row by row from the
    # south, and one quadrilateral between four neighbouring points
    assert lines[4:11] == [
        "POINTS 6 float",
        "0.500000000000 0.500000000000 201.000000000000",
        "1.500000000000 0.500000000000 202.000000000000",
        "2.500000000000 0.500000000000 203.000000000000",
        "0.500000000000 1.500000000000 101.000000000000",
        "1.500000000000 1.500000000000 102.000000000000",
        "2.500000000000 1.500000000000 103.000000000000",
    ]
    assert lines[11:14] == ["POLYGONS 2 10", "4 0 1 4 3 ", "4 1 2 5 4 "]
    assert _values(lines) == [3.0] * 6


def test_the_temporary_map_is_removed(tools, vtk_input, tmp_path):
    before = tools.g_list(type="raster").stdout.split()

    _export(tools, vtk_input, tmp_path / "out", flags="g")

    assert tools.g_list(type="raster").stdout.split() == before


def test_null_applies_to_a_surface_as_well(tools, vtk_input, tmp_path):
    _export(
        tools,
        vtk_input,
        tmp_path / "out",
        elevation="vt_e",
        null=-5,
        where="start_time >= '2001-02-01' and start_time < '2001-03-01'",
    )

    assert _values(_lines(tmp_path / "out", 0)) == [1.5, -5.0, -5.0] * 2
