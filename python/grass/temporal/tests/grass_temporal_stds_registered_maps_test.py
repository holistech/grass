"""A space time dataset over its registered maps

Registering, unregistering and updating the extent (register_map(),
unregister_map(), contains() of the map register,
update_from_registered_maps()), shifting and snapping (shift(), snap(), shift_map_list(), snap_map_list()),
sampling by granules and the check of the temporal topology. The tests go
through the public methods of a dataset, with real maps in a temporary
project, so that the code behind them can move without changing what it
does.
"""

import copy
import datetime
import itertools
import pickle
import types

import pytest

import grass.temporal as tgis
from grass.temporal import topology
from grass.temporal.stds_map_register import StdsMapRegister
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")

COUNTER = itertools.count(1)


def day(number):
    return datetime.datetime(2001, 1, number)


@pytest.fixture(scope="module")
def region(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=10, s=0, e=10, w=0, res=10)
    return tools


@pytest.fixture
def pair(region):
    """Two raster maps m1, m2 and two empty datasets of absolute and relative time

    Returns a namespace-like dict; the datasets are removed afterwards.
    """
    number = next(COUNTER)
    names = {
        "m1": f"sreg{number}_m1",
        "m2": f"sreg{number}_m2",
        "abs": f"sreg{number}_abs",
        "rel": f"sreg{number}_rel",
        "other": f"sreg{number}_other",
    }
    region.r_mapcalc(expression=f"{names['m1']} = 1")
    region.r_mapcalc(expression=f"{names['m2']} = 2")
    for key, temporaltype in (
        ("abs", "absolute"),
        ("rel", "relative"),
        ("other", "absolute"),
    ):
        tgis.open_new_stds(
            name=names[key],
            type="strds",
            temporaltype=temporaltype,
            title="Test",
            descr="Test",
            semantic="field",
            overwrite=True,
        )
    yield names
    for key in ("abs", "rel", "other"):
        tgis.open_old_stds(names[key], "strds").delete()
    region.t_unregister(type="raster", maps=f"{names['m1']},{names['m2']}")
    region.g_remove(flags="f", type="raster", name=f"{names['m1']},{names['m2']}")


def fill(names, key, **kwargs):
    arguments = {
        "type": "raster",
        "name": names[key],
        "maps": f"{names['m1']},{names['m2']}",
    }
    arguments.update(kwargs)
    tgis.register_maps_in_space_time_dataset(**arguments)


def stds_of(names, key):
    stds = tgis.open_old_stds(names[key], "strds")
    stds.select()
    return stds


def map_of(name):
    return tgis.RasterDataset(f"{name}@{tgis.get_current_mapset()}")


def register_ids(stds):
    rows = stds.get_registered_maps("id", order="id")
    return [row["id"] for row in rows] if rows else []


