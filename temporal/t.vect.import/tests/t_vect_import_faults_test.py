"""Test t.vect.import for archives of another CRS and for a project it made itself

The archives are made in a project with the CRS EPSG:3358 (North Carolina,
meters): the map vp_a has the points (500000, 200000) and (500020, 200010).
The import runs in an XY project of its own or in a project the tool made.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, register_stds, vector_points
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def projected(tmp_path_factory):
    """The archives of vp_in in the formats GML and pack, as a dict of path"""
    base = tmp_path_factory.mktemp("vp_projected")
    paths = {}
    with project_session(base / "source", crs="EPSG:3358") as session:
        source = Tools(session=session)
        vector_points(
            source,
            "vp_a",
            [(500000, 200000), (500020, 200010)],
            attributes={"value": [1, 2]},
        )
        register_stds(
            source,
            "stvds",
            "vp_in",
            [MapSpec("vp_a", None, datetime(2001, 1, 1), datetime(2001, 2, 1))],
        )
        for fmt in ("GML", "pack"):
            paths[fmt] = base / f"vp_{fmt}.tar"
            source.t_vect_export(
                input="vp_in", output=str(paths[fmt]), format=fmt, compression="no"
            )
    return paths


@pytest.fixture
def xy(tmp_path):
    """Tools in a new XY project, which has no CRS to match"""
    with project_session(tmp_path / "xy") as session:
        yield Tools(session=session, consistent_return_value=True, capture_stderr=True)


def _nothing_made(tools, prefix):
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout.split()
    assert not tools.g_list(type="vector", pattern=f"{prefix}*").stdout.strip()


def test_pack_into_xy_project(xy, projected, prefix, tmp_path):
    # The XY project has no PROJ_INFO that v.unpack could compare the file of
    # the archive with.
    result = xy.t_vect_import(
        input=str(projected["pack"]),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
        flags="o",
    )

    assert "Traceback" not in result.stderr
    assert "Projection information does not match. Proceeding..." in message(result)
    assert [row.name for row in list_maps(xy, "stvds", prefix)] == [f"{prefix}_1"]


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_other_crs_aborts_without_o(xy, projected, prefix, tmp_path, fmt):
    with pytest.raises(ToolError) as error:
        xy.t_vect_import(
            input=str(projected[fmt]),
            output=prefix,
            basename=prefix,
            directory=str(tmp_path),
        )

    text = message(error.value)
    assert "Projection information does not match. Aborting." in text
    assert "Traceback" not in text
    _nothing_made(xy, prefix)
    # The archive is extracted before the CRS is compared, as for rasters, so
    # the files stay in the given directory; no map or dataset is left.


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_o_goes_past_another_crs(xy, projected, prefix, tmp_path, fmt):
    result = xy.t_vect_import(
        input=str(projected[fmt]),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
        flags="o",
    )

    text = message(result)
    assert "Projection information does not match. Proceeding..." in text
    assert "Re-projection on import" not in text
    assert len(list_maps(xy, "stvds", prefix)) == 1


def test_missing_archive_message_is_neutral(xy, prefix, tmp_path):
    with pytest.raises(ToolError) as error:
        xy.t_vect_import(
            input=str(tmp_path / "none.tar"), output=prefix, directory=str(tmp_path)
        )

    text = message(error.value)
    assert f"Space time vector dataset archive <{tmp_path / 'none.tar'}> not found" in (
        text
    )
    assert "raster" not in text


def test_directory_defaults_to_temporary(tools, prefix, tmp_path_factory):
    # An archive of the project of tools itself, so that the CRS matches.
    base = tmp_path_factory.mktemp("vp_default")
    vector_points(tools, f"{prefix}_m", [(1, 1)], attributes={"value": [3]})
    register_stds(
        tools,
        "stvds",
        f"{prefix}_src",
        [MapSpec(f"{prefix}_m", None, datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    archive = base / "default.tar"
    tools.t_vect_export(
        input=f"{prefix}_src", output=str(archive), format="GML", compression="no"
    )

    tools.t_vect_import(input=str(archive), output=prefix, basename=f"{prefix}_in")

    assert [row.name for row in list_maps(tools, "stvds", prefix)] == [f"{prefix}_in_1"]
    # The files of the archive went to a temporary directory, not next to it.
    assert [path.name for path in base.iterdir()] == ["default.tar"]


def _created_project(tools, projected, prefix, tmp_path, fmt, **options):
    """Import into a project that the tool makes and return its path"""
    gisdbase = Path(tools.g_gisenv(get="GISDBASE").stdout.strip())
    created = gisdbase / f"{prefix}_new"
    tools.t_vect_import(
        input=str(projected[fmt]),
        output=prefix,
        basename=prefix,
        project=created.name,
        directory=str(tmp_path),
        **options,
    )
    return created


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_second_import_into_tool_made_project(tools, projected, prefix, tmp_path, fmt):
    created = _created_project(tools, projected, prefix, tmp_path, fmt)

    with gs.setup.init(created, env=os.environ.copy()) as session:
        second = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        result = second.t_vect_import(
            input=str(projected[fmt]),
            output=f"{prefix}_two",
            basename=f"{prefix}_two",
            directory=str(tmp_path),
        )

        # The CRS is that of the archive, so there is nothing to warn about.
        assert "does not match" not in message(result)
        assert [row.name for row in list_maps(second, "stvds", f"{prefix}_two")] == [
            f"{prefix}_two_1"
        ]


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_a_new_project_gets_the_region_of_the_maps(
    tools, projected, prefix, tmp_path, fmt
):
    created = _created_project(tools, projected, prefix, tmp_path, fmt)

    with gs.setup.init(created, env=os.environ.copy()) as session:
        region = Tools(session=session).g_region(flags="dg").keyval

    # The default region of a new project is a placeholder at the origin. The
    # region of the maps is set, not extended by it: one cell per meter.
    assert {key: region[key] for key in "nswe"} == {
        "n": 200010,
        "s": 200000,
        "w": 500000,
        "e": 500020,
    }
