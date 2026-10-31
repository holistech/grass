"""Test the support for running temporal tests against a PostgreSQL server

The tests marked postgresql need the server named by
GRASS_TEMPORAL_TEST_POSTGRESQL and are skipped without one.
"""

import contextlib
import datetime
import getpass
import os
import re
import sqlite3
import tempfile
import types

import pytest

from grass.temporal.testing import data, postgresql, versions
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


def database_names(server):
    import psycopg2

    connection = psycopg2.connect(server)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT datname FROM pg_database")
            return {row[0] for row in cursor.fetchall()}
    finally:
        connection.close()


def dbname_of(dsn):
    import psycopg2.extensions

    return psycopg2.extensions.parse_dsn(dsn)["dbname"]


@pytest.mark.postgresql
def test_fresh_databases_of_two_calls_differ_and_are_dropped():
    server = postgresql.server_or_skip()
    with (
        postgresql.fresh_database("t") as first,
        postgresql.fresh_database("t") as second,
    ):
        assert first != second
        names = {dbname_of(first), dbname_of(second)}
        assert all(name.startswith("t_") for name in names)
        assert names <= database_names(server)
    assert not names & database_names(server)


def fail_inside_a_fresh_database(server, seen):
    with postgresql.fresh_database("t") as dsn:
        seen.append(dbname_of(dsn))
        assert seen[0] in database_names(server)
        msg = "test failure"
        raise RuntimeError(msg)


@pytest.mark.postgresql
def test_a_fresh_database_is_dropped_when_the_block_raises():
    server = postgresql.server_or_skip()
    seen = []
    with pytest.raises(RuntimeError, match="test failure"):
        fail_inside_a_fresh_database(server, seen)
    assert seen
    assert seen[0] not in database_names(server)


@pytest.mark.postgresql
def test_the_fixture_yields_a_database_that_accepts_connections(postgresql_database):
    import psycopg2

    connection = psycopg2.connect(postgresql_database)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database()")
            assert cursor.fetchone()[0].startswith("t_")
    finally:
        connection.close()


def test_without_the_variable_the_fixture_skips(monkeypatch):
    monkeypatch.delenv(postgresql.SERVER_VARIABLE, raising=False)
    assert postgresql.server_string() is None
    with pytest.raises(pytest.skip.Exception):
        postgresql.server_or_skip()


def test_an_empty_variable_counts_as_unset(monkeypatch):
    monkeypatch.setenv(postgresql.SERVER_VARIABLE, "")
    assert postgresql.server_string() is None
    with pytest.raises(pytest.skip.Exception):
        postgresql.server_or_skip()


def test_an_unreachable_server_skips(monkeypatch):
    # Port 1 accepts no connection, so a stale variable skips, not errors
    monkeypatch.setenv(
        postgresql.SERVER_VARIABLE, "host=127.0.0.1 port=1 user=postgres"
    )
    with pytest.raises(pytest.skip.Exception):
        postgresql.server_or_skip()


def test_rows_of_a_sqlite_database_mask_times_and_users(tmp_path):
    import grass.temporal as tgis

    with temporal_session(tmp_path / "project") as session:
        postgresql.run_scenario(Tools(session=session, consistent_return_value=True))
        # run_scenario removes its datasets; one that stays shows the rows
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        tools.r_mapcalc(expression="kept = 1")
        tools.t_create(
            type="strds", temporaltype="absolute", output="kept_ds", title="k",
            description="k",
        )  # fmt: skip
        tools.t_register(
            type="raster", input="kept_ds", maps="kept", start="2001-01-01"
        )
        database = tgis.get_tgis_database_string()
        rows = postgresql.rows_of("sqlite", database)
        with contextlib.closing(sqlite3.connect(database)) as connection:
            view_columns = [
                row[1]
                for row in connection.execute("PRAGMA table_info(vector_view_abs_time)")
            ]

    assert [row for row in rows["strds_base"] if row[0].startswith("scenario")] == []
    assert all("<masked>" in row for row in rows["strds_base"])
    values = {str(value) for table in rows.values() for row in table for value in row}
    assert getpass.getuser() not in values
    today = datetime.date.today().isoformat()
    assert not [value for value in values if value.startswith(today)]
    assert len(rows["REGISTER(kept_ds@PERMANENT)"]) == 1
    history = [row[-1] for row in rows["VIEW strds_view_abs_time"]]
    assert history[0].startswith("# <time> \nt.create")
    assert not re.search(r"# \d{4}-", history[0])
    assert any(
        isinstance(value, bool) for row in rows["vector_metadata"] for value in row
    )
    assert not [name for name in rows if "_map_register_" in name]
    # SQLite stores a truth value as 0 or 1; the view reports the declared
    # type of the column it selects, which makes it a bool there as well
    is_3d = view_columns.index("is_3d")
    assert rows["VIEW vector_view_abs_time"]
    assert all(
        isinstance(row[is_3d], bool) for row in rows["VIEW vector_view_abs_time"]
    )


