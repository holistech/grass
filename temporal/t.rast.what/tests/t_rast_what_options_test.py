"""Test the selection, the input and the output options of t.rast.what

The data are described in conftest.py.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import message
from grass.tools import ToolError

COORDINATES = "0.5,2.5,2.5,0.5"
FIRST = "0.5000000000|2.5000000000"
SECOND = "2.5000000000|0.5000000000"


def _lines(result):
    return result.stdout.splitlines()


def _values(result):
    return [line.split("|")[-1] for line in _lines(result)]


def test_where_selects_the_maps(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled,
        coordinates=COORDINATES,
        where="start_time > '2001-01-02'",
    )

    # The comparison is one of text: the map that starts on 2001-01-02 is kept
    assert _lines(result) == [
        f"{FIRST}|2001-01-02 00:00:00|2001-01-03 00:00:00|111",
        f"{FIRST}|2001-01-03 00:00:00|2001-01-04 00:00:00|211",
        f"{SECOND}|2001-01-02 00:00:00|2001-01-03 00:00:00|133",
        f"{SECOND}|2001-01-03 00:00:00|2001-01-04 00:00:00|233",
    ]


@pytest.fixture(scope="module")
def reversed_names(tools):
    """Two maps whose alphabetical order is the reverse of their time order:
    wh_zz (5) on the first day and wh_aa (6) on the second"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "wh_b",
        [MapSpec("wh_zz", "5", day(0), day(1)), MapSpec("wh_aa", "6", day(1), day(2))],
    )
    return "wh_b"


def test_the_maps_come_in_the_order_of_time_by_default(tools, reversed_names):
    result = tools.t_rast_what(strds=reversed_names, coordinates="0.5,2.5")

    assert _values(result) == ["5", "6"]


def test_order_sorts_the_maps_by_the_named_column(tools, reversed_names):
    result = tools.t_rast_what(
        strds=reversed_names, coordinates="0.5,2.5", order="name"
    )

    assert _values(result) == ["6", "5"]


def test_order_takes_several_columns(tools, reversed_names):
    result = tools.t_rast_what(
        strds=reversed_names, coordinates="0.5,2.5", order="mapset,name"
    )

    assert _values(result) == ["6", "5"]


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_stdin_gives_the_same_values_as_coordinates(tools, sampled, layout):
    from_stdin = tools.t_rast_what(
        strds=sampled,
        flags="in",
        layout=layout,
        stdin=StringIO("0.5 2.5\n2.5 0.5\n"),
    )
    from_options = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, flags="n", layout=layout
    )

    assert from_stdin.stdout == from_options.stdout


def test_a_third_column_of_stdin_is_the_name_of_the_site_in_the_row_layout(
    tools, sampled
):
    result = tools.t_rast_what(
        strds=sampled,
        flags="in",
        stdin=StringIO("0.5 2.5 siteA\n2.5 0.5 siteB\n"),
    )

    assert _lines(result)[0] == "x|y|site|start|end|value"
    assert (
        _lines(result)[1] == f"{FIRST}|siteA|2001-01-01 00:00:00|2001-01-02 00:00:00|11"
    )
    assert (
        _lines(result)[-1]
        == f"{SECOND}|siteB|2001-01-03 00:00:00|2001-01-04 00:00:00|233"
    )


def test_the_name_of_the_site_is_part_of_the_column_title_in_the_col_layout(
    tools, sampled
):
    result = tools.t_rast_what(
        strds=sampled,
        flags="in",
        layout="col",
        stdin=StringIO("0.5 2.5 siteA\n2.5 0.5 siteB\n"),
    )

    assert _lines(result)[0] == (
        "start|end|0.5000000000,2.5000000000,siteA|2.5000000000,0.5000000000,siteB"
    )


def test_the_name_of_the_site_in_the_timerow_layout(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled,
        flags="in",
        layout="timerow",
        stdin=StringIO("0.5 2.5 siteA\n2.5 0.5 siteB\n"),
    )

    assert _lines(result)[0].startswith("x|y|site|")
    assert _lines(result)[1:] == [
        "0.5|2.5|siteA|11|111|211",
        "2.5|0.5|siteB|33|133|233",
    ]


def test_today_coordinates_win_over_the_i_flag(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled,
        coordinates="0.5,2.5",
        flags="i",
        stdin=StringIO("2.5 0.5\n"),
    )

    assert _values(result) == ["11", "111", "211"]


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.what -i uses the coordinates option, which wins over the standard input",
)
def test_the_i_flag_ignores_the_coordinates(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled,
        coordinates="0.5,2.5",
        flags="i",
        stdin=StringIO("2.5 0.5\n"),
    )

    assert _values(result) == ["33", "133", "233"]


def test_output_writes_a_file_and_nothing_to_the_screen(tools, sampled, tmp_path):
    path = tmp_path / "what.txt"

    result = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, output=str(path), flags="n"
    )

    assert result.stdout == ""
    assert path.read_text().splitlines()[0] == "x|y|start|end|value"
    assert len(path.read_text().splitlines()) == 7


def test_a_dash_as_output_is_the_standard_output(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates="0.5,2.5", output="-")

    assert _values(result) == ["11", "111", "211"]


def test_an_existing_output_is_refused_without_overwrite(tools, sampled, tmp_path):
    path = tmp_path / "what.txt"
    path.write_text("keep")

    with pytest.raises(ToolError) as error:
        tools.t_rast_what(strds=sampled, coordinates="0.5,2.5", output=str(path))

    assert "exists. To overwrite, use the --overwrite flag" in message(error.value)
    assert path.read_text() == "keep"


def test_overwrite_replaces_the_output(tools, sampled, tmp_path):
    path = tmp_path / "what.txt"
    path.write_text("old")

    tools.t_rast_what(
        strds=sampled, coordinates="0.5,2.5", output=str(path), overwrite=True
    )

    assert path.read_text().splitlines()[0].endswith("|11")


@pytest.mark.parametrize("nprocs", [1, 2, 3])
def test_nprocs_gives_the_same_values(tools, sampled, nprocs):
    result = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, nprocs=nprocs)

    assert sorted(_lines(result)) == sorted(
        tools.t_rast_what(strds=sampled, coordinates=COORDINATES).stdout.splitlines()
    )


@pytest.mark.parametrize("layout", ["col", "timerow"])
def test_nprocs_does_not_change_the_other_layouts(tools, sampled, layout):
    single = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, layout=layout)
    several = tools.t_rast_what(
        strds=sampled, coordinates=COORDINATES, layout=layout, nprocs=3
    )

    assert several.stdout == single.stdout


def test_today_the_order_of_the_rows_depends_on_nprocs(tools, sampled):
    # Every process writes the maps it got: with three processes each has one
    # map, so the lines come map after map instead of point after point.
    result = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, nprocs=3)

    assert _values(result) == ["11", "33", "111", "133", "211", "233"]


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.what lists the rows map by map instead of point by point when nprocs is above 1",
)
def test_the_order_of_the_rows_does_not_depend_on_nprocs(tools, sampled):
    result = tools.t_rast_what(strds=sampled, coordinates=COORDINATES, nprocs=3)

    assert _values(result) == ["11", "111", "211", "33", "133", "233"]
