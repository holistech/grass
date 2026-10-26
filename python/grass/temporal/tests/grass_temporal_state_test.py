"""Test the session state of the temporal framework and its forwarding names"""

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.state import (
    get_enable_mapset_check,
    get_raise_on_error,
    get_tgis_db_version,
    get_tgis_dbmi_paramstyle,
    get_tgis_version,
    set_raise_on_error,
)
from grass.temporal import core, db, schema, state


@pytest.fixture(scope="module", autouse=True)
def session(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


HOMES = (state, db, schema)


@pytest.mark.parametrize("name", core.__all__)
def test_core_forwards_the_object_of_its_home_module(name):
    owners = [module for module in HOMES if hasattr(module, name)]
    assert owners, f"{name} is in no module that core forwards"
    assert getattr(core, name) is getattr(owners[0], name)


def test_core_holds_no_session_state():
    assert not hasattr(core, "message_interface")
    assert not hasattr(core, "tgis_backend")
    assert not hasattr(core, "current_mapset")


def test_init_reads_the_session():
    env = gs.gisenv()
    assert tgis.get_current_mapset() == env["MAPSET"]
    assert state.STATE.current_location == env["LOCATION_NAME"]
    assert state.STATE.current_gisdbase == env["GISDBASE"]
    assert state.STATE.backend == "sqlite"
    assert get_tgis_dbmi_paramstyle() == "qmark"
    assert tgis.get_tgis_database_string().endswith("sqlite.db")


def test_the_getters_read_the_state_object(monkeypatch):
    monkeypatch.setattr(state.STATE, "current_mapset", "elsewhere")
    monkeypatch.setattr(state.STATE, "enable_mapset_check", False)
    assert tgis.get_current_mapset() == "elsewhere"
    assert get_enable_mapset_check() is False
    assert core.get_current_mapset() == "elsewhere"


def test_set_raise_on_error_returns_the_previous_value():
    previous = get_raise_on_error()
    try:
        assert set_raise_on_error(not previous) is previous
        assert state.STATE.raise_on_error is (not previous)
        assert get_raise_on_error() is (not previous)
    finally:
        set_raise_on_error(previous)


def test_versions_are_integers_larger_than_zero():
    assert get_tgis_version() > 0
    assert get_tgis_db_version() > 0


def test_a_new_database_is_created_by_the_steps_of_init():
    """The metadata table that the last step creates holds both versions"""
    rows = {row[0]: row[1] for row in tgis.get_tgis_metadata()}
    assert rows["tgis_version"] == str(get_tgis_version())
    assert rows["tgis_db_version"] == str(get_tgis_db_version())
