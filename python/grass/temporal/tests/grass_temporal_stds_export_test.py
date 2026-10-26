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
from grass.pygrass.messages import FatalError
from grass.exceptions import CalledModuleError
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
}

MAP_KIND = {"strds": "raster", "stvds": "vector"}


@pytest.fixture
def failing_modules(monkeypatch):
    """The names of the modules that fail when run"""
    failing = set()
    run_command = gs.run_command

    def run(name, *args, **kwargs):
        if name in failing:
            raise CalledModuleError(name, "", 1)
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


@pytest.mark.parametrize("type_", ["str3ds", "raster3d", "rast3d"])
def test_a_3d_raster_dataset_is_refused_before_anything_is_made(
    datasets, tmp_path, failing_modules, type_
):
    # GRASS has no r3.pack to export the maps with.
    with pytest.raises(FatalError, match="cannot be exported"):
        _export(tmp_path, "ex3", type_, "pack")

    assert not list(tmp_path.iterdir())


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
    ],
)
def test_a_module_that_fails_stops_the_export_with_a_message(
    datasets, tmp_path, failing_modules, type_, format_, module, message
):
    failing_modules.add(module)
    before = Path.cwd()

    with pytest.raises(FatalError, match=message):
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
        with pytest.raises(FatalError, match="is not writable"):
            tgis.export_stds(
                "exr", str(locked / "out.tar"), "no", tmp_path, None, "pack", "strds"
            )
    finally:
        locked.chmod(0o700)
    assert not list(locked.iterdir())


def test_the_vector_maps_of_one_dataset_can_be_exported_twice_in_one_process(
    datasets, tmp_path
):
    for number in (1, 2):
        archive = tmp_path / f"export{number}.tar"
        tgis.export_stds("exv", str(archive), "no", tmp_path, None, "pack", "stvds")

        with tarfile.open(archive) as tar:
            names = tar.getnames()
        assert "exv1.pack" in names, f"export {number}"
        assert "exv2.pack" in names, f"export {number}"


def test_a_vector_map_with_two_layers_is_packed_once(temporal_module_session, tmp_path):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    vector_points(tools, "exl_one", [(1, 1)])
    tools.v_category(input="exl_one", output="exl", option="add", layer=2, type="point")
    tools.t_create(type="stvds", output="exl_ds", title="t", description="t")
    tools.t_register(
        type="vector",
        input="exl_ds",
        maps="exl:1,exl:2",
        start="2001-01-01",
        increment="1 months",
    )

    archive = _export(tmp_path, "exl_ds", "stvds", "pack")

    with tarfile.open(archive) as tar:
        assert tar.getnames().count("exl.pack") == 1


@pytest.mark.parametrize(
    ("name", "type_", "member"),
    [
        ("exr", "raster", "exr1.pack"),
        ("exr", "rast", "exr1.pack"),
        ("exv", "vector", "exv1.pack"),
    ],
)
def test_a_dataset_is_exported_by_the_name_of_its_map_type_too(
    datasets, tmp_path, failing_modules, name, type_, member
):
    # open_old_stds() takes these names, so the archive must hold the maps.
    archive = _export(tmp_path, name, type_, "pack")

    with tarfile.open(archive) as tar:
        assert member in tar.getnames()
    init = dict(line.split("=") for line in _text(archive, "init.txt").splitlines())
    assert init["number_of_maps"] == "2"


def test_an_unknown_dataset_type_is_refused(datasets, tmp_path):
    with pytest.raises(FatalError, match="Unknown type: foo"):
        _export(tmp_path, "exr", "foo", "pack")

    assert not list(tmp_path.iterdir())


@pytest.fixture(scope="module")
def layered_dataset(temporal_module_session):
    """A vector dataset holding layers 1 and 2 of one map"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    vector_points(tools, "lay_one", [(1, 1)])
    tools.v_category(input="lay_one", output="lay", option="add", layer=2, type="point")
    tools.t_create(type="stvds", output="lay_ds", title="t", description="t")
    tools.t_register(
        type="vector",
        input="lay_ds",
        maps="lay:1,lay:2",
        start="2001-01-01",
        increment="1 months",
    )
    return "lay_ds"


def test_a_vector_map_with_two_layers_is_listed_per_layer_and_packed_once(
    layered_dataset, tmp_path, monkeypatch
):
    packed = []
    run_command = gs.run_command

    def run(name, *args, **kwargs):
        if name == "v.pack":
            packed.append(kwargs["input"])
        return run_command(name, *args, **kwargs)

    monkeypatch.setattr(gs, "run_command", run)

    archive = _export(tmp_path, layered_dataset, "stvds", "pack")

    assert _text(archive, "list.txt").splitlines() == [
        "lay:1|2001-01-01 00:00:00|2001-01-01 00:00:00",
        "lay:2|2001-02-01 00:00:00|2001-02-01 00:00:00",
    ]
    assert packed == ["lay"]
    assert "number_of_maps=2" in _text(archive, "init.txt")


@pytest.mark.parametrize("format_", ["GML", "GPKG"])
def test_two_layers_of_a_vector_map_cannot_be_exported_as_ogr_files(
    layered_dataset, tmp_path, format_
):
    # Every row is written to the file named after the map, so the second
    # layer finds the file of the first one and v.out.ogr refuses to
    # overwrite it. This records the behavior; it is not a decision that the
    # archive cannot hold the layers.
    with pytest.raises(FatalError, match=f"as {format_} with v.out.ogr"):
        _export(tmp_path, layered_dataset, "stvds", format_)
