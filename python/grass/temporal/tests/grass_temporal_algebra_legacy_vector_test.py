"""The cases of the earlier gunittest file unittests_temporal_vector_algebra.py

Every case runs in the reference implementation (grass.temporal.classic), in
the classic profile and in the core. The expected maps are those the old
assertions describe (number of maps, extent, minimum, maximum, topology,
granularity); the comment of a case repeats them. CORE holds the cases where
the core calculates differently according to the manual ("Core and classic
algebra"); SHAPE what the old test asserted besides the maps. The datasets
are those of algebra_cases, see its builder for the data.
"""

import pytest

from grass.temporal.testing import algebra_cases
from grass.tools import Tools

KIND = "vector"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 4, points 80, areas 0, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A : A",
        {},
        [
            ("2001-01-01", "2001-01-02", 20, 0, 0),
            ("2001-01-02", "2001-01-03", 20, 0, 0),
            ("2001-01-03", "2001-01-04", 20, 0, 0),
            ("2001-01-04", "2001-01-05", 20, 0, 0),
        ],
        id="temporal select",
    ),
    # Old assertions: n 2, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,during,r} C",
        {},
        [
            ("2001-01-02", "2001-01-04", 20, 0, 0),
            ("2001-01-02", "2001-01-04", 20, 0, 0),
        ],
        id="temporal extent1",
    ),
    # Old assertions: n 2, points 40, areas 0, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A {:,during} C",
        {},
        [
            ("2001-01-02", "2001-01-03", 20, 0, 0),
            ("2001-01-03", "2001-01-04", 20, 0, 0),
        ],
        id="temporal select operators",
    ),
    # Old assertions: n 4, points 0, areas 80, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "buff_p(A,0.5)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0, 20),
            ("2001-01-02", "2001-01-03", 0, 0, 20),
            ("2001-01-03", "2001-01-04", 0, 0, 20),
            ("2001-01-04", "2001-01-05", 0, 0, 20),
        ],
        id="temporal buff operators 1",
    ),
    # Old assertions: n 4, points 0, areas 20, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "buff_a(buff_p(A,1),10)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0, 5),
            ("2001-01-02", "2001-01-03", 0, 0, 5),
            ("2001-01-03", "2001-01-04", 0, 0, 5),
            ("2001-01-04", "2001-01-05", 0, 0, 5),
        ],
        id="temporal buff operators 2",
    ),
    # Old assertions: n 2, points 0, areas 6, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "buff_p(A,2) & buff_p(D,2)",
        {},
        [("2001-01-03", "2001-01-04", 0, 0, 3), ("2001-01-04", "2001-01-05", 0, 0, 3)],
        id="temporal overlay operators 1",
    ),
    # Old assertions: n 4, points 0, areas 8, start 2001-01-01, end 2001-01-05, topo False, gran 2 days
    pytest.param(
        "buff_p(A,1.5) {&,during,r} buff_p(B,1.5)",
        {},
        [
            ("2001-01-01", "2001-01-03", 0, 0, 2),
            ("2001-01-01", "2001-01-03", 0, 0, 2),
            ("2001-01-03", "2001-01-05", 0, 0, 2),
            ("2001-01-03", "2001-01-05", 0, 0, 2),
        ],
        id="temporal overlay operators 2",
    ),
    # Old assertions: n 2, points 0, areas 8, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "buff_p(A,2.5) {&,during,l} buff_p(C,2.5)",
        {},
        [("2001-01-02", "2001-01-03", 0, 0, 4), ("2001-01-03", "2001-01-04", 0, 0, 4)],
        id="temporal overlay operators 3",
    ),
]

CORE = {}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    "A : A": (True, "1 day"),
    "A {:,during,r} C": (False, "2 days"),
    "A {:,during} C": (True, "1 day"),
    "buff_a(buff_p(A,1),10)": (True, "1 day"),
    "buff_p(A,0.5)": (True, "1 day"),
    "buff_p(A,1.5) {&,during,r} buff_p(B,1.5)": (False, "2 days"),
    "buff_p(A,2) & buff_p(D,2)": (True, "1 day"),
    "buff_p(A,2.5) {&,during,l} buff_p(C,2.5)": (True, "1 day"),
}

SHAPE_CORE = {}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.vector_algebra(tools)
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


def test_every_table_entry_belongs_to_a_case():
    # The tables are looked up by expression or id; a key that matches no case
    # would be skipped without notice.
    ids = {case.id for case in CASES}
    assert set(SHAPE) <= {case.values[0] for case in CASES}
    assert set(CORE) <= ids
    assert set(NAMES) <= ids
    assert set(CORE_MESSAGE) <= set(CORE)
    assert set(SHAPE_CORE) <= set(CORE)
