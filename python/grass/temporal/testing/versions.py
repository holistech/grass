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


# The tables that sqlite3_indexes.sql of version 2 indexed on the id alone,
# each with an index named <table>_index. SQLite indexes the primary key
# itself, so new databases no longer get them; databases of version 2 have them.
VERSION_2_ID_INDEXED_TABLES = tuple(
    f"{kind}_{table}"
    for kind in ("strds", "str3ds", "stvds")
    for table in (
        "base",
        "relative_time",
        "absolute_time",
        "spatial_extent",
        "metadata",
    )
) + tuple(
    f"{kind}_{table}"
    for kind in ("raster", "raster3d", "vector")
    for table in ("base", "spatial_extent", "stds_register", "metadata")
)
# The column of the metadata table of each dataset type that names its
# register table; the library of version 2 indexed each register table on id.
REGISTER_COLUMNS = {
    "strds_metadata": "raster_register",
    "str3ds_metadata": "raster3d_register",
    "stvds_metadata": "vector_register",
}


# The line of strds_views.sql that lists the count of the semantic labels.
_LABEL_COUNT_LINE = "A4.number_of_semantic_labels,\n"


def _version_2_view(view: str) -> str:
    """The SQL of a view template without the columns that version 3 added"""
    return view.replace("A4.semantic_label, ", "").replace(_LABEL_COUNT_LINE, "")


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
    upgrade_db_2_to_3.sql adds, in the views that list them (the label of the
    raster maps, the count of the labels of the space time raster datasets),
    in NEWER_INDEXES, and in the indexes on the id alone of the tables in
    VERSION_2_ID_INDEXED_TABLES and of every register table, which neither
    today's files nor the library create. So NEWER_INDEXES and the columns
    go, the views are rebuilt from the installed templates without those
    columns, the indexes on the id are created, and the version is set to 2.
    Compared on 18.10.2026 with git show of the SQL files before the band
    reference commit; the indexes compared again on 31.10.2026 by name, table
    and columns with sqlite3_indexes.sql of that commit plus one per register
    table: equal, and 30 missing without the indexes on the id.
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
            connection.executescript(_version_2_view(view))
        tables = list(VERSION_2_ID_INDEXED_TABLES)
        for metadata, column in REGISTER_COLUMNS.items():
            # The names come from the database under test, not from input.
            rows = connection.execute(
                f"SELECT {column} FROM {metadata} WHERE {column} IS NOT NULL"  # noqa: S608
            )
            tables.extend(row[0] for row in rows)
        for table in tables:
            connection.execute(f"CREATE INDEX {table}_index ON {table} (id)")
    set_version(database, 2)


def downgrade_postgresql_to_version_2(session, dbstring: str) -> None:
    """Turn a PostgreSQL temporal database into the layout of version 2

    The same steps as downgrade_to_version_2(), run through psycopg2 on the
    database dbstring, which t.connect and the first tgis.init() of the
    session have filled with the current tables. The SQL files are the ones of
    the session, as they are for sqlite.

    Compared on 31.10.2026 with a database of version 2 built in PostgreSQL 16
    from the SQL files before the band reference commit (git history, created
    as create_temporal_database() then did): the columns of all tables and
    views (name, type, nullability), the views, the indexes and the version
    row were equal. Run again, left out the downgrade, the comparison showed
    the four extra columns and the version, so it can see a difference.
    """
    import psycopg2  # noqa: PLC0415

    templates = sql_files(session)
    connection = psycopg2.connect(dbstring)
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute((templates / "drop_views.sql").read_text())
            for index in sorted(NEWER_INDEXES):
                cursor.execute(f"DROP INDEX {index}")
            cursor.execute("ALTER TABLE raster_metadata DROP COLUMN semantic_label")
            cursor.execute(
                "ALTER TABLE strds_metadata DROP COLUMN number_of_semantic_labels"
            )
            for name in VIEW_TEMPLATES:
                view = (templates / f"{name}_views.sql").read_text()
                cursor.execute(_version_2_view(view))
            cursor.execute(
                "UPDATE tgis_metadata SET value = '2' WHERE key = 'tgis_db_version'"
            )
    finally:
        connection.close()


def use_older_strds_views(session, dbstring: str | None = None) -> None:
    """Give a current database the strds views it had before t.upgrade

    The views of the space time raster datasets got number_of_semantic_labels
    without a new version of the database, so a database of version 3 made
    before has views without that column. On SQLite the database is the one of
    the session; on PostgreSQL it is dbstring.
    """
    view = (sql_files(session) / "strds_views.sql").read_text()
    sql = (
        "DROP VIEW strds_view_abs_time;\nDROP VIEW strds_view_rel_time;\n"
        + view.replace(_LABEL_COUNT_LINE, "")
    )
    if dbstring is None:
        with sqlite3.connect(database_file(session)) as connection:
            connection.executescript(sql)
        return
    import psycopg2  # noqa: PLC0415

    connection = psycopg2.connect(dbstring)
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(sql)
    finally:
        connection.close()
