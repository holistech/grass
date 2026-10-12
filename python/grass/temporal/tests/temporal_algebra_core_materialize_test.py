"""Tests for reading and materializing series of the algebra core

The session has these raster maps in PERMANENT, all 3 x 3 cells and
constant, registered with days of January 2001:

=======  ====================================================
dataset  maps (value) and time
=======  ====================================================
A        a1..a4 (1..4), daily intervals [1, 2] .. [4, 5]
B        b1 (5) [1, 3], b2 (6) [3, 5]
Z        z1 (null) [1, 2], z2 (2) [2, 3]
RT       rt1 (1), rt2 (2), relative days [0, 1], [1, 2]
=======  ====================================================

and the map tm (7) registered with [1, 2] in no dataset, and the map m
(100) without time stamp.
"""

import datetime
import importlib
import os

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import CalledModuleError, FatalError
from grass.temporal import algebra as ta
from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.series import Space
from grass.tools import Tools

materialize_module = importlib.import_module("grass.temporal.algebra.materialize")

DATASETS = {
    "A": (
        "absolute",
        [("a1", 1, 1, 2), ("a2", 2, 2, 3), ("a3", 3, 3, 4), ("a4", 4, 4, 5)],
    ),
    "B": ("absolute", [("b1", 5, 1, 3), ("b2", 6, 3, 5)]),
    "Z": ("absolute", [("z1", "null()", 1, 2), ("z2", 2, 2, 3)]),
}


def day(number):
    return datetime.datetime(2001, 1, number)


@pytest.fixture(scope="module")
def core_session(tmp_path_factory):
    project = tmp_path_factory.mktemp("core") / "project"
    gs.create_project(project)
    # tgis reads the session from os.environ; mirror it there only for this
    # module, see grass_temporal_gui_support_test.py.
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tgis.init()
        tools = Tools(session=session)
        tools.g_region(n=3, s=0, e=3, w=0, res=1)
        directory = tmp_path_factory.mktemp("register")
        for name, (temporaltype, maps) in DATASETS.items():
            tools.t_create(
                output=name,
                type="strds",
                temporaltype=temporaltype,
                title=name,
                description=name,
            )
            lines = []
            for map_name, value, start, end in maps:
                tools.r_mapcalc(expression=f"{map_name} = {value}")
                lines.append(f"{map_name}|{day(start)}|{day(end)}")
            listing = directory / f"{name}.txt"
            listing.write_text("\n".join(lines) + "\n")
            tools.t_register(input=name, file=listing)
        tools.t_create(
            output="RT",
            type="strds",
            temporaltype="relative",
            title="RT",
            description="RT",
        )
        for map_name, value in [("rt1", 1), ("rt2", 2)]:
            tools.r_mapcalc(expression=f"{map_name} = {value}")
        tools.t_register(
            input="RT", maps="rt1,rt2", start=0, increment=1, unit="days", flags="i"
        )
        tools.r_mapcalc(expression="tm = 7")
        tools.t_register(maps="tm", start="2001-01-01", end="2001-01-02")
        tools.r_mapcalc(expression="m = 100")
        yield session


def registered(name):
    """(start, end, value) of the maps of a dataset, in time order"""
    dataset = tgis.open_old_stds(name, "strds")
    rows = []
    for map_ in dataset.get_registered_maps_as_objects(order="start_time") or []:
        map_.select()
        start, end = map_.get_temporal_extent_as_tuple()
        rows.append((start, end, map_.metadata.get_min()))
    return rows


def test_source_reads_the_registered_maps(core_session):
    a = ta.source("A")
    assert a.times() == [(day(n), day(n + 1)) for n in range(1, 5)]
    assert a.slots[0].content == MapRef("a1@PERMANENT")
    assert a.slots[0].origin == "a1@PERMANENT"
    assert a.slots[0].space == Space(3, 0, 3, 0, 0, 0)
    assert a.kind == "raster"


def test_source_with_where(core_session):
    assert len(ta.source("A", where="start_time >= '2001-01-03'")) == 2


def test_source_of_relative_time(core_session):
    assert ta.source("RT").temporal_type == "relative"
    assert ta.source("RT").slots[0].extent.unit == "days"


