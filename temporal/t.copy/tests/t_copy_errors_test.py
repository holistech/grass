"""Test the refusals of t.copy: missing options, unknown datasets and types"""

import pytest

from grass.tools import ToolError


def test_the_input_is_required(tools):
    with pytest.raises(ToolError, match=r"Required\s+parameter\s+<input>\s+not\s+set"):
        tools.t_copy(output="a")


def test_the_output_is_required(tools):
    with pytest.raises(ToolError, match=r"Required\s+parameter\s+<output>\s+not\s+set"):
        tools.t_copy(input="a")


def test_an_unknown_dataset_is_refused(tools, prefix):
    with pytest.raises(
        ToolError, match=r"Space\s+time\s+dataset\s+<nope>\s+of\s+type\s+<strds>"
    ):
        tools.t_copy(input="nope", output=f"{prefix}_copy")

    assert f"{prefix}_copy" not in tools.t_list(type="strds", columns="name").stdout


@pytest.mark.slow
def test_a_dataset_of_another_type_is_not_found(tools, make_stds, prefix):
    _, (name,) = make_stds(1)

    with pytest.raises(ToolError, match=r"of\s+type\s+<stvds>\s+not\s+found"):
        tools.t_copy(type="stvds", input=name, output=f"{prefix}_copy")


def test_an_unknown_mapset_is_refused(tools, prefix):
    with pytest.raises(ToolError, match=r"no\s+permission\s+to\s+access\s+mapset"):
        tools.t_copy(input="a@this_mapset_does_not_exist", output=f"{prefix}_copy")


def test_an_unknown_type_is_refused(tools):
    with pytest.raises(ToolError, match=r"out\s+of\s+range\s+for\s+parameter\s+<type>"):
        tools.t_copy(type="raster", input="a", output="b")


@pytest.mark.parametrize("identifier", ["a@b@c", "a:b:c@m"])
def test_an_input_with_too_many_parts_is_refused(tools, prefix, identifier):
    with pytest.raises(ToolError) as error:
        tools.t_copy(input=identifier, output=f"{prefix}_copy")

    assert "Wrong identifier" in error.value.stderr
    assert "Traceback" not in error.value.stderr


def test_an_output_with_two_mapsets_is_refused(tools, make_stds):
    _, (name,) = make_stds(1)

    with pytest.raises(ToolError) as error:
        tools.t_copy(input=name, output="a@b@c")

    assert "Wrong identifier" in error.value.stderr
    assert "Traceback" not in error.value.stderr
