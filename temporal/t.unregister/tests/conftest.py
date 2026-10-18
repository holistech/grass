# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fixtures for the t.unregister tests"""

import re
import zlib

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in a project of its own for a whole module

    The region is one cell, so a constant map is cheap. Messages of a
    successful run are kept in result.stderr, because the warnings of
    t.unregister (a map that is not in the temporal database) are part of
    its behaviour.
    """
    with project_session(
        tmp_path_factory.mktemp("t_unregister") / "project"
    ) as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        yield tools


@pytest.fixture
def prefix(request):
    """A name prefix that is unique for the test within its module"""
    node = re.sub(r"\W+", "_", request.node.name).strip("_").lower()
    return f"{node[:24]}_{zlib.crc32(request.node.name.encode()) % 100000}"


@pytest.fixture
def make_stds(tools, prefix):
    """Function that creates maps and datasets that hold all of them

    make(count) creates the maps <prefix>_1 to <prefix>_<count> of the kind
    that stds_type holds, where map n holds the value n and lasts one day
    from day n-1 to day n, and the datasets <prefix>_ds0, <prefix>_ds1, ...
    that each register all of them. Returns the map names and the dataset
    names.
    """

    def make(count, *, stds_type="strds", datasets=1):
        names = [f"{prefix}_ds{index}" for index in range(datasets)]
        maps = create_daily_stds(tools, stds_type, names, count, map_prefix=prefix)
        return maps, names

    return make
