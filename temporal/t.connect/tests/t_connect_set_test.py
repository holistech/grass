"""Test how t.connect sets the connection: -d, -c, driver and database

Every test has a project of its own, because setting a connection writes the
VAR file of the mapset. The options driver and database have defaults (sqlite
and a file in the tgis directory of the mapset), so a call that gives one of
them sets the other to its default as well; the tests pin that. db.connect
does the same (its options have defaults too), and the manual promises
nothing else, so it is today's behaviour, not a pinned defect.
"""

from pathlib import Path

import pytest

from grass.temporal.testing.readback import message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

DEFAULT_DATABASE = "$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db"


@pytest.fixture
def tools(tmp_path):
    """Tools in a project that has no temporal connection yet"""
    with project_session(tmp_path / "project") as session:
        yield Tools(session=session, consistent_return_value=True, capture_stderr=True)


def _printed(tools):
    """The connection as (driver, database)"""
    result = tools.t_connect(flags="p", format="json", mapset=".")
    (entry,) = result
    return entry["driver"], entry["database"]


def _mapset_dir(tools):
    values = {
        key: tools.g_gisenv(get=key).stdout.strip()
        for key in ("GISDBASE", "LOCATION_NAME", "MAPSET")
    }
    return Path(values["GISDBASE"]) / values["LOCATION_NAME"] / values["MAPSET"]


def _var_file(tools):
    path = _mapset_dir(tools) / "VAR"
    return path.read_text() if path.exists() else ""


def test_a_new_mapset_has_no_connection(tools):
    assert _printed(tools) == (None, None)


def test_c_sets_the_default_connection(tools):
    result = tools.t_connect(flags="c")

    assert "Default TGIS driver / database set to:" in message(result)
    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)
    var = _var_file(tools)
    assert "TGISDB_DRIVER: sqlite" in var
    assert f"TGISDB_DATABASE: {DEFAULT_DATABASE}" in var


def test_c_keeps_a_connection_that_exists(tools):
    tools.t_connect(
        driver="sqlite", database="$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db"
    )

    result = tools.t_connect(flags="c")

    assert message(result) == ""
    assert _printed(tools)[1].endswith("/tgis/mine.db")


@pytest.mark.parametrize(
    ("variable", "missing"),
    [
        ("TGISDB_DRIVER=sqlite", "database"),
        (f"TGISDB_DATABASE={DEFAULT_DATABASE}", "driver"),
    ],
)
def test_c_refuses_a_connection_that_is_half_set(tools, variable, missing):
    # Driver and database must be set together; -c gives up when only one of
    # them is in the VAR file of the mapset and leaves it as it is.
    tools.g_gisenv(set=variable, store="mapset")
    before = _var_file(tools)

    with pytest.raises(ToolError) as error:
        tools.t_connect(flags="c")

    assert f"Default TGIS {missing} is not set" in message(error.value)
    assert _var_file(tools) == before


def test_d_sets_the_default_over_a_connection_that_exists(tools):
    tools.t_connect(
        driver="sqlite", database="$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db"
    )

    result = tools.t_connect(flags="d")

    assert "Default driver / database set to:" in message(result)
    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)


def test_d_wins_over_driver_and_database(tools):
    tools.t_connect(flags="d", driver="pg", database="dbname=x")

    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)


def test_driver_and_database_set_the_connection(tools):
    tools.t_connect(driver="pg", database="dbname=grass host=localhost")

    assert _printed(tools) == ("pg", "dbname=grass host=localhost")
    assert "TGISDB_DRIVER: pg" in _var_file(tools)


def test_a_database_file_of_its_own_is_used(tools):
    # The tools create the file named by the connection: here a dataset is
    # made, and the file that holds it is the one that was set.
    tools.t_connect(
        driver="sqlite", database="$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db"
    )

    tools.t_create(output="in_mine", title="t", description="d")

    tgis = _mapset_dir(tools) / "tgis"
    assert (tgis / "mine.db").exists()
    assert not (tgis / "sqlite.db").exists()


def test_p_does_not_set_the_options_it_is_given(tools):
    tools.t_connect(flags="c")

    result = tools.t_connect(flags="p", driver="pg", database="dbname=x")

    assert result.stdout == f"driver:sqlite\ndatabase:{DEFAULT_DATABASE}\n"
    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)


