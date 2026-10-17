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

import dataclasses
import datetime
import importlib
from io import StringIO

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import CalledModuleError, FatalError
from grass.temporal import algebra as ta
from grass.temporal.algebra.content import Const, MapRef
from grass.temporal.algebra.series import Series, Slot, Space
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
def core_session(temporal_module_session, tmp_path_factory):
    session = temporal_module_session
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
    return session


DATASET_CLASSES = {
    "raster3d": tgis.Raster3DDataset,
    "vector": tgis.VectorDataset,
}


def make_map(tools, kind, name):
    """Create a small map of the kind in the session"""
    if kind == "raster3d":
        tools.r3_mapcalc(expression=f"{name} = 1")
    else:
        tools.v_in_ascii(
            input=StringIO("1,1,1\n"), output=name, format="point", separator="comma"
        )


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
    with pytest.raises(
        FatalError, match=r"^Space time raster dataset <missing@PERMANENT> not found$"
    ):
        ta.source("missing")


def test_source_map(core_session):
    assert ta.source_map("tm").times() == [(day(1), day(2))]
    timeless = ta.source_map("m", timestamp=False)
    assert timeless.timeless
    assert timeless.slots[0].content == MapRef("m@PERMANENT")
    with pytest.raises(
        FatalError,
        match=(
            r"^Raster map <m@PERMANENT> has neither a registration in the "
            r"temporal database nor a time stamp$"
        ),
    ):
        ta.source_map("m")


def test_source_map_reads_a_grass_time_stamp(core_session):
    """A single map stamped with r.timestamp but not registered in the
    temporal database is usable, as the classic _open_single_map() makes it"""
    tools = Tools(session=core_session, overwrite=True)
    tools.r_mapcalc(expression="stamped = 42")
    tools.r_timestamp(map="stamped", date="01 Jan 2001/03 Jan 2001")
    assert ta.source_map("stamped").times() == [(day(1), day(3))]


@pytest.mark.parametrize(
    ("kind", "timestamp_tool", "date"),
    [
        ("raster3d", "r3_timestamp", "01 Jan 2001/03 Jan 2001"),
        ("vector", "v_timestamp", "01 Jan 2001/03 Jan 2001"),
    ],
)
def test_source_map_reads_a_grass_time_stamp_of_other_kinds(
    core_session, kind, timestamp_tool, date
):
    """Maps of 3D raster and vector type stamped with r3.timestamp or
    v.timestamp are usable without registration"""
    tools = Tools(session=core_session, overwrite=True)
    name = f"stamped_{kind}"
    make_map(tools, kind, name)
    getattr(tools, timestamp_tool)(map=name, date=date)
    assert not DATASET_CLASSES[kind](f"{name}@PERMANENT").is_in_db()
    series = ta.source_map(name, kind=kind)
    assert series.kind == kind
    assert series.times() == [(day(1), day(3))]
    assert series.slots[0].content == MapRef(f"{name}@PERMANENT")


def test_a_map_with_only_a_grass_time_stamp_is_materialized(core_session):
    """The time stamp of r.timestamp survives source_map() and materialize():
    the result is registered with it"""
    tools = Tools(session=core_session, overwrite=True)
    tools.r_mapcalc(expression="only_stamped = 5")
    tools.r_timestamp(map="only_stamped", date="02 Jan 2001/04 Jan 2001")
    assert not tgis.RasterDataset("only_stamped@PERMANENT").is_in_db()
    ta.materialize(ta.source_map("only_stamped") * 2, "from_stamp", overwrite=True)
    assert registered("from_stamp") == [(day(2), day(4), 10)]


def test_materialize_computes_and_registers(core_session):
    a = ta.source("A")
    dataset = ta.materialize(a + 1, "plus", overwrite=True)
    assert dataset.get_id() == "plus@PERMANENT"
    assert registered("plus") == [(day(n), day(n + 1), n + 1) for n in range(1, 5)]


def test_null_maps_are_registered_only_on_request(core_session):
    a = ta.source("A")
    ta.materialize(ta.where(a > 2, a, None), "high", overwrite=True)
    assert [row[2] for row in registered("high")] == [3, 4]
    ta.materialize(
        ta.where(a > 2, a, None), "high_all", overwrite=True, register_null=True
    )
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

        def percent(self, current, total, step):
            pass

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
    ta.materialize(ta.where(a > 10, a, None), "stale", overwrite=True)
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
    same maps, also for a null condition, if the else is null"""
    a = ta.source("A")
    k = make_series("k", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, 0, None, 1])
    ta.materialize(ta.choose(k, a) * 1, "chosen", overwrite=True)
    ta.materialize(ta.where(k, a, None), "where_lifted", overwrite=True)
    assert registered("chosen") == registered("where_lifted")
    assert [row[2] for row in registered("chosen")] == [1, 4]


def test_where_of_equal_branches(core_session):
    """where(c, X, X) == X where c is not null; A > 2 has no null cell"""
    a = ta.source("A")
    ta.materialize(ta.where(a > 2, a, a), "same", overwrite=True)
    assert [row[2] for row in registered("same")] == [1, 2, 3, 4]


def names_and_calls(chain):
    """(result name, module names) of each planned map, in order"""
    return [
        (planned.name, tuple(call.name for call in planned.calls))
        for planned in chain.maps
    ]


def test_selection_registers_a_map_with_an_origin_without_a_call(make_series):
    """A slot that kept its origin is the registered map itself"""
    chain = ta.plan(make_series("a", (1, 2), (2, 3)), "sel", selection=True)
    assert names_and_calls(chain) == [
        ("a1@PERMANENT", ()),
        ("a2@PERMANENT", ()),
    ]


def test_selection_copies_a_retimed_map_with_g_copy(make_series):
    """A slot without origin but with a plain map reference is a retimed map,
    copied with g.copy and numbered from 1"""
    series = ta.retime(make_series("a", (1, 2), (2, 3)), shift="1 day")
    chain = ta.plan(series, "sel", basename="copy", selection=True)
    assert names_and_calls(chain) == [("copy_1", ("g.copy",)), ("copy_2", ("g.copy",))]
    first = chain.maps[0].calls[0]
    assert first.parameters == {"raster": ("a1@PERMANENT", "copy_1")}


@pytest.mark.parametrize(
    ("kind", "option"), [("raster3d", "raster_3d"), ("vector", "vector")]
)
def test_selection_copies_a_retimed_map_of_other_kinds_with_g_copy(
    make_series, kind, option
):
    series = ta.retime(make_series("a", (1, 2), (2, 3), kind=kind), shift="1 day")
    chain = ta.plan(series, "sel", basename="copy", selection=True)
    assert names_and_calls(chain) == [("copy_1", ("g.copy",)), ("copy_2", ("g.copy",))]
    assert chain.maps[0].calls[0].parameters == {option: ("a1@PERMANENT", "copy_1")}


@pytest.mark.parametrize(
    ("kind", "stds_type", "list_type"),
    [("raster3d", "str3ds", "raster_3d"), ("vector", "stvds", "vector")],
)
def test_materialize_selection_copies_maps_of_other_kinds(
    core_session, kind, stds_type, list_type
):
    """g.copy accepts the map types of the selection: the copy exists with
    the type and is registered with the shifted time"""
    tools = Tools(session=core_session, overwrite=True)
    name = f"sel_src_{kind}"
    make_map(tools, kind, name)
    getattr(tools, "r3_timestamp" if kind == "raster3d" else "v_timestamp")(
        map=name, date="01 Jan 2001/03 Jan 2001"
    )
    series = ta.retime(ta.source_map(name, kind=kind), shift="10 days")
    result = f"sel_{kind}"
    ta.materialize(series, result, basename=result, overwrite=True, selection=True)
    listed = tools.g_list(type=list_type, pattern=f"{result}_1")
    assert listed.stdout.strip() == f"{result}_1"
    dataset = tgis.open_old_stds(result, stds_type)
    maps = dataset.get_registered_maps_as_objects(order="start_time")
    assert [map_.get_id() for map_ in maps] == [f"{result}_1@PERMANENT"]
    maps[0].select()
    assert maps[0].get_temporal_extent_as_tuple() == (day(11), day(13))


def test_selection_numbers_copies_only_in_a_mixed_result(make_series):
    """A result that mixes a registered map with retimed maps numbers the
    copies from 1, independent of how many maps are registered unchanged"""
    kept = make_series("a", (1, 2)).slots[0]
    moved = ta.retime(make_series("b", (2, 3), (3, 4)), shift="1 day").slots
    series = Series((kept, *moved), kind="raster")
    chain = ta.plan(series, "sel", basename="mix", selection=True)
    assert names_and_calls(chain) == [
        ("a1@PERMANENT", ()),
        ("mix_1", ("g.copy",)),
        ("mix_2", ("g.copy",)),
    ]


def test_selection_rejects_computed_content(make_series):
    """t.select selects and retimes maps, it computes none"""
    with pytest.raises(ValueError, match=r"computes none; the function \+\(\) cannot"):
        ta.plan(make_series("a", (1, 2)) + 1, "sel", selection=True)


def test_selection_message_continues_in_lower_case(make_series):
    """The description of the content follows a semicolon, so it starts in
    lower case, also for a number"""
    extent = make_series("a", (1, 2)).slots[0].extent
    series = Series((Slot(extent, Const(1)),), kind="raster")
    with pytest.raises(ValueError, match="computes none; the number 1 cannot be"):
        ta.plan(series, "sel", selection=True)


def test_selection_rejects_a_map_at_a_cell_offset(make_series):
    """A map read at a cell offset (an r.mapcalc neighbourhood) is no plain
    selection; neighbour() in time shifts to another map and is accepted"""
    extent = make_series("a", (1, 2)).slots[0].extent
    series = Series((Slot(extent, MapRef("a1@PERMANENT", (1, 0))),), kind="raster")
    with pytest.raises(ValueError, match="cannot be selected"):
        ta.plan(series, "sel", selection=True)


def test_materialize_selection_registers_and_copies(core_session):
    """A selection registers a1 unchanged under its own name and copies a
    shifted a2 under the result name, numbered from 1"""
    source = ta.source("A")
    kept = Series((source.slots[0],), kind="raster")
    moved = ta.retime(Series((source.slots[1],), kind="raster"), shift="10 days")
    series = Series((*kept.slots, *moved.slots), kind="raster")
    ta.materialize(series, "picked", basename="picked", overwrite=True, selection=True)
    assert registered("picked") == [(day(1), day(2), 1), (day(12), day(13), 2)]
    result = tgis.open_old_stds("picked", "strds")
    ids = [
        map_.get_id()
        for map_ in result.get_registered_maps_as_objects(order="start_time")
    ]
    assert ids == ["a1@PERMANENT", "picked_1@PERMANENT"]


def test_names_reject_a_mapset(make_series):
    with pytest.raises(ValueError, match="'@'"):
        ta.plan(
            make_series("a", (1, 2), (2, 3)),
            "res",
            names=["x@PERMANENT", "y"],
        )


def test_names_reject_an_illegal_name(make_series):
    """gs.legal_name() refuses a space (checked 2026-10-14: it accepts "1x")"""
    with pytest.raises(ValueError, match="not a legal map name"):
        ta.plan(make_series("a", (1, 2), (2, 3)), "res", names=["a b", "y"])


def test_names_reject_an_input_map(core_session, make_series):
    """A result named like an input of the current mapset would be written
    over it when overwriting"""
    with pytest.raises(ValueError, match="a2"):
        ta.plan(
            make_series("a", (1, 2), (2, 3)) + 1,
            "res",
            names=["fresh", "a2"],
        )


def test_names_accept_the_name_of_an_input_map_of_another_mapset(
    core_session, make_series
):
    """The result goes to the current mapset and leaves a2@other alone"""
    series = make_series("a", (1, 2), (2, 3))
    other = dataclasses.replace(series.slots[1], content=MapRef("a2@other"))
    series = Series((series.slots[0], other), kind="raster")
    chain = ta.plan(series, "res", names=["fresh", "a2"])
    assert [planned.name for planned in chain.maps] == ["fresh", "a2"]


def test_selection_copy_may_take_the_name_of_a_map_of_another_mapset(
    core_session, make_series
):
    kept = dataclasses.replace(make_series("C_", (1, 2)).slots[0], origin="C_1@other")
    moved = ta.retime(make_series("b", (2, 3)), shift="1 day").slots
    series = Series((kept, *moved), kind="raster")
    chain = ta.plan(series, "sel", basename="C", selection=True)
    assert [planned.name for planned in chain.maps] == ["C_1@other", "C_1"]


@pytest.mark.parametrize(
    "name", ["ok", "1x", "a b", "", ".a", "a@b", "a,b", "a/b", 'a"b', "äb", "a=b"]
)
def test_silent_name_check_agrees_with_legal_name(name):
    assert materialize_module._is_legal_name(name) == gs.legal_name(name)


def test_names_reject_time_suffix(make_series):
    with pytest.raises(ValueError, match="time_suffix"):
        ta.plan(
            make_series("a", (1, 2), (2, 3)),
            "res",
            names=["x", "y"],
            time_suffix="gran",
        )


def test_selection_rejects_time_suffix(make_series):
    with pytest.raises(ValueError, match="time_suffix"):
        ta.plan(make_series("a", (1, 2)), "res", selection=True, time_suffix="time")


def test_selection_copy_must_not_take_a_registered_name(core_session, make_series):
    """The first copy of basename C is C_1, the name of a map that reaches
    the result unchanged"""
    kept = make_series("C_", (1, 2)).slots[0]
    moved = ta.retime(make_series("b", (2, 3)), shift="1 day").slots
    series = Series((kept, *moved), kind="raster")
    with pytest.raises(ValueError, match="C_1"):
        ta.plan(series, "sel", basename="C", selection=True)


@pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded:DeprecationWarning"
)
@pytest.mark.parametrize("nprocs", [1, 2])
def test_progress_is_reported_once_per_computed_map(core_session, monkeypatch, nprocs):
    """The percent of the messenger is the only progress a long run shows"""
    reported = []
    msgr = tgis.get_tgis_message_interface()
    monkeypatch.setattr(
        msgr, "percent", lambda current, total, step: reported.append((current, total))
    )
    ta.materialize(ta.source("A") * 3, "progress", overwrite=True, nprocs=nprocs)
    assert reported == [(1, 4), (2, 4), (3, 4), (4, 4)]
