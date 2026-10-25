"""Pin the statements and arguments of the database layer

The expected values were recorded from the code before the database layer
was moved out of core.py (25.10.2026, by calling the functions of that code
once and writing the results here). They are not derived from the code under
test. The PostgreSQL parts run without a server: a fake driver with
paramstyle pyformat stands in for psycopg2 and logs every call it receives.
"""

import datetime
import math
import types

import pytest

import grass.temporal as tgis
from grass.temporal import rows

# What the get_*_statement() methods return for a raster map when the
# parameter style of the backend is pyformat (PostgreSQL), as repr() text.
PYFORMAT = {
    "base.get_insert_statement": "('INSERT INTO raster_base ( mapset  ,id  ,name  "
    ",creator  ,creation_time  ,temporal_type ) VALUES (%s "
    ",%s ,%s ,%s ,%s ,%s) ;\\n', ('PERMANENT', "
    "'soil@PERMANENT', 'soil', 'user', "
    "datetime.datetime(2000, 1, 1, 0, 0), 'absolute'))",
    "base.get_update_statement": "('UPDATE raster_base SET  mapset = %s  ,id = %s  ,name "
    "= %s  ,creator = %s  ,creation_time = %s  "
    ",temporal_type = %s WHERE id = %s;\\n', ('PERMANENT', "
    "'soil@PERMANENT', 'soil', 'user', "
    "datetime.datetime(2000, 1, 1, 0, 0), 'absolute', "
    "'soil@PERMANENT'))",
    "base.get_update_all_statement": "('UPDATE raster_base SET  mapset = %s  ,id = %s  "
    ",name = %s  ,creator = %s  ,creation_time = %s  "
    ",temporal_type = %s WHERE id = %s;\\n', "
    "('PERMANENT', 'soil@PERMANENT', 'soil', 'user', "
    "datetime.datetime(2000, 1, 1, 0, 0), 'absolute', "
    "'soil@PERMANENT'))",
    "base.get_select_statement": "('SELECT  mapset  , id  , name  , creator  , "
    "creation_time  , temporal_type  FROM raster_base WHERE "
    "id = %s;\\n', ('soil@PERMANENT',))",
    "base.get_is_in_db_statement": "('SELECT id FROM raster_base WHERE id = %s;\\n', "
    "('soil@PERMANENT',))",
    "base.get_delete_statement": '"DELETE FROM raster_base WHERE id = '
    "'soil@PERMANENT';\\n\"",
    "absolute_time.get_insert_statement": "('INSERT INTO raster_absolute_time ( id  "
    ",start_time  ,end_time ) VALUES (%s ,%s ,%s) "
    ";\\n', ('soil@PERMANENT', "
    "datetime.datetime(2001, 1, 1, 0, 0), "
    "datetime.datetime(2001, 2, 1, 0, 0)))",
    "absolute_time.get_update_statement": "('UPDATE raster_absolute_time SET  id = %s  "
    ",start_time = %s  ,end_time = %s WHERE id = "
    "%s;\\n', ('soil@PERMANENT', "
    "datetime.datetime(2001, 1, 1, 0, 0), "
    "datetime.datetime(2001, 2, 1, 0, 0), "
    "'soil@PERMANENT'))",
    "absolute_time.get_update_all_statement": "('UPDATE raster_absolute_time SET  id = "
    "%s  ,start_time = %s  ,end_time = %s WHERE "
    "id = %s;\\n', ('soil@PERMANENT', "
    "datetime.datetime(2001, 1, 1, 0, 0), "
    "datetime.datetime(2001, 2, 1, 0, 0), "
    "'soil@PERMANENT'))",
    "absolute_time.get_select_statement": "('SELECT  id  , start_time  , end_time  FROM "
    "raster_absolute_time WHERE id = %s;\\n', "
    "('soil@PERMANENT',))",
    "absolute_time.get_is_in_db_statement": "('SELECT id FROM raster_absolute_time WHERE "
    "id = %s;\\n', ('soil@PERMANENT',))",
    "absolute_time.get_delete_statement": '"DELETE FROM raster_absolute_time WHERE id = '
    "'soil@PERMANENT';\\n\"",
    "spatial_extent.get_insert_statement": "('INSERT INTO raster_spatial_extent ( id  "
    ",north  ,south  ,east  ,west  ,top  ,bottom  "
    ",proj ) VALUES (%s ,%s ,%s ,%s ,%s ,%s ,%s "
    ",%s) ;\\n', ('soil@PERMANENT', 2.0, 1.0, 4.0, "
    "3.0, 6.0, 5.0, 'XY'))",
    "spatial_extent.get_update_statement": "('UPDATE raster_spatial_extent SET  id = %s  "
    ",north = %s  ,south = %s  ,east = %s  ,west = "
    "%s  ,top = %s  ,bottom = %s  ,proj = %s WHERE "
    "id = %s;\\n', ('soil@PERMANENT', 2.0, 1.0, "
    "4.0, 3.0, 6.0, 5.0, 'XY', 'soil@PERMANENT'))",
    "spatial_extent.get_update_all_statement": "('UPDATE raster_spatial_extent SET  id = "
    "%s  ,north = %s  ,south = %s  ,east = %s  "
    ",west = %s  ,top = %s  ,bottom = %s  "
    ",proj = %s WHERE id = %s;\\n', "
    "('soil@PERMANENT', 2.0, 1.0, 4.0, 3.0, "
    "6.0, 5.0, 'XY', 'soil@PERMANENT'))",
    "spatial_extent.get_select_statement": "('SELECT  id  , north  , south  , east  , "
    "west  , top  , bottom  , proj  FROM "
    "raster_spatial_extent WHERE id = %s;\\n', "
    "('soil@PERMANENT',))",
    "spatial_extent.get_is_in_db_statement": "('SELECT id FROM raster_spatial_extent "
    "WHERE id = %s;\\n', ('soil@PERMANENT',))",
    "spatial_extent.get_delete_statement": '"DELETE FROM raster_spatial_extent WHERE id = '
    "'soil@PERMANENT';\\n\"",
    "metadata.get_insert_statement": "('INSERT INTO raster_metadata ( id  ,datatype  "
    ",cols  ,rows  ,number_of_cells  ,nsres  ,ewres  "
    ",min  ,max ) VALUES (%s ,%s ,%s ,%s ,%s ,%s ,%s ,%s "
    ",%s) ;\\n', ('soil@PERMANENT', 'CELL', None, None, "
    "None, None, None, 1.0, None))",
    "metadata.get_update_statement": "('UPDATE raster_metadata SET  id = %s  ,datatype = "
    "%s  ,min = %s WHERE id = %s;\\n', "
    "('soil@PERMANENT', 'CELL', 1.0, 'soil@PERMANENT'))",
    "metadata.get_update_all_statement": "('UPDATE raster_metadata SET  id = %s  "
    ",datatype = %s  ,cols = %s  ,rows = %s  "
    ",number_of_cells = %s  ,nsres = %s  ,ewres = "
    "%s  ,min = %s  ,max = %s WHERE id = %s;\\n', "
    "('soil@PERMANENT', 'CELL', None, None, None, "
    "None, None, 1.0, None, 'soil@PERMANENT'))",
    "metadata.get_select_statement": "('SELECT  id  , datatype  , cols  , rows  , "
    "number_of_cells  , nsres  , ewres  , min  , max  "
    "FROM raster_metadata WHERE id = %s;\\n', "
    "('soil@PERMANENT',))",
    "metadata.get_is_in_db_statement": "('SELECT id FROM raster_metadata WHERE id = "
    "%s;\\n', ('soil@PERMANENT',))",
    "metadata.get_delete_statement": '"DELETE FROM raster_metadata WHERE id = '
    "'soil@PERMANENT';\\n\"",
}

