"""Test the refusals of t.rast3d.extract and a relative time dataset"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_extract(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, quarterly, prefix, missing):
    options = {"input": quarterly, "output": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_expression_needs_a_basename(tools, quarterly, prefix):
    text = _refused(tools, input=quarterly, output=prefix, expression="e3_quarterly")

    assert "You need to specify the base name of new created maps" in text


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="e3_missing", output=prefix)

    assert "Space time dataset <e3_missing> of type <raster3d> not found" in text


def test_a_wrong_expression_stops_the_computation(tools, quarterly, prefix):
    text = _refused(
        tools,
        input=quarterly,
        output=prefix,
        expression="e3_quarterly +",
        basename=f"{prefix}_x",
    )

    assert "Error in computation process" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(tools, quarterly, prefix):
    tools.t_rast3d_extract(input=quarterly, output=prefix)

    text = _refused(tools, input=quarterly, output=prefix)

    assert f"Space time raster3d dataset <{prefix}> is already in the database" in text
    assert stds_info(tools, "str3ds", prefix)["number_of_maps"] == 6


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_known_maps_make_the_run_fail(tools, quarterly, prefix):
    options = {
        "input": quarterly,
        "where": "start_time > '2002-01-01'",
        "expression": "e3_quarterly",
        "basename": f"{prefix}_x",
    }
    tools.t_rast3d_extract(output=f"{prefix}_a", **options)

    with pytest.raises(ToolError) as error:
        tools.t_rast3d_extract(output=f"{prefix}_b", **options)

    # The text comparison "2002-01-01 00:00:00" > "2002-01-01" holds, so the
    # first map of the selection is the one of January 2002.
    assert (
        f"Map <{prefix}_x_2002_01@PERMANENT> is already in temporal database, use "
        "overwrite flag to overwrite"
    ) in message(error.value)
    # Nothing is made for the refused run.
    assert (
        f"{prefix}_b"
        not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout
    )


@pytest.fixture(scope="module")
def relative(tools):
    """Four maps of 14 days from day 0 holding 100 to 400, in relative days"""
    small_region(tools, 1, 2, depths=1)
    create_stds(
        tools,
        "str3ds",
        "e3_relative",
        [MapSpec(f"e3_r{k}", 100 * (k + 1), 14 * k, 14 * (k + 1)) for k in range(4)],
        temporaltype="relative",
        unit="days",
    )
    return "e3_relative"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_relative_time_keeps_the_time_and_the_unit(tools, relative, prefix):
    # start_time >= 28 selects the maps 28 to 42 and 42 to 56 (300, 400);
    # the expression keeps only values above 300, so one map remains. The
    # counter of the name counts the selected maps, empty ones included: the
    # map that remains is the second.
    tools.t_rast3d_extract(
        input=relative,
        output=prefix,
        where="start_time >= 28",
        expression="if(e3_relative > 300, e3_relative, null())",
        basename=f"{prefix}_x",
    )

    info = stds_info(tools, "str3ds", prefix)
    assert (info["temporal_type"], info["start_time"], info["end_time"]) == (
        "relative",
        "'42'",
        "'56'",
    )
    assert info["unit"] == "days"
    assert [
        (row.name, row.start, row.min) for row in list_maps(tools, "str3ds", prefix)
    ] == [(f"{prefix}_x_00002", 42, 400.0)]


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, quarterly, prefix):
    text = _refused(tools, input=quarterly, output=prefix, where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout
