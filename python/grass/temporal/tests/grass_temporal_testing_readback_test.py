"""Tests for the readback helpers of grass.temporal.testing

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.script as gs
from grass.temporal.testing.readback import (
    Row,
    cell_values,
    inventory,
    list_maps,
    map_info,
    message,
    stds_info,
)
from grass.tools import ToolError, Tools


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools bound to a session with one dataset of each type

    - strds: a=1 and b=5 on the days 1 and 2 of January 2001 as instants,
      c=2 over [day 5, day 6].
    - str3ds: va=1 and vb=4 as instants on days 1 and 2.
    - stvds: grids vv and vw as instants on days 1 and 2.
    - empty: a strds without maps.
    """
    project = tmp_path_factory.mktemp("readback") / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=10, s=0, e=10, w=0, b=0, t=2, res=1, tbres=1)
        for name, value in (("a", 1), ("b", 5), ("c", 2)):
            tools.r_mapcalc(expression=f"{name} = {value}")
        for name, value in (("va", 1), ("vb", 4)):
            tools.r3_mapcalc(expression=f"{name} = {value}")
        for name in ("vv", "vw"):
            tools.v_mkgrid(map=name, grid=[2, 2])
        for stds_type, name in (
            ("strds", "s"),
            ("str3ds", "s3"),
            ("stvds", "sv"),
            ("strds", "empty"),
        ):
            tools.t_create(
                type=stds_type,
                temporaltype="absolute",
                output=name,
                title=name,
                description=name,
            )
        register = {
            "raster": ("s", "a,b"),
            "raster_3d": ("s3", "va,vb"),
            "vector": ("sv", "vv,vw"),
        }
        for map_type, (stds, maps) in register.items():
            tools.t_register(
                type=map_type,
                input=stds,
                maps=maps,
                start="2001-01-01",
                increment="1 days",
            )
        tools.t_register(
            type="raster", input="s", maps="c", start="2001-01-05", end="2001-01-06"
        )
        yield tools


def test_strds_rows_are_typed_and_ordered(tools):
    assert list_maps(tools, "strds", "s") == [
        Row("a", "2001-01-01 00:00:00", None, 1.0, 1.0),
        Row("b", "2001-01-02 00:00:00", None, 5.0, 5.0),
        Row("c", "2001-01-05 00:00:00", "2001-01-06 00:00:00", 2.0, 2.0),
    ]


def test_str3ds_rows(tools):
    assert list_maps(tools, "str3ds", "s3") == [
        Row("va", "2001-01-01 00:00:00", None, 1.0, 1.0),
        Row("vb", "2001-01-02 00:00:00", None, 4.0, 4.0),
    ]


def test_stvds_rows_have_no_range(tools):
    assert list_maps(tools, "stvds", "sv") == [
        Row("vv", "2001-01-01 00:00:00", None, None, None),
        Row("vw", "2001-01-02 00:00:00", None, None, None),
    ]


@pytest.mark.parametrize(
    ("stds_type", "name", "where", "names"),
    [
        ("strds", "s", "start_time > '2001-01-01 12:00:00'", ["b", "c"]),
        ("str3ds", "s3", "start_time > '2001-01-01 12:00:00'", ["vb"]),
        ("stvds", "sv", "start_time > '2001-01-01 12:00:00'", ["vw"]),
    ],
)
def test_where_restricts_the_rows(tools, stds_type, name, where, names):
    rows = list_maps(tools, stds_type, name, where=where)
    assert [row.name for row in rows] == names


def test_empty_dataset_gives_no_rows(tools):
    assert list_maps(tools, "strds", "empty") == []


def test_unknown_type_is_refused(tools):
    with pytest.raises(ValueError, match="Unknown dataset type"):
        list_maps(tools, "raster", "s")


def test_stds_info_counts_the_maps(tools):
    assert stds_info(tools, "strds", "s")["number_of_maps"] == 3
    assert stds_info(tools, "stvds", "sv")["number_of_maps"] == 2


def test_stds_info_of_an_empty_dataset(tools):
    info = stds_info(tools, "strds", "empty")
    assert info["name"] == "empty"
    assert info["number_of_maps"] == "None"


@pytest.mark.parametrize(
    ("map_type", "name", "start"),
    [
        ("raster", "a", "'2001-01-01 00:00:00'"),
        ("raster_3d", "va", "'2001-01-01 00:00:00'"),
        ("vector", "vw", "'2001-01-02 00:00:00'"),
    ],
)
def test_map_info_of_a_registered_map(tools, map_type, name, start):
    info = map_info(tools, map_type, name)
    assert info["name"] == name
    assert info["start_time"] == start


def test_inventory_lists_the_maps_and_the_datasets(tools):
    maps, datasets = inventory(tools)

    assert sorted(maps) == ["a", "b", "c", "va", "vb", "vv", "vw"]
    assert datasets == [
        ["empty@PERMANENT", "s@PERMANENT"],
        ["s3@PERMANENT"],
        ["sv@PERMANENT"],
    ]


def test_map_info_of_a_map_that_is_not_registered_is_none(tools):
    tools.r_mapcalc(expression="loose = 1")
    assert map_info(tools, "raster", "loose") is None


def test_map_info_raises_any_other_failure(tools):
    with pytest.raises(ToolError):
        map_info(tools, "nonsense", "a")


def test_message_joins_a_wrapped_stderr(tools):
    result = tools.t_info(type="strds", input="s", flags="g")
    assert message(type("R", (), {"stderr": "a  b\n   c\n"})()) == "a b c"
    assert message(result) == " ".join(result.stderr.split())


def test_message_reads_the_text_of_an_error(tools):
    with pytest.raises(ToolError) as raised:
        tools.t_info(
            type="strds", input="a_dataset_with_a_name_that_makes_it_wrap_x" * 2
        )

    assert "\n" not in message(raised.value)
    assert "not found" in message(raised.value)


def test_cell_values_reads_every_cell_and_null(tools):
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.r_mapcalc(expression="cells = if(row() == 1, if(col() == 1, 1.5, null()), 3)")

    assert cell_values(tools, "cells") == [1.5, None, 3.0, 3.0]


def test_cell_values_rounds_only_fcell_maps_to_six_places(tools):
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    tools.r_mapcalc(expression="third_d = 1.0 / 3")
    tools.r_mapcalc(expression="third_f = float(1.0 / 3)")

    assert cell_values(tools, "third_d") == [0.3333333333333333]
    assert cell_values(tools, "third_f") == [0.333333]
