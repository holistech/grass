"""Test the statistics per granule of t.rast.univar: granularity and sampling

The maps are constant or hold a multiple of the column number on a region of
two rows and three columns, so every value below is derived by hand in the
comments. A map covers the six cells; a granule of k maps has 6 * k cells.
"""

import csv
import io
import json
from datetime import datetime
from pathlib import Path

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    intervals,
    register_stds,
    relative_intervals,
    small_region,
)
from grass.temporal.testing.readback import message
from grass.tools import ToolError

DATA = Path(__file__).with_name("data")
HEADER = [
    "id", "semantic_label", "start", "end", "non_null_cells", "null_cells", "min",
    "max", "range", "mean", "mean_of_abs", "stddev", "variance", "coeff_var", "sum",
    "sum_abs",
]  # fmt: skip
MEAN = HEADER.index("mean")
MONTHLY_IDS = [f"gm{number}@PERMANENT" for number in range(1, 7)]


def _first_quarter():
    return ",".join(MONTHLY_IDS[:3])


def _second_quarter():
    return ",".join(MONTHLY_IDS[3:])


def _csv_rows(result):
    return list(csv.reader(io.StringIO(result.stdout)))


def _plain_rows(result):
    return [line.split("|") for line in result.stdout.splitlines()[1:]]


def zoned_dataset(tools):
    """gz1 = col() over January, gz2 = 10 * col() over February, gz3 = 100 *
    col() over March 2001 in the dataset gr_zoned, and the zones map gr_zones =
    col(); returns the name of the dataset

    The test of the output without a granularity compares with a recording
    made from this function with the code before the granularity existed.
    """
    small_region(tools, 2, 3)
    months = intervals(3)
    create_stds(
        tools,
        "strds",
        "gr_zoned",
        [
            MapSpec(f"gz{number}", f"{factor} * col()", *months[number - 1])
            for number, factor in ((1, 1), (2, 10), (3, 100))
        ],
    )
    tools.r_mapcalc(expression="gr_zones = col()", overwrite=True)
    return "gr_zoned"


