"""Tests for the six dataset classes built from MapDataset and StdsDataset

The datasets are not registered in a database. The space time datasets look up
the temporal database when they are built, hence the session.
"""

import copy
import pickle

import pytest

import grass.temporal as tgis
from grass.temporal.abstract_dataset import AbstractDataset
from grass.temporal.abstract_map_dataset import AbstractMapDataset
from grass.temporal.abstract_space_time_dataset import AbstractSpaceTimeDataset
from grass.temporal.datasets import MapDataset, StdsDataset
from grass.temporal.kinds import KINDS

pytestmark = pytest.mark.usefixtures("temporal_module_session")

# class, type, class of the maps (of the datasets for a map), register
CLASSES = [
    (tgis.RasterDataset, "raster", tgis.SpaceTimeRasterDataset, None),
    (tgis.Raster3DDataset, "raster3d", tgis.SpaceTimeRaster3DDataset, None),
    (tgis.VectorDataset, "vector", tgis.SpaceTimeVectorDataset, None),
    (tgis.SpaceTimeRasterDataset, "strds", tgis.RasterDataset, "raster"),
    (tgis.SpaceTimeRaster3DDataset, "str3ds", tgis.Raster3DDataset, "raster3d"),
    (tgis.SpaceTimeVectorDataset, "stvds", tgis.VectorDataset, "vector"),
]
IDS = [name for _, name, _, _ in CLASSES]


@pytest.mark.parametrize(("cls", "name", "other", "register"), CLASSES, ids=IDS)
def test_the_type_and_the_bases_of_a_dataset(cls, name, other, register):
    dataset = cls("a@PERMANENT")
    generic = StdsDataset if register else MapDataset
    abstract = AbstractSpaceTimeDataset if register else AbstractMapDataset

    assert dataset.get_type() == name
    assert dataset.kind is KINDS[name]
    assert dataset.is_stds() is bool(register)
    assert isinstance(dataset, generic)
    assert isinstance(dataset, abstract)
    assert isinstance(dataset, AbstractDataset)


@pytest.mark.parametrize(("cls", "name", "other", "register"), CLASSES, ids=IDS)
def test_the_new_instances_are_of_the_public_classes(cls, name, other, register):
    dataset = cls("a@PERMANENT")
    related = (
        dataset.get_new_map_instance("b@PERMANENT")
        if register
        else dataset.get_new_stds_instance("b@PERMANENT")
    )

    assert type(dataset.get_new_instance("b@PERMANENT")) is cls
    assert type(related) is other
    assert related.get_id() == "b@PERMANENT"


def test_a_subclass_makes_the_public_class_not_its_own():
    class Special(tgis.RasterDataset):
        pass

    assert type(Special("a@PERMANENT").get_new_instance("b@PERMANENT")) is (
        tgis.RasterDataset
    )
    assert type(tgis.RasterDataset("a@PERMANENT").get_new_instance("b@c")) is (
        tgis.RasterDataset
    )


@pytest.mark.parametrize(("cls", "name", "other", "register"), CLASSES[3:], ids=IDS[3:])
def test_the_register_of_the_maps_is_in_the_metadata(cls, name, other, register):
    dataset = cls("a@PERMANENT")

    dataset.set_map_register("the_register")

    assert dataset.get_map_register() == "the_register"
    assert getattr(dataset.metadata, f"get_{register}_register")() == "the_register"


@pytest.mark.parametrize(("cls", "name", "other", "register"), CLASSES, ids=IDS)
def test_a_dataset_survives_copy_and_pickle(cls, name, other, register):
    dataset = cls("a@PERMANENT")

    for clone in (
        copy.copy(dataset),
        copy.deepcopy(dataset),
        pickle.loads(pickle.dumps(dataset)),  # noqa: S301
    ):
        assert type(clone) is cls
        assert clone.get_type() == name
        assert clone.get_id() == "a@PERMANENT"
        assert clone.base.D == dataset.base.D


def test_the_abstract_classes_cannot_be_instantiated():
    for abstract in (AbstractDataset, AbstractMapDataset, AbstractSpaceTimeDataset):
        with pytest.raises(TypeError, match="abstract"):
            abstract()
    for generic in (MapDataset, StdsDataset):
        with pytest.raises(TypeError, match="abstract"):
            generic("a@PERMANENT")
