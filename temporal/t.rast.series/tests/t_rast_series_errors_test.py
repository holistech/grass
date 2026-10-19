"""Test the refusals and the empty cases of t.rast.series"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(**options)
    return message(error.value)


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="ser_missing", method="sum", output=f"{prefix}_o")

    assert "Space time dataset <ser_missing> of type <strds> not found" in text


@pytest.mark.parametrize("missing", ["input", "output"])
def test_a_required_option_is_checked_by_the_parser(tools, stats, prefix, missing):
    options = {"input": stats, "output": f"{prefix}_o", "method": "sum"}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


@pytest.mark.parametrize(
    ("option", "value", "text"),
    [
        ("method", "bogus", "Value <bogus> out of range for parameter <method>"),
        ("order", "bogus", "Value <bogus> out of range for parameter <order>"),
        ("file_limit", "abc", "Invalid value <abc> for parameter <file_limit>"),
    ],
)
def test_a_wrong_value_is_refused_by_the_parser(
    tools, stats, prefix, option, value, text
):
    options = {"input": stats, "output": f"{prefix}_o", "method": "sum"}
    options[option] = value

    assert text in _refused(tools, **options)


@pytest.mark.parametrize("outputs", ["a", "a,b,c"])
def test_methods_and_outputs_must_match(tools, stats, prefix, outputs):
    names = ",".join(f"{prefix}_{name}" for name in outputs.split(","))

    assert "Number requested methods and output maps do not match." in _refused(
        tools, input=stats, method="sum,maximum", output=names
    )


def test_today_a_wrong_where_ends_with_a_traceback(tools, stats, prefix):
    text = _refused(tools, input=stats, method="sum", output=f"{prefix}_o", where="x >")

    assert "Unable to execute" in text
    assert "Traceback" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.series ends in a traceback for a wrong where instead of a message",
)
def test_a_wrong_where_is_refused_with_a_message(tools, stats, prefix):
    text = _refused(tools, input=stats, method="sum", output=f"{prefix}_o", where="x >")

    assert "Traceback" not in text


def test_a_where_that_selects_nothing_makes_no_map(tools, stats, prefix):
    # No error and no output: the tool does nothing when no map is selected.
    result = tools.t_rast_series(
        input=stats,
        method="sum",
        output=f"{prefix}_o",
        where="start_time > '2010-01-01'",
    )

    assert result.returncode == 0
    assert tools.g_list(type="raster", pattern=f"{prefix}_o").stdout.strip() == ""
