"""Fixtures for the t.rast3d.mapcalc characterization tests.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, register_stds
from grass.temporal.testing.readback import stds_info
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture(scope="session")
def mapcalc3d_session(tmp_path_factory):
    """A session with three constant 3D rasters registered in two STR3DS

    The rasters are constant so that the result min and max are deterministic.
    The datasets carry absolute time in three-month intervals from 2001-01-01,
    as in the 2D fixture; the region has a vertical extent (bottom and top).
    """
    project = tmp_path_factory.mktemp("t_rast3d_mapcalc") / "project"
    with project_session(project) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)
        quarters = [
            (datetime(2001, 1, 1), datetime(2001, 4, 1)),
            (datetime(2001, 4, 1), datetime(2001, 7, 1)),
            (datetime(2001, 7, 1), datetime(2001, 10, 1)),
        ]
        maps = [
            MapSpec(f"vol_{number}", number * 100, start, end)
            for number, (start, end) in enumerate(quarters, 1)
        ]
        create_stds(tools, "str3ds", "precip3d_1", maps, title="A test")
        # precip3d_2 holds the same maps with the same time stamps.
        register_stds(tools, "str3ds", "precip3d_2", maps, title="A test")
        yield session


@pytest.fixture
def assert_tinfo3d():
    """Return a helper that checks t.info -g of an str3ds against expected pairs"""

    def _assert(tools, str3ds_name, expected):
        actual = stds_info(tools, "str3ds", str3ds_name)
        for key, value in expected.items():
            assert key in actual, f"missing key {key!r} in t.info output"
            assert actual[key] == value, (
                f"{key}: expected {value!r}, got {actual[key]!r}"
            )

    return _assert
