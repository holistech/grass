"""Test import_stds and export_stds in the process that calls them

The tools run both in a process of their own, so a change of the working
directory or of GISRC that outlives a failed call shows only when the library
is called in the test process. The sessions here are real: the target project
differs from the one the archives were made in.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import io
import os
import tarfile
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal import stds_import
from grass.pygrass.messages import FatalError
from grass.exceptions import CalledModuleError
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    register_stds,
    small_region,
    vector_points,
)
from grass.temporal.testing.session import project_session, temporal_session
from grass.tools import Tools

EPSG = 3358


def _tools(session):
    return Tools(session=session, consistent_return_value=True, overwrite=True)


def _process_state():
    """The working directory, GISRC and mapset the process sees now"""
    return Path.cwd(), os.environ.get("GISRC"), gs.gisenv()["MAPSET"]


def _changed(source, target, name, data=None):
    """Copy the tar archive source to target; drop member name or give it data"""
    with tarfile.open(source) as old, tarfile.open(target, "w") as new:
        for member in old.getmembers():
            if Path(member.name).name != name:
                new.addfile(member, old.extractfile(member))
            elif data is not None:
                member.size = len(data)
                new.addfile(member, io.BytesIO(data))
    return target


def _member(archive, name):
    with tarfile.open(archive) as tar:
        return tar.extractfile(name).read()


@pytest.fixture
def failing_modules(monkeypatch):
    """The names of the modules that fail when run, once

    The restoring of the session runs t.connect again, which must not fail
    on top of the first failure.
    """
    failing = set()
    run_command = gs.run_command

    def run(name, *args, **kwargs):
        if name in failing:
            failing.discard(name)
            raise CalledModuleError(name, "", 1)
        return run_command(name, *args, **kwargs)

    monkeypatch.setattr(gs, "run_command", run)
    return failing


@pytest.fixture(autouse=True)
def _restore_working_directory(monkeypatch):
    # A call that leaves its working directory must not move the later tests.
    monkeypatch.chdir(Path.cwd())


@pytest.fixture(scope="module")
def archives(tmp_path_factory):
    """Archives of a raster and a vector dataset made in a project with a CRS

    "GTiff", "AAIGrid" and "pack" hold two raster maps in that format;
    "vector" holds two vector maps as v.pack files, "GML" and "GPKG" the same
    in the format of their name.
    """
    base = tmp_path_factory.mktemp("stds_io_archives")
    made = {}
    with project_session(base / "source") as session:
        tools = _tools(session)
        tools.g_proj(flags="c", epsg=EPSG)
        small_region(tools, 2, 3)
        create_stds(
            tools,
            "strds",
            "src",
            [
                MapSpec("srca", "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
                MapSpec("srcb", "20", datetime(2001, 2, 1), datetime(2001, 3, 1)),
            ],
        )
        for format_ in ("GTiff", "AAIGrid", "pack"):
            path = base / f"{format_}.tar"
            tools.t_rast_export(
                input="src",
                output=str(path),
                compression="no",
                format=format_,
                directory=str(base),
            )
            made[format_] = path
        for number in (1, 2):
            vector_points(tools, f"vsrc{number}", [(number, 1), (number, 2)])
        register_stds(
            tools,
            "stvds",
            "vsrc",
            [
                MapSpec("vsrc1", None, datetime(2001, 1, 1), datetime(2001, 2, 1)),
                MapSpec("vsrc2", None, datetime(2001, 2, 1), datetime(2001, 3, 1)),
            ],
        )
        for format_, key in (("pack", "vector"), ("GML", "GML"), ("GPKG", "GPKG")):
            path = base / f"{key}.tar"
            tools.t_vect_export(
                input="vsrc",
                output=str(path),
                compression="no",
                format=format_,
                directory=str(base),
            )
            made[key] = path
    return made


@pytest.fixture
def target(tmp_path):
    """A session in an unprojected project, different from the archives' one"""
    with temporal_session(tmp_path / "target") as session:
        yield session


