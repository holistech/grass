"""Test the refusals of t.rast.import

The refusals of the archive itself (missing, no archive, wrong directory) end
with a message. The later ones come from a gs.fatal() that raises ScriptError
while the library runs, so the tool ends with a traceback after the message.
"""

from datetime import datetime
from pathlib import Path

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools


@pytest.fixture(scope="module")
def archive(tools, tmp_path_factory):
    """The path of an archive with one map, made in an unprojected project"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "ime_in",
        [MapSpec("ime_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    path = tmp_path_factory.mktemp("ime_archive") / "ime.tar"
    tools.t_rast_export(input="ime_in", output=str(path), compression="no")
    return path


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_import(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, archive, prefix, missing):
    options = {"input": str(archive), "output": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_a_missing_archive_is_reported_as_a_message(tools, prefix, tmp_path):
    text = _refused(tools, input=str(tmp_path / "none.tar"), output=prefix, flags="o")

    assert "Space time raster dataset archive" in text
    assert "not found" in text
    assert "Traceback" not in text
    assert f"{prefix}" not in tools.t_list(type="strds", columns="name").stdout
    assert list(tmp_path.iterdir()) == []


def test_a_missing_extraction_directory_is_refused(tools, archive, prefix, tmp_path):
    text = _refused(
        tools,
        input=str(archive),
        output=prefix,
        flags="o",
        directory=str(tmp_path / "nope"),
    )

    assert f"Extraction directory <{tmp_path / 'nope'}> not found" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(tools, archive, prefix):
    options = {"input": str(archive), "output": prefix, "basename": prefix}
    tools.t_rast_import(flags="o", **options)

    text = _refused(tools, flags="o", **options)

    assert (
        f"Space time strds dataset <{prefix}@PERMANENT> is already in the database"
        in text
    )


def test_existing_maps_are_refused_without_overwrite(tools, archive, prefix):
    tools.t_rast_import(input=str(archive), output=prefix, basename=prefix, flags="o")

    text = _refused(
        tools, input=str(archive), output=f"{prefix}_2", basename=prefix, flags="o"
    )

    assert f"Unable to import/link raster map <{prefix}_1> from file ime_a.tif" in text


def test_the_maps_keep_their_names_without_a_basename_and_clash(tools, archive, prefix):
    # The names in the archive are those of the exported maps, which still
    # exist in this project.
    text = _refused(tools, input=str(archive), output=prefix, flags="o")

    assert "Unable to import/link raster map <ime_a> from file ime_a.tif" in text


def test_a_file_without_projection_needs_the_o_flag_in_an_unprojected_project(
    tools, archive, prefix
):
    text = _refused(tools, input=str(archive), output=prefix, basename=prefix)

    assert f"Unable to import/link raster map <{prefix}_1> from file ime_a.tif" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_projection_that_differs_is_refused_without_the_o_flag(
    archive, prefix, tmp_path
):
    with project_session(tmp_path / "other") as session:
        other = Tools(session=session)
        other.g_proj(flags="c", epsg=3358)

        text = _refused(other, input=str(archive), output=prefix, basename=prefix)

        other.t_rast_import(
            input=str(archive), output=prefix, basename=prefix, flags="o"
        )

    assert "Projection information does not match. Aborting." in text


def test_today_an_unprojected_archive_cannot_create_a_project(
    tools, archive, prefix, tmp_path
):
    # The archive of an unprojected project holds "XY location (unprojected)"
    # as its projection, which the library hands to gs.create_location() as a
    # PROJ string.
    text = _refused(
        tools,
        input=str(archive),
        output=prefix,
        basename=prefix,
        project=f"{prefix}_new",
        directory=str(tmp_path),
    )

    assert "Can't parse PROJ.4-style parameter string" in text


@pytest.mark.xfail(
    strict=True,
    reason='t.rast.import cannot create a project for an unprojected archive, it passes "XY location (unprojected)" as a PROJ string',
)
def test_an_unprojected_archive_creates_an_unprojected_project(
    tools, archive, prefix, tmp_path
):
    # The manual takes any archive of t.rast.export, and project= creates a
    # new project for it.
    gisdbase = Path(tools.g_gisenv(get="GISDBASE").stdout.strip())

    tools.t_rast_import(
        input=str(archive),
        output=prefix,
        basename=prefix,
        project=f"{prefix}_new",
        directory=str(tmp_path),
    )

    assert (gisdbase / f"{prefix}_new" / "PERMANENT" / "cell").is_dir()
