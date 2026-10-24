"""Differential fuzzing of the algebras for the selection of maps (t.select)

Random expressions of the classic grammar (grass.temporal.testing.expressions)
must register the same maps in two implementations of the algebra. Which two
is set in one place, DIFFERENTIAL in that module: the earlier implementation,
whose outcomes grass.temporal.testing.corpus holds, and the classic profile of
the core. That must give 0 differences. The test of the listed differences
shows that the fuzzer sees one where there is one: the expressions of the
differential test of this directory, run on the core and compared with the
recorded outcomes of the reference.

The seeds 0 to 199 run in the normal run. GRASS_TEMPORAL_FUZZ_COUNT and
GRASS_TEMPORAL_FUZZ_SEED widen that, see the module docstring of
grass.temporal.testing.expressions. The tests carry slow, because the seeds
cost seconds, and fixed_algebra, because they choose their runners themselves.

Normal run: 16.0 s for 216 tests, measured 2026-10-16 with
`python3 -m pytest -p no:cacheprovider -q <this file>`, including the creation of the
datasets.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import (
    boundary_forms,
    check_agreement,
    check_difference_seen,
    check_seed,
    prepare,
    seed_range,
)

KIND = "select"

pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Expressions of the differential test of this directory that the reference
# and the core answer differently on the datasets of the fuzzer.
LISTED = [
    "A[1]",
    "A {:,equal|overlap} B",
    "A",
    "A + B",
    'buff_t(A, "-5 days") {:,during} D',
    'buff_t(A, "-6 days") {:,during} D',
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """Create the datasets of the fuzzer, then switch on the test-only caches

    The caches of grass.temporal.testing.fakes serve both runners alike. They
    start after the creation of the datasets, which runs with real IO.
    """
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("fuzz"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.fixture(autouse=True)
def algebra():
    """Replace the fixture of conftest.py, which builds other datasets and
    runs every test on both algebras; the fuzzer selects its runners itself"""


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
