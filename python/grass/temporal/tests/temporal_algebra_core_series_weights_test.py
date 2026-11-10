"""Weights of the series_method reducer by the overlap in time

With weights, gather() gives each related map the share of time it has in
common with the target slot: "granule" divides the overlap by the length of
the target, "map" by the length of the map. The SeriesAggregate node carries
one weight per map, and the raster backend writes them into the file of
r.series as name|weight, the form r.series reads.

The weekly maps w1, w2, w3 cover 1 to 8, 8 to 15 and 15 to 22 January 2001;
the granules g1 and g2 cover 1 to 11 and 11 to 21 January.
"""

import re
from pathlib import Path

import pytest

import grass.temporal.algebra as ta
from grass.temporal.algebra import reducers
from grass.temporal.algebra.backends import RasterBackend
from grass.temporal.algebra.content import MapRef, SeriesAggregate
from grass.temporal.algebra.operations import gather
from grass.temporal.algebra.series import Extent

MAIN_C = Path(__file__).resolve().parents[4] / "raster" / "r.series" / "main.c"


def ref(name):
    return MapRef(f"{name}@PERMANENT")


@pytest.fixture
def weekly(make_series):
    return make_series("w", (1, 8), (8, 15), (15, 22))


@pytest.fixture
def granules(make_series):
    return make_series("g", (1, 11), (11, 21))


def test_weighted_methods_match_r_series():
    """The list follows the menu of r.series: a method with a w_* function

    Left out are the weighted forms whose result means nothing: count sums
    the weights instead of counting the maps, the four regression methods add
    the weights to an int in lib/stats/c_reg.c and give null for weights
    below 1, and kurtosis sums the third instead of the fourth power of the
    deviations in lib/stats/c_kurt.c.
    """
    menu = re.findall(
        r'\{c_\w+,\s*(w_\w+|NULL),\s*[^,]+,\s*"(\w+)"', MAIN_C.read_text()
    )
    assert len(menu) == len(reducers.SERIES_METHODS)
    weighted = {name for function, name in menu if function != "NULL"}
    meaningless = {"count", "slope", "offset", "detcoeff", "tvalue", "kurtosis"}
    assert set(reducers.WEIGHTED_SERIES_METHODS) == weighted - meaningless


@pytest.mark.parametrize(
    "method",
    [
        "minimum",
        "maximum",
        "range",
        "min_raster",
        "max_raster",
        "diversity",
        "count",
        "slope",
        "offset",
        "detcoeff",
        "tvalue",
        "kurtosis",
    ],
)
def test_series_method_refuses_weights_for_a_method_without_them(method):
    ta.series_method(method)
    with pytest.raises(ValueError, match=method):
        ta.series_method(method, weights="granule")


def test_series_method_refuses_unknown_weights():
    with pytest.raises(ValueError, match="month"):
        ta.series_method("average", weights="month")


def test_series_method_keeps_the_weights():
    assert ta.series_method("sum", weights="map").weights == "map"
    assert ta.series_method("sum").weights is None


def test_weight_of_touching_extents_is_zero():
    # [1, 8) and [8, 15) share the day 8 only as a border, no time.
    target = Extent(1, 8, "days")
    partner = Extent(8, 15, "days")
    assert reducers.overlap_weights("granule", target, [partner]) == (0.0,)
    assert reducers.overlap_weights("map", target, [partner]) == (0.0,)


def test_granule_weights_divide_by_the_target(granules, weekly):
    # g1 [1, 11): w1 lies inside it with 7 of 10 days, w2 [8, 15) has 3 of
    # them: 0.7 and 0.3. g2 [11, 21): w2 with 4 days, w3 [15, 22) with 6.
    result = gather(
        granules,
        ta.relation("overlaps|overlapped|contains"),
        weekly,
        reduce=ta.series_method("average", weights="granule"),
    )
    assert [slot.content for slot in result] == [
        SeriesAggregate("average", (ref("w1"), ref("w2")), weights=(0.7, 0.3)),
        SeriesAggregate("average", (ref("w2"), ref("w3")), weights=(0.4, 0.6)),
    ]


def test_map_weights_divide_by_the_map(granules, weekly):
    # The same overlaps divided by the 7 days of a map: 7/7 and 3/7, 4/7 and
    # 6/7.
    result = gather(
        granules,
        ta.relation("overlaps|overlapped|contains"),
        weekly,
        reduce=ta.series_method("sum", weights="map"),
    )
    assert [slot.content.weights for slot in result] == [
        (1.0, 3 / 7),
        (4 / 7, 6 / 7),
    ]


def test_relative_weights_come_from_the_numbers(make_series):
    # Relative days: g [0, 10) and the maps [0, 7) and [7, 14): 7 and 3 of
    # 10, 7 of 7 and 3 of 7.
    target = make_series("g", (0, 10), unit="days")
    maps = make_series("w", (0, 7), (7, 14), unit="days")
    related = ta.relation("overlaps|contains")
    by_granule = gather(
        target, related, maps, reduce=ta.series_method("average", weights="granule")
    )
    by_map = gather(
        target, related, maps, reduce=ta.series_method("sum", weights="map")
    )
    assert by_granule.slots[0].content.weights == (0.7, 0.3)
    assert by_map.slots[0].content.weights == (1.0, 3 / 7)


def test_unweighted_aggregate_has_no_weights(granules, weekly):
    result = gather(
        granules,
        ta.relation("overlaps|overlapped|contains"),
        weekly,
        reduce=ta.series_method("sum"),
    )
    assert [slot.content.weights for slot in result] == [None, None]


def test_gather_refuses_an_instant_with_weights(granules, make_series):
    instants = make_series("i", 3)
    with pytest.raises(ValueError, match="instant"):
        gather(
            granules,
            ta.contains,
            instants,
            reduce=ta.series_method("average", weights="granule"),
        )


def test_an_instant_target_is_refused_as_well(make_series, weekly):
    target = make_series("t", 3)
    with pytest.raises(ValueError, match="instant"):
        gather(target, ta.during, weekly, reduce=ta.series_method("sum", weights="map"))


def test_weighted_maps_go_to_r_series_with_their_weights(monkeypatch):
    # One thread and no session file, so -z is not set (see the unweighted
    # tests of series_method).
    monkeypatch.delenv("GISRC", raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    node = SeriesAggregate("sum", (MapRef("a"), MapRef("b")), weights=(1.0, 3 / 7))
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["r.series"]
    # repr() writes the shortest text that reads back as the same double.
    assert calls[0].inputs == ("a|1.0", "b|0.42857142857142855")


def test_a_lone_map_with_a_weight_other_than_one_is_scaled(monkeypatch):
    monkeypatch.delenv("GISRC", raising=False)
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    node = SeriesAggregate("sum", (MapRef("a"),), weights=(3 / 7,))
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["r.series"]
    assert calls[0].inputs == ("a|0.42857142857142855",)


@pytest.mark.parametrize("method", ["average", "stddev", "median"])
def test_a_lone_map_of_another_method_is_copied_whatever_its_weight(method):
    # r.series would compute one weighted map: 7.000000000000001 for an
    # average of 7, about 0 for stddev; the copy keeps the map as it is,
    # as without weights.
    node = SeriesAggregate(method, (MapRef("a"),), weights=(0.3,))
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["g.copy"]


def test_a_lone_map_with_the_weight_one_is_copied():
    node = SeriesAggregate("sum", (MapRef("a"),), weights=(1.0,))
    calls, _ = RasterBackend().plan(node, "out")
    assert [c.name for c in calls] == ["g.copy"]
