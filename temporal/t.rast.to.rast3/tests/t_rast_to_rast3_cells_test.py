"""Test the layers, gaps and data type of the 3D raster maps of t.rast.to.rast3

The dataset has four steps of three months: tr_a holds 1 in every cell, tr_b
holds 10 r + c except in the middle column, which is empty, the third step
(July) has no map and tr_c holds 3 in every cell. The layers of the cube run
from the bottom (the first step) upwards.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import message
from grass.tools import ToolError

CELLS = [
    [[1.0] * 3] * 2,
    [[11.0, None, 13.0], [21.0, None, 23.0]],
    [[None] * 3] * 2,
    [[3.0] * 3] * 2,
]


@pytest.fixture(scope="module")
def cells(tools):
    """The dataset described above; returns its name"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "tr_cells",
        [
            MapSpec("tr_a", "1", datetime(2001, 1, 1), datetime(2001, 4, 1)),
            MapSpec(
                "tr_b",
                "if(col() == 2, null(), row() * 10 + col())",
                datetime(2001, 4, 1),
                datetime(2001, 7, 1),
            ),
            MapSpec("tr_c", "3", datetime(2001, 10, 1), datetime(2002, 1, 1)),
        ],
    )
    return "tr_cells"


def _layers(tools, name, path):
    """The cells of a 3D map as layers of rows, from the bottom"""
    tools.g_region(raster_3d=name)
    tools.r3_out_ascii(input=name, output=str(path), null_value="N")
    lines = path.read_text().splitlines()
    header = dict(line.split(": ") for line in lines[:11])
    rows, cols = int(header["rows"]), int(header["cols"])
    words = [word for line in lines[11:] for word in line.split()]
    values = [None if word == "N" else float(word) for word in words]
    per_layer = rows * cols
    return [
        [values[start + row * cols : start + (row + 1) * cols] for row in range(rows)]
        for start in range(0, len(values), per_layer)
    ]


def test_the_layers_are_the_maps_in_the_order_of_time_with_a_gap(
    tools, cells, prefix, tmp_path
):
    tools.t_rast_to_rast3(input=cells, output=prefix)

    # The first layer of the ascii output is the bottom one
    assert _layers(tools, prefix, tmp_path / "cube.txt") == CELLS


def test_the_gap_is_filled_by_a_temporary_map_that_is_removed(tools, cells, prefix):
    before = tools.g_list(type="raster").stdout.split()

    tools.t_rast_to_rast3(input=cells, output=prefix)

    assert tools.g_list(type="raster").stdout.split() == before


def test_the_current_region_is_unchanged(tools, cells, prefix):
    before = tools.g_region(flags="g3").keyval

    tools.t_rast_to_rast3(input=cells, output=prefix)

    assert tools.g_region(flags="g3").keyval == before


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("expression", "datatype"),
    [("5", "DCELL"), ("float(5.5)", "FCELL"), ("double(5.5)", "DCELL")],
)
def test_the_data_type_follows_the_first_map(tools, prefix, expression, datatype):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_a", expression, datetime(2001, 1, 1), datetime(2001, 2, 1)
            ),
            MapSpec(
                f"{prefix}_b", expression, datetime(2001, 2, 1), datetime(2001, 3, 1)
            ),
        ],
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    assert tools.r3_info(map=prefix, flags="g").keyval["datatype"] == f'"{datatype}"'


def test_the_cube_has_a_title_and_a_description(tools, cells, prefix):
    tools.t_rast_to_rast3(input=cells, output=prefix)

    text = tools.r3_info(map=prefix).stdout
    assert "Title:    Space time voxel cube" in text
    assert "created with t.rast.to.rast3" in text


def test_a_name_with_a_mapset_is_taken(tools, cells, prefix):
    tools.t_rast_to_rast3(input=cells, output=f"{prefix}@PERMANENT")

    assert tools.r3_info(map=prefix, flags="g").keyval["depths"] == 4


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_cube_and_its_registration(tools, cells, prefix):
    tools.t_rast_to_rast3(input=cells, output=prefix)

    tools.t_rast_to_rast3(input=cells, output=prefix, overwrite=True)

    info = tools.t_info(type="raster_3d", input=prefix, flags="g").keyval
    assert info["start_time"] == "'2001-01-01 00:00:00'"


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_to_rast3(**options)
    return message(error.value)


