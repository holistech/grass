"""Map types in the algebra core: relations, cell offsets and planning

Raster3D and vector series share the operations of raster series; what
differs is the dimension of spatial relations, the cell offsets and the
modules that compute the maps.
"""

import math
import re

import pytest

from grass.temporal.algebra import (
    Call,
    Const,
    MapRef,
    Series,
    Slot,
    Space,
    apply,
    buffer,
    cell_offset,
    equal,
    fold,
    gather,
    pairs,
    plan,
    relation,
    retime,
    select,
)
from grass.temporal.algebra.content import SeriesReduce, series_reduce
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


def test_spatial_raster3d_maps_are_computed_in_the_current_region(make_series):
    a = make_series("a", (1, 2), space=LOW, kind="raster3d")
    b = make_series("b", (1, 2), space=MIDDLE, kind="raster3d")
    series = gather(a, relation("equal", spatial=True), b, reduce=fold("+"))
    [call] = plan(series, "R").processes
    assert call.name == "r3.mapcalc"
    assert "region" not in call.parameters


def test_raster3d_reductions_cannot_skip_null_cells_with_r_series(make_series):
    a = make_series("a", (1, 2), kind="raster3d")
    content = series_reduce("sum", (MapRef("x@m"), MapRef("y@m")))
    series = Series((Slot(a.slots[0].extent, content),), kind="raster3d")
    with pytest.raises(ValueError, match=r"r\.series"):
        plan(series, "R")


A_BOX = Space(10, 0, 10, 0)
B_BOX = Space(15, 5, 15, 5)
FAR_BOX = Space(100, 90, 100, 90)


def _vectors(make_series, name, box):
    return make_series(name, (1, 2), space=box, kind="vector")


@pytest.mark.parametrize(
    ("space", "expected"),
    [
        ("keep", A_BOX),
        ("union", Space(15, 0, 15, 0)),
        ("intersection", Space(10, 5, 10, 5)),
    ],
)
def test_gather_combines_the_spatial_extents(make_series, space, expected):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    result = gather(a, equal, b, reduce=fold("and"), space=space)
    assert result.slots[0].space == expected


def test_an_empty_intersection_keeps_the_extent_of_the_target(make_series):
    a = _vectors(make_series, "a", A_BOX)
    far = _vectors(make_series, "b", FAR_BOX)
    result = gather(a, equal, far, reduce=fold("and"), space="intersection")
    assert result.slots[0].space == A_BOX


def test_pairs_combine_the_spatial_extents(make_series):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    result = pairs(a, equal, b, extent="right", space="union")
    assert result.slots[0].space == Space(15, 0, 15, 0)


def test_unknown_space_mode(make_series):
    a = _vectors(make_series, "a", A_BOX)
    with pytest.raises(ValueError, match="space"):
        gather(a, equal, a, reduce=None, space="both")


def test_buffer_grows_the_spatial_extent_and_builds_the_content(make_series):
    a = make_series(
        "a", (1, 2), space=Space(10, 0, 10, 0, top=1, bottom=0), kind="vector"
    )
    result = buffer(a, 2, features="point")
    slot = result.slots[0]
    assert slot.space == Space(12, -2, 12, -2, top=3, bottom=-2)
    assert slot.content == Call("buff_p", (MapRef("a1@PERMANENT"), Const(2.0)))
    # A buffered map is a new map, not the registered one.
    assert slot.origin is None


def test_a_negative_buffer_keeps_the_spatial_extent(make_series):
    a = _vectors(make_series, "a", A_BOX)
    assert buffer(a, -1).slots[0].space == A_BOX


@pytest.mark.parametrize(
    ("kind", "features", "distance", "error"),
    [
        ("raster", "area", 1, ValueError),
        ("vector", "polygon", 1, ValueError),
        ("vector", "area", "1", TypeError),
        ("vector", "area", True, TypeError),
        # A distance that is not finite would give the maps extents that are
        # not finite either.
        ("vector", "area", math.nan, ValueError),
        ("vector", "area", math.inf, ValueError),
    ],
)
def test_buffer_arguments(make_series, kind, features, distance, error):
    a = make_series("a", (1, 2), space=A_BOX, kind=kind)
    with pytest.raises(error):
        buffer(a, distance, features=features)


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (lambda a, b: a & b, "and"),
        (lambda a, b: a | b, "or"),
        (lambda a, b: a ^ b, "xor"),
        (lambda a, b: a + b, "disor"),
        (lambda a, b: a - b, "not"),
    ],
)
def test_python_operators_on_vector_maps_are_overlays(make_series, operation, expected):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    assert operation(a, b).slots[0].content.function == expected