def test_source_of_an_unknown_dataset_type(core_session):
    with pytest.raises(ValueError, match="stds_type"):
        ta.source("A", stds_type="vector")


def test_source_of_missing_dataset(core_session):
    with pytest.raises(FatalError, match="missing"):
        ta.source("missing")


def test_source_map(core_session):
    assert ta.source_map("tm").times() == [(day(1), day(2))]
    timeless = ta.source_map("m", timestamp=False)
    assert timeless.timeless
    assert timeless.slots[0].content == MapRef("m@PERMANENT")
    with pytest.raises(FatalError, match="not registered"):
        ta.source_map("m")


def test_materialize_computes_and_registers(core_session):
    a = ta.source("A")
    dataset = ta.materialize(a + 1, "plus", overwrite=True)
    assert dataset.get_id() == "plus@PERMANENT"
    assert registered("plus") == [(day(n), day(n + 1), n + 1) for n in range(1, 5)]


def test_null_maps_are_registered_only_on_request(core_session):
    a = ta.source("A")
    ta.materialize(ta.where(a > 2, a), "high", overwrite=True)
    assert [row[2] for row in registered("high")] == [3, 4]
    ta.materialize(ta.where(a > 2, a), "high_all", overwrite=True, register_null=True)
    assert [row[2] for row in registered("high_all")] == [None, None, 3, 4]


def test_existing_results_stop_before_anything_is_computed(core_session):
    a = ta.source("A")
    ta.materialize(a * 1, "kept", overwrite=True)
    with pytest.raises(FatalError, match="exists"):
        ta.materialize(a * 2, "kept")
    assert [row[2] for row in registered("kept")] == [1, 2, 3, 4]


def test_overwriting_maps_of_the_other_temporal_type(core_session):
    """A map registered with relative time gets absolute time when a result
    of absolute time overwrites it"""
    ta.materialize(ta.source("RT") * 1, "switch", basename="sw", overwrite=True)
    ta.materialize(ta.source("A") * 1, "switch", basename="sw", overwrite=True)
    assert [row[:2] for row in registered("switch")] == [
        (day(n), day(n + 1)) for n in range(1, 5)
    ]
    assert tgis.open_old_stds("switch", "strds").get_temporal_type() == "absolute"


def test_overwriting_maps_of_absolute_time_with_relative_time(core_session):
    ta.materialize(ta.source("A") * 1, "back", basename="bk", overwrite=True)
    dataset = ta.materialize(ta.source("RT") * 2, "back", basename="bk", overwrite=True)
    assert dataset.get_temporal_type() == "relative"
    assert registered("back") == [(0, 1, 2), (1, 2, 4)]


def test_skipping_null_with_r_series(core_session):
    b, z = ta.source("B"), ta.source("Z")
    ta.materialize(
        ta.gather(b, ta.contains, z, reduce="sum", nulls="skip"), "skip", overwrite=True
    )
    assert registered("skip") == [(day(1), day(3), 2)]


def test_temporary_maps_are_removed(core_session):
    b, z = ta.source("B"), ta.source("Z")
    reduced = ta.gather(b, ta.contains, z * 2, reduce="sum", nulls="skip")
    ta.materialize(reduced, "doubled", overwrite=True)
    assert registered("doubled") == [(day(1), day(3), 4)]
    tools = Tools(session=core_session)
    assert tools.g_list(type="raster", pattern="doubled_*_tmp*") is None


def test_empty_result_creates_an_empty_dataset_with_a_warning(
    core_session, monkeypatch
):
    warnings = []

    class Messages:
        def warning(self, message):
            warnings.append(message)

    monkeypatch.setattr(materialize_module, "get_tgis_message_interface", Messages)
    b, z = ta.source("B"), ta.source("Z")
    ta.materialize(ta.gather(b, ta.contains, z, reduce="sum"), "empty", overwrite=True)
    assert registered("empty") == []
    assert len(warnings) == 1


