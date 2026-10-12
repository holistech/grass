"""The algebra core on vector maps: reading datasets, planning and
computing

The datasets are described in the vector_series fixture in conftest.py.
"""

import pytest

import grass.temporal.algebra as ta
from grass.exceptions import FatalError


def test_source_reads_a_space_time_vector_dataset(vector_series):
    series = ta.source("aa", stds_type="stvds")
    assert series.kind == "vector"
    assert [slot.origin for slot in series] == [f"aa{i}@PERMANENT" for i in range(1, 4)]
    # Vector maps have a spatial extent, which spatial relations need.
    assert series.slots[0].space.east == pytest.approx(10)


def test_source_map_reads_a_vector_map(vector_series):
    series = ta.source_map("ev", kind="vector")
    assert series.kind == "vector"
    assert series.slots[0].origin == "ev@PERMANENT"


def test_missing_vector_map(vector_series):
    with pytest.raises(FatalError, match="not found"):
        ta.source_map("missing", kind="vector")


def test_unknown_dataset_type(vector_series):
    with pytest.raises(ValueError, match="stds_type"):
        ta.source("aa", stds_type="vector")
