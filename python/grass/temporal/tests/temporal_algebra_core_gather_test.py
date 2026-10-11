"""Tests for gather() and the reducers of the algebra core

A has the daily intervals [1, 2] .. [4, 5] of January 2001, B the
intervals [1, 3] and [3, 5], C the interval [2, 4].
"""

import datetime

import pytest

from grass.temporal.algebra.content import NULL, Call, Const, MapRef, SeriesReduce
from grass.temporal.algebra.operations import gather, select
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import contains, during, equal, relation
from grass.temporal.algebra.series import Series, Space


def day(number):
    return datetime.datetime(2001, 1, number)


def ref(name):
    return MapRef(f"{name}@PERMANENT")


def contents(series):
    return [slot.content for slot in series]


@pytest.fixture
def a(make_series):
    return make_series("a", (1, 2), (2, 3), (3, 4), (4, 5))


@pytest.fixture
def b(make_series):
    return make_series("b", (1, 3), (3, 5))


@pytest.fixture
def c(make_series):
    return make_series("c", (2, 4))


def test_sum_of_related_maps_without_the_target(a, b):
    result = gather(b, contains, a, reduce="sum")
    assert result.times() == b.times()
    assert contents(result) == [
        Call("+", (ref("a1"), ref("a2"))),
        Call("+", (ref("a3"), ref("a4"))),
    ]


def test_fold_starts_with_the_target(a, b):
    assert contents(gather(b, contains, a, reduce=fold("-"))) == [
        Call("-", (Call("-", (ref("b1"), ref("a1"))), ref("a2"))),
        Call("-", (Call("-", (ref("b2"), ref("a3"))), ref("a4"))),
    ]


def test_count_is_a_scalar(a, b):
    result = gather(b, contains, a, reduce="count")
    assert result.sort == "scalar"
    assert contents(result) == [Const(2), Const(2)]


@pytest.mark.parametrize(
    ("reduce", "expected"),
    [
        ("first", ref("a1")),
        ("last", ref("a2")),
        ("prod", Call("*", (ref("a1"), ref("a2")))),
        ("min", Call("min", (ref("a1"), ref("a2")))),
        ("max", Call("max", (ref("a1"), ref("a2")))),
        ("mean", Call("/", (Call("+", (ref("a1"), ref("a2"))), Const(2.0)))),
        ("all", Call("&&", (ref("a1"), ref("a2")))),
        ("any", Call("||", (ref("a1"), ref("a2")))),
        (None, ref("b1")),
    ],
)
def test_reducers_propagating_null(a, b, reduce, expected):
    assert contents(gather(b, contains, a, reduce=reduce))[0] == expected


@pytest.mark.parametrize(
    ("reduce", "expected"),
    [
        ("sum", SeriesReduce("sum", (ref("a1"), ref("a2")))),
        ("mean", SeriesReduce("average", (ref("a1"), ref("a2")))),
        ("min", Call("nmin", (ref("a1"), ref("a2")))),
        ("max", Call("nmax", (ref("a1"), ref("a2")))),
        (
            "all",
            Call(
                "nmin",
                (Call("!=", (ref("a1"), Const(0))), Call("!=", (ref("a2"), Const(0)))),
            ),
        ),
    ],
)
def test_reducers_skipping_null(a, b, reduce, expected):
    result = gather(b, contains, a, reduce=reduce, nulls="skip")
    assert contents(result)[0] == expected


@pytest.mark.parametrize("reduce", [fold("+"), "prod"])
def test_reducers_without_skip_semantics(a, b, reduce):
    with pytest.raises(ValueError, match="null"):
        gather(b, contains, a, reduce=reduce, nulls="skip")


def test_unknown_reducer(a, b):
    with pytest.raises(ValueError, match="Unknown reducer"):
        gather(b, contains, a, reduce="median")


def test_scalar_reduction_in_python(b, make_series):
    s = make_series("s", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, None, 3, 4])
    assert contents(gather(b, contains, s, reduce="sum", nulls="skip")) == [
        Const(1),
        Const(7),
    ]
    assert contents(gather(b, contains, s, reduce="sum")) == [NULL, Const(7)]


@pytest.mark.parametrize(
    ("missing", "expected"),
    [
        ("drop", [ref("c1"), ref("c1")]),
        ("null", [NULL, ref("c1"), ref("c1"), NULL]),
        ("keep", [ref("a1"), ref("c1"), ref("c1"), ref("a4")]),
    ],
)
def test_missing(a, c, missing, expected):
    result = gather(a, during, c, reduce="first", missing=missing)
    assert contents(result) == expected


