"""The cases of the earlier gunittest file unittests_temporal_algebra_mixed_stds.py

Expressions that relate datasets of different types.

Every case runs in the earlier implementation (reference), in the classic
profile and in the new algebra (core). The expected maps are those the old
assertions describe (number of maps, extent, minimum, maximum, topology,
granularity); the comment of a case repeats them. CORE holds the cases where
the core calculates differently according to the manual ("Core and classic
algebra"); SHAPE what the old test asserted besides the maps. The
datasets are those of legacy_data, see its builder for the data.
"""

import re

import pytest

from grass.temporal.testing import legacy_data
from grass.tools import Tools

KIND = "select"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A {:,during} stvds(C)",
        {"stdstype": "str3ds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal select operators1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A {:,equal|during} stvds(C)",
        {"stdstype": "str3ds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal select operators2",
    ),
    # Old assertions: n 2, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A {!:,during} stvds(C)",
        {"stdstype": "str3ds"},
        [("2001-01-01", "2001-01-02", 1, 1), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal select operators3",
    ),
    # Old assertions: n 1, start 2001-01-02, end 2001-01-04, topo True, gran 2 days
    pytest.param(
        "C {:,contains} str3ds(A)",
        {"stdstype": "stvds"},
        [("2001-01-02", "2001-01-04", 20, 0, 0)],
        id="temporal select operators4",
    ),
    # Old assertions: n 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A {:,during} strds(B)",
        {"stdstype": "str3ds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal select operators5",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if(A {#,during} stvds(C) == 1, A)",
        {"stdstype": "str3ds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal hash operator1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if({contains}, stvds(C) {#,contains} A == 2, A)",
        {"stdstype": "str3ds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal hash operator2",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if({contains}, stvds(C) {#,contains} str3ds(A) == 2, str3ds(A))",
        {"result_type": "str3ds", "stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="different stds handling1",
    ),
]

CORE = {}

CORE_MESSAGE = {}

# Cases where the core refuses what the manual promises: t.select.md says that
# both algebras pull maps of another dataset type into a selection with
# strds(), str3ds() and stvds(). The core relates a 3D raster series on the left
# to a vector series ("temporal hash operator1") but not a vector series on
# the left to a raster series. The first table holds what the core does
# today, the case itself what is right.
CORE_TODAY = {
    "different stds handling1": "Other:ValueError",
    "temporal hash operator2": "Other:ValueError",
}

CORE_TODAY_MESSAGE = {
    "different stds handling1": "A\\ raster\\#d\\ series\\ cannot\\ be\\ related\\ to\\ a\\ vector\\ series",
    "temporal hash operator2": "A\\ raster\\#d\\ series\\ cannot\\ be\\ related\\ to\\ a\\ vector\\ series",
}

NAMES = {}

SHAPE = {
    "A {!:,during} stvds(C)": (True, "1 day"),
    "A {:,during} strds(B)": (True, "1 day"),
    "A {:,during} stvds(C)": (True, "1 day"),
    "A {:,equal|during} stvds(C)": (True, "1 day"),
    "C {:,contains} str3ds(A)": (True, "2 days"),
    "if(A {#,during} stvds(C) == 1, A)": (True, "1 day"),
    "if({contains}, stvds(C) {#,contains} A == 2, A)": (True, "1 day"),
    "if({contains}, stvds(C) {#,contains} str3ds(A) == 2, str3ds(A))": (True, "1 day"),
}

SHAPE_CORE = {}

DRY = [
    pytest.param(
        "A {:,during} stvds(C)",
        {"stdstype": "str3ds"},
        {"register": 2, "stdstype": "str3ds"},
        id="temporal select operators1 (dry run)",
    ),
    pytest.param(
        "A {:,equal|during} stvds(C)",
        {"stdstype": "str3ds"},
        {"register": 2, "stdstype": "str3ds"},
        id="temporal select operators2 (dry run)",
    ),
    pytest.param(
        "if({contains}, (stvds(C) {#,contains} str3ds(A)) == 2, str3ds(A))",
        {"stdstype": "strds"},
        {"register": 2, "stdstype": "strds"},
        id="different stds handling2 (dry run)",
    ),
]

DRY_SHOULD = [
    pytest.param(
        "if({contains}, (stvds(C) {#,contains} str3ds(A)) == 2, str3ds(A))",
        {"stdstype": "strds"},
        {"register": 2, "stdstype": "str3ds"},
        "core",
        id="different stds handling2 (dry run)-core",
    ),
]

# What the classic profile plans where it differs from the reference. Its run
# of this expression makes a str3ds, as the run of the reference does
# (test_mixed_runs_make_a_str3ds); its plan names that type, while the plan
# of the reference names the stdstype of the call, which the old test
# asserted. Decided 19.10.2026: the plan names what the run makes.
DRY_CLASSIC = {
    "different stds handling2 (dry run)": {"register": 2, "stdstype": "str3ds"},
}

# What a runner does today where it should plan what its run makes, as the
# classic profile does (DRY_CLASSIC): the core stops as in the cases above.
DRY_TODAY = {
    ("different stds handling2 (dry run)", "core"): (
        "ValueError",
        "A raster3d series cannot be related to a vector series",
    ),
}


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    legacy_data.mixed_types(tools)
    return temporal_module_session


def case_id(request):
    # The last part of the id is the runner.
    return request.node.callspec.id.rsplit("-", 1)[0]


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize(("expression", "options", "expected"), CASES)
def test_cases(data, request, runner, expression, options, expected):
    shape = SHAPE.get(expression)
    message = None
    if runner == "core":
        name = case_id(request)
        if name in CORE:
            expected = CORE[name]
            message = CORE_MESSAGE.get(name)
            shape = SHAPE_CORE.get(name, shape)
        elif name in CORE_TODAY:
            expected = CORE_TODAY[name]
            message = CORE_TODAY_MESSAGE.get(name)
            shape = None
    legacy_data.check_case(
        KIND,
        runner,
        expression,
        options,
        expected,
        shape,
        message,
        NAMES.get(case_id(request)),
    )


@pytest.mark.xfail(
    strict=True,
    reason="the core refuses expressions that relate datasets of different types, which the earlier algebra and t.select.md allow",
)
@pytest.mark.parametrize(
    ("expression", "options", "expected"), [c for c in CASES if c.id in CORE_TODAY]
)
def test_cases_the_core_should_run(data, expression, options, expected):
    legacy_data.check_case(
        KIND, "core", expression, options, expected, SHAPE.get(expression)
    )


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize(("expression", "options", "expected"), DRY)
def test_dry_runs(data, request, runner, expression, options, expected):
    name = case_id(request)
    today = DRY_TODAY.get((name, runner))
    if today is not None:
        with pytest.raises(ValueError, match=re.escape(today[1])):
            legacy_data.check_dry(KIND, runner, expression, options, expected)
        return
    if runner == "classic":
        expected = DRY_CLASSIC.get(name, expected)
    legacy_data.check_dry(KIND, runner, expression, options, expected)


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_mixed_runs_make_a_str3ds(data, runner):
    # The run of the planned expression: the type of its result is what the
    # plan of the classic profile names (DRY_CLASSIC).
    legacy_data.check_case(
        KIND,
        runner,
        "if({contains}, (stvds(C) {#,contains} str3ds(A)) == 2, str3ds(A))",
        {"result_type": "str3ds", "stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
    )


@pytest.mark.xfail(
    strict=True,
    reason="the core refuses the mixed expression, where it should plan the str3ds that the run makes",
)
@pytest.mark.parametrize(("expression", "options", "expected", "runner"), DRY_SHOULD)
def test_dry_runs_the_runners_should_plan(data, runner, expression, options, expected):
    legacy_data.check_dry(KIND, runner, expression, options, expected)


def test_every_table_entry_belongs_to_a_case():
    # The tables are looked up by expression or id; a key that matches no case
    # would be skipped without notice.
    ids = {case.id for case in CASES}
    assert set(SHAPE) <= {case.values[0] for case in CASES}
    assert set(CORE) <= ids
    assert set(NAMES) <= ids
    assert set(CORE_TODAY) <= ids
    assert set(CORE_MESSAGE) <= set(CORE)
    assert set(CORE_TODAY_MESSAGE) <= set(CORE_TODAY)
    assert set(SHAPE_CORE) <= set(CORE)
    assert {name for name, _ in DRY_TODAY} <= {case.id for case in DRY}
    assert set(DRY_CLASSIC) <= {case.id for case in DRY}
