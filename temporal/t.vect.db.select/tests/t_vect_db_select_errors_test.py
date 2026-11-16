"""Test the refusals of t.vect.db.select

The tool runs v.db.select for each map; its failures end the tool with the
message of v.db.select and a traceback.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError, Tools


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_db_select(**options)
    return message(error.value)


def _failed(tools, **options):
    """The result of a run that is expected to end with an error

    A ToolError does not carry stdout, which these tests need to show that the
    refusal came before the first output line.
    """
    # Tools has no public access to its environment (grass.tools of
    # 21.10.2026); broken_tools in temporal/conftest.py does the same.
    result = Tools(
        env=tools._original_env,  # noqa: SLF001
        errors="ignore",
        consistent_return_value=True,
        capture_stderr=True,
    ).t_vect_db_select(**options)
    assert result.returncode == 1
    return result


def test_the_input_is_required(tools):
    assert "Required parameter <input> not set" in _refused(tools)


def test_an_unknown_input_is_refused(tools, intervals):
    text = _refused(tools, input="dbs_missing")

    assert "Space time dataset <dbs_missing> of type <stvds> not found" in text


def test_the_parser_refuses_a_format_outside_the_list(tools, intervals):
    text = _refused(tools, input=intervals, format="yaml")

    assert "Value <yaml> out of range for parameter <format>" in text


def test_a_long_csv_separator_is_refused(tools, intervals):
    text = _refused(tools, input=intervals, format="csv", separator="ab")

    assert "A standard CSV separator (delimiter) is only one character long" in text


def test_a_separator_is_refused_with_json(tools, intervals):
    text = _refused(tools, input=intervals, format="json", separator=",")

    assert "Separator option is not allowed with JSON format" in text


FAILURES = [
    ("where", {"where": "cat >"}, "incomplete input"),
]


@pytest.mark.parametrize(("name", "options", "reason"), FAILURES)
def test_a_failure_of_v_db_select_is_reported_as_a_message(
    tools, intervals, name, options, reason
):
    text = _refused(tools, input=intervals, **options)

    assert reason in text
    assert "Error running v.db.select" in text
    assert "Traceback" not in text


@pytest.mark.parametrize("output_format", ["plain", "csv", "json"])
def test_a_column_missing_in_the_last_map_prints_nothing(tools, partial, output_format):
    # b exists in dp_1 and dp_2 but not in the third map, so the rows of the
    # first two maps must not be printed before the refusal.
    result = _failed(tools, input=partial, columns="b", format=output_format)

    assert "Column <b> not found in the maps: dp_3@" in message(result)
    assert "dp_1" not in message(result)
    assert "dp_2" not in message(result)
    assert result.stdout == ""


def test_a_column_missing_in_one_of_two_maps_names_only_that_map(tools, changing):
    # c exists in dc_2 only, so dc_1 lacks it; a is in both.
    text = _refused(tools, input=changing, columns="a,c")

    assert "Column <c> not found in the maps: dc_1@" in text
    assert "dc_2" not in text


def test_every_missing_column_is_named_in_one_message(tools, changing):
    # b is in dc_1 only and c in dc_2 only, so each lacks one of the two.
    text = _refused(tools, input=changing, columns="b,c")

    assert "Column <b> not found in the maps: dc_2@" in text
    assert "Column <c> not found in the maps: dc_1@" in text


def test_a_column_missing_in_every_map_names_all_maps(tools, intervals):
    text = _refused(tools, input=intervals, columns="nothere")

    assert "Column <nothere> not found in the maps:" in text
    for k in (1, 2, 3):
        assert f"di_{k}@" in text
    assert "Traceback" not in text


def test_the_column_check_ignores_the_case_of_the_name(tools, partial):
    result = tools.t_vect_db_select(input=partial, columns="A")

    assert result.stdout.split("\n")[0] == "start_time|end_time|a"


@pytest.mark.parametrize("columns", ["*", "a+1", "a,*"])
def test_the_column_check_leaves_stars_and_expressions_to_v_db_select(
    tools, partial, columns
):
    result = tools.t_vect_db_select(input=partial, columns=columns)

    assert result.returncode == 0


def test_a_layer_without_a_table_ends_before_the_first_output_line(tools, intervals):
    result = _failed(tools, input=intervals, layer=3)

    assert "No attribute table found for the maps: di_1@" in message(result)
    assert "di_3@" in message(result)
    assert result.stdout == ""


def test_a_t_where_with_a_syntax_error_is_reported_as_a_message(tools, intervals):
    text = _refused(tools, input=intervals, t_where="nonsense =")

    assert "Traceback" not in text
    assert "Invalid t_where condition <nonsense =>" in text
    assert "syntax error" in text
