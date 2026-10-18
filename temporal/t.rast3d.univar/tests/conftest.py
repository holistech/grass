"""Datasets for the tests of t.rast3d.univar

The first dataset (uv3_a) has three daily maps on a region of two rows, three
columns and two layers of size 1. With the voxel number
n = (layer - 1) * 6 + (row - 1) * 3 + column (layers counted from the bottom):

- uv3_1 holds n: 1 to 6 in the lower layer and 7 to 12 in the upper one,
- uv3_2 holds n but nothing in the middle column: 1, 3, 4, 6, 7, 9, 10, 12,
- uv3_3 holds n / 2 as a double map: 0.5 to 6.

The map uv3_zones holds the column number and so makes three zones of four
voxels.

The second dataset (ur3_ds) has five daily maps with constant values on cubes
of their own, listed in the regions test module for the spatial relations.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    register_stds,
    small_region,
)

NUMBER = "(depth() - 1) * 6 + (row() - 1) * 3 + col()"


@pytest.fixture(scope="module")
def values(tools):
    """The dataset uv3_a described above and the zones map; returns its name"""
    small_region(tools, 2, 3, depths=2)
    create_stds(
        tools,
        "str3ds",
        "uv3_a",
        [
            MapSpec("uv3_1", NUMBER, day(0), day(1)),
            MapSpec("uv3_2", f"if(col() == 2, null(), {NUMBER})", day(1), day(2)),
            MapSpec("uv3_3", f"({NUMBER}) / 2.0", day(2), day(3)),
        ],
    )
    tools.r3_mapcalc(expression="uv3_zones = col()", overwrite=True)
    return "uv3_a"


@pytest.fixture(scope="module")
def regions(tools):
    """Five maps with constant values and cubes of their own (see the test
    module); the current region is left at the one of the last map"""
    for name, south, west, bottom, size, value in (
        ("ur3_all", 0, 0, 0, 4, 10),
        ("ur3_in", 1, 1, 1, 2, 20),
        ("ur3_part", 2, 2, 2, 4, 30),
        ("ur3_out", 10, 10, 10, 2, 40),
        ("ur3_high", 1, 1, 10, 2, 50),
    ):
        tools.g_region(
            s=south,
            n=south + size,
            w=west,
            e=west + size,
            b=bottom,
            t=bottom + size,
            res=1,
            res3=1,
        )
        tools.r3_mapcalc(expression=f"{name} = {value}", overwrite=True)
    register_stds(
        tools,
        "str3ds",
        "ur3_ds",
        [
            MapSpec("ur3_all", 0, day(0), day(1)),
            MapSpec("ur3_in", 0, day(1), day(2)),
            MapSpec("ur3_part", 0, day(2), day(3)),
            MapSpec("ur3_out", 0, day(3), day(4)),
            MapSpec("ur3_high", 0, day(4), day(5)),
        ],
    )
    return "ur3_ds"
