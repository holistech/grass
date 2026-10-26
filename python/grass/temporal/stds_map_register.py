"""The table of maps that a space time dataset has registered

Every space time dataset keeps the identifiers of its maps in a table of its
own, the map register. The class StdsMapRegister holds everything that reads
or writes this table: creating, renaming and dropping it, registering and
unregistering a map, selecting the registered maps, and bringing the extent
and the metadata of the dataset up to date with them.

The table name comes from the temporal database and goes into SQL text,
because SQL has no placeholder for a table name. It is therefore checked
against the plain identifier form before it is used; a value that does not
match stops the call with a fatal error. The form is not the one that
create_name() makes: databases written by older versions hold tables named
differently, for example with underscores in the uuid, and the SQL of those
versions only worked for names of this plain form either.

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from grass.exceptions import FatalError

from .abstract_map_dataset import describe_map
from .datetime_math import string_to_datetime
from .db import connection
from .schema import get_sql_template_path, get_tgis_db_version_from_metadata
from .state import get_current_mapset
from .temporal_granularity import (
    compute_absolute_time_granularity,
    compute_relative_time_granularity,
)

# A name that needs no quoting in SQL. This is all that an unquoted statement,
# as older versions made them, could handle.
_TABLE_NAME = re.compile(r"[A-Za-z0-9_]+")


def _placeholder(dbif) -> str:
    """The placeholder of the parameter style of the backend"""
    return "?" if dbif.get_dbmi().paramstyle == "qmark" else "%s"


class StdsMapRegister:
    """The map register table of one space time dataset

    The object holds no state of its own except the dataset, so it is made
    whenever it is needed (AbstractSpaceTimeDataset.map_register) and a copy
    of the dataset never shares it with the original.

    :param stds: The space time dataset
    """

    def __init__(self, stds) -> None:
        self._stds = stds

    def table_name(self) -> str | None:
        """Return the name of the register table, None if there is none yet

        :raises ~grass.exceptions.FatalError: if the name is not a plain
            identifier
        """
        name = self._stds.get_map_register()
        if name is not None and not _TABLE_NAME.fullmatch(name):
            self._stds.msgr.fatal(
                _("Invalid name <{name}> of the map register table of <{ds}>").format(
                    name=name, ds=self._stds.get_id()
                )
            )
        return name

    def create_name(self) -> str:
        """Create the name of a new register table

        A uuid and the map type make the name.
        """
        map_type = self._stds.get_new_map_instance(None).get_type()
        return f"{map_type}_map_register_{uuid.uuid4().hex}"

    def create_statement(self, dbif) -> str:
        """Name a new register table, set the name and return its SQL

        This changes the dataset object only; the caller executes the
        statement together with the insert of the dataset.
        """
        name = self.create_name()
        sql = Path(get_sql_template_path(), "stds_map_register_table_template.sql")
        statement = sql.read_text().replace("SPACETIME_REGISTER_TABLE", name)
        if dbif.get_dbmi().__name__ == "sqlite3":
            statement += f"CREATE INDEX {name}_index ON {name} (id);"
        self._stds.set_map_register(name)
        self._stds.msgr.debug(
            1,
            _("Created register table <%s> for space time %s  dataset <%s>")
            % (
                name,
                self._stds.get_new_map_instance(None).get_type(),
                self._stds.get_id(),
            ),
        )
        return statement

    def drop_statement(self) -> str:
        """Return the SQL that drops the register table"""
        return f"DROP TABLE IF EXISTS {self.table_name()};\n"

    def rename_statement(self, dbif) -> str:
        """Give the register table a new name and return the SQL for it

        The new name is set in the dataset object, which must already carry
        its new identifier; the caller executes the statement.
        """
        old = self.table_name()
        new = self.create_name()
        self._stds.set_map_register(new)
        statement = f'ALTER TABLE {old} RENAME TO "{new}";\n'
        # SQLite names the index after the table
        if dbif.get_dbmi().__name__ == "sqlite3":
            statement += f"DROP INDEX {old}_index;\n"
            statement += f"CREATE INDEX {new}_index ON {new} (id);"
        return statement

    def contains(self, map_id: str, dbif=None) -> bool:
        """Check if a map is registered in the dataset

        :param map_id: The identifier of the map
        :param dbif: The database interface to be used
        """
        table = self.table_name()
        if table is None:
            return False
        stds = self._stds
        with connection(dbif) as dbif:
            sql = f"SELECT id FROM {table} WHERE id = ({_placeholder(dbif)})"
            try:
                dbif.execute(sql, (map_id,), mapset=stds.base.mapset)
                row = dbif.fetchone(mapset=stds.base.mapset)
            except FatalError:
                raise
            except Exception:
                stds.msgr.warning(_("Error in register table request"))
                raise
            return row is not None

    def register(self, map_, dbif=None) -> bool:
        """Register a map in the dataset

        The map must be in the temporal database and have the temporal type
        and, if it is relative, the unit of the dataset; the first map of a
        relative dataset sets the unit. A map that is registered already
        gives a warning and False.

        :param map_: The AbstractMapDataset object
        :param dbif: The database interface to be used
        :return: True if the map has been registered, False if it was
            registered already
        :raises ~grass.exceptions.FatalError: in case of a fatal error
        """
        stds = self._stds
        mapset = get_current_mapset()

        if stds.get_mapset() != mapset:
            stds.msgr.fatal(
                _(
                    "Unable to register map in dataset <%(ds)s> of "
                    "type %(type)s. The mapset of the database does "
                    "not match the current mapset"
                )
                % {"ds": stds.get_id(), "type": stds.get_type()}
            )

        # A connection that was handed in belongs to the caller, also when
        # the registration stops with an error.
        with connection(dbif) as dbif:
            return self._register(map_, dbif, mapset)

    def _register(self, map_, dbif, mapset) -> bool:
        """Register the map over the open connection, see register()"""
        stds = self._stds
        if map_.is_in_db(dbif, mapset=stds.get_mapset()) is False:
            stds.msgr.fatal(
                _(
                    "Only a map that was inserted in the temporal "
                    "database can be registered in a space time "
                    "dataset"
                )
            )

        stds.msgr.debug(
            1,
            f"Register {map_.get_type()} map {describe_map(map_)} in space time {map_.get_type()} dataset <{stds.get_id()}>",
        )

        # First select all data from the database in the current mapset
        map_.select(dbif, mapset=mapset)

        if not map_.check_for_correct_time():
            stds.msgr.fatal(_("Map %s has invalid time") % describe_map(map_))

        map_id = map_.base.get_id()
        map_rel_time_unit = map_.get_relative_time_unit()
        table = self.table_name()

        # The gathered SQL statements are stored here
        statement = ""

        if stds.get_temporal_type() != map_.get_temporal_type():
            stds.msgr.fatal(
                _(
                    "Temporal type of space time dataset "
                    "<%(id)s> and map %(map)s are different"
                )
                % {"id": stds.get_id(), "map": describe_map(map_)}
            )

        # In case no map has been registered yet, set the
        # relative time unit from the first map
        if (
            (
                stds.metadata.get_number_of_maps() is None
                or stds.metadata.get_number_of_maps() == 0
            )
            and stds.map_counter == 0
            and stds.is_time_relative()
        ):
            stds.set_relative_time_unit(map_rel_time_unit)
            statement += stds.relative_time.get_update_all_statement_mogrified(dbif)

            stds.msgr.debug(
                1,
                _("Set temporal unit for space time %s dataset <%s> to %s")
                % (map_.get_type(), stds.get_id(), map_rel_time_unit),
            )

        # Check the relative time unit
        if stds.is_time_relative() and (
            stds.get_relative_time_unit() != map_rel_time_unit
        ):
            stds.msgr.fatal(
                _(
                    "Relative time units of space time dataset "
                    "<%(id)s> and map %(map)s are different"
                )
                % {"id": stds.get_id(), "map": describe_map(map_)}
            )

        stds_mapset = stds.base.get_mapset()
        if stds_mapset != mapset:
            stds.msgr.fatal(
                _("Maps can only registered in a database in the current mapset")
            )

        if self.contains(map_id, dbif):
            stds.msgr.warning(_("Map %s is already registered.") % describe_map(map_))
            return False

        # Register the stds in the map stds register table column
        statement += map_.add_stds_to_register(
            stds_id=stds.base.get_id(), dbif=dbif, execute=False
        )

        # Now put the map name in the stds map register table
        sql = f"INSERT INTO {table} (id) VALUES ({_placeholder(dbif)});\n"
        statement += dbif.mogrify_sql_statement((sql, (map_id,)))

        # Only databases in the current mapset can be modified
        dbif.execute_transaction(statement, mapset=stds_mapset)

        stds.map_counter += 1

        return True

    def unregister(self, map_, dbif=None, execute: bool = True):
        """Unregister a map from the dataset

        :param map_: The map object to unregister
        :param dbif: The database interface to be used
        :param execute: If True the SQL DELETE statement is executed. If
            False the prepared statement is returned and the caller must
            execute it.
        :return: The SQL statement if execute is False, else an empty
            string; an empty string as well if the map is not registered
            (with a warning)
        """
        stds = self._stds
        mapset = get_current_mapset()

        if stds.get_mapset() != mapset:
            stds.msgr.debug(1, f"STDS name <{stds.get_name()}>")
            stds.msgr.fatal(
                _("Maps can only unregistered in a database in the current mapset")
            )

        statement = ""

        with connection(dbif) as dbif:
            if not self.contains(map_.get_id(), dbif):
                stds.msgr.warning(
                    _("Map %(map)s is not registered in space time dataset <%(base)s>")
                    % {"map": describe_map(map_), "base": stds.base.get_id()}
                )
                return ""

            # Remove the space time dataset from the dataset register of the
            # map. The statement must be executed here, otherwise the dataset
            # is not removed correctly.
            map_.remove_stds_from_register(stds.base.get_id(), dbif=dbif, execute=True)

            table = self.table_name()
            if table is not None:
                sql = f"DELETE FROM {table} WHERE id = {_placeholder(dbif)};\n"
                statement += dbif.mogrify_sql_statement((sql, (map_.get_id(),)))

            if execute:
                dbif.execute_transaction(statement, mapset=mapset)
                statement = ""

            stds.map_counter -= 1

            return statement

    def rows(
        self,
        columns=None,
        where=None,
        order=None,
        dbif=None,
        group=None,
        spatial_extent=None,
        spatial_relation=None,
    ):
        """Return the SQL rows of the selected registered maps

        See AbstractSpaceTimeDataset.get_registered_maps() for the meaning
        of the arguments.

        :return: The rows, None if the dataset has no register table
        """
        # Callers have always been allowed to end a condition with a
        # semicolon. Only the end is stripped; a semicolon inside is part of
        # the condition, as in name = 'a;b'.
        if where is not None:
            where = where.rstrip("; \t\r\n").lstrip()
        if order is not None:
            order = order.rstrip("; \t\r\n").lstrip()

        table = self.table_name()
        if table is None:
            return None

        stds = self._stds
        with connection(dbif) as dbif:
            map_type = stds.get_new_map_instance(None).get_type()
            if stds.get_temporal_type() == "absolute":
                map_view = map_type + "_view_abs_time"
            else:
                map_view = map_type + "_view_rel_time"

            if group:
                if not columns:
                    columns = f"{group},group_concat(id,',') AS id"
                else:
                    columns = (
                        group
                        + ", "
                        + ", ".join(
                            [
                                f"group_concat({column},',') AS {column}"
                                for column in columns.split(",")
                            ]
                        )
                    )
                if order is not None and order != "":
                    order = f"{group},{order}"
            else:
                columns = columns or "*"

            # filter by semantic label identifier
            if stds.semantic_label:
                where = stds._update_where_statement_by_semantic_label(where)

            # filter by spatial extent
            if spatial_extent and spatial_relation:
                where = stds._update_where_statement_by_spatial_extent(
                    where, spatial_extent, spatial_relation
                )

            sql = (
                f"SELECT {columns} FROM {map_view} "
                f"WHERE {map_view}.id IN (SELECT id FROM {table})"
            )

            if where is not None and where != "":
                sql += f" AND ({where})"
            if group:
                sql += f" GROUP BY {group}"
            if order is not None and order != "":
                sql += f" ORDER BY {order}"
            sql += ";"

            try:
                dbif.execute(sql, mapset=stds.base.mapset)
                return dbif.fetchall(mapset=stds.base.mapset)
            except RuntimeError:
                stds.msgr.error(
                    _("Unable to get map ids from register table <{}>").format(table)
                )
                raise

    def update_extent(self, dbif=None) -> None:
        """Update the extent, the metadata and the time type of the dataset

        The modification time, the spatial and temporal extent and the type
        specific metadata come from the registered maps. The end time of the
        dataset is the largest end time of the maps; if the maps have none,
        or the end is earlier than the largest start time, the largest start
        time is used.

        :param dbif: The database interface to be used
        """
        stds = self._stds

        if stds.get_mapset() != get_current_mapset():
            stds.msgr.fatal(
                _(
                    "Unable to update dataset <%(ds)s> of type "
                    "%(type)s in the temporal database. The mapset"
                    " of the database does not match the current "
                    "mapset"
                )
                % {"ds": stds.get_id(), "type": stds.get_type()}
            )

        stds.msgr.verbose(
            _(
                "Update metadata, spatial and temporal extent from"
                " all registered maps of <%s>"
            )
            % (stds.get_id())
        )

        # Nothing to do if the map register is not present
        table = self.table_name()
        if not table:
            return

        with connection(dbif) as dbif:
            # The templates read below use the UPDATE-FROM syntax, which SQLite
            # supports only since 3.33.
            dbmi = dbif.get_dbmi()
            if dbmi.__name__ == "sqlite3" and dbmi.sqlite_version_info < (3, 33):
                stds.msgr.fatal(
                    _(
                        "The temporal framework requires SQLite 3.33 or later to "
                        "update a space time dataset, but the Python sqlite3 module "
                        "uses SQLite {version}. Please update SQLite or switch the "
                        "temporal database to the PostgreSQL backend with t.connect."
                    ).format(version=dbmi.sqlite_version)
                )

            map_type = stds.get_new_map_instance(None).get_type()
            absolute = stds.is_time_absolute()
            sql_path = get_sql_template_path()

            # The spatial and temporal extent from the registered maps
            sql = Path(
                sql_path, "update_stds_spatial_temporal_extent_template.sql"
            ).read_text()
            sql = sql.replace("GRASS_MAP", map_type)
            sql = sql.replace("SPACETIME_REGISTER_TABLE", table)
            sql = sql.replace("SPACETIME_ID", stds.base.get_id())
            sql = sql.replace("STDS", stds.get_type())
            sql_script = sql + "\n"

            # The type specific metadata
            sql = Path(sql_path, f"update_{stds.get_type()}_metadata_template.sql")
            sql = sql.read_text()

            # Comment out update of semantic labels for DB version < 3
            if get_tgis_db_version_from_metadata() < 3:
                sql = sql.replace(
                    "number_of_semantic_labels = number_of_semantic_labels_new,",
                    "-- number_of_semantic_labels = number_of_semantic_labels_new,",
                )
                sql = sql.replace(
                    "count(distinct semantic_label)",
                    "-- count(distinct semantic_label)",
                )

            sql = sql.replace("SPACETIME_REGISTER_TABLE", table)
            sql = sql.replace("SPACETIME_ID", stds.base.get_id())
            sql_script += sql + "\n"

            dbif.execute_transaction(sql_script, mapset=stds.base.mapset)

            # Read and validate the selected end time
            stds.select(dbif)

            if absolute:
                _start_time, end_time = stds.get_absolute_time()
            else:
                _start_time, end_time, _unit = stds.get_relative_time()

            time_table = f"{map_type}_{'absolute' if absolute else 'relative'}_time"
            max_start = (
                f"SELECT max(start_time) FROM {time_table} WHERE {time_table}.id IN "
                f"(SELECT id FROM {table})"
            )

            # In case no end time is set, use the maximum start time of
            # all registered maps as end time
            use_start_time = end_time is None
            if not use_start_time:
                # Check if the end time is smaller than the maximum start time
                dbif.execute(max_start + ";", mapset=stds.base.mapset)
                row = dbif.fetchone(mapset=stds.base.mapset)

                if row is not None:
                    # The Python sqlite3 driver gives a text unless the
                    # connection is made with detect_types=PARSE_DECLTYPES
                    if dbif.get_dbmi().__name__ == "sqlite3" and absolute:
                        max_start_time = string_to_datetime(row[0])
                        if max_start_time is None:
                            max_start_time = end_time
                    else:
                        max_start_time = row[0]

                    if end_time < max_start_time:
                        use_start_time = True

            # Set the maximum start time as end time
            if use_start_time:
                sql = (
                    f"UPDATE {stds.get_type()}_{'absolute' if absolute else 'relative'}"
                    f"_time SET end_time = ({max_start}) "
                    f"WHERE id = '{stds.base.get_id()}';"
                )
                dbif.execute_transaction(sql, mapset=stds.base.mapset)

            # Count the temporal map types
            maps = stds.get_registered_maps(order="start_time", dbif=dbif)
            tlist = stds.count_temporal_types(maps)

            if tlist["interval"] > 0 and tlist["point"] == 0 and tlist["invalid"] == 0:
                map_time = "interval"
            elif (
                tlist["interval"] == 0 and tlist["point"] > 0 and tlist["invalid"] == 0
            ):
                map_time = "point"
            elif tlist["interval"] > 0 and tlist["point"] > 0 and tlist["invalid"] == 0:
                map_time = "mixed"
            else:
                map_time = "invalid"

            # Smallest supported temporal resolution
            if map_time == "invalid":
                gran = None
            elif absolute:
                gran = compute_absolute_time_granularity(maps)
            else:
                gran = compute_relative_time_granularity(maps)

            # Set the map time type and update the time objects
            stds.temporal_extent.select(dbif)
            stds.metadata.select(dbif)
            if stds.metadata.get_number_of_maps() > 0:
                stds.temporal_extent.set_map_time(map_time)
                stds.temporal_extent.set_granularity(gran)
            else:
                stds.temporal_extent.set_map_time(None)
                stds.temporal_extent.set_granularity(None)
            stds.temporal_extent.update_all(dbif)

            # Set the modification time
            stds.base.set_mtime(datetime.now())
            stds.base.update(dbif)
