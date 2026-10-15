"""Test that t.rast.mapcalc yields the same maps for every nprocs.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, intervals
from grass.temporal.testing.readback import list_maps
from grass.tools import Tools


@pytest.fixture(scope="module")
def uneven_session(xy_module_session):
    """Session with STRDS a (4 maps) and b (3 maps), monthly from 2001-01."""
    tools = Tools(session=xy_module_session, overwrite=True)
    tools.g_region(s=0, n=30, w=0, e=30, res=10)
    for name, values in (("a", (1, 2, 3, 4)), ("b", (10, 20, 30))):
        maps = [
            MapSpec(f"{name}_{number}", value, start, end)
            for number, (value, (start, end)) in enumerate(
                zip(values, intervals(len(values)), strict=True)
            )
        ]
        create_stds(tools, "strds", name, maps)
    return xy_module_session


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
    rows = list_maps(tools, "strds", "r")
    assert [(row.min, row.max) for row in rows] == [
        (11, 11),
        (22, 22),
        (33, 33),
    ]
