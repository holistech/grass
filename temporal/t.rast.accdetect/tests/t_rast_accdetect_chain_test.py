"""Test t.rast.accdetect on the output of t.rast.accumulate

The scenarios of the old shell and gunittest suites. Six maps of two months
each from 2001-01-01 hold 5, 10, 15, 20, 25, 30 (or the reverse); the default
method of t.rast.accumulate adds the means up, so with the limits 10 and 25 the
accumulated values are 5, 15, 30, 50, 75, 105.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, intervals
from grass.temporal.testing.readback import list_maps, stds_info

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _rows(tools, name):
    return [
        (row.name, row.start, row.min, row.max)
        for row in list_maps(tools, "strds", name)
    ]


def _month(number):
    """The first of the month that is number months after January 2001 plus one"""
    return datetime(2001 + (number - 1) // 12, (number - 1) % 12 + 1, 1)


def _two_months(values):
    return [
        MapSpec(f"temp_{k}", value, _month(2 * k - 1), _month(2 * k + 1))
        for k, value in enumerate(values, 1)
    ]


@pytest.fixture
def accumulation(tools, request):
    """Function that makes the temperature dataset and its accumulation"""

    def make(values, prefix, **options):
        maps = [
            MapSpec(f"{prefix}_{spec.name}", spec.value, spec.start, spec.end)
            for spec in _two_months(values)
        ]
        create_stds(tools, "strds", f"{prefix}_temp", maps)
        tools.t_rast_accumulate(
            input=f"{prefix}_temp",
            output=f"{prefix}_acc",
            basename=f"{prefix}_acc",
            limits="10,25",
            start="2001-01-01",
            granularity="2 months",
            cycle="12 months",
            suffix="num%03",
            **options,
        )
        return f"{prefix}_acc"

    return make


def test_the_accumulation_of_the_old_shell_test(tools, accumulation):
    name = accumulation([5, 10, 15, 20, 25, 30], "fwd")

    assert _rows(tools, name) == [
        ("fwd_acc_001", "2001-01-01 00:00:00", 5.0, 5.0),
        ("fwd_acc_002", "2001-03-01 00:00:00", 15.0, 15.0),
        ("fwd_acc_003", "2001-05-01 00:00:00", 30.0, 30.0),
        ("fwd_acc_004", "2001-07-01 00:00:00", 50.0, 50.0),
        ("fwd_acc_005", "2001-09-01 00:00:00", 75.0, 75.0),
        ("fwd_acc_006", "2001-11-01 00:00:00", 105.0, 105.0),
    ]


def test_the_occurrence_of_the_old_shell_test(tools, accumulation):
    # The values 30, 50 and 75 lie between 20 and 80 (5, 15 and 105 do not):
    # the maps of 1 May, 1 July and 1 September, 120, 181 and 243 days after
    # 1 January (31 + 28 + 31 + 30, then 31 + 30 more, then 31 + 31 more).
    accumulation([5, 10, 15, 20, 25, 30], "occ")

    tools.t_rast_accdetect(
        input="occ_acc",
        occurrence="occ_out",
        basename="occ_out",
        range="20,80",
        start="2001-01-01",
        cycle="12 months",
        suffix="num%03",
    )

    assert _rows(tools, "occ_out") == [
        ("occ_out_003", "2001-05-01 00:00:00", 120.0, 120.0),
        ("occ_out_004", "2001-07-01 00:00:00", 181.0, 181.0),
        ("occ_out_005", "2001-09-01 00:00:00", 243.0, 243.0),
    ]


@pytest.fixture(scope="module")
def thresholds(tools):
    """Minimum 18 over eight months and maximum 78 over ten months, and 40"""
    for name, value, months in (
        ("chain_min", 18, 8),
        ("chain_max", 78, 10),
        ("chain_min40", 40, 8),
    ):
        create_stds(
            tools,
            "strds",
            name,
            [
                MapSpec(
                    f"{name}_map",
                    value,
                    datetime(2001, 1, 1),
                    datetime(2001 + months // 12, months % 12 + 1, 1),
                )
            ],
        )


def test_minimum_and_maximum_datasets_of_the_old_shell_test(
    tools, accumulation, thresholds
):
    # The minimum 18 holds for the accumulated maps up to 1 September, the
    # maximum 78 for those up to 1 November. 5 and 15 are below 18, 105 is
    # above the range maximum 80, so the occurrence is the one of the range
    # test; the indicator marks 1 May as start, 1 July in between and
    # 1 September as end.
    accumulation([5, 10, 15, 20, 25, 30], "mm")

    tools.t_rast_accdetect(
        input="mm_acc",
        occurrence="mm_occ",
        indicator="mm_ind",
        basename="mm",
        range="20,80",
        start="2001-01-01",
        cycle="12 months",
        minimum="chain_min",
        maximum="chain_max",
        staend="1,2,3",
        suffix="num%03",
    )

    assert _rows(tools, "mm_occ") == [
        ("mm_003", "2001-05-01 00:00:00", 120.0, 120.0),
        ("mm_004", "2001-07-01 00:00:00", 181.0, 181.0),
        ("mm_005", "2001-09-01 00:00:00", 243.0, 243.0),
    ]
    assert _rows(tools, "mm_ind") == [
        ("mm_indicator_003", "2001-05-01 00:00:00", 1.0, 1.0),
        ("mm_indicator_004", "2001-07-01 00:00:00", 2.0, 2.0),
        ("mm_indicator_005", "2001-09-01 00:00:00", 3.0, 3.0),
    ]


def test_a_higher_minimum_dataset_removes_the_first_maps(
    tools, accumulation, thresholds
):
    # With the minimum 40 up to 1 September, 30 on 1 May is out: the
    # occurrence stays on 1 July (50) and 1 September (75, the minimum 20 of
    # the range applies after the dataset ended and the maximum 78 holds).
    # The indicator starts on 1 July and ends on 1 September.
    accumulation([5, 10, 15, 20, 25, 30], "mm40")

    tools.t_rast_accdetect(
        input="mm40_acc",
        occurrence="mm40_occ",
        indicator="mm40_ind",
        basename="mm40",
        range="20,80",
        start="2001-01-01",
        cycle="12 months",
        minimum="chain_min40",
        maximum="chain_max",
        suffix="num%03",
    )

    assert [(row[1][:10], row[2]) for row in _rows(tools, "mm40_occ")] == [
        ("2001-07-01", 181.0),
        ("2001-09-01", 243.0),
    ]
    assert [(row[0], row[2]) for row in _rows(tools, "mm40_ind")] == [
        ("mm40_indicator_004", 1.0),
        ("mm40_indicator_005", 3.0),
    ]


def test_the_reverse_scenario_of_the_old_shell_test(tools, accumulation):
    # The temperatures fall (30 to 5) and both tools run with -r. The
    # accumulation starts at the last map, so the first map of the dataset
    # holds the total 105 and the numbering of the names counts from the end.
    name = accumulation([30, 25, 20, 15, 10, 5], "rv", flags="r")

    assert _rows(tools, name) == [
        ("rv_acc_006", "2001-01-01 00:00:00", 105.0, 105.0),
        ("rv_acc_005", "2001-03-01 00:00:00", 75.0, 75.0),
        ("rv_acc_004", "2001-05-01 00:00:00", 50.0, 50.0),
        ("rv_acc_003", "2001-07-01 00:00:00", 30.0, 30.0),
        ("rv_acc_002", "2001-09-01 00:00:00", 15.0, 15.0),
        ("rv_acc_001", "2001-11-01 00:00:00", 5.0, 5.0),
    ]

    tools.t_rast_accdetect(
        input=name,
        occurrence="rv_occ",
        indicator="rv_ind",
        basename="rv_occ",
        range="20,80",
        start="2001-01-01",
        cycle="12 months",
        staend="1,2,3",
        suffix="num%03",
        flags="r",
    )

    # 75, 50 and 30 are in the range: 1 March (59 days), 1 May (120), 1 July
    # (181). Reading from the end, 1 July starts the run (1) and 1 March ends
    # it (3).
    assert _rows(tools, "rv_occ") == [
        ("rv_occ_005", "2001-03-01 00:00:00", 59.0, 59.0),
        ("rv_occ_004", "2001-05-01 00:00:00", 120.0, 120.0),
        ("rv_occ_003", "2001-07-01 00:00:00", 181.0, 181.0),
    ]
    assert _rows(tools, "rv_ind") == [
        ("rv_occ_indicator_005", "2001-03-01 00:00:00", 3.0, 3.0),
        ("rv_occ_indicator_004", "2001-05-01 00:00:00", 2.0, 2.0),
        ("rv_occ_indicator_003", "2001-07-01 00:00:00", 1.0, 1.0),
    ]


@pytest.fixture(scope="module")
def monthly(tools):
    """Thirty maps of the value 5, one per month from 2001-01"""
    create_stds(
        tools,
        "strds",
        "monthly",
        [
            MapSpec(f"mon_{k}", 5, start, end)
            for k, (start, end) in enumerate(intervals(30), 1)
        ],
    )


# Day of the year of the first of each month in 2001 and 2002 (no leap years)
# and of the first six months of 2003; the cycle of 12 months counts from the
# first of January.
DAYS = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]


def test_every_map_of_the_cycles_is_detected(tools, monthly):
    # All values (5) are in the range 1 to 8, so each of the 30 maps holds
    # the days since the start of its cycle: three cycles (2001, 2002, the six
    # months of 2003).
    tools.t_rast_accdetect(
        input="monthly",
        occurrence="mon_occ",
        indicator="mon_ind",
        basename="result",
        start="2001-01-01",
        cycle="12 months",
        range="1,8",
    )

    for name in ("mon_occ", "mon_ind"):
        info = stds_info(tools, "strds", name)
        assert info["semantic_type"] == "mean"
        assert info["start_time"] == "'2001-01-01 00:00:00'"
        assert info["end_time"] == "'2003-07-01 00:00:00'"
        assert info["granularity"] == "'1 month'"
        assert info["map_time"] == "interval"
        assert info["number_of_maps"] == 30
    assert [row[2] for row in _rows(tools, "mon_occ")] == [
        float(d) for d in DAYS
    ] * 2 + [float(d) for d in DAYS[:6]]


def test_stop_ends_the_last_cycle(tools, monthly):
    # Maps that start before 2002-12-31: the months of 2001 and 2002, 24 maps.
    tools.t_rast_accdetect(
        input="monthly",
        occurrence="stop_occ",
        indicator="stop_ind",
        basename="stop",
        start="2001-01-01",
        stop="2002-12-31",
        cycle="12 months",
        range="1,8",
    )

    for name in ("stop_occ", "stop_ind"):
        info = stds_info(tools, "strds", name)
        assert info["semantic_type"] == "mean"
        assert info["start_time"] == "'2001-01-01 00:00:00'"
        assert info["end_time"] == "'2003-01-01 00:00:00'"
        assert info["granularity"] == "'1 month'"
        assert info["map_time"] == "interval"
        assert info["number_of_maps"] == 24


def test_time_suffix_of_both_datasets(tools, monthly, existing):
    tools.t_rast_accdetect(
        input="monthly",
        occurrence="tsuf_occ",
        indicator="tsuf_ind",
        basename="result_time",
        start="2001-01-01",
        cycle="12 months",
        suffix="time",
        range="1,8",
    )

    assert existing(
        [
            "result_time_2001_01",
            "result_time_2001_01_01T00_00_00",
            "result_time_indicator_2001_01",
            "result_time_indicator_2001_01_01T00_00_00",
        ]
    ) == [False, True, False, True]


def test_numeric_suffix_of_both_datasets(tools, monthly, existing):
    tools.t_rast_accdetect(
        input="monthly",
        occurrence="nsuf_occ",
        indicator="nsuf_ind",
        basename="result_num",
        start="2001-01-01",
        cycle="12 months",
        suffix="count%03",
        range="1,8",
    )

    assert existing(
        [
            "result_num_2001_01",
            "result_num_001",
            "result_num_00001",
            "result_num_indicator_2001_01",
            "result_num_indicator_001",
            "result_num_indicator_00001",
        ]
    ) == [False, True, False, False, True, False]
