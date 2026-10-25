"""Regression tests for faults of the infrastructure in grass.temporal.core"""

import sys
import warnings

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.grassdb.create import create_mapset
from grass.pygrass.messages import FatalError
from grass.temporal import core

pytestmark = pytest.mark.real_io


def _unset(*names):
    """Remove variables from the gisenv; g.gisenv fails on one that is not set"""
    environment = gs.gisenv()
    for name in names:
        if name in environment:
            gs.run_command("g.gisenv", unset=name)


@pytest.fixture
def warnings_of_init(temporal_module_session, monkeypatch):
    """Record what init() warns about through the messenger of the process

    The messenger server writes to the stderr of its own process, which a
    test cannot capture reliably, so the calls are recorded instead.
    """
    tgis.init(skip_db_init=True)
    recorded = []
    monkeypatch.setattr(
        core.get_tgis_message_interface(), "warning", recorded.append, raising=False
    )
    yield recorded
    _unset("TGIS_DISABLE_MAPSET_CHECK", "TGIS_DISABLE_TIMESTAMP_WRITE")
    tgis.init(skip_db_init=True)


@pytest.mark.parametrize("value", ["True", "1"])
@pytest.mark.parametrize(
    ("name", "getter"),
    [
        ("TGIS_DISABLE_MAPSET_CHECK", tgis.get_enable_mapset_check),
        ("TGIS_DISABLE_TIMESTAMP_WRITE", tgis.get_enable_timestamp_write),
    ],
)
def test_disable_switch_takes_effect(warnings_of_init, name, getter, value):
    gs.run_command("g.gisenv", set=f"{name}={value}")

    tgis.init(skip_db_init=True)

    assert getter() is False
    assert warnings_of_init == [f"{name} is True"]


def test_second_init_without_the_variable_resets_the_switches(warnings_of_init):
    gs.run_command("g.gisenv", set="TGIS_DISABLE_MAPSET_CHECK=True")
    gs.run_command("g.gisenv", set="TGIS_DISABLE_TIMESTAMP_WRITE=1")
    tgis.init(skip_db_init=True)
    assert tgis.get_enable_mapset_check() is False

    _unset("TGIS_DISABLE_MAPSET_CHECK", "TGIS_DISABLE_TIMESTAMP_WRITE")
    tgis.init(skip_db_init=True)

    assert tgis.get_enable_mapset_check() is True
    assert tgis.get_enable_timestamp_write() is True


def test_other_values_leave_the_switches_on(warnings_of_init):
    gs.run_command("g.gisenv", set="TGIS_DISABLE_MAPSET_CHECK=False")

    tgis.init(skip_db_init=True)

    assert tgis.get_enable_mapset_check() is True
    assert warnings_of_init == []


@pytest.fixture
def raise_mode_restored(temporal_module_session):
    """Leave the error mode of the messenger as the session fixture set it"""
    yield
    core.get_tgis_message_interface().set_raise_on_error(True)
    tgis.set_raise_on_error(True)


def test_raise_fatal_error_applies_on_second_init(raise_mode_restored):
    tgis.init(raise_fatal_error=False, skip_db_init=True)
    msgr = core.get_tgis_message_interface()
    msgr.set_raise_on_error(False)

    tgis.init(raise_fatal_error=True, skip_db_init=True)

    with pytest.raises(FatalError, match="raised by the test"):
        core.get_tgis_message_interface().fatal("raised by the test")


def test_second_init_without_raise_fatal_error_switches_the_mode_off(
    raise_mode_restored,
):
    tgis.init(raise_fatal_error=True, skip_db_init=True)

    tgis.init(raise_fatal_error=False, skip_db_init=True)

    assert core.get_tgis_message_interface().get_raise_on_error() is False


@pytest.fixture
def two_projects(tmp_path):
    projects = []
    for name in ("a", "b"):
        gs.create_project(tmp_path / name)
        create_mapset(tmp_path / name / name)
        projects.append(tmp_path / name / name)
    return projects


def test_second_session_has_running_servers(two_projects, monkeypatch):
    """Objects of the first session reach the servers of the second one

    The restart of the servers must not warn about fork() in a process with
    threads. The warning is raised in a thread of the C interface, where it
    reaches sys.unraisablehook instead of the warnings filter.
    """
    unraisable = []
    monkeypatch.setattr(sys, "unraisablehook", unraisable.append)
    project_a, project_b = two_projects
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with gs.setup.init(project_a):
            tgis.init()
            first = tgis.RasterDataset("map@a")
            assert first.ciface.available_mapsets() == ["a", "PERMANENT"]

        with gs.setup.init(project_b):
            tgis.init()
            msgr = core.get_tgis_message_interface()
            server_pid = msgr.server.pid
            assert msgr.server.is_alive()

            assert first.ciface is tgis.get_tgis_c_library_interface()
            assert first.ciface.available_mapsets() == ["b", "PERMANENT"]
            assert first.msgr is msgr
            first.msgr.message("answered by the second session")
            assert msgr.server.pid == server_pid

    forks = [w for w in caught if "fork()" in str(w.message)]
    assert forks == []
    assert not [u for u in unraisable if "fork()" in str(u.exc_value)]


def test_db_connection_defaults_to_the_current_database(temporal_module_session):
    tgis.init()

    connection = core.DBConnection()

    assert connection.dbstring == core.tgis_database_string
    assert connection.dbstring


def test_connect_error_names_the_own_database(temporal_module_session, tmp_path):
    tgis.init(raise_fatal_error=True)
    own = str(tmp_path / "missing_directory" / "own.db")
    connection = core.DBConnection(backend="sqlite", dbstring=own)

    with pytest.raises(FatalError) as error:
        connection.connect()

    assert own in str(error.value)
    assert core.tgis_database_string not in str(error.value)


class _RecordingConnection:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def rollback(self):
        self.calls.append(self.name)


def test_rollback_reaches_the_connection_of_the_mapset(temporal_module_session):
    # DBConnection.rollback() acts for PostgreSQL only, so a transaction of
    # the SQLite default cannot show the delegation; recorders do.
    tgis.init()
    dbif = tgis.SQLDatabaseInterfaceConnection()
    calls = []
    current = dbif.current_mapset
    dbif.connections = {
        current: _RecordingConnection("current", calls),
        "other": _RecordingConnection("other", calls),
    }

    dbif.rollback()
    dbif.rollback(mapset="other")
    dbif.rollback(mapset=b"other")

    assert calls == ["current", "other", "other"]
