"""Tests for the translation of the algebra syntax onto the core

Each test compares the translation with the core calls of the translation
table, on series built in memory.
"""

import dataclasses
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
        "G": make_series("g", (1, 2), (1, 2)),
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


def test_dataset_functions_name_the_type_in_a_selection(datasets):
    """strds(A) and STVDS(B) read the dataset as one of that type, with the
    spelling of the paper in capitals; a selection relates them"""
    asked = []

    def resolve(name, stds_type=None):
        asked.append((name, stds_type))
        return datasets[name]

    selecting = Translator(resolve=resolve, selection=True)
    result = selecting.statement(parse("R = STRDS(A) {:,during} stvds(B)"))[1]
    assert asked == [("A", "strds"), ("B", "stvds")]
    assert result.slots == operations.select(datasets["A"], during, datasets["B"]).slots
    # A dataset is read once for a type
    selecting.value(parse("R = strds(A) : strds(A)").expression)
    assert asked == [("A", "strds"), ("B", "stvds")]


def test_a_selection_relates_datasets_of_different_types(datasets):
    """The right series gets the map type of the left one; a selection reads
    only its time stamps, so the result is the same without that step"""
    vector = dataclasses.replace(datasets["B"], kind="vector")
    left = datasets["A"]
    assert vector.kind != left.kind
    selecting = Translator(
        resolve=lambda name, stds_type=None: vector if name == "V" else datasets[name],
        selection=True,
    )
    result = selecting.statement(parse("R = A {:,during} V"))[1]
    assert result.slots == operations.select(left, during, datasets["B"]).slots
    plain = Translator(resolve=lambda name: vector if name == "V" else datasets[name])
    assert plain.statement(parse("R = A {:,during} V"))[1].slots == result.slots


@pytest.mark.parametrize("text", ["strds(A, B)", "strds(1)", "STVDS(A + B)"])
def test_dataset_functions_take_one_name(datasets, text):
    selecting = Translator(
        resolve=lambda name, stds_type=None: datasets[name], selection=True
    )
    with pytest.raises(SyntaxError, match="takes the name of a space time dataset"):
        selecting.statement(parse(f"R = {text}"))


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


def test_wrong_number_of_offsets_reads_no_dataset(translator):
    # The resolver of the fixture raises KeyError for a dataset it lacks.
    with pytest.raises(SyntaxError, match="one, two or three offsets"):
        run(translator, "missing[1,2,3,4]")


def test_spatial_relations_work_without_the_spatial_flag(translator, datasets):
    """A spatial name builds the spatial topology also without the flag, as in
    the classic algebra; without a name and without the flag, space is not
    asked"""
    sa, sb = datasets["SA"], datasets["SB"]
    named = Relation(frozenset({"equal"}), frozenset({"equivalent"}))
    result = run(translator, "SA {+,equal|equivalent} SB")
    assert result.slots == operations.gather(sa, named, sb, reduce=fold("+")).slots
    assert result.spatial
    # SC overlaps SA without being equivalent to it
    assert not run(translator, "SA {+,equal|equivalent} SC").slots
    assert not run(translator, "SA + SB").spatial


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


def test_comparisons(translator, datasets):
    a, n = datasets["A"], datasets["N"]
    assert run(translator, "A > 2").slots == operations.apply(">", a, 2).slots
    assert run(translator, "2 < A").slots == operations.apply("<", 2, a).slots
    assert run(translator, "A == N").slots == operations.apply("==", a, n).slots
    with pytest.raises(ValueError, match="equal time stamps"):
        run(translator, "A == B")


def test_comparisons_with_dates_and_times(translator):
    dates = run(translator, 'start_date(A) < "2001-01-03"')
    assert [slot.content for slot in dates] == [Const(1), Const(1), Const(0), Const(0)]
    datetimes = run(translator, 'start_datetime(A) >= "2001-01-02 00:00:00"')
    assert [slot.content for slot in datetimes] == [
        Const(0),
        Const(1),
        Const(1),
        Const(1),
    ]
    times = run(translator, 'start_time(A) == "00:00:00"')
    assert [slot.content for slot in times] == [Const(1)] * 4
    with pytest.raises(TypeError, match="time functions"):
        run(translator, 'A > "2001-01-01"')


