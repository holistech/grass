"""Tests for the rules of plan() that the other tests of the plan leave out

The r.mapcalc text, the region of a spatial run, the order and numbering of
the result maps, the numbering of the copies of a selection, the temporal
type of an empty result and the refusal of equal names.

plan() runs nothing, so these tests need no session.
"""

import dataclasses
import datetime

import pytest

from grass.temporal.algebra import plan
from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.series import Extent, Series, Slot


def expressions(series, **options):
    """The r.mapcalc expression of each planned map"""
    chain = plan(series, "R", **options)
    return [call.parameters["expression"] for call in chain.processes]


def test_the_default_style_is_the_text_of_the_core(make_series):
    series = make_series("a", (1, 2)) > 1
    assert expressions(series) == ['"R_0"=("a1@PERMANENT" > 1)']


def region(series, **options):
    return plan(series, "R", **options).processes[0].parameters.get("region")


def test_a_run_without_spatial_relation_has_no_region(make_series):
    series = make_series("a", (1, 2)) + 1
    assert not series.spatial
    assert region(series) is None


def test_the_union_region_of_a_series_related_in_space_stays(make_series):
    series = dataclasses.replace(make_series("a", (1, 2)) + 1, spatial=True)
    assert region(series) == "union"


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


def test_a_result_without_maps_is_absolute_by_default():
    assert plan(Series(), "R").temporal_type == "absolute"
    assert plan(Series(), "R", selection=True).temporal_type == "absolute"


def test_the_temporal_type_of_the_maps_wins(make_series):
    series = make_series("a", (1, 2), unit="days") * 2
    assert plan(series, "R").temporal_type == "relative"


def test_equal_names_from_a_time_suffix_are_an_error_by_default(make_series):
    series = make_series("a", (1, 2), (1, 3)) + 1
    with pytest.raises(ValueError, match="same name"):
        plan(series, "R", time_suffix="time")


def test_names_given_by_the_caller_may_not_repeat(make_series):
    series = make_series("a", (1, 2), (2, 3))
    with pytest.raises(ValueError, match="same name"):
        plan(series, "R", names=["x", "x"])
