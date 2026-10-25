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


# Value and data type of the two day granule that holds m1=1 and m2=3.
# The values are derived from the inputs unless the entry says
# "measured": r.series interpolates quartiles and percentiles linearly
# between the sorted values, and slope, offset and detcoeff fit a line
# through (map index, value).
TWO_MAP_METHODS = {
    "average": (2.0, "DCELL"),
    "sum": (4.0, "DCELL"),
    "count": (2.0, "CELL"),
    "minimum": (1.0, "CELL"),
    "maximum": (3.0, "CELL"),
    "range": (2.0, "CELL"),
    "median": (2.0, "DCELL"),
    "stddev": (1.0, "DCELL"),
    "variance": (1.0, "DCELL"),
    # Both values occur once; c_mode (lib/stats/c_mode.c) replaces the mode
    # only when a count exceeds the maximum, so a tie keeps the smaller one.
    "mode": (1.0, "CELL"),
    # Zero based index of the smallest and the largest map in time order.
    "min_raster": (0.0, "CELL"),
    "max_raster": (1.0, "CELL"),
    # Number of distinct values.
    "diversity": (2.0, "CELL"),
    # Line through (0, 1) and (1, 3): slope 2, offset 1, perfect fit.
    "slope": (2.0, "DCELL"),
    "offset": (1.0, "DCELL"),
    "detcoeff": (1.0, "DCELL"),
    # 1 + 0.25 * 2, 1 + 0.75 * 2 and 1 + 0.9 * 2.
    "quart1": (1.5, "DCELL"),
    "quart3": (2.5, "DCELL"),
    "perc90": (2.8, "DCELL"),
    # t.rast.aggregate has no quantile option, so r.series uses quantile 0
    # (raster/r.series/main.c) and c_quant (lib/stats/c_percentile.c) returns
    # the smallest value.
    "quantile": (1.0, "DCELL"),
    # Symmetric values.
    "skewness": (0.0, "DCELL"),
    # Excess kurtosis of two points: 1 - 3.
    "kurtosis": (-2.0, "DCELL"),
}


@pytest.mark.parametrize("method", TWO_MAP_METHODS)
def test_two_map_granule_method_families(read, method):
    """A two day granule holds m1=1 and m2=3; the second holds only m3=5,
    which is copied, so every method keeps its CELL value 5"""
    value, datatype = TWO_MAP_METHODS[method]
    rows = read.aggregate(
        f"two_{method}", input="cells", granularity="2 days", method=method
    )
    assert [(row.start, row.end, row.min, row.max) for row in rows] == [
        ("2001-01-01 00:00:00", "2001-01-03 00:00:00", value, value),
        ("2001-01-03 00:00:00", "2001-01-05 00:00:00", 5.0, 5.0),
    ]
    assert read.datatype(rows[0].name) == datatype
    # The single map granule is copied with g.copy, so its CELL type
    # survives whatever the method is.
    assert read.datatype(rows[1].name) == "CELL"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
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


@pytest.mark.parametrize(
    ("dataset", "granularity", "suffix", "names", "ends"),
    [
        (
            "months",
            "1 months",
            "gran",
            ["2001_01", "2001_02", "2001_03"],
            ["2001-02-01", "2001-03-01", "2001-04-01"],
        ),
        (
            "months",
            "1 months",
            "time",
            ["2001_01_01T00_00_00", "2001_02_01T00_00_00", "2001_03_01T00_00_00"],
            ["2001-02-01", "2001-03-01", "2001-04-01"],
        ),
        (
            "hours",
            "1 hours",
            "gran",
            ["2001_01_01_06", "2001_01_01_07", "2001_01_01_08"],
            ["2001-01-01 07:00:00", "2001-01-01 08:00:00", "2001-01-01 09:00:00"],
        ),
        (
            "hours",
            "1 hours",
            "time",
            ["2001_01_01T06_00_00", "2001_01_01T07_00_00", "2001_01_01T08_00_00"],
            ["2001-01-01 07:00:00", "2001-01-01 08:00:00", "2001-01-01 09:00:00"],
        ),
    ],
)
def test_suffix_and_end_for_monthly_and_hourly_granules(
    read, dataset, granularity, suffix, names, ends
):
    """The month grid starts on the first of the month and the hour grid on
    the full hour; the first month map starts on day 10 and the hour maps on
    the hour, so only the month grid is moved. The gran suffix shortens to
    the unit of the granularity, the time suffix always has the full time. Measured
    2026-10-14 with t.rast.aggregate in a temporary XY project; the starts and
    ends follow from the unit of the granularity."""
    rows = read.aggregate(
        f"{dataset}_{suffix}",
        input=dataset,
        granularity=granularity,
        method="sum",
        suffix=suffix,
    )
    assert [row.name for row in rows] == [f"{dataset}_{suffix}_{n}" for n in names]
    assert [row.min for row in rows] == [1.0, 2.0, 3.0]
    assert [row.end.removesuffix(" 00:00:00") for row in rows] == ends


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("method", ["sum", "average", "count", "maximum"])
def test_output_dataset_attributes(read, aggregate_data, method):
    """The aggregation type is the method; title and description are copied
    from the input dataset (they read "cells", the output is named
    otherwise). Measured 2026-10-14 with t.info in a temporary XY project."""
    read.aggregate(f"attr_{method}", input="cells", granularity="2 days", method=method)
    info = read.tools.t_info(input=f"attr_{method}", flags="g").keyval
    assert info["aggregation_type"] == method
    assert info["number_of_maps"] == 2
    text = read.tools.t_info(input=f"attr_{method}").text
    assert "| Title:\n | cells\n" in text
    assert "| Description:\n | cells\n" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_output_copies_the_semantic_type_of_the_input(read):
    """The default is "mean", so only an input of another type shows the copy"""
    read.aggregate("sem", input="semantic", granularity="2 days", method="average")
    assert read.tools.t_info(input="sem", flags="g").keyval["semantic_type"] == "sum"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
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