def test_the_scenario_lets_the_caller_read_the_database_after_each_step(tmp_path):
    import grass.temporal as tgis

    seen = {}
    with temporal_session(tmp_path / "project") as session:
        database = tgis.get_tgis_database_string()

        def after(step):
            seen[step] = postgresql.rows_of("sqlite", database)

        postgresql.run_scenario(
            Tools(session=session, consistent_return_value=True), after=after
        )

    assert list(seen) == [
        f"{stds_type} {step}"
        for stds_type in ("strds", "str3ds", "stvds")
        for step in ("registered", "unregistered", "removed")
    ]
    for stds_type in ("strds", "str3ds", "stvds"):
        register = f"REGISTER(scenario_{stds_type}@PERMANENT)"
        assert len(seen[f"{stds_type} registered"][register]) == 3
        assert len(seen[f"{stds_type} unregistered"][register]) == 2
        assert register not in seen[f"{stds_type} removed"]
    labels = {
        value
        for row in seen["strds registered"]["raster_metadata"]
        for value in row
        if isinstance(value, str) and value.startswith("S2_")
    }
    assert labels == {"S2_1", "S2_2"}


@contextlib.contextmanager
def backend_session(path, backend, dbstring=None):
    """Yield the tools of a session and the string of its temporal database

    backend "postgresql" connects the mapset to the database dbstring and
    creates the tables there; "sqlite" keeps the database of the mapset.
    """
    import grass.temporal as tgis

    with temporal_session(path) as session:
        tools = Tools(session=session, consistent_return_value=True)
        if backend == "postgresql":
            tools.t_connect(driver="pg", database=dbstring)
            tgis.init(raise_fatal_error=True)
        yield tools, tgis.get_tgis_database_string()


def structure_of(backend, dbstring):
    """Return the columns of each table and view and the table of each trigger"""
    if backend == "sqlite":
        with contextlib.closing(sqlite3.connect(dbstring)) as connection:
            objects = connection.execute(
                "SELECT type, name, tbl_name FROM sqlite_master "
                "WHERE type IN ('table', 'view', 'trigger')"
            ).fetchall()
            return {
                f"{kind} {name}": (
                    table
                    if kind == "trigger"
                    else [
                        row[1]
                        for row in connection.execute(f"PRAGMA table_info({name})")
                    ]
                )
                for kind, name, table in objects
            }
    import psycopg2

    with contextlib.closing(psycopg2.connect(dbstring)) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT t.table_type, t.table_name, c.column_name "
            "FROM information_schema.tables t JOIN information_schema.columns c "
            "USING (table_schema, table_name) WHERE table_schema = 'public' "
            "ORDER BY t.table_name, c.ordinal_position"
        )
        result = {}
        for kind, name, column in cursor.fetchall():
            key = f"{'view' if kind == 'VIEW' else 'table'} {name}"
            result.setdefault(key, []).append(column)
        # One row per event of a trigger; the temporal triggers have one each
        cursor.execute(
            "SELECT trigger_name, event_object_table FROM information_schema.triggers "
            "WHERE trigger_schema = 'public'"
        )
        for name, table in cursor.fetchall():
            result[f"trigger {name}"] = table
        return result


