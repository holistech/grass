"""Characterization of t.rast.aggregate.ds before the port

Every expected value was measured on 2026-10-14 with the unchanged tool
(build d8f948a911) in a temporary XY project, with t.rast.list. These tests
are the first pytest coverage of t.rast.aggregate.ds, which had only a shell
script. They passed before the port, except for three documented changes of
the port: the -n test and the relation order test assert the corrected
behavior, and test_strds_sampler_values passes flags="n" for the same
reason (see their docstrings).
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
    core this was inverted; see the git history of this test. The kept map
    has no minimum and maximum, the others hold the inputs 1 and 2, and
    without -n the dropped map does not remain as a raster map either."""
    without = read.aggregate(
        "ds_no", input="input", sample="samp", type="strds", method="average"
    )
    assert without == ["ds_no_2001_01_01", "ds_no_2001_01_02"]
    assert read.tools.g_list(type="raster", pattern="ds_no_*").text.split() == [
        "ds_no_2001_01_01",
        "ds_no_2001_01_02",
    ]
    rows = read.rows_after(
        "ds_n", input="input", sample="samp", type="strds", method="average", flags="n"
    )
    assert [(row[0], row[3], row[4]) for row in rows] == [
        ("ds_n_2001_01_01", "1.0", "1.0"),
        ("ds_n_2001_01_02", "2.0", "2.0"),
        ("ds_n_2001_01_03", "None", "None"),
    ]
    assert read.tools.g_list(type="raster", pattern="ds_n_*").text.split() == [
        "ds_n_2001_01_01",
        "ds_n_2001_01_02",
        "ds_n_2001_01_03",
    ]


def test_instants_are_collected_by_contains(read):
    """The maps of the instants dataset have no end time. The sampler
    interval of day 1 contains pp1 and pp2, so the sum is 10 + 20 = 30. pp3
    lies exactly on the start of day 3 and the intervals are closed at the
    start, so day 3 holds it (30) and day 2 relates to no map and produces
    none. pp4 on day 5 lies outside every interval. The output keeps the
    sampler extents (derived from the inputs, confirmed 2026-10-14 with the
    unchanged tool in a temporary XY project)."""
    rows = read.rows_after(
        "inst_c",
        input="instants",
        sample="samp",
        type="strds",
        method="sum",
        sampling="contains",
    )
    assert [(row[0], row[1], row[2], row[3], row[4]) for row in rows] == [
        (
            "inst_c_2001_01_01",
            "2001-01-01 00:00:00",
            "2001-01-02 00:00:00",
            "30.0",
            "30.0",
        ),
        (
            "inst_c_2001_01_03",
            "2001-01-03 00:00:00",
            "2001-01-04 00:00:00",
            "30.0",
            "30.0",
        ),
    ]


def test_instants_never_overlap_an_interval(read):
    """An instant has no extent that could overlap an interval, so
    sampling=overlaps relates no map at all. The tool then ends with return
    code 0, prints no error and creates no output dataset (measured
    2026-10-14 with the unchanged tool in a temporary XY project: exit code 0
    and t.list shows no output dataset). The silence is documented here, not
    endorsed."""
    result = read.refused(
        "inst_o",
        input="instants",
        sample="samp",
        type="strds",
        method="sum",
        sampling="overlaps",
    )
    assert result.returncode == 0
    assert "ERROR" not in result.stderr
    listing = read.tools.t_list(type="strds", columns="name").text.split()
    assert any(name.startswith("instants") for name in listing)
    assert not [name for name in listing if name.startswith("inst_o")]


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


def test_existing_output_without_overwrite_prints_one_error(read):
    """The classic tool printed the refusal once. With the messenger in raise
    mode the message was printed by the library and again by the tool's own
    handler (measured 2026-10-14: two identical ERROR lines)."""
    options = {"input": "input", "sample": "samp", "type": "strds", "method": "sum"}
    read.aggregate("twice", **options)
    result = read.refused("twice", **options)
    assert result.returncode != 0
    errors = [line for line in result.stderr.splitlines() if line.startswith("ERROR")]
    assert len(errors) == 1
    assert "twice" in errors[0]
