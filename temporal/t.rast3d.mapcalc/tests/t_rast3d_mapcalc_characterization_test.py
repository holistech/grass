"""Characterization of t.rast3d.mapcalc, which shares dataset_mapcalculator

dataset_mapcalculator() is shared with t.rast.mapcalc and is rebuilt on the
algebra core later. The expected values were measured on 2026-10-14 by calling
dataset_mapcalculator(type="raster3d") in process on the fixture datasets
(vol_1..3 = 100, 200, 300), with the semantic label read for raster maps
only, which is the fix that comes with these tests: before it, the tool
aborted on every input. t.rast3d.list prints min and max as floats with a .0.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from grass.tools import Tools


def _maps(tools, str3ds):
    """(numeric suffix, start, end, min, max) of each registered 3D map"""
    text = tools.t_rast3d_list(
        input=str3ds,
        columns="name,start_time,end_time,min,max",
        separator="|",
        format="plain",
        flags="s",
    ).text
    rows = [line.split("|") for line in text.strip().splitlines()]
    return [(row[0].rsplit("_", 1)[-1], row[1], row[2], row[3], row[4]) for row in rows]


def test_two_inputs_equal_sampling_values(mapcalc3d_session):
    """precip3d_1 + precip3d_2 over the three identical granules"""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    tools.t_rast3d_mapcalc(
        flags="n",
        inputs="precip3d_1,precip3d_2",
        output="c3_add",
        expression="precip3d_1 + precip3d_2",
        basename="c3_add",
        method="equal",
        nprocs=2,
    )
    assert _maps(tools, "c3_add") == [
        ("1", "2001-01-01 00:00:00", "2001-04-01 00:00:00", "200.0", "200.0"),
        ("2", "2001-04-01 00:00:00", "2001-07-01 00:00:00", "400.0", "400.0"),
        ("3", "2001-07-01 00:00:00", "2001-10-01 00:00:00", "600.0", "600.0"),
    ]


def test_td_values(mapcalc3d_session):
    """td() over the three three-month granules is 90, 91, 92 days"""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    tools.t_rast3d_mapcalc(
        flags="n",
        inputs="precip3d_1",
        output="c3_td",
        expression="td()",
        basename="c3_td",
    )
    assert [row[3] for row in _maps(tools, "c3_td")] == ["90.0", "91.0", "92.0"]


def test_start_doy_values(mapcalc3d_session):
    """start_doy() over the three granules is 1, 91, 182"""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    tools.t_rast3d_mapcalc(
        flags="n",
        inputs="precip3d_1",
        output="c3_doy",
        expression="start_doy()",
        basename="c3_doy",
    )
    assert [row[3] for row in _maps(tools, "c3_doy")] == ["1.0", "91.0", "182.0"]


def test_null_result_maps_dropped_without_n(mapcalc3d_session, assert_tinfo3d):
    """A result that is all null is removed when -n is not given"""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    tools.t_rast3d_mapcalc(
        flags="s",
        inputs="precip3d_1,precip3d_2",
        output="c3_null",
        expression="(precip3d_1 + precip3d_2) * null()",
        basename="c3_null",
        method="equal",
    )
    assert_tinfo3d(tools, "c3_null", {"number_of_maps": 0})


def test_null_result_maps_kept_with_n(mapcalc3d_session, assert_tinfo3d):
    """The same all-null result is kept when -n is given"""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    tools.t_rast3d_mapcalc(
        flags="sn",
        inputs="precip3d_1,precip3d_2",
        output="c3_null",
        expression="(precip3d_1 + precip3d_2) * null()",
        basename="c3_null",
        method="equal",
    )
    assert_tinfo3d(tools, "c3_null", {"number_of_maps": 3})


def test_spatial_sampling_ignores_the_vertical_extent(mapcalc3d_session):
    """With -s the 3D rasters are related by their 2D extent only: the
    partner map vol_sp_b lies at the same place and time as the granule vol_sp_a
    but above it (bottom 20, top 30, the granule 0 to 10), and is kept. In the
    computation region a is null above 10 and b below 20, so the expression
    uses 100 where b is null, and the result is 1 + 100 = 101 in the layer of
    a. Measured 2026-10-14 on the unchanged tool."""
    tools = Tools(session=mapcalc3d_session, overwrite=True)
    for name, value, bottom, top in [("vol_sp_a", 1, 0, 10), ("vol_sp_b", 10, 20, 30)]:
        tools.g_region(s=0, n=80, w=0, e=120, b=bottom, t=top, res=10, res3=10)
        try:
            tools.r3_mapcalc(expression=f"{name} = {value}")
        finally:
            tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)
    for name in ("a", "b"):
        tools.t_create(
            type="str3ds",
            temporaltype="absolute",
            output=f"vol_sp_s{name}",
            title="t",
            description="t",
        )
        tools.t_register(
            type="raster_3d",
            input=f"vol_sp_s{name}",
            maps=f"vol_sp_{name}",
            start="2001-01-01",
            end="2001-02-01",
        )
    tools.t_rast3d_mapcalc(
        flags="s",
        inputs="vol_sp_sa,vol_sp_sb",
        output="c3_sp",
        expression="vol_sp_sa + if(isnull(vol_sp_sb), 100, vol_sp_sb)",
        basename="c3_sp",
        method="equal",
    )
    assert _maps(tools, "c3_sp") == [
        ("1", "2001-01-01 00:00:00", "2001-02-01 00:00:00", "101.0", "101.0"),
    ]
