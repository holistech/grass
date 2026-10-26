"""Test export_stds for the parts the tools do not reach

The tools cover the archives of raster and vector datasets. This module adds
the 3D raster datasets, which have no tool, time instants, the whole text of
the readme file and the refusals of the single exporters.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import tarfile
from datetime import datetime
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal import stds_export
from grass.exceptions import CalledModuleError, ScriptError
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    register_stds,
    small_region,
    vector_points,
)
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

# Both maps of a dataset are time instants, so the end of the list line is
# that of the start.
INSTANTS = [
    (datetime(2001, 1, 1), None),
    (datetime(2001, 2, 1), datetime(2001, 3, 1)),
]

TAIL = """\
     proj.txt -- Projection information in PROJ.4 format
     init.txt -- GRASS space time {kind} dataset information
     list.txt -- Time series file, lists all maps by name with interval
                 time stamps in ISO-Format. Field separator is |
 metadata.txt -- The output of t.info
   readme.txt -- This file
"""

README_HEADS = {
    ("strds", "GTiff"): (
        "This space time raster dataset was exported with t.rast.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "       *.tif  -- GeoTIFF raster files\n"
        "     *.color  -- GRASS raster color rules\n"
    ),
    ("strds", "AAIGrid"): (
        "This space time raster dataset was exported with t.rast.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "       *.asc  -- Arc/Info ASCII Grid raster files\n"
        "     *.color  -- GRASS raster color rules\n"
    ),
    ("strds", "pack"): (
        "This space time raster dataset was exported with t.rast.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "      *.pack  -- GRASS raster files packed with r.pack\n"
    ),
    ("stvds", "GML"): (
        "This space time vector dataset was exported with t.vect.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "       *.xml  -- Vector GML files\n"
    ),
    ("stvds", "GPKG"): (
        "This space time vector dataset was exported with t.vect.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "      *.gpkg  -- Vector GeoPackage files\n"
    ),
    ("stvds", "pack"): (
        "This space time vector dataset was exported with t.vect.export of GRASS 8\n"
        "\n"
        "Files:\n"
        "      *.pack  -- GRASS vector files packed with v.pack\n"
    ),
    ("str3ds", "pack"): (
        "This space time 3D raster dataset was exported with t.rast3d.export of "
        "GRASS 8\n"
        "\n"
        "Files:\n"
        "      *.pack  -- GRASS 3D raster files packed with r3.pack\n"
    ),
}

MAP_KIND = {"strds": "raster", "stvds": "vector", "str3ds": "raster3d"}


@pytest.fixture(autouse=True)
def _raise_on_error():
    # gs.fatal() ends the process unless the caller asks for an exception.
    saved = gs.get_raise_on_error()
    gs.set_raise_on_error(True)
    yield
    gs.set_raise_on_error(saved)


@pytest.fixture(autouse=True)
def _forget_exported_maps(monkeypatch):
    monkeypatch.setattr(stds_export, "exported_maps", {})


@pytest.fixture
def failing_modules(monkeypatch):
    """The names of the modules that fail when run; r3.pack is made up

    GRASS has no r3.pack, so a 3D raster map is "packed" by an empty file of
    the name the exporter expects.
    """
    failing = set()
    run_command = gs.run_command

    def run(name, *args, **kwargs):
        if name in failing:
            raise CalledModuleError(name, "", 1)
        if name == "r3.pack":
            Path(f"{kwargs['input']}.pack").touch()
            return None
        return run_command(name, *args, **kwargs)

    monkeypatch.setattr(gs, "run_command", run)
    return failing


@pytest.fixture(scope="module")
def datasets(temporal_module_session):
    """One dataset of every type, each with a time instant and an interval"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    small_region(tools, 2, 3, depths=2)
    create_stds(
        tools,
        "strds",
        "exr",
        [
            MapSpec(f"exr{number}", number, start, end)
            for number, (start, end) in enumerate(INSTANTS, 1)
        ],
    )
    create_stds(
        tools,
        "str3ds",
        "ex3",
        [
            MapSpec(f"ex3{number}", number, start, end)
            for number, (start, end) in enumerate(INSTANTS, 1)
        ],
    )
    for number in (1, 2):
        vector_points(tools, f"exv{number}", [(number, 1)])
    register_stds(
        tools,
        "stvds",
        "exv",
        [
            MapSpec(f"exv{number}", None, start, end)
            for number, (start, end) in enumerate(INSTANTS, 1)
        ],
    )
    return {"strds": "exr", "stvds": "exv", "str3ds": "ex3"}


