"""Tests for the open file rule of r.series

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import sys

import pytest

from grass.temporal import series_limits


def _session(monkeypatch, tmp_path, nprocs=None, omp=None, cpus=24):
    """Let the rule see a session file, OpenMP and usable processors"""
    if nprocs is None:
        monkeypatch.delenv("GISRC", raising=False)
    else:
        rc = tmp_path / "rc"
        rc.write_text(f"NPROCS: {nprocs}\n")
        monkeypatch.setenv("GISRC", str(rc))
    if omp is None:
        monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    else:
        monkeypatch.setenv("OMP_NUM_THREADS", omp)
    monkeypatch.setattr(series_limits, "available_cpus", lambda: cpus)


def _soft_limit(monkeypatch, soft):
    """Let the rule see soft open files"""
    resource = pytest.importorskip("resource")
    monkeypatch.setattr(
        resource, "getrlimit", lambda resource_: (soft, resource.RLIM_INFINITY)
    )
    return resource


@pytest.mark.parametrize(
    ("nprocs", "omp", "expected"),
    [(2, "8", 2), (-20, None, 4), (0, None, 24), (0, "8", 8)],
)
def test_a_passed_nprocs_is_counted_as_r_series_counts_it(
    tmp_path, monkeypatch, nprocs, omp, expected
):
    _session(monkeypatch, tmp_path, nprocs=4, omp=omp)
    assert series_limits.series_threads(nprocs) == expected


# Option values are text, and aggregate_raster_maps() passes nprocs on as
# it gets it.
@pytest.mark.parametrize(
    ("nprocs", "omp", "expected"),
    [("2", "8", 2), ("-20", None, 4), ("0", None, 24), ("0", "8", 8)],
)
def test_a_passed_nprocs_as_text_is_counted_as_a_number(
    tmp_path, monkeypatch, nprocs, omp, expected
):
    _session(monkeypatch, tmp_path, nprocs=4, omp=omp)
    assert series_limits.series_threads(nprocs) == expected


def test_a_passed_nprocs_of_0_ignores_nprocs_of_the_session(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, nprocs=4)
    assert series_limits.series_threads(0) == 24
    assert series_limits.series_threads() == 4


def _project(monkeypatch, tmp_path, rasters):
    """Let the rule see a session in mapset user with NPROCS=4 and rasters

    A raster is given as name@mapset; its cell file is what makes it exist.
    """
    database = tmp_path / "db"
    rc = tmp_path / "rc"
    rc.write_text(f"GISDBASE: {database}\nLOCATION_NAME: xy\nMAPSET: user\nNPROCS: 4\n")
    monkeypatch.setenv("GISRC", str(rc))
    monkeypatch.delenv("GRASS_MASK", raising=False)
    monkeypatch.delenv("OMP_NUM_THREADS", raising=False)
    monkeypatch.setattr(series_limits, "available_cpus", lambda: 24)
    for raster in rasters:
        name, _at, mapset = raster.partition("@")
        cell = database / "xy" / mapset / "cell" / name
        cell.parent.mkdir(parents=True, exist_ok=True)
        cell.touch()


@pytest.mark.parametrize("nprocs", [None, 24, 0, -2])
def test_a_raster_mask_counts_one_thread(tmp_path, monkeypatch, nprocs):
    _project(monkeypatch, tmp_path, ["MASK@user"])
    assert series_limits.series_threads(nprocs) == 1


def test_a_mask_of_another_mapset_is_no_mask(tmp_path, monkeypatch):
    _project(monkeypatch, tmp_path, ["MASK@other", "dem@user"])
    assert series_limits.series_threads() == 4


@pytest.mark.parametrize(
    ("grass_mask", "threads"),
    [
        ("dem", 1),
        ("far@other", 1),
        # A name without mapset is looked up in the current mapset only.
        ("far", 4),
        ("dem@other", 4),
        # GRASS_MASK replaces MASK, which exists here.
        ("missing", 4),
    ],
)
def test_grass_mask_names_the_mask(tmp_path, monkeypatch, grass_mask, threads):
    _project(monkeypatch, tmp_path, ["dem@user", "far@other", "MASK@user"])
    monkeypatch.setenv("GRASS_MASK", grass_mask)
    assert series_limits.series_threads() == threads


def test_an_empty_grass_mask_leaves_mask(tmp_path, monkeypatch):
    _project(monkeypatch, tmp_path, ["MASK@user"])
    monkeypatch.setenv("GRASS_MASK", "")
    assert series_limits.series_threads() == 1


@pytest.mark.parametrize("grass_mask", [".hidden", "sub/dem", "dem@", "dem@user@user"])
def test_a_name_the_c_library_rejects_is_no_mask(tmp_path, monkeypatch, grass_mask):
    _project(monkeypatch, tmp_path, [".hidden@user", "sub/dem@user", "dem@user"])
    monkeypatch.setenv("GRASS_MASK", grass_mask)
    assert series_limits.series_threads() == 4


def test_without_a_session_there_is_no_mask(tmp_path, monkeypatch):
    _project(monkeypatch, tmp_path, ["MASK@user"])
    monkeypatch.delenv("GISRC")
    assert series_limits.series_threads(24) == 24


def test_a_raster_mask_raises_the_real_limit(tmp_path, monkeypatch):
    # On one thread 2 x 480 + 64 files fit into 1024.
    _project(monkeypatch, tmp_path, ["MASK@user"])
    _soft_limit(monkeypatch, 1024)
    assert series_limits.series_map_limit(24) == 480
    assert series_limits.exceeded_series_limit(30, nprocs=24) is None


def test_below_both_limits_nothing_is_exceeded(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, omp="3")
    _soft_limit(monkeypatch, 76)
    assert series_limits.exceeded_series_limit(2, file_limit=1000) is None


def test_the_real_limit_is_exceeded_below_file_limit(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, omp="3")
    _soft_limit(monkeypatch, 75)
    assert series_limits.exceeded_series_limit(2, file_limit=1000) == 1


def test_file_limit_is_exceeded_below_the_real_limit(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, omp="3")
    resource = pytest.importorskip("resource")
    _soft_limit(monkeypatch, resource.RLIM_INFINITY)
    assert series_limits.exceeded_series_limit(2, file_limit=1) == 1
    assert series_limits.exceeded_series_limit(1001, file_limit=1000) == 1000


def test_the_smaller_limit_is_given_when_both_are_exceeded(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, omp="3")
    _soft_limit(monkeypatch, 75)
    assert series_limits.exceeded_series_limit(6, file_limit=5) == 1


def test_a_passed_nprocs_changes_the_real_limit(tmp_path, monkeypatch):
    _session(monkeypatch, tmp_path, nprocs=1, omp="1")
    _soft_limit(monkeypatch, 256)
    assert series_limits.exceeded_series_limit(5) is None
    assert series_limits.exceeded_series_limit(5, nprocs=24) == 4


def test_without_the_resource_module_only_file_limit_counts(monkeypatch):
    monkeypatch.setitem(sys.modules, "resource", None)
    assert series_limits.exceeded_series_limit(5000) is None
    assert series_limits.exceeded_series_limit(1001, file_limit=1000) == 1000


def test_the_warning_keeps_the_text_of_t_rast_aggregate():
    assert series_limits.series_limit_warning(1000, 1001) == (
        "The limit of open files (1000) was reached (1001). The module r.series "
        "will be run with flag z, to avoid open files limit exceeding."
    )