def test_an_existing_cube_is_refused_without_overwrite(tools, cells, prefix):
    tools.t_rast_to_rast3(input=cells, output=prefix)

    text = _refused(tools, input=cells, output=prefix)

    assert f"<{prefix}> exists. To overwrite, use the --overwrite flag" in text


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, cells, prefix, missing):
    options = {"input": cells, "output": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="tr_missing", output=prefix)

    assert "Space time dataset <tr_missing> of type <strds> not found" in text


def test_a_dataset_without_maps_is_refused(tools, prefix):
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_empty",
        title="t",
        description="d",
    )

    text = _refused(tools, input=f"{prefix}_empty", output=prefix)

    assert f"Space time raster dataset <{prefix}_empty@PERMANENT> is empty" in text
    assert "Wrong granularity" not in text


def test_the_tool_prints_nothing_to_the_standard_output(tools, cells, prefix):
    result = tools.t_rast_to_rast3(input=cells, output=prefix)

    assert result.stdout == ""


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("expression", "datatype"), [("float(5.5)", "FCELL"), ("double(5.5)", "DCELL")]
)
def test_the_layer_of_a_gap_has_the_type_of_the_first_map(
    tools, prefix, tmp_path, expression, datatype
):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_a", expression, datetime(2001, 1, 1), datetime(2001, 2, 1)
            ),
            MapSpec(
                f"{prefix}_c", expression, datetime(2001, 3, 1), datetime(2001, 4, 1)
            ),
        ],
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=prefix)

    assert tools.r3_info(map=prefix, flags="g").keyval["datatype"] == f'"{datatype}"'
    assert _layers(tools, prefix, tmp_path / "gap.txt") == [
        [[5.5] * 3] * 2,
        [[None] * 3] * 2,
        [[5.5] * 3] * 2,
    ]


def test_a_map_that_is_gone_from_the_mapset_stops_the_run_with_a_message(tools, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", "1", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec(f"{prefix}_b", "1", datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    tools.g_remove(type="raster", name=f"{prefix}_b", flags="f")

    text = _refused(tools, input=f"{prefix}_in", output=prefix)

    assert f"Unable to create 3D raster map <{prefix}>" in text
    assert prefix not in tools.g_list(type="raster_3d", flags="m").stdout
    assert "temporary_null_map" not in tools.g_list(type="raster").stdout


def test_a_failing_r3_support_warns_and_keeps_the_cube(
    tools, broken_tools, cells, prefix
):
    result = broken_tools("r3.support").t_rast_to_rast3(input=cells, output=prefix)

    assert "r3.support failed to set units" in result.stderr
    assert tools.r3_info(map=prefix, flags="g").keyval["depths"] == 4
    assert (
        tools.t_info(type="raster_3d", input=prefix, flags="g").keyval["start_time"]
        == "'2001-01-01 00:00:00'"
    )


def test_a_refused_3d_region_stops_with_a_message(broken_tools, cells, prefix):
    # gs.use_temp_region calls g.region first (measured 29.10.2026 with a
    # logging stand-in: "--o -u save=..." before "t=... b=... tbres=..."), and
    # that call must reach the real tool; tbres= pins the call that sets the 3D
    # region.
    with pytest.raises(ToolError) as error:
        broken_tools("g.region", failing="tbres=").t_rast_to_rast3(
            input=cells, output=prefix
        )

    text = message(error.value)
    assert error.value.returncode == 1
    assert "Unable to set 3D region" in text
    assert "Traceback" not in text


def test_broken_tools_refuses_passing_and_failing_together(broken_tools):
    with pytest.raises(ValueError, match="exclude each other"):
        broken_tools("g.region", passing="-p", failing="tbres=")
