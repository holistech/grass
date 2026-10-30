"""A comparison of two 3D raster datasets with a temporal relation, in if()

As t_rast_algebra_comparison_operator_test.py, also for the new algebra. A has four maps of one day each
with the values 1, 2, 3 and 4 and B the values 10, 20, 30 and 40 on the same
days, so a >= b is false on each day and the else part B is the result.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.differential import RUNNERS, compare, outcome, prepare

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

EXPRESSIONS = [
    # 1 >= 10, 2 >= 20, 3 >= 30, 4 >= 40 are false: B
    ("if(A >= B, A, B)", [10, 20, 30, 40]),
    ("if(A {>=,equal,l} B, A, B)", [10, 20, 30, 40]),
    # 1 < 10 and so on are true: A
    ("if(A {<,equals,|} B, A, B)", [1, 2, 3, 4]),
    # a * 11 = 11, 22, 33, 44 against b = 10, 20, 30, 40 is greater: A
    ("if(A * 11 {>,equal} B, A, B)", [1, 2, 3, 4]),
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("compare"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "values"), EXPRESSIONS)
def test_a_comparison_by_hand(datasets, runner, expression, values):
    result = outcome(KIND, expression, RUNNERS[runner], basename="fa")
    assert "error" not in result, result
    assert [row[3] for row in result["maps"]] == values


@pytest.mark.parametrize(("expression", "values"), EXPRESSIONS)
def test_the_profile_computes_what_the_reference_computes(datasets, expression, values):
    reference = reference_outcome(KIND, expression)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    assert compare(KIND, expression, reference, profile) is None
    assert reference["maps"]
