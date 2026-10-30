"""The cases of the earlier gunittest file of t.rast3d.algebra

The cases are those of test_raster3d_algebra.py on the dataset A of the
series_3d fixture in conftest.py (a1..a4 = 1..4, daily from 2001-01-01), the
same as the setUpClass of the old file. Every case runs in the earlier
implementation (reference), in the classic profile and in the new algebra
(core); the three agree on all of them, so there is no CORE table. The
format is that of t_rast_algebra_legacy_cases_test.py: (expression, options of
the runner, expected maps as (start, end, min, max) or the name of the error
class).
"""

import pytest

from grass.temporal.testing.differential import RUNNERS, outcome

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra


def day(first, last, value):
    """A constant map from the day first to the day last of January 2001"""
    return (
        f"2001-01-{first:02d}T00:00:00",
        f"2001-01-{last:02d}T00:00:00",
        value,
        value,
    )


# A map with a neighbour on both sides is a2 (a1 + a3 = 4) and a3 (a2 + a4 = 6).
NEIGHBORS = [day(2, 3, 4), day(3, 4, 6)]

CASES = [
    pytest.param("A[-1] + A[1]", {}, NEIGHBORS, id="temporal neighbors 1"),
    pytest.param("A[0,0,0,-1] + A[0,0,0,1]", {}, NEIGHBORS, id="temporal neighbors 2"),
    pytest.param(
        "A[0,0,0,-1] + A[0,0,0,1]",
        {"granularity": True},
        NEIGHBORS,
        id="temporal neighbors with granularity",
    ),
    pytest.param(
        "A {+,equal| precedes| follows,l B", {}, "SyntaxError", id="syntax error"
    ),
    pytest.param(
        "A {+,equal| precedes| follows,l} B",
        {"granularity": True},
        "FatalError",
        id="topological operator with granularity",
    ),
    pytest.param("NoSTR3DS + NoSTR3DS", {}, "FatalError", id="unknown dataset"),
]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "expected"), CASES)
def test_cases(series_3d, runner, expression, options, expected):
    result = outcome(
        KIND, expression, RUNNERS[runner], basename=f"l3{runner[:2]}", **options
    )
    if isinstance(expected, str):
        assert result["error"] == expected
        return
    assert "error" not in result, result
    assert sorted(
        (start, end, low, high) for _, start, end, low, high in result["maps"]
    ) == sorted(expected)
