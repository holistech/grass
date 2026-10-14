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


def _make_strds(tools, name, rows, temporaltype="absolute", unit=None):
    """Create STRDS name from constant rasters name_1..name_N

    rows holds (cell value, start, end) per map in registration order; an end
    of None registers a time instant. The rasters are the test's own because a
    raster can carry only one time stamp and the shared fixture rasters must
    keep theirs.
    """
    tools.t_create(
        type="strds",
        temporaltype=temporaltype,
        output=name,
        title="t",
        description="t",
    )
    for number, (value, start, end) in enumerate(rows, 1):
        map_name = f"{name}_{number}"
        tools.r_mapcalc(expression=f"{map_name} = {value}")
        options = {"type": "raster", "input": name, "maps": map_name, "start": start}
        if end is not None:
            options["end"] = end
        if unit is not None:
            options["unit"] = unit
        tools.t_register(**options)


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
    """Three granules give the result maps basename_1..basename_3, numbered
    from 1. The zero padding for ten or more granules is pinned separately."""
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
    """Two input maps lie in one sampler granule: a warning is issued and one
    of them is used. Here the map with the earliest start (char_one_a) is also
    the one registered first, so this test cannot tell the two orders apart;
    test_more_than_one_related_map_takes_the_earliest_start does. The result
    carries the time stamp of the sampler granule, not that of the used map.
    The warning goes to stderr, so the tool is run with
    consistent_return_value=True to get a result object."""
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
    # The sampler granule is three months long, the used map one month.
    assert rows[0][:3] == ("1", "2001-01-01 00:00:00", "2001-04-01 00:00:00")
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
    # The gap from 2001-02-01 to 2001-03-01 consumes no number and no map.
    assert [row[:3] for row in _maps(tools, "char_gap_out")] == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2", "2001-03-01 00:00:00", "2001-04-01 00:00:00"),
    ]


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
    <first map>2 (here char_src_12), so the tool aborts. With the longer name
    first it works. Measured 2026-10-14 on the unchanged tool in a temporary
    XY project. This pins a defect; a rebuild that removes it changes this
    test on purpose. The maps are the test's own, with the cell values of
    prec_1..3 (same rand call and seed), so the shared fixture is not
    re-registered."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for number, upper in [(1, 550), (2, 450), (3, 320)]:
        tools.r_mapcalc(expression=f"char_src_{number} = rand(0, {upper})", seed=1)
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
            maps="char_src_1,char_src_2,char_src_3",
            start="2001-01-01",
            increment="3 months",
            flags="i",
        )
    with pytest.raises(grass.exceptions.CalledModuleError) as excinfo:
        tools.t_rast_mapcalc(
            flags="n",
            inputs="char_pa,char_pa2",
            output="char_hz",
            expression="char_pa + char_pa2",
            basename="char_hz",
            method="equal",
        )
    assert "Invalid map <char_src_12>" in str(excinfo.value)
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


def test_map_names_are_zero_padded_to_the_count(mapcalc_session):
    """Ten granules give basename_01..basename_10: the suffix width follows
    the number of granules, as gs.get_num_suffix gives it"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    days = [f"2001-01-{day:02d}" for day in range(1, 12)]
    _make_strds(
        tools,
        "char_pad",
        [(number, days[number - 1], days[number]) for number in range(1, 11)],
    )
    tools.t_rast_mapcalc(
        inputs="char_pad",
        output="char_pad_out",
        expression="char_pad",
        basename="pad",
    )
    names = tools.t_rast_list(input="char_pad_out", columns="name", flags="u").text
    assert names.split() == [f"pad_{number:02d}" for number in range(1, 11)]


def test_more_than_one_related_map_takes_the_earliest_start(mapcalc_session):
    """Two input maps lie in the single three-month sampler granule
    2001-01-01 to 2001-04-01: char_mo_i_1 (value 10) is registered first but
    starts on 2001-02-01, char_mo_i_2 (value 100) is registered second but
    starts on 2001-01-01. The map with the earliest start is used, not the
    one registered first. Everything that depends on the time of the current
    sample comes from the sampler granule (90 days, ending on 2001-04-01), not
    from the used map (31 days, ending on 2001-02-01)."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(tools, "char_mo_s", [(1000, "2001-01-01", "2001-04-01")])
    _make_strds(
        tools,
        "char_mo_i",
        [(10, "2001-02-01", "2001-03-01"), (100, "2001-01-01", "2001-02-01")],
    )
    for expression, expected in [
        ("char_mo_s + char_mo_i", "1100.0"),
        ("char_mo_s + char_mo_i + end_month()", "1104.0"),
        ("td()", "90.0"),
        ("end_time()", "90.0"),
    ]:
        tools.t_rast_mapcalc(
            flags="n",
            inputs="char_mo_s,char_mo_i",
            output="char_mo_out",
            expression=expression,
            basename="char_mo_out",
            method="contain",
        )
        assert _maps(tools, "char_mo_out") == [
            ("1", "2001-01-01 00:00:00", "2001-04-01 00:00:00", expected, expected)
        ], expression


