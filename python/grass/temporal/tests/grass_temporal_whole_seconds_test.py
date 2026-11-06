"""The creation and modification time of a dataset are whole seconds in memory

The temporal database keeps whole seconds (db_datetime()). The setters of
BaseRow cut the microseconds as well, so that a dataset that was just made in
this process shows the same time as the dataset read back from the database.
"""

import re
from datetime import datetime, timedelta, timezone

import pytest

import grass.temporal as tgis
from grass.temporal.base import BaseRow
from grass.temporal.kinds import KINDS
from grass.tools import Tools

WITH_MICROSECONDS = datetime(2020, 1, 1, 6, 30, 1, 999999)
WHOLE = datetime(2020, 1, 1, 6, 30, 1)


def new_base():
    return BaseRow(KINDS["strds"], ident="whole@PERMANENT")


def test_set_ctime_cuts_microseconds():
    base = new_base()

    base.set_ctime(WITH_MICROSECONDS)
    assert base.get_ctime() == WHOLE

    base.set_ctime()
    assert base.get_ctime().microsecond == 0


def test_set_mtime_cuts_microseconds():
    base = new_base()
    assert base.kind.is_stds

    base.set_mtime(WITH_MICROSECONDS)
    assert base.get_mtime() == WHOLE

    base.set_mtime()
    assert base.get_mtime().microsecond == 0


@pytest.mark.parametrize("name", ["ctime", "mtime"])
def test_setters_keep_the_time_zone(name):
    zone = timezone(timedelta(hours=2))
    base = new_base()

    getattr(base, f"set_{name}")(WITH_MICROSECONDS.replace(tzinfo=zone))

    value = getattr(base, f"get_{name}")()
    assert value.tzinfo == zone
    assert value == WHOLE.replace(tzinfo=zone)


@pytest.mark.parametrize("name", ["ctime", "mtime"])
def test_setters_keep_a_value_that_is_not_a_datetime(name):
    # An old SQLite database may hand out the text of a TIMESTAMP column.
    base = new_base()
    setter = getattr(base, f"set_{name}")
    getter = getattr(base, f"get_{name}")

    setter("2020-01-01 06:30:01.071134")
    assert getter() == "2020-01-01 06:30:01.071134"


def test_new_and_registered_dataset_times_equal_the_stored_ones(
    temporal_module_session,
):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=20, s=0, e=20, w=0, res=10)
    tools.r_mapcalc(expression="whole_sec_map = 1")
    mapset = tgis.get_current_mapset()

    stds = tgis.open_new_stds(
        name="whole_sec",
        type="strds",
        temporaltype="absolute",
        title="Test",
        descr="Test",
        semantic="field",
        overwrite=True,
    )
    assert stds.base.get_ctime().microsecond == 0
    assert stds.base.get_mtime().microsecond == 0

    tgis.register_maps_in_space_time_dataset(
        type="raster",
        name="whole_sec",
        maps="whole_sec_map",
        start="2001-01-01",
        end="2001-01-02",
    )
    registered = tgis.open_old_stds(f"whole_sec@{mapset}", "strds")
    registered.select()
    assert registered.base.get_mtime().microsecond == 0

    reread = tgis.open_old_stds(f"whole_sec@{mapset}", "strds")
    reread.select()
    assert reread.base.get_ctime() == stds.base.get_ctime()
    assert reread.base.get_mtime() == registered.base.get_mtime()
    assert reread.base.get_ctime().microsecond == 0


def test_dataset_with_fractional_stored_times_still_reads(temporal_module_session):
    tgis.open_new_stds(
        name="fractional",
        type="strds",
        temporaltype="absolute",
        title="Test",
        descr="Test",
        semantic="field",
        overwrite=True,
    )
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        dbif.execute_transaction(
            "UPDATE strds_base SET creation_time = '2020-01-01 06:30:03.071134', "
            "modification_time = '2020-01-01 06:30:04.071134' "
            "WHERE name = 'fractional';"
        )
    finally:
        dbif.close()

    stds = tgis.open_old_stds(f"fractional@{tgis.get_current_mapset()}", "strds")
    stds.select()
    stds.print_info()
    # select() fills the row directly and bypasses the setters. The reader
    # cuts the stored fraction (measured 2026-11-07 with this test: it returns
    # a datetime in whole seconds), so the value read equals the stored one
    # without its fraction. That value also shows that the UPDATE hit the row:
    # a new dataset would carry the time of the test run.
    assert stds.base.get_ctime() == datetime(2020, 1, 1, 6, 30, 3)
    assert stds.base.get_mtime() == datetime(2020, 1, 1, 6, 30, 4)
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        dbif.execute(
            "SELECT CAST(creation_time AS TEXT) FROM strds_base "
            "WHERE name = 'fractional';"
        )
        assert [tuple(row) for row in dbif.fetchall()] == [
            ("2020-01-01 06:30:03.071134",)
        ]
    finally:
        dbif.close()


def test_t_info_shows_whole_seconds(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=20, s=0, e=20, w=0, res=10)
    tools.r_mapcalc(expression="info_sec_map = 1")
    tools.t_create(type="strds", output="info_sec", title="Test", description="Test")
    tools.t_register(
        type="raster",
        input="info_sec",
        maps="info_sec_map",
        start="2001-01-01",
        end="2001-01-02",
    )

    text = tools.t_info(type="strds", input="info_sec", flags="g").text
    values = {
        key: value.strip("'")
        for key, value in (
            line.split("=", 1) for line in text.splitlines() if "=" in line
        )
    }
    pattern = r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d"
    assert re.fullmatch(pattern, values["creation_time"])
    assert re.fullmatch(pattern, values["modification_time"])
