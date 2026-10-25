"""Regression tests for faults in identifiers, types and timestamps"""

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError

pytestmark = pytest.mark.real_io


@pytest.fixture
def raising(temporal_module_session):
    tgis.init(raise_fatal_error=True)


@pytest.mark.parametrize("cls", [tgis.RasterBase, tgis.VectorBase, tgis.STRDSBase])
def test_set_id_splits_name_layer_and_mapset(raising, cls):
    base = cls(ident="old@PERMANENT")

    base.set_id("roads:2@PERMANENT")

    assert (base.get_name(), base.get_layer(), base.get_mapset()) == (
        "roads",
        "2",
        "PERMANENT",
    )
    assert base.get_id() == "roads:2@PERMANENT"


def test_constructor_splits_the_identifier_the_same_way(raising):
    base = tgis.VectorBase(ident="roads:2@PERMANENT")

    assert (base.get_name(), base.get_layer(), base.get_mapset()) == (
        "roads",
        "2",
        "PERMANENT",
    )


def test_dataset_set_id_reaches_every_part(raising):
    dataset = tgis.VectorDataset("old@PERMANENT")

    dataset.set_id("roads:2@PERMANENT")

    assert dataset.get_id() == "roads:2@PERMANENT"
    assert dataset.get_name() == "roads"
    assert dataset.get_layer() == "2"
    assert dataset.get_mapset() == "PERMANENT"
    assert dataset.metadata.get_id() == "roads:2@PERMANENT"
    assert dataset.stds_register.get_id() == "roads:2@PERMANENT"


@pytest.mark.parametrize("ident", ["a:b:c@m", "a@b@c", "nomapset"])
def test_wrong_identifier_is_reported(raising, ident):
    base = tgis.RasterBase(ident="old@PERMANENT")

    with pytest.raises(FatalError, match="Wrong identifier"):
        base.set_id(ident)


@pytest.mark.parametrize("name", ["a@b@c", "a:1:2@m"])
def test_split_name_does_not_truncate(raising, name):
    with pytest.raises(FatalError, match="Wrong identifier"):
        tgis.RasterDataset.split_name(name)


def test_split_name_keeps_the_defaults(raising):
    assert tgis.RasterDataset.split_name("a", layer="1", mapset="m") == ("a", "1", "m")
    assert tgis.RasterDataset.split_name("a:2@n", layer="1", mapset="m") == (
        "a",
        "2",
        "n",
    )
