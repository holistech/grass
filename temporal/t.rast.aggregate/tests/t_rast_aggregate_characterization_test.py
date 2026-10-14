"""Characterization of t.rast.aggregate before the port onto the algebra core

Every expected value was measured on 2026-10-14 with the unchanged tool
(build d8f948a911) in a temporary XY project, with t.rast.list
(columns name,start_time,end_time,min,max), r.info -g for the data type and
r.colors.out for the color table. These tests pass before the port and must
stay green after it.
"""

import pytest


@pytest.fixture
def read(aggregate_data):
    return aggregate_data.read


def test_two_map_granule_method_families(read):
    """A two day granule holds m1=1 and m2=3; the second holds only m3=5,
    which is copied, so every method keeps its CELL value 5"""
    expected = {
        "average": (2.0, "DCELL"),
        "sum": (4.0, "DCELL"),
        "count": (2.0, "CELL"),
        "minimum": (1.0, "CELL"),
        "maximum": (3.0, "CELL"),
        "range": (2.0, "CELL"),
        "median": (2.0, "DCELL"),
        "stddev": (1.0, "DCELL"),
        "variance": (1.0, "DCELL"),
    }
    for method, (value, datatype) in expected.items():
        rows = read.aggregate(
            f"two_{method}", input="cells", granularity="2 days", method=method
        )
        assert [(row.start, row.min, row.max) for row in rows] == [
            ("2001-01-01 00:00:00", value, value),
            ("2001-01-03 00:00:00", 5.0, 5.0),
        ]
        assert read.datatype(rows[0].name) == datatype
        # The single map granule is copied with g.copy, so its CELL type
        # survives whatever the method is.
        assert read.datatype(rows[1].name) == "CELL"


@pytest.mark.parametrize("method", ["average", "count", "sum"])
def test_single_map_granule_keeps_value_type_and_color(read, method):
    """A granule with one related map is copied verbatim: the method is
    ignored, and the value, the CELL type and the color table of the source
    survive"""
    rows = read.aggregate(
        f"one_{method}", input="cells", granularity="1 days", method=method
    )
    assert [(row.start, row.min) for row in rows] == [
        ("2001-01-01 00:00:00", 1.0),
        ("2001-01-02 00:00:00", 3.0),
        ("2001-01-03 00:00:00", 5.0),
    ]
    assert read.datatype(rows[0].name) == "CELL"
    assert read.first_color(rows[0].name) == "1 127:127:127"


def test_default_suffix_is_the_granularity_date(read):
    rows = read.aggregate("gran", input="cells", granularity="1 days", method="sum")
    assert [row.name for row in rows] == [
        "gran_2001_01_01",
        "gran_2001_01_02",
        "gran_2001_01_03",
    ]


def test_time_suffix(read):
    rows = read.aggregate(
        "iso", input="cells", granularity="1 days", method="sum", suffix="time"
    )
    assert rows[0].name == "iso_2001_01_01T00_00_00"


def test_numeric_suffix_with_offset(read):
    rows = read.aggregate(
        "num",
        input="cells",
        granularity="1 days",
        method="sum",
        suffix="num%02",
        offset=10,
    )
    assert [row.name for row in rows] == ["num_11", "num_12", "num_13"]
    rows = read.aggregate(
        "num3",
        input="cells",
        granularity="1 days",
        method="sum",
        suffix="num%03",
        offset=100,
    )
    assert rows[0].name == "num3_101"


def test_empty_middle_granule_leaves_a_numeric_gap(read):
    """m1 on day 1 and m3 on day 3 leave the day 2 granule empty; it produces
    no map and its number is skipped, so m3 keeps the gapped number 3"""
    rows = read.aggregate(
        "gap",
        input="cells",
        granularity="1 days",
        method="sum",
        suffix="num%02",
        where="start_time < '2001-01-02' or start_time >= '2001-01-03'",
    )
    assert [row.name for row in rows] == ["gap_01", "gap_03"]


def test_point_dataset_gets_a_final_granule(read):
    """Instants on days 1, 2 and 3 with a daily granularity give three maps;
    the last granule [day 3, day 4] covers the final instant"""
    rows = read.aggregate("pt", input="instants", granularity="1 days", method="sum")
    assert [(row.name, row.start, row.end) for row in rows] == [
        ("pt_2001_01_01", "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        ("pt_2001_01_02", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        ("pt_2001_01_03", "2001-01-03 00:00:00", "2001-01-04 00:00:00"),
    ]


def test_relative_time(read):
    rows = read.aggregate(
        "rel", input="relative", granularity=2, method="sum", suffix="num%02", offset=10
    )
    assert [(row.name, row.start, row.end, row.min) for row in rows] == [
        ("rel_11", "0", "2", 3.0),
        ("rel_12", "2", "4", 7.0),
    ]
    assert read.datatype(rows[0].name) == "DCELL"


def test_sampling_list(read):
    """The non-overlapping list of the gunittest suites; the granule grid is
    [day 5, day 15] and [day 15, day 25]. Each granule collects p3, p5, p7,
    p1 and p2 and sums to 3 + 5 + 7 + 1 + 2 = 18. First granule: p3 [5,25]
    and p7 [5,20] share its start and run past its end; p5 [10,25],
    p1 [10,20] and p2 [12,18] start inside it and run past its end. Second
    granule: p3 and p5 share its end; p7, p1 and p2 start before it and
    end inside it. p10 [5,15] and p11 [15,25] equal a granule or only meet
    the other one, so the list leaves them out."""
    rows = read.aggregate(
        "samp",
        input="probes",
        granularity="10 days",
        method="sum",
        sampling=["overlaps", "overlapped", "during"],
    )
    assert [(row.start, row.min) for row in rows] == [
        ("2001-01-05 00:00:00", 18.0),
        ("2001-01-15 00:00:00", 18.0),
    ]


def test_n_flag_registers_the_all_null_granule(read):
    """Without -n the all null day 3 granule is dropped; with -n it is kept"""
    without = read.aggregate(
        "noN", input="nulls", granularity="1 days", method="average"
    )
    assert [row.name for row in without] == ["noN_2001_01_01", "noN_2001_01_02"]
    with_n = read.aggregate(
        "withN", input="nulls", granularity="1 days", method="average", flags="n"
    )
    assert [row.name for row in with_n] == [
        "withN_2001_01_01",
        "withN_2001_01_02",
        "withN_2001_01_03",
    ]


def test_instant_last_map_adds_no_granule_after_it(read):
    """The last map is the instant tl_inst on day 3, the first one tl_long
    runs from day 1 to day 30. With a granularity of 10 days the grid has the
    single granule [day 1, day 11] that holds the instant. A second granule
    [day 11, day 21] would lie during tl_long, so the sampling list "during"
    would relate it and produce a second map; the tool stops the grid at the
    last instant and the classic granule loop did the same."""
    rows = read.aggregate(
        "tail", input="tail", granularity="10 days", method="sum", sampling=["during"]
    )
    assert [(row.start, row.min) for row in rows] == [("2001-01-01 00:00:00", 7.0)]


def test_file_limit_warning_only_when_r_series_runs(read):
    """With file_limit=0 every granule exceeds the limit, but the daily
    granules hold one map each and are copied with g.copy, so there is no
    warning. The two day granule of m1 and m2 runs r.series with flag z and
    warns once; the granule of m3 alone is copied again."""
    text = "limit of open files"
    assert text not in read.messages(
        "warn_one", input="cells", granularity="1 days", method="sum", file_limit=0
    )
    messages = read.messages(
        "warn_two", input="cells", granularity="2 days", method="sum", file_limit=1
    )
    assert messages.count(text) == 1

