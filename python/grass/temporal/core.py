"""Names of the temporal framework core under their former module

The code of this module lives in state.py (session state and init()), db.py
(connections) and schema.py (creating, checking and upgrading the database).
The names stay importable from here because addons and scripts use
``tgis.core.get_current_mapset()`` and similar calls. The module holds no
state: read the session through the get_*() functions.

SPDX-FileCopyrightText: 2011-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:author: Soeren Gebbert
"""

from .db import (
    DBConnection,
    SQLDatabaseInterfaceConnection,
    SQLStatementError,
    adapt_datetime_iso,
    convert_datetime,
    db_errors,
    get_available_temporal_mapsets,
    init_dbif,
)
from .schema import (
    create_temporal_database,
    get_database_info_string,
    get_sql_template_path,
    get_tgis_db_version_from_metadata,
    get_tgis_metadata,
    upgrade_temporal_database,
)
from .state import (
    get_current_mapset,
    get_enable_mapset_check,
    get_enable_timestamp_write,
    get_raise_on_error,
    get_tgis_c_library_interface,
    get_tgis_database_string,
    get_tgis_db_version,
    get_tgis_dbmi_paramstyle,
    get_tgis_message_interface,
    get_tgis_version,
    init,
    profile_function,
    set_raise_on_error,
    stop_subprocesses,
    tools,
)

__all__ = [
    "DBConnection",
    "SQLDatabaseInterfaceConnection",
    "SQLStatementError",
    "adapt_datetime_iso",
    "convert_datetime",
    "create_temporal_database",
    "db_errors",
    "get_available_temporal_mapsets",
    "get_current_mapset",
    "get_database_info_string",
    "get_enable_mapset_check",
    "get_enable_timestamp_write",
    "get_raise_on_error",
    "get_sql_template_path",
    "get_tgis_c_library_interface",
    "get_tgis_database_string",
    "get_tgis_db_version",
    "get_tgis_db_version_from_metadata",
    "get_tgis_dbmi_paramstyle",
    "get_tgis_message_interface",
    "get_tgis_metadata",
    "get_tgis_version",
    "init",
    "init_dbif",
    "profile_function",
    "set_raise_on_error",
    "stop_subprocesses",
    "tools",
    "upgrade_temporal_database",
]
