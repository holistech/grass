"""The algebra core on 3D raster maps: reading datasets, planning and
computing

The datasets are described in the series_3d fixture in conftest.py.
"""

import pytest

import grass.temporal.algebra as ta
from grass.exceptions import FatalError


def test_source_reads_a_space_time_3d_raster_dataset(series_3d):
    series = ta.source("A", stds_type="str3ds")
    assert series.kind == "raster3d"
    assert [slot.origin for slot in series] == [f"a{i}@PERMANENT" for i in range(1, 5)]


def test_source_map_reads_a_3d_raster_map(series_3d):
    series = ta.source_map("single", kind="raster3d")
    assert series.kind == "raster3d"
    assert series.slots[0].extent is not None
    timeless = ta.source_map("single", timestamp=False, kind="raster3d")
    assert timeless.timeless


def test_source_does_not_read_a_dataset_of_another_type(series_3d):
    with pytest.raises(FatalError, match="not found"):
        ta.source("A", stds_type="strds")
