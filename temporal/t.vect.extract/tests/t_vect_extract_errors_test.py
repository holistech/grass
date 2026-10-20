"""Test the refusals of t.vect.extract"""

import pytest

from grass.temporal.testing.readback import message, stds_info
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


def test_known_maps_make_the_run_fail(tools, quarterly, prefix):
    options = {
        "input": quarterly,
        "where": "start_time > '2002-01-01'",
        "expression": "value > 0",
        "basename": f"{prefix}_x",
    }
    tools.t_vect_extract(output=f"{prefix}_a", **options)

    with pytest.raises(ToolError) as error:
        tools.t_vect_extract(output=f"{prefix}_b", **options)

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


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, quarterly, prefix):
    text = _refused(tools, input=quarterly, output=prefix, where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout
