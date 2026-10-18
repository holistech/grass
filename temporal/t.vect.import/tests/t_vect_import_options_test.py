"""Test the options and flags of t.vect.import that the round trips do not use

The archives come from t.vect.export (conftest.py): vi_1 (January 2001) and
vi_2 (February 2001), each with two points.
"""

from datetime import datetime
from pathlib import Path

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import Tools

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


def _import(tools, archive, prefix, tmp_path, **options):
    options.setdefault("basename", prefix)
    options.setdefault("directory", str(tmp_path))
    flags = options.pop("flags", "") + "o"
    tools.t_vect_import(input=str(archive), output=prefix, flags=flags, **options)
    return list_maps(tools, "stvds", prefix)


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_today_the_numbers_of_the_new_maps_start_at_two(
    tools, archives, prefix, tmp_path, fmt
):
    # stds_import.py counts the lines with enumerate(list_file, 1) and still
    # adds 1 (the same as in t.rast.import).
    rows = _import(tools, archives[fmt], prefix, tmp_path)

    assert [row.name for row in rows] == [f"{prefix}_2", f"{prefix}_3"]


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_the_numbers_of_the_new_maps_start_at_one(
    tools, archives, prefix, tmp_path, fmt
):
    rows = _import(tools, archives[fmt], prefix, tmp_path)

    assert [row.name for row in rows] == [f"{prefix}_1", f"{prefix}_2"]


def test_title_and_description_are_set(tools, archives, prefix, tmp_path):
    _import(
        tools,
        archives["pack"],
        prefix,
        tmp_path,
        title="My title",
        description="My description",
    )

    text = tools.t_info(type="stvds", input=prefix).stdout
    assert "| My title" in text
    assert "| My description" in text


def test_the_extraction_directory_keeps_the_extracted_files(
    tools, archives, prefix, tmp_path
):
    work = tmp_path / "work"
    work.mkdir()

    _import(tools, archives["GML"], prefix, tmp_path, directory=str(work))

    # A GML file is read from the directory, the pack files are unpacked there
    assert {"vi_1.xml", "vi_2.xml", "list.txt", "init.txt", "proj.txt"} <= {
        path.name for path in work.iterdir()
    }


def _region_after(archives, fmt, prefix, tmp_path, flags):
    with project_session(tmp_path / "other") as session:
        other = Tools(session=session)

        _import(other, archives[fmt], prefix, tmp_path, flags=flags)

        return other.g_region(flags="dg").keyval


# A new unprojected project has a default region of one cell from (0, 0) to
# (1, 1); the points lie from (1, 1) to (2, 2), so the extended region runs
# from (0, 0) to (2, 2).
DEFAULT = {"n": 1, "s": 0, "w": 0, "e": 1}
EXTENDED = {"n": 2, "s": 0, "w": 0, "e": 2}


def _extent(region):
    return {key: region[key] for key in DEFAULT}


@pytest.mark.parametrize("fmt", ["GML", "pack"])
def test_without_the_e_flag_the_region_stays(archives, prefix, tmp_path, fmt):
    region = _region_after(archives, fmt, prefix, tmp_path, "")

    assert _extent(region) == DEFAULT


def test_the_e_flag_extends_the_default_region_of_the_project(
    archives, prefix, tmp_path
):
    region = _region_after(archives, "GML", prefix, tmp_path, "e")

    assert _extent(region) == EXTENDED


def test_today_the_e_flag_does_not_extend_the_region_for_a_pack_archive(
    archives, prefix, tmp_path
):
    # stds_import.py hands exp to the GML import only.
    region = _region_after(archives, "pack", prefix, tmp_path, "e")

    assert _extent(region) == DEFAULT


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_e_flag_extends_the_region_for_a_pack_archive(archives, prefix, tmp_path):
    region = _region_after(archives, "pack", prefix, tmp_path, "e")

    assert _extent(region) == EXTENDED


def _run(archive, prefix, tmp_path, **options):
    """t.vect.import in a new project, which reports its messages"""
    with project_session(tmp_path / "other") as session:
        other = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        result = other.t_vect_import(
            input=str(archive), output=prefix, directory=str(tmp_path), **options
        )
        return message(result), list_maps(other, "stvds", prefix)


def test_without_the_o_flag_the_projection_is_ignored_with_a_warning(
    archives, prefix, tmp_path
):
    text, rows = _run(archives["GML"], prefix, tmp_path)

    assert "Re-projection on import is currently not supported" in text
    assert [row.name for row in rows] == ["vi_1", "vi_2"]


def test_with_the_o_flag_there_is_no_warning(archives, prefix, tmp_path):
    text, _ = _run(archives["GML"], prefix, tmp_path, flags="o")

    assert "Re-projection on import" not in text


@pytest.fixture(scope="module")
def projected_archive(tmp_path_factory):
    """An archive made in a project with a real CRS, which a new project needs

    A new project is created from the projection file of the archive, and the
    placeholder text of an unprojected project cannot be read as a CRS.
    """
    base = tmp_path_factory.mktemp("vi_projected")
    with project_session(base / "source") as session:
        source = Tools(session=session)
        source.g_proj(flags="c", epsg=3358)
        vector_points(source, "vip_a", [(1, 1)], attributes={"value": [5]})
        register_stds(
            source,
            "stvds",
            "vip_in",
            [MapSpec("vip_a", None, datetime(2001, 1, 1), datetime(2001, 2, 1))],
        )
        path = base / "vip.tar"
        source.t_vect_export(input="vip_in", output=str(path), compression="no")
    return path


def _gisdbase(tools):
    return Path(tools.g_gisenv(get="GISDBASE").stdout.strip())


def test_the_c_flag_creates_the_project_and_imports_nothing(
    tools, projected_archive, prefix, tmp_path
):
    created = _gisdbase(tools) / f"{prefix}_new"

    tools.t_vect_import(
        input=str(projected_archive),
        output=prefix,
        basename=prefix,
        flags="c",
        project=created.name,
        directory=str(tmp_path),
    )

    assert (created / "PERMANENT" / "PROJ_INFO").exists()
    assert not (created / "PERMANENT" / "vector").exists()


def test_a_new_project_gets_the_maps(tools, projected_archive, prefix, tmp_path):
    created = _gisdbase(tools) / f"{prefix}_new"

    tools.t_vect_import(
        input=str(projected_archive),
        output=prefix,
        basename=prefix,
        project=created.name,
        directory=str(tmp_path),
    )

    assert sorted(
        path.name for path in (created / "PERMANENT" / "vector").iterdir()
    ) == [
        f"{prefix}_2",
    ]


def test_overwrite_replaces_the_dataset_and_the_maps(tools, archives, prefix, tmp_path):
    _import(tools, archives["pack"], prefix, tmp_path)

    rows = _import(tools, archives["pack"], prefix, tmp_path, overwrite=True)

    assert [row.name for row in rows] == [f"{prefix}_2", f"{prefix}_3"]
