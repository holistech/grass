"""Test the refusals of t.vect.extract"""

import pytest

from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_extract(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, quarterly, prefix, missing):
    options = {"input": quarterly, "output": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_expression_needs_a_basename(tools, quarterly, prefix):
    text = _refused(tools, input=quarterly, output=prefix, expression="value > 0")

    assert "You need to specify the base name of new created maps" in text


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="ve_missing", output=prefix)

    assert "Space time dataset <ve_missing> of type <vector> not found" in text


def test_an_unknown_type_is_refused_by_the_parser(tools, quarterly, prefix):
    text = _refused(tools, input=quarterly, output=prefix, type="polygon")

    assert "Value <polygon> out of range for parameter <type>" in text


def test_a_wrong_expression_stops_the_computation(tools, quarterly, prefix):
    text = _refused(
        tools,
        input=quarterly,
        output=prefix,
        expression="nothing_like_a_column >",
        basename=f"{prefix}_x",
    )

    assert "Error in computation process" in text


def test_an_existing_output_is_refused_without_overwrite(tools, quarterly, prefix):
    tools.t_vect_extract(input=quarterly, output=prefix)

    text = _refused(tools, input=quarterly, output=prefix)

    assert f"Space time vector dataset <{prefix}> is already in the database" in text
    assert stds_info(tools, "stvds", prefix)["number_of_maps"] == 6


def test_a_selection_that_finds_no_map_warns_and_makes_no_dataset(
    tools, quarterly, prefix
):
    result = tools.t_vect_extract(
        input=quarterly, output=prefix, where="start_time > '2030-01-01'"
    )

    assert (
        f"Nothing found in the database for space time dataset <{quarterly}> "
        "(type: vector): Dataset is empty or where clause is too constrained or "
        "incorrect"
    ) in message(result)
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


def test_today_known_maps_are_reported_but_the_run_succeeds(tools, quarterly, prefix):
    # The second run creates the same map names for another dataset. The maps
    # are in the temporal database already, so each gets an error message and
    # is skipped, but the exit code is 0 and an empty dataset is made (as in
    # t.rast.extract).
    options = {
        "input": quarterly,
        "where": "start_time > '2002-01-01'",
        "expression": "value > 0",
        "basename": f"{prefix}_x",
    }
    tools.t_vect_extract(output=f"{prefix}_a", **options)

    result = tools.t_vect_extract(output=f"{prefix}_b", **options)

    assert result.returncode == 0
    assert (
        f"Map <{prefix}_x_2002_04@PERMANENT> is already in temporal database, use "
        "overwrite flag to overwrite"
    ) in message(result)
    assert list_maps(tools, "stvds", f"{prefix}_b") == []


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_known_maps_make_the_run_fail(tools, quarterly, prefix):
    options = {
        "input": quarterly,
        "where": "start_time > '2002-01-01'",
        "expression": "value > 0",
        "basename": f"{prefix}_x",
    }
    tools.t_vect_extract(output=f"{prefix}_a", **options)

    with pytest.raises(ToolError):
        tools.t_vect_extract(output=f"{prefix}_b", **options)
