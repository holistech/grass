"""Registration of raster and vector maps with register_maps_in_space_time_dataset()

The tests of the earlier gunittest file test_register_function.py. Maps get
their time stamps from the arguments of the call or, without arguments, from
the time stamp that the map already has in the C library; the result is read
back from the temporal database. Each test makes its own maps and datasets
under fresh names, so the tests do not depend on each other or on their
order.

register_map_object_list() is tested here with the objects that the
registration made.
"""

import datetime
import io
import itertools
from types import SimpleNamespace

import pytest

import grass.temporal as tgis
from grass.tools import Tools

COUNTER = itertools.count(1)

# The earlier test of the C library time stamps wrote them with these texts.
DAY_1 = "1 Jan 2001/2 Jan 2001"
DAY_2 = "2 Jan 2001/3 Jan 2001"


def day(number, hour=0, minute=0, second=0):
    return datetime.datetime(2001, 1, number, hour, minute, second)


@pytest.fixture(scope="module")
def region(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=80, s=0, e=120, w=0, t=1, b=0, res=10)
    return tools


@pytest.fixture
def made(region):
    """Make two maps and one empty map of a type, and a dataset of each time

    The maps are called m1, m2 and empty with a number of the test in front
    (the empty map is a raster map of NULL cells or a vector map without
    features). The dataset names are abs and rel with the same number. After
    the test, the datasets and the maps are removed from the temporal database
    and from the mapset.
    """
    made_things = []

    def make(kind):
        number = next(COUNTER)
        names = SimpleNamespace(
            m1=f"reg{number}_m1",
            m2=f"reg{number}_m2",
            empty=f"reg{number}_empty",
            abs=f"reg{number}_abs",
            rel=f"reg{number}_rel",
            kind=kind,
        )
        if kind == "raster":
            region.r_mapcalc(expression=f"{names.m1} = 1")
            region.r_mapcalc(expression=f"{names.m2} = 2")
            region.r_mapcalc(expression=f"{names.empty} = null()")
        else:
            region.v_random(output=names.m1, npoints=5, seed=1)
            region.v_random(output=names.m2, npoints=5, seed=1)
            region.r_mapcalc(expression="nullcells = null()")
            region.r_to_vect(input="nullcells", type="point", output=names.empty)
        stds_type = "strds" if kind == "raster" else "stvds"
        for temporaltype, name in (("absolute", names.abs), ("relative", names.rel)):
            tgis.open_new_stds(
                name=name,
                type=stds_type,
                temporaltype=temporaltype,
                title="Test",
                descr="Test",
                semantic="field",
                overwrite=True,
            )
        made_things.append(names)
        return names

    yield make
    for names in made_things:
        stds_type = "strds" if names.kind == "raster" else "stvds"
        for name in (names.abs, names.rel):
            tgis.open_old_stds(name, stds_type).delete()
        region.t_unregister(
            type=names.kind, maps=f"{names.m1},{names.m2},{names.empty}"
        )
        region.g_remove(
            flags="f",
            type=names.kind,
            name=f"{names.m1},{names.m2},{names.empty}",
        )


def map_of(kind, name):
    cls = tgis.RasterDataset if kind == "raster" else tgis.VectorDataset
    return cls(f"{name}@{tgis.get_current_mapset()}")


def absolute_time(kind, name):
    """The absolute time of a map as the temporal database holds it"""
    time_map = map_of(kind, name)
    time_map.select()
    return time_map.get_absolute_time()


def relative_time(kind, name):
    time_map = map_of(kind, name)
    time_map.select()
    return time_map.get_relative_time()


def dataset_time(kind, name):
    stds = tgis.open_old_stds(name, "strds" if kind == "raster" else "stvds")
    stds.select()
    return stds.get_absolute_time()


def write_timestamp(kind, name, text):
    """Set the time stamp of a map in the C library, as g.timestamp does"""
    ciface = tgis.get_tgis_c_library_interface()
    ciface.call(
        "write_timestamp", kind, name, tgis.get_current_mapset(), timestring=text
    )


KINDS = ["raster", "vector"]


