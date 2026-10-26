"""
Rows of the temporal database tables as Python objects

Every dataset keeps its identification, time, space and register data in
rows of tables of its own. A row class lists its columns once, as Column
objects, and gets the getter, the setter and the property of each column
generated; what a column needs beyond that, such as the identifier or a
default time, is written by hand in the class and left alone. The row
classes serialize themselves to INSERT, SELECT and UPDATE statements and run
them through a database interface.

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .db import SQLDatabaseInterfaceConnection, sql_literal, sql_placeholder
from .state import (
    get_current_mapset,
    get_tgis_dbmi_paramstyle,
    get_tgis_message_interface,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator


@contextmanager
def _connected(dbif: SQLDatabaseInterfaceConnection | None) -> Iterator:
    """Yield the given database interface, or a connection made for the block

    A connection made here is closed when the block ends, also on an error.
    The interface of the caller is used as it is and left open. This differs
    from db.connection(), which connects an interface that is not connected.
    """
    if dbif:
        yield dbif
        return
    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        yield dbif
    finally:
        dbif.close()


def _join_terms(terms: Iterable[str], first: str, rest: str) -> str:
    """Join the terms of a statement; the first gets the prefix first, the others rest"""
    return "".join(
        (first if index == 0 else rest) + term for index, term in enumerate(terms)
    )


class DictSQLSerializer:
    """A dictionary of column values that is written as SQL statements

    ``serialize`` makes SELECT, INSERT and UPDATE statements with the
    placeholders of the paramstyle of the database module, and ``deserialize``
    reads a row back.
    """

    def __init__(self) -> None:
        self.D = {}
        self.dbmi_paramstyle = get_tgis_dbmi_paramstyle()

    def serialize(self, type, table, where=None, where_args=()):
        """Convert the internal dictionary into a string of semicolon
        separated SQL statements The keys are the column names and
        the values are the row entries

        Usage:

        .. code-block:: pycon

            >>> init()
            >>> t = DictSQLSerializer()
            >>> t.D["id"] = "soil@PERMANENT"
            >>> t.D["name"] = "soil"
            >>> t.D["mapset"] = "PERMANENT"
            >>> t.D["creator"] = "soeren"
            >>> t.D["creation_time"] = datetime(2001, 1, 1)
            >>> t.D["modification_time"] = datetime(2001, 1, 1)
            >>> t.serialize(type="SELECT", table="raster_base")
            ('SELECT  id  , name  , mapset  , creator  , creation_time  , modification_time  FROM raster_base ;\\n', ())
            >>> t.serialize(type="INSERT", table="raster_base")
            ('INSERT INTO raster_base ( id  ,name  ,mapset  ,creator  ,creation_time  ,modification_time ) VALUES (? ,? ,? ,? ,? ,?) ;\\n', ('soil@PERMANENT', 'soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0)))
            >>> t.serialize(type="UPDATE", table="raster_base")
            ('UPDATE raster_base SET  id = ?  ,name = ?  ,mapset = ?  ,creator = ?  ,creation_time = ?  ,modification_time = ? ;\\n', ('soil@PERMANENT', 'soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0)))
            >>> t.serialize(type="UPDATE ALL", table="raster_base")
            ('UPDATE raster_base SET  id = ?  ,name = ?  ,mapset = ?  ,creator = ?  ,creation_time = ?  ,modification_time = ? ;\\n', ('soil@PERMANENT', 'soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0)))

        :param type: must be SELECT. INSERT, UPDATE
        :param table: The name of the table to select, insert or update
        :param where: The optional where statement
        :param where_args: The values of the placeholders in the where statement,
                           appended to the arguments of the statement
        :return: a tuple containing the SQL string and the arguments

        """  # noqa: E501

        # A type that is none of these makes an empty statement, as before.
        sql = ""
        args = []
        if type == "SELECT":
            sql = "SELECT " + _join_terms(
                (f"{key} " for key in self.D), first=" ", rest=" , "
            )
            sql += " FROM " + table + " "
        elif type == "INSERT":
            placeholder = sql_placeholder(self.dbmi_paramstyle)
            sql = "INSERT INTO " + table + " ("
            sql += _join_terms((f"{key} " for key in self.D), first=" ", rest=" ,")
            sql += ") VALUES ("
            sql += _join_terms((placeholder for _key in self.D), first="", rest=" ,")
            sql += ") "
            args = list(self.D.values())
        elif type in {"UPDATE", "UPDATE ALL"}:
            # UPDATE writes only the entries which are not None.
            keys = [
                key for key in self.D if type == "UPDATE ALL" or self.D[key] is not None
            ]
            placeholder = sql_placeholder(self.dbmi_paramstyle)
            sql = "UPDATE " + table + " SET "
            sql += _join_terms(
                (f"{key} = {placeholder} " for key in keys), first=" ", rest=" ,"
            )
            args = [self.D[key] for key in keys]
        if type in {"SELECT", "INSERT", "UPDATE", "UPDATE ALL"}:
            if where:
                sql += where
            sql += ";\n"

        return sql, (*args, *where_args)

    def deserialize(self, row) -> None:
        """Convert the content of the dbmi dictionary like row into the
        internal dictionary

        :param row: The dictionary like row to store in the internal dict
        """
        self.D = {}
        # A sqlite3.Row iterates over its values, only keys() gives the names.
        for key in row.keys():  # noqa: SIM118
            self.D[key] = row[key]

    def clear(self) -> None:
        """Initialize the internal storage"""
        self.D = {}

    def print_self(self) -> None:
        """Print the content of the internal dictionary to stdout"""
        print(self.D)


###############################################################################


class SQLDatabaseInterface(DictSQLSerializer):
    """This class represents the SQL database interface

    Functions to insert, select and update the internal
    structure of this class in the temporal database are implemented.
    This is the base class for raster, raster3d, vector and
    space time datasets data management classes:

    - Identification information (base)
    - Spatial extent
    - Temporal extent
    - Metadata

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> t = SQLDatabaseInterface("raster", "soil@PERMANENT")
        >>> t.mapset = get_current_mapset()
        >>> t.D["name"] = "soil"
        >>> t.D["mapset"] = "PERMANENT"
        >>> t.D["creator"] = "soeren"
        >>> t.D["creation_time"] = datetime(2001, 1, 1)
        >>> t.get_delete_statement()
        "DELETE FROM raster WHERE id = 'soil@PERMANENT';\\n"
        >>> t.get_is_in_db_statement()
        ('SELECT id FROM raster WHERE id = ?;\\n', ('soil@PERMANENT',))
        >>> t.get_select_statement()
        ('SELECT  name  , mapset  , creator  , creation_time  FROM raster WHERE id = ?;\\n', ('soil@PERMANENT',))
        >>> t.get_select_statement_mogrified()
        "SELECT  name  , mapset  , creator  , creation_time  FROM raster WHERE id = 'soil@PERMANENT';\\n"
        >>> t.get_insert_statement()
        ('INSERT INTO raster ( name  ,mapset  ,creator  ,creation_time ) VALUES (? ,? ,? ,?) ;\\n', ('soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0)))
        >>> t.get_insert_statement_mogrified()
        "INSERT INTO raster ( name  ,mapset  ,creator  ,creation_time ) VALUES ('soil' ,'PERMANENT' ,'soeren' ,'2001-01-01 00:00:00') ;\\n"
        >>> t.get_update_statement()
        ('UPDATE raster SET  name = ?  ,mapset = ?  ,creator = ?  ,creation_time = ? WHERE id = ?;\\n', ('soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0), 'soil@PERMANENT'))
        >>> t.get_update_statement_mogrified()
        "UPDATE raster SET  name = 'soil'  ,mapset = 'PERMANENT'  ,creator = 'soeren'  ,creation_time = '2001-01-01 00:00:00' WHERE id = 'soil@PERMANENT';\\n"
        >>> t.get_update_all_statement()
        ('UPDATE raster SET  name = ?  ,mapset = ?  ,creator = ?  ,creation_time = ? WHERE id = ?;\\n', ('soil', 'PERMANENT', 'soeren', datetime.datetime(2001, 1, 1, 0, 0), 'soil@PERMANENT'))
        >>> t.get_update_all_statement_mogrified()
        "UPDATE raster SET  name = 'soil'  ,mapset = 'PERMANENT'  ,creator = 'soeren'  ,creation_time = '2001-01-01 00:00:00' WHERE id = 'soil@PERMANENT';\\n"

    """  # noqa: E501

    def __init__(self, table=None, ident=None) -> None:
        """Constructor of this class

        :param table: The name of the table
        :param ident: The identifier (primary key) of this
                      object in the database table
        """
        super().__init__()

        self.table = table  # Name of the table, set in the subclass
        self.ident = ident

        if self.ident and self.ident.find("@") >= 0:
            self.mapset = self.ident.split("@")[1]
        else:
            self.mapset = None

    @property
    def msgr(self):
        """The messenger of the current session, fetched at each use"""
        return get_tgis_message_interface()

    def get_table_name(self):
        """Return the name of the table in which the internal
        data are inserted, updated or selected

        :return: The name of the table
        """
        return self.table

    def get_delete_statement(self):
        """Return the delete string

        :return: The DELETE string
        """
        return (
            "DELETE FROM "
            + self.get_table_name()
            + " WHERE id = "
            + sql_literal(str(self.ident))
            + ";\n"
        )

    def _where_id(self, ident):
        """Return the where statement for an identifier and its argument"""
        placeholder = sql_placeholder(self.dbmi_paramstyle)
        return f"WHERE id = {placeholder}", (str(ident),)

    def delete(self, dbif=None) -> None:
        """Delete the entry of this object from the temporal database

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        """
        where, args = self._where_id(self.ident)
        sql = f"DELETE FROM {self.get_table_name()} {where};\n"

        # must use the temporal database of the current mapset,
        # also if the map to be deleted is in a different mapset
        mapset = get_current_mapset()
        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)

    def get_is_in_db_statement(self):
        """Return the selection string that checks if this object is registered in the
        temporal database

        :return: The SELECT string and the argument list
        """
        where, args = self._where_id(self.ident)
        return f"SELECT id FROM {self.get_table_name()} {where};\n", args

    def is_in_db(self, dbif=None, mapset=None) -> bool:
        """Check if this object is present in the temporal database

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :param mapset: The mapset with a temporal database to be used
                       The mapset of the database can be different from
                       the mapset of the map
        :return: True if this object is present in the temporal database,
                 False otherwise
        """

        sql, args = self.get_is_in_db_statement()

        # default: search temporal database in the mapset of the map
        if mapset is None:
            mapset = self.mapset

        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)
            row = dbif.fetchone(mapset=mapset)

        # Nothing found
        return row is not None

    def get_select_statement(self):
        """Return the sql statement and the argument list in
        database specific style

        :return: The SELECT string
        """
        return self.serialize(
            "SELECT", self.get_table_name(), *self._where_id(self.ident)
        )

    def get_select_statement_mogrified(self, dbif=None):
        """Return the select statement as mogrified string

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :return: The SELECT string
        """
        if not dbif:
            dbif = SQLDatabaseInterfaceConnection()

        return dbif.mogrify_sql_statement(
            self.get_select_statement(), mapset=self.mapset
        )

    def select(self, dbif=None, mapset=None) -> bool:
        """Select the content from the temporal database and store it
        in the internal dictionary structure

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        """
        sql, args = self.get_select_statement()

        # default: use the temporal database in the mapset of this map
        if mapset is None:
            mapset = self.mapset

        self.msgr.debug(2, f"SQLDatabaseInterface.select() from mapset {mapset}")

        # The statement always has the identifier as argument.
        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)
            row = dbif.fetchone(mapset=mapset)

        # Nothing found
        if row is None:
            return False

        if len(row) > 0:
            self.deserialize(row)
        else:
            self.msgr.fatal(_("Object not found in the temporal database"))

        return True

    def get_insert_statement(self):
        """Return the sql statement and the argument
        list in database specific style

        :return: The INSERT string
        """
        return self.serialize("INSERT", self.get_table_name())

    def get_insert_statement_mogrified(self, dbif=None):
        """Return the insert statement as mogrified string

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :return: The INSERT string
        """
        if not dbif:
            dbif = SQLDatabaseInterfaceConnection()

        # mapset must be the mapset of the temporal database
        # not of the map
        mapset = get_current_mapset()
        return dbif.mogrify_sql_statement(self.get_insert_statement(), mapset=mapset)

    def insert(self, dbif=None) -> None:
        """Serialize the content of this object and store it in the temporal
        database using the internal identifier

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        """
        sql, args = self.get_insert_statement()

        # use the temporal database in the current mapset
        mapset = get_current_mapset()

        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)

    def get_update_statement(self, ident=None):
        """Return the sql statement and the argument list
        in database specific style

        :param ident: The identifier to be updated, useful for renaming
        :return: The UPDATE string
        """
        return self.serialize(
            "UPDATE", self.get_table_name(), *self._where_id(ident or self.ident)
        )

    def get_update_statement_mogrified(self, dbif=None, ident=None):
        """Return the update statement as mogrified string

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :param ident: The identifier to be updated, useful for renaming
        :return: The UPDATE string
        """

        # use the temporal database in the current mapset
        mapset = get_current_mapset()

        if not dbif:
            dbif = SQLDatabaseInterfaceConnection()

        return dbif.mogrify_sql_statement(
            self.get_update_statement(ident), mapset=mapset
        )

    def update(self, dbif=None, ident=None) -> None:
        """Serialize the content of this object and update it in the temporal
        database using the internal identifier

        Only object entries which are exists (not None) are updated

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :param ident: The identifier to be updated, useful for renaming
        """
        if self.ident is None:
            self.msgr.fatal(_("Missing identifier"))

        # use the temporal database in the current mapset
        mapset = get_current_mapset()

        sql, args = self.get_update_statement(ident)

        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)

    def get_update_all_statement(self, ident=None):
        """Return the sql statement and the argument
        list in database specific style

        :param ident: The identifier to be updated, useful for renaming
        :return: The UPDATE string
        """
        return self.serialize(
            "UPDATE ALL", self.get_table_name(), *self._where_id(ident or self.ident)
        )

    def get_update_all_statement_mogrified(self, dbif=None, ident=None):
        """Return the update all statement as mogrified string

        :param dbif: The database interface to be used,
                     if None a temporary connection will be established
        :param ident: The identifier to be updated, useful for renaming
        :return: The UPDATE string
        """
        if not dbif:
            dbif = SQLDatabaseInterfaceConnection()

        return dbif.mogrify_sql_statement(self.get_update_all_statement(ident))

    def update_all(self, dbif=None, ident=None) -> None:
        """Serialize the content of this object, including None objects,
        and update it in the temporal database using the internal identifier

        :param dbif: The database interface to be used,
                    if None a temporary connection will be established
        :param ident: The identifier to be updated, useful for renaming
        """
        if self.ident is None:
            self.msgr.fatal(_("Missing identifier"))

        # use the temporal database in the current mapset
        mapset = get_current_mapset()

        sql, args = self.get_update_all_statement(ident)

        with _connected(dbif) as dbif:
            dbif.execute(sql, args, mapset=mapset)


@dataclass(frozen=True)
class Column:
    """A column of a table, with the accessors that are generated for it

    :param name: The name of the column, the key in the dictionary D of the
                 row and the column in the table
    :param alias: The name the accessors carry when it is not the name of
                  the column, such as ctime for creation_time
    :param convert: Applied to a value before it is stored, such as float
                    for an edge of a spatial extent; None passes the value on
    :param doc: What the column holds, for the docstrings of the accessors
    :param writable: False for a value the database computes, which gets a
                     getter and a read-only property but no setter
    :param init: Whether a constructor that stores the columns (the metadata
                 rows) puts the column in the row when no value is given: a
                 bool, or a function that decides when the row is made
    :param default: The value that constructor stores when none is given
    """

    name: str
    alias: str | None = None
    convert: Callable[[object], object] | None = None
    doc: str | None = None
    writable: bool = True
    init: bool | Callable[[], bool] = True
    default: object = None

    @property
    def accessor(self) -> str:
        """The name that get_, set_ and the property are built from"""
        return self.alias or self.name


def _generate_accessors(cls: type, column: Column) -> None:
    """Add get_<name>, set_<name> and the property <name> of a column to cls

    A column that is not writable gets no setter, and its property no fset.

    A name that the class or a base class already has is left alone: the
    identifier of a dataset, a default time or a validated type are written
    by hand where a plain store is not enough.
    """
    accessor = column.accessor
    what = column.doc or f"the {column.name.replace('_', ' ')}"
    key, convert = column.name, column.convert

    def getter(self):
        return self.D.get(key)

    def setter(self, value) -> None:
        self.D[key] = value if convert is None else convert(value)

    accessors = [
        ("get", getter, f"Get {what}\n\n        :return: None if not found\n        ")
    ]
    if column.writable:
        accessors.append(("set", setter, f"Set {what}"))
    for prefix, function, text in accessors:
        name = f"{prefix}_{accessor}"
        if not hasattr(cls, name):
            function.__name__ = name
            function.__qualname__ = f"{cls.__qualname__}.{name}"
            function.__doc__ = text
            setattr(cls, name, function)
    if not hasattr(cls, accessor):
        setattr(cls, accessor, accessor_property(accessor, column.writable))


def accessor_property(accessor: str, writable: bool = True) -> property:
    """Return the property that calls get_<accessor> and set_<accessor>

    The accessors are looked up on the instance, so that a class that
    overrides one, such as the setter of the identifier, is called by the
    property of its base class, too.
    """
    return property(
        fget=lambda self: getattr(self, f"get_{accessor}")(),
        fset=(lambda self, value: getattr(self, f"set_{accessor}")(value))
        if writable
        else None,
    )


class Row(SQLDatabaseInterface):
    """A row of a table, whose columns are listed in the class

    A subclass lists the columns it adds in its class attribute ``columns``;
    the accessors of each are generated when the class is created. The order
    of the keys in D, which is the order of the columns in the INSERT
    statement, is not the order of ``columns``: it is the order in which the
    constructor stores the values, and the constructors keep it as it was
    before the accessors were generated.
    """

    columns: tuple[Column, ...] = ()

    def set_id(self, ident) -> None:
        """Convenient method to set the unique identifier (primary key)"""
        self.ident = ident
        self.D["id"] = ident

    def get_id(self):
        """Convenient method to get the unique identifier (primary key)

        :return: None if not found
        """
        return self.D.get("id")

    id = accessor_property("id")

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        for column in cls.__dict__.get("columns", ()):
            _generate_accessors(cls, column)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
