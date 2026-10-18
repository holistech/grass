"""Test the refusals of t.vect.db.select

The tool runs v.db.select for each map; its failures end the tool with the
message of v.db.select and a traceback.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_db_select(**options)
    return message(error.value)


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
    ("columns", {"columns": "nothere"}, "no such column: nothere"),
    ("where", {"where": "cat >"}, "incomplete input"),
    ("layer", {"layer": 3}, "Database connection not defined for layer <3>"),
]


@pytest.mark.parametrize(("name", "options", "reason"), FAILURES)
def test_today_a_failure_of_v_db_select_ends_with_its_message_and_a_traceback(
    tools, intervals, name, options, reason
):
    text = _refused(tools, input=intervals, **options)

    assert reason in text
    assert "Traceback" in text


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize(("name", "options", "reason"), FAILURES)
def test_a_failure_of_v_db_select_is_reported_as_a_message(
    tools, intervals, name, options, reason
):
    assert "Traceback" not in _refused(tools, input=intervals, **options)


def test_today_a_column_that_only_some_maps_have_ends_with_an_error(tools, changing):
    # b exists in the first map only; the rows of the first map are lost.
    text = _refused(tools, input=changing, columns="b")

    assert "no such column: b" in text


def test_a_t_where_with_a_syntax_error_ends_with_a_traceback(tools, intervals):
    text = _refused(tools, input=intervals, t_where="nonsense =")

    assert "Traceback" in text
    assert "syntax error" in text
