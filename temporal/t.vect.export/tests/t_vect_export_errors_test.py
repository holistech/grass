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


def test_a_where_with_a_syntax_error_is_reported_as_a_message(
    tools, absolute, tmp_path
):
    text = _refused(
        tools,
        input=absolute,
        output=str(tmp_path / "out"),
        directory=str(tmp_path),
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert list(tmp_path.iterdir()) == []


def _leftovers(path):
    return sorted(p.name for p in path.iterdir() if p.name.startswith("tmp"))


def test_an_unknown_input_leaves_no_working_directory(tools, tmp_path):
    _refused(
        tools, input="vx_missing", output=str(tmp_path / "out"), directory=str(tmp_path)
    )

    assert _leftovers(tmp_path) == []


def test_a_directory_that_is_a_file_is_refused(tools, absolute, tmp_path):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("x")

    text = _refused(
        tools,
        input=absolute,
        output=str(tmp_path / "out"),
        directory=str(not_a_directory),
    )

    assert f"Directory {not_a_directory} is not a directory" in text
    assert "Traceback" not in text


def test_an_output_in_a_missing_directory_is_refused(tools, absolute, tmp_path):
    output = tmp_path / "nope" / "out"

    text = _refused(tools, input=absolute, output=str(output), directory=str(tmp_path))

    assert f"Output directory {output.parent} not found" in text
    assert "Traceback" not in text
    assert _leftovers(tmp_path) == []


def test_a_map_that_is_gone_stops_the_export_and_leaves_nothing(
    tools, absolute, tmp_path
):
    tools.v_random(output="vx_gone", npoints=2, seed=1, overwrite=True)
    tools.t_create(
        type="stvds",
        temporaltype="absolute",
        output="vx_gone_ds",
        title="t",
        description="d",
        overwrite=True,
    )
    tools.t_register(
        type="vector",
        input="vx_gone_ds",
        maps="vx_gone",
        start="2001-01-01",
        increment="1 months",
        overwrite=True,
    )
    tools.g_remove(flags="f", type="vector", name="vx_gone")

    text = _refused(
        tools, input="vx_gone_ds", output=str(tmp_path / "out"), directory=str(tmp_path)
    )

    assert "Unable to export vector map <vx_gone>" in text
    assert _leftovers(tmp_path) == []
    assert not (tmp_path / "out").exists()
