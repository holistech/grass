# SPDX-License-Identifier: GPL-2.0-or-later
"""Fixture for t.info tests

Creates one project holding every dataset type t.info can report on, so that
the reported metadata can be compared against known values.
"""

from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    intervals,
    make_map,
    register_stds,
)
from grass.temporal.testing.session import project_session
from grass.tools import Tools

MAPSET = "tinfo_mapset"


@pytest.fixture(scope="session")
def temporal_data(tmp_path_factory):
    """Start a session with space time datasets of all types and their maps"""
    tmp_path = tmp_path_factory.mktemp("t_info")

    with project_session(tmp_path / "test_project", mapset=MAPSET) as session:
        tools = Tools(session=session)
        tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10, tbres=10)

        months = intervals(3)
        # The history test reads the t.register call back, so this dataset is
        # registered with the maps= list and the -i flag, which register_stds
        # does not write.
        # Maps with constant values keep the min and max metadata predictable.
        for i in range(1, 4):
            make_map(tools, "raster", f"prec_{i}", i)
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="precip_abs1",
            title="A test",
            description="A test",
        )
        tools.t_register(
            type="raster",
            flags="i",
            input="precip_abs1",
            maps="prec_1,prec_2,prec_3",
            start="2001-01-01",
            increment="1 months",
        )

        # A map can be registered in more than one dataset, which t.info
        # reports for the map.
        register_stds(
            tools,
            "strds",
            "precip_abs2",
            [MapSpec("prec_2", 2, *months[1])],
            title="A second test",
        )

        create_stds(
            tools,
            "str3ds",
            "volume_abs1",
            [MapSpec(f"vol_{i}", i, *months[i - 1]) for i in range(1, 3)],
            title="A 3D test",
        )

        # v.random vectors carry 20 random points, which make_map cannot
        # build, so they are created here and registered with the helper.
        for i in range(1, 3):
            tools.v_random(output=f"vect_{i}", npoints=20, seed=i)
        register_stds(
            tools,
            "stvds",
            "vect_abs1",
            [MapSpec(f"vect_{i}", i, *months[i - 1]) for i in range(1, 3)],
            title="A vector test",
        )

        # Relative time datasets need their own maps because a map can hold
        # only one time stamp.
        create_stds(
            tools,
            "strds",
            "precip_rel1",
            [MapSpec(f"rel_{i}", i, i, i + 1) for i in range(1, 3)],
            temporaltype="relative",
            unit="days",
            title="A relative test",
        )

        # A dataset without registered maps reports empty metadata fields.
        register_stds(tools, "strds", "empty_ds", [], title="An empty test")

        # Non-ASCII text has to survive the round trip through the database.
        # The description differs from the title, which register_stds cannot
        # express.
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="accent_ds",
            title="Précipitation totale",
            description="Précipitation mensuelle",
        )

        yield SimpleNamespace(session=session, mapset=MAPSET, tools=tools)
