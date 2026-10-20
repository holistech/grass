"""Test the refusals of t.rast.out.vtk

The old shell script called the tool with expdir=, an option that does not
exist, and ended with the return code of its last command, so it passed while
every call failed. Here every refusal is checked by its message.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_out_vtk(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "directory"])
def test_a_required_option_is_checked_by_the_parser(
    tools, vtk_input, tmp_path, missing
):
    options = {"input": vtk_input, "directory": str(tmp_path)}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_the_option_of_the_old_script_does_not_exist(tools, vtk_input, tmp_path):
    text = _refused(tools, input=vtk_input, expdir=str(tmp_path))

    assert "expdir" in text


def test_an_unknown_input_is_refused(tools, tmp_path):
    text = _refused(tools, input="vt_missing", directory=str(tmp_path))

    assert "Space time dataset <vt_missing> of type <strds> not found" in text


def test_a_missing_directory_is_refused(tools, vtk_input, tmp_path):
    text = _refused(tools, input=vtk_input, directory=str(tmp_path / "nope"))

    assert f"Export directory <{tmp_path / 'nope'}> not found." in text


def test_an_existing_file_is_refused_without_overwrite(tools, vtk_input, tmp_path):
    existing = tmp_path / "000000_vt_in.vtk"
    existing.write_text("keep")

    text = _refused(tools, input=vtk_input, directory=str(tmp_path))

    assert "000000_vt_in.vtk> exists. To overwrite, use the --overwrite flag" in text
    assert "Unable to export raster map" in text
    assert existing.read_text() == "keep"


def test_overwrite_replaces_the_files(tools, vtk_input, tmp_path):
    existing = tmp_path / "000000_vt_in.vtk"
    existing.write_text("old")

    tools.t_rast_out_vtk(input=vtk_input, directory=str(tmp_path), overwrite=True)

    assert existing.read_text().startswith("# vtk DataFile Version 3.0")


def _copies(tools, prefix="vt_in_"):
    return [
        name
        for name in tools.g_list(type="raster").stdout.split()
        if name.startswith(prefix)
    ]


def _remove(tools):
    if copies := _copies(tools) + _copies(tools, "temporary_null_map_"):
        tools.g_remove(type="raster", name=copies, flags="f")


@pytest.fixture(autouse=True)
def _remove_copies(tools):
    """Remove the copies that a refused export leaves, before and after a test"""
    _remove(tools)
    yield
    _remove(tools)


def test_a_refused_export_removes_the_copy_of_the_map(tools, vtk_input, tmp_path):
    (tmp_path / "000000_vt_in.vtk").write_text("keep")

    _refused(tools, input=vtk_input, directory=str(tmp_path))

    assert _copies(tools) == []


def test_a_directory_that_is_a_file_is_refused(tools, vtk_input, tmp_path):
    not_a_directory = tmp_path / "file"
    not_a_directory.write_text("x")

    text = _refused(tools, input=vtk_input, directory=str(not_a_directory))

    assert f"Export directory <{not_a_directory}> not found" in text
    assert "Traceback" not in text
    assert _copies(tools) == []


def test_a_refused_export_by_granularity_removes_the_null_map(
    tools, vtk_input, tmp_path
):
    (tmp_path / "000000_vt_in.vtk").write_text("keep")

    _refused(tools, input=vtk_input, directory=str(tmp_path), flags="g")

    assert _copies(tools) == []
    assert _copies(tools, "temporary_null_map_") == []


def test_overwrite_replaces_the_files_of_a_surface(tools, vtk_input, tmp_path):
    existing = tmp_path / "000000_vt_in.vtk"
    existing.write_text("old")

    tools.t_rast_out_vtk(
        input=vtk_input,
        directory=str(tmp_path),
        elevation="vt_e",
        overwrite=True,
        where="start_time < '2001-02-01'",
    )

    assert "DATASET POLYDATA" in existing.read_text()


def test_an_existing_file_of_a_surface_is_refused_without_overwrite(
    tools, vtk_input, tmp_path
):
    existing = tmp_path / "000000_vt_in.vtk"
    existing.write_text("keep")

    text = _refused(
        tools,
        input=vtk_input,
        directory=str(tmp_path),
        elevation="vt_e",
        where="start_time < '2001-02-01'",
    )

    assert "Unable to export raster map" in text
    assert existing.read_text() == "keep"


def test_a_where_with_a_syntax_error_is_reported_as_a_message(
    tools, vtk_input, tmp_path
):
    text = _refused(tools, input=vtk_input, directory=str(tmp_path), where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert not list(tmp_path.glob("*.vtk"))
