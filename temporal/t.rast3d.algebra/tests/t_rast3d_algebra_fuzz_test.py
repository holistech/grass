"""Differential fuzzing of the algebras for 3D raster maps

Random expressions of the classic grammar (grass.temporal.testing.expressions)
must register the same maps in two implementations of the algebra: the
reference implementation (grass.temporal.classic), whose outcomes
grass.temporal.testing.corpus holds, and the classic profile of the core. That
must give 0 differences. The test of the listed differences shows that the
fuzzer sees one where there is one: the expressions of the differential test of
this directory, run on the core and compared with the recorded outcomes of the
reference.

The seeds 0 to 199 run in the normal run. GRASS_TEMPORAL_FUZZ_COUNT and
GRASS_TEMPORAL_FUZZ_SEED widen that, see the module docstring of
grass.temporal.testing.expressions. The tests carry slow, because the seeds
cost seconds, and fixed_algebra, because they choose their runners themselves.

Normal run: 19.1 s for 321 tests, measured 2026-10-24 with
`python3 -m pytest -p no:cacheprovider -q <this file>`, with the outcomes of
the reference read from the corpus, including the creation of the datasets.
"""

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.differential import (
    RUNNERS,
    check_agreement,
    check_difference_seen,
    outcome,
    prepare,
)
from grass.temporal.testing.expressions import check_seed, seed_range
from grass.temporal.testing.expressions_generator import boundary_forms

KIND = "raster3d"

pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Expressions of the differential test of this directory that the reference
# and the core answer differently on the datasets of the fuzzer.
LISTED = [
    'buff_t(W, "-1 day")',
    'buff_t(A, "-1 day")',
    "W {:,contains,r} A",
    "W {+,contains,r} A",
    "if({during}, A > 1, W, 0)",
    "if(A > 2, A, W)",
]


# The same for the granularity mode (-g).
LISTED_GRANULARITY = ["if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)"]
GRANULARITY_SEEDS = range(50)


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """Create the datasets of the fuzzer, then switch on the test-only caches

    The caches of grass.temporal.testing.io_cache serve both runners alike. They
    start after the creation of the datasets, which runs with real IO.
    """
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("fuzz"))
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.mark.parametrize("seed", seed_range())
def test_runners_agree(datasets, seed):
    check_seed(KIND, seed)


@pytest.mark.parametrize("expression", boundary_forms(KIND))
def test_runners_agree_on_boundary_forms(datasets, expression):
    check_agreement(
        KIND,
        expression,
        **({"register_null": True} if KIND in {"raster", "raster3d"} else {}),
    )


@pytest.mark.parametrize("expression", LISTED)
def test_compare_sees_a_listed_difference(datasets, expression):
    check_difference_seen(
        KIND,
        expression,
        **({"register_null": True} if KIND in {"raster", "raster3d"} else {}),
    )


@pytest.mark.parametrize("seed", GRANULARITY_SEEDS)
def test_runners_agree_in_granularity_mode(datasets, seed):
    check_seed(KIND, seed, granularity_share=1.0)


@pytest.mark.parametrize("expression", LISTED_GRANULARITY)
def test_compare_sees_a_listed_difference_in_granularity_mode(datasets, expression):
    check_difference_seen(KIND, expression, register_null=True, granularity=True)


def test_granularity_mode_reaches_the_runner(datasets):
    """The option must not end as an error of the parser, equal on both sides"""
    result = outcome(
        KIND, "A + B", RUNNERS["reference"], basename="fa", granularity=True
    )
    assert result["stds"]
    assert result["maps"]
