"""Test the refusals of t.rast.import

Every refusal ends with a message and no traceback. A refusal after the
archive is read leaves no dataset and no map of the run behind, also when it
comes for a later map of the archive.
"""

import io
import tarfile
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
    text = message(error.value)
    assert "Traceback" not in text
    return text


def _nothing_made(tools, output, basename):
    """Assert that a refused run left no dataset and no map of the basename"""
    assert output not in tools.t_list(type="strds", columns="name").stdout.split()
    assert not tools.g_list(type="raster", pattern=f"{basename}*").stdout.strip()


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

    assert f"<{prefix}_1> exists. To overwrite, use the --overwrite flag" in text
    assert (
        f"{prefix}_2" not in tools.t_list(type="strds", columns="name").stdout.split()
    )


def test_a_clash_on_the_second_map_leaves_the_first_unimported(
    tools, tmp_path_factory, prefix
):
    small_region(tools, 2, 3)
    first, second = f"{prefix}_a", f"{prefix}_b"
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(first, "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec(second, "20", datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    path = tmp_path_factory.mktemp("ime_two") / "two.tar"
    tools.t_rast_export(input=f"{prefix}_in", output=str(path), compression="no")
    # Only the second map is left in the project, so only it clashes.
    tools.g_remove(type="raster", name=first, flags="f")

    text = _refused(tools, input=str(path), output=f"{prefix}_out", flags="o")

    assert f"<{second}> exists. To overwrite, use the --overwrite flag" in text
    assert not tools.g_list(type="raster", pattern=first).stdout.strip()
    assert f"{prefix}_out" not in tools.t_list(type="strds", columns="name").stdout


def test_the_maps_keep_their_names_without_a_basename_and_clash(tools, archive, prefix):
    # The names in the archive are those of the exported maps, which still
    # exist in this project.
    text = _refused(tools, input=str(archive), output=prefix, flags="o")

    assert "<ime_a> exists. To overwrite, use the --overwrite flag" in text
    assert prefix not in tools.t_list(type="strds", columns="name").stdout.split()


def test_a_file_without_projection_needs_the_o_flag_in_an_unprojected_project(
    tools, archive, prefix
):
    text = _refused(tools, input=str(archive), output=prefix, basename=prefix)

    assert f"Unable to import/link raster map <{prefix}_1> from file ime_a.tif" in text
    _nothing_made(tools, prefix, prefix)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_projection_that_differs_is_refused_without_the_o_flag(
    archive, prefix, tmp_path
):
    with project_session(tmp_path / "other") as session:
        other = Tools(session=session, consistent_return_value=True)
        other.g_proj(flags="c", epsg=3358)

        text = _refused(other, input=str(archive), output=prefix, basename=prefix)
        _nothing_made(other, prefix, prefix)

        other.t_rast_import(
            input=str(archive), output=prefix, basename=prefix, flags="o"
        )

    assert "Projection information does not match. Aborting." in text


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

    created = gisdbase / f"{prefix}_new" / "PERMANENT"
    assert (created / "cell" / f"{prefix}_1").is_file()
    # The new project has no coordinate system, as the exporting one.
    assert not (created / "PROJ_EPSG").exists()
    assert not (created / "PROJ_INFO").exists()


def test_a_dotted_output_is_refused_before_the_project_is_made(
    tools, archive, prefix, tmp_path
):
    # The name check needs no database, so it must run before anything is
    # written; otherwise a refused name leaves a new project behind.
    gisdbase = Path(tools.g_gisenv(get="GISDBASE").stdout.strip())

    text = _refused(
        tools,
        input=str(archive),
        output=f"{prefix}.dot",
        basename=prefix,
        project=f"{prefix}_dotted",
        directory=str(tmp_path),
    )

    assert "a dot is not allowed" in text
    assert not (gisdbase / f"{prefix}_dotted").exists()


def _with_times(source, target, start, end):
    """Copy the archive source to target with the times of its one map in
    list.txt replaced by start and end"""
    with tarfile.open(source) as old, tarfile.open(target, "w") as new:
        for member in old.getmembers():
            data = old.extractfile(member).read()
            if member.name == "list.txt":
                name = data.decode().split("|")[0]
                data = f"{name}|{start}|{end}\n".encode()
                member.size = len(data)
            new.addfile(member, io.BytesIO(data))


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (
            "2001-01-01 00:00:00+01:00",
            "2001-02-01 00:00:00+02:00",
            (
                "The archive holds times with the time zone offsets +01:00 and "
                "+02:00, but a space time dataset holds one offset and no daylight "
                "saving time"
            ),
        ),
        (
            "2001-01-01 00:00:00+01:00",
            "2001-02-01 00:00:00",
            (
                "The archive holds times with and without a time zone offset, such "
                "as 2001-01-01 00:00:00+01:00 and 2001-02-01 00:00:00, but a space "
                "time dataset holds only one of the two"
            ),
        ),
    ],
    ids=["two offsets", "with and without"],
)
def test_times_of_two_time_zones_are_refused_before_the_first_map(
    tools, archive, prefix, tmp_path, start, end, expected
):
    """t.register would refuse them only after every map was imported"""
    changed = tmp_path / "zones.tar"
    _with_times(archive, changed, start, end)

    text = _refused(
        tools, input=str(changed), output=prefix, basename=prefix, flags="o"
    )

    assert expected in text
    _nothing_made(tools, prefix, prefix)
