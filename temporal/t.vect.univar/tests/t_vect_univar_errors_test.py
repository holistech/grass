"""Test the refusals of t.vect.univar

v.univar runs once per map, and its failures end the tool with a traceback
(the library calls gs.parse_command() without a handler).
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_univar(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "column"])
def test_a_required_option_is_checked_by_the_parser(tools, points, missing):
    options = {"input": points, "column": "value"}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, points):
    text = _refused(tools, input="uv_missing", column="value")

    assert "Space time vector dataset <uv_missing@PERMANENT> not found" in text


def test_an_empty_dataset_is_refused(tools, points):
    tools.t_create(
        type="stvds",
        temporaltype="absolute",
        output="uv_void",
        title="void",
        description="no maps",
        overwrite=True,
    )

    text = _refused(tools, input="uv_void", column="value")

    assert "Space time vector dataset <uv_void@PERMANENT> is empty" in text


def test_a_twhere_that_selects_no_map_says_the_dataset_is_empty(tools, points):
    text = _refused(
        tools, input=points, column="value", twhere="start_time > '2030-01-01'"
    )

    assert "Space time vector dataset <uv_pts@PERMANENT> is empty" in text


def test_the_parser_refuses_a_type_outside_the_list(tools, points):
    text = _refused(tools, input=points, column="value", type="polygon")

    assert "Value <polygon> out of range for parameter <type>" in text


FAILURES = [
    ("where", {"where": "value >"}),
    ("column", {"column": "nothere"}),
    ("layer", {"layer": 3}),
]


@pytest.mark.parametrize(("name", "options"), FAILURES)
def test_today_a_failure_of_v_univar_ends_with_a_traceback(
    tools, points, name, options
):
    text = _refused(tools, input=points, **{"column": "value", **options})

    assert "Traceback" in text
    assert "v.univar -g map=up_1@PERMANENT" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.univar ends in a traceback when v.univar fails instead of a message",
)
@pytest.mark.parametrize(("name", "options"), FAILURES)
def test_a_failure_of_v_univar_is_reported_as_a_message(tools, points, name, options):
    text = _refused(tools, input=points, **{"column": "value", **options})

    assert "Traceback" not in text


def test_a_twhere_with_a_syntax_error_is_reported_as_a_message(tools, points):
    text = _refused(tools, input=points, column="value", twhere="nonsense =")

    assert "Traceback" not in text
    assert "Invalid twhere condition <nonsense =>" in text
    assert "syntax error" in text
