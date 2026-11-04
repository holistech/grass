"""Test t.rast.import for a second import into a project the tool made

The archives come from a project with the CRS EPSG:3358: the map rp_a has
10 in every cell of a region of two rows and three columns.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import Tools

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def projected(tmp_path_factory):
    """The archives of rp_in in the formats GTiff and pack, as a dict of path"""
    base = tmp_path_factory.mktemp("rp_projected")
    paths = {}
    with project_session(base / "source") as session:
        source = Tools(session=session)
        source.g_proj(flags="c", epsg=3358)
        small_region(source, 2, 3)
        create_stds(
            source,
            "strds",
            "rp_in",
            [MapSpec("rp_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1))],
        )
        for fmt in ("GTiff", "pack"):
            paths[fmt] = base / f"rp_{fmt}.tar"
            source.t_rast_export(
                input="rp_in", output=str(paths[fmt]), format=fmt, compression="no"
            )
    return paths


@pytest.mark.parametrize("fmt", ["GTiff", "pack"])
def test_second_import_into_tool_made_project(tools, projected, prefix, tmp_path, fmt):
    gisdbase = Path(tools.g_gisenv(get="GISDBASE").stdout.strip())
    created = gisdbase / f"{prefix}_new"
    tools.t_rast_import(
        input=str(projected[fmt]),
        output=prefix,
        basename=prefix,
        project=created.name,
        directory=str(tmp_path),
    )

    with gs.setup.init(created, env=os.environ.copy()) as session:
        second = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        # The project was made from the PROJ string of the archive, which it
        # writes differently from the EPSG project the archive comes from.
        result = second.t_rast_import(
            input=str(projected[fmt]),
            output=f"{prefix}_two",
            basename=f"{prefix}_two",
            directory=str(tmp_path),
        )

        assert "does not match" not in message(result)
        assert [row.name for row in list_maps(second, "strds", f"{prefix}_two")] == [
            f"{prefix}_two_1"
        ]
