"""Test temporal relations, temporal operators and selection in t.rast.algebra

The "rel" dataset holds one probe map per temporal relation to the single
reference map "ref1" (value 100, [10, 20] of January 2001). The value of a
probe map is its number, see PROBES in conftest.py. The datasets A, B, C and
D are described in the algebra fixture.
"""

import pytest


def probes(algebra, expression):
    """Return the sorted probe numbers selected by an expression on rel"""
    return sorted(int(value) for value in algebra.values(expression))


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        ("equal", [1]),
        # during includes starts and finishes, contains includes started and
        # finished, see the class documentation of the topology connector
        ("during", [2, 4, 6]),
        ("contains", [3, 5, 7]),
        ("starts", [4]),
        ("started", [5]),
        ("finishes", [6]),
        ("finished", [7]),
        ("precedes", [8]),
        ("follows", [9]),
        ("overlaps", [10]),
        ("overlapped", [11]),
        ("over", [10, 11]),
    ],
)
def test_single_relation_selects_the_probe(algebra, relation, expected):
    """Each relation selects exactly the probe maps with this relation"""
    assert probes(algebra, f"rel {{:,{relation}}} ref") == expected


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        ("precedes|follows", [8, 9]),
        ("equal|during", [1, 2, 4, 6]),
        ("equal | during", [1, 2, 4, 6]),
        ("starts|started|finishes|finished", [4, 5, 6, 7]),
        ("overlaps|overlapped|equal", [1, 10, 11]),
        ("during|contains", [2, 3, 4, 5, 6, 7]),
    ],
)
def test_relations_combined_with_or(algebra, relation, expected):
    """Relations separated by | select the union of the single relations"""
    assert probes(algebra, f"rel {{:,{relation}}} ref") == expected


@pytest.mark.parametrize("relation", ["precedes", "follows", "precedes|follows"])
def test_precedes_and_follows_need_adjacent_maps(algebra, relation):
    """Maps separated from the reference by a gap are neither preceding nor
    following it, the manual draws a gap in its figure"""
    selected = probes(algebra, f"rel {{:,{relation}}} ref")
    assert 12 not in selected
    assert 13 not in selected


def test_equals_is_not_a_relation(algebra):
    """Only equal is a relation; the spelling equals is reported"""
    with pytest.raises(SyntaxError, match="equals"):
        algebra.parse("rel {:,equals} ref")


@pytest.mark.parametrize(
    "expression", ["rel {:,nonsense} ref", "rel {:,equal|nonsense} ref"]
)
def test_unknown_relation_is_an_error(algebra, expression):
    """A misspelled relation must not silently produce nothing"""
    with pytest.raises(SyntaxError, match="nonsense"):
        algebra.parse(expression)


def test_unknown_relation_of_arithmetic_operator_is_an_error(algebra):
    """{+,nonsense} must be reported like the relations of the selection"""
    with pytest.raises(SyntaxError, match="nonsense"):
        algebra.parse("rel {+,nonsense} ref")


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("rel !: ref", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        pytest.param(
            "rel {!:} ref",
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        ),
        ("rel {!:,equal} ref", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        ("rel {!:,equal,l} ref", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]),
        ("rel {!:,during|contains} ref", [1, 8, 9, 10, 11, 12, 13]),
        (
            "rel {!:,overlaps|overlapped|precedes|follows} ref",
            [1, 2, 3, 4, 5, 6, 7, 12, 13],
        ),
    ],
)
def test_not_select_is_the_complement(algebra, expression, expected):
    """!: selects the maps without the given relation, also unrelated ones"""
    assert probes(algebra, expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "rel : ref",
        pytest.param("rel {:} ref"),
        "rel {:,equal} ref",
        "rel {:,equal,l} ref",
    ],
)
def test_default_select_is_equal(algebra, expression):
    """The short forms of the select operator are the same as {:,equal,l}"""
    assert probes(algebra, expression) == [1]


@pytest.mark.parametrize(
    "expression",
    [
        "A : D",
        pytest.param("A {:} D"),
        "A {:,equal} D",
        "A {:,equal,l} D",
    ],
)
def test_select_on_daily_datasets(algebra, expression):
    """a3 and a4 are equal to maps of D and keep their own time stamps"""
    assert algebra.triples(expression) == [(3, 4, 3), (4, 5, 4)]


def test_select_with_itself_and_unrelated(algebra):
    """Selecting with itself keeps all maps, with an unrelated STRDS none"""
    assert algebra.values("A : A") == [1, 2, 3, 4]
    assert algebra.run("A : B") == []


def test_not_select_on_daily_datasets(algebra):
    """!: keeps the maps of A without an equal map in D"""
    assert algebra.triples("A !: D") == [(1, 2, 1), (2, 3, 2)]
    assert algebra.triples("A {!:,during} C") == [(1, 2, 1), (4, 5, 4)]
    assert algebra.run("A {!:,during} B") == []


@pytest.mark.parametrize(
    ("modifier", "expected"),
    [
        ("l", (1, 2)),
        ("left", (1, 2)),
        ("r", (1, 3)),
        ("right", (1, 3)),
        ("i", (1, 2)),
        ("intersect", (1, 2)),
        ("u", (1, 3)),
        ("union", (1, 3)),
        ("d", (1, 3)),
        ("disjoint", (1, 3)),
    ],
)
def test_temporal_operator_words_and_letters(algebra, modifier, expected):
    """a1 [1,2] is during b1 [1,3]; letters and words give the same extent"""
    result = algebra.triples(f"A {{+,during,{modifier}}} B")
    assert (result[0][0], result[0][1]) == expected
    assert [value for _, _, value in result] == [6, 7, 9, 10]


