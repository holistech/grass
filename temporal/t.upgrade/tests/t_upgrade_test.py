"""Test t.upgrade on a current database, on a database of version 2 and on others

A database of version 2 is made from a current one in sqlite, see
downgrade_to_version_2(). Every test gets its own project, because the tests
change the database.
"""

import sqlite3
from pathlib import Path

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

CURRENT_VERSION = "3"
VIEW_TEMPLATES = ("raster", "raster3d", "vector", "strds", "str3ds", "stvds")
# sqlite3_indexes.sql got these when the spatial filter of the datasets came,
# with version 3 already in place; a database of version 2 has none of them.
NEWER_INDEXES = {
    "raster_spatial_extent_index_bbox",
    "raster3d_spatial_extent_index_bbox",
    "vector_spatial_extent_index_bbox",
    "raster_metadata_index_semantic_label",
}


def database_file(session):
    """The sqlite file of the temporal database in the mapset of the session"""
    env = gs.gisenv(env=session.env)
    mapset = Path(env["GISDBASE"]) / env["LOCATION_NAME"] / env["MAPSET"]
    return mapset / "tgis" / "sqlite.db"


def sql_files(session):
    """The directory with the SQL files of the installed temporal library"""
    return Path(session.env["GISBASE"]) / "etc" / "sql"


def query(database, statement):
    with sqlite3.connect(database) as connection:
        return connection.execute(statement).fetchall()


def version_of(database):
    return query(
        database, "SELECT value FROM tgis_metadata WHERE key = 'tgis_db_version'"
    )[0][0]


def set_version(database, version):
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE tgis_metadata SET value = ? WHERE key = 'tgis_db_version'",
            (str(version),),
        )


def columns(database, table):
    return [row[1] for row in query(database, f"PRAGMA table_info({table})")]


def views(database):
    return sorted(
        row[0]
        for row in query(database, "SELECT name FROM sqlite_master WHERE type='view'")
    )


def indexes(database):
    rows = query(database, "SELECT name FROM sqlite_master WHERE type='index'")
    return {row[0] for row in rows}


def dump(database):
    """Every statement that rebuilds the database, to compare two states"""
    with sqlite3.connect(database) as connection:
        return list(connection.iterdump())


def downgrade_to_version_2(session):
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


@pytest.fixture
def project(tmp_path):
    """Tools, session and database file of a project with a current database

    The dataset "series" holds map1 (value 1) and map2 (value 2) on the first
    two days of 2001. Function scoped, because the tests change the database.
    Messages of a successful run are kept in result.stderr.
    """
    with project_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools,
            "strds",
            "series",
            [MapSpec(f"map{i}", i, day(i - 1), day(i)) for i in (1, 2)],
        )
        yield tools, session, database_file(session)


def test_current_database_is_left_alone(project):
    tools, _, database = project
    before = dump(database)

    result = tools.t_upgrade()

    assert "Temporal database is up-to-date. Operation canceled" in message(result)
    assert dump(database) == before
    assert version_of(database) == CURRENT_VERSION


def test_project_without_a_database_gets_a_current_one(tmp_path):
    with project_session(tmp_path / "fresh") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        assert not database_file(session).exists()

        result = tools.t_upgrade()

        assert "up-to-date" in message(result)
        assert version_of(database_file(session)) == CURRENT_VERSION


def test_quiet_hides_the_message_and_verbose_shows_it(project):
    tools, _, _ = project

    assert tools.t_upgrade(quiet=True).stderr == ""
    assert "up-to-date" in message(tools.t_upgrade(verbose=True))


def test_downgrade_for_the_tests_gives_version_2(project):
    # The checks that the upgrade tests below rely on: the fabricated database
    # has the layout of version 2, and the rest of GRASS says so.
    tools, session, database = project
    assert "semantic_label" in columns(database, "raster_metadata")

    downgrade_to_version_2(session)

    assert version_of(database) == "2"
    assert "semantic_label" not in columns(database, "raster_metadata")
    assert "number_of_semantic_labels" not in columns(database, "strds_metadata")
    assert not indexes(database) & NEWER_INDEXES
    warning = message(tools.t_info(type="strds", input="series", flags="g"))
    assert "Temporal database version mismatch detected" in warning
    assert "Run t.upgrade" in warning


@pytest.mark.slow
def test_version_2_is_upgraded_to_3(project):
    tools, session, database = project
    before_rows = list_maps(tools, "strds", "series")
    downgrade_to_version_2(session)

    result = tools.t_upgrade()

    assert "from version 2 to 3" in message(result)
    assert version_of(database) == CURRENT_VERSION
    assert "semantic_label" in columns(database, "raster_metadata")
    assert "number_of_semantic_labels" in columns(database, "strds_metadata")
    # The views are those of a database that was never downgraded.
    assert views(database) == sorted(
        f"{kind}_view_{time}_time"
        for kind in ("raster", "raster3d", "vector", "strds", "str3ds", "stvds")
        for time in ("abs", "rel")
    )
    # Nothing registered is lost, and GRASS no longer complains.
    assert list_maps(tools, "strds", "series") == before_rows
    assert "mismatch" not in message(
        tools.t_info(type="strds", input="series", flags="g")
    )


def test_current_database_has_the_newer_indexes(project):
    # Reference for the two tests below: a database created at version 3.
    _, _, database = project

    assert indexes(database) >= NEWER_INDEXES


def test_upgrade_creates_the_same_indexes_as_a_new_database(project):
    tools, session, database = project
    expected = indexes(database)
    downgrade_to_version_2(session)

    tools.t_upgrade()

    assert indexes(database) == expected


@pytest.mark.slow
def test_semantic_labels_work_after_the_upgrade(project):
    tools, session, _ = project
    downgrade_to_version_2(session)
    tools.t_upgrade()

    create_stds(
        tools,
        "strds",
        "labelled",
        [MapSpec("lab1", 5, day(0), day(1), semantic_label="S2_1")],
    )

    result = tools.t_rast_list(
        input="labelled", columns="name,semantic_label", format="json"
    )
    assert [(r["name"], r["semantic_label"]) for r in result.json["data"]] == [
        ("lab1", "S2_1")
    ]
    assert stds_info(tools, "strds", "labelled")["number_of_semantic_labels"] == 1


@pytest.mark.slow
def test_a_second_upgrade_changes_nothing(project):
    tools, session, database = project
    downgrade_to_version_2(session)
    tools.t_upgrade()
    after_first = dump(database)

    result = tools.t_upgrade()

    assert "up-to-date" in message(result)
    assert dump(database) == after_first


@pytest.mark.parametrize("version", ["1", "4"])
def test_other_versions_are_refused_and_left_alone(project, version):
    tools, _, database = project
    set_version(database, version)
    before = dump(database)

    with pytest.raises(ToolError) as raised:
        tools.t_upgrade()

    assert (
        f"Unsupported TGIS DB upgrade scenario: from version {version} to 3"
        in message(raised.value)
    )
    assert dump(database) == before
