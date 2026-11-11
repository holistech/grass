"""Test the flag -w of t.rast.aggregate: weights by the overlap in time

The weekly maps wm0=7 over 1 to 8 January 2001, wm1=14 over 8 to 15 and
wm2=21 over 15 to 22 are aggregated to granules of 10 days, which start on
1 January: [1, 11), [11, 21) and [21, 31). The grid ends behind the last
map, which ends on 22 January. With method sum a map counts with the share
of its own time that lies in the granule, with the other methods with the
share of the granule that it covers; r.series divides the weighted sum by
the sum of the weights. The expected values are derived in the comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a
# second (measured 2026-11-10 with the other tests of this directory).
pytestmark = pytest.mark.slow


def _rows(tools, name):
    return [(row.start, row.end, row.min) for row in list_maps(tools, "strds", name)]


def _stamp(offset):
    return day(offset).strftime("%Y-%m-%d %H:%M:%S")


def _expected(*values, step=10, relative=False):
    """Rows of granules of step days from day 0 with the given values

    The values are compared with a relative tolerance of 1e-12: the weights
    such as 0.3 and 3/7 have no exact binary form.
    """
    rows = []
    for number, value in enumerate(values):
        start, end = number * step, (number + 1) * step
        if relative:
            rows.append((str(start), str(end), pytest.approx(value, rel=1e-12)))
        else:
            rows.append((_stamp(start), _stamp(end), pytest.approx(value, rel=1e-12)))
    return rows


@pytest.fixture(scope="module")
def weekly(tools):
    maps = [
        MapSpec(f"wm{k}", 7.0 * (k + 1), day(7 * k), day(7 * k + 7)) for k in range(3)
    ]
    create_stds(tools, "strds", "w_weekly", maps)
    return "w_weekly"


@pytest.fixture(scope="module")
def weekly_relative(tools):
    """The weekly maps as relative intervals 0 to 7, 7 to 14 and 14 to 21 days"""
    maps = [MapSpec(f"wr{k}", 7.0 * (k + 1), 7 * k, 7 * k + 7) for k in range(3)]
    create_stds(
        tools, "strds", "w_relative", maps, temporaltype="relative", unit="days"
    )
    return "w_relative"


def _aggregate(tools, input_, output, method, **options):
    options.setdefault("granularity", "10 days")
    options.setdefault("sampling", "related")
    tools.t_rast_aggregate(
        input=input_,
        output=output,
        basename=output,
        method=method,
        flags="w",
        **options,
    )
    rows = _rows(tools, output)
    if options["granularity"] == 10:
        rows = [(str(start), str(end), value) for start, end, value in rows]
    return rows


def test_weighted_average(tools, weekly):
    # Weights are overlap / 10 days of the granule.
    # [1, 11): wm0 7 days -> 0.7, wm1 3 days -> 0.3:
    #   (7 * 0.7 + 14 * 0.3) / (0.7 + 0.3) = 9.1
    # [11, 21): wm1 4 days -> 0.4, wm2 6 days -> 0.6:
    #   (14 * 0.4 + 21 * 0.6) / 1.0 = 18.2
    # [21, 31): wm2 1 day -> 0.1: 21 * 0.1 / 0.1 = 21
    assert _aggregate(tools, weekly, "w_average", "average") == _expected(9.1, 18.2, 21)


def test_weighted_kurtosis(tools, weekly):
    # Weights are overlap / 10 days of the granule, as for the average. With
    # two values and the weights p and 1 - p the deviations from the mean are
    # d1 = -(1 - p) * s and d2 = p * s for the distance s of the values; the
    # fourth moment over the squared variance is (1 - 3 * p * (1 - p)) /
    # (p * (1 - p)), kurtosis is that minus 3.
    # [1, 11): 7 with 0.7 and 14 with 0.3, s = 7, p * (1 - p) = 0.21:
    #   mean 9.1, variance 10.29, fourth moment 186.5577,
    #   186.5577 / 10.29^2 - 3 = 37 / 21 - 3 = -26 / 21
    # [11, 21): 14 with 0.4 and 21 with 0.6, s = 7, p * (1 - p) = 0.24:
    #   mean 18.2, variance 11.76, fourth moment 161.3472,
    #   161.3472 / 11.76^2 - 3 = 7 / 6 - 3 = -11 / 6
    # [21, 31): wm2 alone is copied, 21, as for the other methods.
    assert _aggregate(tools, weekly, "w_kurtosis", "kurtosis") == _expected(
        -26 / 21, -11 / 6, 21
    )


def test_weighted_sum(tools, weekly):
    # Weights are overlap / 7 days of the map.
    # [1, 11): wm0 7/7, wm1 3/7: 7 + 14 * 3/7 = 13
    # [11, 21): wm1 4/7, wm2 6/7: 14 * 4/7 + 21 * 6/7 = 8 + 18 = 26
    # [21, 31): wm2 1/7: 21 * 1/7 = 3
    assert _aggregate(tools, weekly, "w_sum", "sum") == _expected(13, 26, 3)


def test_weighted_sum_single_map_is_scaled(tools, weekly):
    # Only wm0 [1, 8): granules of 3 days [1, 4), [4, 7), [7, 10) hold it
    # alone, with 3, 3 and 1 of its 7 days. The sum scales it by 3/7, 3/7
    # and 1/7: 3, 3, 1. Another method copies a single map, as without -w: 7.
    only_first = "name = 'wm0'"
    assert _aggregate(
        tools, weekly, "w_single_sum", "sum", granularity="3 days", where=only_first
    ) == _expected(3, 3, 1, step=3)
    assert _aggregate(
        tools,
        weekly,
        "w_single_average",
        "average",
        granularity="3 days",
        where=only_first,
    ) == _expected(7, 7, 7, step=3)


def test_weighted_lone_map_of_another_method_is_copied(tools, weekly):
    # As above, wm0 alone in each granule of 3 days, with 3, 3 and 1 of its
    # days. r.series would give about 0 for the stddev of one weighted map;
    # the map is copied instead, so each granule holds 7, as without -w.
    only_first = "name = 'wm0'"
    assert _aggregate(
        tools, weekly, "w_lone_stddev", "stddev", granularity="3 days", where=only_first
    ) == _expected(7, 7, 7, step=3)
    tools.t_rast_aggregate(
        input=weekly,
        output="w_lone_unweighted",
        basename="w_lone_unweighted",
        method="stddev",
        granularity="3 days",
        sampling="related",
        where=only_first,
    )
    assert _rows(tools, "w_lone_unweighted") == _expected(7, 7, 7, step=3)


def test_weighted_relative_time(tools, weekly_relative):
    # The same overlaps as in absolute time, counted in relative days:
    # granules [0, 10), [10, 20), [20, 30).
    assert _aggregate(
        tools, weekly_relative, "w_rel_average", "average", granularity=10
    ) == _expected(9.1, 18.2, 21, relative=True)
    assert _aggregate(
        tools, weekly_relative, "w_rel_sum", "sum", granularity=10
    ) == _expected(13, 26, 3, relative=True)


def test_weighted_with_default_sampling(tools, weekly):
    # With contains only wm0 lies within a granule, [1, 11), and covers 7 of
    # its 10 days, the whole of its own 7. The average divides by its single
    # weight 0.7: 7. The sum weights it with 7/7: 7.
    assert _aggregate(
        tools, weekly, "w_contains_average", "average", sampling="contains"
    ) == _expected(7)
    assert _aggregate(
        tools, weekly, "w_contains_sum", "sum", sampling="contains"
    ) == _expected(7)


def test_weighted_granule_with_gap(tools, weekly):
    # Without wm1, [1, 11) holds wm0 alone: average 7 * 0.7 / 0.7 = 7, sum
    # 7 * 7/7 = 7. [11, 21) holds wm2 with 6 days: average 21, sum
    # 21 * 6/7 = 18. [21, 31) holds wm2 with 1 day: average 21, sum 3.
    without_second = "name != 'wm1'"
    assert _aggregate(
        tools, weekly, "w_gap_average", "average", where=without_second
    ) == _expected(7, 21, 21)
    assert _aggregate(
        tools, weekly, "w_gap_sum", "sum", where=without_second
    ) == _expected(7, 18, 3)


@pytest.fixture(scope="module")
def with_instant(tools):
    """wi0=7 over 1 to 8 January 2001 and the time instant wi1=3 on 9 January"""
    maps = [MapSpec("wi0", 7.0, day(0), day(7)), MapSpec("wi1", 3.0, day(8))]
    create_stds(tools, "strds", "w_instant", maps)
    return "w_instant"


@pytest.mark.parametrize(
    ("method", "sampling"),
    [
        ("instant", "related"),
        # equal relates no map to a granule, the instant included, and the
        # instant is refused all the same.
        ("instant", "equal"),
        ("minimum", "related"),
        ("maximum", "related"),
        ("range", "related"),
        ("min_raster", "related"),
        ("max_raster", "related"),
        ("diversity", "related"),
        ("count", "related"),
        ("slope", "related"),
        ("offset", "related"),
        ("detcoeff", "related"),
    ],
)
def test_weighted_refusals(tools, weekly, with_instant, method, sampling):
    if method == "instant":
        input_, method = with_instant, "average"
        expected = "the map <wi1@"
    else:
        input_ = weekly
        # The methods that the flag takes, in the order of the option.
        expected = (
            f"The method <{method}> cannot be weighted by temporal overlap; use "
            "the flag -w with one of: average, median, mode, stddev, sum, "
            "variance, quart1, quart3, perc90, quantile, skewness, kurtosis"
        )
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=input_,
            output="w_refused",
            basename="w_refused",
            granularity="10 days",
            method=method,
            sampling=sampling,
            flags="w",
        )
    assert expected in message(error.value)
    # No dataset and no map: the refusal comes before the first write.
    assert inventory(tools) == before
