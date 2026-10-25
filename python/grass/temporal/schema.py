"""Create, check and upgrade the temporal database

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from .db import SQLDatabaseInterfaceConnection, SQLStatementError, init_dbif
from .state import (
    STATE,
    get_tgis_database_string,
    get_tgis_db_version,
    get_tgis_message_interface,
    get_tgis_version,
)


def get_tgis_db_version_from_metadata(metadata=None):
    """Get the version number of the temporal database from metadata

    :param list metadata: list of metadata items or None
    :returns: The version number of the temporal database as integer
    """
    if metadata is None:
        metadata = get_tgis_metadata()
    for entry in metadata:
        if "tgis_db_version" in entry:
            return int(entry[1])

    # return supported version if not possible to get from metadata
    return get_tgis_db_version()


###############################################################################


def get_tgis_metadata(dbif=None):
    """Return the tgis metadata table as a list of rows (dicts)

    A fatal error is reported if the table cannot be read, so the result is
    never None.

    :param dbif: The database interface to be used
    :returns: The selected rows with key/value columns
    """

    dbif, connection_state_changed = init_dbif(dbif)

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
    finally:
        if connection_state_changed:
            dbif.close()

    return rows


def get_sql_template_path() -> str:
    return str(Path(os.getenv("GISBASE"), "etc", "sql"))


def get_database_info_string():
    dbif = SQLDatabaseInterfaceConnection()

    info = "\nDBMI interface:..... " + str(dbif.get_dbmi().__name__)
    info += "\nTemporal database:.. " + str(get_tgis_database_string())
    return info


###############################################################################


def _create_temporal_database_views(dbif) -> None:
    """Create all views in the temporal database (internal use only)

    Used by create_temporal_database() and upgrade_temporal_database().

    :param dbif: The database interface to be used
    """
    template_path = Path(get_sql_template_path())

    for sql_filename in (
        "raster_views",
        "raster3d_views",
        "vector_views",
        "strds_views",
        "str3ds_views",
        "stvds_views",
    ):
        sql_filepath = (template_path / f"{sql_filename}.sql").read_text()
        dbif.execute_transaction(sql_filepath)


def create_temporal_database(dbif) -> None:
    """This function will create the temporal database

    It will create all tables and triggers that are needed to run
    the temporal GIS

    :param dbif: The database interface to be used
    """
    template_path = Path(get_sql_template_path())
    msgr = get_tgis_message_interface()

    # Read all SQL scripts and templates
    map_tables_template_sql = (template_path / "map_tables_template.sql").read_text()
    raster_metadata_sql = (template_path / "raster_metadata_table.sql").read_text()
    raster3d_metadata_sql = (template_path / "raster3d_metadata_table.sql").read_text()
    vector_metadata_sql = (template_path / "vector_metadata_table.sql").read_text()
    stds_tables_template_sql = (template_path / "stds_tables_template.sql").read_text()
    strds_metadata_sql = (template_path / "strds_metadata_table.sql").read_text()
    str3ds_metadata_sql = (template_path / "str3ds_metadata_table.sql").read_text()
    stvds_metadata_sql = (template_path / "stvds_metadata_table.sql").read_text()

    # Create the raster, raster3d and vector tables SQL statements
    raster_tables_sql = map_tables_template_sql.replace("GRASS_MAP", "raster")
    vector_tables_sql = map_tables_template_sql.replace("GRASS_MAP", "vector")
    raster3d_tables_sql = map_tables_template_sql.replace("GRASS_MAP", "raster3d")

    # Create the space-time raster, raster3d and vector dataset tables
    # SQL statements
    strds_tables_sql = stds_tables_template_sql.replace("STDS", "strds")
    stvds_tables_sql = stds_tables_template_sql.replace("STDS", "stvds")
    str3ds_tables_sql = stds_tables_template_sql.replace("STDS", "str3ds")

    msgr.verbose(_("Creating temporal database: %s") % (str(STATE.database_string)))

    if STATE.backend == "sqlite":
        # We need to create the sqlite3 database path if it does not exist
        tgis_dir = Path(STATE.database_string).parent
        try:
            tgis_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
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
    # Create the global tables for the native grass datatypes
    dbif.execute_transaction(raster_tables_sql)
    dbif.execute_transaction(raster_metadata_sql)
    dbif.execute_transaction(vector_tables_sql)
    dbif.execute_transaction(vector_metadata_sql)
    dbif.execute_transaction(raster3d_tables_sql)
    dbif.execute_transaction(raster3d_metadata_sql)
    # Create the tables for the new space-time datatypes
    dbif.execute_transaction(strds_tables_sql)
    dbif.execute_transaction(strds_metadata_sql)
    dbif.execute_transaction(stvds_tables_sql)
    dbif.execute_transaction(stvds_metadata_sql)
    dbif.execute_transaction(str3ds_tables_sql)
    dbif.execute_transaction(str3ds_metadata_sql)

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


###############################################################################


def upgrade_temporal_database(dbif) -> None:
    """This function will upgrade the temporal database if needed.

    It will update all tables and triggers that are requested by
    currently supported TGIS DB version.

    :param dbif: The database interface to be used
    """
    metadata = get_tgis_metadata(dbif)

    msgr = get_tgis_message_interface()
    upgrade_db_from = None
    for entry in metadata:
        if "tgis_db_version" in entry and entry[1] != str(get_tgis_db_version()):
            upgrade_db_from = entry[1]
            break

    if upgrade_db_from is None:
        msgr.message(_("Temporal database is up-to-date. Operation canceled"))
        dbif.close()
        return

    template_path = Path(get_sql_template_path())
    try:
        upgrade_db_sql = (
            template_path
            / "upgrade_db_{}_to_{}.sql".format(upgrade_db_from, get_tgis_db_version())
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
    # Drop views
    dbif.execute_transaction(drop_views_sql)
    # Perform upgrade
    dbif.execute_transaction(upgrade_db_sql)
    # Recreate views
    _create_temporal_database_views(dbif)

    dbif.close()


###############################################################################


def _create_tgis_metadata_table(content, dbif=None) -> None:
    """!Create the temporal gis metadata table which stores all metadata
    information about the temporal database.

    :param content: The dictionary that stores the key:value metadata
                   that should be stored in the metadata table
    :param dbif: The database interface to be used
    """
    dbif, connection_state_changed = init_dbif(dbif)
    statement = "CREATE TABLE tgis_metadata (key VARCHAR NOT NULL, value VARCHAR);\n"
    dbif.execute_transaction(statement)

    for key in content:
        statement = (
            "INSERT INTO tgis_metadata (key, value) VALUES "
            + "('%s' , '%s');\n" % (str(key), str(content[key]))
        )
        dbif.execute_transaction(statement)

    if connection_state_changed:
        dbif.close()
