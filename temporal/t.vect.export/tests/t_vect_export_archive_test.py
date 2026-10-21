"""Test the archive that t.vect.export writes

The layout of the archive was measured on 18.10.2026 by exporting a dataset of
three maps with each format and listing it with tarfile: a .xml and a .xsd
file per map for GML, a .gpkg file per map for GPKG, a .pack file per map for
pack, then list.txt, proj.txt, init.txt, readme.txt and metadata.txt. What the
files must hold is derived from the registered maps (conftest.py).
"""

import sqlite3
import tarfile

import pytest

from grass.temporal.testing.readback import message

MAPS = ["vx_1", "vx_2", "vx_3"]
FILES = {
    "GML": [f"{name}{ext}" for name in MAPS for ext in (".xml", ".xsd")],
    "GPKG": [f"{name}.gpkg" for name in MAPS],
    "pack": [f"{name}.pack" for name in MAPS],
}
TEXT_FILES = ["list.txt", "proj.txt", "init.txt", "readme.txt", "metadata.txt"]
# The first bytes of a file: bzip2 and gzip signatures, and the "ustar" marker
# of a plain tar archive at offset 257.
SIGNATURES = {"bzip2": (0, b"BZh"), "gzip": (0, b"\x1f\x8b"), "no": (257, b"ustar")}


def _export(tools, name, output, **options):
    return tools.t_vect_export(input=name, output=str(output), **options)


def _read(archive, member):
    with tarfile.open(archive) as tar:
        return tar.extractfile(member).read().decode()


def _init(archive):
    return dict(line.split("=") for line in _read(archive, "init.txt").splitlines())


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GML", "GPKG", "pack"])
def test_the_archive_holds_a_file_per_map_and_the_description(
    tools, absolute, tmp_path, fmt
):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format=fmt, compression="no")

    with tarfile.open(archive) as tar:
        assert tar.getnames() == FILES[fmt] + TEXT_FILES


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GML", "GPKG", "pack"])
def test_init_and_list_describe_the_dataset(tools, absolute, tmp_path, fmt):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format=fmt, compression="no")

    # The extent is that of the points: x from 1 to 3 (map k at x = k), y from
    # 1 to 2.
    assert _init(archive) == {
        "stds_type": "stvds",
        "format": fmt,
        "temporal_type": "absolute",
        "semantic_type": "mean",
        "number_of_maps": "3",
        "north": "2.0",
        "south": "1.0",
        "east": "3.0",
        "west": "1.0",
    }
    # The pack format lists the layer of every map (measured 18.10.2026).
    suffix = ":1" if fmt == "pack" else ""
    assert _read(archive, "list.txt").splitlines() == [
        f"vx_1{suffix}|2001-01-01 00:00:00|2001-02-01 00:00:00",
        f"vx_2{suffix}|2001-02-01 00:00:00|2001-03-01 00:00:00",
        f"vx_3{suffix}|2001-03-01 00:00:00|2001-04-01 00:00:00",
    ]


def test_proj_and_metadata_come_from_the_project_and_the_dataset(
    tools, absolute, tmp_path
):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, compression="no")

    assert "XY location (unprojected)" in _read(archive, "proj.txt")
    assert "Name: ...................... vx_abs" in _read(archive, "metadata.txt")


def test_gml_holds_the_points_and_their_attributes(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format="GML", compression="no")

    # Map 2 has the points (2, 1) and (2, 2) with value 21 and 22 (conftest.py)
    text = _read(archive, "vx_2.xml")
    assert text.count("<ogr:featureMember>") == 2
    for fragment in (
        "<gml:pos>2 1</gml:pos>",
        "<gml:pos>2 2</gml:pos>",
        "<ogr:value>21</ogr:value>",
        "<ogr:value>22</ogr:value>",
        "<ogr:name>2_1</ogr:name>",
        "<ogr:name>2_2</ogr:name>",
    ):
        assert fragment in text