def test_sampler_granule_without_partner_is_skipped(mapcalc_session):
    """Of the three monthly sampler granules (2001-01-01 to 2001-04-01) the
    middle one has no partner in the second dataset, which holds only the
    first and the third month. The middle granule gives no map, but its number
    is used up, so the maps are numbered 1 and 3. With the two-granule dataset
    as the sampler, there is no hole and the maps are numbered 1 and 2; both
    time stamps and values are the same either way."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_np_s",
        [
            (1000, "2001-01-01", "2001-02-01"),
            (2000, "2001-02-01", "2001-03-01"),
            (3000, "2001-03-01", "2001-04-01"),
        ],
    )
    _make_strds(
        tools,
        "char_np_p",
        [(1, "2001-01-01", "2001-02-01"), (3, "2001-03-01", "2001-04-01")],
    )
    tools.t_rast_mapcalc(
        inputs="char_np_s,char_np_p",
        output="char_np_out",
        expression="char_np_s + char_np_p",
        basename="char_np_out",
    )
    assert _maps(tools, "char_np_out") == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", "1001.0", "1001.0"),
        ("3", "2001-03-01 00:00:00", "2001-04-01 00:00:00", "3003.0", "3003.0"),
    ]
    tools.t_rast_mapcalc(
        inputs="char_np_p,char_np_s",
        output="char_np_out",
        expression="char_np_s + char_np_p",
        basename="char_np_out",
    )
    assert _maps(tools, "char_np_out") == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", "1001.0", "1001.0"),
        ("2", "2001-03-01 00:00:00", "2001-04-01 00:00:00", "3003.0", "3003.0"),
    ]


def test_end_time_and_end_doy_of_intervals(mapcalc_session):
    """The three three-month granules from 2001-01-01 end on 2001-04-01,
    2001-07-01 and 2001-10-01: end_time() counts 90, 181 and 273 days from the
    first start (31 + 28 + 31, then + 30 + 31 + 30, then + 31 + 31 + 30), and
    end_doy() is the day of the year of the end, 91, 182 and 274."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    for expression, expected in [
        ("end_time()", ["90.0", "181.0", "273.0"]),
        ("end_doy()", ["91.0", "182.0", "274.0"]),
    ]:
        tools.t_rast_mapcalc(
            inputs="precip_abs1",
            output="char_end",
            expression=expression,
            basename="char_end",
        )
        rows = _maps(tools, "char_end")
        assert [row[1:3] for row in rows] == [
            ("2001-01-01 00:00:00", "2001-04-01 00:00:00"),
            ("2001-04-01 00:00:00", "2001-07-01 00:00:00"),
            ("2001-07-01 00:00:00", "2001-10-01 00:00:00"),
        ]
        assert [row[3] for row in rows] == expected, expression


