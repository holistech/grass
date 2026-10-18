"""Test the layouts and the columns of t.rast.what

The data are described in conftest.py. The coordinates in the text of the row
and column layouts have ten decimals (r.what), those of the timerow layout the
shortest form; this was measured on 18.10.2026, the values are derived.
"""

import pytest

SAMPLE = {
    "p1": ("0.5000000000", "2.5000000000", ["11", "111", "211"]),
    "p2": ("2.5000000000", "0.5000000000", ["33", "133", "233"]),
    "p3": ("1.5000000000", "1.5000000000", ["22", "*", "222"]),
}
TIMES = [
    ("2001-01-01 00:00:00", "2001-01-02 00:00:00"),
    ("2001-01-02 00:00:00", "2001-01-03 00:00:00"),
    ("2001-01-03 00:00:00", "2001-01-04 00:00:00"),
]
COORDINATES = "0.5,2.5,2.5,0.5"


def _lines(result):
    return result.stdout.splitlines()


def _row_lines(names, categories=None):
    """The lines of the row layout for the given points, point after point"""
    lines = []
    for index, name in enumerate(names):
        x, y, values = SAMPLE[name]
        for (start, end), value in zip(TIMES, values, strict=True):
            prefix = f"{categories[index]}|" if categories else ""
            lines.append(f"{prefix}{x}|{y}|{start}|{end}|{value}")
    return lines


def test_row_layout_has_a_line_per_point_and_map(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, flags="n")

    assert _lines(result) == ["x|y|start|end|value", *_row_lines(["p1", "p2"])]


def test_without_the_n_flag_there_is_no_header(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates=COORDINATES)

    assert _lines(result) == _row_lines(["p1", "p2"])


def test_row_layout_is_the_default(tools, sampled):
    explicit = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, layout="row")
    default = tools.t_rast_what(strds=sampled, coordinates=COORDINATES)

    assert explicit.stdout == default.stdout


def test_col_layout_has_a_line_per_map_and_a_column_per_point(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, layout="col", flags="n"
    )

    assert _lines(result) == [
        "start|end|0.5000000000,2.5000000000|2.5000000000,0.5000000000",
        "2001-01-01 00:00:00|2001-01-02 00:00:00|11|33",
        "2001-01-02 00:00:00|2001-01-03 00:00:00|111|133",
        "2001-01-03 00:00:00|2001-01-04 00:00:00|211|233",
    ]


def test_timerow_layout_has_a_line_per_point_and_a_column_per_map(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, layout="timerow", flags="n"
    )

    assert _lines(result) == [
        "x|y|2001-01-01 00:00:00;2001-01-02 00:00:00"
        "|2001-01-02 00:00:00;2001-01-03 00:00:00"
        "|2001-01-03 00:00:00;2001-01-04 00:00:00",
        "0.5|2.5|11|111|211",
        "2.5|0.5|33|133|233",
    ]


def test_points_give_one_location_each_in_the_row_layout(tools, sampled):
    result = tools.t_rast_what(strds=sampled, points="wh_pts", flags="n")

    assert _lines(result) == [
        "x|y|start|end|value",
        *_row_lines(["p1", "p2", "p3"]),
    ]


def test_the_v_flag_adds_the_category_of_the_points(tools, sampled):
    result = tools.t_rast_what(strds=sampled, points="wh_pts", flags="nv")

    assert _lines(result) == [
        "cat|x|y|start|end|value",
        *_row_lines(["p1", "p2", "p3"], categories=[7, 8, 9]),
    ]


def test_the_v_flag_puts_the_category_before_the_coordinates_in_the_col_layout(
    tools, sampled
):
    result = tools.t_rast_what(strds=sampled, points="wh_pts", flags="nv", layout="col")

    assert _lines(result) == [
        "start|end|7,0.5000000000,2.5000000000|8,2.5000000000,0.5000000000"
        "|9,1.5000000000,1.5000000000",
        "2001-01-01 00:00:00|2001-01-02 00:00:00|11|33|22",
        "2001-01-02 00:00:00|2001-01-03 00:00:00|111|133|*",
        "2001-01-03 00:00:00|2001-01-04 00:00:00|211|233|222",
    ]


def test_the_v_flag_in_the_timerow_layout(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled, points="wh_pts", flags="nv", layout="timerow"
    )

    lines = _lines(result)
    assert lines[0].startswith("cat|x|y|2001-01-01 00:00:00;2001-01-02 00:00:00|")
    assert lines[1:] == [
        "7|0.5|2.5|11|111|211",
        "8|2.5|0.5|33|133|233",
        "9|1.5|1.5|22|*|222",
    ]


def test_a_cell_without_a_value_is_a_star(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates="1.5,1.5")

    assert [line.split("|")[-1] for line in _lines(result)] == ["22", "*", "222"]


def test_null_value_replaces_the_star(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates="1.5,1.5", null_value="NA")

    assert [line.split("|")[-1] for line in _lines(result)] == ["22", "NA", "222"]


def test_a_point_outside_the_maps_has_no_value(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates="100,100")

    assert [line.split("|")[-1] for line in _lines(result)] == ["*", "*", "*"]


@pytest.mark.parametrize(("separator", "character"), [(";", ";"), ("tab", "\t")])
def test_separator_replaces_the_bar(tools, sampled, separator, character):
    result = tools.t_rast_what(
        strds=sampled, coordinates="0.5,2.5", separator=separator, flags="n"
    )

    assert _lines(result)[0] == character.join(["x", "y", "start", "end", "value"])
    assert _lines(result)[1].split(character)[-1] == "11"


def test_separator_applies_to_the_col_layout(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, layout="col", separator=";", flags="n"
    )

    assert (
        _lines(result)[0]
        == "start;end;0.5000000000,2.5000000000;2.5000000000,0.5000000000"
    )
    assert _lines(result)[1] == "2001-01-01 00:00:00;2001-01-02 00:00:00;11;33"
