"""Tests of the map loop that several temporal tools share

open_new_map_for() names and opens the new map of each input map, and
register_new_maps() registers the computed maps in the output dataset and
returns the empty ones. The tests compute real maps in a session of the module.
"""

import itertools
import re
from datetime import datetime
from io import StringIO

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal.testing.data import MapSpec, intervals, make_map, register_stds
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

COUNTER = itertools.count(1)


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    return Tools(session=temporal_module_session, overwrite=True, quiet=True)


@pytest.fixture(scope="module")
def monthly(tools):
    """A dataset of two monthly maps and its maps, selected from the database"""
    specs = [
        MapSpec(f"monthly_{number}", number, start, end)
        for number, (start, end) in enumerate(intervals(2), start=1)
    ]
    for spec in specs:
        make_map(tools, "raster", spec.name, spec.value)
    register_stds(tools, "strds", "monthly", specs, via="library")
    dataset = tgis.open_old_stds("monthly", "strds")
    return dataset, dataset.get_registered_maps_as_objects()


@pytest.fixture
def base():
    """A basename that no other test uses"""
    return f"b{next(COUNTER)}"


def open_new(monthly, base, map_type="raster", *, overwrite=False, suffix="num"):
    dataset, maps = monthly
    return [
        tgis.open_new_map_for(
            map,
            base,
            suffix,
            dataset.get_granularity(),
            number,
            map_type=map_type,
            overwrite=overwrite,
            dbif=None,
        )
        for number, map in enumerate(maps, start=1)
    ]


def new_dataset(name, stds_type="strds", *, overwrite=False):
    return tgis.open_new_stds(
        name, stds_type, "absolute", "title", "description", "mean", None, overwrite
    )


def compute_raster(tools, new_maps, expressions):
    for new_map, expression in zip(new_maps, expressions, strict=True):
        tools.r_mapcalc(expression=f"{new_map.get_name()} = {expression}")


def registered_names(dataset):
    return [map.get_name() for map in dataset.get_registered_maps_as_objects()]


def points(tools, name, lines):
    """A point map without attribute table from x,y lines"""
    tools.v_in_ascii(
        input=StringIO("".join(f"{line}\n" for line in lines)),
        output=name,
        format="point",
        separator="comma",
        flags="t",
    )


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01", "2001_02"]),
        ("time", ["2001_01_01T00_00_00", "2001_02_01T00_00_00"]),
        ("num", ["00001", "00002"]),
        ("num%03", ["001", "002"]),
    ],
)
def test_the_new_map_is_named_after_the_input_map(monthly, base, suffix, names):
    new_maps = open_new(monthly, base, suffix=suffix)

    assert [new_map.get_name() for new_map in new_maps] == [
        f"{base}_{name}" for name in names
    ]


@pytest.mark.parametrize("map_type", ["raster", "vector"])
def test_the_new_map_has_the_time_of_the_input_map_and_the_given_type(
    monthly, base, map_type
):
    _dataset, maps = monthly

    new_maps = open_new(monthly, base, map_type)

    assert [new_map.get_temporal_extent_as_tuple() for new_map in new_maps] == [
        map.get_temporal_extent_as_tuple() for map in maps
    ]
    assert {new_map.get_type() for new_map in new_maps} == {map_type}
    assert new_maps[0].get_id() == f"{base}_00001@{tgis.get_current_mapset()}"
    assert not new_maps[0].is_in_db()


def test_a_registered_map_of_the_new_name_stops_without_overwrite(tools, monthly, base):
    taken = open_new(monthly, base)[0]
    compute_raster(tools, [taken], ["1"])
    taken.load()
    taken.insert()

    with pytest.raises(FatalError, match="already in temporal database"):
        open_new(monthly, base)


def test_overwrite_removes_the_entry_of_a_registered_map_of_the_new_name(
    tools, monthly, base
):
    taken = open_new(monthly, base)[0]
    compute_raster(tools, [taken], ["1"])
    taken.load()
    taken.insert()

    new_map = open_new(monthly, base, overwrite=True)[0]

    assert new_map.get_id() == taken.get_id()
    assert not new_map.is_in_db()
    assert not tgis.RasterDataset(taken.get_id()).is_in_db()