def test_text_takes_the_part_the_time_function_gives(translator, datasets):
    """As in the classic algebra, start_time() takes the time of a date
    with time, and the time 00:00 of a date alone"""
    noon = run(translator, 'start_time(A) < "2001-01-01 12:00:00"')
    assert [slot.content for slot in noon] == [Const(1)] * 4
    assert (
        noon.slots
        == operations.apply(
            "<",
            time_functions.timevar(datasets["A"], "start_time"),
            Const(datetime.time(12, 0)),
        ).slots
    )
    midnight = run(translator, 'start_time(A) == "2001-01-01"')
    assert [slot.content for slot in midnight] == [Const(1)] * 4


@pytest.mark.parametrize(
    "text", ['start_time(A) == "no time"', 'start_time(A) == "2001"']
)
def test_text_that_is_no_date_or_time(translator, text):
    """2001 alone is relative time, not a date or the time 20:01"""
    with pytest.raises(ValueError, match=r"is not a date or time"):
        run(translator, text)


@pytest.mark.parametrize("text", ['start_day(A) == "00:00:00"', 'td(A) < "2001-01-01"'])
def test_text_cannot_be_compared_with_numbers(translator, text):
    with pytest.raises(TypeError, match=r"cannot be compared with numbers"):
        run(translator, text)


def test_logical_operators_relate_their_operands(translator, datasets):
    a, b, n = datasets["A"], datasets["B"], datasets["N"]
    left = operations.apply(">", a, 1)
    # N has the time stamps of A, so that the expected series is not empty.
    partners = time_functions.timevar(n, "td")
    expected = operations.apply(
        "&&",
        operations.gather(left, equal, partners, reduce=None),
        operations.gather(left, equal, partners, reduce="all"),
    )
    assert len(expected) == 4
    assert run(translator, "A > 1 && td(N)").slots == expected.slots
    right = time_functions.timevar(b, "td")
    either = operations.apply(
        "||",
        operations.gather(left, during, right, reduce=None),
        operations.gather(left, during, right, reduce="any"),
    )
    assert len(either) == 4
    assert run(translator, "A > 1 {||,during} td(B)").slots == either.slots


def contents(series):
    return [slot.content for slot in series.slots]


def test_comparison_with_a_relation_compares_each_related_map(translator, datasets):
    """B has the maps b1 (1-3) and b2 (3-5); b1 contains a1 and a2, b2 contains
    a3 and a4. Each map is compared with every related map, and the
    comparisons are joined: they are not folded into one another."""
    a, b = contents(datasets["A"]), contents(datasets["B"])
    anywhere = run(translator, "B {>=,contains,|} A")
    assert contents(anywhere) == [
        call("||", call(">=", b[0], a[0]), call(">=", b[0], a[1])),
        call("||", call(">=", b[1], a[2]), call(">=", b[1], a[3])),
    ]
    everywhere = run(translator, "B {<,contains} A")
    assert contents(everywhere) == [
        call("&&", call("<", b[0], a[0]), call("<", b[0], a[1])),
        call("&&", call("<", b[1], a[2]), call("<", b[1], a[3])),
    ]
    assert [slot.extent for slot in everywhere.slots] == [
        slot.extent for slot in datasets["B"].slots
    ]
    assert everywhere.sort == "field"


def test_comparison_with_one_related_map_is_the_comparison(translator, datasets):
    a, n = contents(datasets["A"]), contents(datasets["N"])
    result = run(translator, "A {!=,equal} N")
    assert contents(result) == [call("!=", x, y) for x, y in zip(a, n, strict=True)]


def test_comparison_with_the_right_reference_compares_each_pair(translator, datasets):
    """Every pair takes the time stamp of the right map and is compared alone"""
    a, b = contents(datasets["A"]), contents(datasets["B"])
    result = run(translator, "B {>,contains,&,r} A")
    assert contents(result) == [
        call(">", b[0], a[0]),
        call(">", b[0], a[1]),
        call(">", b[1], a[2]),
        call(">", b[1], a[3]),
    ]
    assert [slot.extent for slot in result.slots] == [
        slot.extent for slot in datasets["A"].slots
    ]


def test_comparison_with_a_relation_needs_two_datasets(translator):
    with pytest.raises(SyntaxError, match="relates two space time datasets"):
        run(translator, "A {>=,equal} 1")


