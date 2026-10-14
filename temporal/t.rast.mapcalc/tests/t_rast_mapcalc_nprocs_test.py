"""Test that t.rast.mapcalc yields the same maps for every nprocs.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture(scope="module")
def uneven_session(tmp_path_factory):
    """Session with STRDS a (4 maps) and b (3 maps), monthly from 2001-01."""
    project = tmp_path_factory.mktemp("t_rast_mapcalc_nprocs") / "test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_gisenv(set="TGIS_USE_CURRENT_MAPSET=1")
        tools.g_region(s=0, n=30, w=0, e=30, res=10)
        for name, values in (("a", (1, 2, 3, 4)), ("b", (10, 20, 30))):
            maps = [f"{name}_{i}" for i in range(len(values))]
            for map_name, value in zip(maps, values, strict=True):
                tools.r_mapcalc(expression=f"{map_name} = {value}")
            tools.t_create(
                type="strds",
                temporaltype="absolute",
                output=name,
                title=name,
                description=name,
            )
            tools.t_register(
                flags="i",
                type="raster",
                input=name,
                maps=",".join(maps),
                start="2001-01-01",
                increment="1 months",
            )
        yield session


@pytest.mark.parametrize("nprocs", [1, 2, 3])
def test_unpaired_last_granule_does_not_lose_maps(uneven_session, nprocs):
    """The last granule of a has no partner in b and is skipped."""
    tools = Tools(session=uneven_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="a,b",
        expression="a + b",
        basename="r",
        output="r",
        nprocs=nprocs,
        method="equal",
    )
    rows = tools.t_rast_list(
        input="r", columns="name,min,max", format="csv", separator="comma"
    ).text
    values = [line.split(",") for line in rows.strip().splitlines()[1:]]
    assert [(float(row[1]), float(row[2])) for row in values] == [
        (11, 11),
        (22, 22),
        (33, 33),
    ]
