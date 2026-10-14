"""Characterization of t.rast.mapcalc before it is rebuilt on the algebra core

The min/max and the values of the temporal functions below were measured on
2026-10-14 with the unchanged tool on the mapcalc_session fixture
(prec_1..3 = rand(0, {550, 450, 320}), seed=1) in a temporary XY project.
t.rast.list prints min and max as a float with a trailing .0 even for integer
(CELL) maps, so the expected strings keep the .0. The time stamps follow the
fixture geometry. All of this must stay equal after the rebuild; there is no
classic switch for this tool.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

import grass.exceptions
from grass.tools import Tools


def _maps(tools, strds):
    """(numeric suffix, start, end, min, max) of each registered map, in order"""
    text = tools.t_rast_list(
        input=strds,
        columns="name,start_time,end_time,min,max",
        separator="|",
        flags="u",
    ).text
    rows = [line.split("|") for line in text.strip().splitlines()]
    return [(row[0].rsplit("_", 1)[-1], row[1], row[2], row[3], row[4]) for row in rows]


def test_two_inputs_equal_sampling_values(mapcalc_session):
    """precip_abs1 + precip_abs2 over the three identical granules"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="n",
        inputs="precip_abs1,precip_abs2",
        output="char_add",
        expression="precip_abs1 + precip_abs2",
        basename="char_add",
        method="equal",
        nprocs=3,
    )
    assert _maps(tools, "char_add") == [
        ("1", "2001-01-01 00:00:00", "2001-04-01 00:00:00", "20.0", "1098.0"),
        ("2", "2001-04-01 00:00:00", "2001-07-01 00:00:00", "28.0", "894.0"),
        ("3", "2001-07-01 00:00:00", "2001-10-01 00:00:00", "4.0", "638.0"),
    ]


def test_map_names_use_get_num_suffix(mapcalc_session):
    """The result maps are basename_1..basename_N, numbered from 1, the width
    taken from the count, as gs.get_num_suffix gives them"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="n",
        inputs="precip_abs1,precip_abs2",
        output="char_names",
        expression="precip_abs1 + precip_abs2",
        basename="nm",
        method="equal",
    )
    names = [
        row.split("|")[0]
        for row in tools.t_rast_list(input="char_names", columns="name", flags="u")
        .text.strip()
        .splitlines()
    ]
    assert names == ["nm_1", "nm_2", "nm_3"]


def test_null_result_maps_dropped_without_n(mapcalc_session, assert_tinfo):
    """A result that is all null is removed when -n is not given"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="s",
        inputs="precip_abs1,precip_abs2",
        output="char_null",
        expression="(precip_abs1 + precip_abs2) * null()",
        basename="char_null",
        method="equal",
    )
    assert_tinfo(tools, "char_null", {"number_of_maps": 0})


def test_null_result_maps_kept_with_n(mapcalc_session, assert_tinfo):
    """The same all-null result is kept when -n is given"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="sn",
        inputs="precip_abs1,precip_abs2",
        output="char_null",
        expression="(precip_abs1 + precip_abs2) * null()",
        basename="char_null",
        method="equal",
    )
    assert_tinfo(tools, "char_null", {"number_of_maps": 3})


def test_start_time_offsets(mapcalc_session):
    """start_time() is the day offset of each granule from the first start:
    0, 90, 181 days for the three three-month granules from 2001-01-01"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="n",
        inputs="precip_abs1",
        output="char_time",
        expression="start_time()",
        basename="char_time",
    )
    assert [row[3] for row in _maps(tools, "char_time")] == ["0.0", "90.0", "181.0"]


def test_td_and_end_functions_of_absolute_instants_are_null(
    mapcalc_session, assert_tinfo
):
    """For a dataset of time instances td(), end_time() and the end calendar
    functions are null, so a result that is only such a function is all null
    and dropped without -n"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for name in ("char_inst_1", "char_inst_2", "char_inst_3"):
        tools.r_mapcalc(expression=f"{name} = rand(0, 500)", seed=1)
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="char_inst",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_inst",
        maps="char_inst_1,char_inst_2,char_inst_3",
        start="2001-01-01",
        increment="1 day",
    )  # instances, no interval
    for function in ("td()", "end_time()", "end_doy()"):
        tools.t_rast_mapcalc(
            inputs="char_inst",
            output="char_inst_out",
            expression=function,
            basename="char_inst_out",
        )
        assert_tinfo(tools, "char_inst_out", {"number_of_maps": 0})


@pytest.mark.parametrize(
    "function",
    [
        "start_year()",
        "start_month()",
        "start_day()",
        "start_doy()",
        "start_dow()",
        "start_week()",
        "end_year()",
        "end_month()",
        "end_day()",
        "end_doy()",
    ],
)
def test_calendar_functions_run_on_absolute_time(
    mapcalc_session, assert_tinfo, function
):
    """Each calendar function yields a map for every granule on absolute time"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="precip_abs1",
        output="char_cal",
        expression=function,
        basename="char_cal",
    )
    assert_tinfo(tools, "char_cal", {"number_of_maps": 3})


