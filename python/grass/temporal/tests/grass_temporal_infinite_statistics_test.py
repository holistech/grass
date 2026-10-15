# SPDX-License-Identifier: GPL-2.0-or-later
"""Tests for maps whose statistics are infinite or not a number"""

import datetime
import sqlite3

import pytest

import grass.temporal as tgis
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


@pytest.fixture
def session_with_maps(tmp_path):
    """Start a session with a map of finite and a map of infinite values"""
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(session=session)
        tools.g_region(n=80, s=0, e=120, w=0, res=10)
        tools.r_mapcalc(expression="finite = 1.5")
        tools.r_mapcalc(expression="infinite = exp(1000)")
        tgis.init()
        yield session


def _loaded_map(name):
    """Return the map loaded from the project with an absolute time"""
    dataset = tgis.RasterDataset(f"{name}@PERMANENT")
    dataset.load()
    dataset.set_absolute_time(datetime.datetime(2001, 1, 1))
    return dataset


def _database_is_writable():
    """Return True if a second connection can start a write transaction

    A connection that was left open inside a transaction makes this fail
    after the timeout.
    """
    connection = sqlite3.connect(tgis.get_tgis_database_string(), timeout=0.2)
    try:
        connection.isolation_level = None
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("ROLLBACK")
    except sqlite3.OperationalError:
        return False
    finally:
        connection.close()
    return True


def test_map_with_infinite_values_is_registered(session_with_maps):
    """The statistics that are not finite are stored as null"""
    dataset = _loaded_map("infinite")
    assert dataset.metadata.get_max() == float("inf")

    dataset.insert()

    stored = tgis.RasterDataset("infinite@PERMANENT")
    assert stored.is_in_db()
    stored.select()
    assert stored.metadata.get_min() is None
    assert stored.metadata.get_max() is None
    assert _database_is_writable()


def test_map_with_nan_statistics_is_updated(session_with_maps):
    """A not a number statistic is stored as null by update as by insert"""
    dataset = _loaded_map("finite")
    dataset.insert()
    dataset.metadata.set_min(float("nan"))
    dataset.metadata.set_max(2.5)

    dataset.update()

    stored = tgis.RasterDataset("finite@PERMANENT")
    stored.select()
    assert stored.metadata.get_min() is None
    assert stored.metadata.get_max() == 2.5


def test_finite_statistics_are_unchanged(session_with_maps):
    """Finite statistics are stored as they are"""
    dataset = _loaded_map("finite")
    dataset.insert()

    stored = tgis.RasterDataset("finite@PERMANENT")
    stored.select()
    assert stored.metadata.get_min() == 1.5
    assert stored.metadata.get_max() == 1.5


def test_failed_insert_leaves_no_connection_open(session_with_maps):
    """A rejected insert neither leaves the database locked nor half written"""
    dataset = _loaded_map("finite")
    dataset.insert()
    assert _database_is_writable()

    duplicate = _loaded_map("finite")
    duplicate.base.set_creator("someone else")
    with pytest.raises(sqlite3.Error) as failure:
        duplicate.insert()

    # The traceback of the failure keeps the frames and with them a
    # connection that the code did not close alive, as in a long running
    # caller that handles the error; without it the garbage collector closes
    # the connection and hides the lock.
    assert failure.tb is not None
    assert _database_is_writable()
    stored = tgis.RasterDataset("finite@PERMANENT")
    stored.select()
    assert stored.base.get_creator() != "someone else"
