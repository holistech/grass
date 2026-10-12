"""Tests for the translation of the algebra syntax onto the core

Each test compares the translation with the core calls of the translation
table, on series built in memory.
"""

import datetime

import pytest

from grass.temporal.algebra import operations, time_functions
from grass.temporal.algebra.content import NULL, Const, MapRef, call
from grass.temporal.algebra.parser.grammar import parse
from grass.temporal.algebra.parser.translate import Translator
from grass.temporal.algebra.reducers import fold
from grass.temporal.algebra.relations import Relation, contains, during, equal
from grass.temporal.algebra.series import Extent, Series, Slot, Space

BOX = Space(north=10, south=0, east=10, west=0)
SHIFTED = Space(north=15, south=5, east=15, west=5)


@pytest.fixture
def datasets(make_series):
    return {
        "A": make_series("a", (1, 2), (2, 3), (3, 4), (4, 5)),
        "N": make_series("n", (1, 2), (2, 3), (3, 4), (4, 5)),
        "B": make_series("b", (1, 3), (3, 5)),
        "C": make_series("c", (2, 4)),
        "D": make_series("d", (3, 4), (4, 5), (5, 6)),
        "I": make_series("i", 1, 2, 3),
        "E": make_series("e", 1, 1, 1, 1),
        "F": make_series("f", 1, 1),
        "RT": make_series("x", (0, 1), (1, 2), (2, 3), unit="days"),
        "SA": make_series("sa", (1, 2), space=BOX),
        "SB": make_series("sb", (1, 2), space=BOX),
        "SC": make_series("sc", (1, 2), space=SHIFTED),
        "td": make_series("td", (1, 2)),
        "A@PERMANENT": make_series("a", (1, 2), (2, 3), (3, 4), (4, 5)),
    }


def map_of(name, *, timestamp=True):
    """map(name) has no time stamp; tmap(name) has [3, 4] of January 2001"""
    ident = f"{name}@PERMANENT"
    if not timestamp:
        return Series((Slot(None, MapRef(ident)),))
    extent = Extent(datetime.datetime(2001, 1, 3), datetime.datetime(2001, 1, 4))
    return Series((Slot(extent, MapRef(ident), None, ident),))


@pytest.fixture
def translator(datasets):
    def make(spatial=False):
        return Translator(
            spatial=spatial, resolve=datasets.__getitem__, resolve_map=map_of
        )

    return make


def run(translator, text, spatial=False):
    """The series of 'R = text'"""
    return translator(spatial).statement(parse(f"R = {text}"))[1]


def value(translator, text):
    """The value of an expression that need not be a series"""
    return translator().value(parse(f"R = {text}").expression)


def days(series):
    return [
        (
            slot.extent.start.day,
            None if slot.extent.end is None else slot.extent.end.day,
        )
        for slot in series
    ]


def test_statement_gives_name_and_series(translator, datasets):
    name, series = translator().statement(parse("R = A"))
    assert name == "R"
    assert series is datasets["A"]


def test_a_dataset_is_read_once(datasets, translator):
    calls = []

    def resolve(name):
        calls.append(name)
        return datasets[name]

    Translator(resolve=resolve).statement(parse("R = A + A * A"))
    assert calls == ["A"]


def test_names_keep_their_mapset_and_may_be_function_names(translator, datasets):
    assert run(translator, "A@PERMANENT") is datasets["A@PERMANENT"]
    assert (
        run(translator, "td + 1").slots
        == operations.apply("+", datasets["td"], 1).slots
    )


def test_constants_fold(translator):
    assert value(translator, "1 + 2 * 3") == Const(7)
    assert value(translator, "-(2)") == Const(-2)
    assert value(translator, "null()") == NULL


def test_expression_without_dataset_is_an_error(translator):
    with pytest.raises(ValueError, match="gives no space time dataset"):
        run(translator, "1 + 2")


@pytest.mark.parametrize("symbol", ["+", "-", "*", "/", "%"])
def test_arithmetic_folds_the_related_maps(translator, datasets, symbol):
    # N has the time stamps of A, so that every map of A has a partner and
    # the comparison cannot pass with two empty series.
    a, n = datasets["A"], datasets["N"]
    expected = operations.gather(a, equal, n, reduce=fold(symbol))
    assert len(expected) == 4
    assert run(translator, f"A {symbol} N").slots == expected.slots


