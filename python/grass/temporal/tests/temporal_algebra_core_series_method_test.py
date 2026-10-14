"""The series_method reducer and the SeriesAggregate content node

series_method lets gather() aggregate related maps with any r.series method,
as t.rast.aggregate does, and keeps its single map g.copy quirk and its
file_limit apart from the skip-sum and skip-mean of the algebra. No session.
"""

import pytest

import grass.temporal.algebra as ta
from grass.temporal.algebra import reducers
from grass.temporal.algebra.backends import RasterBackend
from grass.temporal.algebra.content import MapRef, SeriesAggregate
from grass.temporal.algebra.materialize import _map_names
from grass.temporal.algebra.series import Extent, Series, Slot


def test_check_accepts_any_method():
    reducers.check(ta.series_method("median"), "skip")
    reducers.check(ta.series_method("quantile"), "skip")


def test_sort_is_field():
    assert reducers.sort_of(ta.series_method("sum"), "scalar", "field") == "field"


def test_reduce_builds_the_node_with_the_limit():
    node = reducers.reduce(
        ta.series_method("median", file_limit=5),
        MapRef("t"),
        [MapRef("a"), MapRef("b")],
        "skip",
    )
    assert node == SeriesAggregate("median", (MapRef("a"), MapRef("b")), 5)


def test_single_map_plans_g_copy():
    node = SeriesAggregate("average", (MapRef("a"),), 1000)
    calls, remove = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["g.copy"]
    # pygrass takes the from,to pair of g.copy only as a tuple.
    assert calls[0].parameters["raster"] == ("a", "out")
    assert remove == []


def test_two_maps_plan_r_series_without_z():
    node = SeriesAggregate("sum", (MapRef("a"), MapRef("b")), 1000)
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["r.series"]
    assert calls[0].parameters["method"] == "sum"
    assert calls[0].parameters["output"] == "out"
    # The input maps travel on the call; the file is written at run time.
    assert calls[0].inputs == ("a", "b")
    assert "flags" not in calls[0].parameters
    # plan() writes no file, so neither a file nor an input is planned.
    assert "file" not in calls[0].parameters
    assert "input" not in calls[0].parameters


def test_z_flag_past_the_file_limit():
    node = SeriesAggregate("sum", tuple(MapRef(f"m{i}") for i in range(3)), 2)
    calls, _ = RasterBackend().plan(node, "out")
    assert calls[0].parameters["flags"] == "z"
    assert calls[0].inputs == ("m0", "m1", "m2")


def test_names_must_match_and_be_unique():
    series = Series(
        (
            Slot(Extent(1, 2, "days"), MapRef("a")),
            Slot(Extent(2, 3, "days"), MapRef("b")),
        )
    )
    assert _map_names(series, "b", None, names=["x", "y"]) == ["x", "y"]
    with pytest.raises(ValueError, match="names for"):
        _map_names(series, "b", None, names=["only_one"])
    with pytest.raises(ValueError, match="same name"):
        _map_names(series, "b", None, names=["same", "same"])


def test_names_cannot_be_combined_with_selection():
    series = Series(
        (Slot(Extent(1, 2, "days"), MapRef("a@PERMANENT"), None, "a@PERMANENT"),)
    )
    with pytest.raises(ValueError, match="names cannot be combined with selection"):
        ta.plan(series, "out", selection=True, names=["x"])