def test_a_later_map_that_cannot_be_read_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    broken = _changed(
        archives["GTiff"], tmp_path / "broken.tar", "srcb.tif", b"no image"
    )
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to import/link raster map"):
        tgis.import_stds(
            str(broken),
            "out",
            tmp_path,
            overr=True,
            base="imp",
        )

    assert _process_state() == before


def test_a_later_map_that_cannot_be_read_in_a_new_project_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    broken = _changed(
        archives["GTiff"], tmp_path / "broken.tar", "srcb.tif", b"no image"
    )
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to import/link raster map"):
        tgis.import_stds(str(broken), "out", tmp_path, location="newproject")

    assert _process_state() == before
    # The new project exists, the failed import does not remove it.
    assert (Path(gs.gisenv()["GISDBASE"]) / "newproject" / "PERMANENT").is_dir()


def test_a_missing_file_in_a_new_project_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    broken = _changed(archives["GTiff"], tmp_path / "broken.tar", "srcb.tif")
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to find GeoTIFF raster file"):
        tgis.import_stds(str(broken), "out", tmp_path, location="newproject")

    assert _process_state() == before


def test_a_new_project_without_import_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    before = _process_state()

    tgis.import_stds(
        str(archives["GTiff"]), "out", tmp_path, location="newproject", create=True
    )

    assert _process_state() == before
    assert (Path(gs.gisenv()["GISDBASE"]) / "newproject" / "PERMANENT").is_dir()


@pytest.mark.parametrize("format_", ["GTiff", "AAIGrid", "pack"])
def test_the_files_of_every_map_must_be_in_the_archive(
    archives, target, tmp_path, format_
):
    suffix = {"GTiff": ".tif", "AAIGrid": ".asc", "pack": ".pack"}[format_]
    broken = _changed(archives[format_], tmp_path / "broken.tar", "srcb" + suffix)
    word = {
        "GTiff": "GeoTIFF raster file",
        "AAIGrid": "AAIGrid raster file",
        "pack": "GRASS package file",
    }[format_]

    with pytest.raises(FatalError, match=f"Unable to find {word} <srcb{suffix}>"):
        tgis.import_stds(str(broken), "out", tmp_path, overr=True)


@pytest.mark.parametrize(
    ("format_", "suffix", "word"),
    [
        ("GML", ".xml", "GML vector file"),
        ("GPKG", ".gpkg", "GPKG vector file"),
        ("vector", ".pack", "GRASS package file"),
    ],
)
def test_the_files_of_every_vector_map_must_be_in_the_archive(
    archives, target, tmp_path, format_, suffix, word
):
    broken = _changed(archives[format_], tmp_path / "broken.tar", "vsrc2" + suffix)

    with pytest.raises(FatalError, match=f"Unable to find {word} <vsrc2{suffix}>"):
        tgis.import_stds(str(broken), "out", tmp_path, stds_type="stvds", overr=True)


def test_an_unknown_format_is_refused(archives, target, tmp_path):
    init = _member(archives["GTiff"], "init.txt").replace(b"format=GTiff", b"format=x")
    changed = _changed(archives["GTiff"], tmp_path / "x.tar", "init.txt", init)

    with pytest.raises(FatalError, match="Unsupported input format"):
        tgis.import_stds(str(changed), "out", tmp_path, overr=True)


def test_a_wrong_number_of_maps_in_the_init_file_is_refused(archives, target, tmp_path):
    init = _member(archives["GTiff"], "init.txt")
    changed = _changed(
        archives["GTiff"],
        tmp_path / "x.tar",
        "init.txt",
        init.replace(b"number_of_maps=2", b"number_of_maps=5"),
    )

    with pytest.raises(FatalError, match="Number of maps mismatch"):
        tgis.import_stds(str(changed), "out", tmp_path, overr=True)


