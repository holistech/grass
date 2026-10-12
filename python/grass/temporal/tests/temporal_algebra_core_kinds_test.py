"""Map types in the algebra core: relations, cell offsets and planning

Raster3D and vector series share the operations of raster series; what
differs is the dimension of spatial relations, the cell offsets and the
modules that compute the maps.
"""

import pytest

from grass.temporal.algebra import (
    MapRef,
    Series,
    Slot,
    Space,
    cell_offset,
    equal,
    fold,
    gather,
    plan,
    relation,
    select,
)
from grass.temporal.algebra.content import series_reduce
from grass.temporal.algebra.maptypes import DIMENSIONS, STDS_TYPES

LOW = Space(10, 0, 10, 0, top=10, bottom=0)
HIGH = Space(10, 0, 10, 0, top=30, bottom=20)
MIDDLE = Space(10, 0, 10, 0, top=15, bottom=5)


def test_every_map_type_has_a_dataset_type_and_a_dimension():
    assert STDS_TYPES == {"raster": "strds", "raster3d": "str3ds", "vector": "stvds"}
    assert set(DIMENSIONS) == set(STDS_TYPES)


def test_raster3d_maps_apart_in_height_are_not_related_in_space(make_series):
    low = make_series("a", (1, 2), space=LOW, kind="raster3d")
    high = make_series("b", (1, 2), space=HIGH, kind="raster3d")
    assert len(select(low, relation("equal", spatial=True), high)) == 0


def test_raster3d_maps_overlapping_in_height_are_related(make_series):
    low = make_series("a", (1, 2), space=LOW, kind="raster3d")
    middle = make_series("b", (1, 2), space=MIDDLE, kind="raster3d")
    assert len(select(low, relation("equal", spatial=True), middle)) == 1


def test_raster_maps_ignore_height(make_series):
    low = make_series("a", (1, 2), space=LOW)
    high = make_series("b", (1, 2), space=HIGH)
    assert len(select(low, relation("equal", spatial=True), high)) == 1


def test_temporal_relations_need_no_dimension(make_series):
    a = make_series("a", (1, 2), kind="vector")
    b = make_series("b", (1, 2), kind="vector")
    assert len(select(a, equal, b)) == 1


@pytest.mark.parametrize(
    ("kind", "offsets"),
    [("raster", (1, 0)), ("raster3d", (1, 0, -1))],
)
def test_cell_offset_takes_one_offset_per_axis(make_series, kind, offsets):
    series = cell_offset(make_series("a", (1, 2), kind=kind), *offsets)
    assert series.slots[0].content.offset == offsets


@pytest.mark.parametrize(
    ("kind", "offsets"),
    [
        ("raster", (1, 0, 0)),
        ("raster", (1,)),
        ("raster3d", (1, 0)),
        ("vector", (1, 0)),
    ],
)
def test_cell_offset_with_the_wrong_number_of_offsets(make_series, kind, offsets):
    with pytest.raises(ValueError, match="offset"):
        cell_offset(make_series("a", (1, 2), kind=kind), *offsets)


def test_raster3d_maps_are_computed_with_r3_mapcalc(make_series):
    a = make_series("a", (1, 2), kind="raster3d")
    b = make_series("b", (1, 2), kind="raster3d")
    chain = plan(gather(a, equal, b, reduce=fold("+")), "R")
    assert chain.stds_type == "str3ds"
    [call] = chain.processes
    assert call.name == "r3.mapcalc"
    assert call.parameters["expression"] == '"R_0"=("a1@PERMANENT" + "b1@PERMANENT")'


def test_raster3d_cell_offsets_reach_r3_mapcalc(make_series):
    a = cell_offset(make_series("a", (1, 2), kind="raster3d"), 1, 0, -1)
    [call] = plan(a, "R").processes
    assert call.parameters["expression"] == '"R_0"="a1@PERMANENT"[1,0,-1]'


def test_spatial_raster3d_maps_cannot_use_the_union_of_regions(make_series):
    a = make_series("a", (1, 2), space=LOW, kind="raster3d")
    b = make_series("b", (1, 2), space=MIDDLE, kind="raster3d")
    series = gather(a, relation("equal", spatial=True), b, reduce=fold("+"))
    with pytest.raises(ValueError, match="region=union"):
        plan(series, "R")


def test_raster3d_reductions_cannot_skip_null_cells_with_r_series(make_series):
    a = make_series("a", (1, 2), kind="raster3d")
    content = series_reduce("sum", (MapRef("x@m"), MapRef("y@m")))
    series = Series((Slot(a.slots[0].extent, content),), kind="raster3d")
    with pytest.raises(ValueError, match=r"r\.series"):
        plan(series, "R")
