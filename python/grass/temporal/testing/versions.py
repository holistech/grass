# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Turn a current temporal database into one of an older version

Tests of t.upgrade and of the version check at the start of grass.temporal
need a database of version 2. The helpers here make one from a current
database instead of keeping a binary file, so that the layout follows the
installed SQL files.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import grass.script as gs

VIEW_TEMPLATES = ("raster", "raster3d", "vector", "strds", "str3ds", "stvds")
# sqlite3_indexes.sql got these when the spatial filter of the datasets came,
# with version 3 already in place; a database of version 2 has none of them.
NEWER_INDEXES = {
    "raster_spatial_extent_index_bbox",
    "raster3d_spatial_extent_index_bbox",
    "vector_spatial_extent_index_bbox",
    "raster_metadata_index_semantic_label",
}


def database_file(session) -> Path:
    """The sqlite file of the temporal database in the mapset of the session"""
    env = gs.gisenv(env=session.env)
    mapset = Path(env["GISDBASE"]) / env["LOCATION_NAME"] / env["MAPSET"]
    return mapset / "tgis" / "sqlite.db"


def sql_files(session) -> Path:
    """The directory with the SQL files of the installed temporal library"""
    return Path(session.env["GISBASE"]) / "etc" / "sql"


def set_version(database, version) -> None:
    """Write the version of a sqlite temporal database into its metadata"""
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE tgis_metadata SET value = ? WHERE key = 'tgis_db_version'",
            (str(version),),
        )


def downgrade_to_version_2(session) -> None:
    """Turn the database of the session into the layout of version 2

    The SQL files of version 2 (the last ones before semantic labels, then
    called band references, came) differ from today's in the two columns that
    upgrade_db_2_to_3.sql adds, in the label column of the raster views, the
    only view that mentions it, and in NEWER_INDEXES. So the indexes and the
    columns go, the views are rebuilt from the installed templates without
    the label column, and the version is set to 2. Compared on 18.10.2026
    with git show of the SQL files before the band reference commit.
    """
    database = database_file(session)
    templates = sql_files(session)
    with sqlite3.connect(database) as connection:
        connection.executescript((templates / "drop_views.sql").read_text())
        for index in sorted(NEWER_INDEXES):
            connection.execute(f"DROP INDEX {index}")
        connection.execute("ALTER TABLE raster_metadata DROP COLUMN semantic_label")
        connection.execute(
            "ALTER TABLE strds_metadata DROP COLUMN number_of_semantic_labels"
        )
        for name in VIEW_TEMPLATES:
            view = (templates / f"{name}_views.sql").read_text()
            connection.executescript(view.replace("A4.semantic_label, ", ""))
    set_version(database, 2)