def test_blank_lines_in_the_list_and_init_file_are_skipped(archives, target, tmp_path):
    # The number of maps is compared with the number of lines of the list
    # file, blank ones included, so the init file must count the blank line.
    changed = _changed(
        archives["GTiff"],
        tmp_path / "x.tar",
        "list.txt",
        _member(archives["GTiff"], "list.txt") + b"\n",
    )
    init = _member(changed, "init.txt").replace(
        b"number_of_maps=2", b"number_of_maps=3"
    )
    changed = _changed(changed, tmp_path / "y.tar", "init.txt", b"\n" + init + b"\n\n")

    tgis.import_stds(str(changed), "out", tmp_path, overr=True)

    assert gs.read_command("g.list", type="raster").split() == ["srca", "srcb"]


@pytest.mark.parametrize(
    ("archive", "options", "module", "message"),
    [
        (
            "GTiff",
            {},
            "r.in.gdal",
            "Unable to import/link raster map <srca> from file srca.tif",
        ),
        (
            "GTiff",
            {"link": True},
            "r.external",
            "Unable to import/link raster map <srca> from file srca.tif",
        ),
        (
            "GTiff",
            {},
            "r.colors",
            "Unable to set the color rules for raster map <srca>",
        ),
        (
            "pack",
            {},
            "r.unpack",
            "Unable to unpack raster map <srca> from file srca.pack",
        ),
        (
            "GML",
            {"stds_type": "stvds"},
            "v.in.ogr",
            "Unable to import vector map <vsrc1> from file vsrc1.xml",
        ),
        (
            "GPKG",
            {"stds_type": "stvds", "link": True},
            "v.external",
            "Unable to import vector map <vsrc1> from file vsrc1.gpkg",
        ),
        (
            "vector",
            {"stds_type": "stvds"},
            "v.unpack",
            "Unable to unpack vector map <vsrc1> from file vsrc1.pack",
        ),
    ],
)
def test_a_module_that_fails_stops_the_import_with_a_message(
    archives, target, tmp_path, failing_modules, archive, options, module, message
):
    failing_modules.add(module)

    with pytest.raises(FatalError, match=message):
        tgis.import_stds(str(archives[archive]), "out", tmp_path, overr=True, **options)

    assert "out" not in gs.read_command("t.list", type="strds").split()


def test_a_new_project_without_the_temporal_database_is_refused(
    archives, target, tmp_path, failing_modules
):
    failing_modules.add("t.connect")

    with pytest.raises(FatalError, match="Unable to create default temporal"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, location="newproject")


def test_an_environment_that_cannot_be_made_is_refused(
    archives, target, tmp_path, monkeypatch
):
    def refuse(*args):
        msg = "no room"
        raise OSError(msg)

    monkeypatch.setattr(gs, "create_environment", refuse)

    with pytest.raises(
        FatalError, match="Unable to create environment for location newproject"
    ):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, location="newproject")


def test_an_extraction_without_the_data_filter_is_refused(
    archives, target, tmp_path, monkeypatch
):
    monkeypatch.delattr(tarfile, "data_filter")

    with pytest.raises(FatalError, match="Extracting may be unsafe"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, overr=True)


def test_an_aaigrid_file_without_projection_is_imported_into_a_project_with_one(
    archives, tmp_path
):
    with temporal_session(tmp_path / "target", crs=f"EPSG:{EPSG}"):
        tgis.import_stds(str(archives["AAIGrid"]), "out", tmp_path)

        assert gs.read_command("g.list", type="raster").split() == ["srca", "srcb"]


def test_the_region_is_set_from_the_last_map_if_asked(archives, tmp_path):
    with temporal_session(tmp_path / "target", crs=f"EPSG:{EPSG}"):
        before = gs.region()

        tgis.import_stds(
            str(archives["pack"]), "out", tmp_path, set_current_region=True
        )

        region = gs.region()
        assert (region["rows"], region["cols"]) == (2, 3)
        assert (before["rows"], before["cols"]) != (2, 3)


