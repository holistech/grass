"""Test the refusals of t.rast.univar"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_univar(**options)
    return message(error.value)


def test_the_input_is_required(tools):
    assert "Required parameter <input> not set" in _refused(tools)


def test_an_unknown_input_is_refused(tools):
    text = _refused(tools, input="uv_missing")

    assert "Space time dataset <uv_missing> of type <strds> not found" in text


def test_percentile_needs_the_e_flag(tools, values):
    assert "Option <percentile> requires <-e>" in _refused(
        tools, input=values, percentile=10
    )


def test_a_percentile_outside_the_range_is_refused(tools, values):
    text = _refused(tools, input=values, flags="e", percentile=101)

    assert "Value <101> out of range for parameter <percentile>" in text


def test_a_percentile_that_is_no_number_is_refused(tools, values):
    text = _refused(tools, input=values, flags="e", percentile="x")

    assert "Invalid value <x> for parameter <percentile>" in text


def test_zones_must_be_an_integer_map(tools, values):
    text = _refused(tools, input=values, zones="uv_3")

    assert "Zoning raster must be of type CELL" in text


def test_unknown_zones_are_refused(tools, values):
    text = _refused(tools, input=values, zones="uv_no_zones")

    assert "uv_no_zones" in text


def test_an_unknown_format_is_refused_by_the_parser(tools, values):
    text = _refused(tools, input=values, format="xml")

    assert "Value <xml> out of range for parameter <format>" in text


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, values):
    text = _refused(tools, input=values, where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