def test_an_empty_raster_map_is_returned_and_not_registered(tools, monthly, base):
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps, ["7", "null()"])
    output = new_dataset(base)

    empty = tgis.register_new_maps(new_maps, output, False, None)

    assert [map.get_id() for map in empty] == [new_maps[1].get_id()]
    assert registered_names(output) == [new_maps[0].get_name()]
    assert not new_maps[1].is_in_db()
    # Removing the empty map is up to the caller.
    assert new_maps[1].map_exists()
    first = tgis.RasterDataset(new_maps[0].get_id())
    first.select()
    assert first.metadata.get_min() == 7
    output.select()
    assert (
        output.get_temporal_extent_as_tuple()
        == new_maps[0].get_temporal_extent_as_tuple()
    )


def test_an_empty_raster_map_is_registered_when_asked(tools, monthly, base):
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps, ["7", "null()"])
    output = new_dataset(base)

    empty = tgis.register_new_maps(new_maps, output, True, None)

    assert empty == []
    assert registered_names(output) == [new_map.get_name() for new_map in new_maps]


def test_a_vector_map_without_primitives_is_returned_and_not_registered(
    tools, monthly, base
):
    new_maps = open_new(monthly, base, "vector")
    points(tools, new_maps[0].get_name(), ["1,1"])
    tools.v_edit(tool="create", map=new_maps[1].get_name())
    output = new_dataset(base, "stvds")

    empty = tgis.register_new_maps(new_maps, output, False, None)

    assert [map.get_id() for map in empty] == [new_maps[1].get_id()]
    assert registered_names(output) == [new_maps[0].get_name()]


def test_the_primitives_of_a_vector_map_without_topology_are_counted(
    tools, monthly, base
):
    # Without topology the metadata of the map hold no number of primitives.
    # r.to.vect -b of a raster of only null cells gives a map without points.
    new_maps = open_new(monthly, base, "vector")
    for new_map, value in zip(new_maps, ["1", "null()"], strict=True):
        tools.r_mapcalc(expression=f"{new_map.get_name()} = {value}")
        tools.r_to_vect(
            input=new_map.get_name(),
            output=new_map.get_name(),
            type="point",
            flags="b",
        )
    output = new_dataset(base, "stvds")

    empty = tgis.register_new_maps(new_maps, output, False, None)

    assert [map.get_id() for map in empty] == [new_maps[1].get_id()]
    assert registered_names(output) == [new_maps[0].get_name()]


def test_an_overwritten_output_dataset_holds_only_the_new_maps(tools, monthly, base):
    old_maps = open_new(monthly, f"{base}_old")
    compute_raster(tools, old_maps, ["1", "2"])
    tgis.register_new_maps(old_maps, new_dataset(base), False, None)
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps, ["3", "null()"])
    output = new_dataset(base, overwrite=True)

    empty = tgis.register_new_maps(new_maps, output, False, None)

    assert [map.get_id() for map in empty] == [new_maps[1].get_id()]
    assert registered_names(tgis.open_old_stds(base, "strds")) == [
        new_maps[0].get_name()
    ]


def test_maps_are_added_to_an_existing_output_dataset(tools, monthly, base):
    old_maps = open_new(monthly, f"{base}_old", suffix="time")
    compute_raster(tools, old_maps[:1], ["1"])
    tgis.register_new_maps(old_maps[:1], new_dataset(base), False, None)
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps[1:], ["2"])
    output = tgis.open_old_stds(base, "strds")

    tgis.register_new_maps(new_maps[1:], output, False, None)

    assert registered_names(output) == [
        old_maps[0].get_name(),
        new_maps[1].get_name(),
    ]
    output.select()
    assert output.get_temporal_extent_as_tuple() == (
        old_maps[0].get_temporal_extent_as_tuple()[0],
        new_maps[1].get_temporal_extent_as_tuple()[1],
    )


