"""Test t.upgrade on a current database, on a database of version 2 and on others

A database of version 2 is made from a current one in sqlite, see
downgrade_to_version_2(). Every test gets its own project, because the tests
change the database.
"""

import sqlite3

import psycopg2
import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, make_map
from grass.temporal.testing.database_image import structure_of
from grass.temporal.testing.postgresql import rows_of
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.temporal.testing.session import project_session
from grass.temporal.testing.versions import (
    NEWER_INDEXES,
    VERSION_2_ID_INDEXED_TABLES,
    database_file,
    downgrade_postgresql_to_version_2,
    downgrade_to_version_2,
    set_version,
    use_older_strds_views,
)
from grass.tools import ToolError, Tools

CURRENT_VERSION = "3"


def query(database, statement):
    with sqlite3.connect(database) as connection:
        return connection.execute(statement).fetchall()


def version_of(database):
    return query(
        database, "SELECT value FROM tgis_metadata WHERE key = 'tgis_db_version'"
    )[0][0]


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


BACKENDS = ["sqlite", pytest.param("postgresql", marks=pytest.mark.postgresql)]
VIEW_COUNT = 12


def fetch(backend, dbstring, statement):
    """Run a statement on either backend and return its rows"""
    if backend == "sqlite":
        return query(dbstring, statement)
    connection = psycopg2.connect(dbstring)
    try:
        with connection, connection.cursor() as cursor:
            cursor.execute(statement)
            return cursor.fetchall() if cursor.description else []
    finally:
        connection.close()


@pytest.fixture(params=BACKENDS)
def either_backend(request, tmp_path):
    """Backend, tools, session and database of a project with a current database

    Like project, on sqlite and on PostgreSQL. The dataset "series" has two
    maps; "empty" has none. The database is a string: the file for sqlite,
    the libpq text for PostgreSQL.
    """
    backend = request.param
    dbstring = (
        request.getfixturevalue("postgresql_database")
        if backend == "postgresql"
        else None
    )
    with project_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        if backend == "postgresql":
            tools.t_connect(driver="pg", database=dbstring)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools,
            "strds",
            "series",
            [MapSpec(f"map{i}", i, day(i - 1), day(i)) for i in (1, 2)],
        )
        create_stds(tools, "strds", "empty", [])
        if backend == "sqlite":
            dbstring = str(database_file(session))
        yield backend, tools, session, dbstring


def downgrade(backend, session, dbstring):
    if backend == "sqlite":
        downgrade_to_version_2(session)
    else:
        downgrade_postgresql_to_version_2(session, dbstring)


def stored_version(backend, dbstring):
    return fetch(
        backend,
        dbstring,
        "SELECT value FROM tgis_metadata WHERE key = 'tgis_db_version'",
    )[0][0]


def test_current_database_is_left_alone(project):
    tools, _, database = project
    before = structure_of(database)

    result = tools.t_upgrade()

    assert "up-to-date" in message(result)
    assert "created anew" in message(result)
    assert structure_of(database) == before
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
    (register,) = query(database, "SELECT raster_register FROM strds_metadata")[0]
    assert indexes(database) >= {
        f"{table}_index" for table in VERSION_2_ID_INDEXED_TABLES
    }
    assert f"{register}_index" in indexes(database)
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
    version_2 = indexes(database)

    tools.t_upgrade()

    # A new database has no index on the id alone, version 2 had them; the
    # upgrade keeps them, nothing drops them.
    assert indexes(database) == expected | version_2


def postgresql_indexes(dbstring):
    """Name, table and definition of every index of a PostgreSQL database"""
    return sorted(
        fetch(
            "postgresql",
            dbstring,
            "SELECT indexname, tablename, indexdef FROM pg_indexes"
            " WHERE schemaname = 'public'",
        )
    )


@pytest.mark.postgresql
def test_new_and_upgraded_postgresql_databases_have_the_same_indexes(
    tmp_path, postgresql_database
):
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        tools.t_connect(driver="pg", database=postgresql_database)
        create_stds(tools, "strds", "series", [MapSpec("map1", 1, day(0), day(1))])
        new = postgresql_indexes(postgresql_database)
        downgrade_postgresql_to_version_2(session, postgresql_database)

        tools.t_upgrade()

        assert postgresql_indexes(postgresql_database) == new
    assert {name for name, _, _ in new} >= NEWER_INDEXES


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


