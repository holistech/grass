# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fixture for t.register tests"""

import re
import zlib

import pytest

from grass.temporal.testing.data import make_map
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture
def session_with_rasters(tmp_path):
    """Start a session in a new project and create small test rasters."""
    with project_session(tmp_path / "test") as session:
        tools = Tools(session=session)
        tools.g_region(s=0, n=1, w=0, e=1, res=1)
        for name in ("a", "b", "c"):
            make_map(tools, "raster", name, 1)
        yield session


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in a project of its own for a whole module

    The region is one cell, so a constant map is cheap. Messages of a
    successful run are kept in result.stderr, because the warnings of
    t.register (a map that is already registered) are part of its behaviour.
    """
    with project_session(tmp_path_factory.mktemp("t_register") / "project") as session:
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
def make_maps(tools, prefix):
    """Function that creates count maps named <prefix>_1 to <prefix>_<count>

    kind is raster, raster_3d or vector. The value of map number n is n; a
    vector map has the one point (n, n) with the attribute value n. Returns
    the names.
    """

    def make(count, kind="raster"):
        names = []
        for number in range(1, count + 1):
            name = f"{prefix}_{number}"
            make_map(tools, kind, name, number)
            names.append(name)
        return names

    return make


@pytest.fixture
def dataset(tools, prefix):
    """Function that creates a dataset of the test and returns its name"""

    def create(stds_type="strds", temporaltype="absolute", suffix=""):
        name = f"{prefix}_ds{suffix}"
        tools.t_create(
            type=stds_type,
            temporaltype=temporaltype,
            output=name,
            title="t",
            description="d",
        )
        return name

    return create
