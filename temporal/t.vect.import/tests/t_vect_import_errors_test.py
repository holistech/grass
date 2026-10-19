"""Test the refusals of t.vect.import

The library reports its refusals with gs.fatal(), which in a tool called from a
session ends with a traceback after the message. The archives come from
t.vect.export (conftest.py); the damaged ones are copies of them.
"""

import io
import tarfile

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    options.setdefault("flags", "o")
    with pytest.raises(ToolError) as error:
        tools.t_vect_import(**options)
    return message(error.value)


def _damaged(archive, target, *, drop=(), replace=None):
    """A copy of an archive without the members drop and with new texts

    replace maps a member to its new text.
    """
    replace = replace or {}
    with tarfile.open(archive) as source, tarfile.open(target, "w") as out:
        for member in source.getmembers():
            if member.name in drop:
                continue
            if member.name in replace:
                data = replace[member.name].encode()
                member.size = len(data)
                out.addfile(member, io.BytesIO(data))
            else:
                out.addfile(member, source.extractfile(member))
    return target


@pytest.mark.parametrize("missing", ["input", "output", "directory"])
def test_a_required_option_is_checked_by_the_parser(
    tools, archives, prefix, tmp_path, missing
):
    options = {
        "input": str(archives["GML"]),
        "output": prefix,
        "directory": str(tmp_path),
    }
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_today_a_missing_archive_ends_with_a_traceback(tools, prefix, tmp_path):
    text = _refused(
        tools, input=str(tmp_path / "none.tar"), output=prefix, directory=str(tmp_path)
    )

    assert "Space time raster dataset archive" in text
    assert "not found" in text
    assert "Traceback" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.import ends in a traceback for a missing archive instead of a message",
)
def test_a_missing_archive_is_reported_as_a_message(tools, prefix, tmp_path):
    text = _refused(
        tools, input=str(tmp_path / "none.tar"), output=prefix, directory=str(tmp_path)
    )

    assert "Traceback" not in text


def test_a_missing_extraction_directory_is_refused(tools, archives, prefix, tmp_path):
    text = _refused(
        tools,
        input=str(archives["GML"]),
        output=prefix,
        directory=str(tmp_path / "nope"),
    )

    assert f"Extraction directory <{tmp_path / 'nope'}> not found" in text


