"""The selection of the paper that mixes dataset types

Gebbert, Leppelt and Pebesma (2019) select the maps of a 3D raster time
series that are during the maps of a vector time series. The paper prints the
function names in capitals, STR3DS(A) and STVDS(B); the functions are written
in lower case and exist in the classic algebra only, so the selection needs
-c. The datasets are those of conftest.py: A of type str3ds and B of type
stvds, whose maps stand in the relations listed there.
"""

import pytest

from grass.temporal.testing import expressions
from grass.temporal.testing.expressions import RUNNERS, compare, outcome
from grass.tools import ToolError, Tools

PRINTED = "STR3DS(A) {:,during,l} STVDS(B)"
LOWER_CASE = "str3ds(A) {:,during,l} stvds(B)"


@pytest.fixture
def str3ds_result(monkeypatch):
    """Read the result of a selection as a dataset of type str3ds"""
    monkeypatch.setitem(expressions.STDS_TYPES, "select", "str3ds")


def run(runner, expression, basename):
    return outcome(
        "select",
        expression,
        RUNNERS[runner],
        basename=basename,
        stdstype="str3ds",
        register_null=True,
    )


def test_the_profile_selects_what_the_reference_selects(series, str3ds_result):
    reference = run("reference", LOWER_CASE, "fa")
    profile = run("classic", LOWER_CASE, "fb")
    assert compare("select", LOWER_CASE, reference, profile) is None
    # By hand from the table in conftest.py: during includes starts and
    # finishes, so a1 (starts b8) and a2 (finishes b8) are selected; a3
    # contains b2 and b9 and a4 contains b5, they are not during any map.
    assert "error" not in reference
    assert [row[1:3] for row in reference["maps"]] == [
        ["2001-01-01T00:00:00", "2001-01-11T00:00:00"],
        ["2001-01-11T00:00:00", "2001-01-21T00:00:00"],
    ]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_function_names_in_capitals_are_refused(series, str3ds_result, runner):
    assert run(runner, PRINTED, "fa")["error"] == "SyntaxError"


def test_the_tool_selects_with_the_classic_flag(series):
    """-c takes precedence over the variable of the fixture algebra"""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds", flags="c")
    listing = tools.t_rast3d_list(input="published", columns="name", format="json")
    assert listing["data"]


def test_the_core_does_not_know_the_functions(series, algebra):
    """Observed 2026-10-17: the new algebra reports unknown functions"""
    if algebra != "core":
        pytest.skip("the classic setting reads the functions")
    tools = Tools(session=series.session, overwrite=True)
    with pytest.raises(ToolError, match="Unknown function"):
        tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds")
