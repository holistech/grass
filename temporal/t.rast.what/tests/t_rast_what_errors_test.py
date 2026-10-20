"""Test the refusals of t.rast.what"""

from io import StringIO

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_what(**options)
    return message(error.value)


def test_the_dataset_is_required(tools):
    assert "Required parameter <strds> not set" in _refused(tools, coordinates="1,1")


def test_an_unknown_dataset_is_refused(tools):
    text = _refused(tools, strds="wh_missing", coordinates="1,1")

    assert "Space time dataset <wh_missing> of type <strds> not found" in text


def test_a_position_is_needed(tools, sampled):
    text = _refused(tools, strds=sampled)

    assert (
        "Please specify the coordinates, the points option or use the 'i' flag" in text
    )


def test_points_and_coordinates_exclude_each_other(tools, sampled):
    text = _refused(tools, strds=sampled, points="wh_pts", coordinates="1,1")

    assert "Options coordinates and points are mutually exclusive" in text


def test_the_v_flag_needs_points(tools, sampled):
    text = _refused(tools, strds=sampled, coordinates="1,1", flags="v")

    # A refusal by the tool itself, before r.what is called
    assert "Flag 'v' required option 'points'" in text
    assert "Traceback" not in text


def test_the_v_flag_needs_points_with_stdin_too(tools, sampled):
    text = _refused(tools, strds=sampled, flags="iv", stdin=StringIO("1 1\n"))

    assert "Flag 'v' required option 'points'" in text
    assert "Traceback" not in text


def test_coordinates_come_in_pairs(tools, sampled):
    text = _refused(tools, strds=sampled, coordinates="1,2,3")

    assert "Option <coordinates> must be provided in multiples of 2" in text


def test_a_selection_without_maps_is_refused(tools, sampled):
    text = _refused(
        tools,
        strds=sampled,
        coordinates="1,1",
        where="start_time > '2010-01-01'",
    )

    assert "Space time raster dataset <wh_a@PERMANENT> is empty" in text


def test_unknown_points_are_refused(tools, sampled):
    text = _refused(tools, strds=sampled, points="wh_no_points")

    assert "wh_no_points" in text


@pytest.mark.parametrize(
    ("option", "value"),
    [("layout", "diagonal"), ("order", "color")],
)
def test_a_value_outside_the_list_is_refused_by_the_parser(
    tools, sampled, option, value
):
    text = _refused(tools, strds=sampled, coordinates="1,1", **{option: value})

    assert f"Value <{value}> out of range for parameter <{option}>" in text


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, sampled):
    text = _refused(tools, strds=sampled, coordinates="1,1", where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