def test_start_time_and_end_time_on_relative_time(mapcalc_session):
    """The relative granules 10 to 12, 12 to 14 and 14 to 16 days: start_time()
    and end_time() count from the first start (10), not from 0, so start_time()
    is 0, 2, 4 and end_time() is 2, 4, 6"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_rel",
        [(1, 10, 12), (1, 12, 14), (1, 14, 16)],
        temporaltype="relative",
        unit="days",
    )
    for expression, expected in [
        ("start_time()", ["0.0", "2.0", "4.0"]),
        ("end_time()", ["2.0", "4.0", "6.0"]),
    ]:
        tools.t_rast_mapcalc(
            inputs="char_rel",
            output="char_rel_out",
            expression=expression,
            basename="char_rel_out",
        )
        rows = _maps(tools, "char_rel_out")
        assert [row[1:3] for row in rows] == [("10", "12"), ("12", "14"), ("14", "16")]
        assert [row[3] for row in rows] == expected, expression


def test_start_time_of_absolute_instants(mapcalc_session):
    """Positive control for the instant tests: on three daily instances from
    2001-01-01, start_time() is 0, 1, 2 and gives three maps. The result maps
    are instances too, so they have no end time."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_instc",
        [(1, "2001-01-01", None), (2, "2001-01-02", None), (3, "2001-01-03", None)],
    )
    tools.t_rast_mapcalc(
        inputs="char_instc",
        output="char_instc_out",
        expression="start_time()",
        basename="char_instc_out",
    )
    assert _maps(tools, "char_instc_out") == [
        ("1", "2001-01-01 00:00:00", "None", "0.0", "0.0"),
        ("2", "2001-01-02 00:00:00", "None", "1.0", "1.0"),
        ("3", "2001-01-03 00:00:00", "None", "2.0", "2.0"),
    ]


@pytest.mark.parametrize("function", ["td()", "end_time()", "end_doy()"])
def test_null_functions_of_instants_are_kept_with_n(mapcalc_session, function):
    """With -n the all-null results of the functions that are null for time
    instances are registered, one per instance, without min and max"""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_instn",
        [(1, "2001-01-01", None), (2, "2001-01-02", None), (3, "2001-01-03", None)],
    )
    tools.t_rast_mapcalc(
        flags="n",
        inputs="char_instn",
        output="char_instn_out",
        expression=function,
        basename="char_instn_out",
    )
    assert _maps(tools, "char_instn_out") == [
        ("1", "2001-01-01 00:00:00", "None", "None", "None"),
        ("2", "2001-01-02 00:00:00", "None", "None", "None"),
        ("3", "2001-01-03 00:00:00", "None", "None", "None"),
    ]


# Sampler granules (start, end) of the per-method test, by number.
_METHOD_GRANULES = {
    1: ("2001-01-01", "2001-02-01"),
    2: ("2001-03-01", "2001-04-01"),
    3: ("2001-05-01", "2001-06-01"),
    4: ("2001-07-01", "2001-08-01"),
    5: ("2001-09-01", "2001-10-01"),
    6: ("2001-11-01", "2001-12-01"),
    7: ("2002-01-01", "2002-03-01"),
    8: ("2002-04-01", "2002-05-01"),
}


@pytest.fixture(scope="module")
def method_datasets(mapcalc_session):
    """Sampler char_ms with the eight granules in _METHOD_GRANULES and input
    char_mi with eight maps, map N (cell value N) related to granule N:

    1. equals granule 1
    2. 2001-03-10 to 2001-03-20, inside granule 2
    3. 2001-04-20 to 2001-06-10, covers granule 3
    4. 2001-07-20 to 2001-08-20, starts in granule 4 and ends after it
    5. 2001-10-01 to 2001-10-15, begins where granule 5 ends
    6. 2001-10-15 to 2001-11-01, ends where granule 6 begins
    7. 2002-01-01 to 2002-02-01, inside granule 7, sharing its start
    8. 2002-04-01 to 2002-07-01, covers granule 8, sharing its start

    Each map is related to its own granule only, so every granule has at most
    one partner and no "more than a single map" case arises.
    """
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_ms",
        [(1000 * number, *times) for number, times in _METHOD_GRANULES.items()],
    )
    _make_strds(
        tools,
        "char_mi",
        [
            (1, "2001-01-01", "2001-02-01"),
            (2, "2001-03-10", "2001-03-20"),
            (3, "2001-04-20", "2001-06-10"),
            (4, "2001-07-20", "2001-08-20"),
            (5, "2001-10-01", "2001-10-15"),
            (6, "2001-10-15", "2001-11-01"),
            (7, "2002-01-01", "2002-02-01"),
            (8, "2002-04-01", "2002-07-01"),
        ],
    )


