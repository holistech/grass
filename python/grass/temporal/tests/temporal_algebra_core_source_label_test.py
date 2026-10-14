"""Tests for source() with the semantic label of a raster dataset.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

from grass.exceptions import FatalError
import grass.script as gs
import grass.temporal as tgis
from grass.temporal.algebra.sources import source
from grass.tools import Tools


@pytest.fixture(scope="module")
def labeled_session(tmp_path_factory):
    """STRDS "test" with an S2_8 and an S2_4 map in each of two months."""
    tmp_path = tmp_path_factory.mktemp("source_label")
    project = tmp_path / "project"
    gs.create_project(project)
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        # tgis reads the session from os.environ.
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tools = Tools(session=session, overwrite=True)
        tools.g_gisenv(set="TGIS_USE_CURRENT_MAPSET=1")
        tools.g_region(s=0, n=20, w=0, e=20, res=10)
        rows = []
        for name, label, start in [
            ("b8_1", "S2_8", "2001-01-01"),
            ("b4_1", "S2_4", "2001-01-01"),
            ("b8_2", "S2_8", "2001-02-01"),
            ("b4_2", "S2_4", "2001-02-01"),
        ]:
            tools.r_mapcalc(expression=f"{name} = 1")
            rows.append(f"{name}|{start}|{label}")
        maps_file = tmp_path / "maps.txt"
        maps_file.write_text("\n".join(rows) + "\n", encoding="utf-8")
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="test",
            title="A test",
            description="A test",
        )
        tools.t_register(type="raster", input="test", file=str(maps_file))
        tgis.init(raise_fatal_error=True)
        yield session


def map_names(series):
    return sorted(slot.origin.split("@")[0] for slot in series.slots)


@pytest.mark.parametrize("name", ["test.S2_8", "test.S2_8@PERMANENT"])
def test_label_keeps_only_its_maps(labeled_session, name):
    assert map_names(source(name)) == ["b8_1", "b8_2"]


def test_without_label_all_maps(labeled_session):
    assert map_names(source("test")) == ["b4_1", "b4_2", "b8_1", "b8_2"]


def test_missing_dataset_with_label(labeled_session):
    with pytest.raises(FatalError):
        source("nothere.S2_8")