def test_a_database_alone_sets_the_driver_to_its_default(tools):
    tools.t_connect(driver="pg", database="dbname=x")

    tools.t_connect(database="other.db")

    assert _printed(tools) == ("sqlite", "other.db")


def test_a_driver_alone_sets_the_database_to_its_default(tools):
    tools.t_connect(driver="sqlite", database="other.db")

    tools.t_connect(driver="pg")

    assert _printed(tools) == ("pg", DEFAULT_DATABASE)


def test_no_option_sets_the_defaults(tools):
    tools.t_connect(driver="pg", database="dbname=x")

    tools.t_connect()

    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)


def test_g_is_deprecated(tools):
    tools.t_connect(flags="c")

    result = tools.t_connect(flags="g", verbose=True)

    assert result.stdout == f"driver=sqlite\ndatabase={DEFAULT_DATABASE}\n"
    assert "Flag 'g' is deprecated" in message(result)


def test_an_unknown_driver_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.t_connect(driver="mysql", database="x")

    assert "Value <mysql> out of range for parameter <driver>" in message(error.value)
    assert _printed(tools) == (None, None)


def test_a_database_of_only_spaces_is_refused(tools):
    # The value would be stripped to nothing and the variable removed, which
    # left a driver without a database and an exit code of 0.
    tools.t_connect(flags="c")
    before = _var_file(tools)

    with pytest.raises(ToolError) as error:
        tools.t_connect(database="   ")

    assert "Option <database> must not be empty." in message(error.value)
    assert _var_file(tools) == before
    assert _printed(tools) == ("sqlite", DEFAULT_DATABASE)


def test_a_driver_of_only_spaces_is_refused(tools):
    # The parser already refuses it, because spaces are no driver of the list;
    # the test keeps the connection from changing if that check ever moves.
    tools.t_connect(flags="c")
    before = _var_file(tools)

    with pytest.raises(ToolError) as error:
        tools.t_connect(driver="   ")

    assert "out of range for parameter <driver>" in message(error.value)
    assert _var_file(tools) == before


@pytest.mark.parametrize("flag", ["c", "d"])
def test_p_is_refused_together_with_c_or_d(tools, flag):
    # -p used to win without a word, so the setting the caller asked for with
    # -c or -d was never made.
    tools.t_connect(driver="pg", database="dbname=x")
    before = _var_file(tools)

    with pytest.raises(ToolError) as error:
        tools.t_connect(flags=f"p{flag}")

    assert f"Options <-p> and <-{flag}> are mutually exclusive" in message(error.value)
    assert _var_file(tools) == before


@pytest.mark.parametrize("flag", ["c", "d"])
def test_deprecated_g_is_refused_together_with_c_or_d(tools, flag):
    # -g prints like -p but is turned into a print only after the parser has
    # looked at the flags, so it needs its own exclusion; otherwise it printed
    # and skipped the setting.
    tools.t_connect(driver="pg", database="dbname=x")
    before = _var_file(tools)

    with pytest.raises(ToolError) as error:
        tools.t_connect(flags=f"g{flag}")

    assert f"Options <-g> and <-{flag}> are mutually exclusive" in message(error.value)
    assert _var_file(tools) == before


def test_a_value_longer_than_4096_characters_is_cut(tools):
    # libgis reads a VAR line into a buffer of GPATH_MAX characters, so the
    # tail of a longer value is lost without a message. The current mapset is
    # read by libgis (-p), any mapset named with mapset= by the reader in
    # lib/temporal; both cut at the same place (4094 characters of value,
    # measured 31.10.2026 with values of 4000 to 5000 characters). The test
    # pins what the two readers share, not the exact length.
    value = "a" * 5000

    tools.t_connect(database=value)

    assert len(_var_file(tools).split("TGISDB_DATABASE:")[1].split()[0]) == 5000
    (plain,) = tools.t_connect(flags="p").stdout.splitlines()[1:]
    (_, other) = _printed(tools)
    printed = plain.removeprefix("database:")
    assert printed == other
    assert len(printed) < len(value)
    assert value.startswith(printed)
