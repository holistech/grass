"""Test every method and the size of t.rast.neighbors on a ramp of nine cells

The ramp holds 1 to 9 row by row. Its centre cell sees all nine values with a
window of 3 x 3; its upper left corner sees only the four cells that lie in
the region (1, 2, 4, 5), because cells outside the region are null and left
out. The expected values are derived from the formulas of lib/stats (n is the
number of non-null cells in the window, the variance uses the divisor n):

- centre: sum 45, mean 5, sum of squared deviations 60, variance 60 / 9,
  sorted 1 to 9.
- corner: sum 12, mean 3, sum of squared deviations 4 + 1 + 1 + 4 = 10,
  variance 2.5, sorted 1, 2, 4, 5.
- median is the mean of the two middle sorted values, mode the smallest value
  of the highest count (every value occurs once here), diversity the number
  of distinct values.
- quantile q is the type 7 estimate: k = q (n - 1) and the linear mix of the
  two sorted values around k. Centre: quart1 k = 2 gives 3, quart3 k = 6 gives
  7, perc90 k = 7.2 gives 8 0.8 + 9 0.2 = 8.2. Corner: quart1 k = 0.75 gives
  1 0.25 + 2 0.75 = 1.75, quart3 k = 2.25 gives 4 0.75 + 5 0.25 = 4.25,
  perc90 k = 2.7 gives 4 0.3 + 5 0.7 = 4.7.
- interspersion is (100 d + (c / 2)) / c + 1 for c = cells - 1 other cells of
  which d differ from the centre cell, stored in an integer map.
"""

import math

import pytest

from grass.temporal.testing.readback import cell_values, list_maps

# method: (centre, corner)
EXPECTED = {
    "average": (5.0, 3.0),
    "median": (5.0, 3.0),
    "mode": (1.0, 1.0),
    "minimum": (1.0, 1.0),
    "maximum": (9.0, 5.0),
    "range": (8.0, 4.0),
    "stddev": (math.sqrt(60 / 9), math.sqrt(2.5)),
    "sum": (45.0, 12.0),
    "count": (9.0, 4.0),
    "variance": (60 / 9, 2.5),
    "diversity": (9.0, 4.0),
    # Centre: 8 of 8 other cells differ: (800 + 4) / 8 + 1 = 101.5. Corner: 3
    # of 3 differ: (300 + 1) / 3 + 1 = 101.33. The output map is an integer
    # map (CELL), so both are stored as 101 (the 101.5 is cut, not rounded up,
    # measured 18.10.2026 with r.info -g on the output).
    "interspersion": (101.0, 101.0),
    "quart1": (3.0, 1.75),
    "quart3": (7.0, 4.25),
    "perc90": (8.2, 4.7),
}


def _result(tools, input, prefix, **options):
    tools.t_rast_neighbors(input=input, output=prefix, basename=prefix, **options)
    (row,) = list_maps(tools, "strds", prefix)
    return cell_values(tools, row.name)


@pytest.mark.parametrize("method", sorted(EXPECTED))
def test_method(tools, ramp, prefix, method):
    values = _result(tools, ramp, prefix, method=method)

    centre, corner = EXPECTED[method]
    assert values[4] == pytest.approx(centre, rel=1e-9)
    assert values[0] == pytest.approx(corner, rel=1e-9)


@pytest.mark.parametrize(
    ("quantile", "centre", "corner"),
    [(0.5, 5.0, 3.0), (0.25, 3.0, 1.75), (1.0, 9.0, 5.0)],
)
def test_a_quantile(tools, ramp, prefix, quantile, centre, corner):
    values = _result(tools, ramp, prefix, method="quantile", quantile=quantile)

    assert (values[4], values[0]) == (pytest.approx(centre), pytest.approx(corner))


def test_the_default_method_is_the_average_in_a_window_of_three(tools, ramp, prefix):
    assert _result(tools, ramp, prefix) == pytest.approx(
        [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]
    )


def test_a_window_of_five_sees_the_whole_map_everywhere(tools, ramp, prefix):
    # Every cell lies within two cells of every other in a 3 x 3 map.
    assert _result(tools, ramp, prefix, size=5) == [5.0] * 9


def test_a_window_of_one_copies_the_cells(tools, ramp, prefix):
    assert _result(tools, ramp, prefix, size=1) == [float(v) for v in range(1, 10)]


def test_every_method_of_the_tool_is_tested():
    # The methods are read from the option in the source of the tool.
    import re
    from pathlib import Path

    source = (Path(__file__).parents[1] / "t.rast.neighbors.py").read_text()
    block = source.split("# % key: method", 1)[1].split("# %end", 1)[0]
    options = re.search(r"# % options: (.*)", block).group(1)
    assert sorted(options.split(",")) == sorted([*EXPECTED, "quantile"])
