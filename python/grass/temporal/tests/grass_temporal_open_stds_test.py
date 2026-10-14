"""Tests for the parsing of dataset names in open_stds.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

from grass.exceptions import FatalError
import grass.script as gs
import grass.temporal as tgis
from grass.temporal.open_stds import _parse_id
from grass.tools import Tools


def test_label_is_split_for_strds():
    assert _parse_id("test.S2_8@m", stds_type="strds") == ("test", "m", "S2_8")


@pytest.mark.parametrize(
    "stds_type", ["raster", "rast", "str3ds", "raster3d", "stvds", "vector"]
)
def test_other_types_keep_the_dot(stds_type):
    assert _parse_id("test.S2_8", stds_type=stds_type) == ("test.S2_8", None, None)


@pytest.fixture
def project_session(tmp_path, monkeypatch):
    project = tmp_path / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        # tgis reads the session from os.environ.
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        Tools(session=session).g_gisenv(set="TGIS_USE_CURRENT_MAPSET=1")
        tgis.init(raise_fatal_error=True)
        yield session


def test_new_dataset_with_dot_keeps_its_name(project_session):
    """A dot in the name of a new raster dataset is not a label."""
    sp = tgis.open_new_stds("a.b", "raster", "absolute", "t", "d", "mean")
    assert sp.get_id() == f"a.b@{sp.get_mapset()}"


@pytest.mark.parametrize("stds_type", ["strds", "raster", "rast"])
def test_old_raster_dataset_is_opened_with_its_label(project_session, stds_type):
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")
    sp = tgis.open_old_stds("test.S2_8", stds_type)
    assert sp.get_name() == "test.S2_8"
    assert sp.get_name(semantic_label=False) == "test"


def test_new_raster_dataset_with_dot_cannot_be_read_again(project_session):
    """A dot in the name of an existing raster dataset is read as a label.

    open_new_stds() keeps "a.b" whole, but open_old_stds() reads it as the
    dataset "a" with the semantic label "b", as it always did for "strds".
    A dataset created with a dot (e.g. as output of t.rast.mapcalc) is
    therefore not found again under the type "raster".
    """
    tgis.open_new_stds("a.b", "raster", "absolute", "t", "d", "mean")
    with pytest.raises(FatalError):
        tgis.open_old_stds("a.b", "raster")
