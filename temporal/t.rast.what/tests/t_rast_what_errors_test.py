"""Test the refusals of t.rast.what"""

from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
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


@pytest.mark.parametrize("nprocs", [1, 2])
def test_a_failing_r_what_is_reported_by_the_tool(tools, nprocs):
    # The second map is still registered but gone from the mapset, so r.what
    # fails on its input.
    small_region(tools, 3, 3)
    name = f"wh_gone_{nprocs}"
    create_stds(
        tools,
        "strds",
        name,
        [MapSpec(f"{name}_{k}", "1", day(k), day(k + 1)) for k in range(2)],
    )
    tools.g_remove(type="raster", name=f"{name}_1", flags="f")

    text = _refused(tools, strds=name, coordinates="1,1", nprocs=nprocs)

    assert "Error running r.what" in text
    assert "Traceback" not in text


NO_LOCATION_SAMPLED = (
    "No location was sampled: r.what returned no line. "
    "Check the locations and the separator."
)


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_no_sampled_location_is_refused(tools, sampled, layout):
    # r.what reads the pipe-separated line as one word, warns and writes no line.
    text = _refused(
        tools,
        strds=sampled,
        layout=layout,
        flags="i",
        separator="pipe",
        stdin=StringIO("2.5|3.5|s1\n"),
    )

    assert NO_LOCATION_SAMPLED in text
    assert "Traceback" not in text


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_a_point_map_without_points_is_refused(tools, sampled, layout):
    # The project lives for the whole module and v.edit refuses an existing
    # map, so each layout creates a map of its own.
    empty = f"wh_no_points_{layout}"
    tools.v_edit(map=empty, tool="create")

    text = _refused(tools, strds=sampled, layout=layout, points=empty)

    assert NO_LOCATION_SAMPLED in text
    assert "Traceback" not in text


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_no_sampled_location_leaves_the_output_file(tools, sampled, layout, tmp_path):
    target = tmp_path / "kept.txt"
    target.write_bytes(b"kept\n")

    text = _refused(
        tools,
        strds=sampled,
        layout=layout,
        flags="i",
        separator="pipe",
        stdin=StringIO("2.5|3.5|s1\n"),
        output=str(target),
        overwrite=True,
    )

    assert NO_LOCATION_SAMPLED in text
    assert target.read_bytes() == b"kept\n"


def test_no_sampled_location_does_not_create_the_output_file(tools, sampled, tmp_path):
    target = tmp_path / "never.txt"

    _refused(
        tools,
        strds=sampled,
        flags="i",
        separator="pipe",
        stdin=StringIO("2.5|3.5|s1\n"),
        output=str(target),
    )

    assert not target.exists()


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_a_location_outside_the_region_is_still_written(tools, sampled, layout):
    # r.what writes a null value for it, so this is a sampled location.
    result = tools.t_rast_what(strds=sampled, layout=layout, coordinates="50,50")

    assert "*" in result.stdout