def test_the_progress_is_shown_every_ten_maps_and_at_the_end(
    tools, base, monkeypatch, capfd
):
    specs = [
        MapSpec(f"{base}_in_{number}", number, start, end)
        for number, (start, end) in enumerate(intervals(12), start=1)
    ]
    for spec in specs:
        make_map(tools, "raster", spec.name, spec.value)
    register_stds(tools, "strds", f"{base}_in", specs, via="library")
    dataset = tgis.open_old_stds(f"{base}_in", "strds")
    new_maps = open_new((dataset, dataset.get_registered_maps_as_objects()), base)
    compute_raster(tools, new_maps, ["1"] * len(new_maps))
    output = new_dataset(base)
    monkeypatch.setenv("GRASS_MESSAGE_FORMAT", "gui")
    capfd.readouterr()

    tgis.register_new_maps(new_maps, output, False, None)

    progress = [
        line
        for line in capfd.readouterr().err.splitlines()
        if line.startswith("GRASS_INFO_PERCENT")
    ]
    # 10 of 12 maps is 83 percent.
    assert progress == ["GRASS_INFO_PERCENT: 83", "GRASS_INFO_PERCENT: 100"]


def cycles_of(dataset, start, end, stop=None, cycle="1 months", offset=None):
    return list(
        tgis.dataset_cycles(
            dataset, start, end, stop=stop, cycle=cycle, offset=offset, dbif=None
        )
    )


def test_the_cycles_run_to_the_end_of_the_data(monthly):
    # The maps cover January and February 2001.
    dataset, _maps = monthly

    assert cycles_of(dataset, datetime(2001, 1, 1), datetime(2001, 2, 1)) == [
        (datetime(2001, 1, 1), datetime(2001, 2, 1)),
        (datetime(2001, 2, 1), datetime(2001, 3, 1)),
    ]


def test_stop_ends_the_last_cycle(monthly):
    dataset, _maps = monthly

    assert cycles_of(
        dataset, datetime(2001, 1, 1), datetime(2001, 2, 1), datetime(2001, 2, 10)
    ) == [
        (datetime(2001, 1, 1), datetime(2001, 2, 1)),
        (datetime(2001, 2, 1), datetime(2001, 2, 10)),
    ]


def test_a_cycle_that_starts_at_the_end_of_the_data_is_left_out(monthly):
    dataset, _maps = monthly

    assert cycles_of(dataset, datetime(2001, 3, 1), datetime(2001, 4, 1)) == []


def test_the_month_cycles_count_from_the_start(monthly):
    # From January 31 the next cycle starts on February 28, then March 31,
    # beyond the data.
    dataset, _maps = monthly

    assert cycles_of(dataset, datetime(2001, 1, 31), datetime(2001, 2, 28)) == [
        (datetime(2001, 1, 31), datetime(2001, 2, 28)),
        (datetime(2001, 2, 28), datetime(2001, 3, 1)),
    ]


@pytest.fixture(scope="module")
def instants(tools):
    """A dataset of two absolute instants, January 1 and 3 2001"""
    specs = [
        MapSpec("instant_1", 1, datetime(2001, 1, 1)),
        MapSpec("instant_2", 2, datetime(2001, 1, 3)),
    ]
    for spec in specs:
        make_map(tools, "raster", spec.name, spec.value)
    register_stds(tools, "strds", "instants", specs, via="library")
    return tgis.open_old_stds("instants", "strds")


def test_an_instant_at_the_end_of_the_data_is_in_a_cycle(instants):
    # The data end with the instant of January 3, one second behind it the
    # cycle that starts on January 3 is still before the end.
    assert cycles_of(
        instants, datetime(2001, 1, 1), datetime(2001, 1, 3), cycle="2 days"
    ) == [
        (datetime(2001, 1, 1), datetime(2001, 1, 3)),
        (datetime(2001, 1, 3), datetime(2001, 1, 3, 0, 0, 1)),
    ]


@pytest.fixture(scope="module")
def relative(tools):
    """A dataset of relative instants at 0, 2 and 4 days"""
    specs = [MapSpec(f"relative_{number}", number, number) for number in (0, 2, 4)]
    for spec in specs:
        make_map(tools, "raster", spec.name, spec.value)
    register_stds(
        tools,
        "strds",
        "relative",
        specs,
        temporaltype="relative",
        unit="days",
        via="library",
    )
    return tgis.open_old_stds("relative", "strds")


