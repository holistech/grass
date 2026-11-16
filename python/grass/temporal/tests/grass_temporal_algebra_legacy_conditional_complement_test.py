"""The cases of the earlier gunittest file unittests_temporal_raster_conditionals_complement_else.py

The complement of an else part.

The expected maps are those the old assertions describe (number of maps,
extent, minimum, maximum, topology, granularity); the comment of a case repeats
them. CORE holds the maps the core makes where they differ according to the
manual ("Differences from GRASS 8.5"); SHAPE what the old test asserted besides
the maps. The datasets are those of algebra_cases, see its builder for the data.
"""

import pytest

from grass.temporal.testing import algebra_cases
from grass.tools import Tools

KIND = "raster"


CASES = [
    # Old assertions: n 4, minmin 1, maxmax 17, start 2001-01-01, end 2001-01-07, topo True, gran 1 day
    pytest.param(
        "merge(if({equal|contains}, B {#,contains} A == 2, B {+,contains,l} A, A), A {!:,during} B)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-04", 12, 12),
            ("2001-01-04", "2001-01-06", 17, 17),
            ("2001-01-06", "2001-01-07", 6, 6),
        ],
        id="temporal conditional complement",
    ),
    # Old assertions: n 6, minmin 1, maxmax 17, start 2001-01-01, end 2001-01-07, topo True, gran 1 day
    pytest.param(
        "merge(if({equal|contains|during}, B {#,contains} A == 2, B {+,contains,r} A, A), A {!:,during} B)",
        {},
        [
            ("2001-01-01", "2001-01-02", 1, 1),
            ("2001-01-02", "2001-01-03", 12, 12),
            ("2001-01-03", "2001-01-04", 12, 12),
            ("2001-01-04", "2001-01-05", 17, 17),
            ("2001-01-05", "2001-01-06", 17, 17),
            ("2001-01-06", "2001-01-07", 6, 6),
        ],
        id="temporal conditional complement right side timestamps",
    ),
]

CORE = {
    # Manual, Differences from GRASS 8.5, item 4: a right reference gives one map
    # per related pair with the value of the pair; the classic algebra combined
    # the left map with all of its related maps in each result
    "temporal conditional complement right side timestamps": [
        ("2001-01-01", "2001-01-02", 1, 1),
        ("2001-01-02", "2001-01-03", 9, 9),
        ("2001-01-03", "2001-01-04", 10, 10),
        ("2001-01-04", "2001-01-05", 12, 12),
        ("2001-01-05", "2001-01-06", 13, 13),
        ("2001-01-06", "2001-01-07", 6, 6),
    ],
}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    "merge(if({equal|contains|during}, B {#,contains} A == 2, B {+,contains,r} A, A), A {!:,during} B)": (
        True,
        "1 day",
    ),
    "merge(if({equal|contains}, B {#,contains} A == 2, B {+,contains,l} A, A), A {!:,during} B)": (
        True,
        "1 day",
    ),
}

SHAPE_CORE = {}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.conditional_complement(tools)
    return temporal_module_session


def case_id(request):
    return request.node.callspec.id


@pytest.mark.parametrize(("expression", "options", "expected"), CASES)
def test_cases(data, request, expression, options, expected):
    shape = SHAPE.get(expression)
    message = None
    name = case_id(request)
    if name in CORE:
        expected = CORE[name]
        message = CORE_MESSAGE.get(name)
        shape = SHAPE_CORE.get(name, shape)
    algebra_cases.check_case(
        KIND,
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
