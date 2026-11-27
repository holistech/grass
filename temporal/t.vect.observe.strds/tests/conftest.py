"""Datasets for the tests of t.vect.observe.strds

The region has two rows and two columns of size 1. A map made by
vector_points() at the cell centres has the points p1 to p4 (cat 1 to 4)
at (0.5, 1.5), (1.5, 1.5), (0.5, 0.5) and (1.5, 0.5): in the cells (row 1,
column 1), (1, 2), (2, 1) and (2, 2) of the raster maps, counted from 1.

The raster datasets:

- ob_a has the integer maps ra_1 to ra_3 (March, April and May 2001) with
  100 k + 10 row + col in map k: the point p1 reads 100 k + 11, p2 100 k + 12,
  p3 100 k + 21 and p4 100 k + 22,
- ob_b has the float maps rb_1 and rb_2 (April and May 2001) holding 0.5 + k,
- ob_rel has the integer maps rr_1 to rr_3 in the months 0 to 3 (relative
  time, unit months) with 100 k + 10 row + col.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    small_region,
    vector_points,
)

CENTRES = [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5)]
NUMBER = "10 * row() + col()"


@pytest.fixture(autouse=True)
def _region(tools):
    small_region(tools, 2, 2)


@pytest.fixture(scope="module")
def rasters(tools):
    """The datasets ob_a, ob_b and ob_rel described above"""
    small_region(tools, 2, 2)
    create_stds(
        tools,
        "strds",
        "ob_a",
        [
            MapSpec(
                f"ra_{k}",
                f"{100 * k} + {NUMBER}",
                datetime(2001, k + 2, 1),
                datetime(2001, k + 3, 1),
            )
            for k in (1, 2, 3)
        ],
    )
    create_stds(
        tools,
        "strds",
        "ob_b",
        [
            MapSpec(
                f"rb_{k}",
                f"0.5 + {k}",
                datetime(2001, k + 3, 1),
                datetime(2001, k + 4, 1),
            )
            for k in (1, 2)
        ],
    )
    create_stds(
        tools,
        "strds",
        "ob_rel",
        [MapSpec(f"rr_{k}", f"{100 * k} + {NUMBER}", k - 1, k) for k in (1, 2, 3)],
        temporaltype="relative",
        unit="months",
    )


@pytest.fixture
def points(tools, prefix):
    """The map <prefix>_pts with the four points and the column h = 1 to 4"""
    name = f"{prefix}_pts"
    vector_points(tools, name, CENTRES, attributes={"h": [1, 2, 3, 4]})
    return name
