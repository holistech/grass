"""Test that r.univar and r3.univar print nan, never -nan, without values"""

import json
import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def tools(tmp_path):
    """Tools in a session of an XY project with a 3 by 3 by 1 region"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.g_region(s=0, n=3, w=0, e=3, b=0, t=1, res=1, res3=1)
        tools.r_mapcalc(expression="empty = float(null())")
        tools.r3_mapcalc(expression="empty3 = float(null())")
        # Zone 1 has values, zone 2 has none.
        tools.r_mapcalc(expression="zones = if(col() <= 2, 1, 2)")
        tools.r_mapcalc(expression="partly = if(col() <= 2, row(), null())")
        yield tools


TOOLS = pytest.mark.parametrize(
    ("tool", "map_name"), [("r_univar", "empty"), ("r3_univar", "empty3")]
)


@TOOLS
def test_plain_prints_nan_for_every_statistic(tools, tool, map_name):
    out = getattr(tools, tool)(map=map_name).stdout

    assert "-nan" not in out
    for label in (
        "mean:",
        "standard deviation:",
        "variance:",
        "variation coefficient:",
    ):
        assert f"{label} nan" in out, out


@TOOLS
@pytest.mark.parametrize("flags", ["g", "e", "eg"])
def test_shell_and_extended_print_nan(tools, tool, map_name, flags):
    out = getattr(tools, tool)(map=map_name, flags=flags, percentile=90).stdout

    assert "-nan" not in out
    if "g" in flags:
        for key in ("mean", "stddev", "variance", "coeff_var"):
            assert f"{key}=nan\n" in out, out
    if "e" in flags and "g" in flags:
        for key in ("first_quartile", "median", "third_quartile", "percentile_90"):
            assert f"{key}=nan\n" in out, out
    elif "e" in flags:
        for text in ("1st quartile: nan", "3rd quartile: nan", "90th percentile: nan"):
            assert text in out, out


@TOOLS
def test_csv_prints_no_minus_nan(tools, tool, map_name):
    out = getattr(tools, tool)(map=map_name, format="csv").stdout

    assert "-nan" not in out


@TOOLS
def test_json_keeps_null(tools, tool, map_name):
    out = getattr(tools, tool)(map=map_name, format="json", flags="e").stdout

    data = json.loads(out)
    for key in ("mean", "stddev", "variance", "coeff_var", "median"):
        assert data[key] is None, data


@pytest.mark.parametrize("flags", ["", "g", "e"])
def test_zones_print_nan(tools, flags):
    out = tools.r_univar(map="partly", zones="zones", flags=flags).stdout

    assert "-nan" not in out
    assert "nan" in out


def test_zones_table_prints_nan(tools):
    out = tools.r_univar(
        map="partly", zones="zones", format="csv", flags="e", percentile=90
    ).stdout

    assert "-nan" not in out
    rows = [line.split(",") for line in out.strip().splitlines()]
    zone_two = [row for row in rows if row[0] == "2"]
    assert zone_two, out
    assert "nan" in zone_two[0]


def test_zones_json_keeps_null(tools):
    out = tools.r_univar(map="partly", zones="zones", format="json").stdout

    zone_two = [zone for zone in json.loads(out) if zone["zone"] == 2][0]
    assert zone_two["mean"] is None
