"""The cases of the earlier gunittest file unittests_temporal_raster3d_algebra.py

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

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

RUNNERS = ["reference", "classic", "core"]

CASES = [
    # Old assertions: n 2, minmin 4, maxmax 6, start 2001-01-02, end 2001-01-04
    pytest.param(
        "A[-1] + A[1]",
        {},
        [("2001-01-02", "2001-01-03", 4, 4), ("2001-01-03", "2001-01-04", 6, 6)],
        id="temporal neighbors 1",
    ),
    # Old assertions: n 2, minmin 4, maxmax 6, start 2001-01-02, end 2001-01-04
    pytest.param(
        "A[0,0,0,-1] + A[0,0,0,1]",
        {},
        [("2001-01-02", "2001-01-03", 4, 4), ("2001-01-03", "2001-01-04", 6, 6)],
        id="temporal neighbors 2",
    ),
]

CORE = {}

CORE_MESSAGE = {}

# Cases where the core differs although the manual does not say so; the first
# table holds what the core does today, the case itself what is right
CORE_TODAY = {}

CORE_TODAY_MESSAGE = {}

NAMES = {}

SHAPE = {}

SHAPE_CORE = {}

DRY = []

# What a runner makes of a planned run although the manual does not say so
DRY_TODAY = {}


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    legacy_data.raster3d_algebra(tools)
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
