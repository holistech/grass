"""Test the weights and the circular window of t.rast.neighbors on the spike

The spike holds 10 in the centre, 20 to the right of it, 40 in the upper left
corner and 0 elsewhere (conftest.py). With the weight w(d) of a cell at the
distance d from the centre of the window:

- the average is sum(w v) / sum(w), so a common factor of the weights cancels;
- the sum is sum(w v), so it keeps the factor.

The centre sees the whole map: its cells lie at d = 0 (value 10), d = 1 (the
four edge cells, 20 among them) and d = sqrt(2) (the four corners, 40 among
them). The upper left corner sees four cells: itself (d = 0, value 40), two
edge cells (d = 1, value 0) and the diagonal cell (d = sqrt(2), the centre of
the map, value 10).

gaussian: w = exp(-d^2 / (2 s^2)) / (2 pi s^2) with s the weighting factor.
exponential: w = exp(f d) with f the weighting factor.
"""

import math

import pytest

from grass.temporal.testing.readback import cell_values, list_maps, message
from grass.tools import ToolError


def _cells(tools, input, prefix, **options):
    tools.t_rast_neighbors(input=input, output=prefix, basename=prefix, **options)
    (row,) = list_maps(tools, "strds", prefix)
    return cell_values(tools, row.name)


def _gauss(sigma):
    return lambda d2: math.exp(-d2 / (2 * sigma**2)) / (2 * math.pi * sigma**2)


def _exponential(factor):
    return lambda d2: math.exp(factor * math.sqrt(d2))


def _centre(w, *, total=False):
    # Values by squared distance: 10 at 0, 20 at 1, 40 at 2; weights of the
    # other cells count in the divisor (4 at 1, 4 at 2, none at 0 besides).
    numerator = 10 * w(0) + 20 * w(1) + 40 * w(2)
    return numerator if total else numerator / (w(0) + 4 * w(1) + 4 * w(2))


def _corner(w):
    numerator = 40 * w(0) + 10 * w(2)
    return numerator / (w(0) + 2 * w(1) + w(2))


def test_no_weights_give_the_plain_average(tools, spike, prefix):
    # 70 / 9 in the centre; (40 + 0 + 0 + 10) / 4 in the corner.
    values = _cells(tools, spike, prefix)

    assert (values[4], values[0]) == (pytest.approx(70 / 9), pytest.approx(12.5))


@pytest.mark.parametrize("sigma", [1.0, 2.0])
def test_gaussian_weights(tools, spike, prefix, sigma):
    values = _cells(
        tools,
        spike,
        prefix,
        weighting_function="gaussian",
        weighting_factor=sigma,
    )

    w = _gauss(sigma)
    assert values[4] == pytest.approx(_centre(w), rel=1e-9)
    assert values[0] == pytest.approx(_corner(w), rel=1e-9)


@pytest.mark.parametrize("factor", [-1.0, -0.5])
def test_exponential_weights(tools, spike, prefix, factor):
    values = _cells(
        tools,
        spike,
        prefix,
        weighting_function="exponential",
        weighting_factor=factor,
    )

    w = _exponential(factor)
    assert values[4] == pytest.approx(_centre(w), rel=1e-9)
    assert values[0] == pytest.approx(_corner(w), rel=1e-9)


def test_a_weighted_sum_keeps_the_factor_of_the_weights(tools, spike, prefix):
    values = _cells(
        tools,
        spike,
        prefix,
        method="sum",
        weighting_function="gaussian",
        weighting_factor=1,
    )

    assert values[4] == pytest.approx(_centre(_gauss(1), total=True), rel=1e-9)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_weighted_median_takes_the_value_at_half_the_weight(tools, spike, prefix):
    # Exponential weights with the factor -3: w(0) = 1, w(1) = e^-3 = 0.0498,
    # w(sqrt 2) = e^-4.243 = 0.0144. Sorted values of the centre window: six
    # zeros (three edge cells, three corners: weight 3 (0.0498 + 0.0144) =
    # 0.193), then 10 (weight 1), 20 and 40. The total weight is
    # 1 + 4 0.0498 + 4 0.0144 = 1.257, half of it 0.628. The cumulative weight
    # passes 0.628 at the 10 (0.193 + 1), so the median is 10. Without weights
    # six of nine values are 0 and the median is 0.
    values = _cells(
        tools,
        spike,
        prefix,
        method="median",
        weighting_function="exponential",
        weighting_factor=-3,
    )

    assert values[4] == 10.0
    assert _cells(tools, spike, f"{prefix}_plain", method="median")[4] == 0.0


def test_a_weight_file(tools, spike, prefix, tmp_path):
    # The matrix 1 2 1 / 2 4 2 / 1 2 1 gives the centre
    # (40 1 + 10 4 + 20 2) / 16 = 7.5. The corner sees the lower right part
    # of the matrix, 4 2 / 2 1: (40 4 + 0 + 0 + 10 1) / 9.
    weights = tmp_path / "weights.txt"
    weights.write_text("1 2 1\n2 4 2\n1 2 1\n")

    values = _cells(
        tools, spike, prefix, weighting_function="file", weight=str(weights)
    )

    assert values[4] == pytest.approx(7.5)
    assert values[0] == pytest.approx(170 / 9)


def test_a_circular_window_leaves_out_the_corners(tools, spike, prefix):
    # The centre keeps the four edge cells and itself: (10 + 20) / 5. The upper
    # left corner keeps itself and its two edge cells: 40 / 3.
    values = _cells(tools, spike, prefix, flags="c")

    assert (values[4], values[0]) == (pytest.approx(6.0), pytest.approx(40 / 3))


def test_the_weighting_function_may_be_abbreviated(tools, spike, prefix):
    # The old suite wrote "gauss"; the parser accepts a unique prefix.
    values = _cells(
        tools,
        spike,
        prefix,
        weighting_function="gauss",
        weighting_factor=1.5,
    )

    assert values[4] == pytest.approx(_centre(_gauss(1.5)), rel=1e-9)


@pytest.mark.parametrize(
    "options",
    [
        {"weighting_function": "file"},
        {"size": 4},
        {"weighting_function": "gaussian"},
    ],
    ids=["file-without-file", "even-size", "gaussian-without-factor"],
)
def test_today_a_failing_r_neighbors_ends_with_a_traceback(
    tools, spike, prefix, options
):
    # The tool collects the exit codes of its r.neighbors runs in order to
    # report them, but the queue raises on the first failing process before
    # that code is reached.
    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(input=spike, output=prefix, basename=prefix, **options)

    assert "CalledModuleError" in message(error.value)
    assert "Error running modules." not in message(error.value)


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("size", [4])
def test_a_failing_r_neighbors_is_reported_by_the_tool(tools, spike, prefix, size):
    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(input=spike, output=prefix, basename=prefix, size=size)

    assert "Traceback" not in message(error.value)