def test_today_a_file_that_is_no_archive_ends_with_a_traceback(tools, prefix, tmp_path):
    junk = tmp_path / "junk"
    junk.write_text("no archive")

    text = _refused(tools, input=str(junk), output=prefix, directory=str(tmp_path))

    assert "tarfile.ReadError" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.import ends in a tarfile.ReadError traceback for a file that is no archive instead of a message",
)
def test_a_file_that_is_no_archive_is_reported_as_a_message(tools, prefix, tmp_path):
    junk = tmp_path / "junk"
    junk.write_text("no archive")

    text = _refused(tools, input=str(junk), output=prefix, directory=str(tmp_path))

    assert "Traceback" not in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(
    tools, archives, prefix, tmp_path
):
    options = {
        "input": str(archives["pack"]),
        "output": prefix,
        "basename": prefix,
        "directory": str(tmp_path),
    }
    tools.t_vect_import(flags="o", **options)

    text = _refused(tools, **options)

    assert (
        f"Space time stvds dataset <{prefix}@PERMANENT> is already in the database"
        in text
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_existing_maps_are_refused_without_overwrite(tools, archives, prefix, tmp_path):
    # The names in the archive are those of the exported maps, which still
    # exist in this project.
    text = _refused(
        tools, input=str(archives["pack"]), output=prefix, directory=str(tmp_path)
    )

    assert "<vi_1> exists. To overwrite, use the --overwrite flag" in text


def test_a_raster_archive_is_refused(tools, archives, prefix, tmp_path):
    raster = _damaged(
        archives["GML"],
        tmp_path / "raster.tar",
        replace={
            "init.txt": "stds_type=strds\ntemporal_type=absolute\n"
            "semantic_type=mean\nnumber_of_maps=2\n"
        },
    )

    text = _refused(tools, input=str(raster), output=prefix, directory=str(tmp_path))

    assert "The archive file is of wrong space time dataset type" in text


@pytest.mark.parametrize(
    ("member", "kind"),
    [("init.txt", "init"), ("list.txt", "list"), ("proj.txt", "projection")],
)
def test_an_archive_without_a_description_file_is_refused(
    tools, archives, prefix, tmp_path, member, kind
):
    broken = _damaged(archives["GML"], tmp_path / "broken.tar", drop=[member])

    text = _refused(tools, input=str(broken), output=prefix, directory=str(tmp_path))

    assert f"Unable to find {kind} file <{member}>" in text


@pytest.mark.parametrize(
    ("fmt", "member", "kind"),
    [
        ("GML", "vi_1.xml", "GML vector file"),
        ("pack", "vi_1.pack", "GRASS package file"),
    ],
)
def test_an_archive_without_a_map_file_is_refused(
    tools, archives, prefix, tmp_path, fmt, member, kind
):
    broken = _damaged(archives[fmt], tmp_path / "broken.tar", drop=[member])

    text = _refused(tools, input=str(broken), output=prefix, directory=str(tmp_path))

    assert f"Unable to find {kind} <{member}> in archive." in text


def test_a_number_of_maps_that_differs_from_the_list_is_refused(
    tools, archives, prefix, tmp_path
):
    init = (
        "stds_type=stvds\nformat=GML\ntemporal_type=absolute\n"
        "semantic_type=mean\nnumber_of_maps=3\n"
    )
    broken = _damaged(
        archives["GML"], tmp_path / "broken.tar", replace={"init.txt": init}
    )

    text = _refused(tools, input=str(broken), output=prefix, directory=str(tmp_path))

    assert "Number of maps mismatch in init and list file." in text


def test_an_init_file_without_the_keywords_is_refused(
    tools, archives, prefix, tmp_path
):
    broken = _damaged(
        archives["GML"],
        tmp_path / "broken.tar",
        replace={"init.txt": "stds_type=stvds\n"},
    )

    text = _refused(tools, input=str(broken), output=prefix, directory=str(tmp_path))

    assert "Key words temporal_type, semantic_type or number_of_maps not found" in text


def test_a_format_that_the_tool_cannot_read_is_refused(
    tools, archives, prefix, tmp_path
):
    init = (
        "stds_type=stvds\nformat=shp\ntemporal_type=absolute\n"
        "semantic_type=mean\nnumber_of_maps=2\n"
    )
    broken = _damaged(
        archives["GML"], tmp_path / "broken.tar", replace={"init.txt": init}
    )

    text = _refused(tools, input=str(broken), output=prefix, directory=str(tmp_path))

    assert "Unsupported input format" in text


def test_a_relative_archive_without_a_unit_is_refused(
    tools, archives, prefix, tmp_path
):
    init = (
        "stds_type=stvds\nformat=GML\ntemporal_type=relative\n"
        "semantic_type=mean\nnumber_of_maps=2\n"
    )
    broken = _damaged(
        archives["GML"], tmp_path / "broken.tar", replace={"init.txt": init}
    )

    text = _refused(
        tools,
        input=str(broken),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
    )

    assert "Key word relative_time_unit not found in init file." in text


# The export offers GPKG, the import reads GML and pack only (stds_import.py).
def _gpkg_archive(tools, tmp_path):
    archive = tmp_path / "gpkg.tar"
    tools.t_vect_export(
        input="vi_pair", output=str(archive), format="GPKG", compression="no"
    )
    return archive


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_a_gpkg_archive_cannot_be_imported(tools, archives, prefix, tmp_path):
    archive = _gpkg_archive(tools, tmp_path)

    text = _refused(
        tools,
        input=str(archive),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
    )

    assert "Unsupported input format" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason='t.vect.import cannot import a GPKG archive, it ends with "Unsupported input format"',
)
def test_a_gpkg_archive_can_be_imported(tools, prefix, tmp_path):
    archive = _gpkg_archive(tools, tmp_path)

    tools.t_vect_import(
        input=str(archive),
        output=prefix,
        basename=prefix,
        directory=str(tmp_path),
        flags="o",
    )
