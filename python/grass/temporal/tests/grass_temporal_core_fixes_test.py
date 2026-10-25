"""Regression tests for faults of the infrastructure in grass.temporal.core"""

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal import core

pytestmark = pytest.mark.real_io


def _unset(*names):
    """Remove variables from the gisenv; g.gisenv fails on one that is not set"""
    environment = gs.gisenv()
    for name in names:
        if name in environment:
            gs.run_command("g.gisenv", unset=name)


@pytest.fixture
def warnings_of_init(temporal_module_session, monkeypatch):
    """Record what init() warns about through the messenger of the process

    The messenger server writes to the stderr of its own process, which a
    test cannot capture reliably, so the calls are recorded instead.
    """
    tgis.init(skip_db_init=True)
    recorded = []
    monkeypatch.setattr(
        core.get_tgis_message_interface(), "warning", recorded.append, raising=False
    )
    yield recorded
    _unset("TGIS_DISABLE_MAPSET_CHECK", "TGIS_DISABLE_TIMESTAMP_WRITE")
    tgis.init(skip_db_init=True)


@pytest.mark.parametrize("value", ["True", "1"])
@pytest.mark.parametrize(
    ("name", "getter"),
    [
        ("TGIS_DISABLE_MAPSET_CHECK", tgis.get_enable_mapset_check),
        ("TGIS_DISABLE_TIMESTAMP_WRITE", tgis.get_enable_timestamp_write),
    ],
)
def test_disable_switch_takes_effect(warnings_of_init, name, getter, value):
    gs.run_command("g.gisenv", set=f"{name}={value}")

    tgis.init(skip_db_init=True)

    assert getter() is False
    assert warnings_of_init == [f"{name} is True"]


def test_second_init_without_the_variable_resets_the_switches(warnings_of_init):
    gs.run_command("g.gisenv", set="TGIS_DISABLE_MAPSET_CHECK=True")
    gs.run_command("g.gisenv", set="TGIS_DISABLE_TIMESTAMP_WRITE=1")
    tgis.init(skip_db_init=True)
    assert tgis.get_enable_mapset_check() is False

    _unset("TGIS_DISABLE_MAPSET_CHECK", "TGIS_DISABLE_TIMESTAMP_WRITE")
    tgis.init(skip_db_init=True)

    assert tgis.get_enable_mapset_check() is True
    assert tgis.get_enable_timestamp_write() is True


def test_other_values_leave_the_switches_on(warnings_of_init):
    gs.run_command("g.gisenv", set="TGIS_DISABLE_MAPSET_CHECK=False")

    tgis.init(skip_db_init=True)

    assert tgis.get_enable_mapset_check() is True
    assert warnings_of_init == []
