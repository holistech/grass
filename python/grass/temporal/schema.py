"""Create, check and upgrade the temporal database

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from .db import (
    SQLDatabaseInterfaceConnection,
    SQLStatementError,
    connection,
    sql_literal,
)
from .state import (
    STATE,
    get_tgis_database_string,
    get_tgis_db_version,
    get_tgis_message_interface,
    get_tgis_version,
)


def metadata_value(metadata, key):
    """Return the value stored under key in the rows of tgis_metadata, or None

    The rows are read by the columns key and value. ``key in row`` must not be
    used for this: it asks for a column name on the rows of psycopg2, so on
    PostgreSQL it is never true for a key. Plain tuples work as well.

    :param metadata: The rows of the table tgis_metadata
    :param str key: The key to look up
    :returns: The value as text, or None if no row has the key
    """
    for entry in metadata:
        try:
            row_key, value = entry["key"], entry["value"]
        except TypeError:
            row_key, value = entry[0], entry[1]
        if row_key == key:
            return value
    return None


def get_tgis_db_version_from_metadata(metadata=None):
    """Get the version number of the temporal database from metadata

    :param list metadata: list of metadata items or None
    :returns: The version number of the temporal database as integer
    """
    if metadata is None:
        metadata = get_tgis_metadata()
    version = metadata_value(metadata, "tgis_db_version")
    if version is not None:
        return int(version)

    # return supported version if not possible to get from metadata
    return get_tgis_db_version()


def get_tgis_metadata(dbif=None):
    """Return the tgis metadata table as a list of rows (dicts)

    A fatal error is reported if the table cannot be read, so the result is
    never None.

    :param dbif: The database interface to be used
    :returns: The selected rows with key/value columns
    """

    with connection(dbif) as dbif:
        try:
            dbif.execute("SELECT * FROM tgis_metadata;\n")
            rows = dbif.fetchall()
        except SQLStatementError:
            # A caller that used to get None reported this same text itself.
            get_tgis_message_interface().fatal(
                _(
                    "Unable to receive temporal database metadata.\n"
                    "Current temporal database info:%(info)s"
                )
                % ({"info": get_database_info_string()})
            )

        return rows


def get_sql_template_path() -> str:
    """Return the directory of the SQL files that create the temporal database"""
    return str(Path(os.getenv("GISBASE"), "etc", "sql"))


def get_database_info_string():
    """Return the database module and the database string as text"""
    dbif = SQLDatabaseInterfaceConnection()

    info = "\nDBMI interface:..... " + str(dbif.get_dbmi().__name__)
    info += "\nTemporal database:.. " + str(get_tgis_database_string())
    return info


def _views_sql() -> str:
    """Return the SQL text that creates all views of the temporal database"""
    template_path = Path(get_sql_template_path())

    return "\n".join(
        (template_path / f"{sql_filename}.sql").read_text()
        for sql_filename in (
            "raster_views",
            "raster3d_views",
            "vector_views",
            "strds_views",
            "str3ds_views",
            "stvds_views",
        )
    )


def _create_temporal_database_views(dbif) -> None:
    """Create all views in the temporal database (internal use only)

    Used by create_temporal_database().

    :param dbif: The database interface to be used
    """
    dbif.execute_transaction(_views_sql())


def create_temporal_database(dbif) -> None:
    """This function will create the temporal database

    It will create all tables and triggers that are needed to run
    the temporal GIS

    :param dbif: The database interface to be used
    """
    template_path = Path(get_sql_template_path())
    msgr = get_tgis_message_interface()

    # The scripts in the order they run: the tables of the native data types
    # and of the space-time datasets, each followed by its metadata table.
    map_tables_template_sql = (template_path / "map_tables_template.sql").read_text()
    stds_tables_template_sql = (template_path / "stds_tables_template.sql").read_text()
    table_scripts = []
    for name in ("raster", "vector", "raster3d"):
        table_scripts.append(map_tables_template_sql.replace("GRASS_MAP", name))
        table_scripts.append((template_path / f"{name}_metadata_table.sql").read_text())
    for name in ("strds", "stvds", "str3ds"):
        table_scripts.append(stds_tables_template_sql.replace("STDS", name))
        table_scripts.append((template_path / f"{name}_metadata_table.sql").read_text())

    msgr.verbose(_("Creating temporal database: %s") % (str(STATE.database_string)))

    if STATE.backend == "sqlite":
        # We need to create the sqlite3 database path if it does not exist
        tgis_dir = Path(STATE.database_string).parent
        try:
            tgis_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            msgr.fatal(
                _(
                    "Unable to create SQLite temporal database\n"
                    "Exception: %s\nPlease use t.connect to set a "
                    "read- and writable temporal database path"
                )
                % (e)
            )

        # Set up the trigger that takes care of
        # the correct deletion of entries across the different tables
        delete_trigger_sql = (template_path / "sqlite3_delete_trigger.sql").read_text()
        indexes_sql = (template_path / "sqlite3_indexes.sql").read_text()
    else:
        # Set up the trigger that takes care of
        # the correct deletion of entries across the different tables
        delete_trigger_sql = (
            template_path / "postgresql_delete_trigger.sql"
        ).read_text()
        indexes_sql = (template_path / "postgresql_indexes.sql").read_text()

    # Connect now to the database
    if dbif.connected is not True:
        dbif.connect()

    # Execute the SQL statements
    for script in table_scripts:
        dbif.execute_transaction(script)

    # Create views
    _create_temporal_database_views(dbif)

    # The delete trigger
    dbif.execute_transaction(delete_trigger_sql)
    # The indexes
    dbif.execute_transaction(indexes_sql)

    # Create the tgis metadata table to store the database
    # initial configuration
    # The metadata table content
    metadata = {}
    metadata["tgis_version"] = get_tgis_version()
    metadata["tgis_db_version"] = get_tgis_db_version()
    metadata["creation_time"] = datetime.today()
    _create_tgis_metadata_table(metadata, dbif)

    dbif.close()


def upgrade_temporal_database(dbif) -> None:
    """This function will upgrade the temporal database if needed.

    It will update all tables and triggers that are requested by
    currently supported TGIS DB version.

    :param dbif: The database interface to be used
    """
    metadata = get_tgis_metadata(dbif)

    msgr = get_tgis_message_interface()
    upgrade_db_from = metadata_value(metadata, "tgis_db_version")
    if upgrade_db_from == str(get_tgis_db_version()):
        upgrade_db_from = None

    if upgrade_db_from is None:
        msgr.message(_("Temporal database is up-to-date. Operation canceled"))
        dbif.close()
        return

    template_path = Path(get_sql_template_path())
    try:
        upgrade_db_sql = (
            template_path
            / f"upgrade_db_{upgrade_db_from}_to_{get_tgis_db_version()}.sql"
        ).read_text()
    except FileNotFoundError:
        msgr.fatal(
            _("Unsupported TGIS DB upgrade scenario: from version %s to %s")
            % (upgrade_db_from, get_tgis_db_version())
        )

    drop_views_sql = (template_path / "drop_views.sql").read_text()

    msgr.message(
        _("Upgrading temporal database <%s> from version %s to %s...")
        % (STATE.database_string, upgrade_db_from, get_tgis_db_version())
    )
    _run_upgrade(dbif, f"{drop_views_sql}\n{upgrade_db_sql}\n{_views_sql()}")
    dbif.close()


def _run_upgrade(dbif, sql: str) -> None:
    """Run the SQL of an upgrade in one transaction, or end with a message

    One transaction: the views must not be gone when the upgrade fails, and
    the version must stay what it was.
    """
    try:
        dbif.execute_transaction(sql)
    except SQLStatementError as error:
        dbif.close()
        get_tgis_message_interface().fatal(
            _(
                "The upgrade of the temporal database failed and was rolled back: {error}"
            ).format(error=error)
        )


# One row of the metadata table. The values go in through sql_literal(), so a
# quote in a value cannot end the text early.
_METADATA_ROW = "INSERT INTO tgis_metadata (key, value) VALUES ({key} , {value});\n"


def _create_tgis_metadata_table(content, dbif=None) -> None:
    """!Create the temporal gis metadata table which stores all metadata
    information about the temporal database.

    :param content: The dictionary that stores the key:value metadata
                   that should be stored in the metadata table
    :param dbif: The database interface to be used
    """
    with connection(dbif) as dbif:
        statement = (
            "CREATE TABLE tgis_metadata (key VARCHAR NOT NULL, value VARCHAR);\n"
        )
        dbif.execute_transaction(statement)

        for key in content:
            # str() first: the creation time is stored as str() writes it,
            # with its microseconds, as before.
            statement = _METADATA_ROW.format(
                key=sql_literal(str(key)), value=sql_literal(str(content[key]))
            )
            dbif.execute_transaction(statement)