def test_union_of_target_and_related(a, b):
    result = gather(a, during, b, reduce="first", extent="union")
    assert result.times() == [
        (day(1), day(3)),
        (day(1), day(3)),
        (day(3), day(5)),
        (day(3), day(5)),
    ]


def test_count_law(a, c):
    """count is greater than zero exactly for the slots of select()"""
    counted = gather(a, during, c, reduce="count")
    assert counted.times() == select(a, during, c).times()
    assert all(slot.content.value > 0 for slot in counted)


def test_equal_times_all_and_pairwise(make_series):
    x = make_series("x", (1, 2), (1, 2))
    y = make_series("y", (1, 2), (1, 2))
    assert contents(gather(x, equal, y, reduce="sum")) == [
        Call("+", (ref("y1"), ref("y2"))),
        Call("+", (ref("y1"), ref("y2"))),
    ]
    assert contents(gather(x, equal, y, reduce="sum", equal_times="pairwise")) == [
        ref("y1"),
        ref("y2"),
    ]


def test_pairwise_broadcasts_a_single_map(make_series):
    x = make_series("x", (1, 2), (1, 2))
    z = make_series("z", (1, 2))
    assert contents(gather(x, equal, z, reduce="first", equal_times="pairwise")) == [
        ref("z1"),
        ref("z1"),
    ]


def test_pairwise_rejects_other_counts(make_series):
    x = make_series("x", (1, 2), (1, 2))
    y = make_series("y", (1, 2), (1, 2), (1, 2))
    with pytest.raises(ValueError, match="cannot be paired"):
        gather(x, equal, y, reduce="first", equal_times="pairwise")


def test_pairwise_has_no_effect_with_spatial_relations(make_series):
    space = Space(1, 0, 1, 0)
    x = make_series("x", (1, 2), (1, 2), space=space)
    y = make_series("y", (1, 2), (1, 2), (1, 2), space=space)
    result = gather(
        x, relation("equal", spatial=True), y, reduce="count", equal_times="pairwise"
    )
    assert contents(result) == [Const(3), Const(3)]


def test_gather_of_empty_series(a):
    assert gather(Series(), equal, a, reduce="sum").slots == ()
    assert gather(a, equal, Series(), reduce="sum").slots == ()


def test_pairwise_keeps_the_order_of_maps_of_equal_time(make_series):
    x = make_series("x", (1, 2), (1, 2), (1, 2))
    y = make_series("y", (1, 2), (1, 2), (1, 2))
    result = gather(x, equal, y, reduce=fold("-"), equal_times="pairwise")
    assert contents(result) == [
        Call("-", (ref("x1"), ref("y1"))),
        Call("-", (ref("x2"), ref("y2"))),
        Call("-", (ref("x3"), ref("y3"))),
    ]


@pytest.mark.parametrize(
    "options",
    [
        {"extent": "union"},
        {"equal_times": "pairwise"},
        {"nulls": "skip"},
    ],
)
def test_gather_of_empty_series_with_options(a, options):
    assert gather(Series(), equal, a, reduce="sum", **options).slots == ()
    assert gather(a, equal, Series(), reduce="sum", **options).slots == ()


def test_gather_without_related_slots_keeps_or_nulls_the_target(a):
    nulled = gather(a, equal, Series(), reduce="sum", missing="null")
    assert contents(nulled) == [NULL] * 4
    assert nulled.times() == a.times()
    assert gather(a, equal, Series(), reduce="sum", missing="keep").slots == a.slots
    assert gather(Series(), equal, a, reduce="sum", missing="null").slots == ()


@pytest.mark.parametrize("reduce", ["all", "any"])
@pytest.mark.parametrize("nulls", ["propagate", "skip"])
def test_truth_reducers_of_one_map_are_0_or_1(a, c, reduce, nulls):
    result = gather(a, during, c, reduce=reduce, nulls=nulls, missing="drop")
    one_map = Call("!=", (ref("c1"), Const(0)))
    assert contents(result) == [one_map, one_map]


def test_keep_rejects_count(a, c):
    with pytest.raises(ValueError, match=r"missing=\"keep\".*'count'"):
        gather(a, during, c, reduce="count", missing="keep")


def test_keep_rejects_a_scalar_reduction_of_a_field(a, make_series):
    s = make_series("s", (2, 4), values=[7])
    with pytest.raises(ValueError, match=r"missing=\"keep\".*'first'"):
        gather(a, during, s, reduce="first", missing="keep")


def test_keep_works_with_a_reducer_that_keeps_the_sort(a, c):
    result = gather(a, during, c, reduce="sum", missing="keep")
    assert result.sort == "field"
    assert contents(result) == [ref("a1"), ref("c1"), ref("c1"), ref("a4")]
