"""Test the weighted kurtosis of r.series"""

import pytest


def _kurtosis(tools, tmp_path, values, weights):
    """Kurtosis of one cell series, weighted by a file of lines name|weight"""
    lines = []
    for number, (value, weight) in enumerate(zip(values, weights, strict=True)):
        name = f"map_{number}"
        tools.r_mapcalc(expression=f"{name} = {value}.0")
        lines.append(f"{name}|{weight}")
    listing = tmp_path / "maps.txt"
    listing.write_text("\n".join(lines) + "\n")
    tools.r_series(file=listing, output="result", method="kurtosis")
    return tools.r_univar(map="result", format="json")["mean"]


def test_weighted_kurtosis_uses_the_fourth_power(xy_session, tmp_path):
    # Values 7 and 14 with weights 0.7 and 0.3, total weight 1:
    #   mean  = 0.7 * 7 + 0.3 * 14 = 9.1
    #   d     = -2.1 and 4.9, d^2 = 4.41 and 24.01
    #   var   = 0.7 * 4.41 + 0.3 * 24.01 = 10.29
    #   d^4   = 19.4481 and 576.4801
    #   m4    = 0.7 * 19.4481 + 0.3 * 576.4801 = 186.5577
    #   kurt  = 186.5577 / 10.29^2 - 3 = 37 / 21 - 3 = -26 / 21 = -1.2380952...
    # The third power gave -2.727891156462585 (28.812 / 105.8841 - 3).
    result = _kurtosis(xy_session, tmp_path, [7, 14], [0.7, 0.3])

    assert result == pytest.approx(-26 / 21, rel=1e-9)


def test_weights_of_one_give_the_unweighted_kurtosis(xy_session, tmp_path):
    # Values 1, 2 and 6: mean 3, d = -2, -1, 3, sum d^2 = 14, sum d^4 = 98,
    # kurt = 98 / (3 * (14 / 3)^2) - 3 = 1.5 - 3 = -1.5. With all weights 1
    # r.series takes the unweighted routine.
    result = _kurtosis(xy_session, tmp_path, [1, 2, 6], [1, 1, 1])

    assert result == pytest.approx(-1.5, rel=1e-9)


def test_equal_weights_other_than_one_give_the_unweighted_kurtosis(
    xy_session, tmp_path
):
    # Doubling every weight doubles the count, the sums of d^2 and d^4, so
    # var and kurt stay: 196 / (6 * (14 / 3)^2) - 3 = 1.5 - 3 = -1.5. This
    # case reaches the weighted routine, because the weights are not all 1.
    result = _kurtosis(xy_session, tmp_path, [1, 2, 6], [2, 2, 2])

    assert result == pytest.approx(-1.5, rel=1e-9)
