"""Test the refusals of t.vect.export"""

import os

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_export(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, absolute, tmp_path, missing):
    options = {"input": absolute, "output": str(tmp_path / "out")}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, tmp_path):
    text = _refused(tools, input="vx_missing", output=str(tmp_path / "out"))

    assert "Space time dataset <vx_missing> of type <stvds> not found" in text


def _missing_directory(tools, absolute, tmp_path):
    return _refused(
        tools,
        input=absolute,
        output=str(tmp_path / "out"),
        directory=str(tmp_path / "nope"),
    )


def test_today_a_missing_directory_ends_with_a_traceback(tools, absolute, tmp_path):
    text = _missing_directory(tools, absolute, tmp_path)

    assert "No such file or directory" in text
    assert "Traceback" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.export ends in a traceback for a missing directory instead of a message",
)
def test_a_missing_directory_is_refused_with_a_message(tools, absolute, tmp_path):
    text = _missing_directory(tools, absolute, tmp_path)

    assert f"Directory {tmp_path / 'nope'} not found" in text


def _read_only_directory(tools, absolute, tmp_path):
    read_only = tmp_path / "ro"
    read_only.mkdir()
    read_only.chmod(0o500)
    try:
        return _refused(
            tools,
            input=absolute,
            output=str(tmp_path / "out"),
            directory=str(read_only),
        )
    finally:
        read_only.chmod(0o700)


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to any directory")
def test_today_a_directory_that_is_not_writable_ends_with_a_traceback(
    tools, absolute, tmp_path
):
    text = _read_only_directory(tools, absolute, tmp_path)

    assert "Permission denied" in text
    assert "Traceback" in text


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to any directory")
@pytest.mark.xfail(
    strict=True,
    reason="t.vect.export ends in a PermissionError traceback for a directory that is not writable instead of a message",
)
def test_a_directory_that_is_not_writable_is_refused_with_a_message(
    tools, absolute, tmp_path
):
    text = _read_only_directory(tools, absolute, tmp_path)

    assert "is not writable" in text


def test_an_existing_archive_is_refused_without_overwrite(tools, absolute, tmp_path):
    archive = tmp_path / "out"
    archive.write_text("keep")

    text = _refused(tools, input=absolute, output=str(archive))

    assert "exists. To overwrite, use the --overwrite flag" in text
    assert archive.read_text() == "keep"


@pytest.mark.parametrize(
    ("option", "value"),
    [("format", "shp"), ("compression", "zip")],
)
def test_a_value_outside_the_list_is_refused_by_the_parser(
    tools, absolute, tmp_path, option, value
):
    text = _refused(
        tools, input=absolute, output=str(tmp_path / "out"), **{option: value}
    )

    assert f"Value <{value}> out of range for parameter <{option}>" in text
