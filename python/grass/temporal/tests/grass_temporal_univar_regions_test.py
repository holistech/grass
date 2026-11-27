"""Test the region of each map in the univariate statistics of a 3D dataset

t.rast3d.univar has no flag for it, but the library function takes
rast_region for both dataset types.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, day, register_stds
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    # The last loop pass leaves the region on the cube of the second map; the
    # first one is larger.
    for name, low, size, value in (("ur3a", 0, 4, 10), ("ur3b", 1, 2, 20)):
        tools.g_region(
            s=low, n=low + size, w=low, e=low + size, b=low, t=low + size, res=1, res3=1
        )
        tools.r3_mapcalc(expression=f"{name} = {value}")
    register_stds(
        tools,
        "str3ds",
        "ur3_ds",
        [MapSpec("ur3a", 0, day(0), day(1)), MapSpec("ur3b", 0, day(1), day(2))],
    )
    return tools


def _cells(capsys, rast_region):
    tgis.print_gridded_dataset_univar_statistics(
        "str3ds", "ur3_ds", None, None, False, rast_region=rast_region
    )
    lines = capsys.readouterr().out.splitlines()
    header = lines[0].split("|")
    return [
        dict(zip(header, line.split("|"), strict=True))["non_null_cells"]
        for line in lines[1:]
    ]


def test_a_3d_dataset_is_computed_in_the_current_region_by_default(tools, capsys):
    assert _cells(capsys, False) == ["8", "8"]


def test_rast_region_uses_the_region_of_each_3d_map(tools, capsys):
    assert _cells(capsys, True) == ["64", "8"]
