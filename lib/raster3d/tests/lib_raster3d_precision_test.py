"""Test the values that 3D raster maps of a reduced precision keep

A 3D raster map can keep fewer mantissa bits than its type holds: the
option precision of r3.in.ascii and the variable RASTER3D_PRECISION set the
number of bits. The library packs each value of a compressed tile into
sign, exponent and the leading bits of the mantissa of its IEEE 754
representation in big-endian order (XDR), and clears the other bits: the
magnitude is truncated, not rounded. A float has 23 mantissa bits, a double
52; a map of full precision keeps all of them.

Maps of a reduced precision written by the releases before GRASS 8.6 on a
little-endian host hold other bits: the library handed the packing each
value in the byte order of the host, so it kept the least significant
bytes. The header of a map tells the two apart (Version 3 for the new
maps); a map of an older version reads as before.

The expected values are derived from the input values with struct: pack
the value in the byte order the packing sees, read the bytes as one
big-endian integer, clear all but the leading bits and unpack again.
"""

import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

DATA = Path(__file__).parent / "data"

# Values of both signs with set bits in nearly every byte of their mantissa
# (65536.0625 and -8.875 have few set bits). None is less than 0.001 in
# magnitude, so that 20 decimal places of r3.out.ascii give at least 17
# significant digits, which identify a double exactly. With 11 values in
# a row of 10 cells the values repeat with a shift from row to row; the
# repetition lets zlib shrink a tile of many cells.
VALUES = [
    0.1,
    -2.718281828459045,
    3.141592653589793,
    -1234.5678,
    0.3333333333333333,
    65536.0625,
    -0.001,
    7.38905609893065,
    -0.7071067811865476,
    299792.458,
    -8.875,
]

# The size of the test maps: 6 rows, 10 columns and 4 layers.
ROWS, COLUMNS, LAYERS = 6, 10, 4

# The struct code, the length in bytes and the number of bits of sign and
# exponent of each type.
LAYOUT = {"float": ("f", 4, 9), "double": ("d", 8, 12)}

# Precisions below the full one. The packing counts the lowest exponent bit
# of a float and the four lowest of a double as mantissa bits and branches
# on whether it keeps more than 8, 16, ... 48 bits besides the first byte;
# these precisions lie on both sides of each of these limits, including the
# limit of 32 bits of a double, and leave a rest of none and of some bits
# in a partial byte.
REDUCED = [
    *(("float", precision) for precision in (0, 1, 7, 8, 15, 16, 22)),
    *(("double", precision) for precision in (0, 4, 5, 12, 20, 28, 29, 36, 44, 51)),
]

# The maps written with the library before the change: their name and
# precision. See test_map_of_the_former_library_reads_as_before.
FORMER = {"float": ("former_float", 7), "double": ("former_double", 20)}

little_endian_only = pytest.mark.skipif(
    sys.byteorder != "little",
    reason="the files of the former maps were written on a little-endian host "
    "and keep the bytes of that byte order",
)


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


def _kept(value, cell_type, precision, byteorder=">"):
    """The value whose bytes in the byte order keep only their leading bits

    The packing keeps the leading bits of the bytes it gets: sign, exponent
    and precision mantissa bits if it gets big-endian bytes (byteorder
    ">"), the leading bits of the least significant bytes if it gets
    little-endian bytes ("<", the library before the change). None stands
    for a null cell, which stays null.
    """
    if value is None:
        return None
    code, length, sign_and_exponent = LAYOUT[cell_type]
    code = byteorder + code
    kept = sign_and_exponent + precision
    bits = int.from_bytes(struct.pack(code, value), "big")
    bits &= ~((1 << (8 * length - kept)) - 1)
    return struct.unpack(code, bits.to_bytes(length, "big"))[0]


def _as_type(value, cell_type):
    """The value that a map of the type keeps at full precision"""
    if value is None or cell_type == "double":
        return value
    return struct.unpack("f", struct.pack("f", value))[0]


def _values(cells, nulls):
    """The values of a map of the number of cells in the order of
    r3.in.ascii and r3.out.ascii -h, with a null in every seventh cell if
    nulls is set
    """
    return [
        None if nulls and index % 7 == 3 else VALUES[index % len(VALUES)]
        for index in range(cells)
    ]


def _cells(text):
    """The values of r3.out.ascii -h output, None for a null cell"""
    return [None if word == "*" else float(word) for word in text.split()]