def test_calendar_function_values(mapcalc_session):
    """start_month() over the three three-month granules is 1, 4, 7"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="precip_abs1",
        output="char_mon",
        expression="start_month()",
        basename="char_mon",
    )
    assert [row[3] for row in _maps(tools, "char_mon")] == ["1.0", "4.0", "7.0"]


def test_calendar_function_on_relative_time_is_fatal(mapcalc_session):
    """start_doy() on relative time stops with the 'absolute time' error"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for name in ("char_relc_1", "char_relc_2", "char_relc_3"):
        tools.r_mapcalc(expression=f"{name} = rand(0, 500)", seed=1)
    tools.t_create(
        type="strds",
        temporaltype="relative",
        output="char_relc",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_relc",
        maps="char_relc_1,char_relc_2,char_relc_3",
        start=0,
        increment=2,
        unit="days",
        flags="i",
    )
    with pytest.raises(grass.exceptions.CalledModuleError) as excinfo:
        tools.t_rast_mapcalc(
            inputs="char_relc",
            output="char_relc_out",
            expression="start_doy()",
            basename="char_relc_out",
        )
    assert "support only absolute time" in str(excinfo.value)


def test_td_on_relative_time(mapcalc_session):
    """td() on relative two-day intervals is 2"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for name in ("char_relt_1", "char_relt_2", "char_relt_3"):
        tools.r_mapcalc(expression=f"{name} = rand(0, 500)", seed=1)
    tools.t_create(
        type="strds",
        temporaltype="relative",
        output="char_relt",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_relt",
        maps="char_relt_1,char_relt_2,char_relt_3",
        start=0,
        increment=2,
        unit="days",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="char_relt",
        output="char_relt_out",
        expression="td()",
        basename="char_relt_out",
    )
    assert [row[3] for row in _maps(tools, "char_relt_out")] == ["2.0", "2.0", "2.0"]


@pytest.mark.parametrize(
    ("method", "expected"),
    [("equal", 3), ("during", 0), ("contain", 0), ("overlap", 0)],
)
def test_sampling_methods(mapcalc_session, assert_tinfo, method, expected):
    """precip_abs1 and precip_abs2 carry identical stamps: only 'equal' relates
    the maps; 'during', 'contain' and 'overlap' do not include equal and give
    no result map"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="n",
        inputs="precip_abs1,precip_abs2",
        output="char_meth",
        expression="precip_abs1 + precip_abs2",
        basename="char_meth",
        method=method,
    )
    assert_tinfo(tools, "char_meth", {"number_of_maps": expected})


def test_more_than_one_related_map_warns_and_uses_first(mapcalc_session):
    """Two input maps lie in one sampler granule: a warning is issued and the
    first (earliest start) is used. The warning goes to stderr, so the tool is
    run with consistent_return_value=True to get a result object."""
    tools = Tools(session=mapcalc_session, overwrite=True, consistent_return_value=True)
    tools.r_mapcalc(expression="char_one_s = rand(0, 550)", seed=1)
    tools.r_mapcalc(expression="char_one_a = rand(0, 450)", seed=1)
    tools.r_mapcalc(expression="char_one_b = rand(0, 320)", seed=1)
    # sampler: one three-month granule from 2001-01-01
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="char_s",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_s",
        maps="char_one_s",
        start="2001-01-01",
        increment="3 months",
        flags="i",
    )
    # input: two monthly maps that both lie during the granule
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="char_i",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_i",
        maps="char_one_a,char_one_b",
        start="2001-01-01",
        increment="1 month",
        flags="i",
    )
    result = tools.t_rast_mapcalc(
        inputs="char_s,char_i",
        output="char_first",
        expression="char_s + char_i",
        basename="char_first",
        method="contain",
    )
    stderr = result.stderr
    if isinstance(stderr, bytes):
        stderr = stderr.decode()
    assert "more than a single map" in stderr
    # contain relates both input maps; the first by start (char_one_a) is used,
    # so the result is char_one_s + char_one_a, with the same cell values as
    # prec_1 + prec_2 (min 120, max 986, measured 2026-10-14).
    rows = _maps(tools, "char_first")
    assert len(rows) == 1
    assert rows[0][3:] == ("120.0", "986.0")


