"""Tests for gather() and the reducers of the algebra core

A has the daily intervals [1, 2] .. [4, 5] of January 2001, B the
intervals [1, 3] and [3, 5], C the interval [2, 4].
"""

import datetime
import re

import pytest

from grass.temporal.algebra import reducers
from grass.temporal.algebra.content import NULL, Call, Const, MapRef, SeriesReduce
from grass.temporal.algebra.materialize import plan
from grass.temporal.algebra.operations import gather, select
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import (
    contains,
    during,
    equal,
    overlaps,
    precedes,
    relation,
)
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
        Call("-", (ref("b1"), ref("a1"), ref("a2"))),
        Call("-", (ref("b2"), ref("a3"), ref("a4"))),
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
        (
            "any",
            Call(
                "nmax",
                (Call("!=", (ref("a1"), Const(0))), Call("!=", (ref("a2"), Const(0)))),
            ),
        ),
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


@pytest.mark.parametrize("nulls", ["propagate", "skip"])
def test_min_over_one_related_map_is_that_map(a, c, nulls):
    result = gather(a, during, c, reduce="min", nulls=nulls)
    assert contents(result) == [ref("c1"), ref("c1")]


def test_mean_over_one_related_map(a, c):
    assert contents(gather(a, during, c, reduce="mean"))[0] == Call(
        "/", (ref("c1"), Const(1.0))
    )
    skipping = gather(a, during, c, reduce="mean", nulls="skip")
    assert contents(skipping)[0] == SeriesReduce("average", (ref("c1"),))


@pytest.mark.parametrize("reduce", [fold("+"), "prod"])
def test_reducers_without_skip_semantics(a, b, reduce):
    with pytest.raises(ValueError, match="null"):
        gather(b, contains, a, reduce=reduce, nulls="skip")


def test_unknown_reducer(a, b):
    with pytest.raises(ValueError, match="Unknown reducer"):
        gather(b, contains, a, reduce="median")


def test_unknown_reducer_names_every_kind_of_reducer(a, b):
    """The reducers that the message names can be imported from
    grass.temporal.algebra"""
    from grass.temporal.algebra import compare, series_method

    assert (compare, series_method) == (reducers.compare, reducers.series_method)
    expected = (
        "Unknown reducer 'nonsense', use one of sum, prod, min, max, mean, "
        "count, all, any, and, or, first, last, fold(operator), "
        "compare(symbol, join), series_method(method) or None"
    )
    with pytest.raises(ValueError, match=f"^{re.escape(expected)}$"):
        gather(b, contains, a, reduce="nonsense")


def test_scalar_reduction_in_python(b, make_series):
    s = make_series("s", (1, 2), (2, 3), (3, 4), (4, 5), values=[1, None, 3, 4])
    assert contents(gather(b, contains, s, reduce="sum", nulls="skip")) == [
        Const(1),
        Const(7),
    ]
    assert contents(gather(b, contains, s, reduce="sum")) == [NULL, Const(7)]


# b1 = [1, 3] contains the first two values and b2 = [3, 5] the last two.
SCALARS = [
    # reduce, values, propagating null, skipping null
    ("sum", [1, None, 3, 4], [None, 7], [1, 7]),
    ("mean", [1, None, 3, 4], [None, 3.5], [1.0, 3.5]),
    ("min", [1, None, 3, 4], [None, 3], [1, 3]),
    ("max", [1, None, 3, 4], [None, 4], [1, 4]),
    ("all", [1, None, 3, 4], [None, 1], [1, 1]),
    ("any", [1, None, 3, 4], [None, 1], [1, 1]),
    ("all", [0, None, 3, 0], [None, 0], [0, 0]),
    ("any", [0, None, 3, 0], [None, 1], [0, 1]),
    ("all", [2, 5, 3, 0], [1, 0], [1, 0]),
    ("any", [0, 0, 0, 0], [0, 0], [0, 0]),
]


@pytest.mark.parametrize(("reduce", "values", "propagate", "skip"), SCALARS)
def test_scalars_are_reduced_in_python(a, b, reduce, values, propagate, skip):
    s = Series(
        tuple(
            slot.__class__(slot.extent, Const(value))
            for slot, value in zip(a.slots, values, strict=True)
        ),
        sort="scalar",
    )
    for nulls, expected in (("propagate", propagate), ("skip", skip)):
        result = gather(b, contains, s, reduce=reduce, nulls=nulls)
        assert result.sort == "scalar"
        assert contents(result) == [Const(value) for value in expected], nulls


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


def test_pairwise_broadcasts_a_single_target_map(make_series):
    x = make_series("x", (1, 2))
    y = make_series("y", (1, 2), (1, 2), (1, 2))
    result = gather(x, equal, y, reduce="sum", equal_times="pairwise")
    assert contents(result) == [Call("+", (ref("y1"), ref("y2"), ref("y3")))]


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