def _read(tools, name, flags="h"):
    """The cells of a map from r3.out.ascii with 20 decimal places

    That gives each value exactly whose magnitude is at least 0.0001, as are
    VALUES and their truncations (the smallest is about 0.00098); smaller
    values lose digits or read as 0.
    """
    return _cells(tools.r3_out_ascii(input=name, flags=flags, precision=20).text)


def _import(tools, tmp_path, name, values, size=(ROWS, COLUMNS, LAYERS), **options):
    """Import the values into the map of the name"""
    rows, columns, layers = size
    lines = [
        f"north: {rows}",
        "south: 0",
        f"east: {columns}",
        "west: 0",
        f"top: {layers}",
        "bottom: 0",
        f"rows: {rows}",
        f"cols: {columns}",
        f"levels: {layers}",
        *("*" if value is None else repr(value) for value in values),
    ]
    path = Path(tmp_path) / f"{name}.txt"
    path.write_text("\n".join(lines) + "\n")
    tools.g_region(s=0, n=rows, w=0, e=columns, b=0, t=layers, res=1, res3=1)
    tools.r3_in_ascii(input=path, output=name, **options)


def _map_directory(session, name):
    """The directory of the 3D raster map of the name in the current mapset"""
    env = gs.gisenv(env=session.env)
    return Path(env["GISDBASE"]) / env["LOCATION_NAME"] / env["MAPSET"] / "grid3" / name


def _header(session, name):
    """The lines of the header file of the 3D raster map"""
    return (_map_directory(session, name) / "cellhd").read_text().splitlines()


def _copy_former(tools, session, cell_type, name):
    """Copy the former map of the type into the current mapset as name"""
    shutil.copytree(DATA / FORMER[cell_type][0], _map_directory(session, name))
    tools.g_region(s=0, n=4, w=0, e=5, b=0, t=3, res=1, res3=1)


def _former_output(session, name):
    """The output of r3.out.ascii as the test data recorded it"""
    return gs.read_command(
        "r3.out.ascii", input=name, flags="h", precision=17, env=session.env
    )


def test_derivation_gives_the_worked_examples():
    # Each step of the precision of a float adds one mantissa bit: 1.25 is
    # 1.01 and 8.875 is 1.000111 times 2 ** 3 in binary.
    assert [_kept(1.25, "float", precision) for precision in (0, 1, 2)] == [
        1.0,
        1.0,
        1.25,
    ]
    assert [_kept(8.875, "float", precision) for precision in range(7)] == [
        8.0,
        8.0,
        8.0,
        8.0,
        8.5,
        8.75,
        8.875,
    ]
    assert _kept(-8.875, "double", 4) == -8.5
    # On a little-endian host the bytes of 1.25 in a float are 00 00 a0 3f;
    # with precision 22 the packing kept all but the lowest bit of the last
    # byte, which is the second lowest exponent bit: 1.25 became 1.25 / 4.
    assert _kept(1.25, "float", 22, byteorder="<") == 0.3125


@pytest.mark.parametrize("with_nulls", [False, True], ids=["no-nulls", "nulls"])
@pytest.mark.parametrize("tiles", ["default", "2x2x2"])
@pytest.mark.parametrize(("cell_type", "precision"), REDUCED)
def test_reduced_precision_keeps_the_leading_mantissa_bits(
    tools, tmp_path, cell_type, precision, tiles, with_nulls
):
    # zlib shrinks the one tile of the map with the default tiles and does
    # not shrink the first tile in the file of the map with tiles of 2 x 2 x 2
    # cells (measured 2026-11-06 from the compression flag that leads each
    # tile in the cell file).
    values = _values(ROWS * COLUMNS * LAYERS, with_nulls)
    _import(
        tools,
        tmp_path,
        "reduced",
        values,
        type=cell_type,
        precision=precision,
        compression="zip",
        tiledimension=tiles,
    )

    assert _read(tools, "reduced") == [
        _kept(value, cell_type, precision) for value in values
    ]


@pytest.mark.parametrize(("cell_type", "precision"), [("float", 10), ("double", 36)])
def test_tile_of_nulls_only_reads_back(tools, tmp_path, cell_type, precision):
    # The tile of rows and columns 1 and 2 of the two bottom layers holds
    # nulls only, which the packing stores as a code of its own.
    values = [
        None if layer < 2 and row < 2 and column < 2 else VALUES[index % len(VALUES)]
        for index, (layer, row, column) in enumerate(
            (layer, row, column)
            for layer in range(4)
            for row in range(4)
            for column in range(4)
        )
    ]
    _import(
        tools,
        tmp_path,
        "nulls",
        values,
        size=(4, 4, 4),
        type=cell_type,
        precision=precision,
        compression="zip",
        tiledimension="2x2x2",
    )

    assert _read(tools, "nulls") == [
        _kept(value, cell_type, precision) for value in values
    ]