@pytest.mark.postgresql
def test_a_fresh_database_has_the_tables_views_and_triggers_of_sqlite(
    tmp_path, postgresql_database
):
    with backend_session(tmp_path / "sqlite", "sqlite") as (_, database):
        expected = structure_of("sqlite", database)
    with backend_session(
        tmp_path / "postgresql", "postgresql", postgresql_database
    ) as (_, database):
        actual = structure_of("postgresql", database)

    assert "trigger delete_raster_base" in expected
    assert actual == expected


def floats_as_sqlite_stores_them(stages):
    """Return the rows with every float written with six decimals and read back

    SQLite gets the values of an insert or update as text with six decimals,
    PostgreSQL gets the full value. Applied to both sides, this tolerates
    that difference and nothing else.
    """
    return {
        step: {
            name: sorted(
                (
                    tuple(
                        float(f"{value:f}") if isinstance(value, float) else value
                        for value in row
                    )
                    for row in table
                ),
                key=repr,
            )
            for name, table in rows.items()
        }
        for step, rows in stages.items()
    }


@pytest.mark.postgresql
def test_the_scenario_gives_the_same_rows_on_both_backends(
    tmp_path, postgresql_database
):
    stages = {}
    labels = {}
    for backend, dbstring in (
        ("sqlite", None),
        ("postgresql", postgresql_database),
    ):
        seen = stages[backend] = {}
        listed = labels[backend] = {}
        with backend_session(tmp_path / backend, backend, dbstring) as (
            tools,
            database,
        ):

            def after(step, backend=backend, database=database, seen=seen):
                seen[step] = postgresql.rows_of(backend, database)
                # The list of labels is not stored but read by t.info
                if step in {"strds registered", "strds unregistered"}:
                    listed[step] = tools.t_info(
                        flags="g", type="strds", input="scenario_strds"
                    ).keyval["semantic_labels"]

            postgresql.run_scenario(tools, after=after)

    assert len(stages["postgresql"]) == 9
    assert floats_as_sqlite_stores_them(
        stages["postgresql"]
    ) == floats_as_sqlite_stores_them(stages["sqlite"])
    assert labels["sqlite"]["strds registered"] == "S2_1,S2_2"
    assert labels["postgresql"] == labels["sqlite"]


def tables_naming(rows, prefix):
    """Return the names of the tables and views with a value starting with prefix"""
    return {
        name
        for name, table in rows.items()
        for row in table
        if any(str(value).startswith(prefix) for value in row)
    }


@pytest.mark.parametrize(
    "backend", ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)]
)
def test_deleting_a_map_removes_its_rows_from_every_table(tmp_path, request, backend):
    """The delete triggers remove the rows the library does not delete itself"""
    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with backend_session(tmp_path / "project", backend, dbstring) as (
        tools,
        database,
    ):
        data.small_region(tools, 1, 1, depths=1)
        for stds_type in data.MAP_TYPE_OF_STDS:
            data.create_stds(
                tools,
                stds_type,
                f"kept_{stds_type}",
                [
                    data.MapSpec(f"gone_{stds_type}", 1, data.day(1), data.day(2)),
                    data.MapSpec(f"stays_{stds_type}", 2, data.day(2), data.day(3)),
                ],
            )
        before = tables_naming(postgresql.rows_of(backend, database), "gone_")
        for stds_type, map_type in data.MAP_TYPE_OF_STDS.items():
            # Without input the map leaves the temporal database
            tools.t_unregister(type=map_type, maps=f"gone_{stds_type}")
        after = tables_naming(postgresql.rows_of(backend, database), "gone_")

    for kind in ("raster", "raster3d", "vector"):
        assert {
            f"{kind}_base",
            f"{kind}_absolute_time",
            f"{kind}_spatial_extent",
            f"{kind}_metadata",
        } <= before
    assert after == set()