@pytest.mark.parametrize("kind", KINDS)
def test_absolute_time_in_a_dataset(made, kind):
    names = made(kind)
    tgis.register_maps_in_space_time_dataset(
        type=kind,
        name=names.abs,
        maps=f"{names.m1},{names.m2}",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )

    assert absolute_time(kind, names.m1) == (day(1), day(2))
    assert absolute_time(kind, names.m2) == (day(2), day(3))
    assert dataset_time(kind, names.abs) == (day(1), day(3))


@pytest.mark.parametrize("kind", KINDS)
def test_the_time_stamps_of_the_maps_are_used_without_arguments(made, kind):
    names = made(kind)
    write_timestamp(kind, names.m1, DAY_1)
    write_timestamp(kind, names.m2, DAY_2)

    tgis.register_maps_in_space_time_dataset(
        type=kind, name=names.abs, maps=f"{names.m1},{names.m2}"
    )

    assert absolute_time(kind, names.m1) == (day(1), day(2))
    assert absolute_time(kind, names.m2) == (day(2), day(3))
    assert dataset_time(kind, names.abs) == (day(1), day(3))


@pytest.mark.parametrize("kind", KINDS)
def test_arguments_win_over_the_time_stamp_of_the_map(made, kind):
    names = made(kind)
    write_timestamp(kind, names.m1, DAY_1)

    tgis.register_maps_in_space_time_dataset(
        type=kind,
        name=names.abs,
        maps=names.m1,
        start="2001-02-01",
        increment="1 day",
        interval=True,
    )

    february = datetime.datetime(2001, 2, 1), datetime.datetime(2001, 2, 2)
    assert absolute_time(kind, names.m1) == february
    assert dataset_time(kind, names.abs) == february


def test_arguments_win_over_a_relative_time_stamp_of_the_map(made):
    names = made("raster")
    write_timestamp("raster", names.m1, "1 day")

    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=names.abs,
        maps=names.m1,
        start="2001-02-01",
        increment="1 day",
        interval=True,
    )

    february = datetime.datetime(2001, 2, 1), datetime.datetime(2001, 2, 2)
    assert absolute_time("raster", names.m1) == february
    assert dataset_time("raster", names.abs) == february


@pytest.mark.parametrize("kind", KINDS)
def test_maps_registered_without_a_dataset_go_into_one_by_object(made, kind):
    names = made(kind)
    tgis.register_maps_in_space_time_dataset(
        type=kind,
        name=None,
        maps=f"{names.m1},{names.m2}",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )
    assert absolute_time(kind, names.m1) == (day(1), day(2))
    assert absolute_time(kind, names.m2) == (day(2), day(3))

    stds = tgis.open_old_stds(names.abs, "strds" if kind == "raster" else "stvds")
    tgis.register_map_object_list(
        type=kind,
        map_list=[map_of(kind, names.m1), map_of(kind, names.m2)],
        output_stds=stds,
        delete_empty=False,
    )

    assert dataset_time(kind, names.abs) == (day(1), day(3))


def test_empty_raster_maps_are_deleted_on_request(made):
    names = made("raster")
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=None,
        maps=f"{names.m1},{names.m2},{names.empty}",
        start="2001-01-01 10:30:01",
        increment="8 hours",
        interval=False,
    )
    assert absolute_time("raster", names.m1)[0] == day(1, 10, 30, 1)
    assert absolute_time("raster", names.m2)[0] == day(1, 18, 30, 1)
    assert absolute_time("raster", names.empty)[0] == day(2, 2, 30, 1)
    assert map_of("raster", names.empty).map_exists() is True

    maps = [map_of("raster", name) for name in (names.m1, names.m2, names.empty)]
    for registered in maps:
        registered.select()
    stds = tgis.open_old_stds(names.abs, "strds")
    tgis.register_map_object_list(
        type="raster", map_list=maps, output_stds=stds, delete_empty=True
    )

    # Maps at points in time: the end of the dataset is the start of the last
    # map that is left, not the end of a map.
    assert dataset_time("raster", names.abs) == (day(1, 10, 30, 1), day(1, 18, 30, 1))
    assert map_of("raster", names.empty).map_exists() is False