def relative_dataset(tools):
    """gr1 .. gr6 with the values 1 .. 6 from day 0 to day 6, one day each, in
    the relative dataset gr_relative; returns the name of the dataset"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "gr_relative",
        [
            MapSpec(f"gr{number}", number, start, end)
            for number, (start, end) in enumerate(relative_intervals(6), 1)
        ],
        temporaltype="relative",
        unit="days",
    )
    return "gr_relative"


@pytest.fixture(scope="module")
def monthly(tools):
    """gm1 .. gm6 with the values 1 .. 6 over January to June 2001, one month
    each, in the dataset gr_monthly"""
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "gr_monthly",
        [
            MapSpec(f"gm{number}", number, start, end)
            for number, (start, end) in enumerate(intervals(6), 1)
        ],
    )
    return "gr_monthly"


@pytest.fixture(scope="module")
def crossing(tools, monthly):
    """The six maps of gr_monthly and gx = 100 from 15 March to 15 April
    2001, across the border of two quarters, in the dataset gr_crossing"""
    tools.r_mapcalc(expression="gx = 100")
    register_stds(
        tools,
        "strds",
        "gr_crossing",
        [
            *(
                MapSpec(f"gm{number}", None, start, end)
                for number, (start, end) in enumerate(intervals(6), 1)
            ),
            MapSpec("gx", None, datetime(2001, 3, 15), datetime(2001, 4, 15)),
        ],
    )
    return "gr_crossing"


@pytest.fixture(scope="module")
def zoned(tools):
    return zoned_dataset(tools)


@pytest.fixture(scope="module")
def relative(tools):
    return relative_dataset(tools)


def test_granularity_three_months_contains(tools, monthly):
    result = tools.t_rast_univar(input=monthly, granularity="3 months")

    rows = _plain_rows(result)
    # The first map starts on 1 January, so the quarters start there. The
    # granule [January, April) contains gm1 .. gm3: 18 cells, the mean is
    # (1 + 2 + 3) * 6 / 18 = 2; [April, July) gm4 .. gm6: (4 + 5 + 6) / 3 = 5.
    assert [row[:4] for row in rows] == [
        [_first_quarter(), "", "2001-01-01 00:00:00", "2001-04-01 00:00:00"],
        [_second_quarter(), "", "2001-04-01 00:00:00", "2001-07-01 00:00:00"],
    ]
    assert [float(row[MEAN]) for row in rows] == [2, 5]
    assert [row[4] for row in rows] == ["18", "18"]


def test_map_across_a_boundary(tools, crossing):
    contains = _plain_rows(tools.t_rast_univar(input=crossing, granularity="3 months"))
    related = _plain_rows(
        tools.t_rast_univar(input=crossing, granularity="3 months", sampling="related")
    )

    # gx from 15 March to 15 April lies in neither quarter, so contains
    # leaves it out and the means stay 2 and 5.
    assert [row[0] for row in contains] == [_first_quarter(), _second_quarter()]
    assert [float(row[MEAN]) for row in contains] == [2, 5]
    # related takes gx into both quarters, after the maps that start before
    # it: (1 + 2 + 3 + 100) / 4 = 26.5 and (100 + 4 + 5 + 6) / 4 = 28.75.
    assert [row[0] for row in related] == [
        _first_quarter() + ",gx@PERMANENT",
        "gx@PERMANENT," + _second_quarter(),
    ]
    assert [float(row[MEAN]) for row in related] == [26.5, 28.75]


def test_granularity_relative_time(tools, relative):
    result = tools.t_rast_univar(input=relative, granularity=3, format="csv")

    rows = _csv_rows(result)[1:]
    # Granules [0, 3) and [3, 6) of days hold gr1 .. gr3 and gr4 .. gr6.
    assert [row[2:4] for row in rows] == [["0", "3"], ["3", "6"]]
    assert [float(row[MEAN]) for row in rows] == [2, 5]


def test_granularity_json(tools, monthly):
    result = tools.t_rast_univar(input=monthly, granularity="3 months", format="json")

    data = json.loads(result.stdout)
    assert [list(entry)[:3] for entry in data] == [["maps", "start", "end"]] * 2
    assert [(entry["maps"], entry["start"], entry["end"]) for entry in data] == [
        (MONTHLY_IDS[:3], "2001-01-01 00:00:00", "2001-04-01 00:00:00"),
        (MONTHLY_IDS[3:], "2001-04-01 00:00:00", "2001-07-01 00:00:00"),
    ]
    assert all("id" not in entry and "semantic_label" not in entry for entry in data)
    # The statistics keep the keys of r.univar: n is the number of cells.
    assert [(entry["n"], entry["mean"]) for entry in data] == [(18, 2), (18, 5)]


def test_granularity_csv_quotes_ids(tools, monthly):
    result = tools.t_rast_univar(input=monthly, granularity="3 months", format="csv")

    lines = result.stdout.splitlines()
    assert lines[1].startswith(f'"{_first_quarter()}",,2001-01-01 00:00:00,')
    rows = _csv_rows(result)
    assert rows[0] == HEADER
    assert [len(row) for row in rows[1:]] == [len(HEADER)] * 2
    assert [row[0] for row in rows[1:]] == [_first_quarter(), _second_quarter()]


def test_granularity_zones(tools, zoned):
    result = tools.t_rast_univar(
        input=zoned, granularity="2 months", zones="gr_zones", format="csv"
    )

    rows = _csv_rows(result)
    zone = rows[0].index("zone")
    assert rows[0][zone : zone + 2] == ["zone", "label"]
    columns = [rows[0].index(name) for name in ("non_null_cells", "min", "max")]
    columns += [rows[0].index(name) for name in ("mean", "sum")]
    # Zone c holds the two cells of column c. [January, March) contains gz1
    # (value c) and gz2 (10 * c): four cells c, c, 10c, 10c, so the mean is
    # 5.5 * c and the sum 22 * c. [March, May) contains gz3 alone: two cells
    # 100 * c, sum 200 * c.
    assert [[row[zone]] + [float(row[k]) for k in columns] for row in rows[1:]] == [
        ["1", 4, 1, 10, 5.5, 22],
        ["2", 4, 2, 20, 11, 44],
        ["3", 4, 3, 30, 16.5, 66],
        ["1", 2, 100, 100, 100, 200],
        ["2", 2, 200, 200, 200, 400],
        ["3", 2, 300, 300, 300, 600],
    ]
    assert [row[0] for row in rows[1:]] == ["gz1@PERMANENT,gz2@PERMANENT"] * 3 + [
        "gz3@PERMANENT"
    ] * 3


@pytest.mark.parametrize(
    ("options", "text"),
    [
        pytest.param(
            {"flags": "r", "granularity": "3 months"},
            "The region of each map (-r) cannot be used with a granularity",
            id="r_flag",
        ),
        pytest.param(
            {"sampling": "related"},
            "Option <sampling> requires <granularity>",
            id="sampling_without_granularity",
        ),
        pytest.param(
            {"separator": "comma", "granularity": "3 months"},
            "The format plain with the separator ',' cannot be used with a granularity",
            id="plain_with_comma",
        ),
        pytest.param(
            {"granularity": "0 months"},
            # The text of the shared check of the granularity, which
            # t.rast.aggregate gives for the same value.
            "The granularity '0 months' must be positive",
            id="zero_months",
        ),
    ],
)
def test_refusals(tools, monthly, tmp_path, options, text):
    output = tmp_path / "stats.txt"

    with pytest.raises(ToolError) as error:
        tools.t_rast_univar(input=monthly, output=str(output), **options)

    assert error.value.returncode != 0
    assert text in message(error.value)
    assert not output.exists()


def test_zero_months_has_the_text_of_t_rast_aggregate(tools, monthly):
    with pytest.raises(ToolError) as univar:
        tools.t_rast_univar(input=monthly, granularity="0 months")
    with pytest.raises(ToolError) as aggregate:
        tools.t_rast_aggregate(
            input=monthly,
            output="gr_never",
            basename="gr_never",
            granularity="0 months",
            method="average",
        )

    assert message(univar.value).endswith(message(aggregate.value))


def test_empty_granule_gives_no_row(tools, monthly):
    tools.r_mapcalc(expression="gm7 = 7")
    tools.r_mapcalc(expression="gm8 = 8")
    months = intervals(8)
    register_stds(
        tools,
        "strds",
        "gr_gap",
        [
            MapSpec(f"gm{number}", None, *months[number - 1])
            for number in (1, 2, 3, 7, 8)
        ],
    )

    rows = _plain_rows(tools.t_rast_univar(input="gr_gap", granularity="3 months"))

    # No map lies in the second quarter, so it gives no row. The third,
    # [July, October), holds gm7 and gm8: (7 + 8) / 2 = 7.5.
    assert [row[2:4] for row in rows] == [
        ["2001-01-01 00:00:00", "2001-04-01 00:00:00"],
        ["2001-07-01 00:00:00", "2001-10-01 00:00:00"],
    ]
    assert [float(row[MEAN]) for row in rows] == [2, 7.5]


def test_no_granule_with_a_map(tools, crossing, tmp_path):
    # gx alone, from 15 March to 15 April: the months start on 1 March, the
    # start of gx rounded down, and neither March nor April contains gx.
    output = tmp_path / "stats.txt"
    result = tools.t_rast_univar(
        input=crossing,
        granularity="1 month",
        where="name = 'gx'",
        output=str(output),
    )

    assert "No map is related to any granule" in message(result)
    assert not output.exists()
    result = tools.t_rast_univar(
        input=crossing, granularity="1 month", where="name = 'gx'", format="json"
    )
    assert json.loads(result.stdout) == []


def test_where_selects_before_the_granules(tools, crossing):
    # Without gm3, the first quarter holds gm1 and gm2 under related, and
    # gx: (1 + 2 + 100) / 3 = 34.333...
    rows = _plain_rows(
        tools.t_rast_univar(
            input=crossing,
            granularity="3 months",
            sampling="related",
            where="name != 'gm3'",
        )
    )

    assert rows[0][0] == "gm1@PERMANENT,gm2@PERMANENT,gx@PERMANENT"
    assert float(rows[0][MEAN]) == pytest.approx(103 / 3, rel=1e-12)


def test_nprocs_gives_the_same_output(tools, crossing):
    options = {"input": crossing, "granularity": "1 month", "sampling": "related"}

    assert (
        tools.t_rast_univar(nprocs=3, **options).stdout
        == tools.t_rast_univar(nprocs=1, **options).stdout
    )


def test_a_granule_without_statistics_warns(tools, monthly, broken_tools):
    # A stand-in r.univar that prints nothing and ends with 0.
    silent = broken_tools("r.univar", status=0)

    result = silent.t_rast_univar(input=monthly, granularity="3 months")

    assert (
        f"Unable to get statistics for the raster maps <{_first_quarter()}>"
        in message(result)
    )


RECORDED = {
    "plain": ("gr_zoned", {}),
    "plain_zones": ("gr_zoned", {"zones": "gr_zones"}),
    "csv_extended": ("gr_zoned", {"format": "csv", "flags": "e"}),
    "json": ("gr_zoned", {"format": "json"}),
    "json_zones": ("gr_zoned", {"format": "json", "zones": "gr_zones"}),
    "json_relative": ("gr_relative", {"format": "json"}),
    "plain_relative": ("gr_relative", {}),
}


@pytest.mark.parametrize("case", list(RECORDED))
def test_without_granularity_unchanged(tools, zoned, relative, case):
    # The outputs were recorded on 2026-11-10 with the tool and the library
    # of commit a061ece033, before the granularity existed, from
    # zoned_dataset() and relative_dataset(). Only the start of the first
    # map of the relative dataset differs from that recording: the JSON
    # wrote null for a start of 0, and the record now holds "0".
    recorded = json.loads(DATA.joinpath("without_granularity.json").read_text())
    name, options = RECORDED[case]

    assert tools.t_rast_univar(input=name, **options).stdout == recorded[case]
