"""Tests for the options of plan() that give the classic rules

The options (the way the r.mapcalc text is written, the list order of the
result maps, the numbering of the copies of a selection, the temporal type
of an empty result, the region of a spatial run) are what a variant of the
algebra that is built on the core needs. Their defaults are the rules of the
core, which the other tests of the plan pin. The options of evaluate() are
tested in temporal_algebra_core_evaluate_options_test.py.

plan() runs nothing, so these tests need no session.
"""

import dataclasses
import datetime

import pytest

from grass.temporal.algebra import (
    MapcalcStyle,
    apply,
    plan,
)
from grass.temporal.algebra.content import Call, Const, MapRef
from grass.temporal.algebra.series import Extent, Series, Slot

BARE = MapcalcStyle(quote_names=False, written_integers=True, bare_comparisons=True)


def expressions(series, **options):
    """The r.mapcalc expression of each planned map"""
    chain = plan(series, "R", **options)
    return [call.parameters["expression"] for call in chain.processes]


def test_the_default_style_is_the_text_of_the_core(make_series):
    series = make_series("a", (1, 2)) > 1
    assert expressions(series, mapcalc=MapcalcStyle()) == expressions(series)
    assert expressions(series) == ['"R_0"=("a1@PERMANENT" > 1)']


def test_names_can_be_written_without_quotes(make_series):
    series = make_series("a", (1, 2), (2, 3)) + 1
    style = MapcalcStyle(quote_names=False)
    assert expressions(series, mapcalc=style) == [
        "R_0=(a1@PERMANENT + 1)",
        "R_1=(a2@PERMANENT + 1)",
    ]


def test_unquoted_names_with_a_cell_offset(make_series):
    series = make_series("a", (1, 2)).slots[0]
    moved = Series(
        (dataclasses.replace(series, content=MapRef(series.origin, (1, 0))),)
    )
    style = MapcalcStyle(quote_names=False)
    assert expressions(moved, mapcalc=style) == ["R_0=a1@PERMANENT[1,0]"]


def test_integers_can_be_written_as_they_are(make_series):
    series = make_series("a", (1, 2)) + 3000000000
    assert expressions(series) == ['"R_0"=("a1@PERMANENT" + 3000000000.0)']
    written = MapcalcStyle(written_integers=True)
    assert expressions(series, mapcalc=written) == [
        '"R_0"=("a1@PERMANENT" + 3000000000)'
    ]


def test_written_integers_keep_floats_and_booleans(make_series):
    style = MapcalcStyle(written_integers=True)
    series = make_series("a", (1, 2))
    assert expressions(series + 2.5, mapcalc=style) == ['"R_0"=("a1@PERMANENT" + 2.5)']
    series = Series(
        (
            Slot(
                series.slots[0].extent, Call("+", (MapRef("a1@PERMANENT"), Const(True)))
            ),
        )
    )
    assert expressions(series, mapcalc=style) == ['"R_0"=("a1@PERMANENT" + 1)']


def test_comparisons_can_be_written_without_parentheses(make_series):
    a, b = make_series("a", (1, 2)), make_series("b", (1, 2))
    style = MapcalcStyle(bare_comparisons=True)
    assert expressions(a == b, mapcalc=style) == [
        '"R_0"="a1@PERMANENT" == "b1@PERMANENT"'
    ]
    # The operands of other operators keep their parentheses.
    assert expressions(apply("&&", a > 1, b < 2), mapcalc=style) == [
        '"R_0"=("a1@PERMANENT" > 1 && "b1@PERMANENT" < 2)'
    ]
    assert expressions((a + 1) > b, mapcalc=style) == [
        '"R_0"=("a1@PERMANENT" + 1) > "b1@PERMANENT"'
    ]


def test_a_comparison_as_an_operand_keeps_its_parentheses(make_series):
    a, b = make_series("a", (1, 2)), make_series("b", (1, 2))
    style = MapcalcStyle(bare_comparisons=True)
    assert expressions((a > 1) + b, mapcalc=style) == [
        '"R_0"=(("a1@PERMANENT" > 1) + "b1@PERMANENT")'
    ]
    assert expressions(apply("==", a > 1, b > 2), mapcalc=style) == [
        '"R_0"=("a1@PERMANENT" > 1) == ("b1@PERMANENT" > 2)'
    ]
    assert expressions(apply("neg", a > 1), mapcalc=style) == [
        '"R_0"=(-("a1@PERMANENT" > 1))'
    ]


def test_a_comparison_in_a_function_or_an_or_is_bare(make_series):
    a, b = make_series("a", (1, 2)), make_series("b", (1, 2))
    style = MapcalcStyle(bare_comparisons=True)
    assert expressions(apply("||", a > 1, b < 2), mapcalc=style) == [
        '"R_0"=("a1@PERMANENT" > 1 || "b1@PERMANENT" < 2)'
    ]
    assert expressions(apply("abs", a > 1), mapcalc=style) == [
        '"R_0"=abs("a1@PERMANENT" > 1)'
    ]


def test_bare_comparisons_leave_other_operators_alone(make_series):
    series = make_series("a", (1, 2)) + 1
    assert expressions(series, mapcalc=MapcalcStyle(bare_comparisons=True)) == (
        expressions(series)
    )