def test_single_instant_granule_is_copied_with_value_and_type(read):
    """Each daily granule holds one instant, so sum copies it: the value is
    that of the input (not a sum over several maps) and CELL stays CELL"""
    rows = read.aggregate("ptv", input="instants", granularity="1 days", method="sum")
    assert [row.min for row in rows] == [1.0, 2.0, 3.0]
    assert [read.datatype(row.name) for row in rows] == ["CELL"] * 3


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
    p1 and p2 and sums to 3 + 5 + 7 + 1 + 2 = 18. The topology builder files
    a pair related by "starts" or "finishes" under "during" as well (see
    topology.py), so "during" also selects the maps
    that share the start or the end of the granule: p3 and p7 share the start
    of the first granule, p3 and p5 the end of the second. First granule:
    p3 [5,25] and p7 [5,20] share its start and run past its end; p5 [10,25],
    p1 [10,20] and p2 [12,18] start inside it and run past its end. Second
    granule: p3 and p5 share its end; p7, p1 and p2 start before it and end
    inside it. p10 [5,15] and p11 [15,25] equal a granule or only meet the
    other one, so the list leaves them out. Measured 2026-10-14 with the
    tool in a temporary XY project: "overlaps" and "overlapped" alone sum to
    8 and 10, "during" alone (and "starts" with "finishes") to 10 and 8."""
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


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
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


def test_sampling_list_keeps_the_maps_in_time_order(read):
    """min_raster returns the index of the smallest map among the related
    maps, so it shows their order. The grid ends at the end of the last
    map by start time (oa3, day 7), so it is the single granule [day 1,
    day 11]. oa1=5 [day 3, day 15] and oa2=1 [day 4, day 15] overlap it and
    oa3=9 [day 6, day 7] lies inside it; oz [day 1, day 30] shares its start
    and is not in the list. In time order the
    related maps are oa1, oa2, oa3, and the smallest, oa2, has index 1. The
    classic tool concatenated the maps per relation in the order equal,
    contains, during, starts, started, finishes, finished, overlaps,
    overlapped, so it read oa3, oa1, oa2 and returned 2 (measured 2026-10-14
    with the script of commit 91f4669c39 in a temporary XY project). The core
    reads one union in time order; the result differs only for order
    dependent methods such as min_raster, max_raster and slope."""
    rows = read.aggregate(
        "order",
        input="ordering",
        granularity="10 days",
        method="min_raster",
        sampling=["overlaps", "contains"],
    )
    assert [(row.start, row.min) for row in rows] == [("2001-01-01 00:00:00", 1.0)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_existing_output_without_overwrite_prints_one_error(read):
    """The classic tool printed the refusal once. With the messenger in raise
    mode the message was printed by the library and again by the tool's own
    handler (measured 2026-10-14: two identical ERROR lines)."""
    read.aggregate("twice", input="cells", granularity="1 days", method="sum")
    result = read.refused("twice", input="cells", granularity="1 days", method="sum")
    assert result.returncode != 0
    errors = [line for line in result.stderr.splitlines() if line.startswith("ERROR")]
    assert len(errors) == 1
    assert "twice" in errors[0]


def test_result_name_equal_to_an_input_map_stops_the_run(read, aggregate_data):
    """A result map named like an input map that no granule of the result
    reads still stops the run and leaves that map untouched.

    The input holds q on day 1, o_2001_01_03 (value 99) on days 2 to 3 and r
    on day 3. With a two day granularity the second granule is named
    o_2001_01_03 and reduces to r alone.
    """
    result = read.capturing_errors.t_rast_aggregate(
        input="clash",
        output="o2",
        basename="o",
        granularity="2 days",
        method="sum",
    )
    assert result.returncode != 0
    assert "o_2001_01_03" in result.stderr
    stats = read.tools.r_univar(map="o_2001_01_03", flags="g").keyval
    assert float(stats["max"]) == 99.0


def test_input_with_a_semantic_label_aggregates_only_those_maps(read):
    """input=name.label reads the maps with that label: day 1 has the maps of
    both labels, and the sum over the label A leaves out the map of label B."""
    rows = read.aggregate(
        "labeled_a", input="labeled.A", granularity="1 days", method="sum"
    )
    assert [(row.start, row.min) for row in rows] == [
        ("2001-01-01 00:00:00", 1.0),
        ("2001-01-02 00:00:00", 5.0),
    ]