def test_environment_precision_truncates_like_the_option(tools, session, tmp_path):
    values = _values(ROWS * COLUMNS * LAYERS, nulls=True)
    options = {"type": "double", "compression": "zip"}
    _import(tools, tmp_path, "source", values, precision="max", **options)
    _import(tools, tmp_path, "option", values, precision=10, **options)
    env = session.env.copy()
    env["RASTER3D_PRECISION"] = "10"
    gs.run_command("r3.mapcalc", expression="environment = source", env=env)

    expected = [_kept(value, "double", 10) for value in values]
    assert _read(tools, "environment") == expected
    assert _read(tools, "option") == expected


EXACT_VALUES_SCRIPT = """\
import sys
from ctypes import POINTER, byref, c_double, cast

from grass.lib.gis import G_gisinit, G_mapset
from grass.lib.raster import DCELL_TYPE
from grass.lib.raster3d import (
    RASTER3D_USE_CACHE_DEFAULT,
    RASTER3D_Map,
    Rast3d_close,
    Rast3d_get_double,
    Rast3d_init_defaults,
    Rast3d_is_null_value_num,
    Rast3d_open_cell_old,
)

G_gisinit("test")
Rast3d_init_defaults()
handle = Rast3d_open_cell_old(
    sys.argv[1], G_mapset(), None, DCELL_TYPE, RASTER3D_USE_CACHE_DEFAULT
)
if not handle:
    sys.exit("Rast3d_open_cell_old failed")
map_ptr = cast(handle, POINTER(RASTER3D_Map))
region = map_ptr.contents.region
for depth in range(region.depths):
    for row in range(region.rows):
        for col in range(region.cols):
            value = c_double(Rast3d_get_double(map_ptr, col, row, depth))
            null = Rast3d_is_null_value_num(byref(value), DCELL_TYPE)
            print("*" if null else repr(value.value))
if not Rast3d_close(map_ptr):
    sys.exit("Rast3d_close failed")
"""


def _exact_values(session, tmp_path, name):
    """The values of the 3D raster map read through the library, exactly

    The script runs in a process of its own and prints repr() of each value
    as a double, in the order of r3.out.ascii -h, None for a null cell.
    """
    script = tmp_path / "exact_values.py"
    script.write_text(EXACT_VALUES_SCRIPT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), name],
        env=session.env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return [None if word == "*" else float(word) for word in result.stdout.split()]


@little_endian_only
@pytest.mark.parametrize("cell_type", ["float", "double"])
def test_map_of_the_former_library_reads_as_before(tools, session, tmp_path, cell_type):
    """A map of version 2 and a reduced precision reads as before

    The test data are a map of 4 rows, 5 columns and 3 layers, one tile,
    which zlib shrinks, of the values VALUES with a null in every seventh
    cell (the order of _values), written with r3.in.ascii type=float
    precision=7 and type=double precision=20, compression=zip, and the
    library before the change on x86_64 (little-endian), 2026-11-06. The
    files .ref are the output of r3.out.ascii -h precision=17 of these maps
    with the same library; they show the null cells, while every other
    value is too small for 17 decimal places.

    The exact values are those of the former packing, which kept the
    leading bits of the little-endian bytes (_kept with byteorder "<").
    That this is what the library before the change reads from these files
    was measured on 2026-11-06: the same comparison, run with that library
    installed in place of the new one, matched in all 60 cells of each map.
    """
    _copy_former(tools, session, cell_type, "former")
    name, precision = FORMER[cell_type]

    assert "Version: 2" in _header(session, "former")
    assert _former_output(session, "former") == (DATA / f"{name}.ref").read_text()
    assert _exact_values(session, tmp_path, "former") == [
        _kept(value, cell_type, precision, byteorder="<")
        for value in _values(4 * 5 * 3, nulls=True)
    ]


@little_endian_only
def test_header_rewrite_keeps_the_former_reading(tools, session, tmp_path):
    # r3.support writes the header of a map with a new unit through
    # Rast3d_rewrite_header(), which keeps the version of the map.
    _copy_former(tools, session, "float", "former")
    tools.r3_support(map="former", unit="meters")

    header = _header(session, "former")
    assert "Units: meters" in header
    assert "Version: 2" in header
    assert (
        _former_output(session, "former")
        == (DATA / f"{FORMER['float'][0]}.ref").read_text()
    )
    # r3.out.ascii prints too few digits to show the small values.
    assert _exact_values(session, tmp_path, "former") == [
        _kept(value, "float", FORMER["float"][1], byteorder="<")
        for value in _values(4 * 5 * 3, nulls=True)
    ]