def test_empty_vector_maps_are_deleted_on_request(made):
    names = made("vector")
    tgis.register_maps_in_space_time_dataset(
        type="vector",
        name=None,
        maps=f"{names.m1},{names.m2},{names.empty}",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )
    assert absolute_time("vector", names.m1) == (day(1), day(2))
    assert absolute_time("vector", names.m2) == (day(2), day(3))
    assert absolute_time("vector", names.empty) == (day(3), day(4))
    assert map_of("vector", names.empty).map_exists() is True

    maps = [map_of("vector", name) for name in (names.m1, names.m2, names.empty)]
    for registered in maps:
        registered.select()
    stds = tgis.open_old_stds(names.abs, "stvds")
    tgis.register_map_object_list(
        type="vector", map_list=maps, output_stds=stds, delete_empty=True
    )

    assert dataset_time("vector", names.abs) == (day(1), day(3))
    assert map_of("vector", names.empty).map_exists() is False


def test_time_stamps_with_a_time_of_day_are_used_without_arguments(made):
    names = made("raster")
    write_timestamp("raster", names.m1, "1 Jan 2001 10:30:01")
    write_timestamp("raster", names.m2, "1 Jan 2001 18:30:01")

    tgis.register_maps_in_space_time_dataset(
        type="raster", name=None, maps=f"{names.m1},{names.m2}"
    )

    assert absolute_time("raster", names.m1)[0] == day(1, 10, 30, 1)
    assert absolute_time("raster", names.m2)[0] == day(1, 18, 30, 1)


def test_an_interval_inside_one_second_is_registered_as_a_time_instance(made):
    # The database keeps whole seconds; cut to them, the first interval has
    # equal start and end and becomes a time instance, the second crosses a
    # second boundary and stays an interval.
    names = made("raster")
    rows = io.StringIO(
        f"{names.m1}|2001-01-01 10:00:00.2|2001-01-01 10:00:00.7\n"
        f"{names.m2}|2001-01-01 10:00:01.7|2001-01-01 10:00:02.2\n"
    )

    tgis.register_maps_in_space_time_dataset(type="raster", name=names.abs, file=rows)

    assert absolute_time("raster", names.m1) == (day(1, 10), None)
    assert absolute_time("raster", names.m2) == (day(1, 10, 0, 1), day(1, 10, 0, 2))
    assert dataset_time("raster", names.abs) == (day(1, 10), day(1, 10, 0, 2))


@pytest.mark.parametrize(
    ("end", "expected"),
    [
        (datetime.datetime(2001, 1, 1, 10, 0, 0, 700000), None),
        (datetime.datetime(2001, 1, 1, 10, 0, 0, 200000), None),
        (
            datetime.datetime(2001, 1, 1, 10, 0, 1),
            datetime.datetime(2001, 1, 1, 10, 0, 1),
        ),
    ],
)
def test_set_absolute_time_compares_start_and_end_in_whole_seconds(end, expected):
    item = tgis.RasterDataset("a@PERMANENT")

    assert item.set_absolute_time(datetime.datetime(2001, 1, 1, 10, 0, 0, 200000), end)

    assert item.get_absolute_time()[1] == expected


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (1.2, 1.7, (1, None)),
        (1, 1.9, (1, None)),
        (-0.5, 0.4, (0, None)),
        (0.9, 1.1, (0, 1)),
        (1.7, 2.2, (1, 2)),
        (3, 3, (3, None)),
    ],
)
def test_relative_interval_within_one_unit_becomes_an_instance(start, end, expected):
    item = tgis.RasterDataset("a@PERMANENT")

    assert item.set_relative_time(start, end, "days")

    assert item.get_temporal_extent_as_tuple() == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [(1.7, 1.2), (-0.4, -0.5), (1, 0.5), (2.2, 1.7)],
)
def test_relative_end_before_start_is_refused_within_one_unit(monkeypatch, start, end):
    errors = []
    item = tgis.RasterDataset("a@PERMANENT")
    # Without a session there is no messenger; record what it is given.
    monkeypatch.setattr(
        tgis.RasterDataset,
        "msgr",
        property(lambda self: SimpleNamespace(error=errors.append)),
    )
    before = item.get_temporal_extent_as_tuple()

    assert not item.set_relative_time(start, end, "days")

    assert len(errors) == 1
    assert "End time must be greater than start time" in errors[0]
    assert item.get_temporal_extent_as_tuple() == before


