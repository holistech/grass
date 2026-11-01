"""The series_method reducer and the SeriesAggregate content node

series_method lets gather() aggregate related maps with any r.series method,
as t.rast.aggregate does, and keeps its single map g.copy quirk and its
file_limit apart from the skip-sum and skip-mean of the algebra. Only the
check against the r.series interface description needs a session.
"""

import xml.etree.ElementTree as ET

import pytest

import grass.script as gs
import grass.temporal.algebra as ta
from grass.temporal.algebra import reducers, variants
from grass.temporal.algebra.backends import RasterBackend
from grass.temporal.algebra.content import MapRef, SeriesAggregate
from grass.temporal.algebra.materialize import _map_names
from grass.temporal.algebra.series import Extent, Series, Slot
from grass.temporal.testing.session import project_session


def test_check_accepts_any_method():
    reducers.check(ta.series_method("median"), "skip")
    reducers.check(ta.series_method("quantile"), "skip")


def test_series_method_rejects_an_unknown_method():
    with pytest.raises(ValueError, match="medain"):
        ta.series_method("medain")


@pytest.fixture
def session(tmp_path):
    with project_session(tmp_path / "project") as grass_session:
        yield grass_session


def test_series_methods_match_r_series(session):
    """The list must follow r.series when its methods change"""
    description = gs.read_command(
        "r.series", "--interface-description", env=session.env
    )
    parameters = ET.fromstring(description).iter("parameter")
    method = next(p for p in parameters if p.get("name") == "method")
    names = {value.findtext("name") for value in method.find("values")}
    assert names == set(reducers.SERIES_METHODS)


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


def test_two_maps_plan_r_series_without_z(monkeypatch):
    # One thread and no session file: two maps need 68 open files, which
    # any machine allows, whatever its processors and NPROCS.
    monkeypatch.delenv("GISRC", raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
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


def _open_files(monkeypatch, soft, threads):
    """Let the plan see soft open files and r.series run threads threads

    No session file is named, so NPROCS of a session of another test cannot
    count. Return the list that collects the warnings of the plan.
    """
    resource = pytest.importorskip("resource")
    monkeypatch.delenv("GISRC", raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", str(threads))
    monkeypatch.setattr(
        resource, "getrlimit", lambda resource_: (soft, resource.RLIM_INFINITY)
    )
    warnings = []

    class Messages:
        def warning(self, message):
            warnings.append(message)

    monkeypatch.setattr(variants, "get_tgis_message_interface", Messages)
    return warnings


def test_an_aggregate_past_the_open_files_reads_row_by_row(monkeypatch):
    """Two maps on three threads hold 12 files besides the 64 kept free, one
    more than a limit of 75 allows, although file_limit is far away"""
    warnings = _open_files(monkeypatch, 75, 3)
    node = SeriesAggregate("sum", (MapRef("a"), MapRef("b")), 1000)
    calls, _ = RasterBackend().plan(node, "out")
    assert calls[0].parameters["flags"] == "z"
    assert len(warnings) == 1
    assert warnings[0].startswith("The limit of open files (1) was reached (2). ")


def test_an_aggregate_within_both_limits_keeps_its_maps_open(monkeypatch):
    warnings = _open_files(monkeypatch, 76, 3)
    node = SeriesAggregate("sum", (MapRef("a"), MapRef("b")), 1000)
    calls, _ = RasterBackend().plan(node, "out")
    assert "flags" not in calls[0].parameters
    assert warnings == []


def test_an_aggregate_past_file_limit_warns_with_file_limit(monkeypatch):
    resource = pytest.importorskip("resource")
    warnings = _open_files(monkeypatch, resource.RLIM_INFINITY, 1)
    node = SeriesAggregate("sum", tuple(MapRef(f"m{i}") for i in range(3)), 2)
    calls, _ = RasterBackend().plan(node, "out")
    assert calls[0].parameters["flags"] == "z"
    assert len(warnings) == 1
    assert "(2) was reached (3)" in warnings[0]


def test_a_lone_map_is_copied_without_a_warning(monkeypatch):
    warnings = _open_files(monkeypatch, 10, 1)
    node = SeriesAggregate("sum", (MapRef("a"),), 0)
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["g.copy"]
    assert warnings == []


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


def test_series_aggregate_is_an_operand():
    series = Series((Slot(Extent(1, 2, "days"), MapRef("a")),))
    node = SeriesAggregate("average", (MapRef("b"), MapRef("c")), 1000)
    result = ta.apply("+", series, node)
    assert node in result.slots[0].content.args