def test_an_archive_of_another_dataset_type_is_refused(archives, target, tmp_path):
    with pytest.raises(FatalError, match="wrong space time dataset type"):
        tgis.import_stds(str(archives["vector"]), "out", tmp_path, overr=True)


def _gisdbase():
    return Path(gs.gisenv()["GISDBASE"])


def test_a_projection_that_differs_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    before = _process_state()

    with pytest.raises(FatalError, match="Projection information does not match"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path)

    assert _process_state() == before


def test_a_project_that_cannot_be_made_leaves_the_process_as_it_was(
    archives, target, tmp_path
):
    (_gisdbase() / "taken").mkdir()
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to create location taken"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, location="taken")

    assert _process_state() == before


def test_an_environment_that_cannot_be_made_leaves_the_process_as_it_was(
    archives, target, tmp_path, monkeypatch
):
    def refuse(*args):
        msg = "no room"
        raise OSError(msg)

    monkeypatch.setattr(gs, "create_environment", refuse)
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to create environment"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, location="newproject")

    assert _process_state() == before


def test_a_new_project_without_the_temporal_database_leaves_the_process_as_it_was(
    archives, target, tmp_path, failing_modules
):
    failing_modules.add("t.connect")
    before = _process_state()

    with pytest.raises(FatalError, match="Unable to create default temporal"):
        tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, location="newproject")

    assert _process_state() == before


def test_the_vector_maps_of_one_archive_can_be_imported_twice_in_one_process(
    archives, tmp_path
):
    # The second import is into a project of its own, so the maps are not
    # there yet and must be imported. v.unpack needs a project with a CRS.
    for number in (1, 2):
        with temporal_session(tmp_path / f"target{number}", crs=f"EPSG:{EPSG}"):
            tgis.import_stds(
                str(archives["vector"]),
                "vout",
                tmp_path,
                stds_type="stvds",
                overr=True,
            )

            names = gs.read_command("g.list", type="vector").split()
            assert names == ["vsrc1", "vsrc2"], f"import {number}"


@pytest.fixture(scope="module")
def dotted_archive(tmp_path_factory):
    """An archive of raster maps with a dot in their name"""
    base = tmp_path_factory.mktemp("stds_io_dotted")
    with project_session(base / "source") as session:
        tools = _tools(session)
        tools.g_proj(flags="c", epsg=EPSG)
        small_region(tools, 2, 3)
        create_stds(
            tools,
            "strds",
            "dotted",
            [
                MapSpec("dot.a", "10", datetime(2001, 1, 1), datetime(2001, 2, 1)),
                MapSpec("dot.b", "20", datetime(2001, 2, 1), datetime(2001, 3, 1)),
            ],
        )
        path = base / "dotted.tar"
        tools.t_rast_export(
            input="dotted",
            output=str(path),
            compression="no",
            format="GTiff",
            directory=str(base),
        )
    return path


def test_raster_maps_with_a_dot_in_their_name_are_imported(
    dotted_archive, target, tmp_path
):
    tgis.import_stds(str(dotted_archive), "out", tmp_path, overr=True)

    assert gs.read_command("g.list", type="raster").split() == ["dot.a", "dot.b"]


@pytest.mark.parametrize("directory", [None, ""])
def test_a_new_project_without_an_extraction_directory_uses_a_temporary_one(
    archives, target, tmp_path, monkeypatch, directory
):
    # The tools pass an empty string for an option that is not given.
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)

    tgis.import_stds(
        str(archives["GTiff"]), "out", directory, location="newproject", create=True
    )

    assert (Path(gs.gisenv()["GISDBASE"]) / "newproject" / "PERMANENT").is_dir()
    # Nothing of the archive is extracted into the working directory.
    assert not list(work.iterdir())


