"""The cases of the earlier gunittest file unittests_temporal_raster_algebra_grs.py

The granularity mode of the raster algebra.

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

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 6, minmin 0, maxmax 5, start 2001-01-01, end 2001-07-01, topo True, gran 1 month
    pytest.param(
        "if(C == 9,  A - 1)",
        {"granularity": True},
        [
            ("2001-01-01", "2001-02-01", 0, 0),
            ("2001-02-01", "2001-03-01", 1, 1),
            ("2001-03-01", "2001-04-01", 2, 2),
            ("2001-04-01", "2001-05-01", 3, 3),
            ("2001-05-01", "2001-06-01", 4, 4),
            ("2001-06-01", "2001-07-01", 5, 5),
        ],
        id="1",
    ),
    # Old assertions: n 6, minmin 17, maxmax 23, start 2001-01-01, end 2001-07-01, topo True, gran 1 month
    pytest.param(
        "A + B + C",
        {"granularity": True},
        [
            ("2001-01-01", "2001-02-01", 17, 17),
            ("2001-02-01", "2001-03-01", 18, 18),
            ("2001-03-01", "2001-04-01", 19, 19),
            ("2001-04-01", "2001-05-01", 21, 21),
            ("2001-05-01", "2001-06-01", 22, 22),
            ("2001-06-01", "2001-07-01", 23, 23),
        ],
        id="2",
    ),
    # Old assertions: n 0, topo False
    pytest.param("A + B + C + tmap(nullmap)", {"granularity": True}, [], id="3"),
    # Old assertions: n 15, minmin 2, maxmax 6, start 2001-01-01, end 2001-05-06, topo True, gran 1 day
    pytest.param(
        "if(D == 11,  A - 1, A + 1)",
        {"granularity": True},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 2, 2),
            ("2001-01-04", "2001-01-05", 2, 2),
            ("2001-01-05", "2001-01-06", 2, 2),
            ("2001-03-01", "2001-03-02", 2, 2),
            ("2001-03-02", "2001-03-03", 2, 2),
            ("2001-03-03", "2001-03-04", 2, 2),
            ("2001-03-04", "2001-03-05", 2, 2),
            ("2001-03-05", "2001-03-06", 2, 2),
            ("2001-05-01", "2001-05-02", 6, 6),
            ("2001-05-02", "2001-05-03", 6, 6),
            ("2001-05-03", "2001-05-04", 6, 6),
            ("2001-05-04", "2001-05-05", 6, 6),
            ("2001-05-05", "2001-05-06", 6, 6),
        ],
        id="4",
    ),
    # Old assertions: n 6, minmin 2, maxmax 7, start 2001-01-01, end 2001-07-01
    pytest.param(
        "A + (A # A)",
        {},
        [
            ("2001-01-01", "2001-02-01", 2, 2),
            ("2001-02-01", "2001-03-01", 3, 3),
            ("2001-03-01", "2001-04-01", 4, 4),
            ("2001-04-01", "2001-05-01", 5, 5),
            ("2001-05-01", "2001-06-01", 6, 6),
            ("2001-06-01", "2001-07-01", 7, 7),
        ],
        id="simple arith hash 1",
    ),
    # Old assertions: n 6, minmin 1, maxmax 1, start 2001-01-01, end 2001-07-01
    pytest.param(
        "(A + A) # A",
        {},
        [
            ("2001-01-01", "2001-02-01", 1, 1),
            ("2001-02-01", "2001-03-01", 1, 1),
            ("2001-03-01", "2001-04-01", 1, 1),
            ("2001-04-01", "2001-05-01", 1, 1),
            ("2001-05-01", "2001-06-01", 1, 1),
            ("2001-06-01", "2001-07-01", 1, 1),
        ],
        id="simple arith hash 2",
    ),
    # Old assertions: n 15, minmin 2, maxmax 6, start 2001-01-01, end 2001-05-06, topo True, gran 1 day
    pytest.param(
        "A + td(A:D)",
        {"granularity": True},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 2, 2),
            ("2001-01-04", "2001-01-05", 2, 2),
            ("2001-01-05", "2001-01-06", 2, 2),
            ("2001-03-01", "2001-03-02", 4, 4),
            ("2001-03-02", "2001-03-03", 4, 4),
            ("2001-03-03", "2001-03-04", 4, 4),
            ("2001-03-04", "2001-03-05", 4, 4),
            ("2001-03-05", "2001-03-06", 4, 4),
            ("2001-05-01", "2001-05-02", 6, 6),
            ("2001-05-02", "2001-05-03", 6, 6),
            ("2001-05-03", "2001-05-04", 6, 6),
            ("2001-05-04", "2001-05-05", 6, 6),
            ("2001-05-05", "2001-05-06", 6, 6),
        ],
        id="simple arith td 1",
    ),
    # Old assertions: n 5, minmin 4, maxmax 12, start 2001-02-01, end 2001-07-01
    pytest.param(
        'if(start_date(A) >= "2001-02-01", A + A)',
        {"granularity": True},
        [
            ("2001-02-01", "2001-03-01", 4, 4),
            ("2001-03-01", "2001-04-01", 6, 6),
            ("2001-04-01", "2001-05-01", 8, 8),
            ("2001-05-01", "2001-06-01", 10, 10),
            ("2001-06-01", "2001-07-01", 12, 12),
        ],
        id="simple arith if 1",
    ),
    # Old assertions: n 6, minmin 0, maxmax 0, start 2001-01-01, end 2001-07-01
    pytest.param(
        "if(A#A == 1, A - A)",
        {"granularity": True},
        [
            ("2001-01-01", "2001-02-01", 0, 0),
            ("2001-02-01", "2001-03-01", 0, 0),
            ("2001-03-01", "2001-04-01", 0, 0),
            ("2001-04-01", "2001-05-01", 0, 0),
            ("2001-05-01", "2001-06-01", 0, 0),
            ("2001-06-01", "2001-07-01", 0, 0),
        ],
        id="simple arith if 2",
    ),
    # Old assertions: n 6, minmin -6, maxmax 11, start 2001-01-01, end 2001-07-01
    pytest.param(
        'if(start_date(A) < "2001-03-01" && A#A == 1, A+C, A-C)',
        {"granularity": True},
        [
            ("2001-01-01", "2001-02-01", 10, 10),
            ("2001-02-01", "2001-03-01", 11, 11),
            ("2001-03-01", "2001-04-01", -6, -6),
            ("2001-04-01", "2001-05-01", -5, -5),
            ("2001-05-01", "2001-06-01", -4, -4),
            ("2001-06-01", "2001-07-01", -3, -3),
        ],
        id="complex arith if 1",
    ),
    # Old assertions: n 14, minmin 2, maxmax 10, start 2001-01-02, end 2001-05-06
    pytest.param(
        "(A[0,0,-1] : D) + (A[0,0,1] : D)",
        {"granularity": True},
        [
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 2, 2),
            ("2001-01-04", "2001-01-05", 2, 2),
            ("2001-01-05", "2001-01-06", 2, 2),
            ("2001-03-01", "2001-03-02", 5, 5),
            ("2001-03-02", "2001-03-03", 6, 6),
            ("2001-03-03", "2001-03-04", 6, 6),
            ("2001-03-04", "2001-03-05", 6, 6),
            ("2001-03-05", "2001-03-06", 6, 6),
            ("2001-05-01", "2001-05-02", 9, 9),
            ("2001-05-02", "2001-05-03", 10, 10),
            ("2001-05-03", "2001-05-04", 10, 10),
            ("2001-05-04", "2001-05-05", 10, 10),
            ("2001-05-05", "2001-05-06", 10, 10),
        ],
        id="temporal neighbors",
    ),
    # Old assertions: n 6, minmin 100, maxmax 105, start 2001-01-01, end 2001-07-01
    pytest.param(
        "A + map(singletmap)",
        {"granularity": True},
        [
            ("2001-01-01", "2001-02-01", 100, 100),
            ("2001-02-01", "2001-03-01", 101, 101),
            ("2001-03-01", "2001-04-01", 102, 102),
            ("2001-04-01", "2001-05-01", 103, 103),
            ("2001-05-01", "2001-06-01", 104, 104),
            ("2001-06-01", "2001-07-01", 105, 105),
        ],
        id="map",
    ),
    # Old assertions: n 1, minmin 201, maxmax 201, start 2001-03-01, end 2001-04-01, topo True, gran 1 month
    pytest.param(
        "tmap(singletmap) + A + map(singletmap)",
        {"granularity": True},
        [("2001-03-01", "2001-04-01", 201, 201)],
        id="tmap map",
    ),
]

CORE = {}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    "A + B + C": (True, "1 month"),
    "A + B + C + tmap(nullmap)": (False, None),
    "A + td(A:D)": (True, "1 day"),
    "if(C == 9,  A - 1)": (True, "1 month"),
    "if(D == 11,  A - 1, A + 1)": (True, "1 day"),
    "tmap(singletmap) + A + map(singletmap)": (True, "1 month"),
}

SHAPE_CORE = {}

DRY = [
    pytest.param(
        "if(C == 9,  A - 1)",
        {"granularity": True},
        {
            "names": ["r.mapcalc", "r.mapcalc"],
            "processes": 6,
            "register": 6,
            "stdstype": "strds",
        },
        id="1 (dry run)",
    ),
    pytest.param(
        "A + B + C",
        {"granularity": True},
        {
            "names": ["r.mapcalc", "r.mapcalc"],
            "processes": 6,
            "register": 6,
            "stdstype": "strds",
        },
        id="2 (dry run)",
    ),
    pytest.param(
        "A + B + C + tmap(nullmap)",
        {"granularity": True},
        {"processes": 0, "register": 0, "stdstype": "strds"},
        id="3 (dry run)",
    ),
]


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.raster_granularity(tools)
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
    algebra_cases.check_dry(KIND, runner, expression, options, expected)


def test_every_table_entry_belongs_to_a_case():
    # The tables are looked up by expression or id; a key that matches no case
    # would be skipped without notice.
    ids = {case.id for case in CASES}
    assert set(SHAPE) <= {case.values[0] for case in CASES}
    assert set(CORE) <= ids
    assert set(NAMES) <= ids
    assert set(CORE_MESSAGE) <= set(CORE)
    assert set(SHAPE_CORE) <= set(CORE)