def test_comparison_without_braces_pairs_equal_times(translator, datasets):
    a, n = contents(datasets["A"]), contents(datasets["N"])
    assert contents(run(translator, "A >= N")) == [
        call(">=", x, y) for x, y in zip(a, n, strict=True)
    ]


def test_or_without_braces_joins_with_or(translator, datasets):
    """Two maps of G share the time stamp of the first map of A"""
    left = operations.apply(">", datasets["A"], 1)
    right = operations.apply(">", datasets["G"], 1)
    expected = operations.apply(
        "||",
        operations.gather(left, equal, right, reduce=None),
        operations.gather(left, equal, right, reduce="any"),
    )
    assert len(expected) == 1
    assert run(translator, "A > 1 || G > 1").slots == expected.slots


def test_logical_operator_with_right_reference_pairs(translator, datasets):
    left = operations.apply(">", datasets["A"], 1)
    right = time_functions.timevar(datasets["B"], "td")
    expected = operations.pairs(
        left,
        during,
        right,
        extent="right",
        content=lambda mine, theirs: call("&&", mine, theirs),
    )
    assert run(translator, "A > 1 {&&,during,r} td(B)").slots == expected.slots


def test_precedence_of_conditions(translator):
    """&& binds stronger than ||, and parentheses group conditions"""
    assert len(run(translator, "if(td(A) == 1 || td(A) == 2 && td(A) == 3, A)")) == 4
    assert len(run(translator, "if((td(A) == 1 || td(A) == 2) && td(A) == 3, A)")) == 0


def test_if_with_scalar_condition_chooses_whole_maps(translator, datasets):
    b = datasets["B"]
    assert days(run(translator, "if({during}, start_day(A) > 1, B)")) == [(3, 5)]
    assert days(run(translator, "if({during,&}, start_day(A) > 1, B)")) == [(3, 5)]
    assert days(run(translator, "if({during,|}, start_day(A) > 1, B)")) == [
        (1, 3),
        (3, 5),
    ]
    with_else = run(translator, "if({during}, start_day(A) > 1, B, 0)")
    assert [slot.content for slot in with_else] == [Const(0), b.slots[1].content]


def test_if_with_scalar_condition_takes_then_and_else_independently(translator):
    result = run(translator, "if({equal|contains}, start_day(B) > 2, B, A)")
    assert days(result) == [(1, 2), (2, 3), (3, 5)]
    assert [slot.content for slot in result] == [
        MapRef("a1@PERMANENT"),
        MapRef("a2@PERMANENT"),
        MapRef("b2@PERMANENT"),
    ]


def test_if_takes_else_maps_without_related_condition(translator):
    """Else applies where the condition is false or where no condition is
    related, as in figure A3 of the paper that introduced the algebra; then
    leaves the maps without related condition out"""
    result = run(translator, "if({equal|contains}, start_day(B) > 2, B, D)")
    assert [slot.content for slot in result] == [
        MapRef("b2@PERMANENT"),
        MapRef("d3@PERMANENT"),
    ]
    result = run(translator, "if({equal|contains}, start_day(B) > 2, D, A)")
    assert [slot.content for slot in result] == [
        MapRef("a1@PERMANENT"),
        MapRef("a2@PERMANENT"),
        MapRef("d1@PERMANENT"),
        MapRef("d2@PERMANENT"),
    ]
    result = run(translator, "if({equal|contains}, start_day(B) > 2, 0, D)")
    assert [slot.content for slot in result] == [
        Const(0),
        Const(0),
        MapRef("d3@PERMANENT"),
    ]
    # Without a relation beyond equal the condition speaks of maps of equal
    # time only.
    for text in ("if(start_day(B) > 2, B, D)", "if({equal}, start_day(B) > 2, B, D)"):
        result = run(translator, text)
        assert [slot.content for slot in result] == [MapRef("b2@PERMANENT")]


def test_if_with_map_condition_is_where(translator, datasets):
    a, b = datasets["A"], datasets["B"]
    condition = operations.apply(">", a, 1)
    k = operations.gather(
        b, contains, condition, reduce="all", missing="null", equal_times="pairwise"
    )
    assert (
        run(translator, "if({during}, A > 1, B)").slots == operations.where(k, b).slots
    )
    assert (
        run(translator, "if({during}, A > 1, B, 0)").slots
        == operations.where(k, b, 0).slots
    )