def test_a_failed_upgrade_leaves_the_views_and_the_version(either_backend):
    backend, tools, session, dbstring = either_backend
    downgrade(backend, session, dbstring)
    # Stands in for any error inside the upgrade script (a lock, a full disk,
    # a change made by hand): the script adds this column itself.
    fetch(
        backend,
        dbstring,
        "ALTER TABLE strds_metadata ADD COLUMN number_of_semantic_labels INTEGER",
    )
    before = rows_of(backend, dbstring)
    assert sum(key.startswith("VIEW ") for key in before) == VIEW_COUNT

    with pytest.raises(ToolError) as raised:
        tools.t_upgrade()

    text = message(raised.value)
    assert "The upgrade of the temporal database failed and was rolled back" in text
    assert "Traceback" not in text
    assert stored_version(backend, dbstring) == "2"
    assert rows_of(backend, dbstring) == before


def test_a_second_upgrade_after_a_failed_one_runs_through(either_backend):
    backend, tools, session, dbstring = either_backend
    downgrade(backend, session, dbstring)
    fetch(
        backend,
        dbstring,
        "ALTER TABLE strds_metadata ADD COLUMN number_of_semantic_labels INTEGER",
    )
    with pytest.raises(ToolError):
        tools.t_upgrade()
    fetch(
        backend,
        dbstring,
        "ALTER TABLE strds_metadata DROP COLUMN number_of_semantic_labels",
    )

    tools.t_upgrade()

    assert stored_version(backend, dbstring) == CURRENT_VERSION


def test_the_upgrade_counts_no_semantic_labels_in_old_datasets(either_backend):
    backend, tools, session, dbstring = either_backend
    downgrade(backend, session, dbstring)

    tools.t_upgrade()

    counts = dict(
        fetch(
            backend,
            dbstring,
            "SELECT id, number_of_semantic_labels FROM strds_metadata",
        )
    )
    assert counts == {"series@PERMANENT": 0, "empty@PERMANENT": None}


def test_version_2_with_data_is_upgraded_on_both_backends(either_backend):
    backend, tools, session, dbstring = either_backend
    current = rows_of(backend, dbstring)
    downgrade(backend, session, dbstring)
    before = rows_of(backend, dbstring)

    tools.t_upgrade()

    assert stored_version(backend, dbstring) == CURRENT_VERSION
    after = rows_of(backend, dbstring)
    assert after.keys() == before.keys()
    for name, rows in before.items():
        if name == "tgis_metadata":
            expected = sorted(
                [
                    (k, CURRENT_VERSION if k == "tgis_db_version" else v)
                    for k, v in rows
                ],
                key=repr,
            )
            assert after[name] == expected
        elif name.startswith("VIEW "):
            # The views of the upgraded database are those of the database
            # before the downgrade, with their rows.
            assert after[name] == current[name]
        elif name in ("raster_metadata", "strds_metadata"):
            # The two tables got one column at their end.
            assert sorted((row[:-1] for row in after[name]), key=repr) == rows
        else:
            assert after[name] == rows


def make_maps(tools, *, label=None):
    """Create a1 without and a2 with the semantic label, return their names"""
    for name, value in (("a1", 1), ("a2", 2)):
        make_map(tools, "raster", name, value)
    if label:
        tools.r_support(map="a2", semantic_label=label)
    return "a1,a2"


def registered_ids(backend, dbstring, table):
    return sorted(row[0] for row in fetch(backend, dbstring, f"SELECT id FROM {table}"))


def test_registering_a_labelled_map_in_version_2_names_t_upgrade(either_backend):
    backend, tools, session, dbstring = either_backend
    maps = make_maps(tools, label="S2_1")
    downgrade(backend, session, dbstring)
    before = rows_of(backend, dbstring)

    # Only the second map has a label, and no write may have happened before
    # it is found.
    with pytest.raises(ToolError) as raised:
        tools.t_register(
            input="series",
            maps=maps,
            start="2001-01-03",
            increment="1 day",
        )

    text = message(raised.value)
    assert (
        f"The temporal database <{dbstring}> has version 2, which cannot store "
        "the semantic label of <a2@PERMANENT>. Run t.upgrade first."
    ) in text
    assert "Traceback" not in text
    assert "no column named" not in text
    assert registered_ids(backend, dbstring, "raster_base") == [
        "map1@PERMANENT",
        "map2@PERMANENT",
    ]
    assert registered_ids(backend, dbstring, "raster_metadata") == [
        "map1@PERMANENT",
        "map2@PERMANENT",
    ]
    assert [row.name for row in list_maps(tools, "strds", "series")] == ["map1", "map2"]
    assert rows_of(backend, dbstring) == before