def test_fold_of_a_right_associative_operator_keeps_its_nesting(make_series):
    """r.mapcalc reads a ^ b ^ c as a ^ (b ^ c), but fold is defined from left
    to right"""
    x = make_series("x", (1, 2))
    y = make_series("y", (1, 2), (1, 2))
    (content,) = contents(gather(x, equal, y, reduce=fold("^")))
    assert content == Call("^", (Call("^", (ref("x1"), ref("y1"))), ref("y2")))
    (call,) = plan(gather(x, equal, y, reduce=fold("^")), "R").processes
    assert call.parameters["expression"] == (
        '"R_0"=(("x1@PERMANENT" ^ "y1@PERMANENT") ^ "y2@PERMANENT")'
    )


MANY = 1000
Y = [f'"y{i}@PERMANENT"' for i in range(1, MANY + 1)]


def joined(operator, names):
    return "(" + f" {operator} ".join(names) + ")"


@pytest.mark.parametrize(
    ("reduce", "expected"),
    [
        ("sum", joined("+", Y)),
        ("prod", joined("*", Y)),
        ("mean", f"({joined('+', Y)} / 1000.0)"),
        ("all", joined("&&", Y)),
        ("any", joined("||", Y)),
        ("min", f"min({', '.join(Y)})"),
        (fold("-"), joined("-", ['"x1@PERMANENT"', *Y])),
    ],
)
def test_reducing_many_related_maps_does_not_recurse_deeply(
    make_series, reduce, expected
):
    """A left-deep tree of 1000 maps overflowed the stack in plan(), repr(),
    hash() and ==; one flat call per reduction does not"""
    x = make_series("x", (1, 2))
    y = make_series("y", *[(1, 2)] * MANY)
    result = gather(x, equal, y, reduce=reduce)
    (slot,) = result.slots
    assert slot == gather(x, equal, y, reduce=reduce).slots[0]
    assert isinstance(hash(slot), int)
    assert "y1000@PERMANENT" in repr(slot)
    (call,) = plan(result, "R").processes
    assert call.parameters["expression"] == f'"R_0"={expected}'


def test_extent_of_the_result(make_series):
    """x = [1, 3] overlaps y = [2, 5]"""
    x = make_series("x", (1, 3))
    y = make_series("y", (2, 5))
    times = {
        mode: gather(x, overlaps, y, reduce="first", extent=mode).times()
        for mode in ("left", "union", "intersection", "disjoint")
    }
    assert times == {
        "left": [(day(1), day(3))],
        "union": [(day(1), day(5))],
        "intersection": [(day(2), day(3))],
        "disjoint": [(day(1), day(5))],
    }


def test_gather_keeps_the_left_time_stamp(make_series):
    """The time stamp of the left operand, named as in select() and pairs(),
    is also the default"""
    x = make_series("x", (1, 3))
    y = make_series("y", (2, 5))
    for result in (
        gather(x, overlaps, y, reduce="first", extent="left"),
        gather(x, overlaps, y, reduce="first"),
    ):
        assert result.times() == [(day(1), day(3))]
        assert contents(result) == [ref("y1")]


def test_gather_refuses_target(a, b):
    """The message names the allowed values, and "target" is not taken as
    another name of the left time stamp"""
    with pytest.raises(
        ValueError,
        match=r"^extent must be one of left, union, intersection, disjoint, "
        r"got 'target'$",
    ):
        gather(b, contains, a, reduce="sum", extent="target")


def test_intersection_of_adjacent_maps_is_an_instant(make_series):
    x = make_series("x", (1, 2))
    y = make_series("y", (2, 3))
    result = gather(x, precedes, y, reduce="first", extent="intersection")
    assert result.times() == [(day(2), None)]


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("missing", "ignore"),
        ("missing", None),
        ("extent", "right"),
        ("equal_times", "first"),
        ("nulls", "ignore"),
        ("nulls", True),
    ],
)
def test_invalid_option_values(a, b, option, value):
    with pytest.raises(ValueError, match=option):
        gather(b, contains, a, reduce="sum", **{option: value})


@pytest.mark.parametrize(("reduce", "function"), [("and", "&&"), ("or", "||")])
def test_and_or_join_the_related_contents_as_they_are(a, b, c, reduce, function):
    """Unlike all and any they do not compare a single related content with 0:
    r.mapcalc refuses a floating point map as an operand of && and ||, and the
    classic algebra writes it unchanged"""
    assert contents(gather(a, during, c, reduce=reduce)) == [ref("c1"), ref("c1")]
    assert contents(gather(b, contains, a, reduce=reduce))[0] == Call(
        function, (ref("a1"), ref("a2"))
    )
    assert contents(gather(a, during, c, reduce="all"))[0] == Call(
        "!=", (ref("c1"), Const(0))
    )


@pytest.mark.parametrize("reduce", ["and", "or"])
def test_and_or_cannot_skip_null_cells(a, b, reduce):
    with pytest.raises(ValueError, match="null"):
        gather(b, contains, a, reduce=reduce, nulls="skip")
