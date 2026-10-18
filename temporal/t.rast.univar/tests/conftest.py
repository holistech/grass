"""Datasets for the tests of t.rast.univar

The first dataset (uv_a) has three daily maps on a region of two rows and three
columns of size 1. With the cell number n = (row - 1) * 3 + column:

- uv_1 holds n: 1, 2, 3 in the northern row and 4, 5, 6 in the southern one,
- uv_2 holds n but nothing in the middle column: 1, 3, 4, 6,
- uv_3 holds n / 2 as a float map: 0.5 to 3.

The map uv_zones holds the column number and so makes three zones of two cells.

The second dataset (ur_ds) has four daily maps with constant values on regions
of their own, listed in REGIONS in the test module for the spatial relations.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    register_stds,
    small_region,
)

NUMBER = "(row() - 1) * 3 + col()"


@pytest.fixture(scope="module")
def values(tools):
    """The dataset uv_a described above and the zones map; returns its name"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "uv_a",
        [
            MapSpec("uv_1", NUMBER, day(0), day(1)),
            MapSpec("uv_2", f"if(col() == 2, null(), {NUMBER})", day(1), day(2)),
            MapSpec("uv_3", f"({NUMBER}) / 2.0", day(2), day(3)),
        ],
    )
    tools.r_mapcalc(expression="uv_zones = col()", overwrite=True)
    return "uv_a"


@pytest.fixture(scope="module")
def labeled(tools):
    """Four maps with two semantic labels, S2_B1 (10, 30) and S2_C1 (20, 40)
    on the same days of two datasets; returns the name of the dataset"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "uv_l",
        [
            MapSpec("uv_b1", "10", day(0), day(1), semantic_label="S2_B1"),
            MapSpec("uv_c1", "20", day(0), day(1), semantic_label="S2_C1"),
            MapSpec("uv_b2", "30", day(1), day(2), semantic_label="S2_B1"),
            MapSpec("uv_c2", "40", day(1), day(2), semantic_label="S2_C1"),
        ],
    )
    return "uv_l"


@pytest.fixture(scope="module")
def regions(tools):
    """Four maps with constant values and regions of their own (see the test
    module); the current region is left at the one of the first map"""
    for name, south, west, size, value in (
        ("ur_all", 0, 0, 4, 10),
        ("ur_in", 1, 1, 2, 20),
        ("ur_part", 2, 2, 4, 30),
        ("ur_out", 10, 10, 2, 40),
    ):
        tools.g_region(s=south, n=south + size, w=west, e=west + size, res=1)
        tools.r_mapcalc(expression=f"{name} = {value}", overwrite=True)
    register_stds(
        tools,
        "strds",
        "ur_ds",
        [
            MapSpec("ur_all", 0, day(0), day(1)),
            MapSpec("ur_in", 0, day(1), day(2)),
            MapSpec("ur_part", 0, day(2), day(3)),
            MapSpec("ur_out", 0, day(3), day(4)),
        ],
    )
    return "ur_ds"