def test_gaps_in_the_sampler_are_skipped(mapcalc_session, assert_tinfo):
    """A gap between two sampler maps is no granule and yields no result map"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.r_mapcalc(expression="char_gap_a = rand(0, 500)", seed=1)
    tools.r_mapcalc(expression="char_gap_b = rand(0, 500)", seed=1)
    for name in ("char_gap_s", "char_gap_i"):
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output=name,
            title="t",
            description="t",
        )
        tools.t_register(
            type="raster",
            input=name,
            maps="char_gap_a",
            start="2001-01-01",
            end="2001-02-01",
        )
        tools.t_register(
            type="raster",
            input=name,
            maps="char_gap_b",
            start="2001-03-01",
            end="2001-04-01",
        )
    tools.t_rast_mapcalc(
        inputs="char_gap_s,char_gap_i",
        output="char_gap_out",
        expression="char_gap_s + char_gap_i",
        basename="char_gap_out",
        method="equal",
    )
    assert_tinfo(tools, "char_gap_out", {"number_of_maps": 2})


def test_operand_order_does_not_matter(mapcalc_session, assert_tinfo):
    """Dataset names are substituted textually, one name after the other.
    precip_abs1 and precip_abs2 have the same length and neither contains the
    other, so the expression may name them in any order and still computes
    over all three granules."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        flags="n",
        inputs="precip_abs1,precip_abs2",
        output="char_sub",
        expression="precip_abs2 + precip_abs1",
        basename="char_sub",
        method="equal",
    )
    assert_tinfo(tools, "char_sub", {"number_of_maps": 3})
    assert [row[3:] for row in _maps(tools, "char_sub")] == [
        ("20.0", "1098.0"),
        ("28.0", "894.0"),
        ("4.0", "638.0"),
    ]


def test_substring_substitution_hazard(mapcalc_session):
    """The first input is substituted first, the others in reverse sorted
    order. If the first input's name is a prefix of a later one (pa and pa2),
    pa is replaced inside pa2 and the expression names the nonexistent map
    prec_12, so the tool aborts. With the longer name first it works. Measured
    2026-10-14 on the unchanged tool in a temporary XY project. This pins a
    defect; a rebuild that removes it changes this test on purpose."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for name in ("char_pa", "char_pa2"):
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output=name,
            title="t",
            description="t",
        )
        tools.t_register(
            type="raster",
            input=name,
            maps="prec_1,prec_2,prec_3",
            start="2001-01-01",
            increment="3 months",
            flags="i",
        )
    with pytest.raises(grass.exceptions.CalledModuleError):
        tools.t_rast_mapcalc(
            flags="n",
            inputs="char_pa,char_pa2",
            output="char_hz",
            expression="char_pa + char_pa2",
            basename="char_hz",
            method="equal",
        )
    tools.t_rast_mapcalc(
        flags="n",
        inputs="char_pa2,char_pa",
        output="char_hz",
        expression="char_pa + char_pa2",
        basename="char_hz",
        method="equal",
    )
    assert [row[3:] for row in _maps(tools, "char_hz")] == [
        ("20.0", "1098.0"),
        ("28.0", "894.0"),
        ("4.0", "638.0"),
    ]


def test_semantic_label_of_the_sampled_map_is_transferred(mapcalc_session):
    """Each result map takes the semantic label of the map it was sampled from.
    The maps are the tool's own, so the shared fixture rasters stay unlabeled."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for name in ("char_lab_1", "char_lab_2"):
        tools.r_mapcalc(expression=f"{name} = 5")
        tools.r_support(map=name, semantic_label="S2_1")
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="char_lab",
        title="t",
        description="t",
    )
    tools.t_register(
        type="raster",
        input="char_lab",
        maps="char_lab_1,char_lab_2",
        start="2001-01-01",
        increment="1 month",
        flags="i",
    )
    tools.t_rast_mapcalc(
        inputs="char_lab",
        output="char_lab_out",
        expression="char_lab * 2",
        basename="char_lab_out",
    )
    text = tools.t_rast_list(
        input="char_lab_out", columns="name,semantic_label", separator="|", flags="u"
    ).text
    assert text.strip().splitlines() == ["char_lab_out_1|S2_1", "char_lab_out_2|S2_1"]
