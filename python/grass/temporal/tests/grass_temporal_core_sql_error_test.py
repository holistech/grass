"""A failed SQL statement of the temporal database raises SQLStatementError"""

import sqlite3

import pytest

import grass.temporal as tgis

BAD = "SELECT * FROM raster_base WHERE ("


@pytest.fixture
def dbif(temporal_module_session):
    tgis.init()
    return tgis.SQLDatabaseInterfaceConnection()


def _message_of_sqlite(statement):
    with pytest.raises(sqlite3.Error) as error:
        sqlite3.connect(":memory:").execute(statement)
    return str(error.value)


def test_execute_raises_the_error_with_the_message_of_sqlite(dbif):
    with pytest.raises(tgis.SQLStatementError) as error:
        dbif.execute(BAD)

    assert str(error.value) == _message_of_sqlite(BAD)
    assert error.value.statement == BAD
    assert isinstance(error.value.__cause__, sqlite3.Error)


def test_execute_transaction_raises_the_same_error(dbif):
    with pytest.raises(tgis.SQLStatementError) as error:
        dbif.execute_transaction(BAD)

    assert error.value.statement == BAD
    assert isinstance(error.value.__cause__, sqlite3.Error)


def test_the_error_is_not_a_database_error():
    # Callers that want the message catch SQLStatementError; the type no
    # longer depends on the database driver.
    assert not issubclass(tgis.SQLStatementError, sqlite3.Error)
    assert issubclass(tgis.SQLStatementError, RuntimeError)


def test_the_connection_is_usable_after_the_error(dbif):
    with pytest.raises(tgis.SQLStatementError):
        dbif.execute(BAD)

    dbif.execute("SELECT 1")