def test_relative_cycles_with_an_offset(relative):
    # Cycles of 2 days with a gap of 1: [0, 2), [3, 5), and [6, 8) starts
    # behind the end of the data, 5 (one unit behind the instant at 4).
    assert cycles_of(relative, 0, 2, cycle=2, offset=1) == [(0, 2), (3, 5)]


def test_the_relative_stop_0_cuts_no_cycle(relative):
    # The cycle [-2, 1) starts before the stop 0 and keeps its end; any other
    # stop would cut it.
    assert cycles_of(relative, -2, 1, stop=0, cycle=3, offset=0) == [(-2, 1)]


def test_relative_cycles_end_at_stop(relative):
    assert cycles_of(relative, 0, 3, stop=4, cycle=3, offset=0) == [(0, 3), (3, 4)]


def day_map(name, first, last):
    """A raster map object without data from day first to day last of 2001-01"""
    map_ = tgis.RasterDataset(f"{name}@PERMANENT")
    map_.set_absolute_time(datetime(2001, 1, first), datetime(2001, 1, last))
    return map_


def selected(granule, others):
    tgis.SpatioTemporalTopologyBuilder().build([granule], others)
    return tgis.first_related_map_id(granule)


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [
        # The granule of days 3 to 5 against a map of the same time ...
        (3, 5, "same@PERMANENT"),
        # ... during a longer map, overlapping and overlapped by a map, and
        # containing a shorter map.
        (1, 9, "long@PERMANENT"),
        (4, 7, "late@PERMANENT"),
        (1, 4, "early@PERMANENT"),
        (4, 5, "short@PERMANENT"),
    ],
)
def test_the_map_of_each_relation_is_selected(first, last, expected):
    granule = day_map("granule", 3, 5)
    other = day_map(expected.split("@")[0], first, last)

    assert selected(granule, [other]) == expected


def test_the_relations_are_tried_in_their_order():
    # The granule (days 3 to 5) is during "long", equal to "same", overlaps
    # "late", is overlapped by "early" and contains "short": EQUAL comes first,
    # then DURING, OVERLAPS, OVERLAPPED and CONTAINS.
    others = [
        day_map("short", 4, 5),
        day_map("early", 1, 4),
        day_map("late", 4, 7),
        day_map("long", 1, 9),
        day_map("same", 3, 5),
    ]
    order = []
    while others:
        name = selected(day_map("granule", 3, 5), others)
        order.append(name)
        others = [other for other in others if other.get_id() != name]

    assert order == [
        "same@PERMANENT",
        "long@PERMANENT",
        "late@PERMANENT",
        "early@PERMANENT",
        "short@PERMANENT",
    ]


def test_a_map_that_only_follows_is_not_selected():
    assert selected(day_map("granule", 3, 5), [day_map("after", 5, 7)]) is None


def test_the_result_map_has_the_name_type_and_time_given(monthly, base):
    _dataset, maps = monthly

    result = tgis.open_result_map(maps[1], f"{base}_r", overwrite=False, dbif=None)

    assert result.get_id() == f"{base}_r@{tgis.get_current_mapset()}"
    assert result.get_type() == "raster"
    assert (
        result.get_temporal_extent_as_tuple() == maps[1].get_temporal_extent_as_tuple()
    )
    assert not result.is_in_db()


def test_the_result_map_takes_the_relative_time_and_unit(relative, base):
    input_map = relative.get_registered_maps_as_objects()[1]

    result = tgis.open_result_map(input_map, f"{base}_r", overwrite=False, dbif=None)

    assert result.get_temporal_extent_as_tuple() == (2, None)
    assert result.get_relative_time_unit() == "days"


def test_a_registered_result_map_raises_without_overwrite(tools, monthly, base):
    _dataset, maps = monthly
    taken = open_new(monthly, base)[0]
    compute_raster(tools, [taken], ["1"])
    taken.load()
    taken.insert()

    message = (
        f"Map <{taken.get_id()}> is already registered in the temporal"
        " database, use overwrite flag to overwrite."
    )
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        tgis.open_result_map(maps[0], taken.get_name(), overwrite=False, dbif=None)

    assert taken.is_in_db()


