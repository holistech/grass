"""Test that 3D raster maps stored with a reduced precision read back

A 3D raster map can keep fewer mantissa bits than its type holds: r3.mask
stores the mask with precision 0, r3.in.ascii has an option for it, and the
variable RASTER3D_PRECISION sets it for every tool that writes a map. The
library packs the values of such a tile into fewer bytes than the full
precision takes, and the number of bytes depends on the null cells in the
tile. zlib compresses the packed tile when that makes it smaller. Reading
it back has to accept that zlib expands it to fewer bytes than a tile of
full precision takes.
"""

import os
import struct
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

# The reproduction: the size of the map (rows, columns, layers) and the
# expression of the map whose cells of value 1 the mask hides. With the
# default tiles a map this small is one tile. zlib does not shrink the mask
# of 2 x 3 x 2 or 2 x 2 x 2 cells, which therefore read back before as
# well, and shrinks those of 3 x 3 x 3 cells and more, which did not
# (measured 2026-11-06 with the library before the change).
MASK_CASES = {
    "2x3x2-layer": (2, 3, 2, "depth() == 2"),
    "2x3x2-chequered": (2, 3, 2, "(row() + col() + depth()) % 2"),
    "3x5x3-chequered": (3, 5, 3, "(row() + col() + depth()) % 2"),
    "3x5x3-layer": (3, 5, 3, "depth() == 2"),
    "3x5x3-column": (3, 5, 3, "col() == 2"),
    "3x4x3-chequered": (3, 4, 3, "(row() + col() + depth()) % 2"),
    "3x3x3-chequered": (3, 3, 3, "(row() + col() + depth()) % 2"),
    "2x2x2-chequered": (2, 2, 2, "(row() + col() + depth()) % 2"),
    "4x4x4-chequered": (4, 4, 4, "(row() + col() + depth()) % 2"),
    "3x5x3-random": (3, 5, 3, "rand(0, 2)"),
}

# The size of the test map: 6 rows, 10 columns and 4 layers.
ROWS, COLUMNS, LAYERS = 6, 10, 4

# A precision below the full one of each type.
REDUCED = [
    ("float", "0"),
    ("float", "10"),
    ("float", "22"),
    ("double", "0"),
    ("double", "23"),
    ("double", "51"),
]


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


def _read(tools, name, flags="h"):
    """The cells of a map with enough decimal places to give each value of
    the map exactly
    """
    return _cells(tools.r3_out_ascii(input=name, flags=flags, precision=17).text)


def _input_values(with_nulls, repeating=False):
    """The values of the test map in the order of r3.in.ascii and
    r3.out.ascii -h: layers from the bottom, rows from the north, columns
    from the west

    Each cell has a value of its own, or with repeating one of five
    values, so that zlib shrinks the larger tiles of a map of reduced
    precision.
    """

    def value(row, column, layer):
        if repeating:
            return round(1 + (row + 2 * column + 3 * layer) % 5 / 7, 6)
        return round(row + column / 7 + layer / 13, 6)

    return [
        None
        if with_nulls and (row + column + layer) % 3 == 0
        else value(row, column, layer)
        for layer in range(1, LAYERS + 1)
        for row in range(1, ROWS + 1)
        for column in range(1, COLUMNS + 1)
    ]


def _as_type(value, cell_type):
    """The value that a map of the type keeps at full precision"""
    if value is None or cell_type == "double":
        return value
    return struct.unpack("f", struct.pack("f", value))[0]


def _import(tools, tmp_path, name, values, **options):
    """Import the values into the map of the name"""
    lines = [
        f"north: {ROWS}",
        "south: 0",
        f"east: {COLUMNS}",
        "west: 0",
        f"top: {LAYERS}",
        "bottom: 0",
        f"rows: {ROWS}",
        f"cols: {COLUMNS}",
        f"levels: {LAYERS}",
        *("*" if value is None else str(value) for value in values),
    ]
    path = Path(tmp_path) / f"{name}.txt"
    path.write_text("\n".join(lines) + "\n")
    tools.g_region(s=0, n=ROWS, w=0, e=COLUMNS, b=0, t=LAYERS, res=1, res3=1)
    tools.r3_in_ascii(input=path, output=name, **options)