def _export(tmp_path, name, type_, format_, **kwargs):
    archive = tmp_path / "out.tar"
    tgis.export_stds(name, str(archive), "no", tmp_path, None, format_, type_, **kwargs)
    return archive


def _text(archive, member):
    with tarfile.open(archive) as tar:
        return tar.extractfile(member).read().decode()


@pytest.mark.parametrize(("type_", "format_"), list(README_HEADS))
def test_the_readme_names_the_files_of_the_format(
    datasets, tmp_path, type_, format_, failing_modules
):
    archive = _export(tmp_path, datasets[type_], type_, format_)

    expected = README_HEADS[type_, format_] + TAIL.format(kind=MAP_KIND[type_])
    assert _text(archive, "readme.txt") == expected


def test_a_3d_raster_dataset_is_exported_with_r3_pack(
    datasets, tmp_path, failing_modules
):
    archive = _export(tmp_path, "ex3", "str3ds", "pack")

    with tarfile.open(archive) as tar:
        names = tar.getnames()
    assert names == [
        "ex31.pack",
        "ex32.pack",
        "list.txt",
        "proj.txt",
        "init.txt",
        "readme.txt",
        "metadata.txt",
    ]
    # The end of a time instant is its start.
    assert _text(archive, "list.txt").splitlines() == [
        "ex31|2001-01-01 00:00:00|2001-01-01 00:00:00",
        "ex32|2001-02-01 00:00:00|2001-03-01 00:00:00",
    ]
    init = dict(line.split("=") for line in _text(archive, "init.txt").splitlines())
    assert init["stds_type"] == "str3ds"
    assert init["number_of_maps"] == "2"
    assert init["format"] == "pack"


@pytest.mark.parametrize(
    ("type_", "format_", "layer"),
    [
        ("strds", "GTiff", ""),
        ("strds", "AAIGrid", ""),
        ("strds", "pack", ""),
        ("stvds", "GML", ""),
        ("stvds", "GPKG", ""),
        ("stvds", "pack", ":1"),
    ],
)
def test_the_end_of_a_time_instant_is_its_start(
    datasets, tmp_path, type_, format_, layer, failing_modules
):
    archive = _export(tmp_path, datasets[type_], type_, format_)

    name = datasets[type_]
    last = "|None" if type_ == "strds" else ""
    assert _text(archive, "list.txt").splitlines() == [
        f"{name}1{layer}|2001-01-01 00:00:00|2001-01-01 00:00:00{last}",
        f"{name}2{layer}|2001-02-01 00:00:00|2001-03-01 00:00:00{last}",
    ]


@pytest.mark.parametrize(
    ("type_", "format_", "module", "message"),
    [
        ("strds", "GTiff", "r.out.gdal", "Unable to export raster map <exr1>"),
        ("strds", "AAIGrid", "r.out.gdal", "Unable to export raster map <exr1>"),
        (
            "strds",
            "pack",
            "r.pack",
            "Unable to export raster map <exr1> with r.pack",
        ),
        (
            "strds",
            "GTiff",
            "r.colors.out",
            "Unable to export color rules for raster map <exr1> r.out.gdal",
        ),
        (
            "stvds",
            "GML",
            "v.out.ogr",
            "Unable to export vector map <exv1> as GML with v.out.ogr",
        ),
        (
            "stvds",
            "GPKG",
            "v.out.ogr",
            "Unable to export vector map <exv1> as GPKG with v.out.ogr",
        ),
        (
            "stvds",
            "pack",
            "v.pack",
            "Unable to export vector map <exv1> with v.pack",
        ),
        (
            "str3ds",
            "pack",
            "r3.pack",
            "Unable to export raster map <ex31> with r3.pack",
        ),
    ],
)
def test_a_module_that_fails_stops_the_export_with_a_message(
    datasets, tmp_path, failing_modules, type_, format_, module, message
):
    failing_modules.add(module)
    before = Path.cwd()

    with pytest.raises(ScriptError, match=message):
        _export(tmp_path, datasets[type_], type_, format_)

    # The work directory is gone and the process is where it was.
    assert Path.cwd() == before
    assert not [path for path in tmp_path.iterdir() if path.is_dir()]
    assert not (tmp_path / "out.tar").exists()


def test_an_output_directory_that_cannot_be_written_is_refused(datasets, tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        with pytest.raises(ScriptError, match="is not writable"):
            tgis.export_stds(
                "exr", str(locked / "out.tar"), "no", tmp_path, None, "pack", "strds"
            )
    finally:
        locked.chmod(0o700)
    assert not list(locked.iterdir())
