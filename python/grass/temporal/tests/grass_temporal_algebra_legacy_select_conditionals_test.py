"""The cases of the earlier gunittest file unittests_temporal_conditionals.py

Conditional expressions of the select algebra.

Every case runs in the earlier implementation (reference), in the classic
profile and in the new algebra (core). The expected maps are those the old
assertions describe (number of maps, extent, minimum, maximum, topology,
granularity); the comment of a case repeats them. CORE holds the cases where
the core calculates differently according to the manual ("Core and classic
algebra"); SHAPE what the old test asserted besides the maps. The
datasets are those of legacy_data, see its builder for the data.
"""

import pytest

from grass.temporal.testing import legacy_data
from grass.tools import Tools

KIND = "select"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(start_date(A) >= "2001-01-03", A)',
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal condition 1",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(td(A) == 1, A)",
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal condition 2",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(td(A) == 1 || start_date(A) >= "2001-01-03", A)',
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal condition 3",
    ),
    # Old assertions: n 2, minmin 1, maxmax 2, start 2001-01-01, end 2001-01-03, topo True, gran 1 day
    pytest.param(
        "if(start_day(A) <= 2, A)",
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-02", 1, 1), ("2001-01-02", "2001-01-03", 2, 2)],
        id="temporal condition 5",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        'if(td(A) == 1 {||,during} start_date(C) < "2001-01-02", A)',
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal condition 6",
    ),
    # Old assertions: n 2, minmin 5, maxmax 6, start 2001-01-01, end 2001-01-05, topo True, gran 2 days
    pytest.param(
        'if({over},start_date(C) == "2001-01-02" {&&,contains} td(A) == 1, B)',
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-03", 5, 5), ("2001-01-03", "2001-01-05", 6, 6)],
        id="temporal condition 7",
    ),
    # Old assertions: n 2, minmin 5, maxmax 6, start 2001-01-01, end 2001-01-05, topo True, gran 2 days
    pytest.param(
        'if(start_date(B) <= "2001-01-01" {||,over,|} td(E) == 2, B)',
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-03", 5, 5), ("2001-01-03", "2001-01-05", 6, 6)],
        id="temporal condition 8",
    ),
    # Old assertions: n 1, minmin 5, maxmax 5, start 2001-01-01, end 2001-01-03, topo True, gran 2 days
    pytest.param(
        'if(start_date(B) <= "2001-01-01" {&&,over,&} td(E) == 2, B)',
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-03", 5, 5)],
        id="temporal condition 9",
    ),
    # Old assertions: n 3, minmin 11, maxmax 13, start 2000-12-31, end 2001-01-06, topo True, gran 2 days
    pytest.param(
        'if(start_date(B) <= "2001-01-01" {||,over,|,r} td(E) == 2, E)',
        {"stdstype": "strds"},
        [
            ("2000-12-31", "2001-01-02", 11, 11),
            ("2001-01-02", "2001-01-04", 12, 12),
            ("2001-01-04", "2001-01-06", 13, 13),
        ],
        id="temporal condition 10",
    ),
    # Old assertions: n 1, minmin 11, maxmax 11, start 2000-12-31, end 2001-01-02, topo True, gran 2 days
    pytest.param(
        'if(start_date(B) <= "2001-01-01" {&&,over,r} td(E) == 2, E)',
        {"stdstype": "strds"},
        [("2000-12-31", "2001-01-02", 11, 11)],
        id="temporal condition 11",
    ),
    # Old assertions: n 1, minmin 11, maxmax 11, start 2000-12-31, end 2001-01-02, topo True, gran 2 days
    pytest.param(
        'if(start_date(B) <= "2001-01-01" {&&,over,|,r} td(E) == 2, E)',
        {"stdstype": "strds"},
        [("2000-12-31", "2001-01-02", 11, 11)],
        id="temporal condition 12",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({equal|contains},td(B) == 2 {&&,contains} td(A) == 1, A)",
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal conditional 13",
    ),
    # Old assertions: n 4, minmin 1, maxmax 9, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(start_date(A) <= "2001-01-03", A, D)',
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 9, 9),
        ],
        id="temporal condition else 1",
    ),
    # Old assertions: n 2, minmin 4, maxmax 8, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(td(D) == 1 && start_date(A) >= "2001-01-04", A, D)',
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 8, 8), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal condition else 2",
    ),
    # Old assertions: n 3, minmin 8, maxmax 10, start 2001-01-03, end 2001-01-06, topo True, gran 1 day
    pytest.param(
        'if({contains},td(B) == 2 {&&,contains} start_date(D) >= "2001-01-04", A, D)',
        {"stdstype": "strds"},
        [
            ("2001-01-03", "2001-01-04", 8, 8),
            ("2001-01-04", "2001-01-05", 9, 9),
            ("2001-01-05", "2001-01-06", 10, 10),
        ],
        id="temporal condition else 3",
    ),
    # Old assertions: n 3, minmin 5, maxmax 11, start 2000-12-31, end 2001-01-05, topo False, gran 2 days
    pytest.param(
        'if({equal|over},start_date(B) <= "2001-01-01" {&&,over,|,r} td(E) == 2, E, B)',
        {"stdstype": "strds"},
        [
            ("2000-12-31", "2001-01-02", 11, 11),
            ("2001-01-01", "2001-01-03", 5, 5),
            ("2001-01-03", "2001-01-05", 6, 6),
        ],
        id="temporal condition else 4",
    ),
]