@pytest.mark.parametrize(
    ("method", "granules"),
    [
        # Map and granule have the same extent.
        ("equal", [1]),
        # The map covers the granule: map 3 strictly, map 8 with a shared start.
        ("during", [3, 8]),
        # The map lies in the granule: map 2 strictly, map 7 with a shared start.
        ("contain", [2, 7]),
        # The map starts in the granule and ends after it.
        ("overlap", [4]),
        # Map 6 ends where granule 6 begins: "follows" names the granule's
        # relation to the map, so it selects the map that comes before it.
        ("follows", [6]),
        # Map 5 begins where granule 5 ends: "precedes" selects the map that
        # comes after the granule.
        ("precedes", [5]),
        # Map 2 and map 7 lie in their granule, map 8 starts together with
        # its granule and runs on. Granule 1 is missing although its map
        # starts with it: the method asks the sampling for "equals" while the
        # topology says "equal". Granule 4 is missing although its map starts
        # inside it and runs on; that was only measured, not derived.
        ("start", [2, 7, 8]),
    ],
)
def test_sampling_methods_take_the_related_map(
    mapcalc_session, method_datasets, method, granules
):
    """Per sampling method, which granules get a result and which map each
    one takes, told by the cell value N of the taken map. Result map numbers
    are the granule numbers, because the gaps between the granules consume no
    number. Measured 2026-10-14 on the unchanged tool; the geometry is in the
    method_datasets fixture."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="char_ms,char_mi",
        output="char_meth_out",
        expression="char_mi",
        basename="char_meth_out",
        method=method,
    )
    assert _maps(tools, "char_meth_out") == [
        (
            str(number),
            f"{_METHOD_GRANULES[number][0]} 00:00:00",
            f"{_METHOD_GRANULES[number][1]} 00:00:00",
            f"{number}.0",
            f"{number}.0",
        )
        for number in granules
    ]


_FIXTURE_REGION = {"s": 0, "n": 80, "w": 0, "e": 120, "b": 0, "t": 50, "res": 10}


def _map_in_region(tools, name, value, **region):
    """Create the constant raster name in the given region, then restore the
    fixture region that the other tests of the session rely on"""
    tools.g_region(**{**_FIXTURE_REGION, "res3": 10, **region})
    try:
        tools.r_mapcalc(expression=f"{name} = {value}")
    finally:
        tools.g_region(**_FIXTURE_REGION, res3=10)


def _stds_of_maps(tools, name, rows):
    """Create STRDS name from existing rasters; rows hold (map, start, end)"""
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=name,
        title="t",
        description="t",
    )
    for map_name, start, end in rows:
        tools.t_register(type="raster", input=name, maps=map_name, start=start, end=end)


def _exists(tools, name):
    return name in tools.t_list(type="strds", columns="name", format="plain").text


def test_first_related_map_follows_the_method_order(mapcalc_session):
    """The sampler granule 2001-01-01 to 2001-02-01 relates to two maps: char_fo_2
    (value 20) equal to it, and char_fo_1 (value 10), which starts a month
    earlier and ends a month later, so the granule lies during it. The map
    used is the first of the first relation that has one, relations taken in
    the order of the method list, not the one with the earliest start over
    all relations: method equal,during uses the equal map (21), during,equal
    the covering map (11). The granule has value 1. Measured 2026-10-14 on the
    unchanged tool with the probe of this geometry."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(tools, "char_fo_s", [(1, "2001-01-01", "2001-02-01")])
    for name, value in (("char_fo_1", 10), ("char_fo_2", 20)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    _stds_of_maps(
        tools,
        "char_fo_p",
        [
            ("char_fo_1", "2000-12-01", "2001-03-01"),
            ("char_fo_2", "2001-01-01", "2001-02-01"),
        ],
    )
    for method, expected in [("equal,during", "21.0"), ("during,equal", "11.0")]:
        tools.t_rast_mapcalc(
            inputs="char_fo_s,char_fo_p",
            output="char_fo_out",
            expression="char_fo_s + char_fo_p",
            basename="char_fo_out",
            method=method,
        )
        assert _maps(tools, "char_fo_out") == [
            ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", expected, expected)
        ], method


@pytest.fixture
def spatial_datasets(mapcalc_session):
    """Three monthly sampler granules a1..a3 (values 1, 2, 3) on the fixture
    region and three partners of equal time (values 10, 20, 30) with other
    extents: b1 touches the region at the corner (120, 80) only, b2 overlaps
    it, b3 lies far away. Outside its extent a partner is null in the
    computation region."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    months = [
        ("2001-01-01", "2001-02-01"),
        ("2001-02-01", "2001-03-01"),
        ("2001-03-01", "2001-04-01"),
    ]
    for number in (1, 2, 3):
        _map_in_region(tools, f"char_sp_a{number}", number)
    _map_in_region(tools, "char_sp_b1", 10, s=80, n=160, w=120, e=240)
    _map_in_region(tools, "char_sp_b2", 20, s=-40, n=40, w=60, e=180)
    _map_in_region(tools, "char_sp_b3", 30, s=900, n=980, w=1000, e=1120)
    _stds_of_maps(
        tools,
        "char_sp_a",
        [(f"char_sp_a{n}", *months[n - 1]) for n in (1, 2, 3)],
    )
    _stds_of_maps(
        tools,
        "char_sp_b",
        [(f"char_sp_b{n}", *months[n - 1]) for n in (1, 2, 3)],
    )
    return tools


def test_spatial_sampling_keeps_partners_that_touch(spatial_datasets):
    """With -s a partner is kept if its 2D extent intersects the granule's,
    touching included: the corner partner b1 and the overlapping b2 give maps,
    the far one b3 does not (so there is no third map). Where a partner is
    null in the computation region the expression uses 100, so the results are
    1 + 100 = 101 for b1 (no cell of b1 lies in the region), and for b2 the
    overlap 2 + 20 = 22 and elsewhere 102. Without -s all three granules
    give a map, the third 3 + 100 = 103. Measured 2026-10-14 on the unchanged
    tool."""
    tools = spatial_datasets
    expression = "char_sp_a + if(isnull(char_sp_b), 100, char_sp_b)"
    tools.t_rast_mapcalc(
        flags="s",
        inputs="char_sp_a,char_sp_b",
        output="char_sp_out",
        expression=expression,
        basename="char_sp_out",
        method="equal",
    )
    assert _maps(tools, "char_sp_out") == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", "101.0", "101.0"),
        ("2", "2001-02-01 00:00:00", "2001-03-01 00:00:00", "22.0", "102.0"),
    ]
    tools.t_rast_mapcalc(
        inputs="char_sp_a,char_sp_b",
        output="char_sp_out",
        expression=expression,
        basename="char_sp_out",
        method="equal",
    )
    assert _maps(tools, "char_sp_out") == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", "101.0", "101.0"),
        ("2", "2001-02-01 00:00:00", "2001-03-01 00:00:00", "22.0", "102.0"),
        ("3", "2001-03-01 00:00:00", "2001-04-01 00:00:00", "103.0", "103.0"),
    ]


def test_samplers_of_another_temporal_type_give_no_samples(mapcalc_session):
    """A partner of relative time cannot be sampled by a sampler of absolute
    time: the tool says so, reports that it found no samples, ends without an
    error and creates no output dataset. Measured 2026-10-14 on the unchanged
    tool."""
    tools = Tools(session=mapcalc_session, overwrite=True, consistent_return_value=True)
    _make_strds(tools, "char_tt_s", [(1, "2001-01-01", "2001-02-01")])
    _make_strds(
        tools,
        "char_tt_p",
        [(2, 0, 1)],
        temporaltype="relative",
        unit="days",
    )
    result = tools.t_rast_mapcalc(
        inputs="char_tt_s,char_tt_p",
        output="char_tt_out",
        expression="char_tt_s + char_tt_p",
        basename="char_tt_out",
        method="equal",
    )
    assert "must be of the same temporal type" in result.stderr
    assert "No samples found for map calculation" in result.stderr
    assert not _exists(tools, "char_tt_out")


def test_sampler_of_time_instants_gives_no_samples(mapcalc_session):
    """A sampler of time instants has no granules to sample by: the tool says
    that the sampler must be of interval time, reports that it found no
    samples, ends without an error and creates no output dataset. Measured
    2026-10-14 on the unchanged tool."""
    tools = Tools(session=mapcalc_session, overwrite=True, consistent_return_value=True)
    _make_strds(tools, "char_pt_s", [(1, "2001-01-01", None), (2, "2001-01-02", None)])
    _make_strds(tools, "char_pt_p", [(3, "2001-01-01", "2001-01-02")])
    result = tools.t_rast_mapcalc(
        inputs="char_pt_s,char_pt_p",
        output="char_pt_out",
        expression="char_pt_s + char_pt_p",
        basename="char_pt_out",
        method="equal",
    )
    assert "must be interval" in result.stderr
    assert "No samples found for map calculation" in result.stderr
    assert not _exists(tools, "char_pt_out")


@pytest.mark.parametrize("where", [None, "start_time >= '2001-03-01'"])
def test_partner_without_maps_gives_an_empty_output(
    mapcalc_session, assert_tinfo, where
):
    """If no map of the partner remains (the dataset has none, or where leaves
    none), no sampler granule has a partner: no map is computed, but the
    output dataset is created, empty. Measured 2026-10-14 on the unchanged
    tool."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_ep_s",
        [(1, "2001-01-01", "2001-02-01"), (2, "2001-03-01", "2001-04-01")],
    )
    if where is None:
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="char_ep_p",
            title="t",
            description="t",
        )
    else:
        _make_strds(tools, "char_ep_p", [(3, "2001-01-01", "2001-02-01")])
    options = {} if where is None else {"where": where}
    tools.t_rast_mapcalc(
        inputs="char_ep_s,char_ep_p",
        output="char_ep_out",
        expression="char_ep_s + char_ep_p",
        basename="char_ep_out",
        method="equal",
        **options,
    )
    assert _exists(tools, "char_ep_out")
    assert_tinfo(tools, "char_ep_out", {"number_of_maps": 0})


