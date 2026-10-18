"""Test the options and flags of t.rast.import that the round trips do not use

The archive comes from t.rast.export. It holds two monthly maps on a region of
two rows and three columns: im_a with 10 in every cell (January) and im_b with
7 in every cell (February). All imports use -o, because the project is
unprojected and the files carry no projection.
"""

from datetime import datetime
from pathlib import Path

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import cell_values, list_maps, stds_info
from grass.temporal.testing.session import project_session
from grass.tools import Tools

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def archive(tools, tmp_path_factory):
    """The path of an uncompressed archive of the dataset described above"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "im_in",
        [
            MapSpec("im_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("im_b", "7", datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    path = tmp_path_factory.mktemp("im_archive") / "im.tar"
    tools.t_rast_export(input="im_in", output=str(path), compression="no")
    return path


@pytest.fixture(autouse=True)
def _work_in_tmp_path(tools, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield
    # Two tests move the region; the next test needs the region of the archive.
    small_region(tools, 2, 3)


def _import(tools, archive, prefix, **options):
    options.setdefault("basename", prefix)
    flags = options.pop("flags", "") + "o"
    tools.t_rast_import(input=str(archive), output=prefix, flags=flags, **options)
    return list_maps(tools, "strds", prefix)


def test_the_maps_have_the_times_and_cells_of_the_exported_ones(tools, archive, prefix):
    rows = _import(tools, archive, prefix)

    assert [(row.start, row.end) for row in rows] == [
        ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
    ]
    assert [cell_values(tools, row.name) for row in rows] == [[10.0] * 6, [7.0] * 6]


def test_today_the_numbers_of_the_new_maps_start_at_two(tools, archive, prefix):
    rows = _import(tools, archive, prefix)

    assert [row.name for row in rows] == [f"{prefix}_2", f"{prefix}_3"]


def test_title_and_description_are_set(tools, archive, prefix):
    _import(tools, archive, prefix, title="My title", description="My description")

    text = tools.t_info(type="strds", input=prefix).stdout
    assert "| My title" in text
    assert "| My description" in text


def test_the_extraction_directory_keeps_the_extracted_files(
    tools, archive, prefix, tmp_path
):
    work = tmp_path / "work"
    work.mkdir()

    _import(tools, archive, prefix, directory=str(work))

    assert {"im_a.tif", "im_b.tif", "list.txt", "init.txt", "proj.txt"} <= {
        path.name for path in work.iterdir()
    }


def test_without_a_directory_nothing_is_left_in_the_current_directory(
    tools, archive, prefix, tmp_path
):
    _import(tools, archive, prefix)

    assert list(tmp_path.iterdir()) == []


def test_memory_is_passed_on_and_the_cells_are_unchanged(tools, archive, prefix):
    rows = _import(tools, archive, prefix, memory=50)

    assert [cell_values(tools, row.name) for row in rows] == [[10.0] * 6, [7.0] * 6]


def _region(tools):
    return {
        key: float(value)
        for key, value in tools.g_region(flags="g").keyval.items()
        if key in {"n", "s", "e", "w"}
    }


def test_the_r_flag_sets_the_region_from_the_last_map(tools, archive, prefix):
    tools.g_region(n=100, s=90, w=50, e=60, res=1)

    _import(tools, archive, prefix, flags="r")

    # Both maps cover the cells of the exported region, rows 0 to 2 and
    # columns 0 to 3
    assert _region(tools) == {"n": 2.0, "s": 0.0, "w": 0.0, "e": 3.0}


def test_without_the_r_flag_the_region_stays(tools, archive, prefix):
    tools.g_region(n=100, s=90, w=50, e=60, res=1)

    _import(tools, archive, prefix)

    assert _region(tools) == {"n": 100.0, "s": 90.0, "w": 50.0, "e": 60.0}


def test_the_dataset_has_the_extent_of_the_maps(tools, archive, prefix):
    _import(tools, archive, prefix)

    info = stds_info(tools, "strds", prefix)
    assert (info["north"], info["south"], info["east"], info["west"]) == (2, 0, 3, 0)
    assert info["number_of_maps"] == 2


def _info(tools, name):
    return tools.r_info(map=name, flags="e").keyval


def test_without_the_l_flag_the_cells_are_copied(tools, archive, prefix):
    (row, _) = _import(tools, archive, prefix)

    assert _info(tools, row.name)["maptype"] == "raster"


def test_the_l_flag_links_the_files_of_the_extraction_directory(
    tools, archive, prefix, tmp_path
):
    work = tmp_path / "work"
    work.mkdir()

    rows = _import(tools, archive, prefix, flags="l", directory=str(work))

    info = _info(tools, rows[0].name)
    assert info["maptype"] == "GDAL-link"
    assert info["source1"] == f'"{work / "im_a.tif"} band 1"'
    assert [cell_values(tools, row.name) for row in rows] == [[10.0] * 6, [7.0] * 6]


@pytest.mark.parametrize(
    ("flags", "extent"),
    [
        ("", {"n": 1, "s": 0, "w": 0, "e": 1}),
        ("e", {"n": 2, "s": 0, "w": 0, "e": 3}),
    ],
)
def test_the_e_flag_extends_the_default_region_of_the_project(
    archive, prefix, tmp_path, flags, extent
):
    # A new unprojected project has a default region of one cell from (0, 0)
    # to (1, 1); the maps cover (0, 0) to (3, 2).
    with project_session(tmp_path / "other") as session:
        other = Tools(session=session)

        other.t_rast_import(
            input=str(archive),
            output=prefix,
            basename=prefix,
            flags="o" + flags,
            directory=str(tmp_path),
        )

        region = other.g_region(flags="dg").keyval
    assert {key: region[key] for key in extent} == extent


@pytest.fixture(scope="module")
def projected_archive(tmp_path_factory):
    """An archive made in a project with a real CRS, which a new project needs

    A new project is created from the projection file of the archive, and the
    placeholder text of an unprojected project cannot be read as a CRS.
    """
    base = tmp_path_factory.mktemp("im_projected")
    with project_session(base / "source") as session:
        source = Tools(session=session)
        source.g_proj(flags="c", epsg=3358)
        small_region(source, 2, 3)
        create_stds(
            source,
            "strds",
            "imp_in",
            [MapSpec("imp_a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1))],
        )
        path = base / "imp.tar"
        source.t_rast_export(input="imp_in", output=str(path), compression="no")
    return path


def _gisdbase(tools):
    return Path(tools.g_gisenv(get="GISDBASE").stdout.strip())


def test_the_c_flag_creates_the_project_and_imports_nothing(
    tools, projected_archive, prefix, tmp_path
):
    created = _gisdbase(tools) / f"{prefix}_new"

    tools.t_rast_import(
        input=str(projected_archive),
        output=prefix,
        basename=prefix,
        flags="c",
        project=created.name,
        directory=str(tmp_path),
    )

    assert (created / "PERMANENT" / "PROJ_INFO").exists()
    assert not (created / "PERMANENT" / "cell").exists()


def test_a_new_project_gets_the_maps(tools, projected_archive, prefix, tmp_path):
    created = _gisdbase(tools) / f"{prefix}_new"

    tools.t_rast_import(
        input=str(projected_archive),
        output=prefix,
        basename=prefix,
        project=created.name,
        directory=str(tmp_path),
    )

    assert sorted(path.name for path in (created / "PERMANENT" / "cell").iterdir()) == [
        f"{prefix}_2",
    ]
