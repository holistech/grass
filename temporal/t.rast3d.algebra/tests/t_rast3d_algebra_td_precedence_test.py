"""The function td() as left operand of a stronger operator in 3D raster algebra

As t_rast_algebra_td_precedence_test.py. A has four maps of one day each with
the values 1, 2, 3 and 4, so td(A) is 1 for each of them.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, outcome, prepare

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# (expression, value of the four maps, value before the correction)
CHANGED = [
    # a + td / a: 1 + 1, 2 + 1 / 2, 3 + 1 / 3, 4 + 1 / 4
    (
        "A + td(A) / A",
        [2, 2.5, 3 + 1 / 3, 4.25],
        [2, 1.5, 4 / 3, 1.25],  # (a + td) / a
    ),
    # a - 2 td: 1 - 2, 2 - 2, 3 - 2, 4 - 2
    ("A - td(A) * 2", [-1, 0, 1, 2], [0, 2, 4, 6]),  # (a - td) 2
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("td"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new", "old"), CHANGED)
def test_td_binds_as_operand_of_the_stronger_operator(
    datasets, runner, expression, new, old
):
    assert new != old
    result = outcome(KIND, expression, RUNNERS[runner], basename="fa")
    assert "error" not in result, result
    assert [low for *_, low, _high in result["maps"]] == pytest.approx(new, rel=1e-5)