def test_new_map_has_version_3(tools, session, tmp_path):
    _import(tools, tmp_path, "new", _values(24, nulls=False), size=(2, 3, 4))

    assert "Version: 3" in _header(session, "new")


@pytest.mark.parametrize("cell_type", ["float", "double"])
@pytest.mark.parametrize(
    ("precision", "compression"),
    [("max", "zip"), (10, "none")],
    ids=["full-precision", "uncompressed"],
)
def test_full_precision_and_uncompressed_maps_keep_their_values(
    tools, tmp_path, precision, compression, cell_type
):
    # Without compression the library stores the full precision whatever
    # precision the tool asks for.
    values = _values(ROWS * COLUMNS * LAYERS, nulls=True)
    _import(
        tools,
        tmp_path,
        "kept",
        values,
        type=cell_type,
        precision=precision,
        compression=compression,
    )

    assert _read(tools, "kept") == [_as_type(value, cell_type) for value in values]


@little_endian_only
def test_rewriting_a_former_map_sets_its_values_to_zero(tools, session, tmp_path):
    # r3.null writes the map anew with its precision 7. It reads the values
    # of the former map: the two least significant bytes of each float,
    # with sign and exponent 0. The new packing keeps sign, exponent and the
    # 7 leading mantissa bits of each value, all 0 for such a value.
    precision = FORMER["float"][1]
    _copy_former(tools, session, "float", "rewritten")
    tools.r3_null(map="rewritten", setnull=12345)

    values = _values(4 * 5 * 3, nulls=True)
    expected = [
        _kept(_kept(value, "float", precision, byteorder="<"), "float", precision)
        for value in values
    ]
    assert [value for value in expected if value is not None] == [0.0] * 51
    assert "Version: 3" in _header(session, "rewritten")
    assert "Precision: 7" in _header(session, "rewritten")
    assert _read(tools, "rewritten") == expected
    # 20 decimal places hide values below 5e-21, such as the old 7.3e-41.
    assert _exact_values(session, tmp_path, "rewritten") == expected


FLOAT_ROWS_SCRIPT = """\
import sys
from ctypes import POINTER, byref, c_float, cast

from grass.lib.gis import G_gisinit
from grass.lib.raster import FCELL_TYPE
from grass.lib.raster3d import (
    RASTER3D_USE_CACHE_DEFAULT,
    RASTER3D_Map,
    RASTER3D_Region,
    Rast3d_close,
    Rast3d_get_window,
    Rast3d_init_defaults,
    Rast3d_open_cell_new,
    Rast3d_put_float,
)

G_gisinit("test")
Rast3d_init_defaults()
region = RASTER3D_Region()
Rast3d_get_window(byref(region))
handle = Rast3d_open_cell_new(
    sys.argv[1], FCELL_TYPE, RASTER3D_USE_CACHE_DEFAULT, byref(region)
)
if not handle:
    sys.exit("Rast3d_open_cell_new failed")
map_ptr = cast(handle, POINTER(RASTER3D_Map))
values = iter(sys.argv[2:])
for depth in range(region.depths):
    for row in range(region.rows):
        for col in range(region.cols):
            Rast3d_put_float(map_ptr, col, row, depth, c_float(float(next(values))))
if not Rast3d_close(map_ptr):
    sys.exit("Rast3d_close failed")
"""


def test_float_row_in_a_double_file_keeps_its_values(tools, session, tmp_path):
    # r3.in.v5d opens its map with float values in a file of the default
    # type double, for which Rast3d_open_cell_new() sets the precision 23:
    # a double keeps all 23 mantissa bits of a float. The script calls the
    # library in a process of its own as that tool does.
    values = _values(3 * 4 * 2, nulls=False)
    tools.g_region(s=0, n=3, w=0, e=4, b=0, t=2, res=1, res3=1)
    script = tmp_path / "float_rows.py"
    script.write_text(FLOAT_ROWS_SCRIPT, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), "float_rows", *map(repr, values)],
        env=session.env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    header = _header(session, "float_rows")
    assert "CellType: double" in header
    assert "Precision: 23" in header
    assert _read(tools, "float_rows") == [_as_type(value, "float") for value in values]


