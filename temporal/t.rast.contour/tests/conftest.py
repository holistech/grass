"""Datasets for the tests of t.rast.contour

The region has four rows and four columns of size 1, so the cell centres lie at
the coordinates 0.5 to 3.5. A contour of the level L of the column ramp
(column c holds c) runs along x = L - 0.5 from y = 0.5 to y = 3.5, and a
contour of the level L of the row ramp (row r holds 2 r) along y = 4.5 - L / 2
from x = 0.5 to x = 3.5. r.contour draws no line at the lowest level of a map,
because it lies on the border of the data (the centres of the first row or
column), but one at the highest.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region

COLUMNS = "double(col())"
ROWS = "double(row() * 2)"


def quarter(index):
    """The first day of quarter index, counted from 2001-01-01"""
    month = 1 + 3 * index
    return datetime(2001 + (month - 1) // 12, (month - 1) % 12 + 1, 1)


@pytest.fixture(scope="module")
def quarterly(tools):
    """Four maps of three months: the column ramp, the row ramp, the column
    ramp again and a map without a value; returns the name of the dataset"""
    small_region(tools, 4, 4)
    create_stds(
        tools,
        "strds",
        "ctr_quarterly",
        [
            MapSpec("ctr_cols1", COLUMNS, quarter(0), quarter(1)),
            MapSpec("ctr_rows", ROWS, quarter(1), quarter(2)),
            MapSpec("ctr_cols2", COLUMNS, quarter(2), quarter(3)),
            MapSpec("ctr_null", "double(null())", quarter(3), quarter(4)),
        ],
    )
    return "ctr_quarterly"


@pytest.fixture(scope="module")
def ramps(tools):
    """Two daily maps without a null map: the column ramp and the row ramp"""
    small_region(tools, 4, 4)
    create_stds(
        tools,
        "strds",
        "ctr_ramps",
        [
            MapSpec("ctr_r_cols", COLUMNS, datetime(2001, 1, 1), datetime(2001, 1, 2)),
            MapSpec("ctr_r_rows", ROWS, datetime(2001, 1, 2), datetime(2001, 1, 3)),
        ],
    )
    return "ctr_ramps"
