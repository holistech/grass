"""Test conditional statements (if, else) of t.rast.algebra

The datasets are described in the algebra fixture in conftest.py. Map a<i>
of dataset A has the value i and the interval [i, i + 1] of January 2001.
The 2001-01-01 was a Monday.
"""

import pytest


def a_intervals(values):
    """Return the expected maps of dataset A with the given values"""
    return [(number, number + 1, value) for number, value in enumerate(values, 1)]


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        # the two-argument if of r.mapcalc gives 0 where the condition is false
        ("if(A > 2, A)", [0, 0, 3, 4]),
        ("if(A > 2, A, 0)", [0, 0, 3, 4]),
        ("if(A > 2, A, A * 10)", [10, 20, 3, 4]),
        ("if(A > 2, 1, 0)", [0, 0, 1, 1]),
        ("if(A > 2, 7)", [0, 0, 7, 7]),
        ("if(A == 2, A + N, A - N)", [-10, 14, -10, -10]),
        ("if(A != 2, A)", [1, 0, 3, 4]),
        ("if(A >= 3, A)", [0, 0, 3, 4]),
        ("if(A <= 2, A)", [1, 2, 0, 0]),
        ("if(A < 2, A)", [1, 0, 0, 0]),
        ("if(A > 1 && A < 4, A)", [0, 2, 3, 0]),
        ("if(A > 3 || A < 2, A)", [1, 0, 0, 4]),
        ("if(A == 2 || A == 3, A, 0)", [0, 2, 3, 0]),
        ("if(A > 100, A)", [0, 0, 0, 0]),
    ],
)
def test_raster_value_conditions(algebra, expression, values):
    """Conditions on the cell values decide per cell which branch is used"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("if(isnull(A), 1, 0)", [0, 0, 0, 0]),
        ("if(isntnull(A), A)", [1, 2, 3, 4]),
        ("if(exist(A), A)", [1, 2, 3, 4]),
    ],
)
def test_isnull_isntnull_exist(algebra, expression, values):
    """isnull(), isntnull() and exist() can be used in conditions"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # maps that are null everywhere are not registered without -n
        ("if(A > 2, A, null())", [(3, 4, 3), (4, 5, 4)]),
        ("if(A > 2, null(), A)", [(1, 2, 1), (2, 3, 2)]),
        ("if(A > 2, null(), 0)", [(1, 2, 0), (2, 3, 0)]),
        ("if(A > 2, 5, null())", [(3, 4, 5), (4, 5, 5)]),
        ("if(A > 2, null())", [(1, 2, 0), (2, 3, 0)]),
    ],
)
def test_null_in_conditions(algebra, expression, expected):
    """null() sets cells to NULL; maps without any valid cell are dropped"""
    assert algebra.triples(expression) == expected


def test_else_branch_with_other_dataset(algebra):
    """The else branch may be another STRDS with equal time stamps"""
    assert algebra.values("if(A > 2, A, N)") == [11, 12, 3, 4]


