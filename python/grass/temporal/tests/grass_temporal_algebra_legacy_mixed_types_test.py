"""The cases of the earlier gunittest file unittests_temporal_algebra_mixed_stds.py

Expressions that relate datasets of different types.

Every case runs in the earlier implementation (reference), in the classic
profile and in the new algebra (core). The expected maps are those the old
assertions describe (number of maps, extent, minimum, maximum, topology,
granularity); the comment of a case repeats them. CORE holds the cases where
the core calculates differently according to the manual ("Core and classic
algebra"); SHAPE what the old test asserted besides the maps. The
datasets are those of algebra_cases, see its builder for the data.
"""

import pytest

from grass.temporal.testing import algebra_cases
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

# What the classic profile and the core plan where they differ from the
# reference. Their run of this expression makes a str3ds, as the run of the
# reference does (test_mixed_runs_make_a_str3ds); their plan names that type,
# while the plan of the reference names the stdstype of the call, which the
# old test asserted. Decided 19.10.2026: the plan names what the run makes.
DRY_AS_RUN = {
    "different stds handling2 (dry run)": {"register": 2, "stdstype": "str3ds"},
}


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.mixed_types(tools)
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
    algebra_cases.check_case(
        KIND,
        runner,
        expression,
        options,
        expected,
        shape,
        message,
        NAMES.get(case_id(request)),
    )


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize(("expression", "options", "expected"), DRY)
def test_dry_runs(data, request, runner, expression, options, expected):
    if runner != "reference":
        expected = DRY_AS_RUN.get(case_id(request), expected)
    algebra_cases.check_dry(KIND, runner, expression, options, expected)


@pytest.mark.parametrize("runner", RUNNERS)
def test_mixed_runs_make_a_str3ds(data, runner):
    # The run of the planned expression: the type of its result is what the
    # plans of the classic profile and the core name (DRY_AS_RUN).
    algebra_cases.check_case(
        KIND,
        runner,
        "if({contains}, (stvds(C) {#,contains} str3ds(A)) == 2, str3ds(A))",
        {"result_type": "str3ds", "stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
    )


def test_every_table_entry_belongs_to_a_case():
    # The tables are looked up by expression or id; a key that matches no case
    # would be skipped without notice.
    ids = {case.id for case in CASES}
    assert set(SHAPE) <= {case.values[0] for case in CASES}
    assert set(CORE) <= ids
    assert set(NAMES) <= ids
    assert set(CORE_MESSAGE) <= set(CORE)
    assert set(SHAPE_CORE) <= set(CORE)
    assert set(DRY_AS_RUN) <= {case.id for case in DRY}
