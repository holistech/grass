"""Test the choice of the GDAL data type for exported CELL maps

SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.temporal.stds_export import _gdal_type_for_cell_map


@pytest.mark.parametrize(
    ("minimum", "maximum", "nodata", "expected"),
    [
        # Byte holds 0 to 255, UInt16 0 to 65535, Int16 -32768 to 32767,
        # UInt32 0 to 2**32 - 1 and Int32 -2**31 to 2**31 - 1.
        (0, 255, 255, "Byte"),
        (0, 255, 256, "UInt16"),
        (5, 5, -77, "Int16"),
        (-1, 200, 255, "Int16"),
        (0, 65535, 65535, "UInt16"),
        (0, 65535, 65536, "UInt32"),
        (0, 32767, -32768, "Int16"),
        (0, 32768, -1, "Int32"),
        (0, 40000, 50000, "UInt16"),
        (-32769, 5, 0, "Int32"),
        (0, 2**32 - 1, 0, "UInt32"),
        (0, 2**31, -1, None),
        (-(2**31), 5, 2**31 - 1, "Int32"),
        (0, 5, 2**32, None),
        (3, 3, 3.0, "Byte"),
    ],
)
def test_the_smallest_type_that_holds_the_values_and_nodata(
    minimum, maximum, nodata, expected
):
    assert _gdal_type_for_cell_map(minimum, maximum, nodata) == expected


@pytest.mark.parametrize("nodata", [None, 1.5, -0.1])
def test_a_nodata_value_that_is_no_whole_number_gives_no_type(nodata):
    assert _gdal_type_for_cell_map(0, 5, nodata) is None
