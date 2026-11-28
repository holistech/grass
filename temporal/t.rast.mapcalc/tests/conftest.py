"""Fixtures for t.rast.mapcalc tests.

SPDX-FileCopyrightText: 2025 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, register_stds
from grass.temporal.testing.readback import stds_info
from grass.temporal.testing.session import project_session
from grass.tools import Tools

# Three-month granules from 2001-01-01, the time of both datasets.
QUARTERS = [
    (datetime(2001, 1, 1), datetime(2001, 4, 1)),
    (datetime(2001, 4, 1), datetime(2001, 7, 1)),
    (datetime(2001, 7, 1), datetime(2001, 10, 1)),
]


@pytest.fixture(scope="session")
def mapcalc_session(tmp_path_factory):
    """GRASS session with prec_1..prec_3 rasters and precip_abs1/2 STRDS.

    Session-scoped: setup (region, rasters, STRDS, TGIS init) runs once for
    the whole test run. Tests use overwrite=True for their outputs and
    test_failure_on_missing_map restores its rename in a finally block, so
    sharing across modules is safe.

    The rasters hold rand(0, value) with a fixed seed, not constants, so they
    are made here and only registered through the shared helpers.
    """
    project = tmp_path_factory.mktemp("t_rast_mapcalc") / "test"
    with project_session(project) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)
        for name, val in [("prec_1", 550), ("prec_2", 450), ("prec_3", 320)]:
            tools.r_mapcalc(expression=f"{name} = rand(0, {val})", seed=1)
        maps = [
            MapSpec(f"prec_{number}", None, start, end)
            for number, (start, end) in enumerate(QUARTERS, 1)
        ]
        # A raster carries one time stamp, so precip_abs2 gets the stamps
        # that precip_abs1 gave the same maps.
        for name in ("precip_abs1", "precip_abs2"):
            register_stds(tools, "strds", name, maps, title="A test", overwrite=True)
        yield session


@pytest.fixture
def assert_tinfo():
    """Return a helper that checks t.info -g output against expected key/value pairs."""

    def _assert(tools, strds_name, expected):
        actual = stds_info(tools, "strds", strds_name)
        for key, value in expected.items():
            assert key in actual, f"missing key {key!r} in t.info output"
            assert actual[key] == value, (
                f"{key}: expected {value!r}, got {actual[key]!r}"
            )

    return _assert