def test_empty_series_creates_an_empty_dataset_with_a_warning(
    core_session, monkeypatch
):
    warnings = []

    class Messages:
        def warning(self, message):
            warnings.append(message)

    monkeypatch.setattr(materialize_module, "get_tgis_message_interface", Messages)
    nothing = ta.source("A", where="start_time > '2030-01-01'")
    assert len(nothing) == 0
    dataset = ta.materialize(nothing + 1, "nothing", overwrite=True)
    assert dataset.get_id() == "nothing@PERMANENT"
    assert registered("nothing") == []
    assert len(warnings) == 1


# Running a map as a sequence of calls in the background forks a process,
# and Python 3.12 warns about forking while other threads exist (the
# messenger of grass.temporal runs in a process, pytest in threads); the
# calls are independent processes of GRASS, so there is no lock to deadlock.
@pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded:DeprecationWarning"
)
def test_parallel_processes_give_the_same_result(core_session):
    a = ta.source("A")
    ta.materialize(a * 3, "parallel", overwrite=True, nprocs=2)
    assert [row[2] for row in registered("parallel")] == [3, 6, 9, 12]
    b, z = ta.source("B"), ta.source("Z")
    reduced = ta.gather(b, ta.contains, z * 2, reduce="sum", nulls="skip")
    ta.materialize(reduced, "parallel_series", overwrite=True, nprocs=2)
    assert registered("parallel_series") == [(day(1), day(3), 4)]


@pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded:DeprecationWarning"
)
@pytest.mark.timeout(60)
def test_parallel_failure_of_a_sequence_of_calls_is_raised(core_session, monkeypatch):
    """r.series reads a missing map after r.mapcalc has written the temporary
    maps; the background process reports the failure instead of waiting
    forever"""
    b, z = ta.source("B"), ta.source("Z")
    reduced = ta.gather(b, ta.contains, z * 2, reduce="sum", nulls="skip")
    run_module = materialize_module._module

    def failing_module(call, overwrite):
        module = run_module(call, overwrite)
        if call.name == "r.series":
            module.inputs["input"].value = "no_such_map"
        return module

    monkeypatch.setattr(materialize_module, "_module", failing_module)
    with pytest.raises(CalledModuleError, match="no_such_map"):
        ta.materialize(reduced, "parallel_failing", overwrite=True, nprocs=2)


def test_removed_empty_maps_leave_no_row_in_the_temporal_database(core_session):
    a = ta.source("A")
    ta.materialize(a * 1, "stale", overwrite=True)
    assert tgis.RasterDataset("stale_0@PERMANENT").is_in_db()
    ta.materialize(ta.where(a > 10, a), "stale", overwrite=True)
    assert registered("stale") == []
    assert not tgis.RasterDataset("stale_0@PERMANENT").is_in_db()
    # The names are free again, also without overwrite.
    ta.materialize(a * 1, "stale2", basename="stale")
    assert [row[2] for row in registered("stale2")] == [1, 2, 3, 4]


def test_map_only_in_the_temporal_database_stops_before_computing(core_session):
    tools = Tools(session=core_session)
    tools.r_mapcalc(expression="ghost_0 = 1")
    tools.t_register(maps="ghost_0", start="2001-01-01", end="2001-01-02")
    tools.g_remove(type="raster", name="ghost_0", flags="f")
    assert tgis.RasterDataset("ghost_0@PERMANENT").is_in_db()
    with pytest.raises(FatalError, match="ghost_0"):
        ta.materialize(ta.source("A") * 1, "ghosts", basename="ghost")
    assert tools.g_list(type="raster", pattern="ghost_*") is None


@pytest.mark.parametrize(
    ("name", "basename"),
    [
        ("a.b", None),
        ("a.b.c", None),
        ("a@PERMANENT", None),
        ("ok", "a@b"),
    ],
)
def test_invalid_names_stop_before_computing(core_session, name, basename):
    tools = Tools(session=core_session)
    before = tools.g_list(type="raster").stdout
    with pytest.raises(ValueError, match="must not contain"):
        ta.materialize(ta.source("A") * 1, name, basename=basename)
    assert tools.g_list(type="raster").stdout == before


def test_basename_may_contain_a_dot(core_session):
    """Only the dataset name is split at a dot (as name.semantic_label); map
    names may contain one"""
    ta.materialize(ta.source("A") * 1, "dotted", basename="a.b", overwrite=True)
    assert [row[2] for row in registered("dotted")] == [1, 2, 3, 4]
    assert tgis.RasterDataset("a.b_0@PERMANENT").is_in_db()


