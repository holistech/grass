"""Test the refusals of t.rast.colors"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_colors(**options)
    return message(error.value)


def test_the_input_is_required(tools):
    assert "Required parameter <input> not set" in _refused(tools, color="grey")


def test_an_unknown_input_is_refused(tools):
    text = _refused(tools, input="col_missing", color="grey")

    assert "Space time dataset <col_missing> of type <strds> not found" in text


def test_a_source_of_colours_is_required(tools, colored):
    name, _, _ = colored

    text = _refused(tools, input=name)

    assert (
        "At least one of the following options is required: <raster>, <raster_3d>, "
        "<color>, <rules>, <-r>, <-l> and <-d>" in text
    )
    assert "Error in r.colors call" in text


def test_only_one_source_of_colours_is_allowed(tools, colored):
    name, first, _ = colored

    text = _refused(tools, input=name, color="grey", raster=first)

    assert (
        "Options <color>, <rules>, <raster> and <raster_3d> are mutually exclusive"
        in text
    )


def test_an_unknown_colour_table_is_refused_by_the_parser(tools, colored, table):
    name, first, _ = colored
    before = table(first)

    text = _refused(tools, input=name, color="nosuchtable")

    assert "Value <nosuchtable> out of range for parameter <color>" in text
    assert table(first) == before


def test_a_missing_rules_file_is_refused(tools, colored, tmp_path):
    name, _, _ = colored
    missing = tmp_path / "nofile"

    text = _refused(tools, input=name, rules=str(missing))

    assert f"Unable to load rules file <{missing}>" in text


def test_an_unknown_raster_is_refused(tools, colored):
    name, _, _ = colored

    text = _refused(tools, input=name, raster="col_no_such_map")

    assert "Error in r.colors call" in text


def test_a_dataset_without_maps_is_left_alone(tools, prefix):
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_empty",
        title="empty",
        description="empty",
    )

    result = tools.t_rast_colors(input=f"{prefix}_empty", color="grey")

    assert result.returncode == 0
    assert message(result) == ""


def test_a_failing_listing_of_the_rules_is_reported(broken_tools, colored):
    name, _, _ = colored

    with pytest.raises(ToolError) as error:
        broken_tools("r.colors").t_rast_colors(input=name, flags="l")

    assert "Error in r.colors call" in message(error.value)
