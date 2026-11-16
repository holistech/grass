# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests of the seed option of v.ppa

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
# v.ppa method=f num_distances=10 random_points=200 format=csv nprocs=1; the
# input are the 20 points of v.random npoints=20 seed=7.
FORMER = {
    1: "e66e82a1a6fa3a979eb95d36b6412b68",
    12345: "7bb5d473deef5a91870b88e28eeb00d4",
}


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in a new project with a small region"""
    project = tmp_path_factory.mktemp("v_ppa_seed") / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session) as tools,
    ):
        tools.g_region(n=100, s=0, e=100, w=0, res=10)
        tools.v_random(output="points", npoints=20, seed=7)
        yield tools


def run(tools, seed):
    """Run v.ppa with the seed and return what it prints"""
    return tools.v_ppa(
        input="points",
        method="f",
        num_distances=10,
        random_points=200,
        format="csv",
        nprocs=1,
        seed=seed,
    ).stdout


def checksum(tools, seed):
    """Checksum of what run() prints"""
    return hashlib.md5(run(tools, seed).encode()).hexdigest()


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
    assert checksum(tools, seed) == FORMER[seed]
