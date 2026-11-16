"""Test every method of t.rast.series on two series of five values

The series are those of conftest.py (first cell 1, 2, 3, 4, 10; second cell
3, 2, 4, 5, 2). The expected values are derived by hand from the formulas of
lib/stats, with n = 5 and the position i = 0 to 4 in time order:

- variance, standard deviation, skewness, kurtosis use the mean m and the
  deviations d = v - m with the divisor n (not n - 1): var = sum(d^2) / n,
  skewness = sum(d^3) / (n var^1.5), kurtosis = sum(d^4) / (n var^2) - 3.
- slope = (sum(i v) - n 2 m) / (sum(i^2) - n 4), offset = m - 2 slope,
  detcoeff = (sum(i v) - n 2 m)^2 / ((sum(i^2) - n 4) (sum(v^2) - n m^2)).
- quantile q is the type 7 estimate: k = q (n - 1) and the linear mix of the
  two sorted values around k. quart1 is q = 0.25, quart3 0.75, perc90 0.9.
- median is the mean of the two middle sorted values, mode the smallest value
  of the highest count, diversity the number of distinct values.
- min_raster and max_raster count the maps from 0; the first position wins a
  tie.
"""

import math
import re
from pathlib import Path

import pytest

# First cell: sorted 1 2 3 4 10, m = 4, d = -3 -2 -1 0 6, sum(d^2) = 50,
# var = 10. Second cell: sorted 2 2 3 4 5, m = 3.2, d = -0.2 -1.2 0.8 1.8 -1.2,
# sum(d^2) = 6.8, var = 1.36.
EXPECTED = {
    "average": (4.0, 3.2),
    "count": (5.0, 5.0),
    # Sorted 1 2 3 4 10 and 2 2 3 4 5: the middle value.
    "median": (3.0, 3.0),
    # All five values of the first series differ, so the first sorted value
    # wins; the 2 of the second series occurs twice.
    "mode": (1.0, 2.0),
    "minimum": (1.0, 2.0),
    # The minimum 1 is in map 0; the 2 of the second cell is first in map 1
    # (the later 2 in map 4 does not replace it).
    "min_raster": (0.0, 1.0),
    "maximum": (10.0, 5.0),
    "max_raster": (4.0, 3.0),
    "stddev": (math.sqrt(10), math.sqrt(1.36)),
    "range": (9.0, 3.0),
    "sum": (20.0, 16.0),
    "variance": (10.0, 1.36),
    "diversity": (5.0, 4.0),
    # First cell: sum(i v) = 60, numerator 60 - 5 2 4 = 20, denominator
    # 30 - 20 = 10: slope 2, offset 4 - 2 2 = 0, detcoeff 400 / (10 50) = 0.8
    # (sum(v^2) = 130, 130 - 5 16 = 50). Second cell: sum(i v) = 33,
    # numerator 33 - 5 2 3.2 = 1: slope 0.1, offset 3.2 - 0.2 = 3.0, detcoeff
    # 1 / (10 6.8) = 1 / 68 (sum(v^2) = 58, 58 - 5 10.24 = 6.8).
    "slope": (2.0, 0.1),
    "offset": (0.0, 3.0),
    "detcoeff": (0.8, 1 / 68),
    # k = 1 gives the second sorted value, k = 3 the fourth; k = 3.6 mixes
    # the fourth and fifth value: 4 0.4 + 10 0.6 = 7.6 and 4 0.4 + 5 0.6 = 4.6.
    "quart1": (2.0, 2.0),
    "quart3": (4.0, 4.0),
    "perc90": (7.6, 4.6),
    # sum(d^3) = -27 - 8 - 1 + 0 + 216 = 180 and sum(d^4) = 81 + 16 + 1 + 0
    # + 1296 = 1394: skewness 180 / (5 10^1.5) = 1.13842, kurtosis
    # 1394 / (5 100) - 3 = -0.212. Second cell: sum(d^3) = 2.88 and
    # sum(d^4) = 15.056: 2.88 / (5 1.36^1.5) = 0.363173 and
    # 15.056 / (5 1.36^2) - 3 = -1.371972.
    "skewness": (180 / (5 * 10**1.5), 2.88 / (5 * 1.36**1.5)),
    "kurtosis": (-0.212, 15.056 / (5 * 1.36**2) - 3),
}


def _approx(pair):
    return [pytest.approx(value, rel=1e-9, abs=1e-12) for value in pair]


@pytest.mark.parametrize("method", sorted(EXPECTED))
def test_method(series, stats, method):
    assert series(stats, method=method) == [_approx(EXPECTED[method])]


def test_every_method_of_the_tool_is_tested():
    # The methods are read from the option in the source of the tool, so a
    # method that is added there without a test fails here. The interface
    # description would need a session of its own for a tool that only the
    # session finds.
    source = (Path(__file__).parents[1] / "t.rast.series.py").read_text()
    block = source.split("# % key: method", 1)[1].split("# %end", 1)[0]
    options = re.search(r"# % options: (.*)", block).group(1)
    assert sorted(options.split(",")) == sorted([*EXPECTED, "quantile"])