def test_registering_maps_without_labels_works_in_version_2(either_backend):
    backend, tools, session, dbstring = either_backend
    make_maps(tools)
    downgrade(backend, session, dbstring)

    tools.t_register(
        input="series", maps="a1,a2", start="2001-01-03", increment="1 day"
    )

    expected = ["a1@PERMANENT", "a2@PERMANENT", "map1@PERMANENT", "map2@PERMANENT"]
    assert registered_ids(backend, dbstring, "raster_base") == expected
    names = [row.name for row in list_maps(tools, "strds", "series")]
    assert names == ["map1", "map2", "a1", "a2"]


def view_columns(backend, dbstring):
    """The columns of every view, in their order, by view"""
    if backend == "sqlite":
        statement = (
            "SELECT m.name, p.name FROM sqlite_master m, pragma_table_info(m.name) p"
            " WHERE m.type = 'view' ORDER BY m.name, p.cid"
        )
    else:
        statement = (
            "SELECT c.table_name, c.column_name FROM information_schema.columns c"
            " JOIN information_schema.views v ON v.table_schema = c.table_schema"
            " AND v.table_name = c.table_name WHERE c.table_schema = 'public'"
            " ORDER BY c.table_name, c.ordinal_position"
        )
    columns = {}
    for view, column in fetch(backend, dbstring, statement):
        columns.setdefault(view, []).append(column)
    return columns


def all_indexes(backend, dbstring):
    if backend == "sqlite":
        statement = "SELECT name, sql FROM sqlite_master WHERE type = 'index'"
    else:
        statement = (
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public'"
        )
    return sorted(fetch(backend, dbstring, statement), key=repr)


def test_t_upgrade_creates_the_views_of_a_current_database_anew(either_backend):
    backend, tools, session, dbstring = either_backend
    current = view_columns(backend, dbstring)
    assert "number_of_semantic_labels" in current["strds_view_abs_time"]
    use_older_strds_views(session, None if backend == "sqlite" else dbstring)
    assert (
        "number_of_semantic_labels"
        not in view_columns(backend, dbstring)["strds_view_rel_time"]
    )

    result = tools.t_upgrade()

    assert (
        f"Temporal database <{dbstring}> is up-to-date; its views were created anew."
    ) in message(result)
    assert view_columns(backend, dbstring) == current
    first = (rows_of(backend, dbstring), all_indexes(backend, dbstring))

    tools.t_upgrade()

    assert view_columns(backend, dbstring) == current
    assert (rows_of(backend, dbstring), all_indexes(backend, dbstring)) == first
    assert stored_version(backend, dbstring) == CURRENT_VERSION


@pytest.mark.slow
def test_an_old_database_keeps_working_until_t_upgrade(project):
    # A database of version 3 made before: its strds views lack the count of
    # the semantic labels, and it has indexes on the id alone.
    tools, session, database = project
    use_older_strds_views(session)
    (register,) = query(database, "SELECT raster_register FROM strds_metadata")[0]
    old_indexes = {"strds_base_index", f"{register}_index"}
    query(database, "CREATE INDEX strds_base_index ON strds_base (id)")
    query(database, f"CREATE INDEX {register}_index ON {register} (id)")
    make_map(tools, "raster", "map3", 3)

    tools.t_register(input="series", maps="map3", start="2001-01-03", end="2001-01-04")

    assert [row.name for row in list_maps(tools, "strds", "series")] == [
        "map1",
        "map2",
        "map3",
    ]
    assert stds_info(tools, "strds", "series")["number_of_maps"] == 3
    assert tools.t_list(type="strds", columns="name").stdout == "series\n"
    (row,) = tools.t_list(type="strds", format="json").json
    assert row["number_of_maps"] == 3
    assert "number_of_semantic_labels" not in row

    result = tools.t_upgrade()

    assert "created anew" in message(result)
    (row,) = tools.t_list(type="strds", format="json").json
    assert row["number_of_semantic_labels"] == 0
    assert indexes(database) >= old_indexes
