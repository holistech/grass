"""Tests for the data helpers of grass.temporal.testing.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import (
    DAY0,
    MapSpec,
    create_stds,
    day,
    intervals,
    make_map,
    timestamp,
)
from grass.temporal.testing.readback import list_maps
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

MAP_KIND = {"strds": "raster", "str3ds": "raster_3d", "stvds": "vector"}


def test_day_and_timestamp():
    assert day(0) == DAY0 == datetime(2001, 1, 1)
    assert day(1, hours=6) == datetime(2001, 1, 2, 6)
    assert timestamp(31) == "2001-02-01"


def test_intervals_by_month():
    assert intervals(3) == [
        (datetime(2001, 1, 1), datetime(2001, 2, 1)),
        (datetime(2001, 2, 1), datetime(2001, 3, 1)),
        (datetime(2001, 3, 1), datetime(2001, 4, 1)),
    ]


def test_intervals_by_month_cross_a_year_end():
    assert intervals(2, start=11) == [
        (datetime(2001, 12, 1), datetime(2002, 1, 1)),
        (datetime(2002, 1, 1), datetime(2002, 2, 1)),
    ]


def test_intervals_by_day_from_start():
    assert intervals(2, granularity="day", start=5) == [
        (datetime(2001, 1, 6), datetime(2001, 1, 7)),
        (datetime(2001, 1, 7), datetime(2001, 1, 8)),
    ]


def test_intervals_rejects_unknown_granularity():
    with pytest.raises(ValueError, match="year"):
        intervals(1, granularity="year")


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    with temporal_session(tmp_path_factory.mktemp("data") / "project") as session:
        yield Tools(session=session)


def _specs(stds_type, case):
    """Three maps for case "interval", "point" or "relative"."""
    names = [f"{stds_type}_{case}_{number}" for number in (1, 2, 3)]
    if case == "interval":
        times = [(start, end) for start, end in intervals(3)]
    elif case == "point":
        times = [(day(number), None) for number in (0, 10, 20)]
    else:
        times = [(0, 1), (1, 3), (3, 6)]
    return [
        MapSpec(name, number, start, end)
        for number, (name, (start, end)) in enumerate(
            zip(names, times, strict=True), start=1
        )
    ]


def _expected(specs, case):
    """Times as the list tools print them: text for absolute, numbers for relative"""
    if case == "relative":
        return [(spec.name, spec.start, spec.end) for spec in specs]
    fmt = "%Y-%m-%d %H:%M:%S"
    return [
        (
            spec.name,
            spec.start.strftime(fmt),
            None if spec.end is None else spec.end.strftime(fmt),
        )
        for spec in specs
    ]


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("via", ["tool", "library"])
@pytest.mark.parametrize("case", ["interval", "point", "relative"])
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_create_stds_registers_the_given_times(tools, stds_type, case, via):
    specs = [
        MapSpec(f"{via}_{spec.name}", spec.value, spec.start, spec.end)
        for spec in _specs(stds_type, case)
    ]
    options = {"temporaltype": "relative", "unit": "days"} if case == "relative" else {}
    create_stds(
        tools, stds_type, f"{via}_{stds_type}_{case}", specs, via=via, **options
    )

    rows = list_maps(tools, stds_type, f"{via}_{stds_type}_{case}")

    assert [(row.name, row.start, row.end) for row in rows] == _expected(specs, case)


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("stds_type", ["strds", "str3ds", "stvds"])
def test_both_routes_give_the_same_rows(tools, stds_type):
    results = []
    for via in ("tool", "library"):
        specs = [
            MapSpec(
                f"same_{stds_type}_{via}{spec.name[-1]}",
                spec.value,
                spec.start,
                spec.end,
            )
            for spec in _specs(stds_type, "interval")
        ]
        create_stds(tools, stds_type, f"same_{stds_type}_{via}", specs, via=via)
        rows = list_maps(tools, stds_type, f"same_{stds_type}_{via}")
        # The map names differ by route; times and values must not.
        results.append([row._replace(name=row.name[-1]) for row in rows])
    assert results[0] == results[1]


def test_make_map_values(tools):
    make_map(tools, "raster", "mm_r", 7)
    make_map(tools, "raster_3d", "mm_r3", 8)
    make_map(tools, "vector", "mm_v", 9)

    assert tools.r_univar(map="mm_r", format="json").json["max"] == 7
    assert tools.r3_univar(map="mm_r3", format="json").json["max"] == 8
    rows = tools.v_db_select(map="mm_v", format="json").json["records"]
    assert [(row["x"], row["y"], row["value"]) for row in rows] == [(9, 9, 9)]


def test_semantic_label_is_set(tools):
    specs = [
        MapSpec("sl_1", 1, day(0), day(1), semantic_label="S2_1"),
        MapSpec("sl_2", 2, day(1), day(2), semantic_label="S2_2"),
    ]
    create_stds(tools, "strds", "sl", specs)

    result = tools.t_rast_list(input="sl", columns="name,semantic_label", format="json")

    assert [(r["name"], r["semantic_label"]) for r in result.json["data"]] == [
        ("sl_1", "S2_1"),
        ("sl_2", "S2_2"),
    ]


def test_semantic_label_on_a_vector_dataset_is_an_error(tools):
    specs = [MapSpec("slv_1", 1, day(0), day(1), semantic_label="x")]
    with pytest.raises(ValueError, match="semantic label"):
        create_stds(tools, "stvds", "slv", specs)


def test_make_map_region_is_used_for_the_map_only(tools):
    def region():
        return tools.g_region(flags="g3").keyval

    tools.g_region(n=10, s=0, e=10, w=0, t=4, b=0, res=1, res3=1)
    before = region()

    make_map(tools, "raster", "rg_small", 1, region={"n": 2, "s": 0, "e": 2, "w": 0})

    assert region() == before
    assert tools.r_info(map="rg_small", flags="g").keyval["rows"] == 2


def test_make_map_restores_the_3d_resolution(tools):
    def region():
        return tools.g_region(flags="g3").keyval

    tools.g_region(n=10, s=0, e=10, w=0, t=4, b=0, res=1, res3=1)
    before = region()

    make_map(tools, "raster_3d", "rg_coarse", 1, region={"res3": 5, "tbres": 2})

    assert region() == before


@pytest.mark.needs_solo_run
@pytest.mark.parametrize("via", ["tool", "library"])
def test_registering_twice_with_overwrite(tools, via):
    specs = [MapSpec(f"ow_{via}_1", 1, day(0), day(1))]
    create_stds(tools, "strds", f"ow_{via}", specs, via=via)

    create_stds(tools, "strds", f"ow_{via}", specs, via=via, overwrite=True)

    assert [row.name for row in list_maps(tools, "strds", f"ow_{via}")] == [
        f"ow_{via}_1"
    ]