# What the SQLite connection writes for a value in mogrify_sql_statement()
LITERALS = [
    "SELECT NULL",
    "SELECT 0",
    "SELECT 7",
    "SELECT -3",
    "SELECT 1",
    "SELECT 2.500000",
    "SELECT 0.000000",
    "SELECT 123456789.123457",
    "SELECT NULL",
    "SELECT NULL",
    "SELECT NULL",
    "SELECT 'soil'",
    "SELECT 'it''s'",
    "SELECT 'a?b'",
    "SELECT '?'",
    "SELECT ''",
    "SELECT 'x''; DROP TABLE t; --'",
    "SELECT '2001-02-03 04:05:06'",
    "SELECT '2001-02-03 04:05:06.000789'",
    "SELECT '2001-02-03'",
]
VALUES = [
    None, 0, 7, -3, True, 2.5, 1e-7, 123456789.123456789, math.nan, math.inf,
    -math.inf, "soil", "it's", "a?b", "?", "", "x'; DROP TABLE t; --",
    datetime.datetime(2001, 2, 3, 4, 5, 6),
    datetime.datetime(2001, 2, 3, 4, 5, 6, 789), datetime.date(2001, 2, 3),
]  # fmt: skip

# The calls a DBConnection makes on a PostgreSQL driver
PG_CALLS = {
    "execute_args": [
        None,
        [
            ("connect", "host=x dbname=y"),
            ("connection.cursor", "DictCursor"),
            ("cursor.execute", "SELECT %s", (1,)),
            ("connection.commit",),
            ("cursor.close",),
            ("connection.close",),
        ],
    ],
    "execute_plain": [
        None,
        [
            ("connect", "host=x dbname=y"),
            ("connection.cursor", "DictCursor"),
            ("cursor.execute", "SELECT 1"),
            ("connection.commit",),
            ("cursor.close",),
            ("connection.close",),
        ],
    ],
    "mogrify_unconnected": [
        "MOGRIFIED",
        [
            ("connect", "host=x dbname=y"),
            ("connection.cursor", "DictCursor"),
            ("cursor.mogrify", "SELECT %s", ("a",)),
            ("connection.commit",),
            ("cursor.close",),
            ("connection.close",),
        ],
    ],
    "mogrify_no_args": ["SELECT 1", []],
    "transaction": [
        None,
        [
            ("connect", "host=x dbname=y"),
            ("connection.cursor", "DictCursor"),
            ("cursor.execute", "INSERT INTO t VALUES (1)"),
            ("connection.commit",),
            ("connection.commit",),
            ("cursor.close",),
            ("connection.close",),
        ],
    ],
    "check_table": [
        True,
        [
            ("connect", "host=x dbname=y"),
            ("connection.cursor", "DictCursor"),
            (
                "cursor.execute",
                "SELECT EXISTS(SELECT * FROM information_schema.tables WHERE "
                "table_name=%s)",
                ("raster_base",),
            ),
            ("cursor.fetchone",),
            ("connection.commit",),
            ("cursor.close",),
            ("connection.close",),
        ],
    ],
    "connected": [
        "MOGRIFIED",
        ("row",),
        [("row",)],
        [
            ("cursor.mogrify", "SELECT %s", ("a",)),
            ("connection.rollback",),
            ("cursor.fetchone",),
            ("cursor.fetchall",),
        ],
    ],
    "close": [("connection.commit",), ("cursor.close",), ("connection.close",)],
}


