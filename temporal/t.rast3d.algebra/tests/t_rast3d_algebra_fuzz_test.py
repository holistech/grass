"""Differential fuzzing of the algebras for 3D raster maps

Random expressions of the classic grammar (grass.temporal.testing.expressions)
run on two implementations of the algebra, and the registered maps must agree.
Until the classic profile of the core exists, the first and the second are both
the earlier implementation (SECOND below): that must give 0 differences and
shows that the fuzzer sees no difference where there is none. The test of the
listed differences shows that it sees one where there is one: the expressions
of the differential test of this directory, run on the reference and on the
core.

The seeds 0 to 199 run in the normal run. GRASS_TEMPORAL_FUZZ_COUNT and
GRASS_TEMPORAL_FUZZ_SEED widen that, see the module docstring of
grass.temporal.testing.expressions. The tests carry slow, because the seeds
cost seconds, and fixed_algebra, because they choose their runner themselves.

Normal run: 26.0 s for 269 tests, measured 2026-10-15 with
`python3 -m pytest -p no:cacheprovider -q <this file>`, including the creation of the
datasets (one run; other agents used the machine at the same time).
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import (
    RUNNERS,
    boundary_forms,
    compare,
    generate,
    outcome,
    prepare,
    seed_range,
)

KIND = "raster3d"
FIRST = RUNNERS["reference"]
SECOND = RUNNERS["reference"]

pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Expressions of the differential test of this directory that the reference
# and the core answer differently on the datasets of the fuzzer.
LISTED = [
    'buff_t(W, "-1 day")',
    'buff_t(A, "-1 day")',
    "if(A > 2, A)",
    "W {:,contains,r} A",
    "W {+,contains,r} A",
    "if({during}, A > 1, W, 0)",
    "if(A > 2, A, W)",
    "A {+,equal|overlap} B",
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """Create the datasets of the fuzzer in the session of the module"""
    return prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("fuzz"))


@pytest.fixture(scope="module")
def io_cache_storage():
    """Answers of the test-only caches, shared by the tests of one module"""
    return fakes.CacheStorage()


@pytest.fixture(autouse=True)
def cached_io(datasets, io_cache_storage):
    """Both runners get the caches of grass.temporal.testing.fakes alike"""
    with fakes.cached_io(io_cache_storage):
        yield


@pytest.mark.parametrize("seed", seed_range())
def test_runners_agree(datasets, seed):
    expression, options = generate(KIND, seed)
    first = outcome(KIND, expression, FIRST, basename="fa", **options)
    second = outcome(KIND, expression, SECOND, basename="fb", **options)
    assert compare(KIND, expression, first, second) is None, f"seed {seed}"


@pytest.mark.parametrize("expression", boundary_forms(KIND))
def test_runners_agree_on_boundary_forms(datasets, expression):
    options = {"register_null": True} if KIND in {"raster", "raster3d"} else {}
    first = outcome(KIND, expression, FIRST, basename="fa", **options)
    second = outcome(KIND, expression, SECOND, basename="fb", **options)
    assert compare(KIND, expression, first, second) is None


@pytest.mark.parametrize("expression", LISTED)
def test_compare_sees_a_listed_difference(datasets, expression):
    options = {"register_null": True}
    first = outcome(KIND, expression, RUNNERS["reference"], basename="fa", **options)
    second = outcome(KIND, expression, RUNNERS["core"], basename="fb", **options)
    assert compare(KIND, expression, first, second) is not None
