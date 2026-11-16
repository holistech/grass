"""The cases of the earlier gunittest file unittests_temporal_raster_algebra_spatial_topology.py

Spatial relations.

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
    # Old assertions: n 4, minmin 2, maxmax 8, start 2001-01-01, topo False
    pytest.param(
        "A {+,equal|equivalent,l} B",
        {"spatial": True},
        [
            ("2001-01-01", None, 2, 2),
            ("2001-01-01", None, 4, 4),
            ("2001-01-01", None, 6, 6),
            ("2001-01-01", None, 8, 8),
        ],
        id="equal equivalent sum",
    ),
    # Old assertions: n 2, minmin 4, maxmax 6, start 2001-01-01, topo False
    pytest.param(
        "A {+,equal|overlap,l} B",
        {"spatial": True},
        [("2001-01-01", None, 4, 4), ("2001-01-01", None, 6, 6)],
        id="equal overlap sum",
    ),
    # Old assertions: n 4, minmin 4, maxmax 6, start 2001-01-01, topo False
    pytest.param(
        "A {+,equal|overlap,l} B",
        {"register_null": True, "spatial": True},
        [
            ("2001-01-01", None, 4, 4),
            ("2001-01-01", None, 6, 6),
            ("2001-01-01", None, None, None),
            ("2001-01-01", None, None, None),
        ],
        id="equal overlap sum with null",
    ),
    # Old assertions: n 1, minmin 5, maxmax 5, start 2001-01-01, topo True
    pytest.param(
        "A {+,equal|contain,l} B",
        {"spatial": True},
        [("2001-01-01", None, 5, 5)],
        id="equal contain sum",
    ),
    # Old assertions: n 4, minmin 2, maxmax 8, start 2001-01-01, topo False
    pytest.param(
        "A {+,equal|equivalent|contain,l} B",
        {"spatial": True},
        [
            ("2001-01-01", None, 2, 2),
            ("2001-01-01", None, 6, 6),
            ("2001-01-01", None, 7, 7),
            ("2001-01-01", None, 8, 8),
        ],
        id="equal equivalent contain sum",
    ),
    # Old assertions: n 4, minmin 2, maxmax 8, start 2001-01-01, topo False
    pytest.param(
        "if({equal|equivalent}, A > 0 {&&,equal|equivalent} B < 10, A {+,equal|equivalent,l} B)",
        {"spatial": True},
        [
            ("2001-01-01", None, 2, 2),
            ("2001-01-01", None, 4, 4),
            ("2001-01-01", None, 6, 6),
            ("2001-01-01", None, 8, 8),
        ],
        id="equal equivalent compare",
    ),
]

CORE = {}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    "A {+,equal|contain,l} B": (True, None),
    "A {+,equal|equivalent,l} B": (False, None),
    "A {+,equal|equivalent|contain,l} B": (False, None),
    "A {+,equal|overlap,l} B": (False, None),
    "if({equal|equivalent}, A > 0 {&&,equal|equivalent} B < 10, A {+,equal|equivalent,l} B)": (
        False,
        None,
    ),
}

SHAPE_CORE = {}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.spatial_topology(tools)
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
