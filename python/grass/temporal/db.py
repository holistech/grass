"""Access to the temporal database: connections, SQL literals and names

This module provides the connections to the SQLite or PostgreSQL database of
the temporal framework and the functions that make connecting safe. It is
also the one place that checks the table, view and column names that go into
the text of a statement (sql_identifier(), sql_statement()).

Usage:

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> # Create the temporal database
    >>> tgis.init()
    >>> # Establish a database connection
    >>> dbif, connection_state_changed = tgis.init_dbif(None)
    >>> dbif.connect()
    >>> # Execute a SQL statement
    >>> dbif.execute_transaction("SELECT datetime(0, 'unixepoch', 'localtime');")
    >>> # Mogrify an SQL statement
    >>> dbif.mogrify_sql_statement(
    ...     ["SELECT name from raster_base where name = ?", ("precipitation",)]
    ... )
    "SELECT name from raster_base where name = 'precipitation'"
    >>> dbif.close()

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import contextlib
import math
import re
import sqlite3
from datetime import datetime
from importlib.util import find_spec
from pathlib import Path
from typing import TYPE_CHECKING

from grass.script.utils import decode

from .state import (
    STATE,
    get_current_mapset,
    get_tgis_c_library_interface,
    get_tgis_message_interface,
    tools,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

# Import all supported database backends (sqlite3 imported above)
# Ignore import errors since they are checked later

db_errors: tuple[type[sqlite3.Error], type[psycopg2.Error]] | tuple[type[sqlite3.Error]]
# Postgresql is optional, existence is checked when needed
if find_spec("psycopg2") is not None and find_spec("psycopg2.extras") is not None:
    # Following explanations on how importing submodules work
    # from ruff's v0.13.3 new F401 handling https://github.com/astral-sh/ruff/pull/20200
    # importing "psycopg2.extras" actually makes an "import psycopg2",
    # making the members of the form `psycopg2.*` available, and then also imports the
    # extras and makes available the members of the form `psycopg2.extras.*`.
    import psycopg2.extras

    db_errors = (sqlite3.Error, psycopg2.Error)
else:
    db_errors = (sqlite3.Error,)


class SQLStatementError(RuntimeError):
    """A SQL statement of the temporal database failed

    The message is the one of the database driver; statement holds the SQL
    text. Tools report it with a fatal error instead of a traceback. The class
    does not derive from the driver's errors, so a caller does not depend on
    the database backend.
    """

    def __init__(self, message, statement):
        super().__init__(message)
        self.statement = statement


def db_datetime(value: datetime) -> datetime:
    """Bring a time to the resolution of the temporal database

    The database keeps whole seconds: the microseconds are cut off, not
    rounded. A time zone stays as it is, without any conversion of the clock
    time; t.register relies on the stored zone to refuse a dataset that would
    mix times with and without one. Every value that goes into or comes out
    of the database passes here, so the paths of SQLite (adapter and written
    statement) and PostgreSQL store the same time. The values in memory are
    not touched.
    """
    return value.replace(microsecond=0)


def adapt_datetime_iso(value: datetime) -> str:
    """Adapt datetime object to an ISO 8601 string in whole seconds.

    A naive time gives the same text as before ("2001-01-01 06:30:00"). An
    aware time keeps its offset: the adapter used to drop it, while the
    written statement (sql_literal) kept it, and the two paths must store
    the same text.
    """
    return db_datetime(value).isoformat(sep=" ")


def convert_datetime(value: bytes) -> datetime:
    """Convert ISO 8601 string to a datetime in whole seconds, zone kept.

    A text written by an older version can carry microseconds; they are cut,
    so the value can be compared with a new one.
    """
    return db_datetime(datetime.fromisoformat(value.decode()))


sqlite3.register_adapter(datetime, adapt_datetime_iso)
sqlite3.register_converter("date", convert_datetime)
sqlite3.register_converter("datetime", convert_datetime)
sqlite3.register_converter("timestamp", convert_datetime)


def get_available_temporal_mapsets(mapsets: str | None = None) -> dict:
    """Return a list of of mapset names with temporal database driver and names.

    :param mapsets: A string specifying target mapsets ('.' for current, '*'
                       for all mapsets in the location, or comma-separated names).
                       If None, defaults to the current search path.

    :returns: A dictionary, mapset names are keys, the tuple (driver,
              database) are the values
    """
    c_library_interface = get_tgis_c_library_interface()
    message_interface = get_tgis_message_interface()

    connections = tools.t_connect(flags="p", format="json", mapset=mapsets, quiet=True)
    mapsets_list = [conn for conn in connections if all(conn.values())]

    tgis_mapsets = {}

    for mapset_data in mapsets_list:
        mapset = mapset_data["mapset"]
        driver = mapset_data["driver"]
        database = c_library_interface.get_database_name(mapset)

        message_interface.debug(
            1,
            "get_available_temporal_mapsets: "
            f"\n  mapset {mapset}\n  driver {driver}\n  database {database}",
        )
        if driver and database:
            # Check if the temporal sqlite database exists
            if driver == "sqlite" and not Path(database).exists():
                # Inform if DB for defined connection does not exist
                message_interface.verbose(
                    _(
                        "Temporal database connection for mapset <%s> "
                        "defined as:\n %s\nBut database file does not exist."
                    )
                    % (mapset, database)
                )
                continue
            tgis_mapsets[mapset] = (driver, database)

    return tgis_mapsets


class SQLDatabaseInterfaceConnection:
    """The connections to the temporal databases of the mapsets in the search path

    Mapsets that share a database share one connection. A connection is opened
    by ``connect`` and used through the mapset name, the current mapset if none
    is given.
    """

    def __init__(self, mapsets: str | None = None) -> None:
        self.tgis_mapsets = get_available_temporal_mapsets(mapsets)
        self.current_mapset = get_current_mapset()
        self.connections = {}
        self.connected = False

        self.unique_connections = {}

        for mapset in self.tgis_mapsets:
            driver, dbstring = self.tgis_mapsets[mapset]

            if dbstring not in self.unique_connections:
                self.unique_connections[dbstring] = DBConnection(
                    backend=driver, dbstring=dbstring
                )

            self.connections[mapset] = self.unique_connections[dbstring]

    @property
    def msgr(self):
        """The messenger of the current session, fetched at each use"""
        return get_tgis_message_interface()

    def get_dbmi(self, mapset=None):
        """Return the database module (sqlite3 or psycopg2) of a mapset"""
        if mapset is None:
            mapset = self.current_mapset

        mapset = decode(mapset)
        return self.connections[mapset].dbmi

    def rollback(self, mapset=None) -> None:
        """
        Roll back the last transaction. This must be called
        in case a new query should be performed after a db error.

        This is only relevant for postgresql database.
        """
        if mapset is None:
            mapset = self.current_mapset

        self.connections[decode(mapset)].rollback()

    def connect(self) -> None:
        """Connect to the DBMI to execute SQL statements

        Supported backends are sqlite3 and postgresql
        """
        for mapset in self.tgis_mapsets:
            driver, dbstring = self.tgis_mapsets[mapset]
            conn = self.connections[mapset]
            if conn.is_connected() is False:
                conn.connect(dbstring)

        self.connected = True

    def is_connected(self):
        """Tell whether ``connect`` has been called and ``close`` has not"""
        return self.connected

    def close(self) -> None:
        """Close the DBMI connection

        There may be several temporal databases in a location, hence
        close all temporal databases that have been opened.
        """
        for key in self.unique_connections:
            self.unique_connections[key].close()

        self.connected = False

    def add_mapset(self, mapset):
        """Ensure the temporal database of the given mapset is part of this
        connection, so datasets can be accessed by fully qualified name
        (name@mapset) even when the mapset is not on the current search path.

        The method is idempotent: mapsets already known to the connection are
        left untouched. If the mapset has no accessible temporal database, it
        is not added and a later query against it fails with the usual error.
        """
        mapset = decode(mapset)
        if mapset in self.tgis_mapsets:
            return
        new_mapsets = get_available_temporal_mapsets(mapset)
        if mapset not in new_mapsets:
            return
        driver, dbstring = new_mapsets[mapset]
        self.tgis_mapsets[mapset] = (driver, dbstring)
        if dbstring not in self.unique_connections:
            self.unique_connections[dbstring] = DBConnection(
                backend=driver, dbstring=dbstring
            )
        self.connections[mapset] = self.unique_connections[dbstring]
        if self.connected and not self.connections[mapset].is_connected():
            self.connections[mapset].connect(dbstring)

    def _connection_of(self, mapset, refusal):
        """Return the connection of a mapset, the current one if none is given

        :param refusal: The message, with ``{reason}``, for a mapset that has
                        no accessible temporal database. Each caller passes
                        its own ``_()`` literal so that the message ids are
                        found in the source.
        """
        if mapset is None:
            mapset = self.current_mapset

        mapset = decode(mapset)
        if mapset not in self.tgis_mapsets:
            self.msgr.fatal(
                refusal.format(reason=self._create_mapset_error_message(mapset))
            )

        return self.connections[mapset]

    def mogrify_sql_statement(self, content, mapset=None):
        """Return the SQL statement and arguments as executable SQL string

        :param content: The content as tuple with two entries, the first
                        entry is the SQL statement with DBMI specific
                        place holder (?), the second entry is the argument
                        list that should substitute the place holder.
        :param mapset: The mapset of the abstract dataset or temporal
                       database location, if None the current mapset
                       will be used
        """
        return self._connection_of(
            mapset, _("Unable to mogrify sql statement. {reason}")
        ).mogrify_sql_statement(content)

    def check_table(self, table_name: str, mapset=None):
        """Check if a table exists in the temporal database

        :param table_name: The name of the table to be checked for existence
        :param mapset: The mapset of the abstract dataset or temporal
                       database location, if None the current mapset
                       will be used
        :returns: True if the table exists, False otherwise
        """
        return self._connection_of(
            mapset, _("Unable to check table. {reason}")
        ).check_table(table_name)

    def execute(self, statement, args=None, mapset=None):
        """

        :param mapset: The mapset of the abstract dataset or temporal
                       database location, if None the current mapset
                       will be used
        """
        return self._connection_of(
            mapset, _("Unable to execute sql statement. {reason}")
        ).execute(statement, args)

    def fetchone(self, mapset=None):
        """Fetch the next row of the last statement executed for the mapset"""
        return self._connection_of(
            mapset, _("Unable to fetch one. {reason}")
        ).fetchone()

    def fetchall(self, mapset=None):
        """Fetch all remaining rows of the last statement for the mapset"""
        return self._connection_of(
            mapset, _("Unable to fetch all. {reason}")
        ).fetchall()

    def execute_transaction(self, statement, mapset=None):
        """Execute a transactional SQL statement

        The BEGIN and END TRANSACTION statements will be added automatically
        to the sql statement

        :param statement: The executable SQL statement or SQL script
        """
        return self._connection_of(
            mapset, _("Unable to execute transaction. {reason}")
        ).execute_transaction(statement)

    def _create_mapset_error_message(self, mapset) -> str:
        return _(
            "You have no permission to access mapset <{mapset}>, or mapset"
            " <{mapset}> has no temporal database."
            " Accessible mapsets are: <{mapsets}>"
        ).format(mapset=decode(mapset), mapsets=",".join(self.tgis_mapsets.keys()))


class DBConnection:
    """This class represents the database interface connection
    and provides access to the chosen backend modules.

    The following DBMS are supported:

    - sqlite via the sqlite3 standard library
    - postgresql via psycopg2
    """

    def __init__(self, backend=None, dbstring: str | None = None) -> None:
        """Constructor of a database connection

        :param backend: The database backend sqlite or pg
        :param dbstring: The database connection string
        """
        self.connected = False
        if backend is None:
            if decode(STATE.backend) == "sqlite":
                self.dbmi = sqlite3
            else:
                self.dbmi = psycopg2
        else:  # noqa: PLR5501
            if decode(backend) == "sqlite":
                self.dbmi = sqlite3
            else:
                self.dbmi = psycopg2

        if dbstring is None:
            dbstring = STATE.database_string

        self.dbstring = dbstring

        self.msgr.debug(
            1,
            "DBConnection constructor:"
            f"\n  backend: {backend}"
            f"\n  dbstring: {self.dbstring}",
        )

    @property
    def msgr(self):
        """The messenger of the current session, fetched at each use"""
        return get_tgis_message_interface()

    def __del__(self) -> None:
        if self.connected is True:
            self.close()

    def is_connected(self):
        """Tell whether the connection is open"""
        return self.connected

    def rollback(self) -> None:
        """
        Roll back the last transaction. This must be called
        in case a new query should be performed after a db error.

        This is only relevant for postgresql database.
        """
        if self.dbmi.__name__ == "psycopg2" and self.connected:
            self.connection.rollback()

    def connect(self, dbstring: str | None = None) -> None:
        """Connect to the DBMI to execute SQL statements

        Supported backends are sqlite3 and postgresql

        param dbstring: The database connection string
        """
        # Connection in the current mapset
        if dbstring is None:
            dbstring = self.dbstring

        dbstring = decode(dbstring)

        try:
            if self.dbmi.__name__ == "sqlite3":
                self.connection = self.dbmi.connect(
                    dbstring,
                    detect_types=self.dbmi.PARSE_DECLTYPES | self.dbmi.PARSE_COLNAMES,
                )
                self.connection.row_factory = self.dbmi.Row
                self.connection.isolation_level = None
                self.connection.text_factory = str
                self.cursor = self.connection.cursor()
                # busy_timeout is set to 30 seconds to avoid "database is locked" errors
                self.cursor.executescript(
                    "PRAGMA synchronous = OFF;"
                    "PRAGMA journal_mode = MEMORY;"
                    "PRAGMA busy_timeout = 30000;"
                )
            elif self.dbmi.__name__ == "psycopg2":
                self.connection = self.dbmi.connect(dbstring)
                self.cursor = self.connection.cursor(
                    cursor_factory=self.dbmi.extras.DictCursor
                )
            self.connected = True
        except (self.dbmi.Error, OSError) as e:
            self.msgr.fatal(
                _(
                    "Unable to connect to %(db)s database: "
                    '%(string)s\nException: "%(ex)s"\nPlease use'
                    " t.connect to set a read- and writable "
                    "temporal database backend"
                )
                % (
                    {
                        "db": self.dbmi.__name__,
                        "string": dbstring,
                        "ex": e,
                    }
                )
            )

    def close(self) -> None:
        """Close the DBMI connection, also when it is closed already"""
        if not self.connected:
            return
        try:
            self.connection.commit()
        finally:
            # The file stays open and, for PostgreSQL, the session stays
            # alive until the connection object is collected if only the
            # cursor is closed.
            self.cursor.close()
            self.connection.close()
            self.connected = False

    def mogrify_sql_statement(self, content):
        """Return the SQL statement and arguments as executable SQL string

        :param content: The content as tuple with two entries, the first
                        entry is the SQL statement with DBMI specific
                        place holder (?), the second entry is the argument
                        list that should substitute the place holder.

        Usage:

        .. code-block:: pycon

            >>> init()
            >>> dbif = SQLDatabaseInterfaceConnection()
            >>> dbif.mogrify_sql_statement(
            ...     [
            ...         "SELECT ctime FROM raster_base WHERE id = ?",
            ...         [
            ...             "soil@PERMANENT",
            ...         ],
            ...     ]
            ... )
            "SELECT ctime FROM raster_base WHERE id = 'soil@PERMANENT'"

        """
        sql = content[0]
        args = content[1]

        if self.dbmi.__name__ == "psycopg2":
            if len(args) == 0:
                return sql
            args = _pg_args(args)
            if self.connected:
                return self.cursor.mogrify(sql, args)
            self.connect()
            statement = self.cursor.mogrify(sql, args)
            self.close()
            return statement

        if self.dbmi.__name__ == "sqlite3":
            if len(args) == 0:
                return sql
            # Unfortunately as sqlite does not support
            # the transformation of sql strings and qmarked or
            # named arguments we must make our hands dirty
            # and do it by ourself. :(
            # Doors are open for SQL injection because of the
            # limited python sqlite3 implementation!!!
            #
            # The statement is cut at its placeholders and put together again
            # in one pass. Searching the placeholders in the statement while
            # it grows would take a question mark inside an inserted text for
            # the next placeholder.
            parts = sql.split("?")
            statement = parts[0]
            for count, part in enumerate(parts[1:]):
                statement += sql_literal(args[count]) + part

            return statement

    def check_table(self, table_name: str):
        """Check if a table exists in the temporal database

        :param table_name: The name of the table to be checked for existence
        :returns: True if the table exists, False otherwise
        """
        table_exists = False
        connected = False
        if not self.connected:
            self.connect()
            connected = True

        # Check if the database already exists
        if self.dbmi.__name__ == "sqlite3":
            self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
                (table_name,),
            )
            name = self.cursor.fetchone()
            if name and name[0] == table_name:
                table_exists = True
        else:
            # Check for raster_base table
            self.cursor.execute(
                "SELECT EXISTS(SELECT * FROM information_schema.tables "
                "WHERE table_name=%s)",
                (str(table_name),),
            )
            if self.cursor.fetchone()[0]:
                table_exists = True

        if connected:
            self.close()

        return table_exists

    def execute(self, statement, args=None):
        """Execute a SQL statement

        :param statement: The executable SQL statement or SQL script
        """
        connected = False
        if not self.connected:
            self.connect()
            connected = True
        try:
            if args:
                if self.dbmi.__name__ == "psycopg2":
                    args = _pg_args(args)
                self.cursor.execute(statement, args)
            else:
                self.cursor.execute(statement)
        except db_errors as error:
            # The exception keeps the statement; a tool that reports the
            # error shows one message instead of the SQL as a second one.
            self.msgr.debug(1, f"Unable to execute:\n {statement}")
            raise SQLStatementError(str(error), statement) from error
        finally:
            if connected:
                self.close()

    def fetchone(self):
        """Fetch the next row, None if the connection is closed"""
        if self.connected:
            return self.cursor.fetchone()
        return None

    def fetchall(self):
        """Fetch all remaining rows, None if the connection is closed"""
        if self.connected:
            return self.cursor.fetchall()
        return None

    def execute_transaction(self, statement, mapset=None):
        """Execute a transactional SQL statement

        The BEGIN and END TRANSACTION statements will be added automatically
        to the sql statement

        :param statement: The executable SQL statement or SQL script
        """
        connected = False
        if not self.connected:
            self.connect()
            connected = True

        sql_script = f"BEGIN TRANSACTION;\n{statement};\nEND TRANSACTION;"

        try:
            if self.dbmi.__name__ == "sqlite3":
                self.cursor.executescript(sql_script)
            else:
                self.cursor.execute(statement)
            self.connection.commit()
        except db_errors as error:
            self.msgr.debug(1, f"Unable to execute transaction:\n {statement}")
            # executescript() has already sent BEGIN. Without the rollback
            # close() would commit the statements that ran before the
            # failing one and the database would keep a half written entry.
            if self.dbmi.__name__ == "sqlite3" and self.connection.in_transaction:
                self.connection.rollback()
            raise SQLStatementError(str(error), statement) from error
        finally:
            if connected:
                self.close()


def init_dbif(dbif):
    """This method checks if the database interface connection exists,
    if not a new one will be created, connected and True will be returned.
    If the database interface exists but is not connected, the connection
    will be established.

    Library code uses connection(), which closes what it opened even if the
    block ends with an error; this function stays for scripts and tools that
    close by hand.

    :returns: the tuple (dbif, connection_state_changed)

    Usage code sample:

    .. code-block:: python

        dbif, connection_state_changed = tgis.init_dbif(None)

        sql = dbif.mogrify_sql_statement(
            ["SELECT * FROM raster_base WHERE ? = ?"], ["id", "soil@PERMANENT"]
        )
        dbif.execute_transaction(sql)

        if connection_state_changed:
            dbif.close()

    """
    connection_state_changed = False

    if dbif is None:
        dbif = SQLDatabaseInterfaceConnection()
        dbif.connect()
        connection_state_changed = True
    elif dbif.is_connected() is False:
        dbif.connect()
        connection_state_changed = True

    return dbif, connection_state_changed


def sql_placeholder(dbmi_paramstyle: str) -> str:
    """Return the placeholder of an argument in the parameter style of the backend"""
    return "?" if dbmi_paramstyle == "qmark" else "%s"


# A name that SQLite and PostgreSQL read without quotes. Statements are
# written without quotes around names, so this is the form they can take.
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def sql_identifier(name: str) -> str:
    """Return a table, view or column name that may be written into a statement

    SQL has no placeholder for a name, so a name goes into the text of a
    statement. Only a plain name is let through: a letter or an underscore,
    then letters, digits and underscores. A name that starts with a digit is
    refused as well, because SQLite does not read it as a name ("unrecognized
    token"). Nothing but the name can get into a statement this way.

    :param name: The name of a table, view or column
    :return: The name, unchanged
    :raises ValueError: for anything else, None included
    """
    if not isinstance(name, str) or not _IDENTIFIER.fullmatch(name):
        msg = f"Not a plain SQL identifier: {name!r}"
        raise ValueError(msg)
    return name


def sql_statement(template: str, **identifiers: str) -> str:
    """Put checked names into the fixed text of a statement

    Each keyword fills the field of the same name in the template
    (str.format); every value passes sql_identifier() first. Values of the
    data do not belong here: they are bound as parameters or written with
    sql_literal().

    :param template: The text of the statement with a field for each name
    :param identifiers: The names of tables, views and columns
    :raises ValueError: if a name is not a plain identifier
    """
    return template.format(
        **{field: sql_identifier(name) for field, name in identifiers.items()}
    )


def _pg_args(args):
    """Bring the datetimes among the arguments for psycopg2 to database time

    SQLite does this in its adapter. psycopg2 sends a datetime as it is, with
    microseconds, so it is done before the call.
    """
    return tuple(db_datetime(a) if isinstance(a, datetime) else a for a in args)


def sql_literal(value: object, dbmi_paramstyle: str = "qmark") -> str:
    """Write a Python value as a literal of an SQL statement

    This is the text that mogrify_sql_statement() puts in place of a
    placeholder when SQLite has to give a statement as text. Text is put in
    single quotes with the quotes inside doubled, as SQLite escapes them;
    None is NULL; a float that is not finite is NULL too, because SQLite has
    no literal for inf and nan and would read the bare word as a column name
    (statistics of a map with infinite values are unknown, which is what NULL
    says). Floats have six decimals. Datetimes are written in whole seconds,
    the resolution of the database, with their offset if they have one: the
    same text as the SQLite adapter stores (db_datetime()).

    A text is written the same for every database: single quotes with the
    quotes inside doubled is standard SQL. The callers that put a text into a
    statement that is executed as text (a where condition, the delete or
    update statement of a script) call it with the default parameter style
    also when the database is PostgreSQL. The style is only a check that the
    caller does not ask for the literal of a backend that quotes by its
    connection; it changes nothing in the text.

    :param value: The value
    :param dbmi_paramstyle: The parameter style of the backend; only "qmark"
                            (SQLite) is supported, because psycopg2 quotes
                            with the help of its connection (cursor.mogrify)
    :raises ValueError: for any other parameter style, whatever the value
    """
    if dbmi_paramstyle != "qmark":
        msg = (
            f"No SQL literal without a connection for parameter style {dbmi_paramstyle}"
        )
        raise ValueError(msg)
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return f"{int(value)}"
    if isinstance(value, float) and not math.isfinite(value):
        return "NULL"
    if isinstance(value, float):
        return f"{value:f}"
    if isinstance(value, datetime):
        value = db_datetime(value)
    # Default is a string, this works for date objects too
    return "'{}'".format(str(value).replace("'", "''"))


@contextlib.contextmanager
def connection(
    dbif: SQLDatabaseInterfaceConnection | None = None,
) -> Iterator[SQLDatabaseInterfaceConnection]:
    """Give a connected database interface and close it again if opened here

    Replaces the pair of init_dbif() and the test of connection_state_changed
    before every return. A connection that is passed in and already connected
    is handed on as it is and stays open. Without one, or with one that is not
    connected, a connection is made and closed when the block ends, also when
    it ends with an exception such as the FatalError of msgr.fatal().

    :param dbif: The database interface of the caller, or None
    """
    dbif, connection_state_changed = init_dbif(dbif)
    try:
        yield dbif
    finally:
        if connection_state_changed:
            dbif.close()