CORE = {}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    'if(start_date(A) <= "2001-01-03", A, D)': (True, "1 day"),
    'if(start_date(A) >= "2001-01-03", A)': (True, "1 day"),
    'if(start_date(B) <= "2001-01-01" {&&,over,&} td(E) == 2, B)': (True, "2 days"),
    'if(start_date(B) <= "2001-01-01" {&&,over,r} td(E) == 2, E)': (True, "2 days"),
    'if(start_date(B) <= "2001-01-01" {&&,over,|,r} td(E) == 2, E)': (True, "2 days"),
    'if(start_date(B) <= "2001-01-01" {||,over,|,r} td(E) == 2, E)': (True, "2 days"),
    'if(start_date(B) <= "2001-01-01" {||,over,|} td(E) == 2, B)': (True, "2 days"),
    "if(start_day(A) <= 2, A)": (True, "1 day"),
    'if(td(A) == 1 {||,during} start_date(C) < "2001-01-02", A)': (True, "1 day"),
    'if(td(A) == 1 || start_date(A) >= "2001-01-03", A)': (True, "1 day"),
    "if(td(A) == 1, A)": (True, "1 day"),
    'if(td(D) == 1 && start_date(A) >= "2001-01-04", A, D)': (True, "1 day"),
    'if({contains},td(B) == 2 {&&,contains} start_date(D) >= "2001-01-04", A, D)': (
        True,
        "1 day",
    ),
    "if({equal|contains},td(B) == 2 {&&,contains} td(A) == 1, A)": (True, "1 day"),
    'if({equal|over},start_date(B) <= "2001-01-01" {&&,over,|,r} td(E) == 2, E, B)': (
        False,
        "2 days",
    ),
    'if({over},start_date(C) == "2001-01-02" {&&,contains} td(A) == 1, B)': (
        True,
        "2 days",
    ),
}

SHAPE_CORE = {}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    legacy_data.conditionals(tools)
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


def test_every_table_entry_belongs_to_a_case():
    # The tables are looked up by expression or id; a key that matches no case
    # would be skipped without notice.
    ids = {case.id for case in CASES}
    assert set(SHAPE) <= {case.values[0] for case in CASES}
    assert set(CORE) <= ids
    assert set(NAMES) <= ids
    assert set(CORE_MESSAGE) <= set(CORE)
    assert set(SHAPE_CORE) <= set(CORE)
