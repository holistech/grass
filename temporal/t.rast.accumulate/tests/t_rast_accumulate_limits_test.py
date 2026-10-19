"""Test the lower and upper datasets of t.rast.accumulate, and their defects

The input is the dataset acc_daily of seven daily maps with the values
5, 10, 20, 35, 20, 10, 5 from 2001-01-01. A threshold dataset applies to a
granule when its map lasts longer than the granule, and the run takes the
threshold of the granule from it. The expected sums are derived in the
comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

VALUES = [5, 10, 20, 35, 20, 10, 5]


def _text(offset):
    return day(offset).strftime("%Y-%m-%d %H:%M:%S")


@pytest.fixture(scope="module")
def daily(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "lim_daily",
        [MapSpec(f"lim_d{k}", v, day(k), day(k + 1)) for k, v in enumerate(VALUES)],
    )
    # Thresholds that change on the fourth day: 0 and 20 for the lower,
    # 15 and 40 for the upper dataset.
    for name, values in (("lim_lower", (0, 20)), ("lim_upper", (15, 40))):
        create_stds(
            tools,
            "strds",
            name,
            [
                MapSpec(f"{name}_a", values[0], day(0), day(3)),
                MapSpec(f"{name}_b", values[1], day(3), day(7)),
            ],
        )
    # One lower map equal in time to each input map, with the value 10.
    create_stds(
        tools,
        "strds",
        "lim_equal",
        [MapSpec(f"lim_e{k}", 10, day(k), day(k + 1)) for k in range(7)],
    )
    return "lim_daily"


def _accumulate(tools, output, **options):
    options = {
        "input": "lim_daily",
        "start": "2001-01-01",
        "cycle": "7 days",
        "limits": "0,40",
        "method": "gdd",
        **options,
    }
    tools.t_rast_accumulate(output=output, basename=output, **options)
    return [(row.start, row.min) for row in list_maps(tools, "strds", output)]


def _sums(*values):
    return [(_text(k), v) for k, v in enumerate(values)]


def test_a_lower_dataset_that_changes_over_time(tools, daily):
    # Days 1 to 3 use the lower value 0: increments 5, 10, 20. Days 4 to 7 use
    # 20: 35 - 20 = 15, then 0, 0, 0 (negative increments are 0).
    rows = _accumulate(tools, "lim_low", lower="lim_lower")

    assert rows == _sums(5, 15, 35, 50, 50, 50, 50)


def test_an_upper_dataset_that_changes_over_time(tools, daily, zero):
    # bedd with the lower limit 0 and the upper dataset 15 on days 1 to 3 and
    # 40 on days 4 to 7: min(value, upper) = 5 10 15 | 35 20 10 5.
    rows = _accumulate(
        tools, "lim_up", method="bedd", lower="lim_equal_zero", upper="lim_upper"
    )

    assert rows == _sums(5, 15, 30, 65, 85, 95, 100)


@pytest.fixture(scope="module")
def zero(tools, daily):
    create_stds(
        tools, "strds", "lim_equal_zero", [MapSpec("lim_zero", 0, day(0), day(7))]
    )


def test_a_lower_dataset_alone_uses_the_upper_limit(tools, daily):
    # Lower 10 from the dataset (above the limit 0), upper 30 from limits:
    # as bedd 10 to 30, sums 0 0 10 30 40 40 40.
    create_stds(
        tools, "strds", "lim_ten", [MapSpec("lim_ten_map", 10, day(0), day(10))]
    )

    rows = _accumulate(
        tools, "lim_alone", method="bedd", limits="0,30", lower="lim_ten"
    )

    assert rows == _sums(0, 0, 10, 30, 40, 40, 40)


def test_today_a_threshold_map_of_the_same_time_is_ignored(tools, daily):
    # The tool looks for the relations EQUALS, DURING, OVERLAPS, OVERLAPPING
    # and CONTAINS of the granule to the map of the threshold dataset. The
    # topology files equal times under EQUAL, so a map with the time of the
    # granule is never found and the limit applies: gdd with the lower limit
    # 0 gives the sums 5 15 35 70 90 100 105.
    rows = _accumulate(tools, "lim_eq_today", lower="lim_equal")

    assert rows == _sums(5, 15, 35, 70, 90, 100, 105)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accumulate ignores a threshold map of the same time, it looks for EQUALS but the topology files equal times under EQUAL",
)
def test_a_threshold_map_of_the_same_time_is_used(tools, daily):
    # The lower map 10 gives the increments 0 0 10 25 10 0 0, the sums
    # 0 0 10 35 45 45 45.
    rows = _accumulate(tools, "lim_eq", lower="lim_equal")

    assert rows == _sums(0, 0, 10, 35, 45, 45, 45)


@pytest.fixture(scope="module")
def half_day_lower(tools, daily):
    """A lower limit of 10 from the noon of day 2 to the noon of day 3

    The granule of day 2 overlaps the map, the map overlaps the granule of
    day 3; the manual names both relations, overlaps and overlapped.
    """
    create_stds(
        tools,
        "strds",
        "lim_half",
        [MapSpec("lim_half_map", 10, day(2, hours=12), day(3, hours=12))],
    )
    return "lim_half"


def test_today_a_threshold_map_that_the_granule_overlaps_last_is_ignored(
    tools, half_day_lower
):
    # The tool looks for OVERLAPPING, the topology files the relation under
    # OVERLAPPED. Day 2 finds the lower 10 (increment 20 - 10 = 10), day 3
    # does not and takes the limit 0 (increment 35): sums 5 15 25 60 80 90 95.
    rows = _accumulate(tools, "lim_ov_today", lower=half_day_lower)

    assert rows == _sums(5, 15, 25, 60, 80, 90, 95)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accumulate ignores a threshold map that the granule overlaps last, it looks for OVERLAPPING but the topology files OVERLAPPED",
)
def test_a_threshold_map_that_the_granule_overlaps_last_is_used(tools, half_day_lower):
    # Day 3 takes the lower 10 as well: increment 25, sums 5 15 25 50 70 80 85.
    rows = _accumulate(tools, "lim_ov", lower=half_day_lower)

    assert rows == _sums(5, 15, 25, 50, 70, 80, 85)


def test_today_the_reverse_flag_takes_the_threshold_of_another_day(tools, daily):
    # With -r the tool computes the last day first but reads the threshold
    # of the granule at the same position of the list in time order. The
    # lower values (0 on the days 1 to 3, 20 on the days 4 to 7) are read for
    # the days 1 2 3 4 5 6 7 when the steps work on the days 7 6 5 4 3 2 1:
    #   step day 7 (lower of day 1: 0): 5          sum 5
    #   step day 6 (lower of day 2: 0): 10         sum 15
    #   step day 5 (lower of day 3: 0): 20         sum 35
    #   step day 4 (lower of day 4: 20): 35 - 20   sum 50
    #   step day 3 (lower of day 5: 20): 0         sum 50
    #   step day 2 (lower of day 6: 20): 0         sum 50
    #   step day 1 (lower of day 7: 20): 0         sum 50
    rows = _accumulate(tools, "lim_rev_today", lower="lim_lower", flags="r")

    assert rows == _sums(50, 50, 50, 50, 35, 15, 5)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accumulate -r reads the threshold of the mirrored day, the list in time order is indexed from the wrong end",
)
def test_the_reverse_flag_takes_the_threshold_of_the_day(tools, daily):
    # Each step uses the lower value of its own day: day 7, 6, 5 have 20 (all
    # increments 0), day 4 has 20 (15), days 3, 2, 1 have 0 (20, 10, 5), so
    # the sums by date are 50 45 35 15 0 0 0.
    rows = _accumulate(tools, "lim_rev", lower="lim_lower", flags="r")

    assert rows == _sums(50, 45, 35, 15, 0, 0, 0)


@pytest.fixture(scope="module")
def relative_threshold(tools, daily):
    create_stds(
        tools,
        "strds",
        "lim_relative",
        [MapSpec("lim_rel_map", 10, 0, 10)],
        temporaltype="relative",
        unit="days",
    )


def test_today_a_threshold_dataset_of_the_other_time_type_is_accepted(
    tools, relative_threshold
):
    # The tool means to refuse it, but compares the type of the dataset
    # before the dataset is read. No map of the dataset relates to a granule,
    # so the limits apply.
    rows = _accumulate(tools, "lim_rel_today", lower="lim_relative")

    assert rows == _sums(5, 15, 35, 70, 90, 100, 105)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accumulate accepts a threshold dataset of the other time type, the check compares the type before the dataset is read",
)
def test_a_threshold_dataset_of_the_other_time_type_is_refused(
    tools, relative_threshold
):
    with pytest.raises(ToolError) as error:
        _accumulate(tools, "lim_rel", lower="lim_relative")

    assert "Temporal type of input strds and lower strds must be equal" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("options", "text"),
    [
        (
            {"lower": "no_such_dataset"},
            "Space time raster dataset <no_such_dataset@PERMANENT> not found",
        ),
        (
            {"upper": "lim_lower"},
            "The upper option works only in conjunction with the lower option",
        ),
        (
            {"lower": "lim_lower", "upper": "no_such_dataset"},
            "Space time raster dataset <no_such_dataset@PERMANENT> not found",
        ),
    ],
    ids=["lower_unknown", "upper_alone", "upper_unknown"],
)
def test_the_refusals_of_the_threshold_datasets(request, tools, daily, options, text):
    with pytest.raises(ToolError) as error:
        _accumulate(tools, f"lim_err_{request.node.callspec.id}", **options)

    assert text in message(error.value)
