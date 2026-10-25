"""Regression tests for faults of the infrastructure in grass.temporal.core"""

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal import c_libraries_interface, core
from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

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


SECOND_SESSION_SCRIPT = """
import json
import sys
import warnings

import grass.script as gs
import grass.temporal as tgis
from grass.grassdb.create import create_mapset
from grass.temporal import core

unraisable = []
sys.unraisablehook = unraisable.append
root = sys.argv[1]
mapsets = []
for name in ("a", "b"):
    gs.create_project(f"{root}/{name}")
    create_mapset(f"{root}/{name}/{name}")
    mapsets.append(f"{root}/{name}/{name}")

result = {}
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    with gs.setup.init(mapsets[0]):
        tgis.init()
        first = tgis.RasterDataset("map@a")
        result["first"] = first.ciface.available_mapsets()
    with gs.setup.init(mapsets[1]):
        tgis.init()
        msgr = core.get_tgis_message_interface()
        pid = msgr.server.pid
        result["alive"] = msgr.server.is_alive()
        result["same_ciface"] = first.ciface is tgis.get_tgis_c_library_interface()
        result["second"] = first.ciface.available_mapsets()
        result["same_msgr"] = first.msgr is msgr
        first.msgr.message("answered by the second session")
        result["same_pid"] = msgr.server.pid == pid
result["forks"] = [str(w.message) for w in caught if "fork()" in str(w.message)]
result["unraisable"] = [str(u.exc_value) for u in unraisable]
print(json.dumps(result))
"""


