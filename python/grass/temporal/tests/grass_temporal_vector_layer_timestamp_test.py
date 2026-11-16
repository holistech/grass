# SPDX-License-Identifier: GPL-2.0-or-later

"""The file based timestamp of a vector map belongs to a layer

A vector map has one timestamp file per layer. The test writes two different
timestamps to two layers of one map with v.timestamp and lets VectorDataset
read and remove them, so the layer must reach the C library in each call.
"""

from datetime import datetime

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io

FIRST = datetime(2001, 1, 1)
SECOND = datetime(2005, 5, 5)


@pytest.fixture
def two_layers(tmp_path):
    """A vector map whose layers 1 and 2 carry different timestamps"""
    with temporal_session(tmp_path / "project") as session:
        tgis.init(raise_fatal_error=True)
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=10, s=0, e=10, w=0, res=1)
        tools.v_random(output="vect", npoints=3, seed=1)
        tools.v_timestamp(map="vect", layer="1", date="01 jan 2001")
        tools.v_timestamp(map="vect", layer="2", date="05 may 2005")
        mapset = gs.gisenv(env=session.env)["MAPSET"]
        yield session, mapset, tools


def test_the_timestamp_of_each_layer_is_read(two_layers):
    _, mapset, _ = two_layers
    for layer, expected in (("1", FIRST), ("2", SECOND)):
        vector = tgis.VectorDataset(f"vect:{layer}@{mapset}")

        assert vector.read_timestamp_from_grass() is True
        assert vector.get_absolute_time() == (expected, None)


def test_only_the_timestamp_of_the_layer_is_removed(two_layers):
    _, mapset, tools = two_layers

    assert tgis.VectorDataset(f"vect:2@{mapset}").remove_timestamp_from_grass()

    assert tgis.VectorDataset(f"vect:1@{mapset}").has_grass_timestamp() is True
    assert tgis.VectorDataset(f"vect:2@{mapset}").has_grass_timestamp() is False
