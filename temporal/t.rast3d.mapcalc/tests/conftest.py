"""Fixtures for the t.rast3d.mapcalc characterization tests.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture(scope="session")
def mapcalc3d_session(tmp_path_factory):
    """A session with three constant 3D rasters registered in two STR3DS

    The rasters are constant so that the result min and max are deterministic.
    The datasets carry absolute time in three-month intervals from 2001-01-01,
    as in the 2D fixture; the region has a vertical extent (bottom and top).
    """
    project = tmp_path_factory.mktemp("t_rast3d_mapcalc") / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_gisenv(set="TGIS_USE_CURRENT_MAPSET=1")
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)
        for name, value in [("vol_1", 100), ("vol_2", 200), ("vol_3", 300)]:
            tools.r3_mapcalc(expression=f"{name} = {value}")
        for name in ("precip3d_1", "precip3d_2"):
            tools.t_create(
                type="str3ds",
                temporaltype="absolute",
                output=name,
                title="A test",
                description="A test",
            )
        tools.t_register(
            flags="i",
            type="raster_3d",
            input="precip3d_1",
            maps="vol_1,vol_2,vol_3",
            start="2001-01-01",
            increment="3 months",
        )
        tools.t_register(
            type="raster_3d",
            input="precip3d_2",
            maps="vol_1,vol_2,vol_3",
        )
        yield session


@pytest.fixture
def assert_tinfo3d():
    """Return a helper that checks t.info -g of an str3ds against expected pairs"""

    def _assert(tools, str3ds_name, expected):
        actual = tools.t_info(type="str3ds", input=str3ds_name, flags="g").keyval
        for key, value in expected.items():
            assert key in actual, f"missing key {key!r} in t.info output"
            assert actual[key] == value, (
                f"{key}: expected {value!r}, got {actual[key]!r}"
            )

    return _assert
