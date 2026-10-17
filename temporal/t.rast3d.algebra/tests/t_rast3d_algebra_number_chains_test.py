"""Chains that start with map() are grouped from the left in 3D raster algebra

As t_rast_algebra_number_chains_test.py. A has four maps with the values 1, 2,
3 and 4, and the map single, without time stamp, has the value 1000.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, outcome, prepare

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# (expression, value of the four maps, value before the correction)
CHAINS = [
    # (1000 - 1) - A = 999 - A
    ("map(single) - 1 - A", [998, 997, 996, 995], [1000, 1001, 1002, 1003]),
    # (1000 * 2) + A = 2000 + A
    ("map(single) * 2 + A", [2001, 2002, 2003, 2004], [3000, 4000, 5000, 6000]),
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("chains"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new", "old"), CHAINS)
def test_a_chain_is_grouped_from_the_left(datasets, runner, expression, new, old):
    assert new != old
    result = outcome(KIND, expression, RUNNERS[runner], basename="fa")
    assert "error" not in result, result
    assert [low for *_, low, _high in result["maps"]] == new
