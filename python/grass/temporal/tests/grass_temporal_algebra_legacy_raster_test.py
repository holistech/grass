"""The cases of the earlier gunittest file unittests_temporal_raster_algebra.py

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

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,during,r} C",
        {},
        [("2001-01-02", "2001-01-04", 2, 2), ("2001-01-02", "2001-01-04", 3, 3)],
        id="temporal extent1",
    ),
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
    # Old assertions: n 4, minmin 2, maxmax 5, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A + (A {#, equal,l} A)",
        {"time_suffix": "gran"},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 3, 3),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 5, 5),
        ],
        id="simple arith hash 1",
    ),
    # Old assertions: n 4, minmin 2, maxmax 5, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A + td(A)",
        {"time_suffix": "time"},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 3, 3),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 5, 5),
        ],
        id="simple arith td 1",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A / td(A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="simple arith td 2",
    ),
    # Old assertions: n 4, minmin 2, maxmax 5, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A {+,equal} td(A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 3, 3),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 5, 5),
        ],
        id="simple arith td 3",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A {/, equal} td(A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="simple arith td 4",
    ),
    # Old assertions: n 3, minmin 4, maxmax 8, start 2001-01-02, end 2001-01-05
    pytest.param(
        'if({equal}, start_date(A) >= "2001-01-02", A + A)',
        {},
        [
            ("2001-01-02", "2001-01-03", 4, 4),
            ("2001-01-03", "2001-01-04", 6, 6),
            ("2001-01-04", "2001-01-05", 8, 8),
        ],
        id="simple arith if 1",
    ),
    # Old assertions: n 4, minmin 0, maxmax 0, start 2001-01-01, end 2001-01-05
    pytest.param(
        "if({equal}, A#A == 1, A - A)",
        {},
        [
            ("2001-01-01", "2001-01-02", 0, 0),
            ("2001-01-02", "2001-01-03", 0, 0),
            ("2001-01-03", "2001-01-04", 0, 0),
            ("2001-01-04", "2001-01-05", 0, 0),
        ],
        id="simple arith if 2",
    ),
    # Old assertions: n 2, minmin 9, maxmax 10, start 2001-01-02, end 2001-01-04
    pytest.param(
        'if(start_date(A) < "2001-01-03" && A#A == 1, A{+, starts,l}C, A{+, finishes,l}C)',
        {},
        [("2001-01-02", "2001-01-03", 9, 9), ("2001-01-03", "2001-01-04", 10, 10)],
        id="complex arith if 1",
    ),
    # Old assertions: n 4, minmin 2, maxmax 20, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A {*, equal} A {+, equal} A",
        {},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 6, 6),
            ("2001-01-03", "2001-01-04", 12, 12),
            ("2001-01-04", "2001-01-05", 20, 20),
        ],
        id="simple arith 1",
    ),
    # Old assertions: n 0
    pytest.param("A {*, during} A {+, during} A", {}, [], id="simple arith 2"),
    # Old assertions: n 4, minmin 2, maxmax 5, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A / A + A*A/A",
        {},
        [
            ("2001-01-01", "2001-01-02", 2, 2),
            ("2001-01-02", "2001-01-03", 3, 3),
            ("2001-01-03", "2001-01-04", 4, 4),
            ("2001-01-04", "2001-01-05", 5, 5),
        ],
        id="simple arith 3",
    ),
    # Old assertions: n 0
    pytest.param("A {+,equal,i} B", {}, [], id="temporal intersection 1"),
    # Old assertions: n 4, minmin 6, maxmax 10, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A {+,during,i} B",
        {},
        [
            ("2001-01-01", "2001-01-02", 6, 6),
            ("2001-01-02", "2001-01-03", 7, 7),
            ("2001-01-03", "2001-01-04", 9, 9),
            ("2001-01-04", "2001-01-05", 10, 10),
        ],
        id="temporal intersection 2",
    ),
    # Old assertions: n 2, minmin 6, maxmax 9, start 2001-01-01, end 2001-01-04
    pytest.param(
        "A {+,starts,i} B",
        {},
        [("2001-01-01", "2001-01-02", 6, 6), ("2001-01-03", "2001-01-04", 9, 9)],
        id="temporal intersection 3",
    ),
    # Old assertions: n 2, minmin 7, maxmax 10, start 2001-01-02, end 2001-01-05
    pytest.param(
        "A {+,finishes,intersect} B",
        {},
        [("2001-01-02", "2001-01-03", 7, 7), ("2001-01-04", "2001-01-05", 10, 10)],
        id="temporal intersection 4",
    ),
    # Old assertions: n 4, minmin 6, maxmax 10, start 2001-01-01, end 2001-01-05
    pytest.param(
        "A {+,starts|finishes,i} B",
        {},
        [
            ("2001-01-01", "2001-01-02", 6, 6),
            ("2001-01-02", "2001-01-03", 7, 7),
            ("2001-01-03", "2001-01-04", 9, 9),
            ("2001-01-04", "2001-01-05", 10, 10),
        ],
        id="temporal intersection 5",
    ),
    # Old assertions: n 1, minmin 12, maxmax 12, start 2001-01-01, end 2001-01-04
    pytest.param(
        "B {+,overlaps,u} C",
        {},
        [("2001-01-01", "2001-01-04", 12, 12)],
        id="temporal intersection 6",
    ),
    # Old assertions: n 1, minmin 13, maxmax 13, start 2001-01-02, end 2001-01-05
    pytest.param(
        "B {+,overlapped,u} C",
        {},
        [("2001-01-02", "2001-01-05", 13, 13)],
        id="temporal intersection 7",
    ),
    # Old assertions: n 4, minmin 8, maxmax 11, start 2001-01-01, end 2001-01-05
    pytest.param(
        'A {+,during,l} buff_t(C, "1 day")',
        {},
        [
            ("2001-01-01", "2001-01-02", 8, 8),
            ("2001-01-02", "2001-01-03", 9, 9),
            ("2001-01-03", "2001-01-04", 10, 10),
            ("2001-01-04", "2001-01-05", 11, 11),
        ],
        id="temporal intersection 8",
    ),
    # Old assertions: n 2, minmin 4, maxmax 6, start 2001-01-02, end 2001-01-04
    pytest.param(
        "A[-1] + A[1]",
        {},
        [("2001-01-02", "2001-01-03", 4, 4), ("2001-01-03", "2001-01-04", 6, 6)],
        id="temporal neighbors 1",
    ),
    # Old assertions: n 2, minmin 4, maxmax 6, start 2001-01-02, end 2001-01-04
    pytest.param(
        "A[0,0,-1] + A[0,0,1]",
        {},
        [("2001-01-02", "2001-01-03", 4, 4), ("2001-01-03", "2001-01-04", 6, 6)],
        id="temporal neighbors 2",
    ),
    # Old assertions: n 1, minmin 99, maxmax 99, start 2001-01-03, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "tmap(singletmap)",
        {},
        [("2001-01-03", "2001-01-04", 99, 99)],
        id="tmap function1",
    ),
    # Old assertions: n 1, minmin 100, maxmax 100, start 2001-01-03, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "tmap(singletmap) + 1",
        {},
        [("2001-01-03", "2001-01-04", 100, 100)],
        id="tmap function2",
    ),
    # Old assertions: n 4, minmin 101, maxmax 104, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "map(singlemap) + A",
        {},
        [
            ("2001-01-01", "2001-01-02", 101, 101),
            ("2001-01-02", "2001-01-03", 102, 102),
            ("2001-01-03", "2001-01-04", 103, 103),
            ("2001-01-04", "2001-01-05", 104, 104),
        ],
        id="map function1",
    ),
    # Old assertions: n 4, minmin 100, maxmax 400, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A * map(singlemap)",
        {},
        [
            ("2001-01-01", "2001-01-02", 100, 100),
            ("2001-01-02", "2001-01-03", 200, 200),
            ("2001-01-03", "2001-01-04", 300, 300),
            ("2001-01-04", "2001-01-05", 400, 400),
        ],
        id="map function2",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A : A",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal select same left right",
    ),
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A : D",
        {},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal select",
    ),
    # Old assertions: n 2, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A {!:,during} C",
        {},
        [("2001-01-01", "2001-01-02", 1, 1), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal select operators2",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo False, gran 2 days
    pytest.param(
        "A {:,during,d} B",
        {},
        [
            ("2001-01-01", "2001-01-03", 1, 1),
            ("2001-01-01", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-05", 3, 3),
            ("2001-01-03", "2001-01-05", 4, 4),
        ],
        id="temporal select operators3",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,equal|during,r} C",
        {},
        [("2001-01-02", "2001-01-04", 2, 2), ("2001-01-02", "2001-01-04", 3, 3)],
        id="temporal select operators4",
    ),
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A # D == 1, A)",
        {},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal hash operator1",
    ),
    # Old assertions: n 2, minmin 1, maxmax 1, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A # D",
        {},
        [("2001-01-03", "2001-01-04", 1, 1), ("2001-01-04", "2001-01-05", 1, 1)],
        id="temporal hash operator2",
    ),
    # Old assertions: n 1, minmin 2, maxmax 2, start 2001-01-02, end 2001-01-04, topo True, gran 2 days
    pytest.param(
        "C {#,contains} A",
        {},
        [("2001-01-02", "2001-01-04", 2, 2)],
        id="temporal hash operator3",
    ),
    # Old assertions: n 1, minmin 2, maxmax 2, start 2001-01-02, end 2001-01-04, topo True, gran 2 days
    pytest.param(
        "if({during},A # D == 1, C {#,contains} A)",
        {},
        [("2001-01-02", "2001-01-04", 2, 2)],
        id="temporal hash operator4",
    ),
    # Old assertions: n 2, minmin 8, maxmax 13, start 2001-01-01, end 2001-01-05, topo True, gran 2 days
    pytest.param(
        "B {+,contains,l} A",
        {},
        [("2001-01-01", "2001-01-03", 8, 8), ("2001-01-03", "2001-01-05", 13, 13)],
        id="raster arithmetic relation 1",
    ),
    # Old assertions: n 2, minmin 10, maxmax 72, start 2001-01-01, end 2001-01-05, topo True, gran 2 days
    pytest.param(
        "B {*,contains,l} A",
        {},
        [("2001-01-01", "2001-01-03", 10, 10), ("2001-01-03", "2001-01-05", 72, 72)],
        id="raster arithmetic relation 2",
    ),
    # Old assertions: n 4, minmin 8, maxmax 13, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "B {+,contains,r} A",
        {},
        [
            ("2001-01-01", "2001-01-02", 8, 8),
            ("2001-01-02", "2001-01-03", 8, 8),
            ("2001-01-03", "2001-01-04", 13, 13),
            ("2001-01-04", "2001-01-05", 13, 13),
        ],
        id="raster arithmetic relation 4",
    ),
    # Old assertions: n 1, minmin 208, maxmax 208, start 2001-01-03, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "tmap(singletmap) {+,equal| precedes| follows,l} A + map(singlemap)",
        {},
        [("2001-01-03", "2001-01-04", 208, 208)],
        id="raster arithmetic relation 5",
    ),
    # Old assertions: n 4, minmin -2, maxmax -2, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "(((((((A + A) - A) * A) / A) % A) - td(A)) - (A # A))",
        {},
        [
            ("2001-01-01", "2001-01-02", -2, -2),
            ("2001-01-02", "2001-01-03", -2, -2),
            ("2001-01-03", "2001-01-04", -2, -2),
            ("2001-01-04", "2001-01-05", -2, -2),
        ],
        id="capacity 1",
    ),
]

CORE = {
    # Manual, Core and classic algebra, item 4: a right reference gives one map
    # per related pair with the value of the pair; the classic algebra combines
    # the left map with all of its related maps in each result
    "raster arithmetic relation 4": [
        ("2001-01-01", "2001-01-02", 6, 6),
        ("2001-01-02", "2001-01-03", 7, 7),
        ("2001-01-03", "2001-01-04", 9, 9),
        ("2001-01-04", "2001-01-05", 10, 10),
    ],
}

CORE_MESSAGE = {}

# Cases where the core differs although the manual does not say so; the first
# table holds what the core does today, the case itself what is right
CORE_TODAY = {}

CORE_TODAY_MESSAGE = {}

# The names of the maps, as the old test asserted for time_suffix (the basename r of the old test reads N_ in outcome())
NAMES = {
    "simple arith hash 1": [
        "N_2001_01_01",
        "N_2001_01_02",
        "N_2001_01_03",
        "N_2001_01_04",
    ],
    "simple arith td 1": [
        "N_2001_01_01T00_00_00",
        "N_2001_01_02T00_00_00",
        "N_2001_01_03T00_00_00",
        "N_2001_01_04T00_00_00",
    ],
}

SHAPE = {
    "(((((((A + A) - A) * A) / A) % A) - td(A)) - (A # A))": (True, "1 day"),
    "A # D": (True, "1 day"),
    "A * map(singlemap)": (True, "1 day"),
    "A : A": (True, "1 day"),
    "A : D": (True, "1 day"),
    "A {!:,during} C": (True, "1 day"),
    "A {:,during,d} B": (False, "2 days"),
    "A {:,during,r} C": (False, "2 days"),
    "A {:,equal|during,r} C": (False, "2 days"),
    "B {*,contains,l} A": (True, "2 days"),
    "B {+,contains,l} A": (True, "2 days"),
    "B {+,contains,r} A": (True, "1 day"),
    "C {#,contains} A": (True, "2 days"),
    "if(A # D == 1, A)": (True, "1 day"),
    "if({contains}, B == 5,  A - 1,  A + 1)": (True, "1 day"),
    "if({during},A # D == 1, C {#,contains} A)": (True, "2 days"),
    "map(singlemap) + A": (True, "1 day"),
    "tmap(singletmap)": (True, "1 day"),
    "tmap(singletmap) + 1": (True, "1 day"),
    "tmap(singletmap) {+,equal| precedes| follows,l} A + map(singlemap)": (
        True,
        "1 day",
    ),
}

SHAPE_CORE = {}

DRY = [
    pytest.param(
        "A {:,during,r} C",
        {},
        {
            "names": ["r.mapcalc", "r.mapcalc"],
            "processes": 2,
            "register": 2,
            "stdstype": "strds",
        },
        id="temporal extent1 (dry run)",
    ),
    pytest.param(
        "(((((((A + A) - A) * A) / A) % A) - td(A)) - (A # A))",
        {},
        {"processes": 4, "register": 4, "stdstype": "strds"},
        id="capacity 1 (dry run)",
    ),
]

# What a runner makes of a planned run although the manual does not say so
DRY_TODAY = {}


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    legacy_data.raster_algebra(tools)
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


@pytest.mark.parametrize("runner", RUNNERS)
@pytest.mark.parametrize(("expression", "options", "expected"), DRY)
def test_dry_runs(data, request, runner, expression, options, expected):
    today = DRY_TODAY.get((case_id(request), runner))
    if isinstance(today, tuple):
        with pytest.raises(ValueError, match=re.escape(today[1])):
            legacy_data.check_dry(KIND, runner, expression, options, expected)
    else:
        legacy_data.check_dry(KIND, runner, expression, options, today or expected)


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