def test_arithmetic_with_numbers_and_maps_without_time(translator, datasets):
    a = datasets["A"]
    assert run(translator, "A * 2").slots == operations.apply("*", a, 2).slots
    assert run(translator, "2 - A").slots == operations.apply("-", 2, a).slots
    assert run(translator, "-A").slots == operations.apply("neg", a).slots
    m = map_of("m", timestamp=False)
    assert run(translator, "A + map(m)").slots == operations.apply("+", a, m).slots


def test_arithmetic_of_maps_without_time_stamp(translator, datasets):
    """map(L) + 1 stays a map without time stamp, as in the SAVI example
    of the paper that introduced the algebra"""
    a = datasets["A"]
    m = map_of("m", timestamp=False)
    shifted = Series((Slot(None, call("+", MapRef("m@PERMANENT"), Const(1))),))
    assert value(translator, "map(m) + 1").slots == shifted.slots
    assert (
        run(translator, "A * (map(m) + 1)").slots
        == operations.apply("*", a, shifted).slots
    )
    with pytest.raises(ValueError, match="needs a series with time stamps"):
        operations.apply("+", m, 1)


@pytest.mark.parametrize(
    ("temporal", "extent"),
    [("l", "target"), ("u", "union"), ("i", "intersection"), ("d", "disjoint")],
)
def test_arithmetic_with_temporal_operator(translator, datasets, temporal, extent):
    b, a = datasets["B"], datasets["A"]
    expected = operations.gather(b, contains, a, reduce=fold("+"), extent=extent)
    assert run(translator, f"B {{+,contains,{temporal}}} A").slots == expected.slots


def test_arithmetic_with_right_reference_pairs(translator, datasets):
    b, a = datasets["B"], datasets["A"]
    expected = operations.pairs(
        b,
        contains,
        a,
        extent="right",
        content=lambda mine, theirs: call("-", mine, theirs),
    )
    assert run(translator, "B {-,contains,r} A").slots == expected.slots


def test_operator_in_braces_needs_two_datasets(translator):
    with pytest.raises(SyntaxError, match="relates two space time datasets"):
        run(translator, "A {+,during} 2")


def test_selection(translator, datasets):
    a, b, n = datasets["A"], datasets["B"], datasets["N"]
    selected = run(translator, "A : N")
    assert len(selected) == 4
    assert selected.slots == operations.select(a, equal, n).slots
    assert (
        run(translator, "A {:,during} B").slots == operations.select(a, during, b).slots
    )
    assert (
        run(translator, "A !: C").slots
        == operations.select(a, equal, datasets["C"], related=False).slots
    )
    assert (
        run(translator, "A {!:,during} C").slots
        == operations.select(a, during, datasets["C"], related=False).slots
    )


def test_selection_with_temporal_operator(translator, datasets):
    b, a = datasets["B"], datasets["A"]
    assert (
        run(translator, "B {:,contains,r} A").slots
        == operations.pairs(b, contains, a, extent="right").slots
    )
    assert (
        run(translator, "B {:,contains,u} A").slots
        == operations.gather(b, contains, a, reduce=None, extent="union").slots
    )


@pytest.mark.parametrize("temporal", ["r", "u", "i", "d"])
def test_inverse_selection_takes_only_l(translator, temporal):
    with pytest.raises(SyntaxError, match="inverse selection"):
        run(translator, f"A {{!:,during,{temporal}}} B")


def test_hash_counts_related_maps(translator, datasets):
    a, n = datasets["A"], datasets["N"]
    counted = run(translator, "A # N")
    assert counted.slots == operations.gather(a, equal, n, reduce="count").slots
    assert [slot.content for slot in counted] == [Const(1)] * 4
    counted = run(translator, "B {#,contains} A")
    assert counted.sort == "scalar"
    assert [slot.content for slot in counted] == [Const(2), Const(2)]


