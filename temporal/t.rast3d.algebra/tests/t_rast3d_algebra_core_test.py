"""The algebra core on 3D raster maps: reading datasets, planning and
computing

The datasets are described in the series_3d fixture in conftest.py.
"""

import pytest

import grass.temporal as tgis
import grass.temporal.algebra as ta
from grass.exceptions import FatalError
from grass.temporal.algebra.materialize import check_absent


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


def _values(name):
    dataset = tgis.open_old_stds(name, "str3ds")
    rows = []
    for map_ in dataset.get_registered_maps_as_objects(order="start_time"):
        map_.select()
        rows.append((map_.get_id(), map_.metadata.get_min(), map_.metadata.get_max()))
    return rows


def test_materialize_computes_3d_raster_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    b = ta.source("B", stds_type="str3ds")
    ta.materialize(
        ta.gather(a, ta.equal, b, reduce=ta.fold("+")), "core_sum", overwrite=True
    )
    assert [row[1:] for row in _values("core_sum")] == [
        (11 * i, 11 * i) for i in range(1, 5)
    ]


def test_materialize_leaves_out_empty_3d_raster_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    condition = ta.apply(">", a, 2)
    ta.materialize(ta.where(condition, a), "core_where", overwrite=True)
    assert [row[1] for row in _values("core_where")] == [3, 4]


def test_existing_3d_result_without_overwrite(series_3d):
    a = ta.source("A", stds_type="str3ds")
    ta.materialize(a, "core_once", basename="core_once", overwrite=True)
    with pytest.raises(FatalError, match="exists"):
        ta.materialize(a, "core_once", basename="core_once")


def test_check_absent_finds_existing_3d_maps(series_3d):
    a = ta.source("A", stds_type="str3ds")
    ta.materialize(a, "core_maps", basename="core_maps", overwrite=True)
    chain = ta.plan(a, "core_other", basename="core_maps")
    with pytest.raises(FatalError, match="exists"):
        check_absent(chain)
