"""Deleting a map with AbstractMapDataset.delete()

delete() removes the map from the temporal database. The datasets that
held the map have to describe what is left of them afterwards: their
number of maps and their time range.
"""

import itertools

import pytest

import grass.temporal as tgis
from grass.tools import Tools

COUNTER = itertools.count(1)


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=20, s=0, e=20, w=0, res=10)
    return tools


@pytest.fixture
def shared(tools):
    """Return a function that makes maps registered in two datasets

    make(2) makes two maps of one day each, on 1 and 2 January 2001, and the
    datasets A and B that both hold them. Afterwards the datasets and the
    maps are removed again.
    """
    made = []

    def make(count):
        number = next(COUNTER)
        maps = [f"del{number}_m{i}" for i in range(1, count + 1)]
        datasets = [f"del{number}_a", f"del{number}_b"]
        for name in datasets:
            tgis.open_new_stds(
                name=name,
                type="strds",
                temporaltype="absolute",
                title="Test",
                descr="Test",
                semantic="mean",
                overwrite=True,
            )
        for index, name in enumerate(maps, start=1):
            tools.r_mapcalc(expression=f"{name} = {index}")
            for dataset in datasets:
                tgis.register_maps_in_space_time_dataset(
                    type="raster",
                    name=dataset,
                    maps=name,
                    start=f"2001-01-0{index} 00:00:00",
                    end=f"2001-01-0{index + 1} 00:00:00",
                )
        made.append((maps, datasets))
        return maps, datasets

    yield make
    for maps, datasets in made:
        for name in datasets:
            tgis.open_old_stds(name, "strds").delete()
        tools.g_remove(flags="f", type="raster", name=",".join(maps))


def _state(dataset):
    stds = tgis.open_old_stds(dataset, "strds")
    stds.select()
    return stds.metadata.get_number_of_maps(), stds.get_temporal_extent_as_tuple()


def _map(name):
    return tgis.RasterDataset(f"{name}@{tgis.get_current_mapset()}")


def test_the_only_map_leaves_empty_datasets(shared):
    maps, datasets = shared(1)

    _map(maps[0]).delete()

    for dataset in datasets:
        assert _state(dataset) == (0, (None, None))


def test_the_datasets_keep_the_range_of_the_maps_that_are_left(shared):
    maps, datasets = shared(2)

    _map(maps[0]).delete()

    for dataset in datasets:
        number, (start, end) = _state(dataset)
        assert number == 1
        assert (start.day, end.day) == (2, 3)


def test_statements_are_returned_and_nothing_is_changed_without_execute(shared):
    maps, datasets = shared(1)

    statement = _map(maps[0]).delete(execute=False)

    assert statement
    for dataset in datasets:
        assert _state(dataset)[0] == 1


def test_update_false_leaves_the_datasets_as_they_were(shared):
    maps, datasets = shared(1)

    _map(maps[0]).delete(update=False)

    for dataset in datasets:
        assert _state(dataset)[0] == 1
