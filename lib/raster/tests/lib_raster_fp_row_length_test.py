"""Test that a floating-point row decompressing to fewer bytes than a row fails

A compressed floating-point raster map stores each row as a flag byte and a
zlib stream, found through a table of row offsets at the start of the file.
A stream that is valid but holds fewer cells than a row cannot come from a
correct writer; reading it has to fail instead of leaving the rest of the
row undefined.
"""

import struct
import zlib
from pathlib import Path

import pytest

from grass.exceptions import CalledModuleError
from grass.tools import Tools

ROWS, COLUMNS = 3, 100

# The struct code of a value of each type, stored big-endian (XDR).
CODES = {"float": "f", "double": "d"}


def _rewrite_row(path, row, data):
    """Replace a row of a compressed raster file with the flag of zlib and
    the zlib stream of data, and move the offsets of the rows after it
    """
    content = path.read_bytes()
    width = content[0]
    offsets = [
        int.from_bytes(content[1 + i * width : 1 + (i + 1) * width], "big")
        for i in range(ROWS + 1)
    ]
    rows = [content[offsets[i] : offsets[i + 1]] for i in range(ROWS)]
    assert rows[row][:1] == b"1", "the row has to be compressed in the first place"
    rows[row] = b"1" + zlib.compress(data)
    position = 1 + (ROWS + 1) * width
    new_offsets = [position]
    for stored in rows:
        position += len(stored)
        new_offsets.append(position)
    table = b"".join(offset.to_bytes(width, "big") for offset in new_offsets)
    path.write_bytes(bytes([width]) + table + b"".join(rows))


@pytest.fixture
def tools(session):
    with Tools(session=session, consistent_return_value=True) as tools:
        yield tools


def _map_file(tools, session, cell_type):
    """Create a zlib compressed map of the type with constant rows and
    return the path of its data file
    """
    tools.g_region(n=ROWS, s=0, e=COLUMNS, w=0, rows=ROWS, cols=COLUMNS)
    tools.r_mapcalc(
        expression=f"values = {cell_type}(1.5)",
        env={**session.env, "GRASS_COMPRESSOR": "ZLIB"},
    )
    cellhd = Path(
        tools.g_findfile(file="values", element="cellhd", format="json")["file"]
    )
    return cellhd.parent.parent / "fcell" / "values"


@pytest.mark.parametrize("cell_type", ["float", "double"])
def test_rewritten_row_of_full_length_reads_back(tools, session, cell_type):
    # Shows that the rewritten file is valid, so that the failure of the
    # short row below comes from its length only.
    path = _map_file(tools, session, cell_type)
    _rewrite_row(
        path, 1, struct.pack(f">{COLUMNS}{CODES[cell_type]}", *[2.5] * COLUMNS)
    )

    text = tools.r_out_ascii(input="values", flags="h").text

    assert [line.split() for line in text.splitlines()] == [
        ["1.5"] * COLUMNS,
        ["2.5"] * COLUMNS,
        ["1.5"] * COLUMNS,
    ]


@pytest.mark.parametrize("cell_type", ["float", "double"])
def test_short_row_fails(tools, session, cell_type):
    path = _map_file(tools, session, cell_type)
    short = COLUMNS - 1
    _rewrite_row(path, 1, struct.pack(f">{short}{CODES[cell_type]}", *[2.5] * short))

    with pytest.raises(CalledModuleError, match="row 1 of <values>"):
        tools.r_out_ascii(input="values", flags="h")