@pytest.mark.parametrize(
    ("reduce", "expected"),
    [("sum", 10), ("prod", 24), ("mean", 2.5), ("min", 1), ("max", 4), ("all", 1)],
)
def test_reduction_of_more_than_two_maps_is_computed_by_r_mapcalc(
    core_session, reduce, expected
):
    """The flat call (a + b + c + d) is read by r.mapcalc like the nested one"""
    a = ta.source("A")
    target = ta.granules("2001-01-01", "2001-01-05", "4 days")
    reduced = ta.gather(target, ta.contains, a, reduce=reduce)
    ta.materialize(reduced, "flat", overwrite=True)
    assert registered("flat") == [(day(1), day(5), expected)]


def test_subtraction_of_more_than_two_maps_is_computed_from_left_to_right(
    core_session,
):
    """b1 contains a1 and a2: 5 - 1 - 2 is 2, while 5 - (1 - 2) would be 6"""
    reduced = ta.gather(
        ta.source("B"), ta.contains, ta.source("A"), reduce=ta.fold("-")
    )
    ta.materialize(reduced, "flat_minus", overwrite=True)
    assert [row[2] for row in registered("flat_minus")] == [2, -1]


def test_temporary_maps_are_removed_in_chunks_of_100(monkeypatch):
    """One g.remove call with every name could exceed the size of the argument
    list"""
    calls = []
    monkeypatch.setattr(
        materialize_module,
        "Module",
        lambda *args, **parameters: calls.append((args, parameters)),
    )
    names = [f"R_{number}_tmp0" for number in range(250)]
    materialize_module._remove(names, "raster")
    assert [len(parameters["name"].split(",")) for _, parameters in calls] == [
        100,
        100,
        50,
    ]
    assert ",".join(parameters["name"] for _, parameters in calls) == ",".join(names)
    calls.clear()
    materialize_module._remove([], "raster")
    assert calls == []


def test_temporary_maps_are_removed_when_a_call_fails(core_session, monkeypatch):
    """r.series is made to fail after r.mapcalc has written the temporary
    maps of its inputs"""
    tools = Tools(session=core_session)
    b, a = ta.source("B"), ta.source("A")
    reduced = ta.gather(b, ta.contains, a * 2, reduce="sum", nulls="skip")
    run_module = materialize_module._module

    def failing_module(call, overwrite):
        module = run_module(call, overwrite)
        if call.name == "r.series":

            def fail():
                msg = "forced failure"
                raise RuntimeError(msg)

            module.run = fail
        return module

    monkeypatch.setattr(materialize_module, "_module", failing_module)
    # Without the cleanup the temporary maps stay: the check can see them.
    with monkeypatch.context() as context:
        context.setattr(materialize_module, "_remove", lambda names, kind: None)
        with pytest.raises(RuntimeError, match="forced failure"):
            ta.materialize(reduced, "failing", overwrite=True)
        assert tools.g_list(type="raster", pattern="failing_*_tmp*") is not None
    tools.g_remove(type="raster", pattern="failing_*", flags="f")
    with pytest.raises(RuntimeError, match="forced failure"):
        ta.materialize(reduced, "failing", overwrite=True)
    assert tools.g_list(type="raster", pattern="failing_*_tmp*") is None


def test_choose_equals_where_of_the_lifted_condition(core_session, make_series):
    """Without registration of empty maps both kinds of conditions keep the
    same maps, also for a null condition"""
    a = ta.source("A")
    k = make_series("k", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, 0, None, 1])
    ta.materialize(ta.choose(k, a) * 1, "chosen", overwrite=True)
    ta.materialize(ta.where(k, a), "where_lifted", overwrite=True)
    assert registered("chosen") == registered("where_lifted")
    assert [row[2] for row in registered("chosen")] == [1, 4]


def test_where_of_equal_branches(core_session):
    """where(c, X, X) == X where c is not null; A > 2 has no null cell"""
    a = ta.source("A")
    ta.materialize(ta.where(a > 2, a, a), "same", overwrite=True)
    assert [row[2] for row in registered("same")] == [1, 2, 3, 4]