def test_else_branch_without_related_dataset_gives_nothing(algebra):
    """The manual: if, then and else are equal in time; B is not equal to A"""
    assert algebra.run("if(A > 2, A, B)") == []


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("if({equal}, A > 2, A)", [0, 0, 3, 4]),
        ("if({equal}, A > 2, A, A * 10)", [10, 20, 3, 4]),
        ("if({equal}, A > 2, A + N, A)", [1, 2, 16, 18]),
    ],
)
def test_if_with_explicit_equal_relation(algebra, expression, values):
    """{equal} between condition and conclusion is the default"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        # B contains A: b1 contains a1 and a2, b2 contains a3 and a4
        ("if({contains}, B > 5, A)", [0, 0, 3, 4]),
        ("if({contains}, B > 5, A, A * 10)", [10, 20, 3, 4]),
        ("if({during}, td(B) == 2, A)", [1, 2, 3, 4]),
    ],
)
def test_if_with_other_topology_between_condition_and_conclusion(
    algebra, expression, values
):
    """The relation in braces connects the condition STRDS with the conclusion"""
    assert algebra.triples(expression) == a_intervals(values)


@pytest.mark.parametrize(
    "expression",
    ["if({during}, B > 5, A)", "if({equal}, B > 5, A)", "if({contains}, A > 2, B)"],
)
def test_if_without_matching_relation_gives_nothing(algebra, expression):
    """Without a map in the requested relation nothing is concluded"""
    assert algebra.run(expression) == []


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("if(td(A) == 1, A)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ("if(td(A) != 1, A)", []),
        ("if(td(A) > 1, A)", []),
        ("if(td(A) >= 1, A)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ("if(td(A) < 2, A)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ("if(td(B) == 2, B)", [(1, 3, 5), (3, 5, 6)]),
        ("if(td(B) <= 1, B)", []),
        # no map of A is equal to a map of B
        ("if(td(B) == 2, A)", []),
        ("if(td(A) == 1, A, N)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
    ],
)
def test_time_difference_conditions(algebra, expression, expected):
    """td() is the length of the interval in days; maps that fail a
    temporal-only condition are not selected"""
    assert algebra.triples(expression) == expected


@pytest.mark.parametrize(
    ("condition", "selected"),
    [
        ('start_date(A) >= "2001-01-03"', [3, 4]),
        ('start_date(A) < "2001-01-03"', [1, 2]),
        ('start_date(A) == "2001-01-02"', [2]),
        ('start_date(A) != "2001-01-02"', [1, 3, 4]),
        ('end_date(A) == "2001-01-04"', [3]),
        ('end_date(A) <= "2001-01-03"', [1, 2]),
        ("start_year(A) == 2001", [1, 2, 3, 4]),
        ("start_year(A) == 2002", []),
        ("start_month(A) == 1", [1, 2, 3, 4]),
        ("start_month(A) == 2", []),
        ("start_week(A) == 1", [1, 2, 3, 4]),
        ("start_day(A) == 3", [3]),
        ("start_day(A) > 2", [3, 4]),
        ("start_dow(A) == 3", [3]),
        ("start_dow(A) < 3", [1, 2]),
        ("start_doy(A) > 2", [3, 4]),
        ("start_hour(A) == 0", [1, 2, 3, 4]),
        ("start_hour(A) == 1", []),
        ("start_minute(A) == 0", [1, 2, 3, 4]),
        ("start_second(A) == 0", [1, 2, 3, 4]),
        ("end_year(A) == 2001", [1, 2, 3, 4]),
        ("end_month(A) == 1", [1, 2, 3, 4]),
        ("end_week(A) == 1", [1, 2, 3, 4]),
        ("end_day(A) == 3", [2]),
        ("end_dow(A) == 2", [1]),
        ("end_doy(A) < 3", [1]),
        ("end_hour(A) == 0", [1, 2, 3, 4]),
        ("end_minute(A) == 0", [1, 2, 3, 4]),
        ("end_second(A) == 0", [1, 2, 3, 4]),
    ],
)
def test_start_and_end_functions(algebra, condition, selected):
    """Each start_*() and end_*() function of the manual selects the maps whose
    time stamp fulfils the comparison"""
    expected = [(number, number + 1, number) for number in selected]
    assert algebra.triples(f"if({condition}, A)") == expected


@pytest.mark.parametrize(
    ("condition", "selected"),
    [
        ("start_doy(A, 0) == 3", [3]),
        # the offset selects the neighbour: -1 is the previous map
        ("start_doy(A, -1) == 3", [4]),
        ("start_doy(A, 1) == 3", [2]),
        ("end_day(A, -1) == 3", [3]),
        ("start_doy(A, -2) == 1", [3]),
    ],
)
def test_offset_in_time_functions(algebra, condition, selected):
    """start_doy(A, -1) is the value of the previous map; maps without such
    neighbour cannot be selected"""
    result = algebra.triples(f"if({condition}, A)")
    assert [(start, value) for start, _, value in result if value] == [
        (number, number) for number in selected
    ]


def test_offset_condition_drops_maps_without_neighbour(algebra):
    """The first map has no predecessor and is not part of the result"""
    assert algebra.triples("if(start_doy(A, -1) > 0, start_doy(A, -1), 0)") == [
        (2, 3, 1),
        (3, 4, 2),
        (4, 5, 3),
    ]


def test_time_functions_on_instants(algebra):
    """start_*() works for time instants and keeps them as instants"""
    assert algebra.triples("if(start_doy(I) == 2, I)") == [(2, None, 2)]
    assert algebra.triples('if(start_date(I) >= "2001-01-02", I)') == [
        (2, None, 2),
        (3, None, 3),
    ]


def test_doy_example_of_the_manual(algebra):
    """Example "Compute DOY for spatio-temporal conditions": the neighbour
    modifier and the offset of start_doy() in one expression"""
    expression = "if(A > 0.0 && A[-1] > 0.0 && A[-2] > 0.0, start_doy(A, -1), 0)"
    assert algebra.triples(expression) == [(3, 4, 2), (4, 5, 3)]


@pytest.mark.parametrize(
    ("condition", "selected"),
    [
        # Evaluated from left to right, the manual: ((d == 1 || d == 2) && d == 2)
        ("start_day(A) == 1 || start_day(A) == 2 && start_day(A) == 2", [2]),
        # ((d == 2 && d == 2) || d == 1)
        ("start_day(A) == 2 && start_day(A) == 2 || start_day(A) == 1", [1, 2]),
        ("start_day(A) == 1 || start_day(A) == 2 || start_day(A) == 4", [1, 2, 4]),
        ("start_day(A) > 0 && start_day(A) < 3 && start_day(A) < 2", [1]),
        ("start_day(A) > 0 && start_day(A) < 3 || start_day(A) == 4", [1, 2, 4]),
        ("start_day(A) == 4 || start_day(A) > 0 && start_day(A) < 3", [1, 2]),
        ('start_date(A) > "2001-01-01" && start_date(A) < "2001-01-04"', [2, 3]),
    ],
)
def test_temporal_conditions_are_combined_from_left_to_right(
    algebra, condition, selected
):
    """&& and || have the same precedence for temporal conditions"""
    expected = [(number, number + 1, number) for number in selected]
    assert algebra.triples(f"if({condition}, A)") == expected


@pytest.mark.parametrize(
    ("condition", "values"),
    [
        ("A > 1 && A < 4", [0, 2, 3, 0]),
        ("A < 3 && start_day(A) > 1", [0, 2, 0, 0]),
        ("A < 3 || start_day(A) > 3", [1, 2, 0, 4]),
        ("A < 3 && start_day(A) > 3", [0, 0, 0, 0]),
        ("start_day(A) > 1 && start_day(A) < 4 && A < 3", [0, 2, 0, 0]),
        ("td(A) == 1 && A > 2", [0, 0, 3, 4]),
        ("td(A) == 5 && A > 2", [0, 0, 0, 0]),
        ("td(A) == 5 || A > 2", [0, 0, 3, 4]),
        ("A > 2 && td(A) == 1", [0, 0, 3, 4]),
        ("td(A) == 1 && A == 2", [0, 2, 0, 0]),
        # the temporal condition is tested before the raster condition
        ("start_day(A) == 1 && A == 1 || A == 3", [1, 0, 3, 0]),
        ("td(A) == 5 && A == 1 || A == 3", [0, 0, 3, 0]),
        ("td(A) == 5 || td(A) == 1 && A == 1", [1, 0, 0, 0]),
        ("td(A) == 5 || td(A) == 5 || A == 3", [0, 0, 3, 0]),
    ],
)
def test_temporal_and_raster_conditions_combined(algebra, condition, values):
    """Raster conditions and temporal conditions can be mixed with && and ||"""
    assert algebra.triples(f"if({condition}, A, 0)") == a_intervals(values)


@pytest.mark.parametrize(
    ("condition", "values"),
    [
        ("td(A) == 1 && A == 1 || A == 3", [1, 0, 3, 0]),
        ("td(A) == 1 && A == 2 || A == 3", [0, 2, 3, 0]),
    ],
)
def test_td_and_raster_condition_chain(algebra, condition, values):
    """Evaluated from left to right: (td(A) == 1 && A == x) || A == 3"""
    assert algebra.triples(f"if({condition}, A)") == a_intervals(values)


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("if(start_day(A) == 2, A, 0)", [0, 2, 0, 0]),
        ("if(td(A) == 1, A, 0)", [1, 2, 3, 4]),
        ("if(td(A) == 2, A, 0)", [0, 0, 0, 0]),
        ("if({during}, td(B) == 2, A, 0)", [1, 2, 3, 4]),
        ("if({during}, td(B) == 1, A, 0)", [0, 0, 0, 0]),
    ],
)
def test_temporal_condition_with_number_as_else(algebra, expression, values):
    """if(topologies, conditions, A, 0) puts 0 where the condition is false"""
    assert algebra.values(expression) == values


def test_temporal_condition_with_else_expression(algebra):
    """The else branch of a temporal condition is evaluated for the others"""
    assert algebra.values("if(start_day(A) == 2, A, A * 10)") == [10, 2, 30, 40]
    assert algebra.values("if(start_day(A) == 2, A, N)") == [11, 2, 13, 14]


def test_hash_in_conditions(algebra):
    """Counting related maps with # in the condition"""
    assert algebra.triples("if(B {#,contains} A == 2, B)") == [(1, 3, 5), (3, 5, 6)]
    assert algebra.triples("if(B {#,contains} A > 2, B)") == []
    assert algebra.triples("if({equal}, A # D == 1, A)") == [(3, 4, 3), (4, 5, 4)]
    assert algebra.triples("if({equal}, B {#,contains} A > 1, B {:,contains} A)") == [
        (1, 3, 5),
        (3, 5, 6),
    ]


