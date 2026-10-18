"""Test the refusals of t.rast3d.univar"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_univar(**options)
    return message(error.value)


def test_the_input_is_required(tools):
    assert "Required parameter <input> not set" in _refused(tools, output="out.txt")


def test_an_unknown_input_is_refused(tools):
    text = _refused(tools, input="uv3_missing")

    assert "Space time dataset <uv3_missing> of type <str3ds> not found" in text


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


def test_zones_from_a_double_map_are_rounded(tools, values):
    # r3.univar (raster/r.univar/r3.univar_main.c) rounds the value of a double
    # zones map to the nearest integer, halves away from zero, instead of
    # refusing it. uv3_3 holds n / 2, so the zones 1 to 6 hold the voxels with
    # n = 1 and 2, 3 and 4, and so on up to 11 and 12 of the first map.
    result = tools.t_rast3d_univar(
        input=values, zones="uv3_3", where="start_time < '2001-01-02'"
    )

    rows = [line.split("|") for line in result.stdout.splitlines()[1:]]
    assert [(row[3], row[5], row[-2]) for row in rows] == [
        ("1", "2", "3"),
        ("2", "2", "7"),
        ("3", "2", "11"),
        ("4", "2", "15"),
        ("5", "2", "19"),
        ("6", "2", "23"),
    ]


def test_unknown_zones_are_refused(tools, values):
    text = _refused(tools, input=values, zones="uv3_no_zones")

    assert "uv3_no_zones" in text


def test_an_unknown_format_is_refused_by_the_parser(tools, values):
    text = _refused(tools, input=values, format="xml")

    assert "Value <xml> out of range for parameter <format>" in text