def test_all_three_styles_together(make_series):
    a, b = make_series("a", (1, 2)), make_series("b", (1, 2))
    series = apply("&&", a > 3000000000, b < 2)
    assert expressions(series, mapcalc=BARE) == [
        "R_0=(a1@PERMANENT > 3000000000 && b1@PERMANENT < 2)"
    ]


def region(series, **options):
    return plan(series, "R", **options).processes[0].parameters.get("region")


def test_a_spatial_run_can_always_use_the_union_region(make_series):
    series = make_series("a", (1, 2)) + 1
    assert not series.spatial
    assert region(series) is None
    assert region(series, union_region=True) == "union"


def test_the_union_region_of_a_series_related_in_space_stays(make_series):
    series = dataclasses.replace(make_series("a", (1, 2)) + 1, spatial=True)
    assert region(series) == "union"
    assert region(series, union_region=False) == "union"


def test_3d_raster_maps_have_no_union_region(make_series):
    series = make_series("a", (1, 2), kind="raster3d") + 1
    assert region(series, union_region=True) is None


def ranked(series, ranks):
    """series with the list order given by ranks, one per slot in time order"""
    slots = tuple(
        dataclasses.replace(slot, rank=rank)
        for slot, rank in zip(series.slots, ranks, strict=True)
    )
    return dataclasses.replace(series, slots=slots)


@pytest.fixture
def listed_series(make_series):
    """a1 [1,2], a2 [2,3] and a3 [3,4], listed as a3, a1, a2"""
    return ranked(make_series("a", (1, 2), (2, 3), (3, 4)) * 2, (1, 2, 0))


def test_results_are_numbered_in_time_order_by_default(listed_series):
    chain = plan(listed_series, "R")
    assert [name for name, _, _ in chain.register] == ["R_0", "R_1", "R_2"]
    assert [call.parameters["expression"] for call in chain.processes] == [
        '"R_0"=("a1@PERMANENT" * 2)',
        '"R_1"=("a2@PERMANENT" * 2)',
        '"R_2"=("a3@PERMANENT" * 2)',
    ]


def test_results_can_be_numbered_in_list_order(listed_series):
    chain = plan(listed_series, "R", list_order=True)
    assert [call.parameters["expression"] for call in chain.processes] == [
        '"R_0"=("a3@PERMANENT" * 2)',
        '"R_1"=("a1@PERMANENT" * 2)',
        '"R_2"=("a2@PERMANENT" * 2)',
    ]
    assert [(name, start.day) for name, start, _ in chain.register] == [
        ("R_0", 3),
        ("R_1", 1),
        ("R_2", 2),
    ]


def test_list_order_without_ranks_is_the_time_order(make_series):
    series = make_series("a", (1, 2), (2, 3)) * 2
    assert plan(series, "R", list_order=True) == plan(series, "R")


def test_list_order_applies_to_time_suffixes(listed_series):
    chain = plan(listed_series, "R", list_order=True, time_suffix="time")
    assert [name for name, _, _ in chain.register] == [
        "R_2001_01_03T00_00_00",
        "R_2001_01_01T00_00_00",
        "R_2001_01_02T00_00_00",
    ]


def test_list_order_applies_to_given_names(listed_series):
    chain = plan(listed_series, "R", list_order=True, names=["x", "y", "z"])
    assert [name for name, _, _ in chain.register] == ["x", "y", "z"]
    assert chain.register[0][1].day == 3


@pytest.fixture
def selection():
    """The registered map s1 [1,2] before the retimed maps s2 and s3"""

    def slot(name, start, end, *, registered):
        extent = Extent(
            datetime.datetime(2001, 1, start), datetime.datetime(2001, 1, end)
        )
        ident = f"{name}@PERMANENT"
        return Slot(extent, MapRef(ident), None, ident if registered else None)

    return Series(
        (slot("s1", 1, 2, registered=True), slot("s2", 2, 3, registered=False))
        + (slot("s3", 3, 4, registered=False),)
    )


def copies(chain):
    return [
        call.parameters["raster"][1]
        for call in chain.processes
        if call.name == "g.copy"
    ]


def test_copies_of_a_selection_are_counted_by_default(selection):
    assert copies(plan(selection, "R", selection=True)) == ["R_1", "R_2"]


def test_copies_of_a_selection_can_be_numbered_by_position(selection):
    chain = plan(selection, "R", selection=True, copies_by_position=True)
    assert copies(chain) == ["R_2", "R_3"]


def test_copies_by_position_follow_the_list_order(selection):
    series = ranked(selection, (2, 0, 1))
    chain = plan(series, "R", selection=True, copies_by_position=True, list_order=True)
    # s2 is first in the list, s3 second, s1 (registered) last.
    assert copies(chain) == ["R_1", "R_2"]
    assert [name for name, _, _ in chain.register] == ["R_1", "R_2", "s1@PERMANENT"]


def test_a_result_without_maps_is_absolute_by_default():
    assert plan(Series(), "R").temporal_type == "absolute"
    assert plan(Series(), "R", selection=True).temporal_type == "absolute"


def test_a_result_without_maps_can_take_a_temporal_type():
    assert plan(Series(), "R", temporal_type="relative").temporal_type == "relative"
    chain = plan(Series(), "R", selection=True, temporal_type="relative")
    assert chain.temporal_type == "relative"


def test_the_temporal_type_of_the_maps_wins(make_series):
    series = make_series("a", (1, 2), unit="days") * 2
    assert plan(series, "R", temporal_type="absolute").temporal_type == "relative"