def test_rows_of_masks_the_temporary_directory_in_a_command_history(tmp_path):
    import grass.temporal as tgis

    with temporal_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        data.small_region(tools, 1, 1)
        # Registers from a file in a new temporary directory
        data.create_stds(
            tools, "strds", "listed", [data.MapSpec("one", 1, data.day(1))]
        )
        rows = postgresql.rows_of("sqlite", tgis.get_tgis_database_string())

    (history,) = [row[-1] for row in rows["VIEW strds_view_abs_time"]]
    assert 'file="<temporary directory>/maps.txt"' in history
    assert tempfile.gettempdir() not in history


@pytest.mark.parametrize(
    "backend",
    ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)],
)
def test_a_version_2_database_is_recognized(tmp_path, backend, request, monkeypatch):
    from grass.temporal import SQLDatabaseInterfaceConnection, state

    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with backend_session(tmp_path / backend, backend, dbstring) as (_, database):
        # temporal_session mirrors the session environment into os.environ
        session = types.SimpleNamespace(env=os.environ)
        if backend == "sqlite":
            versions.downgrade_to_version_2(session)
        else:
            versions.downgrade_postgresql_to_version_2(session, database)
        warnings = []
        monkeypatch.setattr(state.STATE.message_interface, "warning", warnings.append)
        state._check_versions(SQLDatabaseInterfaceConnection())

    assert len(warnings) == 1
    assert "Temporal database version mismatch detected" in warnings[0]
    assert "Your existing temporal database version: 2" in warnings[0]


@pytest.mark.parametrize(
    "backend", ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)]
)
def test_registered_maps_grouped_by_start_time(tmp_path, request, backend):
    import grass.temporal as tgis

    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with backend_session(tmp_path / backend, backend, dbstring) as (tools, _):
        data.small_region(tools, 1, 1)
        # The later name is registered first, so that the order of the ids
        # inside the group is not the order of registration.
        data.create_stds(
            tools,
            "strds",
            "grouped",
            [
                data.MapSpec("b", 1, data.day(1), data.day(2)),
                data.MapSpec("a", 2, data.day(1), data.day(2)),
            ],
        )
        mapset = tgis.get_current_mapset()
        stds = tgis.open_old_stds("grouped", "strds")
        (row,) = stds.get_registered_maps(columns="id", group="start_time")

    assert row["id"] == f"a@{mapset},b@{mapset}"
    # Rows are read by name and by position, the group column first
    assert row.keys() == ["start_time", "id"]
    assert row[1] == row["id"]
    assert row[0] == row["start_time"]


@pytest.mark.parametrize(
    "backend", ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)]
)
def test_grouped_columns_stay_aligned(tmp_path, request, backend):
    import grass.temporal as tgis

    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with backend_session(tmp_path / backend, backend, dbstring) as (tools, _):
        data.small_region(tools, 1, 1)
        # Same start; the end times run against the order of the ids
        data.create_stds(
            tools,
            "strds",
            "aligned",
            [
                data.MapSpec("b", 1, data.day(1), data.day(2)),
                data.MapSpec("a", 2, data.day(1), data.day(3)),
            ],
        )
        stds = tgis.open_old_stds("aligned", "strds")
        ends = {
            row["id"]: str(row["end_time"])
            for row in stds.get_registered_maps(columns="id,end_time")
        }
        (row,) = stds.get_registered_maps(columns="id,end_time", group="start_time")

    ids = row["id"].split(",")
    assert len(ids) == 2
    assert row["end_time"].split(",") == [ends[name] for name in ids]
    assert len(set(row["end_time"].split(","))) == 2


@pytest.mark.parametrize(
    "backend", ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)]
)
def test_semantic_labels_are_listed_by_name(tmp_path, request, backend):
    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with backend_session(tmp_path / backend, backend, dbstring) as (tools, _):
        data.small_region(tools, 1, 1)
        # S2_2 comes first in the registration and in the file order
        data.create_stds(
            tools,
            "strds",
            "labelled",
            [
                data.MapSpec("m2", 1, data.day(1), data.day(2), "S2_2"),
                data.MapSpec("m1", 2, data.day(2), data.day(3), "S2_1"),
            ],
        )
        listed = tools.t_info(flags="g", type="strds", input="labelled").keyval[
            "semantic_labels"
        ]

    assert listed == "S2_1,S2_2"