def test_second_session_has_running_servers(tmp_path):
    """Objects of the first session reach the servers of the second one

    The restart of the servers must not warn about fork() in a process with
    threads. The warning reaches sys.unraisablehook when a thread of the C
    interface raises it. The check runs in a process of its own: a worker of
    pytest-xdist has threads of its own, so every fork() there warns.
    """
    run = subprocess.run(
        [sys.executable, "-c", SECOND_SESSION_SCRIPT, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout.splitlines()[-1])
    assert result == {
        "first": ["a", "PERMANENT"],
        "alive": True,
        "same_ciface": True,
        "second": ["b", "PERMANENT"],
        "same_msgr": True,
        "same_pid": True,
        "forks": [],
        "unraisable": [],
    }


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


def _open_handles(path):
    """Count the file descriptors of this process that point to the file"""
    target = Path(path).resolve()
    count = 0
    for descriptor in Path("/proc/self/fd").iterdir():
        try:
            if descriptor.readlink().resolve() == target:
                count += 1
        except OSError:
            continue
    return count


def test_close_releases_the_sqlite_file(temporal_module_session):
    tgis.init()
    before = _open_handles(core.tgis_database_string)
    connection = core.DBConnection()
    connection.connect()
    assert _open_handles(core.tgis_database_string) == before + 1

    connection.close()

    assert _open_handles(core.tgis_database_string) == before


def test_interface_close_releases_every_connection(temporal_module_session):
    tgis.init()
    before = _open_handles(core.tgis_database_string)
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    dbif.close()

    assert _open_handles(core.tgis_database_string) == before
    assert dbif.is_connected() is False


BROKEN = "SELECT * FROM table_that_does_not_exist WHERE ("


@pytest.mark.parametrize(
    ("method", "statement_getter", "statement"),
    [
        ("delete", "get_delete_statement", BROKEN),
        ("is_in_db", "get_is_in_db_statement", BROKEN),
        ("select", "get_select_statement", (BROKEN, [])),
        ("insert", "get_insert_statement", (BROKEN, [])),
        ("update", "get_update_statement", (BROKEN, [])),
        ("update_all", "get_update_all_statement", (BROKEN, [])),
    ],
)
def test_failed_statement_does_not_leave_the_connection_open(
    temporal_module_session, monkeypatch, method, statement_getter, statement
):
    tgis.init()
    base = tgis.RasterBase(ident="broken@" + tgis.get_current_mapset())
    monkeypatch.setattr(base, statement_getter, lambda *args: statement)
    before = _open_handles(core.tgis_database_string)

    with pytest.raises(tgis.SQLStatementError) as error:
        getattr(base, method)()

    # The traceback keeps the frame, and with it the connection, alive; a
    # connection that was only forgotten would be closed by garbage collection
    # as soon as the exception is gone and the test would not see it.
    assert error.tb is not None
    assert _open_handles(core.tgis_database_string) == before


@pytest.fixture
def without_metadata_table(tmp_path):
    """A session of its own whose temporal database has lost tgis_metadata"""
    with temporal_session(tmp_path / "project"):
        dbif = tgis.SQLDatabaseInterfaceConnection()
        dbif.connect()
        dbif.execute("DROP TABLE tgis_metadata;")
        dbif.close()
        yield


def test_missing_metadata_table_is_reported_by_get_tgis_metadata(
    without_metadata_table,
):
    with pytest.raises(FatalError, match="Unable to receive temporal database meta"):
        tgis.get_tgis_metadata()


def test_missing_metadata_table_does_not_end_in_a_type_error(without_metadata_table):
    with pytest.raises(FatalError, match="Unable to receive temporal database meta"):
        tgis.get_tgis_db_version_from_metadata()


def test_failed_metadata_read_closes_its_own_connection(without_metadata_table):
    before = _open_handles(core.tgis_database_string)

    with pytest.raises(FatalError) as error:
        tgis.get_tgis_metadata()

    assert error.tb is not None
    assert _open_handles(core.tgis_database_string) == before


@pytest.fixture
def labelled_strds(temporal_module_session):
    tgis.init()
    tools = Tools(session=temporal_module_session, consistent_return_value=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    specs = [
        MapSpec("sl_a", 1, day(0), day(1), semantic_label="S2_1"),
        MapSpec("sl_b", 2, day(1), day(2), semantic_label="S2_2"),
    ]
    create_stds(tools, "strds", "sl_strds", specs, via="library", overwrite=True)
    return tgis.open_old_stds("sl_strds", "strds")


@pytest.fixture
def connection_count(monkeypatch):
    """List that receives one entry for every connect() of the interface"""
    calls = []
    original = core.SQLDatabaseInterfaceConnection.connect

    def counted(self):
        calls.append(self)
        return original(self)

    monkeypatch.setattr(core.SQLDatabaseInterfaceConnection, "connect", counted)
    return calls


def test_semantic_labels_use_one_connection(labelled_strds, connection_count):
    assert labelled_strds.metadata.semantic_labels == "S2_1,S2_2"

    assert len(connection_count) == 1


def test_semantic_labels_use_the_given_connection(labelled_strds, connection_count):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    connection_count.clear()

    assert labelled_strds.metadata.get_semantic_labels(dbif) == "S2_1,S2_2"

    assert connection_count == []
    assert dbif.is_connected()
    dbif.close()


def test_rpc_defs_have_no_name_defined_twice():
    # A second definition replaces the first at run time, so only the source
    # shows it.
    source = Path(c_libraries_interface.__file__).read_text(encoding="utf-8")
    definition = next(
        node
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ClassDef) and node.name == "RPCDefs"
    )
    names = [
        target.id
        for node in definition.body
        if isinstance(node, ast.Assign)
        for target in node.targets
    ]
    assert sorted(name for name in set(names) if names.count(name) > 1) == []


def test_rpc_defs_function_numbers_are_unique():
    numbers = {
        name: value
        for name, value in vars(c_libraries_interface.RPCDefs).items()
        if name.isupper() and not name.startswith("TYPE_")
    }
    assert len(set(numbers.values())) == len(numbers)


@pytest.mark.parametrize("number", [5, 40, 50, 99, -1])
def test_unknown_function_number_is_answered_with_an_error(
    temporal_module_session, number
):
    tgis.init(raise_fatal_error=True)
    ciface = tgis.get_tgis_c_library_interface()
    ciface.check_server()
    pid = ciface.server.pid

    ciface.client_conn.send([number])
    with pytest.raises(FatalError, match="function"):
        ciface.safe_receive("unknown function")

    # The server went on serving; it was not restarted either.
    assert ciface.available_mapsets()
    assert ciface.server.pid == pid