def test_if_with_map_condition_needs_then_and_else_of_equal_time(translator):
    for text in [
        "if(A > 2, A, D)",
        "if({equal|during}, A > 2, B, A)",
        "if(A > 2, if(A > 3, A, N), B)",
    ]:
        with pytest.raises(ValueError, match="equal time stamps"):
            run(translator, text)


def test_if_without_else_gives_zero_for_map_conditions(translator, datasets):
    a = datasets["A"]
    k = operations.gather(
        a,
        equal,
        operations.apply(">", a, 2),
        reduce="all",
        missing="null",
        equal_times="pairwise",
    )
    result = run(translator, "if(A > 2, A)")
    assert result.slots == operations.where(k, a).slots
    assert all(slot.content.args[2] == Const(0) for slot in result)


def test_if_with_numbers_only_takes_the_maps_of_the_condition(translator, datasets):
    a = datasets["A"]
    assert (
        run(translator, "if(A > 1, 5, 0)").slots
        == operations.where(operations.apply(">", a, 1), 5, 0).slots
    )
    chosen = run(translator, "if(td(A) == 1, 5)")
    assert [slot.content for slot in chosen] == [Const(5)] * 4
    with pytest.raises(SyntaxError, match="needs a space time dataset as then or else"):
        run(translator, "if({during}, A > 1, 5)")


def test_if_with_condition_without_time_stamp(translator, datasets):
    a = datasets["A"]
    condition = Series((Slot(None, call(">", MapRef("m@PERMANENT"), Const(1))),))
    assert (
        run(translator, "if(map(m) > 1, A)").slots
        == operations.where(condition, a).slots
    )
    with pytest.raises(SyntaxError, match=r"relation of if\(\) needs a condition"):
        run(translator, "if({during}, map(m) > 1, A)")


def test_if_with_equal_time_conditions_of_different_count(translator):
    """Four maps of one time cannot be paired with two"""
    with pytest.raises(ValueError, match="cannot be paired"):
        run(translator, "if(start_day(F) == 1, E)")


def test_empty_series_pass_through(translator):
    empty = run(translator, "if(td(A) > 5, A)")
    assert len(empty) == 0
    assert len(run(translator, "A + if(td(A) > 5, A)")) == 0
    assert len(run(translator, "if(td(A) > 5, A, N)")) == 4


def test_td_of_an_instant_is_null(translator):
    assert len(run(translator, "if(td(I) > 0, I)")) == 0


@pytest.mark.parametrize(
    ("text", "ident"),
    [
        ("if(start_month(RT) == 1, RT)", "x1@PERMANENT"),
        ('if(start_date(RT) < "2001-01-01", RT)', "x1@PERMANENT"),
        ("RT + start_doy(RT, -1)", "x1@PERMANENT"),
        ("if(end_doy(I) > 1, I)", "i1@PERMANENT"),
        ("I + end_day(I)", "i1@PERMANENT"),
    ],
)
def test_time_variable_that_a_map_lacks_is_an_error(translator, text, ident):
    """The end of an instant and the calendar of relative time do not exist;
    the error names the first map without them"""
    with pytest.raises(ValueError, match=f"<{ident}>"):
        run(translator, text)


def test_time_variables_that_exist_on_instants_and_relative_time(translator):
    assert len(run(translator, "if(start_day(I) > 1, I)")) == 2
    assert len(run(translator, "if(td(RT) == 1, RT)")) == 3


def test_rfc_examples(translator, datasets):
    a, b = datasets["A"], datasets["B"]
    # C = if({contains}, td(B) == 2, A)
    k = operations.gather(
        a,
        during,
        operations.apply("==", time_functions.timevar(b, "td"), 2),
        reduce="all",
        missing="null",
        equal_times="pairwise",
    )
    assert (
        run(translator, "if({contains}, td(B) == 2, A)").slots
        == operations.choose(k, a).slots
    )
    # C = if({during,|}, A > 1 && start_day(A) == 1, B, 0)
    c = run(translator, "A > 1 && start_day(A) == 1")
    k = operations.gather(
        b, contains, c, reduce="any", missing="null", equal_times="pairwise"
    )
    assert (
        run(translator, "if({during,|}, A > 1 && start_day(A) == 1, B, 0)").slots
        == operations.where(k, b, 0).slots
    )