def test_register_into_an_empty_dataset(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    first = stds_of(pair, "abs")
    mapset = tgis.get_current_mapset()
    assert register_ids(first) == [f"{pair['m1']}@{mapset}", f"{pair['m2']}@{mapset}"]
    other = stds_of(pair, "other")
    assert other.get_map_register() is not None
    assert register_ids(other) == []
    assert other.map_register.contains(f"{pair['m1']}@{mapset}") is False

    stored = map_of(pair["m1"])
    stored.select()
    assert other.register_map(stored) is True

    assert other.map_register.contains(stored.get_id()) is True
    assert other.map_counter == 1
    assert register_ids(other) == [stored.get_id()]


def test_register_into_a_filled_dataset_counts_up(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    only_first = stds_of(pair, "other")
    first = map_of(pair["m1"])
    first.select()
    second = map_of(pair["m2"])
    second.select()
    only_first.register_map(first)

    assert only_first.register_map(second) is True

    assert only_first.map_counter == 2
    assert register_ids(only_first) == [first.get_id(), second.get_id()]

    assert only_first.unregister_map(first) == ""

    assert only_first.map_counter == 1
    assert register_ids(only_first) == [second.get_id()]


def test_registering_a_registered_map_again_gives_false(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    again = map_of(pair["m1"])
    again.select()

    assert stds.register_map(again) is False

    assert len(register_ids(stds)) == 2
    assert stds.map_counter == 0


def test_unregister_the_last_map_empties_the_dataset(pair):
    fill(pair, "other", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "other")
    for name in (pair["m1"], pair["m2"]):
        item = map_of(name)
        item.select()
        assert stds.unregister_map(item) == ""
    stds.update_from_registered_maps()

    stds = stds_of(pair, "other")
    assert register_ids(stds) == []
    assert stds.metadata.get_number_of_maps() == 0
    assert stds.get_temporal_extent_as_tuple() == (None, None)


def test_unregister_a_map_that_is_not_registered(pair):
    stds = stds_of(pair, "other")
    item = map_of(pair["m1"])
    item.select()

    assert stds.unregister_map(item) == ""

    assert stds.map_counter == 0


def test_unregister_without_execute_returns_the_delete_statement(pair):
    fill(pair, "other", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "other")
    item = map_of(pair["m1"])
    item.select()

    statement = stds.unregister_map(item, execute=False)

    assert statement.startswith("DELETE FROM " + stds.get_map_register())
    assert item.get_id() in statement
    assert len(register_ids(stds_of(pair, "other"))) == 2


def test_update_with_absolute_intervals(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")

    stds.update_from_registered_maps()

    stds = stds_of(pair, "abs")
    assert stds.get_absolute_time() == (day(1), day(3))
    assert stds.metadata.get_number_of_maps() == 2
    assert stds.temporal_extent.get_map_time() == "interval"


def test_update_with_absolute_points_takes_the_last_start_as_end(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=False)

    stds = stds_of(pair, "abs")

    assert stds.get_absolute_time() == (day(1), day(2))
    assert stds.temporal_extent.get_map_time() == "point"


def test_update_with_relative_intervals(pair):
    fill(
        pair,
        "rel",
        start="0",
        increment="1",
        unit="days",
        interval=True,
    )

    stds = stds_of(pair, "rel")

    assert stds.get_relative_time() == (0, 2, "days")
    assert stds.metadata.get_number_of_maps() == 2


def test_update_with_relative_points(pair):
    fill(pair, "rel", start="0", increment="3", unit="days", interval=False)

    stds = stds_of(pair, "rel")

    assert stds.get_relative_time() == (0, 3, "days")
    assert stds.temporal_extent.get_map_time() == "point"


def test_update_of_an_empty_dataset_changes_nothing(pair):
    stds = stds_of(pair, "other")

    stds.update_from_registered_maps()

    stds = stds_of(pair, "other")
    assert stds.metadata.get_number_of_maps() == 0
    assert stds.get_temporal_extent_as_tuple() == (None, None)


def timed_map(name, start, end, unit=None):
    """A map object that holds a time without a database"""
    item = tgis.RasterDataset(f"{name}@PERMANENT")
    if unit is None:
        assert item.set_absolute_time(start, end)
    else:
        assert item.set_relative_time(start, end, unit)
    return item


def extents(maps):
    return [item.get_temporal_extent_as_tuple() for item in maps]


def test_shift_map_list_moves_absolute_maps():
    maps = [
        timed_map("a", day(1), day(2)),
        timed_map("b", day(2), None),
    ]

    shifted = tgis.AbstractSpaceTimeDataset.shift_map_list(maps, "2 days")

    assert extents(shifted) == [(day(3), day(4)), (day(4), None)]


def test_shift_map_list_moves_relative_maps():
    maps = [timed_map("a", 1, 2, "days"), timed_map("b", 3, None, "days")]

    shifted = tgis.AbstractSpaceTimeDataset.shift_map_list(maps, 5)

    assert extents(shifted) == [(6, 7), (8, None)]


def test_shift_map_list_without_maps_or_with_a_wrong_granularity():
    assert tgis.AbstractSpaceTimeDataset.shift_map_list(None, "1 day") is None
    maps = [timed_map("a", day(1), day(2))]
    assert tgis.AbstractSpaceTimeDataset.shift_map_list(maps, "1 fortnight") is None
    assert extents(maps) == [(day(1), day(2))]


def test_snap_map_list_without_maps_is_none():
    assert tgis.AbstractSpaceTimeDataset.snap_map_list(None) is None
    assert tgis.AbstractSpaceTimeDataset.snap_map_list([]) is None


def test_snap_map_list_closes_gaps_and_sorts():
    maps = [
        timed_map("c", day(5), day(6)),
        timed_map("a", day(1), day(2)),
        timed_map("b", day(3), None),
    ]

    snapped = tgis.AbstractSpaceTimeDataset.snap_map_list(maps)

    assert [item.get_name() for item in snapped] == ["a", "b", "c"]
    assert extents(snapped) == [
        (day(1), day(3)),
        (day(3), day(5)),
        (day(5), day(6)),
    ]


def test_snap_map_list_keeps_the_end_of_maps_that_start_together():
    maps = [
        timed_map("a", day(1), day(4)),
        timed_map("b", day(1), day(2)),
        timed_map("c", day(5), day(6)),
    ]

    snapped = tgis.AbstractSpaceTimeDataset.snap_map_list(maps)

    assert extents(snapped) == [
        (day(1), day(4)),
        (day(1), day(5)),
        (day(5), day(6)),
    ]


def test_snap_map_list_gives_the_last_instant_the_granularity_as_length():
    maps = [timed_map("a", day(1), None), timed_map("b", day(2), None)]

    snapped = tgis.AbstractSpaceTimeDataset.snap_map_list(maps)

    assert extents(snapped) == [(day(1), day(2)), (day(2), day(3))]


def test_snap_map_list_of_relative_maps():
    maps = [timed_map("a", 0, None, "days"), timed_map("b", 3, None, "days")]

    snapped = tgis.AbstractSpaceTimeDataset.snap_map_list(maps)

    assert extents(snapped) == [(0, 3), (3, 6)]


def times_of(names, key):
    stds = stds_of(names, key)
    maps = stds.get_registered_maps_as_objects(order="start_time")
    return extents(maps)


def test_shift_a_dataset_moves_its_maps_and_its_extent(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")

    assert stds.shift("3 days") is True

    assert times_of(pair, "abs") == [(day(4), day(5)), (day(5), day(6))]
    assert stds_of(pair, "abs").get_absolute_time() == (day(4), day(6))


def test_shift_a_relative_dataset(pair):
    fill(pair, "rel", start="0", increment="1", unit="days", interval=True)
    stds = stds_of(pair, "rel")

    assert stds.shift("10") is True

    assert times_of(pair, "rel") == [(10, 11), (11, 12)]


def test_shift_with_a_wrong_granularity_is_false(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    assert stds_of(pair, "abs").shift("1 fortnight") is False
    assert times_of(pair, "abs") == [(day(1), day(2)), (day(2), day(3))]


def test_snap_a_dataset_of_instants_gives_them_the_granularity(pair):
    fill(pair, "abs", start="2001-01-01", increment="2 days", interval=False)
    stds = stds_of(pair, "abs")

    stds.snap()

    assert times_of(pair, "abs") == [(day(1), day(3)), (day(3), day(5))]
    assert stds_of(pair, "abs").get_absolute_time() == (day(1), day(5))


def test_snap_a_relative_dataset_of_instants(pair):
    fill(pair, "rel", start="0", increment="2", unit="days", interval=False)

    stds_of(pair, "rel").snap()

    assert times_of(pair, "rel") == [(0, 2), (2, 4)]


def test_update_map_timestamps_changes_the_maps_and_other_datasets(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    fill(pair, "other", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    maps = stds.get_registered_maps_as_objects(order="start_time")

    stds.update_map_timestamps(
        maps, [(day(10), day(11)), (day(11), day(13))], stds_dbif()
    )

    assert times_of(pair, "abs") == [(day(10), day(11)), (day(11), day(13))]
    assert stds_of(pair, "abs").get_absolute_time() == (day(10), day(13))
    assert stds_of(pair, "other").get_absolute_time() == (day(10), day(13))


def stds_dbif():
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    return dbif


def gap_ids(granules):
    return [[item.get_id() for item in granule] for granule in granules]


@pytest.mark.parametrize(
    ("spans", "expected"),
    [
        # The granule (0, 4) is equal to one map: the equal map wins over the
        # map that contains the granule.
        ([(-1, 9), (0, 4)], "m1"),
        # A map that contains the granule wins over one that overlaps it.
        ([(-1, 9), (3, 6)], "m0"),
        # A map that overlaps the granule wins over one inside it.
        ([(1, 2), (3, 6)], "m1"),
        # "overlaps" is tried before "overlapped".
        ([(-2, 2), (3, 6)], "m1"),
    ],
)
def test_resample_takes_the_relations_in_a_fixed_order(spans, expected):
    maps = [timed_map(f"m{i}", a, b, "days") for i, (a, b) in enumerate(spans)]

    granules = tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        maps, 0, 4, 4
    )

    assert gap_ids(granules) == [[f"{expected}@PERMANENT"]]


def test_resample_without_maps_is_none():
    assert (
        tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity([], 0, 4, 1)
        is None
    )


def test_resample_with_a_granule_that_cuts_a_map_in_half_uses_overlap():
    first = timed_map("first", 0, 3, "days")
    granules = tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        [first], 2, 4, 2
    )

    assert gap_ids(granules) == [["first@PERMANENT"]]


def test_registered_maps_by_granularity_of_an_interval_dataset(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    mapset = tgis.get_current_mapset()

    granules = stds.get_registered_maps_as_objects_by_granularity()

    assert gap_ids(granules) == [[f"{pair['m1']}@{mapset}"], [f"{pair['m2']}@{mapset}"]]


def test_registered_maps_by_granularity_with_a_smaller_granule(pair):
    fill(pair, "abs", start="2001-01-01", increment="2 days", interval=True)
    stds = stds_of(pair, "abs")
    mapset = tgis.get_current_mapset()

    granules = stds.get_registered_maps_as_objects_by_granularity(gran="1 day")

    assert (
        gap_ids(granules)
        == [[f"{pair['m1']}@{mapset}"]] * 2 + [[f"{pair['m2']}@{mapset}"]] * 2
    )


def test_registered_maps_by_granularity_of_instants_reaches_the_last_one(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=False)
    stds = stds_of(pair, "abs")
    mapset = tgis.get_current_mapset()

    granules = stds.get_registered_maps_as_objects_by_granularity()

    assert gap_ids(granules) == [[f"{pair['m1']}@{mapset}"], [f"{pair['m2']}@{mapset}"]]


def test_registered_maps_by_granularity_relative(pair):
    fill(pair, "rel", start="0", increment="2", unit="days", interval=True)
    stds = stds_of(pair, "rel")

    granules = stds.get_registered_maps_as_objects_by_granularity(gran=1)

    assert len(granules) == 4


def test_registered_maps_by_granularity_of_an_empty_dataset_is_none(pair):
    stds = stds_of(pair, "other")

    assert stds.get_registered_maps_as_objects_by_granularity(gran="1 day") is None


def test_registered_maps_by_granularity_rejects_a_wrong_granularity(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")

    with pytest.raises(tgis.FatalError, match="Wrong granularity"):
        stds.get_registered_maps_as_objects_by_granularity(gran="1 fortnight")


def test_registered_maps_by_granularity_filters_with_where(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    mapset = tgis.get_current_mapset()

    granules = stds.get_registered_maps_as_objects_by_granularity(
        where=f"name = '{pair['m2']}'"
    )

    assert gap_ids(granules) == [[f"{pair['m2']}@{mapset}"]]


FORBIDDEN_INTERVAL = {
    "equal": [(1, 3), (1, 3)],
    "during": [(1, 5), (2, 3)],
    "overlaps": [(1, 4), (3, 6)],
    "starts": [(1, 3), (1, 5)],
    "finishes": [(2, 5), (4, 5)],
}
ALLOWED_INTERVAL = {
    "follows": [(1, 2), (2, 3)],
    "precedes": [(1, 2), (4, 5)],
}


@pytest.mark.parametrize("relation", sorted(FORBIDDEN_INTERVAL))
def test_interval_topology_with_a_forbidden_relation_is_wrong(pair, relation):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    maps = [
        timed_map(f"t{i}", day(start), day(end))
        for i, (start, end) in enumerate(FORBIDDEN_INTERVAL[relation])
    ]

    assert stds.check_temporal_topology(maps=maps) is False


@pytest.mark.parametrize("relation", sorted(ALLOWED_INTERVAL))
def test_interval_topology_with_an_allowed_relation_is_right(pair, relation):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    maps = [
        timed_map(f"t{i}", day(start), day(end))
        for i, (start, end) in enumerate(ALLOWED_INTERVAL[relation])
    ]

    assert stds.check_temporal_topology(maps=maps) is True


def test_topology_of_the_registered_maps_is_read_when_no_list_is_given(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)

    assert stds_of(pair, "abs").check_temporal_topology() is True


def test_point_topology_forbids_only_equal_instants(pair):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=False)
    stds = stds_of(pair, "abs")
    equal = [timed_map("p1", day(1), None), timed_map("p2", day(1), None)]
    apart = [timed_map("p1", day(1), None), timed_map("p2", day(2), None)]

    assert stds.check_temporal_topology(maps=equal) is False
    assert stds.check_temporal_topology(maps=apart) is True


def test_topology_of_a_dataset_without_maps_is_wrong(pair):
    # No map pair, hence no relation counts, hence not "correct".
    assert stds_of(pair, "other").check_temporal_topology() is False


@pytest.mark.parametrize(
    "name",
    [
        "x; DROP TABLE raster_base",
        "raster_map_register_" + "a" * 32 + " ",
        "raster_map_register_a-b",
        'raster_map_register_"x"',
        # SQLite does not read a name that starts with a digit as a name.
        "2020_precip_PERMANENT_raster_register",
    ],
)
def test_a_register_table_name_of_another_form_is_refused(pair, name):
    stds = stds_of(pair, "abs")
    stds.set_map_register(name)

    with pytest.raises(tgis.FatalError, match="Invalid name"):
        stds.get_registered_maps("id")
    with pytest.raises(tgis.FatalError, match="Invalid name") as refused:
        stds.map_register.contains("a@PERMANENT")
    # The refusal is the whole message; the check that found the name wrong
    # does not show up as a second traceback.
    assert refused.value.__context__ is None


def test_a_register_table_of_an_older_form_is_used(pair):
    # GRASS 7 made the name from a uuid with underscores instead of the plain
    # hex digits, and a database may still hold such tables.
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")
    old = "raster_map_register_1B2C3D4E_5f6a_4b7c_8d9e_0f1a2b3c4d5e"
    dbif = stds_dbif()
    dbif.execute_transaction(
        f'ALTER TABLE {stds.get_map_register()} RENAME TO "{old}";'
    )
    stds.set_map_register(old)
    stds.update(dbif=dbif)
    dbif.close()

    stds = stds_of(pair, "abs")
    assert stds.get_map_register() == old
    assert len(register_ids(stds)) == 2
    assert stds.map_register.contains(register_ids(stds)[0]) is True


@pytest.mark.parametrize("how", ["copy", "deepcopy", "pickle"])
def test_a_copy_of_a_dataset_has_a_register_of_its_own(pair, how):
    fill(pair, "abs", start="2001-01-01", increment="1 day", interval=True)
    stds = stds_of(pair, "abs")

    if how == "pickle":
        clone = pickle.loads(pickle.dumps(stds))  # noqa: S301
    else:
        clone = getattr(copy, how)(stds)

    assert clone.map_register.table_name() == stds.map_register.table_name()
    assert clone.map_register._stds is clone
    assert register_ids(clone) == register_ids(stds)


def test_a_new_register_name_has_the_form_of_the_check(pair):
    stds = stds_of(pair, "abs")

    name = stds.map_register.create_name()

    assert name.startswith("raster_map_register_")
    assert len(name) == len("raster_map_register_") + 32
    assert name != stds.map_register.create_name()
    assert stds.map_register.table_name() == stds.get_map_register()


def test_resample_counts_the_months_from_the_start_not_from_the_last_cut():
    # From 31 January the granules start on 28 February and 31 March; a
    # count from the cut of the previous granule would give 28 March.
    whole = timed_map(
        "whole", datetime.datetime(2001, 1, 31), datetime.datetime(2001, 4, 30)
    )

    granules = tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        [whole],
        datetime.datetime(2001, 1, 31),
        datetime.datetime(2001, 4, 30),
        "1 month",
    )

    assert [granule[0].get_temporal_extent_as_tuple() for granule in granules] == [
        (datetime.datetime(2001, 1, 31), datetime.datetime(2001, 2, 28)),
        (datetime.datetime(2001, 2, 28), datetime.datetime(2001, 3, 31)),
        (datetime.datetime(2001, 3, 31), datetime.datetime(2001, 4, 30)),
    ]


def test_registered_maps_by_granularity_of_relative_instants_reaches_the_last(pair):
    fill(pair, "rel", start="0", increment="2", unit="days", interval=False)
    stds = stds_of(pair, "rel")
    mapset = tgis.get_current_mapset()

    granules = stds.get_registered_maps_as_objects_by_granularity(gran=1)

    # The instants at 0 and 2 each fall in the granule that starts there
    assert [[item.get_id() for item in granule][:1] for granule in granules] == [
        [f"{pair['m1']}@{mapset}"],
        [None],
        [f"{pair['m2']}@{mapset}"],
    ]


ALL_RELATIONS = (
    "equal",
    "during",
    "contains",
    "overlaps",
    "overlapped",
    "starts",
    "finishes",
    "started",
    "finished",
    "follows",
    "precedes",
)
FORBIDDEN_FOR_INTERVALS = ALL_RELATIONS[:9]


@pytest.mark.parametrize("map_time", ["interval", "mixed"])
@pytest.mark.parametrize("relation", ALL_RELATIONS)
def test_counted_relations_against_the_rules_for_intervals(map_time, relation):
    counts = dict.fromkeys(ALL_RELATIONS, 0)
    counts[relation] = 3

    result = topology.has_correct_temporal_topology(counts, map_time)

    assert result is (relation not in FORBIDDEN_FOR_INTERVALS)


@pytest.mark.parametrize("relation", ALL_RELATIONS)
def test_counted_relations_against_the_rules_for_instants(relation):
    counts = dict.fromkeys(ALL_RELATIONS, 0)
    counts[relation] = 3

    assert topology.has_correct_temporal_topology(counts, "point") is (
        relation != "equal"
    )


@pytest.mark.parametrize("map_time", ["interval", "mixed", "point"])
def test_a_missing_count_is_no_relation(map_time):
    assert topology.has_correct_temporal_topology({}, map_time) is True


@pytest.mark.parametrize("map_time", ["invalid", None, "fuzzy"])
def test_other_map_times_have_no_correct_topology(map_time):
    assert topology.has_correct_temporal_topology({}, map_time) is False


def test_no_counted_relations_is_no_correct_topology():
    assert topology.has_correct_temporal_topology(None, "interval") is False


def test_shifting_an_empty_list_of_maps_gives_none():
    assert tgis.AbstractSpaceTimeDataset.shift_map_list([], "1 day") is None


def test_shifting_a_dataset_without_maps_gives_false(pair):
    stds = stds_of(pair, "other")

    assert stds.shift("1 day") is False
    assert register_ids(stds) == []


def test_snapping_a_dataset_without_maps_changes_nothing(pair):
    stds = stds_of(pair, "other")

    assert stds.snap() is None
    assert register_ids(stds) == []


class ScriptRecorder:
    """Stand-in for the database interface that keeps the script it is given"""

    def __init__(self):
        self.script = None

    def is_connected(self):
        return True

    def execute(self, statement, *args, **kwargs):
        """Take the query for the database version; the answer is version 3"""

    def fetchall(self, *args, **kwargs):
        return [("tgis_db_version", "3")]

    def execute_transaction(self, script, mapset=None):
        self.script = script


def update_script(dataset_id):
    """The SQL script that the update templates give for a strds of this id"""
    stds = types.SimpleNamespace(
        base=types.SimpleNamespace(get_id=lambda: dataset_id, mapset="PERMANENT"),
        get_type=lambda: "strds",
    )
    recorder = ScriptRecorder()
    StdsMapRegister(stds)._run_update_templates(recorder, "reg_table", "raster")
    return recorder.script


def test_the_update_templates_quote_the_dataset_id():
    script = update_script("a'b@m")

    assert "id = 'a''b@m';" in script
    assert "'a'b@m'" not in script


# Text of the update templates for ds@PERMANENT as they were filled while the
# templates held the quotes themselves, taken on 2026-10-27 by filling
# lib/temporal/SQL/update_stds_spatial_temporal_extent_template.sql and
# update_strds_metadata_template.sql of commit b2ca025b24 (git show) with the
# placeholder code of that commit. Written out, not computed from the
# templates, so that a change of the templates cannot move the expectation.
OLD_UPDATE_SCRIPT = """--#############################################################################
-- This SQL script is to update the spatial and temporal extent as well as
-- the modification time and revision of a space time dataset. This script
-- should be called when maps inserted or deleted in a space time dataset.
--
--
-- Author: Soeren Gebbert soerengebbert <at> googlemail <dot> com
-- UPDATE FROM syntax: Stefan Blumentrath stefan  <dot>  blumentrath <at> gmx <dot> de
--#############################################################################

-- reg_table is a placeholder for specific stds map register table name (SQL compliant)
-- ds@PERMANENT is a placeholder for specific stds id: name@mapset
-- raster is a placeholder for specific map type: raster, raster3d or vector
-- strds is a placeholder for specific space-time dataset type: strds, str3ds, stvds

-- UPDATE strds_base SET modification_time = datetime("NOW") WHERE id = 'ds@PERMANENT';
-- UPDATE strds_base SET revision = (revision + 1) WHERE id = 'ds@PERMANENT';

-- Number of registered maps
UPDATE strds_metadata SET number_of_maps =
       (SELECT count(id) FROM reg_table)
       WHERE id = 'ds@PERMANENT';

-- Update the temporal extent
UPDATE strds_absolute_time
   SET
       start_time = new_stats.start_time_new,
       end_time = new_stats.end_time_new
  FROM
       (SELECT
           min(start_time) AS start_time_new,
           max(end_time) AS end_time_new
        FROM
            reg_table INNER JOIN
            raster_absolute_time ON
            reg_table.id = raster_absolute_time.id
       ) AS new_stats
 WHERE strds_absolute_time.id = 'ds@PERMANENT';

UPDATE strds_relative_time
   SET
       start_time = new_stats.start_time_new,
       end_time = new_stats.end_time_new
  FROM
       (SELECT
           min(start_time) AS start_time_new,
           max(end_time) AS end_time_new
       FROM
           reg_table INNER JOIN
           raster_relative_time ON
           reg_table.id = raster_relative_time.id
       ) AS new_stats
 WHERE strds_relative_time.id = 'ds@PERMANENT';

-- Update the spatial extent
UPDATE strds_spatial_extent
   SET
       north = new_stats.north_new,
       south = new_stats.south_new,
       east = new_stats.east_new,
       west = new_stats.west_new,
       top = new_stats.top_new,
       bottom = new_stats.bottom_new,
       proj = new_stats.proj_new
  FROM
       (SELECT
           max(north) AS north_new,
           min(south) AS south_new,
           max(east) AS east_new,
           min(west) AS west_new,
           max(top) AS top_new,
           min(bottom) AS bottom_new,
           min(proj) AS proj_new
       FROM
           reg_table INNER JOIN
           raster_spatial_extent ON
           reg_table.id = raster_spatial_extent.id
       ) AS new_stats
 WHERE strds_spatial_extent.id = 'ds@PERMANENT';

--#############################################################################
-- This SQL is to update a space-time raster dataset metadata
--
-- Author: Soeren Gebbert soerengebbert <at> googlemail <dot> com
-- UPDATE FROM syntax: Stefan Blumentrath stefan  <dot>  blumentrath <at> gmx <dot> de
--#############################################################################

-- reg_table is a placeholder for specific stds map register table name (SQL compliant)
-- ds@PERMANENT is a placeholder for specific stds id: name@mapset
-- for TGIS < 3 the lines for semantic labels get replaced / commented out

UPDATE strds_metadata
   SET
       -- Update the number of registered semantic labels
       number_of_semantic_labels = number_of_semantic_labels_new,
       -- Update the min and max values
       min_min = new_stats.min_min_new,
       min_max = new_stats.min_max_new,
       max_min = new_stats.max_min_new,
       max_max = new_stats.max_max_new,
       -- Update the resolution
       nsres_min = new_stats.nsres_min_new,
       nsres_max = new_stats.nsres_max_new,
       ewres_min = new_stats.ewres_min_new,
       ewres_max = new_stats.ewres_max_new
  FROM
       (SELECT
            count(distinct semantic_label) AS number_of_semantic_labels_new,
            min(min) AS min_min_new,
            max(min) AS min_max_new,
            min(max) AS max_min_new,
            max(max) AS max_max_new,
            min(nsres) AS nsres_min_new,
            max(nsres) AS nsres_max_new,
            min(ewres) AS ewres_min_new,
            max(ewres) AS ewres_max_new
        FROM
            reg_table INNER JOIN
            raster_metadata ON
            reg_table.id = raster_metadata.id
       ) AS new_stats
 WHERE strds_metadata.id = 'ds@PERMANENT';

"""


def without_comments(script):
    return [line for line in script.splitlines() if not line.lstrip().startswith("--")]


def test_the_update_sql_of_a_valid_id_is_unchanged():
    # The comment that explains the placeholder holds the placeholder, so the
    # filled-in identifier is quoted there now. Comments do not run; the
    # statements are compared line by line.
    assert without_comments(update_script("ds@PERMANENT")) == without_comments(
        OLD_UPDATE_SCRIPT
    )
