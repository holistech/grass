"""Datasets for the tests of t.vect.what.strds

The region has two rows and two columns of size 1. A map made by
vector_points() at the cell centres has the points p1 to p4 (cat 1 to 4) at
(0.5, 1.5), (1.5, 1.5), (0.5, 0.5) and (1.5, 0.5), in the cells (row 1,
column 1), (1, 2), (2, 1) and (2, 2) of the raster maps, counted from 1.

The raster datasets, all with 100 k + 10 row + col in map k (so p1 reads
100 k + 11, p2 100 k + 12, p3 100 k + 21 and p4 100 k + 22):

- wh_a has the integer maps wr_1 to wr_6, one month each from 2001-03-01,
- wh_rel has the integer maps wrr_1 to wrr_6 of five minutes each from 0
  (relative time, unit minutes).

The tool changes the tables of the vector maps, so every test makes its own
maps with the fixture vectors().
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    register_stds,
    small_region,
    vector_points,
)

CENTRES = [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5)]
NUMBER = "10 * row() + col()"
# The cells of the points in the raster maps: 10 row + col
CELLS = [11, 12, 21, 22]


@pytest.fixture(autouse=True)
def _region(tools):
    small_region(tools, 2, 2)


@pytest.fixture(scope="module")
def rasters(tools):
    """The datasets wh_a and wh_rel described above"""
    small_region(tools, 2, 2)
    create_stds(
        tools,
        "strds",
        "wh_a",
        [
            MapSpec(
                f"wr_{k}",
                f"{100 * k} + {NUMBER}",
                datetime(2001, k + 2, 1),
                datetime(2001, k + 3, 1),
            )
            for k in range(1, 7)
        ],
    )
    create_stds(
        tools,
        "strds",
        "wh_rel",
        [
            MapSpec(f"wrr_{k}", f"{100 * k} + {NUMBER}", 5 * (k - 1), 5 * k)
            for k in range(1, 7)
        ],
        temporaltype="relative",
        unit="minutes",
    )


@pytest.fixture
def vectors(tools, prefix):
    """A function that makes the dataset <prefix>_ds of point maps

    vectors(times) makes one map for each (start, end) in times, named
    <prefix>_v1, <prefix>_v2 and so on, with the points above and the column
    h = 1 to 4, and registers them. Without times it takes the intervals
    2001-01-01 to 2001-04-01, 2001-05-01 to 2001-07-01 and 2001-08-01 to
    2001-12-01. Returns the dataset and the names of the maps.
    """

    def make(times=None, **options):
        times = times or [
            (datetime(2001, 1, 1), datetime(2001, 4, 1)),
            (datetime(2001, 5, 1), datetime(2001, 7, 1)),
            (datetime(2001, 8, 1), datetime(2001, 12, 1)),
        ]
        names = [f"{prefix}_v{number}" for number in range(1, len(times) + 1)]
        for name in names:
            vector_points(tools, name, CENTRES, attributes={"h": [1, 2, 3, 4]})
        register_stds(
            tools,
            "stvds",
            f"{prefix}_ds",
            [
                MapSpec(name, None, *time)
                for name, time in zip(names, times, strict=True)
            ],
            **options,
        )
        return SimpleNamespace(dataset=f"{prefix}_ds", maps=names)

    return make