def test_overwrite_removes_the_entry_of_a_registered_result_map(tools, monthly, base):
    _dataset, maps = monthly
    taken = open_new(monthly, base)[0]
    compute_raster(tools, [taken], ["1"])
    taken.load()
    taken.insert()

    result = tgis.open_result_map(maps[0], taken.get_name(), overwrite=True, dbif=None)

    assert result.get_id() == taken.get_id()
    assert not result.is_in_db()
    assert not tgis.RasterDataset(taken.get_id()).is_in_db()


def output_dataset(name):
    return tgis.SpaceTimeRasterDataset(f"{name}@{tgis.get_current_mapset()}")


def test_the_new_output_dataset_takes_the_values_of_the_input(tools, monthly, base):
    dataset, _maps = monthly
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps, ["5", "null()"])

    empty = tgis.register_in_new_stds(
        new_maps, output_dataset(base), dataset, False, overwrite=False, dbif=None
    )

    assert [map.get_id() for map in empty] == [new_maps[1].get_id()]
    output = tgis.open_old_stds(base, "strds")
    assert registered_names(output) == [new_maps[0].get_name()]
    dataset.select()
    assert output.get_initial_values() == dataset.get_initial_values()


def test_overwrite_replaces_the_output_dataset_and_its_maps(tools, monthly, base):
    dataset, _maps = monthly
    old_maps = open_new(monthly, f"{base}_old")
    compute_raster(tools, old_maps, ["1", "2"])
    tgis.register_new_maps(old_maps, new_dataset(base), False, None)
    new_maps = open_new(monthly, base)
    compute_raster(tools, new_maps, ["3", "4"])

    tgis.register_in_new_stds(
        new_maps, output_dataset(base), dataset, False, overwrite=True, dbif=None
    )

    assert registered_names(tgis.open_old_stds(base, "strds")) == [
        new_map.get_name() for new_map in new_maps
    ]


def mapset_maps(tools, map_type):
    return tools.g_list(type=map_type).stdout.split()


@pytest.mark.parametrize("map_type", ["raster", "vector"])
def test_remove_maps_removes_all_given_maps_and_no_other(
    tools, monthly, base, map_type
):
    new_maps = open_new(monthly, base, map_type)
    for new_map in new_maps:
        if map_type == "raster":
            tools.r_mapcalc(expression=f"{new_map.get_name()} = 1")
        else:
            points(tools, new_map.get_name(), ["1,1"])
    kept = f"{base}_kept"
    if map_type == "raster":
        tools.r_mapcalc(expression=f"{kept} = 1")
    else:
        points(tools, kept, ["1,1"])

    tgis.remove_maps(new_maps, map_type)

    assert [name for name in mapset_maps(tools, map_type) if base in name] == [kept]


def test_remove_maps_without_maps_calls_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        tgis.tool_steps.gs, "run_command", lambda *args, **kwargs: calls.append(args)
    )

    tgis.remove_maps([], "raster")

    assert calls == []


def test_the_names_of_a_file_are_stripped_and_blank_lines_left_out(tmp_path):
    path = tmp_path / "names.txt"
    path.write_text("a\n\n  b  \n\t\nc@other")

    assert tgis.names_from_file(str(path)) == ["a", "b", "c@other"]


def test_the_names_of_a_file_with_windows_line_ends(tmp_path):
    path = tmp_path / "names.txt"
    path.write_bytes(b"a\r\nb\r\n")

    assert tgis.names_from_file(str(path)) == ["a", "b"]


def test_an_empty_file_has_no_names(tmp_path):
    path = tmp_path / "names.txt"
    path.write_text("")

    assert tgis.names_from_file(str(path)) == []


@pytest.mark.parametrize("make_directory", [False, True])
def test_a_path_that_is_no_file_raises(tmp_path, make_directory):
    path = tmp_path / "names"
    if make_directory:
        path.mkdir()

    with pytest.raises(ValueError, match=re.escape(f"File <{path}> not found")):
        tgis.names_from_file(str(path))
