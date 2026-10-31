"""Test the support for running temporal tests against a PostgreSQL server

The tests marked postgresql need the server named by
GRASS_TEMPORAL_TEST_POSTGRESQL and are skipped without one.
"""

import datetime
import getpass
import re

import pytest

from grass.temporal.testing import postgresql
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
        rows = postgresql.rows_of("sqlite", tgis.get_tgis_database_string())

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
    # SQLite stores a truth value as 0 or 1; a view has no type of its own
    assert any(
        isinstance(value, bool)
        for row in rows["VIEW vector_view_abs_time"]
        for value in row
    )
