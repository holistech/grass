"""Test the refusals of t.copy: missing options, unknown datasets and types"""

import pytest

from grass.tools import ToolError


def test_the_input_is_required(tools):
    with pytest.raises(ToolError, match=r"Required parameter <input> not set"):
        tools.t_copy(output="a")


def test_the_output_is_required(tools):
    with pytest.raises(ToolError, match=r"Required parameter <output> not set"):
        tools.t_copy(input="a")


def test_an_unknown_dataset_is_refused(tools, prefix):
    with pytest.raises(ToolError, match=r"Space time dataset <nope> of type\s+<strds>"):
        tools.t_copy(input="nope", output=f"{prefix}_copy")

    assert f"{prefix}_copy" not in tools.t_list(type="strds", columns="name").stdout


@pytest.mark.slow
def test_a_dataset_of_another_type_is_not_found(tools, make_stds, prefix):
    _, (name,) = make_stds(1)

    with pytest.raises(ToolError, match=r"of type\s+<stvds> not found"):
        tools.t_copy(type="stvds", input=name, output=f"{prefix}_copy")


def test_an_unknown_mapset_is_refused(tools, prefix):
    with pytest.raises(ToolError, match=r"no\s+permission\s+to\s+access\s+mapset"):
        tools.t_copy(input="a@this_mapset_does_not_exist", output=f"{prefix}_copy")


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match="out of range for parameter <type>"):
        tools.t_copy(type="raster", input="a", output="b")