def test_an_archive_without_color_rules_is_imported(archives, target, tmp_path):
    changed = _changed(archives["GTiff"], tmp_path / "x.tar", "srca.color")
    changed = _changed(changed, tmp_path / "y.tar", "srcb.color")

    tgis.import_stds(str(changed), "out", tmp_path, overr=True)

    assert gs.read_command("g.list", type="raster").split() == ["srca", "srcb"]


@pytest.fixture(scope="module")
def two_layer_archive(tmp_path_factory):
    """A pack archive whose list holds both layers of one vector map

    The export writes one line for such a map; the list is extended by the
    second layer here, as the pack format allows it: the whole map with all
    its layers is in the one file.
    """
    base = tmp_path_factory.mktemp("stds_io_layers")
    with project_session(base / "source") as session:
        tools = _tools(session)
        tools.g_proj(flags="c", epsg=EPSG)
        vector_points(tools, "lay_one", [(1, 1)])
        tools.v_category(
            input="lay_one", output="lay", option="add", layer=2, type="point"
        )
        tools.t_create(type="stvds", output="lay_ds", title="t", description="t")
        tools.t_register(
            type="vector",
            input="lay_ds",
            maps="lay:1,lay:2",
            start="2001-01-01",
            increment="1 months",
        )
        path = base / "lay.tar"
        tools.t_vect_export(
            input="lay_ds",
            output=str(path),
            compression="no",
            format="pack",
            directory=str(base),
        )
    listed = _member(path, "list.txt")
    changed = _changed(
        path, base / "list.tar", "list.txt", listed + b"lay:2|2001-01-01|2001-01-01\n"
    )
    init = _member(changed, "init.txt").replace(
        b"number_of_maps=1", b"number_of_maps=2"
    )
    return _changed(changed, base / "layers.tar", "init.txt", init)


def test_a_vector_map_with_two_layers_is_unpacked_once(
    two_layer_archive, tmp_path, monkeypatch
):
    unpacked = []
    run_command = gs.run_command

    def run(name, *args, **kwargs):
        if name == "v.unpack":
            unpacked.append(kwargs["output"])
        return run_command(name, *args, **kwargs)

    monkeypatch.setattr(gs, "run_command", run)
    with temporal_session(tmp_path / "target", crs=f"EPSG:{EPSG}"):
        tgis.import_stds(
            str(two_layer_archive), "out", tmp_path, stds_type="stvds", overr=True
        )

        assert gs.read_command("g.list", type="vector").split() == ["lay"]
        listed = gs.read_command("t.vect.list", input="out", columns="name,layer")
        assert listed.split()[1:] == ["lay|1", "lay|2"]
    assert unpacked == ["lay"]


@pytest.mark.parametrize("fails", [False, True])
def test_the_error_mode_of_grass_script_is_the_one_of_the_caller_afterwards(
    archives, target, tmp_path, fails
):
    # init() lets the temporal framework raise whenever grass.script raises, so
    # grass.script must not be left raising while the import runs it.
    gs.set_raise_on_error(False)
    seen = []
    init = stds_import.init

    def recording(**kwargs):
        seen.append(gs.get_raise_on_error())
        init(**kwargs)

    stds_import.init = recording
    try:
        if fails:
            with pytest.raises(FatalError):
                tgis.import_stds(str(archives["vector"]), "out", tmp_path, overr=True)
        else:
            tgis.import_stds(str(archives["GTiff"]), "out", tmp_path, overr=True)
    finally:
        stds_import.init = init

    assert seen
    assert seen == [False] * len(seen)
    assert gs.get_raise_on_error() is False
    # The framework of the session still raises, as the session set it up.
    assert tgis.get_raise_on_error() is True


def test_making_a_project_leaves_the_error_mode_of_grass_script_alone(
    archives, target, tmp_path
):
    gs.set_raise_on_error(False)

    tgis.import_stds(
        str(archives["GTiff"]), "out", tmp_path, location="modeproject", create=True
    )

    assert gs.get_raise_on_error() is False
    assert tgis.get_raise_on_error() is True
