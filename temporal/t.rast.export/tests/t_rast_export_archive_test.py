"""Test the archive that t.rast.export writes

The layout of the archive was measured on 18.10.2026 by exporting a dataset of
three maps with each format and listing it with tarfile: the maps (a raster
file and a .color file each for GTiff and AAIGrid, a .pack file for pack),
then list.txt, proj.txt, init.txt, readme.txt and metadata.txt. What the files
must hold is derived from the registered maps (conftest.py).
"""

import tarfile

import pytest

MAPS = ["ex_a", "ex_b", "ex_c"]
FILES = {
    "GTiff": [f"{name}{ext}" for name in MAPS for ext in (".tif", ".color")],
    "AAIGrid": [f"{name}{ext}" for name in MAPS for ext in (".asc", ".color")],
    "pack": [f"{name}.pack" for name in MAPS],
}
TEXT_FILES = ["list.txt", "proj.txt", "init.txt", "readme.txt", "metadata.txt"]
# The first bytes of a file: bzip2 and gzip signatures, and the "ustar" marker
# of a plain tar archive at offset 257.
SIGNATURES = {"bzip2": (0, b"BZh"), "gzip": (0, b"\x1f\x8b"), "no": (257, b"ustar")}


def _export(tools, name, output, **options):
    return tools.t_rast_export(input=name, output=str(output), **options)


def _read(archive, member):
    with tarfile.open(archive) as tar:
        return tar.extractfile(member).read().decode()


def _init(archive):
    return dict(line.split("=") for line in _read(archive, "init.txt").splitlines())


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GTiff", "AAIGrid", "pack"])
def test_the_archive_holds_a_file_per_map_and_the_description(
    tools, absolute, tmp_path, fmt
):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format=fmt, compression="no")

    with tarfile.open(archive) as tar:
        assert tar.getnames() == FILES[fmt] + TEXT_FILES


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GTiff", "AAIGrid", "pack"])
def test_init_and_list_describe_the_dataset(tools, absolute, tmp_path, fmt):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format=fmt, compression="no")

    assert _init(archive) == {
        "stds_type": "strds",
        "format": fmt,
        "temporal_type": "absolute",
        "semantic_type": "mean",
        "number_of_maps": "3",
        "north": "2.0",
        "south": "0.0",
        "east": "3.0",
        "west": "0.0",
    }
    assert _read(archive, "list.txt").splitlines() == [
        "ex_a|2001-01-01 00:00:00|2001-02-01 00:00:00|None",
        "ex_b|2001-02-01 00:00:00|2001-03-01 00:00:00|None",
        "ex_c|2001-03-01 00:00:00|2001-04-01 00:00:00|None",
    ]


def test_proj_and_metadata_come_from_the_project_and_the_dataset(
    tools, absolute, tmp_path
):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, compression="no")

    assert "XY location (unprojected)" in _read(archive, "proj.txt")
    assert "Name: ...................... ex_abs" in _read(archive, "metadata.txt")


def test_the_relative_time_is_written_as_numbers(tools, relative, tmp_path):
    archive = tmp_path / "out"

    _export(tools, relative, archive, compression="no")

    init = _init(archive)
    assert init["temporal_type"] == "relative"
    assert init["relative_time_unit"] == "years"
    assert _read(archive, "list.txt").splitlines() == [
        "ex_r1|1|2|None",
        "ex_r2|2|3|None",
    ]


@pytest.mark.parametrize("compression", ["no", "gzip", "bzip2"])
def test_the_compression_of_the_archive(tools, absolute, tmp_path, compression):
    archive = tmp_path / "out"

    _export(tools, absolute, archive, compression=compression)

    offset, signature = SIGNATURES[compression]
    with archive.open("rb") as handle:
        handle.seek(offset)
        assert handle.read(len(signature)) == signature
    with tarfile.open(archive) as tar:
        assert len(tar.getnames()) == len(FILES["GTiff"]) + len(TEXT_FILES)


def test_the_default_compression_is_bzip2(tools, absolute, tmp_path):
    archive = tmp_path / "out"

    _export(tools, absolute, archive)

    assert archive.read_bytes()[:3] == b"BZh"


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
        "ex_b",
        "ex_c",
    ]
    with tarfile.open(archive) as tar:
        assert "ex_a.tif" not in tar.getnames()


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_packed_maps_are_not_compressed_again(tools, absolute, tmp_path):
    # r.pack runs with -c, so a .pack member is a plain tar archive and the
    # outer compression of the archive does the work once.
    archive = tmp_path / "out"

    _export(tools, absolute, archive, format="pack", compression="no")

    with tarfile.open(archive) as outer:
        member = outer.extractfile("ex_a.pack")
        assert member.read(2) != b"\x1f\x8b"
        member.seek(0)
        with tarfile.open(fileobj=member, mode="r:") as inner:
            assert inner.getnames()
