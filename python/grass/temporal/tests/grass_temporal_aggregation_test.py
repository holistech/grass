"""Tests for aggregate_raster_maps() and the open files of r.series

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.temporal import aggregation, series_limits
from grass.tools import Tools

resource = pytest.importorskip("resource")

MAPS = 20


class _Messages:
    """Stands in for the message interface and records the warnings"""

    def __init__(self):
        self.warnings = []

    def warning(self, text):
        self.warnings.append(text)

    def verbose(self, text):
        pass


class _NewMap:
    """Stands in for the raster map the function registers, as an existing one"""

    def __init__(self, map_id):
        self.metadata = self
        self.map_id = map_id

    def is_in_db(self, dbif):
        return False

    def load(self):
        pass

    def get_min(self):
        return 1


@pytest.fixture
def recorded(monkeypatch, tmp_path):
    """Run aggregate_raster_maps() without r.series and note what it was given"""
    messages = _Messages()
    calls = []
    monkeypatch.setattr(aggregation, "get_tgis_message_interface", lambda: messages)
    monkeypatch.setattr(aggregation, "get_current_mapset", lambda: "PERMANENT")
    monkeypatch.setattr(aggregation, "RasterDataset", _NewMap)
    monkeypatch.setattr(
        aggregation.gs, "tempfile", lambda create: str(tmp_path / "names")
    )
    monkeypatch.setattr(
        aggregation.gs, "run_command", lambda *args, **kwargs: calls.append(kwargs)
    )

    def aggregate(count, nprocs=0):
        names = [f"m{number}" for number in range(count)]
        aggregation.aggregate_raster_maps(
            names, "agg", None, None, 1, "sum", True, None, nprocs=nprocs
        )
        return calls[-1]

    aggregate.messages = messages
    return aggregate


def _limits(monkeypatch, tmp_path, soft, nprocs_of_session=None):
    """Let the rule see a soft limit, 24 processors and NPROCS of the session"""
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    if nprocs_of_session is None:
        monkeypatch.delenv("GISRC", raising=False)
    else:
        rc = tmp_path / "rc"
        rc.write_text(f"NPROCS: {nprocs_of_session}\n")
        monkeypatch.setenv("GISRC", str(rc))
    monkeypatch.setattr(series_limits, "available_cpus", lambda: 24)
    monkeypatch.setattr(
        resource, "getrlimit", lambda resource_: (soft, resource.RLIM_INFINITY)
    )


def test_aggregate_raster_maps_counts_the_passed_nprocs(
    recorded, monkeypatch, tmp_path
):
    """nprocs=0 asks OpenMP for 24 threads whatever NPROCS of the session is,
    so 5 maps need 2 x 24 x 5 + 64 = 304 files, more than the 256 allowed"""
    _limits(monkeypatch, tmp_path, 256, nprocs_of_session=4)
    call = recorded(5, nprocs=0)
    assert call["flags"] == "z"
    assert len(recorded.messages.warnings) == 1


def test_aggregate_raster_maps_keeps_its_maps_open_within_both_limits(
    recorded, monkeypatch, tmp_path
):
    _limits(monkeypatch, tmp_path, 256, nprocs_of_session=4)
    call = recorded(2, nprocs=0)
    assert not call.get("flags")
    assert recorded.messages.warnings == []


def test_aggregate_raster_maps_warns_past_1000_maps(recorded, monkeypatch):
    monkeypatch.setattr(resource, "getrlimit", lambda r: (resource.RLIM_INFINITY,) * 2)
    call = recorded(1001)
    assert call["flags"] == "z"
    assert len(recorded.messages.warnings) == 1
    assert "(1000) was reached (1001)" in recorded.messages.warnings[0]


@pytest.fixture(scope="module")
def session(temporal_module_session):
    grass_session = temporal_module_session
    tools = Tools(session=grass_session, overwrite=True)
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for number in range(1, MAPS + 1):
        tools.r_mapcalc(expression=f"n{number} = {number}")
    return grass_session, tools


@pytest.fixture
def few_open_files():
    """Lower the soft limit of open files of this process to 256

    The children that run the modules inherit it.
    """
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, hard))
    yield
    resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def test_aggregate_raster_maps_past_the_open_files_runs_and_sums(
    session, few_open_files, monkeypatch
):
    """20 maps on 8 threads need 2 x 8 x 20 + 64 = 384 files, more than the 256
    allowed; with -z r.series runs and gives the sum 1 + 2 + ... + 20"""
    grass_session, tools = session
    monkeypatch.setenv("OMP_NUM_THREADS", "8")
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        new_map = tgis.aggregate_raster_maps(
            [f"n{number}" for number in range(1, MAPS + 1)],
            "opensum",
            datetime.datetime(2001, 1, 1),
            datetime.datetime(2001, 1, 2),
            1,
            "sum",
            True,
            dbif,
            nprocs=8,
        )
    finally:
        dbif.close()
    assert new_map is not None
    assert float(tools.r_univar(map="opensum_1", flags="g").keyval["min"]) == 210.0