def test_relative_time_in_a_dataset(made):
    names = made("raster")
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=names.rel,
        maps=f"{names.m1},{names.m2}",
        start=0,
        increment=1,
        unit="day",
        interval=True,
    )

    assert relative_time("raster", names.m1) == (0, 1, "day")
    assert relative_time("raster", names.m2) == (1, 2, "day")
    stds = tgis.open_old_stds(names.rel, "strds")
    stds.select()
    assert stds.get_relative_time() == (0, 2, "day")


def test_relative_time_stamps_of_the_maps_are_used_without_arguments(made):
    names = made("raster")
    write_timestamp("raster", names.m1, "1000000 seconds/1500000 seconds")
    write_timestamp("raster", names.m2, "1500000 seconds/2000000 seconds")

    tgis.register_maps_in_space_time_dataset(
        type="raster", name=names.rel, maps=f"{names.m1},{names.m2}"
    )

    assert relative_time("raster", names.m1) == (1000000, 1500000, "seconds")
    assert relative_time("raster", names.m2) == (1500000, 2000000, "seconds")
    stds = tgis.open_old_stds(names.rel, "strds")
    stds.select()
    assert stds.get_relative_time() == (1000000, 2000000, "seconds")


def test_relative_time_without_a_dataset(made):
    names = made("raster")
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=None,
        maps=f"{names.m1},{names.m2}",
        start=0,
        increment=1,
        unit="day",
        interval=True,
    )

    assert relative_time("raster", names.m1) == (0, 1, "day")
    assert relative_time("raster", names.m2) == (1, 2, "day")


def test_relative_time_with_seconds_without_a_dataset(made):
    names = made("raster")
    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name=None,
        maps=f"{names.m1},{names.m2}",
        start=1000000,
        increment=500000,
        unit="seconds",
        interval=True,
    )

    assert relative_time("raster", names.m1) == (1000000, 1500000, "seconds")
    assert relative_time("raster", names.m2) == (1500000, 2000000, "seconds")


def test_relative_time_stamps_of_the_maps_are_used_without_a_dataset(made):
    names = made("raster")
    write_timestamp("raster", names.m1, "1000000 seconds/1500000 seconds")
    write_timestamp("raster", names.m2, "1500000 seconds/2000000 seconds")

    tgis.register_maps_in_space_time_dataset(
        type="raster", name=None, maps=f"{names.m1},{names.m2}"
    )

    assert relative_time("raster", names.m1) == (1000000, 1500000, "seconds")
    assert relative_time("raster", names.m2) == (1500000, 2000000, "seconds")


def test_an_empty_3d_map_is_deleted_on_request(region):
    # The removal of an empty map names the type of g.remove by the kind of
    # the map. A wrong name for 3D rasters would leave the empty map behind,
    # which no other test of the library sees.
    number = next(COUNTER)
    full, empty, stds_name = (
        f"reg{number}_{part}" for part in ("full", "empty", "abs")
    )
    region.r3_mapcalc(expression=f"{full} = 1")
    region.r3_mapcalc(expression=f"{empty} = null()")
    mapset = tgis.get_current_mapset()
    tgis.open_new_stds(
        name=stds_name,
        type="str3ds",
        temporaltype="absolute",
        title="Test",
        descr="Test",
        semantic="field",
        overwrite=True,
    )
    tgis.register_maps_in_space_time_dataset(
        type="raster3d",
        name=None,
        maps=f"{full},{empty}",
        start="2001-01-01",
        increment="1 day",
        interval=True,
    )
    maps = [tgis.Raster3DDataset(f"{name}@{mapset}") for name in (full, empty)]
    for registered in maps:
        registered.select()
    stds = tgis.open_old_stds(stds_name, "str3ds")

    tgis.register_map_object_list(
        type="raster3d", map_list=maps, output_stds=stds, delete_empty=True
    )

    listed = region.g_list(type="raster_3d", pattern=f"reg{number}_*")
    assert listed.stdout.split() == [full]
    assert maps[1].is_in_db(None) is False
    stds.select()
    assert [row["name"] for row in stds.get_registered_maps(columns="name")] == [full]
    stds.delete()
    region.t_unregister(type="raster3d", maps=full)
    region.g_remove(flags="f", type="raster_3d", name=full)
