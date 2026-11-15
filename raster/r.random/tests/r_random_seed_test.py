# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests of the seed option of r.random

The option is read with G_random_seed_from_option(): a seed is an integer
from -2147483648 to 4294967295 with nothing after it.
"""

import hashlib
import os

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.tools import Tools

# Checksums of the result for seed=1 and seed=12345, recorded on 2026-11-07
# with the tool as it was before it read the seed with
# G_random_seed_from_option(): the tool ran in a temporary project with the
# region of the fixture below, and the md5 sum was taken of the stdout of
# r.out.ascii -h (raster) and of v.out.ascii format=point (vector).
FORMER = {
    1: (
        "2b180ac895d34e0fc602d6e70bb7e501",
        "ded972c32c84296d7cd906d83d85fc14",
    ),
    12345: (
        "de271359b232e68d2f8f1c396259adf3",
        "e91a9839bc41f7e9e31869aacaf1bf9b",
    ),
}


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in a new project with a small region"""
    project = tmp_path_factory.mktemp("r_random_seed") / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session) as tools,
    ):
        tools.g_region(n=100, s=0, e=100, w=0, res=10)
        tools.r_mapcalc(expression="base = row() * col()")
        yield tools


def run(tools, seed):
    """Run r.random with the seed, once for a raster and once for a vector"""
    tools.r_random(
        input="base", npoints=15, raster="random_raster", seed=seed, overwrite=True
    )
    tools.r_random(
        input="base", npoints=15, vector="random_vector", seed=seed, overwrite=True
    )


def checksum(tools):
    """Checksums of the raster and the vector which run() wrote"""
    raster = tools.r_out_ascii(input="random_raster", flags="h").stdout
    vector = tools.v_out_ascii(input="random_vector", format="point").stdout
    return (
        hashlib.md5(raster.encode()).hexdigest(),
        hashlib.md5(vector.encode()).hexdigest(),
    )


@pytest.mark.parametrize(
    ("seed", "accepted"),
    [
        (-2147483648, True),
        (0, True),
        (4294967295, True),
        (-2147483649, False),
        (4294967296, False),
        ("12abc", False),
        ("1.5", False),
    ],
)
def test_seed_bounds(tools, seed, accepted):
    """A seed from -2^31 to 2^32 - 1 is taken, any other text is refused"""
    if accepted:
        run(tools, seed)
        return
    with pytest.raises(CalledModuleError) as error:
        run(tools, seed)
    assert "Invalid random seed" in str(error.value)


@pytest.mark.parametrize("seed", sorted(FORMER))
def test_seed_gives_the_former_result(tools, seed):
    """The seeds which were valid before still give the recorded result"""
    run(tools, seed)
    assert checksum(tools) == FORMER[seed]
