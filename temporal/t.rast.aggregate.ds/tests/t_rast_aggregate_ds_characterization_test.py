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
    holds only null maps and averages to an all null map"""
    rows = read.rows_after(
        "a_strds", input="input", sample="samp", type="strds", method="average"
    )
    assert [(row[0], row[3]) for row in rows] == [
        ("a_strds_2001_01_01", "1.0"),
        ("a_strds_2001_01_02", "2.0"),
        ("a_strds_2001_01_03", "None"),
    ]


def test_stvds_sampler(read):
    """A vector sampler is accepted: only its time stamps form the grid, the
    aggregated maps are the raster input (sum, sampling=contains, offset=33)"""
    rows = read.rows_after(
        "a_stvds",
        input="precip",
        sample="vsoil",
        type="stvds",
        method="sum",
        sampling="contains",
        offset=33,
    )
    assert [(row[0], row[3]) for row in rows] == [
        ("a_stvds_2001_01", "100.0"),
        ("a_stvds_2001_05", "500.0"),
        ("a_stvds_2001_08", "100.0"),
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
