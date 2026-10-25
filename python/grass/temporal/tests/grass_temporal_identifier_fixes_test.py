"""Regression tests for faults in identifiers, types and timestamps"""

from datetime import datetime

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


# The mapset after the @ becomes part of the string, so the payload ends in a
# comment; "x' OR '1'='1" would only compare '1' with '1@PERMANENT'.
EVIL = "x' OR 1=1 --"


@pytest.fixture
def victim(temporal_module_session):
    """A registered map and a map object whose identifier is an injection"""
    tgis.init(raise_fatal_error=True)
    mapset = tgis.get_current_mapset()

    def make(name):
        return tgis.RasterBase(
            ident=f"{name}@{mapset}",
            name=name,
            mapset=mapset,
            creator="user",
            creation_time=datetime(2001, 1, 1),
            temporal_type="absolute",
        )

    own = make("b6_victim")
    own.insert()
    evil = make(EVIL)
    evil.ident = f"{EVIL}@{mapset}"
    evil.D["id"] = evil.ident
    yield own, evil
    own.delete()


def test_delete_binds_the_identifier(victim):
    own, evil = victim

    evil.delete()

    assert own.is_in_db()


def test_is_in_db_binds_the_identifier(victim):
    own, evil = victim

    assert evil.is_in_db() is False


def test_select_binds_the_identifier(victim):
    own, evil = victim

    assert evil.select() is False


def test_update_and_update_all_bind_the_identifier(victim):
    own, evil = victim
    evil.set_creator("evil")

    evil.update()
    evil.update_all()

    own.select()
    assert own.D["creator"] == "user"


def test_text_statements_quote_the_identifier(victim):
    own, evil = victim
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        dbif.execute_transaction(evil.get_delete_statement())
    finally:
        dbif.close()

    assert own.is_in_db()
    assert evil.get_select_statement_mogrified().endswith(
        "WHERE id = 'x'' OR 1=1 --@" + tgis.get_current_mapset() + "';\n"
    )


@pytest.mark.parametrize("stds_type", ["rast3d", "raster3d", "raster_3d", "str3ds"])
def test_check_new_stds_knows_every_name_of_the_3d_type(raising, stds_type):
    dataset = tgis.check_new_stds("b8_new", stds_type)

    assert dataset.get_type() == "str3ds"
