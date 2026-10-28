"""Tests of the map loop that several temporal tools share

open_new_map_for() names and opens the new map of each input map, and
register_new_maps() registers the computed maps in the output dataset and
returns the empty ones. The tests compute real maps in a session of the module.
"""

import itertools
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
