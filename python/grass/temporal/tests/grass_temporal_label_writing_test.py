"""Tests that opening a dataset for writing refuses a semantic label

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.exceptions import FatalError
import grass.temporal as tgis
from grass.temporal.testing.data import insert_old_stds
from grass.temporal.testing.session import temporal_session


@pytest.fixture
def project_session(tmp_path):
    with temporal_session(tmp_path / "project") as session:
        yield session


@pytest.mark.parametrize("stds_type", ["raster", "rast", "strds"])
def test_open_for_writing_refuses_a_label(project_session, stds_type):
    tgis.open_new_stds("test", "strds", "absolute", "t", "d", "mean")

    with pytest.raises(FatalError, match="selects maps by the semantic label <S2_1>"):
        tgis.open_old_stds("test.S2_1", stds_type, for_writing=True)
    with pytest.raises(FatalError, match="semantic label <S2_1>"):
        tgis.open_old_stds("test.S2_1@PERMANENT", stds_type, for_writing=True)

    # Without the keyword the label still selects maps, as before.
    sp = tgis.open_old_stds("test.S2_1", stds_type)
    assert sp.get_id() == "test@PERMANENT"
    assert sp.semantic_label == "S2_1"
    # The name without a label opens for writing.
    sp = tgis.open_old_stds("test", stds_type, for_writing=True)
    assert sp.get_id() == "test@PERMANENT"


@pytest.mark.parametrize("stds_type", ["raster", "rast", "strds"])
def test_open_for_writing_takes_a_dotted_old_name(project_session, stds_type):
    """A dataset of an older release with a dot in its name is no label"""
    insert_old_stds("a.b")

    sp = tgis.open_old_stds("a.b", stds_type, for_writing=True)

    assert sp.get_id() == "a.b@PERMANENT"
    assert sp.semantic_label is None


def test_open_for_writing_refuses_a_label_after_a_dotted_name(project_session):
    """With the dataset a.b and the dataset a, the name a.b selects a.b"""
    insert_old_stds("a.b")
    tgis.open_new_stds("a", "strds", "absolute", "t", "d", "mean")

    assert tgis.open_old_stds("a.b", "strds", for_writing=True).get_id() == (
        "a.b@PERMANENT"
    )
    with pytest.raises(FatalError, match="semantic label <c>"):
        tgis.open_old_stds("a.c", "strds", for_writing=True)