def test_hash_condition_with_computation(algebra):
    """Example "Computation with time intervals" of the manual, with the
    averaging written out: (b1 + a1 + a2 - b1) / 2 = 1, (b2 + a3 + a4 - b2) / 2 = 3"""
    expression = (
        "if({equal}, B {#,contains} A > 1, "
        "(B {+,contains,l} A {-,equal,l} B) {/,equal,l} (B {#,contains} A), A)"
    )
    assert algebra.triples(expression) == [(1, 3, 1), (3, 5, 3)]


def test_hash_condition_with_float_average(algebra):
    """The same average as float: (8 - 5) / 2 and (13 - 6) / 2"""
    expression = (
        "if(B {#,contains} A > 1, "
        "float(B {+,contains,l} A - B) / (B {#,contains} A), A)"
    )
    assert algebra.triples(expression) == [(1, 3, 1.5), (3, 5, 3.5)]


def test_manual_example_with_contains_relation(algebra):
    """Example "Computation with time intervals" as written in the manual"""
    expression = (
        "if(B {#,contains} A > 1, (B {+,contains,l} A - B) / (B {#,contains} A), A)"
    )
    assert algebra.triples(expression) == [(1, 3, 1), (3, 5, 3)]


def test_manual_example_with_equal_slash_operator(algebra):
    """Example "Computation with time intervals with temporal topology
    relation" as written in the manual"""
    expression = (
        "if({equal}, B {#,contains} A > 1, "
        "(B {+,contains,l} A {-,equal,l} B) {/,equal,l} (B {#,contains} A), A)"
    )
    assert len(algebra.run(expression)) == 2


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        (
            'if(start_date(A) < "2001-01-03", A + N)',
            [(1, 2, 12), (2, 3, 14)],
        ),
        ("if(A > 1 && A < 4 && td(A) > 0, N)", a_intervals([0, 12, 13, 0])),
    ],
)
def test_manual_examples_with_conditions(algebra, expression, expected):
    """Examples "Sum of space-time raster datasets" and "Selection of raster
    cells" of the manual with datasets of this fixture"""
    assert algebra.triples(expression) == expected