def test_same_dataset_twice_substitutes_its_name_twice(mapcalc_session):
    """The inputs x,x name one dataset, so there is no sampling and the n-th
    map of each input goes with the n-th granule. The name is substituted once
    per input: the second pass replaces the dataset name inside the map name
    the first pass put there (char_xx_1 becomes char_xx_1_1), so the tool
    aborts. With the name once in the inputs it works. Measured 2026-10-14 on
    the unchanged tool; like the prefix hazard above, this pins a defect that a
    rebuild may remove on purpose."""
    tools = Tools(session=mapcalc_session, overwrite=True)
    _make_strds(
        tools,
        "char_xx",
        [(3, "2001-01-01", "2001-05-01"), (4, "2001-05-01", "2001-09-01")],
    )
    with pytest.raises(grass.exceptions.CalledModuleError) as excinfo:
        tools.t_rast_mapcalc(
            inputs="char_xx,char_xx",
            output="char_xx_out",
            expression="char_xx * char_xx",
            basename="char_xx_out",
        )
    assert "Invalid map <char_xx_1_1>" in str(excinfo.value)
    tools.t_rast_mapcalc(
        inputs="char_xx",
        output="char_xx_out",
        expression="char_xx * char_xx",
        basename="char_xx_out",
    )
    assert _maps(tools, "char_xx_out") == [
        ("1", "2001-01-01 00:00:00", "2001-05-01 00:00:00", "9.0", "9.0"),
        ("2", "2001-05-01 00:00:00", "2001-09-01 00:00:00", "16.0", "16.0"),
    ]


def test_sampler_without_maps_gives_no_samples(mapcalc_session):
    """If where leaves no map of the sampler, the tool reports that it found
    no samples, ends without an error and creates no output dataset. Measured
    2026-10-14 on the unchanged tool."""
    tools = Tools(session=mapcalc_session, overwrite=True, consistent_return_value=True)
    _make_strds(tools, "char_es_s", [(1, "2001-01-01", "2001-02-01")])
    _make_strds(tools, "char_es_p", [(2, "2001-03-01", "2001-04-01")])
    result = tools.t_rast_mapcalc(
        inputs="char_es_s,char_es_p",
        output="char_es_out",
        expression="char_es_s + char_es_p",
        basename="char_es_out",
        method="equal",
        where="start_time >= '2001-03-01'",
    )
    assert "No samples found for map calculation" in result.stderr
    assert not _exists(tools, "char_es_out")