@pytest.mark.parametrize(
    ("relation", "probe", "modifier", "expected"),
    [
        ("overlaps", 10, "l", (5, 15)),
        ("overlaps", 10, "r", (10, 20)),
        ("overlaps", 10, "i", (10, 15)),
        ("overlaps", 10, "u", (5, 20)),
        ("overlaps", 10, "d", (5, 20)),
        ("overlapped", 11, "l", (15, 25)),
        ("overlapped", 11, "r", (10, 20)),
        ("overlapped", 11, "i", (15, 20)),
        ("overlapped", 11, "u", (10, 25)),
        ("overlapped", 11, "d", (10, 25)),
        ("precedes", 8, "l", (5, 10)),
        ("precedes", 8, "r", (10, 20)),
        ("precedes", 8, "u", (5, 20)),
        ("follows", 9, "l", (20, 25)),
        ("follows", 9, "r", (10, 20)),
        ("follows", 9, "u", (10, 25)),
        ("follows", 9, "d", (10, 25)),
        ("during", 2, "l", (12, 18)),
        ("during", 2, "r", (10, 20)),
        ("during", 2, "i", (12, 18)),
        ("during", 2, "u", (10, 20)),
    ],
)
def test_temporal_extent_of_the_result(algebra, relation, probe, modifier, expected):
    """The temporal operator decides the time stamp of the result map"""
    result = algebra.triples(f"rel {{+,{relation},{modifier}}} ref")
    [(start, end, value)] = [row for row in result if row[2] == 100 + probe]
    assert (start, end) == expected
    assert value == 100 + probe


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # a1 and a2 are both in b1, a3 and a4 in b2
        ("A {+,during} B", [6, 7, 9, 10]),
        ("A {-,during} B", [-4, -3, -3, -2]),
        ("A {*,during} B", [5, 10, 18, 24]),
        ("A {/,during} B", [0, 0, 0, 0]),
        ("A {%,during} B", [1, 2, 3, 4]),
        ("float(A) {/,during} B", [0.2, 0.4, 0.5, 4 / 6]),
    ],
)
def test_arithmetic_operators_with_relation(algebra, expression, expected):
    """Every arithmetic operator can carry a topological relation"""
    assert algebra.values(expression) == pytest.approx(expected)


def test_aggregation_is_not_symmetric(algebra):
    """The manual: B {+,contains} A sums all contained maps into one result,
    A {+,during} B keeps one result per contained map"""
    assert algebra.triples("B {+,contains} A") == [(1, 3, 8), (3, 5, 13)]
    assert algebra.triples("A {+,during} B") == [
        (1, 2, 6),
        (2, 3, 7),
        (3, 4, 9),
        (4, 5, 10),
    ]


def test_aggregation_over_several_relations(algebra):
    """Each a<i> is summed with itself (equal), its predecessor (follows) and
    its successor (precedes)"""
    assert algebra.triples("A {+,equal|precedes|follows,l} A") == [
        (1, 2, 4),
        (2, 3, 8),
        (3, 4, 12),
        (4, 5, 11),
    ]


def test_aggregation_of_contained_maps_with_right_reference(algebra):
    """With the right reference the aggregated sum gets the time stamps of A"""
    assert algebra.triples("C {+,contains,r} A") == [(2, 3, 12), (3, 4, 12)]
    assert algebra.triples("C {+,contains,l} A") == [(2, 4, 12)]


def test_relation_with_unrelated_datasets_gives_nothing(algebra):
    """Without any related pair there is no result map"""
    assert algebra.run("A {+,precedes} N") != []
    assert algebra.run("rel {+,equal} A") == []


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("rel {#,during} ref", [1, 1, 1]),
        ("ref {#,contains} rel", [3]),
        ("ref # rel", [1]),
        ("ref {#,equal} rel", [1]),
        ("ref {#,starts} rel", [1]),
        ("ref {#,overlaps} rel", [1]),
        ("B {#,contains} A", [2, 2]),
        ("A {#,during} B", [1, 1, 1, 1]),
        ("C {#,contains} A", [2]),
        ("A # D", [1, 1]),
        ("A {#,equal} A", [1, 1, 1, 1]),
    ],
)
def test_hash_counts_related_maps(algebra, expression, expected):
    """The hash operator returns the number of related maps per map"""
    assert algebra.values(expression) == expected


@pytest.mark.parametrize(
    ("relation", "expected"),
    [("equal|during", 4), ("precedes|follows", 2), ("overlaps|overlapped", 2)],
)
def test_hash_with_several_relations(algebra, relation, expected):
    """ref has one equal map and is during three probes; the count of
    equal|during is the sum"""
    assert algebra.values(f"ref {{#,{relation}}} rel") == [expected]


def test_selection_of_multiply_related_map_appears_once(algebra):
    """A map related to several maps is selected once, not once per partner"""
    assert algebra.triples("ref {:,contains} rel") == [(10, 20, 100)]


def test_select_with_time_extent_of_single_map(algebra):
    """tmap() gives a single raster a time stamp so that it can be related"""
    assert algebra.triples("A {:,equal} tmap(singletmap)") == [(3, 4, 3)]
    assert algebra.triples("D {+,equal,l} tmap(singletmap)") == [(3, 4, 107)]
