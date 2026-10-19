"""Test the refusals of t.rast.export"""

import os

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_export(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, absolute, tmp_path, missing):
    options = {"input": absolute, "output": str(tmp_path / "out")}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, tmp_path):
    text = _refused(tools, input="ex_missing", output=str(tmp_path / "out"))

    assert "Space time dataset <ex_missing> of type <strds> not found" in text


def test_a_missing_directory_is_refused(tools, absolute, tmp_path):
    text = _refused(
        tools,
        input=absolute,
        output=str(tmp_path / "out"),
        directory=str(tmp_path / "nope"),
    )

    assert f"Directory {tmp_path / 'nope'} not found" in text


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to any directory")
def test_a_directory_that_is_not_writable_is_refused(tools, absolute, tmp_path):
    read_only = tmp_path / "ro"
    read_only.mkdir()
    read_only.chmod(0o500)

    try:
        text = _refused(
            tools,
            input=absolute,
            output=str(tmp_path / "out"),
            directory=str(read_only),
        )
    finally:
        read_only.chmod(0o700)

    assert f"Directory {read_only} is not writable" in text


def test_an_existing_archive_is_refused_without_overwrite(tools, absolute, tmp_path):
    archive = tmp_path / "out"
    archive.write_text("keep")

    text = _refused(tools, input=absolute, output=str(archive))

    assert "exists. To overwrite, use the --overwrite flag" in text
    assert archive.read_text() == "keep"


@pytest.mark.parametrize(
    ("option", "value"),
    [("format", "tiff"), ("compression", "zip"), ("type", "Int8")],
)
def test_a_value_outside_the_list_is_refused_by_the_parser(
    tools, absolute, tmp_path, option, value
):
    text = _refused(
        tools, input=absolute, output=str(tmp_path / "out"), **{option: value}
    )

    assert f"Value <{value}> out of range for parameter <{option}>" in text


def _failing_dataset(tools):
    """A dataset with one map without values, which the export cannot handle"""
    tools.r_mapcalc(expression="ex_empty = null()", overwrite=True)
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="ex_empty_ds",
        title="t",
        description="d",
        overwrite=True,
    )
    tools.t_register(
        type="raster",
        input="ex_empty_ds",
        maps="ex_empty",
        start="2001-01-01",
        increment="1 months",
        overwrite=True,
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_a_map_without_values_ends_with_a_traceback(tools, tmp_path):
    _failing_dataset(tools)

    text = _refused(tools, input="ex_empty_ds", output=str(tmp_path / "out"))

    assert "unsupported operand type(s) for +: 'NoneType' and 'int'" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="t.rast.export fails on a map without values with a TypeError (None + int)",
)
def test_a_map_without_values_can_be_exported(tools, tmp_path):
    _failing_dataset(tools)

    tools.t_rast_export(input="ex_empty_ds", output=str(tmp_path / "out"))

    assert (tmp_path / "out").is_file()


def _leftovers(tmp_path):
    return sorted(
        path.name for path in tmp_path.iterdir() if path.name.startswith("tmp")
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_a_failed_export_leaves_its_working_directory(tools, tmp_path):
    _failing_dataset(tools)

    _refused(tools, input="ex_empty_ds", output=str(tmp_path / "out"))

    assert len(_leftovers(tmp_path)) == 1


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="t.rast.export leaves its working directory behind when the export fails",
)
def test_a_failed_export_removes_its_working_directory(tools, tmp_path):
    _failing_dataset(tools)

    _refused(tools, input="ex_empty_ds", output=str(tmp_path / "out"))

    assert _leftovers(tmp_path) == []
