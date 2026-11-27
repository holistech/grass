"""Text with quotes and question marks survives mogrify_sql_statement"""

import pytest

import grass.temporal as tgis

TEXTS = ['it\'s ? "quoted"', "?", "''", "a?b?c", "x'; DROP TABLE raster_base; --"]


@pytest.fixture
def dbif(temporal_module_session):
    tgis.init()
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    yield dbif
    dbif.close()


@pytest.mark.parametrize("text", TEXTS)
def test_a_text_is_read_back_as_given(dbif, text):
    statement = dbif.mogrify_sql_statement(["SELECT ?, ?", [text, 7]])

    dbif.execute(statement)
    row = dbif.fetchone()

    assert tuple(row) == (text, 7)


def test_a_question_mark_in_a_value_is_not_a_placeholder(dbif):
    statement = dbif.mogrify_sql_statement(["SELECT ?, ?, ?", ["a?", None, "b"]])

    assert statement == "SELECT 'a?', NULL, 'b'"
