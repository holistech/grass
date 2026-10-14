"""Characterization of t.rast.aggregate.ds before the port

Every expected value was measured on 2026-10-14 with the unchanged tool
(build d8f948a911) in a temporary XY project, with t.rast.list. These tests
are the first pytest coverage of t.rast.aggregate.ds, which had only a shell
script. They passed before the port, except for two documented changes of
the port that the -n test and the relation order test assert in their
corrected form (see their docstrings).
"""

import pytest


@pytest.fixture
def read(aggregate_ds_data):
    return aggregate_ds_data.read


def test_strds_sampler_values(read):
    """The daily sampler intervals aggregate m1 and m2; the day 3 interval
    holds only null maps and averages to an all null map. Each output map
    takes the extent of its sampler interval, so the day 3 map ends on
    2001-01-04. The values were measured before the -n fix, when the default
    kept the all null map; -n now keeps it, hence the flag."""
    rows = read.rows_after(
        "a_strds",
        input="input",
        sample="samp",
        type="strds",
        method="average",
        flags="n",
    )
    assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
        ("a_strds_2001_01_01", "2001-01-01 00:00:00", "2001-01-02 00:00:00", "1.0"),
        ("a_strds_2001_01_02", "2001-01-02 00:00:00", "2001-01-03 00:00:00", "2.0"),
        ("a_strds_2001_01_03", "2001-01-03 00:00:00", "2001-01-04 00:00:00", "None"),
    ]


def test_stvds_sampler(read):
    """A vector sampler is accepted: only its time stamps form the grid, the
    aggregated maps are the raster input (sum, sampling=contains). The
    intervals are uneven and the output maps take them over unchanged. The
    offset has no effect here: it is added only to numeric suffixes, and the
    default suffix is the granularity date."""
    rows = read.rows_after(
        "a_stvds",
        input="precip",
        sample="vsoil",
        type="stvds",
        method="sum",
        sampling="contains",
        offset=33,
    )
    assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
        ("a_stvds_2001_01", "2001-01-01 00:00:00", "2001-04-01 00:00:00", "100.0"),
        ("a_stvds_2001_05", "2001-05-01 00:00:00", "2001-07-01 00:00:00", "500.0"),
        ("a_stvds_2001_08", "2001-08-01 00:00:00", "2001-12-01 00:00:00", "100.0"),
    ]


def test_n_flag_registers_the_all_null_granule(read):
    """-n keeps null maps and the default drops them, as in t.rast.aggregate
    and as the help text promises. Before the tool moved onto the algebra
    core this was inverted; see the git history of this test."""
    without = read.aggregate(
        "ds_no", input="input", sample="samp", type="strds", method="average"
    )
    assert without == ["ds_no_2001_01_01", "ds_no_2001_01_02"]
    with_n = read.aggregate(
        "ds_n", input="input", sample="samp", type="strds", method="average", flags="n"
    )
    assert with_n == ["ds_n_2001_01_01", "ds_n_2001_01_02", "ds_n_2001_01_03"]


def test_numeric_suffix_with_offset_and_sampler_gap(read):
    """The sampler interval of day 2 relates to no map of gapin (g1 on day 1,
    g3 on day 3). It produces no map, but its number is used up, so the
    numbering continues after the gap: the offset 10 gives 11 and 13 and the
    day 3 map is not renumbered to 12. The output keeps the sampler extents."""
    rows = read.rows_after(
        "num",
        input="gapin",
        sample="samp",
        type="strds",
        method="sum",
        suffix="num%02",
        offset=10,
    )
    assert [(row[0], row[1], row[2], row[3]) for row in rows] == [
        ("num_11", "2001-01-01 00:00:00", "2001-01-02 00:00:00", "1.0"),
        ("num_13", "2001-01-03 00:00:00", "2001-01-04 00:00:00", "3.0"),
    ]


def test_related_maps_are_read_in_time_order(read):
    """The sampler interval 2001-01-01 .. 2001-01-11 contains ct (day 5 ..
    6) and overlaps ov1 (day 2 .. 15, the smaller value). min_raster returns
    the index of the smallest map among the related maps. The related maps
    are read as one union in time order, so ov1 (starts first) comes first
    and the index is 0. Before the tool moved onto the algebra core it
    concatenated the maps per relation in the order equal, contains, during,
    starts, started, finishes, finished, overlaps, overlapped, read ct then
    ov1 and returned 1 (measured 2026-10-14 with the unchanged tool, see the
    git history of this test). Only order dependent methods (min_raster,
    max_raster, slope, offset, detcoeff) with several listed relations are
    affected."""
    rows = read.rows_after(
        "ord",
        input="ordin",
        sample="osamp",
        type="strds",
        method="min_raster",
        sampling="overlaps,contains",
    )
    assert [(row[1], row[2], row[3]) for row in rows] == [
        ("2001-01-01 00:00:00", "2001-01-11 00:00:00", "0.0")
    ]