@pytest.mark.parametrize("function", ["*", ">", "&&", "if", "buff_a"])
def test_other_functions_on_vector_maps(make_series, function):
    a = _vectors(make_series, "a", A_BOX)
    with pytest.raises(ValueError, match="vector"):
        apply(function, a, a)


def test_scalar_values_of_vector_maps_are_numbers(make_series):
    days = make_series("a", (1, 2), values=[3], kind="vector")
    assert (days - 1).slots[0].content == Const(2)


def test_xor_of_raster_maps_is_the_function_of_r_mapcalc(make_series):
    a = make_series("a", (1, 2))
    b = make_series("b", (1, 2))
    assert (a ^ b).slots[0].content.function == "xor"


@pytest.mark.parametrize(
    "operation",
    [
        lambda a, scalar: a + 1,
        lambda a, scalar: 1 - a,
        lambda a, scalar: a + scalar,
        lambda a, scalar: scalar + a,
    ],
)
def test_overlays_combine_vector_maps_only(make_series, operation):
    a = _vectors(make_series, "a", A_BOX)
    scalar = make_series("s", (1, 2), values=[3], kind="vector")
    with pytest.raises(ValueError, match="vector maps only"):
        operation(a, scalar)


def _calls(series, name="R"):
    return [(call.name, call.parameters) for call in plan(series, name).processes]


def test_an_overlay_of_two_vector_maps_is_one_v_overlay(make_series):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    chain = plan(gather(a, equal, b, reduce=fold("and")), "R")
    assert chain.stds_type == "stvds"
    [(name, parameters)] = [(c.name, c.parameters) for c in chain.processes]
    assert name == "v.overlay"
    assert parameters == {
        "ainput": "a1@PERMANENT",
        "binput": "b1@PERMANENT",
        "operator": "and",
        "output": chain.maps[0].name,
    }


def test_a_chain_of_overlays_computes_intermediate_maps(make_series):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    c = _vectors(make_series, "c", B_BOX)
    series = gather(
        gather(a, equal, b, reduce=fold("or")), equal, c, reduce=fold("not")
    )
    chain = plan(series, "R")
    first, second = chain.processes
    assert first.parameters["output"] == second.parameters["ainput"]
    assert first.parameters["output"] in chain.remove
    assert second.parameters["operator"] == "not"


def test_patch_and_buffer_of_vector_maps(make_series):
    a = _vectors(make_series, "a", A_BOX)
    b = _vectors(make_series, "b", B_BOX)
    series = buffer(gather(a, equal, b, reduce=fold("disor")), 2.5, features="line")
    patch, buffered = plan(series, "R").processes
    assert patch.name == "v.patch"
    assert patch.parameters["input"] == "a1@PERMANENT,b1@PERMANENT"
    assert buffered.name == "v.buffer"
    assert buffered.parameters["input"] == patch.parameters["output"]
    assert buffered.parameters["type"] == "line"
    assert buffered.parameters["distance"] == 2.5


def test_an_unchanged_vector_map_is_registered_as_it_is(make_series):
    a = _vectors(make_series, "a", A_BOX)
    chain = plan(a, "R")
    assert chain.maps[0].name == "a1@PERMANENT"
    assert chain.maps[0].calls == ()


def test_a_vector_map_with_a_new_time_stamp_is_copied(make_series):
    a = _vectors(make_series, "a", A_BOX)
    chain = plan(retime(a, shift="1 day"), "R")
    [call] = chain.processes
    assert call.name == "g.copy"
    # pygrass.modules.Module takes the from,to pair of g.copy only as a tuple;
    # a string "from,to" raises TypeError (seen 2026-10-13 with tshift() in
    # the tests of t.vect.algebra).
    assert call.parameters == {"vector": ("a1@PERMANENT", chain.maps[0].name)}


def test_unchanged_raster_maps_are_still_computed(make_series):
    chain = plan(make_series("a", (1, 2)), "R")
    assert [call.name for call in chain.processes] == ["r.mapcalc"]


@pytest.mark.parametrize(
    ("content", "description"),
    [
        (Const(1), "The number 1"),
        (Const(None), "null()"),
        (Call("+", (MapRef("a@m"), MapRef("b@m"))), "The function +()"),
        (MapRef("a@m", (1, 0)), "The map <a@m> at the cell offset (1, 0)"),
        (SeriesReduce("sum", (MapRef("a@m"),)), "The reduction sum of a series"),
    ],
)
def test_vector_maps_cannot_be_numbers_or_raster_expressions(
    make_series, content, description
):
    a = _vectors(make_series, "a", A_BOX)
    series = Series((Slot(a.slots[0].extent, content),), kind="vector")
    # The message names the content in words, not as the repr of a node.
    message = f"{description} cannot be computed as a vector map"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        plan(series, "R")
