"""The selection of the paper that mixes dataset types

Gebbert, Leppelt and Pebesma (2019) select the maps of a 3D raster time
series that are during the maps of a vector time series. The paper prints the
function names in capitals, STR3DS(A) and STVDS(B); both algebras read the
functions. Capitals are accepted for these three names, and only before an
opening parenthesis. The datasets are
those of conftest.py: A of type str3ds and B of type stvds, whose maps stand
in the relations listed there.
"""

import pytest

from grass.temporal.testing import expressions
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.expressions import RUNNERS, compare, outcome
from grass.tools import Tools

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
    reference = reference_outcome(
        "select", LOWER_CASE, stdstype="str3ds", register_null=True
    )
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
def test_the_function_names_in_capitals_select_like_lower_case(
    series, str3ds_result, runner
):
    printed = run(runner, PRINTED, "fa")
    lower = run(runner, LOWER_CASE, "fb")
    assert compare("select", PRINTED, printed, lower) is None
    # The same maps as in the test above: a1 and a2.
    assert "error" not in printed
    assert [row[1:3] for row in printed["maps"]] == [
        ["2001-01-01T00:00:00", "2001-01-11T00:00:00"],
        ["2001-01-11T00:00:00", "2001-01-21T00:00:00"],
    ]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(
    "expression",
    [
        "Str3ds(A) {:,during,l} stvds(B)",
        "STR3ds(A) {:,during,l} stvds(B)",
        "str3ds(A) {:,during,l} STVDs(B)",
    ],
)
def test_other_capital_spellings_are_refused(series, str3ds_result, runner, expression):
    assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_a_dataset_named_like_a_capital_function_stays_a_name(
    series, str3ds_result, runner
):
    """Without a parenthesis after it, STVDS is a dataset name

    No dataset of that name exists here, so the selection stops where the
    dataset is looked up. The lower case stvds in the same place is a
    syntax error.
    """
    result = run(runner, "A {:,during,l} STVDS", "fa")
    assert result["error"] == "FatalError"
    assert "not found" in result["msg"]


def test_the_tool_selects_with_the_classic_flag(series):
    """-c takes precedence over the variable of the fixture algebra"""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds", flags="c")
    listing = tools.t_rast3d_list(input="published", columns="name", format="json")
    assert listing["data"]


def test_the_tool_selects_with_the_functions_in_both_algebras(series, algebra):
    """Observed 2026-10-17: the new algebra read no dataset type function
    before; both algebras select the maps a1 and a2 now"""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds")
    listing = tools.t_rast3d_list(input="published", columns="name", format="json")
    assert len(listing["data"]) == 2
