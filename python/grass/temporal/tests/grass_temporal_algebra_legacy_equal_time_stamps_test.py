"""The cases of the earlier gunittest file unittests_temporal_raster_algebra_equal_ts.py

Maps with equal time stamps.

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
    # Old assertions: n 4, minmin 11, maxmax 14, start 2001-01-01, topo False
    pytest.param(
        "A + A",
        {},
        [
            ("2001-01-01", None, 11, 11),
            ("2001-01-01", None, 12, 12),
            ("2001-01-01", None, 13, 13),
            ("2001-01-01", None, 14, 14),
        ],
        id="simple operator",
    ),
    # Old assertions: n 4, minmin 11, maxmax 14, start 2001-01-01, topo False
    pytest.param(
        "A {+, equal,l} A",
        {},
        [
            ("2001-01-01", None, 11, 11),
            ("2001-01-01", None, 12, 12),
            ("2001-01-01", None, 13, 13),
            ("2001-01-01", None, 14, 14),
        ],
        id="complex operator",
    ),
    # Old assertions: n 1, minmin 110, maxmax 110, start 2001-01-01, topo True
    pytest.param(
        "tmap(singletmap) {+, equal,l} A",
        {},
        [("2001-01-01", None, 110, 110)],
        id="single map complex operator",
    ),
    # Old assertions: n 1, minmin 110, maxmax 110, start 2001-01-01, topo True
    pytest.param(
        "tmap(singletmap) + A",
        {},
        [("2001-01-01", None, 110, 110)],
        id="single map simple operator",
    ),
    # Old assertions: n 4, minmin 110, maxmax 110, start 2001-01-01, topo False
    pytest.param(
        "tmap(singletmap) {+, equal,r} A",
        {},
        [
            ("2001-01-01", None, 110, 110),
            ("2001-01-01", None, 110, 110),
            ("2001-01-01", None, 110, 110),
            ("2001-01-01", None, 110, 110),
        ],
        id="single map complex operator right ts",
    ),
]

CORE = {
    # Manual, Core and classic algebra, item 4: a right reference gives one map
    # per related pair with the value of the pair; the classic algebra combines
    # the left map with all of its related maps in each result
    "single map complex operator right ts": [
        ("2001-01-01", None, 101, 101),
        ("2001-01-01", None, 102, 102),
        ("2001-01-01", None, 103, 103),
        ("2001-01-01", None, 104, 104),
    ],
}

CORE_MESSAGE = {}

NAMES = {}

SHAPE = {
    "A + A": (False, None),
    "A {+, equal,l} A": (False, None),
    "tmap(singletmap) + A": (True, None),
    "tmap(singletmap) {+, equal,l} A": (True, None),
    "tmap(singletmap) {+, equal,r} A": (False, None),
}

SHAPE_CORE = {}

DRY = []


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.equal_time_stamps(tools)
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