@pytest.mark.parametrize("name", MASK_CASES)
def test_mask_of_compressible_tiles_is_readable(tools, name):
    rows, columns, layers, expression = MASK_CASES[name]
    tools.g_region(s=0, n=rows, w=0, e=columns, b=0, t=layers, res=1, res3=1)
    tools.r3_mapcalc(expression=f"m = {expression}", seed=7)
    values = _read(tools, "m")
    tools.r3_mask(map="m", maskvalues=1)

    # r3.mask writes a null for a cell to hide and 0 for the others.
    assert _read(tools, "RASTER3D_MASK") == [
        None if value == 1 else 0 for value in values
    ]
    assert _read(tools, "m", flags="hm") == [
        None if value == 1 else value for value in values
    ]


@pytest.mark.parametrize("with_nulls", [False, True], ids=["no-nulls", "nulls"])
@pytest.mark.parametrize("tiles", ["default", "8x8x2"])
@pytest.mark.parametrize(("cell_type", "precision"), REDUCED)
def test_reduced_precision_map_is_readable(
    tools, tmp_path, cell_type, precision, tiles, with_nulls
):
    # zlib is the only compression of 3D raster maps. Tiles of 8 x 8 x 2
    # cells cut the map into four tiles, all clipped by its edges. zlib
    # shrinks at least one tile of the map in every case (each case failed
    # with the library before the change, 2026-11-06). The values are
    # compared with the same map in tiles of 2 x 2 x 2 cells, which zlib
    # does not shrink (they read back with the library before the change):
    # the test is about reading a tile that zlib shrank, while the values
    # that a reduced precision keeps are the subject of the tests of the 3D
    # raster library.
    values = _input_values(with_nulls, repeating=True)
    options = {"type": cell_type, "precision": precision, "compression": "zip"}
    _import(tools, tmp_path, "small_tiles", values, tiledimension="2x2x2", **options)
    _import(tools, tmp_path, "compressed", values, tiledimension=tiles, **options)

    stored = _read(tools, "small_tiles")
    assert _read(tools, "compressed") == stored
    assert [value is None for value in stored] == [value is None for value in values]


@pytest.mark.parametrize(("cell_type", "precision"), REDUCED)
def test_zeros_of_reduced_precision_map_read_back(
    tools, tmp_path, cell_type, precision
):
    # Zero has no set bit in any byte order, so the map keeps it whatever
    # the precision. The nulls make the tile one with a null bit vector, as
    # in a mask.
    values = [None if value is None else 0 for value in _input_values(True)]
    _import(
        tools,
        tmp_path,
        "zeros",
        values,
        type=cell_type,
        precision=precision,
        compression="zip",
    )

    assert _read(tools, "zeros") == values


@pytest.mark.parametrize("with_nulls", [False, True], ids=["no-nulls", "nulls"])
@pytest.mark.parametrize("cell_type", ["float", "double"])
@pytest.mark.parametrize(
    ("compression", "tiles"),
    [("zip", "default"), ("zip", "2x2x2"), ("none", "default")],
    ids=["full-precision", "small-tiles", "uncompressed"],
)
def test_full_precision_and_uncompressed_tiles_read_as_before(
    tools, tmp_path, compression, tiles, cell_type, with_nulls
):
    # These maps read back before the change as well: a tile of full
    # precision expands to the length that the reader asks for, and tiles of
    # 2 x 2 x 2 cells and maps without compression are stored without zlib.
    values = _input_values(with_nulls)
    _import(
        tools,
        tmp_path,
        "full",
        values,
        type=cell_type,
        precision="max",
        compression=compression,
        tiledimension=tiles,
    )

    assert _read(tools, "full") == [_as_type(value, cell_type) for value in values]