def test_manual_example_selection_with_topology(algebra):
    """Manual example: selection of raster cells with temporal topology relation"""
    expression = "if({equal}, A > 1 && A < 4 && td(A) > 0, N)"
    assert algebra.triples(expression) == a_intervals([0, 12, 13, 0])


@pytest.mark.parametrize(
    "expression",
    [
        "if(N > 12.0, A / 3600.0 / 24.0 / td(A))",
        "if({equal}, N > 12.0, A / 3600.0 / 24.0 {/,equal,l} td(A))",
    ],
)
def test_manual_example_conditional_computation(algebra, expression):
    """Example "Conditional computation": recharge per second where the
    condition holds, with and without explicit topology"""
    values = algebra.values(expression)
    assert values == pytest.approx([0, 0, 3 / 86400, 4 / 86400], abs=1e-6)


def test_manual_example_ndvi(algebra):
    """Example "Computation of NDVI" with float() and parentheses"""
    values = algebra.values("float(N - A) / (N + A)")
    assert values == pytest.approx([10 / 12, 10 / 14, 10 / 16, 10 / 18])


def test_conditions_with_unavailable_dataset_fail(algebra):
    """A condition on a STRDS that does not exist is an error"""
    with pytest.raises(algebra.errors, match="NotThere"):
        algebra.parse("if(NotThere > 1, A)")


CONDITION_HB = (
    "if({equal|contains}, HB {#,contains,r} HA == 2, HB {+,contains,l} HA, HA)"
)
CONDITION_HB_RIGHT = (
    "if({equal|contains|during}, HB {#,contains,r} HA == 2, HB {+,contains,r} HA, HA)"
)
# The maps of HA outside of HB: they have no condition map.
OUTSIDE_HB = "HA {!:,during} HB"


def test_else_part_needs_a_condition_map(algebra):
    """HB holds hb1 (7) [2,4] and hb2 (8) [4,6], HA has ha1..ha6 (1..6) of one
    day. hb1 + ha2 + ha3 = 12 and hb2 + ha4 + ha5 = 17 where HB contains two
    maps of HA. ha1 and ha6 lie outside of HB: without a condition map there
    is no result for them, also not from the else part."""
    assert algebra.triples(CONDITION_HB) == [(2, 4, 12), (4, 6, 17)]


def test_complement_with_merge(algebra):
    """The manual example: maps without condition map are added with merge()
    and the inverse select operator"""
    assert algebra.triples(f"merge({CONDITION_HB}, {OUTSIDE_HB})") == [
        (1, 2, 1),
        (2, 4, 12),
        (4, 6, 17),
        (6, 7, 6),
    ]


def test_complement_with_merge_and_right_reference(algebra):
    """As above with the time stamps of HA: one map per day"""
    assert algebra.triples(f"merge({CONDITION_HB_RIGHT}, {OUTSIDE_HB})") == [
        (1, 2, 1),
        (2, 3, 12),
        (3, 4, 12),
        (4, 5, 17),
        (5, 6, 17),
        (6, 7, 6),
    ]
