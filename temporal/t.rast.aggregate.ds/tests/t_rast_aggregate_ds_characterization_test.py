"""Characterization of t.rast.aggregate.ds before the port

Every expected value was measured on 2026-10-14 with the unchanged tool
(build d8f948a911) in a temporary XY project, with t.rast.list. These tests
are the first pytest coverage of t.rast.aggregate.ds, which had only a shell
script. They pass before the port; the -n test below pins the current,
inverted behaviour and is flipped in the port (see its docstring).
"""

import pytest


@pytest.fixture
def read(aggregate_ds_data):
    return aggregate_ds_data.read


def test_strds_sampler_values(read):
    """The daily sampler intervals aggregate m1 and m2; the day 3 interval
    holds only null maps and averages to an all null map. Each output map
    takes the extent of its sampler interval, so the day 3 map ends on
    2001-01-04"""
    rows = read.rows_after(
        "a_strds", input="input", sample="samp", type="strds", method="average"
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


def test_n_flag_is_inverted_before_the_fix(read):
    """Pins the behaviour of -n before the fix: t.rast.aggregate.ds passes
    register_null straight to delete_empty, so WITHOUT -n it keeps the all
    null day 3 map and WITH -n it deletes it, the opposite of the help text
    and of t.rast.aggregate. The move onto the algebra core fixes this, and
    this test then asserts the corrected behaviour.
    """
    without = read.aggregate(
        "ds_no", input="input", sample="samp", type="strds", method="average"
    )
    assert without == ["ds_no_2001_01_01", "ds_no_2001_01_02", "ds_no_2001_01_03"]
    with_n = read.aggregate(
        "ds_n", input="input", sample="samp", type="strds", method="average", flags="n"
    )
    assert with_n == ["ds_n_2001_01_01", "ds_n_2001_01_02"]


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


def test_related_maps_are_read_per_relation_before_the_port(read):
    """Pins the order in which the related maps reach an order dependent
    method before the port. The sampler interval 2001-01-01 .. 2001-01-11
    contains ct (day 5 .. 6) and overlaps ov1 (day 2 .. 15, the smaller
    value). min_raster returns the index of the smallest map among the related
    maps. In time order ov1 comes first and the index would be 0; the tool
    concatenates the maps per relation in the order equal, contains, during,
    starts, started, finishes, finished, overlaps, overlapped, so it reads ct
    then ov1 and returns 1. The move onto the algebra core reads one union in
    time order and this test then asserts 0."""
    rows = read.rows_after(
        "ord",
        input="ordin",
        sample="osamp",
        type="strds",
        method="min_raster",
        sampling="overlaps,contains",
    )
    assert [(row[1], row[2], row[3]) for row in rows] == [
        ("2001-01-01 00:00:00", "2001-01-11 00:00:00", "1.0")
    ]
