"""The cases of the earlier gunittest file unittests_temporal_raster_conditionals.py

Conditional expressions of the raster algebra.

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

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 4, minmin 0, maxmax 5, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains}, B == 5,  A - 1,  A + 1)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 1, 1),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 5, 5),
        ],
        id="temporal conditional time dimension bug",
    ),
    # Old assertions: n 2, minmin 16, maxmax 18, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(td(A) == 1,  D * 2, D)",
        {},
        [("2001-01-03", "2001-01-04", 16, 16), ("2001-01-04", "2001-01-05", 18, 18)],
        id="temporal conditional 1",
    ),
    # Old assertions: n 4, minmin 4, maxmax 5, start 2001-01-01, end 2001-01-05, topo False, gran 2 days
    pytest.param(
        "if({during},exist(A),  B - 1,  B + 1)",
        {},
        [
            ("2001-01-01", "2001-01-03", 4, 4),
            ("2001-01-01", "2001-01-03", 4, 4),
            ("2001-01-03", "2001-01-05", 5, 5),
            ("2001-01-03", "2001-01-05", 5, 5),
        ],
        id="temporal conditional relation 1",
    ),
    # Old assertions: n 4, minmin 0, maxmax 3, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 1 && A < 4 && isntnull(A), A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 0, 0),
        ],
        id="spatial conditional 1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if(A > 1 && A < 4 && isntnull(A), A, null())",
        {},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="spatial conditional 2",
    ),
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 1, A, D)",
        {},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="spatial conditional 3",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 0, A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatial conditional 4",
    ),
    # Old assertions: n 2, minmin 0, maxmax 6, start 2001-01-01, end 2001-01-05, topo True, gran 2 days
    pytest.param(
        "if(B > 5 {&&,contains,l} A < 5, B)",
        {},
        [("2001-01-01", "2001-01-03", 0, 0), ("2001-01-03", "2001-01-05", 6, 6)],
        id="spatial conditional 5",
    ),
    # Old assertions: n 2, minmin 8, maxmax 9, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains},B > 5, D)",
        {},
        [("2001-01-03", "2001-01-04", 8, 8), ("2001-01-04", "2001-01-05", 9, 9)],
        id="spatial conditional relation 1",
    ),
    # Old assertions: n 4, minmin 1, maxmax 8, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains}, B <= 5, A, A * 2)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 6, 6),
            ("2001-01-04", "2001-01-05", 8, 8),
        ],
        id="spatial conditional relation 2",
    ),
    # Old assertions: n 4, minmin 3, maxmax 10, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains}, B > 5, A, 10)",
        {},
        [
            ("2001-01-01", "2001-01-02", 10, 10),
            ("2001-01-02", "2001-01-03", 10, 10),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatial conditional numeric relation 1",
    ),
    # Old assertions: n 4, minmin 0, maxmax 4.5, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains},B > 5, A + 2 / 4.0)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 3.5, 3.5),
            ("2001-01-04", "2001-01-05", 4.5, 4.5),
        ],
        id="spatial conditional numeric relation 2",
    ),
    # Old assertions: n 4, minmin 0, maxmax 2, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 2, 0, A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 0, 0),
            ("2001-01-04", "2001-01-05", 0, 0),
        ],
        id="spatial conditional numeric 1",
    ),
    # Old assertions: n 4, minmin 3, maxmax 8, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 2, A, 8)",
        {},
        [
            ("2001-01-01", "2001-01-02", 8, 8),
            ("2001-01-02", "2001-01-03", 8, 8),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatial conditional numeric 2",
    ),
    # Old assertions: n 4, minmin 0, maxmax 1, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A > 2, 1, 0)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 1, 1),
            ("2001-01-04", "2001-01-05", 1, 1),
        ],
        id="spatial conditional numeric 3",
    ),
    # Old assertions: n 2, minmin 0, maxmax 0, start 2001-01-01, end 2001-01-03, topo True, gran 1 day
    pytest.param(
        "if(A > 2, null())",
        {},
        [("2001-01-01", "2001-01-02", 0, 0), ("2001-01-02", "2001-01-03", 0, 0)],
        id="spatial conditional numeric 4",
    ),
    # Old assertions: n 4, minmin 0, maxmax 1, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(A < 2 && start_date(A) < "2001-01-03", A)',
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 0, 0),
            ("2001-01-04", "2001-01-05", 0, 0),
        ],
        id="spatiotemporal conditional 1",
    ),
    # Old assertions: n 4, minmin 2, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(A < 3 || start_date(A) < "2001-01-04", A + 1, A - 1)',
        {},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 3, 3),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 3, 3),
        ],
        id="spatiotemporal conditional 2",
    ),
    # Old assertions: n 2, minmin 0, maxmax 0, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if({contains},B > 5 && start_day(B) < 3, D)",
        {},
        [("2001-01-03", "2001-01-04", 0, 0), ("2001-01-04", "2001-01-05", 0, 0)],
        id="spatiotemporal conditional relation 1",
    ),
    # Old assertions: n 4, minmin 1, maxmax 8, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if({contains}, start_date(B) < "2001-01-03" || B <= 5, A, A * 2)',
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 6, 6),
            ("2001-01-04", "2001-01-05", 8, 8),
        ],
        id="spatiotemporal conditional relation 2",
    ),
    # Old assertions: n 4, minmin 3, maxmax 10, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if({contains}, start_date(B) >= "2001-01-03" && B > 5, A, 10)',
        {},
        [
            ("2001-01-01", "2001-01-02", 10, 10),
            ("2001-01-02", "2001-01-03", 10, 10),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatiotemporal conditional numeric relation 1",
    ),
    # Old assertions: n 4, minmin 0, maxmax 4.5, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if({contains},td(B) == 2 && start_date(B) == "2001-01-03" && B > 5 , A + 2 / 4.0)',
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 3.5, 3.5),
            ("2001-01-04", "2001-01-05", 4.5, 4.5),
        ],
        id="spatiotemporal conditional numeric relation 2",
    ),
    # Old assertions: n 4, minmin 0, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(start_date(A) < "2001-01-04" && A > 2, 0, A)',
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 0, 0),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatiotemporal conditional numeric 1",
    ),
    # Old assertions: n 4, minmin 2, maxmax 8, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(A > 2 || start_date(A) > "2001-01-01" && start_date(A) < "2001-01-04", A, 8)',
        {},
        [
            ("2001-01-01", "2001-01-02", 8, 8),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="spatiotemporal conditional numeric 2",
    ),
    # Old assertions: n 4, minmin 0, maxmax 1, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        'if(start_date(A) < "2001-01-04" && A > 2, 1, 0)',
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 1, 1),
            ("2001-01-04", "2001-01-05", 0, 0),
        ],
        id="spatiotemporal conditional numeric 3",
    ),
    # Old assertions: n 1, minmin 0, maxmax 0, start 2001-01-01, end 2001-01-02, topo True, gran 1 day
    pytest.param(
        'if(A > 2 || start_date(A) > "2001-01-01", null())',
        {},
        [("2001-01-01", "2001-01-02", 0, 0)],
        id="spatiotemporal conditional numeric 4",
    ),
]

CORE = {
    # Manual, Core and classic algebra, item 1: one result per conclusion map;
    # the classic algebra gives one result for each pair of condition map and
    # conclusion map
    "temporal conditional relation 1": [
        ("2001-01-01", "2001-01-03", 4, 4),
        ("2001-01-03", "2001-01-05", 5, 5),
    ],
    # Manual, Core and classic algebra, item 2: then and else need equal time
    # stamps; the core stops with an error, the classic algebra leaves out the
    # other maps
    "spatial conditional 3": "Other:ValueError",
}

CORE_MESSAGE = {"spatial conditional 3": "equal\\ time\\ stamps"}

NAMES = {}

SHAPE = {
    'if(A < 2 && start_date(A) < "2001-01-03", A)': (True, "1 day"),
    'if(A < 3 || start_date(A) < "2001-01-04", A + 1, A - 1)': (True, "1 day"),
    "if(A > 0, A)": (True, "1 day"),
    "if(A > 1 && A < 4 && isntnull(A), A)": (True, "1 day"),
    "if(A > 1 && A < 4 && isntnull(A), A, null())": (True, "1 day"),
    "if(A > 1, A, D)": (True, "1 day"),
    'if(A > 2 || start_date(A) > "2001-01-01" && start_date(A) < "2001-01-04", A, 8)': (
        True,
        "1 day",
    ),
    'if(A > 2 || start_date(A) > "2001-01-01", null())': (True, "1 day"),
    "if(A > 2, 0, A)": (True, "1 day"),
    "if(A > 2, 1, 0)": (True, "1 day"),
    "if(A > 2, A, 8)": (True, "1 day"),
    "if(A > 2, null())": (True, "1 day"),
    "if(B > 5 {&&,contains,l} A < 5, B)": (True, "2 days"),
    'if(start_date(A) < "2001-01-04" && A > 2, 0, A)': (True, "1 day"),
    'if(start_date(A) < "2001-01-04" && A > 2, 1, 0)': (True, "1 day"),
    "if(td(A) == 1,  D * 2, D)": (True, "1 day"),
    "if({contains}, B <= 5, A, A * 2)": (True, "1 day"),
    "if({contains}, B == 5,  A - 1,  A + 1)": (True, "1 day"),
    "if({contains}, B > 5, A, 10)": (True, "1 day"),
    'if({contains}, start_date(B) < "2001-01-03" || B <= 5, A, A * 2)': (True, "1 day"),
    'if({contains}, start_date(B) >= "2001-01-03" && B > 5, A, 10)': (True, "1 day"),
    "if({contains},B > 5 && start_day(B) < 3, D)": (True, "1 day"),
    "if({contains},B > 5, A + 2 / 4.0)": (True, "1 day"),
    "if({contains},B > 5, D)": (True, "1 day"),
    'if({contains},td(B) == 2 && start_date(B) == "2001-01-03" && B > 5 , A + 2 / 4.0)': (
        True,
        "1 day",
    ),
    "if({during},exist(A),  B - 1,  B + 1)": (False, "2 days"),
}

SHAPE_CORE = {"temporal conditional relation 1": (True, "2 days")}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.raster_conditionals(tools)
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
