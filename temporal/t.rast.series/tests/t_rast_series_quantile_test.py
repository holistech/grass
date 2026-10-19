"""Test the quantile method of t.rast.series, alone and with other methods

The quantile of the sorted values is the type 7 estimate of lib/stats/
c_percentile.c: k = q (n - 1) and the linear mix of the values at floor(k) and
ceil(k). The first cell holds 1, 2, 3, 4, 10, the second 2, 2, 3, 4, 5 sorted.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import message
from grass.tools import ToolError

# q, first cell, second cell (n - 1 = 4):
# 0.0: k = 0, the smallest value; 1.0: k = 4, the largest.
# 0.1: k = 0.4, first cell 1 0.6 + 2 0.4 = 1.4, second 2 0.6 + 2 0.4 = 2.
# 0.5: k = 2, the third value. 0.9: k = 3.6, first cell 4 0.4 + 10 0.6 = 7.6,
# second 4 0.4 + 5 0.6 = 4.6.
QUANTILES = [
    (0.0, 1.0, 2.0),
    (0.1, 1.4, 2.0),
    (0.5, 3.0, 3.0),
    (0.9, 7.6, 4.6),
    (1.0, 10.0, 5.0),
]


@pytest.mark.parametrize(("quantile", "first", "second"), QUANTILES)
def test_a_quantile(series, stats, quantile, first, second):
    result = series(stats, method="quantile", quantile=quantile)

    assert result == [[pytest.approx(first), pytest.approx(second)]]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_median_of_four_values_is_the_mean_of_the_middle_two(tools, series, prefix):
    # The series 100, 200, 300, 400: k = 0.5 3 = 1.5, so the quantile 0.5 is
    # (200 + 300) / 2 = 250. The old gunittest expected 300 (the value at
    # index 2), which was the result of the quantile algorithm that
    # lib/stats used before 21.01.2022; since then t.rast.series gives 250, as
    # the type 7 estimate of R does.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_{k}", 100 * (k + 1), day(k), day(k + 1)) for k in range(4)],
    )

    assert series(f"{prefix}_in", method="quantile", quantile=0.5) == [[250.0, 250.0]]


def test_a_quantile_next_to_another_method(series, stats):
    # The outputs come in the order of the methods; the quantile output is
    # the one at the position of "quantile".
    result = series(stats, outputs=2, method="quantile,maximum", quantile=0.5)

    assert result == [[3.0, 3.0], [10.0, 5.0]]


def test_today_a_quantile_after_another_method_is_the_minimum(series, stats):
    # r.series pairs the values of quantile= with the methods by position
    # (its manual: the same number of values for all options) and uses 0.0
    # where a position has none. t.rast.series passes quantile=0.9 unchanged,
    # so it goes to maximum and the quantile at the second position is the
    # quantile 0.0, the minimum. The form r.series expects, quantile=0,0.9,
    # fails the count of t.rast.series (2 quantiles + 1 method, 2 outputs).
    result = series(stats, outputs=2, method="maximum,quantile", quantile=0.9)

    assert result == [[10.0, 5.0], [1.0, 2.0]]


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.series passes quantile unchanged to r.series, which pairs it with the methods by position, so a quantile after another method becomes the minimum",
)
def test_a_quantile_after_another_method_is_computed(series, stats):
    result = series(stats, outputs=2, method="maximum,quantile", quantile=0.9)

    assert result == [[10.0, 5.0], [pytest.approx(7.6), pytest.approx(4.6)]]


def test_a_quantile_that_no_method_uses_is_refused(tools, stats, prefix):
    # Every value of quantile= counts as an output of the tool, used or not.
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(
            input=stats, method="average", quantile=0.5, output=f"{prefix}_o"
        )

    assert "Number requested methods and output maps do not match." in message(
        error.value
    )


@pytest.mark.parametrize("quantile", ["1.5", "-0.1"])
def test_a_quantile_outside_zero_to_one_is_refused(tools, stats, prefix, quantile):
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(
            input=stats, method="quantile", quantile=quantile, output=f"{prefix}_o"
        )

    assert f"Value <{quantile}> out of range for parameter <quantile>" in message(
        error.value
    )


def test_a_quantile_method_needs_a_quantile(tools, stats, prefix):
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(input=stats, method="quantile", output=f"{prefix}_o")

    assert "Number requested methods and output maps do not match." in message(
        error.value
    )


def test_today_several_quantiles_are_refused(tools, stats, prefix):
    # The tool counts every "quantile" in the method as one method less and
    # each quantile as one output. method=quantile with three quantiles passes
    # that check (0 + 3 outputs), but r.series then wants one method for each
    # output; the form that r.series itself documents, method repeated per
    # quantile, fails the check of the tool (2 + 3 is not 3).
    outputs = ",".join(f"{prefix}_o{n}" for n in range(3))
    with pytest.raises(ToolError) as error:
        tools.t_rast_series(
            input=stats, method="quantile", quantile="0.1,0.5,0.9", output=outputs
        )
    assert "output= and method= must have the same number of values" in message(
        error.value
    )

    with pytest.raises(ToolError) as error:
        tools.t_rast_series(
            input=stats,
            method="quantile,quantile,quantile",
            quantile="0.1,0.5,0.9",
            output=outputs,
        )
    assert "Number requested methods and output maps do not match." in message(
        error.value
    )


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.series refuses several quantiles, its count of methods and outputs does not fit the form r.series documents",
)
def test_several_quantiles_are_computed(series, stats):
    # The example of the r.series manual: method=quantile,quantile,quantile
    # quantile=0.1,0.5,0.9 with three outputs.
    result = series(
        stats,
        outputs=3,
        method="quantile,quantile,quantile",
        quantile="0.1,0.5,0.9",
    )

    assert result == [
        [pytest.approx(1.4), 2.0],
        [3.0, 3.0],
        [pytest.approx(7.6), pytest.approx(4.6)],
    ]