def test_tool_reading_back_its_output_keeps_the_values(tools, session):
    # r.to.rast3elev writes the first pair of input and elevation into the
    # map; for the second pair it reads back the cells away from the second
    # elevation and writes them again. With -m it reads them through the 3D
    # mask, which hides no cell here. Each elevation lies within one layer
    # of the three, where the tool writes the input value: the bottom layer
    # holds a, the top layer b, the middle layer nulls. The map is a double
    # map with precision 10.
    tools.g_region(s=0, n=3, w=0, e=4, b=0, t=3, res=1, res3=1, tbres=1)
    tools.r_mapcalc(expression="a = row() + col() / 7.0")
    tools.r_mapcalc(expression="b = -(row() * 3 + col() / 3.0)")
    tools.r_mapcalc(expression="low = 0.5")
    tools.r_mapcalc(expression="high = 2.5")
    tools.r3_mapcalc(expression="nothing_hidden = 0")
    tools.r3_mask(map="nothing_hidden", maskvalues=1)
    env = session.env.copy()
    env["RASTER3D_PRECISION"] = "10"
    gs.run_command(
        "r.to.rast3elev",
        flags="m",
        input="a,b",
        elevation="low,high",
        output="elevation",
        env=env,
    )

    cells = [(row, column) for row in range(1, 4) for column in range(1, 5)]
    a = [row + column / 7.0 for row, column in cells]
    b = [-(row * 3 + column / 3.0) for row, column in cells]
    expected = [_kept(value, "double", 10) for value in (*a, *[None] * 12, *b)]
    assert _read(tools, "elevation") == expected


FLUSHED_TILE_SCRIPT = """\
import sys
from ctypes import POINTER, byref, c_double, cast

from grass.lib.gis import G_gisinit
from grass.lib.raster import DCELL_TYPE
from grass.lib.raster3d import (
    RASTER3D_USE_CACHE_DEFAULT,
    RASTER3D_Map,
    RASTER3D_Region,
    Rast3d_close,
    Rast3d_flush_tile,
    Rast3d_get_double,
    Rast3d_get_window,
    Rast3d_init_defaults,
    Rast3d_open_cell_new,
    Rast3d_put_double,
    Rast3d_set_file_type,
    Rast3d_set_tile_dimension,
)

G_gisinit("test")
Rast3d_init_defaults()
Rast3d_set_file_type(DCELL_TYPE)
Rast3d_set_tile_dimension(2, 2, 2)
region = RASTER3D_Region()
Rast3d_get_window(byref(region))
handle = Rast3d_open_cell_new(
    sys.argv[1], DCELL_TYPE, RASTER3D_USE_CACHE_DEFAULT, byref(region)
)
if not handle:
    sys.exit("Rast3d_open_cell_new failed")
map_ptr = cast(handle, POINTER(RASTER3D_Map))
cells = [(x, y, z) for z in range(2) for y in range(2) for x in range(2)]
for (x, y, z), value in zip(cells, sys.argv[2:]):
    Rast3d_put_double(map_ptr, x, y, z, c_double(float(value)))
if not Rast3d_flush_tile(map_ptr, 0):
    sys.exit("Rast3d_flush_tile failed")
for x, y, z in cells:
    print(repr(Rast3d_get_double(map_ptr, x, y, z)))
if not Rast3d_close(map_ptr):
    sys.exit("Rast3d_close failed")
"""


def test_flushed_tile_reads_back_while_writing(tools, session, tmp_path):
    # r.to.rast3elev reads back tiles from the cache of the map, never from
    # its file: the test of that tool stayed green with a library that does
    # not swap when it reads a tile of a map open for writing (measured
    # 2026-11-06). Rast3d_flush_tile() writes a tile to the file and drops
    # it from the cache, so that reading one of its cells reads the packed
    # tile from the file while the map is still open for writing.
    values = VALUES[:8]
    tools.g_region(s=0, n=2, w=0, e=2, b=0, t=2, res=1, res3=1)
    script = tmp_path / "flushed_tile.py"
    script.write_text(FLUSHED_TILE_SCRIPT, encoding="utf-8")
    env = session.env.copy()
    env["RASTER3D_PRECISION"] = "10"
    result = subprocess.run(
        [sys.executable, str(script), "flushed", *map(repr, values)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    expected = [_kept(value, "double", 10) for value in values]
    assert [float(line) for line in result.stdout.split()] == expected
    assert "Precision: 10" in _header(session, "flushed")
    assert _read(tools, "flushed") == expected