@pytest.fixture(autouse=True)
def session(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    return temporal_module_session


def db_module():
    """The module that holds DBConnection"""
    return tgis.db


class Cursor:
    def __init__(self, log):
        self.log = log

    def execute(self, *a):
        self.log.append(("cursor.execute", *a))

    def mogrify(self, *a):
        self.log.append(("cursor.mogrify", *a))
        return "MOGRIFIED"

    def fetchone(self):
        self.log.append(("cursor.fetchone",))
        return ("row",)

    def fetchall(self):
        self.log.append(("cursor.fetchall",))
        return [("row",)]

    def close(self):
        self.log.append(("cursor.close",))


class Connection:
    def __init__(self, log):
        self.log = log

    def cursor(self, cursor_factory=None):
        self.log.append(("connection.cursor", cursor_factory))
        return Cursor(self.log)

    def commit(self):
        self.log.append(("connection.commit",))

    def rollback(self):
        self.log.append(("connection.rollback",))

    def close(self):
        self.log.append(("connection.close",))


def fake_pg(log):
    def connect(dbstring):
        log.append(("connect", dbstring))
        return Connection(log)

    return types.SimpleNamespace(
        __name__="psycopg2",
        connect=connect,
        extras=types.SimpleNamespace(DictCursor="DictCursor"),
        paramstyle="pyformat",
    )


def scenario():
    log = []
    conn = db_module().DBConnection(backend="pg", dbstring="host=x dbname=y")
    conn.dbmi = fake_pg(log)
    out = {}

    def step(name, fn):
        log.clear()
        out[name] = [fn()]
        out[name].append(list(log))

    step("execute_args", lambda: conn.execute("SELECT %s", (1,)))
    step("execute_plain", lambda: conn.execute("SELECT 1"))
    step(
        "mogrify_unconnected", lambda: conn.mogrify_sql_statement(["SELECT %s", ("a",)])
    )
    step("mogrify_no_args", lambda: conn.mogrify_sql_statement(["SELECT 1", ()]))
    step("transaction", lambda: conn.execute_transaction("INSERT INTO t VALUES (1)"))
    step("check_table", lambda: conn.check_table("raster_base"))
    conn.connect()
    log.clear()
    out["connected"] = []
    out["connected"].append(conn.mogrify_sql_statement(["SELECT %s", ("a",)]))
    conn.rollback()
    out["connected"].append(conn.fetchone())
    out["connected"].append(conn.fetchall())
    out["connected"].append(list(log))
    log.clear()
    conn.close()
    conn.close()
    out["close"] = list(log)
    return out


def test_pyformat_statements_unchanged(monkeypatch):
    monkeypatch.setattr(rows, "get_tgis_dbmi_paramstyle", lambda: "pyformat")
    ds = tgis.RasterDataset("soil@PERMANENT")
    ds.set_absolute_time(datetime.datetime(2001, 1, 1), datetime.datetime(2001, 2, 1))
    ds.set_spatial_extent_from_values(north=2, south=1, east=4, west=3, top=6, bottom=5)
    ds.base.set_creator("user")
    ds.base.set_ctime(datetime.datetime(2000, 1, 1))
    ds.metadata.set_datatype("CELL")
    ds.metadata.set_min(1)
    ds.metadata.set_max(None)
    actual = {}
    for part in ("base", "absolute_time", "spatial_extent", "metadata"):
        table = getattr(ds, part)
        for name in (
            "get_insert_statement",
            "get_update_statement",
            "get_update_all_statement",
            "get_select_statement",
            "get_is_in_db_statement",
            "get_delete_statement",
        ):
            actual[f"{part}.{name}"] = repr(getattr(table, name)())
    assert actual == PYFORMAT


def test_sqlite_literals_unchanged():
    connection = db_module().DBConnection(backend="sqlite", dbstring=":memory:")
    actual = [connection.mogrify_sql_statement(["SELECT ?", [v]]) for v in VALUES]
    assert actual == LITERALS
    assert (
        connection.mogrify_sql_statement(
            ["INSERT INTO t VALUES (?, ?, ?)", ["a?", None, 4]]
        )
        == "INSERT INTO t VALUES ('a?', NULL, 4)"
    )


def test_postgresql_calls_unchanged():
    assert scenario() == PG_CALLS


@pytest.mark.parametrize(("value", "literal"), list(zip(VALUES, LITERALS, strict=True)))
def test_sql_literal_is_what_mogrify_writes(value, literal):
    from grass.temporal.db import sql_literal  # noqa: PLC0415

    assert literal == f"SELECT {sql_literal(value)}"


def test_sql_literal_needs_a_connection_for_postgresql():
    from grass.temporal.db import sql_literal  # noqa: PLC0415

    with pytest.raises(ValueError, match="pyformat"):
        sql_literal("a", "pyformat")


def test_connection_closes_the_one_it_made():
    from grass.temporal.db import connection  # noqa: PLC0415

    with connection() as dbif:
        assert dbif.is_connected()
    assert not dbif.is_connected()


def test_connection_leaves_a_connected_one_open():
    from grass.temporal.db import connection  # noqa: PLC0415

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        with connection(dbif) as given:
            assert given is dbif
        assert dbif.is_connected()
    finally:
        dbif.close()


def test_connection_connects_and_closes_one_that_was_not_connected():
    from grass.temporal.db import connection  # noqa: PLC0415

    dbif = tgis.SQLDatabaseInterfaceConnection()
    with connection(dbif):
        assert dbif.is_connected()
    assert not dbif.is_connected()


def test_connection_closes_on_a_fatal_error():
    from grass.pygrass.messages import FatalError  # noqa: PLC0415
    from grass.temporal.db import connection  # noqa: PLC0415

    with pytest.raises(FatalError, match="stop"), connection() as dbif:
        tgis.get_tgis_message_interface().fatal("stop")
    assert not dbif.is_connected()


def _boom():
    msg = "boom"
    raise RuntimeError(msg)


def test_connection_leaves_a_connected_one_open_on_an_error():
    from grass.temporal.db import connection  # noqa: PLC0415

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        with pytest.raises(RuntimeError, match="boom"), connection(dbif):
            _boom()
        assert dbif.is_connected()
    finally:
        dbif.close()


def test_add_stds_to_register_works_on_the_connection_it_is_given(monkeypatch):
    # A second connection would not see what the caller has written and not
    # yet committed over the first one.
    opened = []
    connect = tgis.SQLDatabaseInterfaceConnection.connect

    def counting(self, *args, **kwargs):
        opened.append(self)
        return connect(self, *args, **kwargs)

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    monkeypatch.setattr(tgis.SQLDatabaseInterfaceConnection, "connect", counting)
    try:
        tgis.RasterDataset("registering@PERMANENT").add_stds_to_register(
            "some@PERMANENT", dbif=dbif, execute=False
        )
    finally:
        dbif.close()

    assert opened == []