def test_gpkg_holds_the_attributes_of_the_map(tools, absolute, tmp_path):
    archive = tmp_path / "out"
    _export(tools, absolute, archive, format="GPKG", compression="no")
    with tarfile.open(archive) as tar:
        tar.extract("vx_3.gpkg", tmp_path / "x", filter="data")

    with sqlite3.connect(tmp_path / "x" / "vx_3.gpkg") as db:
        rows = db.execute("SELECT x, y, cat, value, name FROM vx_3").fetchall()

    # Map 3 has the points (3, 1) and (3, 2) with value 31 and 32
    assert rows == [(3.0, 1.0, 1, 31, "3_1"), (3.0, 2.0, 2, 32, "3_2")]


def test_the_relative_time_is_written_as_numbers(tools, relative, tmp_path):
    archive = tmp_path / "out"

    _export(tools, relative, archive, compression="no")

    init = _init(archive)
    assert init["temporal_type"] == "relative"
    assert init["relative_time_unit"] == "years"
    assert _read(archive, "list.txt").splitlines() == ["vx_r1|1|2", "vx_r2|2|3"]


@pytest.mark.parametrize("compression", ["no", "gzip", "bzip2"])
def test_the_compression_of_the_archive(tools, absolute, tmp_path, compression):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, compression=compression)

    offset, signature = SIGNATURES[compression]
    with archive.open("rb") as handle:
        handle.seek(offset)
        assert handle.read(len(signature)) == signature
    with tarfile.open(archive) as tar:
        assert len(tar.getnames()) == len(FILES["GML"]) + len(TEXT_FILES)


def test_the_default_compression_is_bzip2(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(tools, absolute, archive)

    assert archive.read_bytes()[:3] == b"BZh"


def test_the_default_format_is_gml(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, compression="no")

    assert _init(archive)["format"] == "GML"


def test_where_selects_the_maps_of_the_archive(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(
        tools,
        absolute,
        archive,
        where="start_time >= '2001-02-01'",
        compression="no",
    )

    assert _init(archive)["number_of_maps"] == "2"
    assert [line.split("|")[0] for line in _read(archive, "list.txt").splitlines()] == [
        "vx_2",
        "vx_3",
    ]
    with tarfile.open(archive) as tar:
        assert "vx_1.xml" not in tar.getnames()


def test_a_selection_without_maps_gives_an_archive_without_maps(
    tools, absolute, tmp_path
):
    archive = tmp_path / "out"

    result = _export(
        tools, absolute, archive, where="start_time > '2020-01-01'", compression="no"
    )

    with tarfile.open(archive) as tar:
        assert tar.getnames() == TEXT_FILES
    assert _init(archive)["number_of_maps"] == "0"
    assert message(result) == ""


def test_the_extent_of_a_selection_is_that_of_the_selected_maps(
    tools, absolute, tmp_path
):
    archive = tmp_path / "out"

    _export(
        tools,
        absolute,
        archive,
        where="start_time >= '2001-02-01'",
        compression="no",
    )

    # Maps 2 and 3 hold the points (2, 1), (2, 2), (3, 1) and (3, 2).
    init = _init(archive)
    assert [init[key] for key in ("north", "south", "east", "west")] == [
        "2.0",
        "1.0",
        "3.0",
        "2.0",
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_packed_maps_are_not_compressed_again(tools, absolute, tmp_path):
    # v.pack runs with -c, so a .pack member is a plain tar archive and the
    # outer compression of the archive does the work once.
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format="pack", compression="no")

    with tarfile.open(archive) as outer:
        member = outer.extractfile("vx_1.pack")
        assert member.read(2) != b"\x1f\x8b"
        member.seek(0)
        with tarfile.open(fileobj=member, mode="r:") as inner:
            assert inner.getnames()


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_readme_names_the_files_of_the_format(tools, absolute, tmp_path):
    archive = tmp_path / "gml"
    _export(tools, absolute, archive, format="GML", compression="no")
    pack = tmp_path / "pack"
    _export(tools, absolute, pack, format="pack", compression="no")

    assert "*.xml  -- Vector GML files" in _read(archive, "readme.txt")
    assert "*.pack  -- GRASS vector files packed with v.pack" in _read(
        pack, "readme.txt"
    )


def test_readme_names_the_gpkg_files_of_a_gpkg_archive(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format="GPKG", compression="no")

    text = _read(archive, "readme.txt")
    assert "*.gpkg  -- Vector GeoPackage files" in text
    assert "*.pack" not in text
