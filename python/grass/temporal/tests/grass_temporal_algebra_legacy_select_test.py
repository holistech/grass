"""The cases of the earlier gunittest file unittests_temporal_algebra.py

Temporalalgebraparser, the select algebra of t.select.

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
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A : A",
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="temporal select1",
    ),
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A : D",
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal select2",
    ),
    # Old assertions: n 2, minmin 1, maxmax 2, start 2001-01-01, end 2001-01-03, topo True, gran 1 day
    pytest.param(
        "A !: D",
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-02", 1, 1), ("2001-01-02", "2001-01-03", 2, 2)],
        id="temporal select3",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A {:,during} C",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal select operators1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A {:,equal|during} C",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal select operators2",
    ),
    # Old assertions: n 2, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "A {!:,during} C",
        {"stdstype": "strds"},
        [("2001-01-01", "2001-01-02", 1, 1), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal select operators3",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,during,d} C",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-04", 2, 2), ("2001-01-02", "2001-01-04", 3, 3)],
        id="temporal select operators4",
    ),
    # Old assertions: n 1, minmin 7, maxmax 7, start 2001-01-02, end 2001-01-04, topo True, gran 2 days
    pytest.param(
        "C {:,contains} A",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-04", 7, 7)],
        id="temporal select operators5",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,during,r} C",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-04", 2, 2), ("2001-01-02", "2001-01-04", 3, 3)],
        id="temporal extent1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo False, gran 2 days
    pytest.param(
        "A {:,during,u} C",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-04", 2, 2), ("2001-01-02", "2001-01-04", 3, 3)],
        id="temporal extent3",
    ),
    # Old assertions: n 2, minmin 3, maxmax 4, start 2001-01-03, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "if(A # D == 1, A)",
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 3, 3), ("2001-01-04", "2001-01-05", 4, 4)],
        id="temporal hash1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if(A {#,during} C == 1, A)",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal hash operator1",
    ),
    # Old assertions: n 2, minmin 2, maxmax 3, start 2001-01-02, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "if({contains}, C {#,contains} A == 2, A)",
        {"stdstype": "strds"},
        [("2001-01-02", "2001-01-03", 2, 2), ("2001-01-03", "2001-01-04", 3, 3)],
        id="temporal hash operator2",
    ),
    # Old assertions: n 1, minmin 99, maxmax 99, start 2001-01-03, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "tmap(singletmap)",
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 99, 99)],
        id="tmap function1",
    ),
    # Old assertions: n 1, minmin 3, maxmax 3, start 2001-01-03, end 2001-01-04, topo True, gran 1 day
    pytest.param(
        "A : tmap(singletmap)",
        {"stdstype": "strds"},
        [("2001-01-03", "2001-01-04", 3, 3)],
        id="tmap function2",
    ),
    # Old assertions: n 7, minmin 1, maxmax 10, start 2001-01-01, end 2001-01-06, topo False, gran 1 day
    pytest.param(
        "merge(A,D)",
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-03", "2001-01-04", 8, 8),
            ("2001-01-04", "2001-01-05", 4, 4),
            ("2001-01-04", "2001-01-05", 9, 9),
            ("2001-01-05", "2001-01-06", 10, 10),
        ],
        id="merge function1",
    ),
    # Old assertions: n 4, minmin 1, maxmax 4, start 2001-01-01, end 2001-01-05, topo True, gran 1 day
    pytest.param(
        "merge(A, B {!:,contains} A)",
        {"stdstype": "strds"},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 2, 2),
            ("2001-01-03", "2001-01-04", 3, 3),
            ("2001-01-04", "2001-01-05", 4, 4),
        ],
        id="merge function2",
    ),
]

CORE = {}

CORE_MESSAGE = {}

# Cases where the core differs although the manual does not say so; the first
# table holds what the core does today, the case itself what is right
CORE_TODAY = {}

CORE_TODAY_MESSAGE = {}

NAMES = {}

SHAPE = {
    "A !: D": (True, "1 day"),
    "A : A": (True, "1 day"),
    "A : D": (True, "1 day"),
    "A : tmap(singletmap)": (True, "1 day"),
    "A {!:,during} C": (True, "1 day"),
    "A {:,during,d} C": (False, "2 days"),
    "A {:,during,r} C": (False, "2 days"),
    "A {:,during,u} C": (False, "2 days"),
    "A {:,during} C": (True, "1 day"),
    "A {:,equal|during} C": (True, "1 day"),
    "C {:,contains} A": (True, "2 days"),
    "if(A # D == 1, A)": (True, "1 day"),
    "if(A {#,during} C == 1, A)": (True, "1 day"),
    "if({contains}, C {#,contains} A == 2, A)": (True, "1 day"),
    "merge(A, B {!:,contains} A)": (True, "1 day"),
    "merge(A,D)": (False, "1 day"),
    "tmap(singletmap)": (True, "1 day"),
}

SHAPE_CORE = {}

DRY = [
    pytest.param(
        "merge(A, B {:,contains} A)",
        {"stdstype": "strds"},
        {"register": 6, "stdstype": "strds"},
        id="merge function1 (dry run)",
    ),
    pytest.param(
        "merge(A, B {!:,contains} A)",
        {"stdstype": "strds"},
        {"register": 4, "stdstype": "strds"},
        id="merge function2 (dry run)",
    ),
    pytest.param(
        "merge(A, D {!:,equal} A)",
        {"stdstype": "strds"},
        {"register": 5, "stdstype": "strds"},
        id="merge function3 (dry run)",
    ),
    pytest.param(
        'tshift(A, "3 days")',
        {"stdstype": "strds"},
        {"register": 4, "stdstype": "strds"},
        id="shift1 (dry run)",
    ),
    pytest.param(
        'tshift(A, "2 days") {:,during,l} C',
        {"stdstype": "strds"},
        {"register": 1, "stdstype": "strds"},
        id="shift2 (dry run)",
    ),
    pytest.param(
        'buff_t(A, "1 day")',
        {"stdstype": "strds"},
        {"register": 4, "stdstype": "strds"},
        id="buffer1 (dry run)",
    ),
    pytest.param(
        'buff_t(A, "1 day") {:,contains,l} C',
        {"stdstype": "strds"},
        {"register": 2, "stdstype": "strds"},
        id="buff2 (dry run)",
    ),
    pytest.param(
        "if(start_doy(A)<3,start_doy(A, 1), A)",
        {"stdstype": "strds"},
        {"register": 4, "stdstype": "strds"},
        id="time constant (dry run)",
    ),
]

DRY_SHOULD = [
    pytest.param(
        "if(start_doy(A)<3,start_doy(A, 1), A)",
        {"stdstype": "strds"},
        {"register": 4, "stdstype": "strds"},
        "core",
        id="time constant (dry run)-core",
    ),
]

# What a runner makes of a planned run although the manual does not say so
DRY_TODAY = {
    ("time constant (dry run)", "core"): (
        "ValueError",
        "merge() needs series of one sort, fields or scalars",
    )
}


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    legacy_data.algebra(tools)
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


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE, a runner plans another run")
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
