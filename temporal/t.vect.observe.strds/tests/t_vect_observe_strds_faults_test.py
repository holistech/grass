"""Test the cases in which t.vect.observe.strds writes nothing, or writes a NULL

The data are described in conftest.py.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, vector_points
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def _options(points, prefix, **options):
    return {
        "input": points,
        "strds": "ob_a",
        "output": prefix,
        "vector_output": f"{prefix}_v",
        "columns": "obs",
        **options,
    }


def _nothing_made(tools, prefix):
    """No vector map, helper map or dataset is left under the prefix"""
    assert tools.g_list(type="vector", pattern=f"{prefix}_v*").stdout.split() == []
    assert tools.g_list(type="vector", pattern="tmp_t_vect_observe*").stdout == ""
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


def test_where_without_points(tools, rasters, points, prefix):
    with pytest.raises(ToolError) as error:
        tools.t_vect_observe_strds(**_options(points, prefix, where="h > 99"))

    text = message(error.value)
    assert f"The where option selects no point of vector map <{points}>" in text
    assert "Traceback" not in text
    assert "KeyError" not in text
    _nothing_made(tools, prefix)


def test_no_common_granule_warns_and_writes_nothing(tools, rasters, points, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_far",
        [MapSpec(f"{prefix}_f1", 1, datetime(2002, 1, 1), datetime(2002, 2, 1))],
    )

    result = tools.t_vect_observe_strds(
        **_options(points, prefix, strds=f"ob_a,{prefix}_far", columns="a,b")
    )

    assert result.returncode == 0
    assert (
        "No granule of space time raster dataset <ob_a@PERMANENT> has a map in each of the "
        "datasets, nothing is written"
    ) in message(result)
    _nothing_made(tools, prefix)
    assert tools.db_columns(table=points).stdout.split() == ["x", "y", "cat", "h"]


def test_two_maps_in_one_granule_warn(tools, rasters, points, prefix):
    # Two maps hold the time of the first granule of ob_a.
    create_stds(
        tools,
        "strds",
        f"{prefix}_twice",
        [
            MapSpec(f"{prefix}_t{k}", k, datetime(2001, 3, 1), datetime(2001, 4, 1))
            for k in (1, 2)
        ],
    )

    result = tools.t_vect_observe_strds(
        **_options(points, prefix, strds=f"ob_a,{prefix}_twice", columns="a,b")
    )

    text = message(result)
    granule = "Granule 2001-03-01 00:00:00 - 2001-04-01 00:00:00"
    assert f"{granule}: space time raster dataset <{prefix}_twice>" in text
    assert f"has 2 maps, only <{prefix}_t1@" in text
    # The first of the two maps is used, as before.
    assert len(list_maps(tools, "stvds", prefix)) == 1


def test_two_maps_in_a_dropped_granule_do_not_warn(tools, rasters, points, prefix):
    # The March granule has two maps in the second dataset and none in the
    # third, so it is left out and nothing about it is said.
    create_stds(
        tools,
        "strds",
        f"{prefix}_twice",
        [
            MapSpec(f"{prefix}_t{k}", k, datetime(2001, 3, 1), datetime(2001, 4, 1))
            for k in (1, 2)
        ],
    )

    result = tools.t_vect_observe_strds(
        **_options(points, prefix, strds=f"ob_a,{prefix}_twice,ob_b", columns="a,b,c")
    )

    assert "has 2 maps" not in message(result)


def test_duplicate_columns_are_refused(tools, rasters, points, prefix):
    with pytest.raises(ToolError) as error:
        tools.t_vect_observe_strds(
            **_options(points, prefix, strds="ob_a,ob_a", columns="a,A")
        )

    assert "The column names must be different: <A> is given twice" in message(
        error.value
    )
    _nothing_made(tools, prefix)
    assert tools.db_columns(table=points).stdout.split() == ["x", "y", "cat", "h"]


def test_overwrite_sets_unsampled_point_to_null(tools, rasters, prefix):
    # The fifth point lies outside the region, so no raster map has a value for
    # it. The input table holds 7 in the column obs for every point.
    name = f"{prefix}_pts"
    vector_points(
        tools,
        name,
        [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5), (9.5, 9.5)],
        attributes={"obs": [7, 7, 7, 7, 7]},
    )

    tools.t_vect_observe_strds(**_options(name, prefix, overwrite=True))

    text = tools.v_db_select(map=f"{prefix}_v", layer=1, columns="cat,obs", flags="c")
    assert text.stdout.splitlines() == ["1|111", "2|112", "3|121", "4|122", "5|"]
    # The input keeps its values.
    kept = tools.v_db_select(map=name, columns="obs", flags="c").stdout.split()
    assert kept == ["7"] * 5