@pytest.mark.parametrize("temporal", ["r", "u", "i", "d"])
def test_hash_takes_only_l(translator, temporal):
    with pytest.raises(SyntaxError, match="hash operator"):
        run(translator, f"B {{#,contains,{temporal}}} A")


def test_cell_functions(translator, datasets):
    a = datasets["A"]
    assert run(translator, "sin(A)").slots == operations.apply("sin", a).slots
    assert (
        run(translator, "float(A) / 2").slots
        == operations.apply("/", operations.apply("float", a), 2).slots
    )
    assert (
        run(translator, "isntnull(A)").slots
        == operations.apply("!", operations.apply("isnull", a)).slots
    )
    assert run(translator, "exist(A)") is a


@pytest.mark.parametrize("text", ["foo(A)", "strds(A)", "min(A, N)", "foo(missing)"])
def test_unknown_functions(translator, text):
    with pytest.raises(SyntaxError, match="Unknown function"):
        run(translator, text)


def test_time_functions(translator, datasets):
    a, i = datasets["A"], datasets["I"]
    assert run(translator, "td(A)").slots == time_functions.timevar(a, "td").slots
    assert (
        run(translator, "start_doy(A, -1)").slots
        == time_functions.neighbour(time_functions.timevar(a, "start_doy"), -1).slots
    )
    assert (
        run(translator, 'tshift(A, "1 day")').slots
        == time_functions.retime(a, shift="1 day").slots
    )
    assert (
        run(translator, 'buff_t(A, "2 days")').slots
        == time_functions.retime(a, buffer="2 days").slots
    )
    assert (
        run(translator, "tsnap(I)").slots == time_functions.retime(i, snap=True).slots
    )
    rt = datasets["RT"]
    assert (
        run(translator, "tshift(RT, -1)").slots
        == time_functions.retime(rt, shift=-1).slots
    )


def test_increment_is_text_or_whole_number(translator):
    with pytest.raises(SyntaxError, match="increment"):
        run(translator, "tshift(A, 1.5)")


def test_merge_and_single_maps(translator, datasets):
    a, c = datasets["A"], datasets["C"]
    assert run(translator, "merge(A, C)").slots == operations.merge(a, c).slots
    assert run(translator, "tmap(event)").slots == map_of("event").slots
    with pytest.raises(SyntaxError, match="the name of one map"):
        run(translator, "tmap(A + 1)")


def test_indices(translator, datasets):
    a = datasets["A"]
    assert run(translator, "A[1]").slots == time_functions.neighbour(a, 1).slots
    assert run(translator, "A[1,0]").slots == operations.cell_offset(a, 1, 0).slots
    assert (
        run(translator, "A[1,0,-1]").slots
        == operations.cell_offset(time_functions.neighbour(a, -1), 1, 0).slots
    )
    with pytest.raises(SyntaxError, match="one, two or three offsets"):
        run(translator, "A[1,2,3,4]")


def test_spatial_relations_need_the_spatial_flag(translator):
    with pytest.raises(ValueError, match="need the spatial flag"):
        run(translator, "SA {+,equal|equivalent} SB")


def test_spatial_flag_adds_space_to_every_relation(translator, datasets):
    sa, sb = datasets["SA"], datasets["SB"]
    anywhere = Relation(frozenset({"equal"}), frozenset())
    # Both datasets share one region, so the slots alone cannot tell whether
    # space took part in the relation; the spatial attribute can.
    assert not run(translator, "SA + SB").spatial
    summed = run(translator, "SA + SB", spatial=True)
    assert summed.spatial
    assert summed.slots == operations.gather(sa, anywhere, sb, reduce=fold("+")).slots
    # SC overlaps SA in space without being equivalent to it, so the spatial
    # name decides whether the pair is related.
    sc = datasets["SC"]
    named = Relation(frozenset({"equal"}), frozenset({"overlap"}))
    overlapping = run(translator, "SA {+,equal|overlap} SC", spatial=True)
    assert len(overlapping) == 1
    assert overlapping.slots == operations.gather(sa, named, sc, reduce=fold("+")).slots
    assert not run(translator, "SA {+,equal|equivalent} SC", spatial=True).slots
