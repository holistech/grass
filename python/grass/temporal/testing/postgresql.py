# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Run temporal tests against a PostgreSQL server and compare the backends

A server is not started by the tests. Whoever runs them starts one and names
it in the environment variable ``GRASS_TEMPORAL_TEST_POSTGRESQL`` as a libpq
connection string of a database the user may create other databases from::

    docker run -d --rm --name grass-tgis-pg -e POSTGRES_HOST_AUTH_METHOD=trust \\
        -p 127.0.0.1:55432:5432 postgres:16
    export GRASS_TEMPORAL_TEST_POSTGRESQL=\\
        "host=127.0.0.1 port=55432 user=postgres dbname=postgres"

``fresh_database()`` creates one database per call, so tests that run in
parallel under pytest-xdist never share one. ``rows_of()`` reads a temporal
database of either backend into the same form, and ``run_scenario()`` fills a
database through the tools, so that both backends can be compared row by row.

pytest is imported only by ``server_or_skip()``; fixtures belong in
conftest.py files.
"""

from __future__ import annotations

import contextlib
import datetime
import os
import re
import sqlite3
import uuid
from decimal import Decimal

from . import data

SERVER_VARIABLE = "GRASS_TEMPORAL_TEST_POSTGRESQL"

# Values that differ between two runs of the same steps
_MASKED_COLUMNS = frozenset({"creation_time", "modification_time", "creator"})
# The command history of a dataset starts each entry with the time of the call
_HISTORY_TIME = re.compile(r"^# \d{4}-\d\d-\d\d \d\d:\d\d:\d\d ", re.MULTILINE)
_REGISTER_TABLE = re.compile(r"(raster|raster3d|vector)_map_register_[0-9a-f]+")
_REGISTER_COLUMN = {
    "strds": "raster_register",
    "str3ds": "raster3d_register",
    "stvds": "vector_register",
}


def server_string() -> str | None:
    """Return the connection string named by the environment, or None"""
    return os.environ.get(SERVER_VARIABLE) or None


def server_or_skip() -> str:
    """Return the connection string of the server, or skip the running test

    Skips when the variable is unset or empty and when the server does not
    answer, so that a stale variable never turns into a wall of errors.
    """
    import pytest

    server = server_string()
    if server is None:
        pytest.skip(f"{SERVER_VARIABLE} names no PostgreSQL server")
    try:
        import psycopg2

        psycopg2.connect(server, connect_timeout=5).close()
    except ImportError:
        pytest.skip("psycopg2 is not installed")
    except psycopg2.Error as error:
        pytest.skip(f"The PostgreSQL server of {SERVER_VARIABLE} is down: {error}")
    return server


@contextlib.contextmanager
def fresh_database(prefix: str):
    """Create a database for one test, yield its connection string, drop it

    The name is <prefix>_<xdist worker>_<8 hex digits of a uuid>. The server
    is the one of server_string(); the database does not exist before the
    block and does not after it, even when the block fails.
    """
    import psycopg2
    from psycopg2 import sql

    server = server_string()
    if server is None:
        msg = f"{SERVER_VARIABLE} names no PostgreSQL server"
        raise RuntimeError(msg)
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    name = f"{prefix}_{worker}_{uuid.uuid4().hex[:8]}"
    # CREATE and DROP DATABASE refuse to run inside a transaction
    admin = psycopg2.connect(server)
    admin.autocommit = True
    try:
        with admin.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            yield psycopg2.extensions.make_dsn(server, dbname=name)
        finally:
            with admin.cursor() as cursor:
                # FORCE ends the connections a failed test left behind
                cursor.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        sql.Identifier(name)
                    )
                )
    finally:
        admin.close()


def _comparable(value, declared_type: str | None):
    """Return value in the form that SQLite and PostgreSQL share"""
    if value is None:
        return None
    if declared_type is not None and declared_type.upper() == "BOOLEAN":
        return bool(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, (Decimal, float)):
        return float(value)
    return value


def _read_all(backend: str, dbstring: str):
    """Return (connection, names of tables, names of views, column types, query)

    The statements here and in rows_of() interpolate names of tables, views and
    columns that were read from the database itself or are constants of this
    module, so they cannot carry user input; the S608 exceptions rest on that.
    """
    if backend == "sqlite":
        connection = sqlite3.connect(dbstring)

        def query(statement):
            return connection.execute(statement).fetchall()

        kinds = {
            kind: [
                row[0]
                for row in query(f"SELECT name FROM sqlite_master WHERE type='{kind}'")  # noqa: S608
            ]
            for kind in ("table", "view")
        }
        types = {
            table: {row[1]: row[2] for row in query(f"PRAGMA table_info({table})")}
            # A view reports the declared type of the column it selects, which
            # turns the 0 and 1 of a BOOLEAN column in a view into bool as well
            for table in kinds["table"] + kinds["view"]
        }
        return connection, kinds["table"], kinds["view"], types, query
    import psycopg2

    connection = psycopg2.connect(dbstring)
    cursor = connection.cursor()

    def query(statement):
        cursor.execute(statement)
        return cursor.fetchall()

    # PostgreSQL returns bool for BOOLEAN on its own; the types are only
    # needed to turn the 0 and 1 of SQLite into bool
    rows = query(
        "SELECT table_name, table_type FROM information_schema.tables "
        "WHERE table_schema='public'"
    )
    tables = [name for name, kind in rows if kind == "BASE TABLE"]
    views = [name for name, kind in rows if kind == "VIEW"]
    return connection, tables, views, {}, query


def _cell(column, value, declared, register_names):
    """Return value of column with the volatile and backend specific parts removed"""
    if column in _MASKED_COLUMNS and value is not None:
        return "<masked>"
    if isinstance(value, str) and value in register_names:
        return f"REGISTER({register_names[value]})"
    if isinstance(value, str):
        return _HISTORY_TIME.sub("# <time> ", value)
    return _comparable(value, declared.get(column))


def rows_of(backend: str, dbstring: str) -> dict[str, list[tuple]]:
    """Return every table and view of a temporal database with sorted rows

    backend is "sqlite" (dbstring is the file) or "postgresql" (dbstring is a
    libpq text). The result is equal for the two backends when the library
    wrote the same. What differs between runs is replaced: the times of
    creation and modification and the user by "<masked>" (also the creation
    time kept in tgis_metadata), the times in a command history by "<time>".
    Truth values are bool, numbers float, times text, and a register table is
    keyed REGISTER(<id of its dataset>) instead of by its random name. Views
    are keyed "VIEW <name>".
    """
    connection, tables, views, types, query = _read_all(backend, dbstring)
    try:
        register_names = {}
        for kind, column in _REGISTER_COLUMN.items():
            for dataset_id, register in query(
                f"SELECT id, {column} FROM {kind}_metadata"  # noqa: S608
            ):
                if register:
                    register_names[register] = dataset_id

        def label(name):
            if _REGISTER_TABLE.fullmatch(name):
                return f"REGISTER({register_names.get(name, '?orphan ' + name)})"
            return name

        result = {}
        for name, is_view in [(n, False) for n in tables] + [(n, True) for n in views]:
            columns = _column_names(backend, query, name)
            declared = types.get(name, {})
            rows = [
                tuple(
                    _cell(column, value, declared, register_names)
                    for column, value in zip(columns, row, strict=True)
                )
                for row in query(f"SELECT * FROM {name}")  # noqa: S608
            ]
            if name == "tgis_metadata":
                # Key and value columns: the time of creation is a value
                rows = [
                    (key, "<masked>" if key in _MASKED_COLUMNS else value)
                    for key, value in rows
                ]
            result[f"VIEW {name}" if is_view else label(name)] = sorted(rows, key=repr)
        return result
    finally:
        connection.close()


def _column_names(backend, query, name):
    """Return the column names of a table or view in their stored order"""
    if backend == "sqlite":
        return [row[1] for row in query(f"PRAGMA table_info({name})")]
    return [
        row[0]
        for row in query(
            "SELECT column_name FROM information_schema.columns "  # noqa: S608
            f"WHERE table_schema='public' AND table_name='{name}' "
            "ORDER BY ordinal_position"
        )
    ]


def run_scenario(tools, after=None) -> None:
    """Fill the temporal database of the session of tools through the tools

    Creates a space time raster, 3D raster and vector dataset with maps
    registered, lists them, unregisters one map of each and removes the
    datasets with -r. The session of tools decides the backend, so the
    same steps give the rows that rows_of() compares between backends.

    after, if given, is called with the name of each step that wrote to the
    database, such as "strds registered", "strds unregistered" and "strds
    removed", right after the step, so that a caller can read the database
    in between; at the end most rows are gone. The maps hold thirds, which
    have more decimals than a float literal on SQLite keeps, and two raster
    maps carry semantic labels, so that the dataset has a list of labels.
    """
    spec = data.MapSpec
    day = data.day
    labels = {1: "S2_1", 2: "S2_2"}
    report = after or (lambda step: None)
    data.small_region(tools, 1, 1, depths=1)
    for stds_type, map_type, listing in (
        ("strds", "raster", "t_rast_list"),
        ("str3ds", "raster_3d", "t_rast3d_list"),
        ("stvds", "vector", "t_vect_list"),
    ):
        name = f"scenario_{stds_type}"
        data.create_stds(
            tools,
            stds_type,
            name,
            [
                spec(
                    f"{name}_{n}",
                    # A vector map takes a number, raster maps an expression
                    n / 3 if map_type == "vector" else f"{n} / 3.0",
                    day(n),
                    day(n + 1),
                    labels.get(n) if map_type == "raster" else None,
                )
                for n in (1, 2, 3)
            ],
        )
        report(f"{stds_type} registered")
        getattr(tools, listing)(input=name)
        tools.t_unregister(type=map_type, input=name, maps=f"{name}_3")
        report(f"{stds_type} unregistered")
        tools.t_remove(flags="rf", type=stds_type, inputs=name)
        report(f"{stds_type} removed")
