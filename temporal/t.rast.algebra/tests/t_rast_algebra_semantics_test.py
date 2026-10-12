"""Invariants and laws of the temporal algebra semantics

The tests compare expressions with each other (metamorphic tests) and with
an independent oracle (Python booleans, hand written relation tables)
instead of fixing single outputs, so that they find inconsistencies nobody
thought of. The datasets are described in the algebra fixture.
"""

import itertools
import random
import re
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.temporal_algebra import TemporalAlgebraParser
from grass.temporal.temporal_raster_base_algebra import TemporalRasterAlgebraLexer
from grass.tools import Tools

RELATIONS = [
    "equal", "during", "contains", "starts", "started", "finishes",
    "finished", "precedes", "follows", "overlaps", "overlapped",
]  # fmt: skip


_basenames = itertools.count()


def fresh_basename():
    """A map name prefix that no earlier test has used

    Result maps of an earlier run keep their time stamp type, which
    influences a later run that overwrites them. A fresh prefix makes a test
    independent of the tests before it, at the cost of a few more maps.
    """
    return f"fresh{next(_basenames)}"


def real_times(algebra, expression, basename=None, **kwargs):
    """The (start, end) strings of the maps a real run registers"""
    rows = algebra.run(
        expression, basename or fresh_basename(), register_null=True, **kwargs
    )
    return sorted((str(row.start), str(row.end)) for row in rows)


@pytest.mark.parametrize(
    "expression",
    ["A + N", "A {+,during,r} B", "B {+,contains,u} A", "if(A > 2, A, N)"],
)
def test_dry_run_reports_the_maps_of_the_real_run(algebra, expression):
    """dry_times() measures what a real run registers"""
    assert algebra.dry_times(expression, register_null=True) == real_times(
        algebra, expression
    )


def test_dry_times_tell_temporal_operators_apart(algebra):
    """Negative check of the measurement: different results are visible"""
    assert algebra.dry_times("A {+,during,r} B") != algebra.dry_times(
        "A {+,during,l} B"
    )


# Bit of the number of a map of T, the dataset that holds the bit as value,
# and the condition of time stamps that is true for the bit.
TRUTH_TABLE_BITS = [
    (2, "PA", "start_month(T) == 2"),
    (1, "PB", "start_day(T) == 2"),
    (0, "PC", "start_hour(T) == 12"),
]


@pytest.mark.parametrize(("bit", "dataset", "condition"), TRUTH_TABLE_BITS)
def test_truth_table_datasets(algebra, bit, dataset, condition):
    """The bits of the truth table maps are readable by value and by time"""
    assert algebra.values("T * 1") == list(range(8))
    assert algebra.values(f"{dataset} * 1") == [
        number >> bit & 1 for number in range(8)
    ]
    assert algebra.values(f"if({condition}, T)") == [
        number for number in range(8) if number >> bit & 1
    ]


@pytest.mark.parametrize("relation", RELATIONS)
@pytest.mark.parametrize(("left", "right"), [("A", "B"), ("B", "A"), ("rel", "ref")])
def test_select_and_inverse_select_partition_the_dataset(
    algebra, relation, left, right
):
    """A {:,R} B and A {!:,R} B together are A, without overlap"""
    selected = algebra.dry_times(f"{left} {{:,{relation}}} {right}")
    rejected = algebra.dry_times(f"{left} {{!:,{relation}}} {right}")
    assert sorted(selected + rejected) == algebra.dry_times(f"{left} : {left}")


def later(task, reason):
    """xfail (strict) until the defect or the rewrite named by task is done

    Use "Kern" for behavior that only the planned rewrite of the algebra core
    fixes and "Befund" for a defect found by these tests. The test fails as
    soon as the case passes, so that the marker gets removed.
    """
    return pytest.mark.xfail(strict=True, reason=f"{task}: {reason}")


# Expressions of all kinds over datasets with unique time stamps.
CORPUS = [
    "A + N", "A - N * 2", "A {+,during,r} B", "B {+,contains,l} A",
    "B {+,contains,u} A", "A {*,during,i} B", "A : B", "A {:,during} B",
    "A {!:,during} B", "A {:,during,r} B", "B {:,contains,u} A",
    "B {:,contains,r} A", "B {#,contains} A", "A[1]", "A[-1] + A",
    'tshift(A, "1 day")', 'buff_t(A, "1 day")', "tsnap(B)",
    "merge(A, D {!:,equal} A)", "if(A > 2, A)", "if(A > 2, A, N)",
    "if(A > 2, A, 0)", "if(td(A) == 1, A)", "if(start_day(A) > 2, A, N)",
    "if({contains}, td(B) == 2, A)", "if({during}, A > 1, B)",
    "if({during}, start_day(A) > 1, B)", "if(A > 1 && td(A) == 1, A)",
    "if(A > 1 || start_day(A) == 1 && A < 3, A)", "RT * 2",
    "if(RT > 1, RT)", "I + 1",
]  # fmt: skip


@pytest.mark.parametrize("expression", CORPUS)
def test_dry_run_and_real_run_agree(algebra, expression):
    """The planned and the computed result maps are the same"""
    assert algebra.dry_times(expression, register_null=True) == real_times(
        algebra, expression
    )


@pytest.mark.parametrize("expression", CORPUS)
def test_result_is_reproducible(algebra, expression):
    """Running an expression twice (overwriting) gives the same maps"""
    basename = fresh_basename()
    assert algebra.run(expression, basename) == algebra.run(expression, basename)


@pytest.mark.parametrize("expression", ["RT * 2", "if(RT > 1, RT)"])
def test_relative_result_replaces_absolute_result_maps(algebra, expression):
    """A relative result written over absolute result maps of the same names"""
    basename = fresh_basename()
    algebra.run("A + N", basename)
    assert real_times(algebra, expression, basename) == algebra.dry_times(
        expression, register_null=True
    )


# (expression, expression that gives the conclusion maps): a conditional
# gives at most one result per conclusion map, at its time stamp.
CONDITION_CORPUS = [
    ("if(A > 2, A)", "A : A"),
    ("if(td(A) == 1, A)", "A : A"),
    ("if({contains}, td(B) == 2, A)", "A : A"),
    pytest.param(
        "if({during}, A > 1, B)", "B : B",
        marks=later("Kern", "one result per pair of maps"),
    ),
    ("if({during}, start_day(A) > 1, B)", "B : B"),
    pytest.param(
        "if({during}, A > 1 || start_day(A) == 1, B)", "B : B",
        marks=later("Kern", "one result per pair of maps"),
    ),
    ("if({equal|contains}, HB {#,contains} HA == 2, HB {+,contains,l} HA)", "HB : HB"),
]  # fmt: skip


@pytest.mark.parametrize(("expression", "conclusion"), CONDITION_CORPUS)
def test_one_result_per_conclusion_map(algebra, expression, conclusion):
    """No duplicate time stamps, and only time stamps of conclusion maps"""
    times = algebra.dry_times(expression, register_null=True)
    assert len(times) == len(set(times))
    assert set(times) <= set(algebra.dry_times(conclusion))


@pytest.mark.parametrize(
    "operator", ["{#,contains,r}", "{#,contains,u}", "{#,contains,i}",
                 "{#,contains,d}", "{#,contains,right}"],
)  # fmt: skip
def test_hash_rejects_temporal_operators(algebra, operator):
    """The count keeps the time stamps of the left maps, r, u, i and d have
    no meaning for it"""
    with pytest.raises(SyntaxError, match="temporal operator"):
        algebra.parse(f"B {operator} A")


@pytest.mark.parametrize("operator", ["{#,contains}", "{#,contains,l}"])
def test_hash_keeps_the_left_time_stamps(algebra, operator):
    """b1 and b2 each contain two maps of A (started and finished)"""
    assert algebra.triples(f"B {operator} A") == [(1, 3, 2), (3, 5, 2)]


@pytest.mark.parametrize(
    "expression", ["merge(A, A)", "merge(A {:,during} B, A)", "merge(A, A : A)"]
)
def test_merge_keeps_one_of_identical_maps(algebra, expression):
    assert algebra.values(expression) == [1, 2, 3, 4]


def test_merge_of_overlapping_selections(algebra):
    """A {:,during} B selects all maps of A (a1, a3 start, a2, a4 finish a
    map of B), A {:,during} C selects a2 and a3 (start and finish c1)"""
    assert algebra.values("merge(A {:,during} B, A {:,during} C)") == [1, 2, 3, 4]


def test_merged_maps_are_not_counted_twice(algebra):
    """Without the deduplication of merge(), n2 + a2 + a2 = 16 and n3 + a3 + a3 = 19"""
    assert algebra.values("N {+,equal} merge(A {:,during} B, A {:,during} C)") == [
        12,
        14,
        16,
        18,
    ]


def test_merge_keeps_different_maps_of_equal_time(algebra):
    """Computed maps of equal time are different maps"""
    assert algebra.values("merge(A + 1, A + 2)") == [2, 3, 3, 4, 4, 5, 5, 6]


@pytest.mark.parametrize("relation", RELATIONS)
def test_merge_of_select_and_inverse_select_is_the_dataset(algebra, relation):
    """Holds without the deduplication of merge() as well, selection and
    inverse selection are disjoint; it guards that the deduplication removes
    nothing else"""
    assert algebra.dry_times(
        f"merge(A {{:,{relation}}} B, A {{!:,{relation}}} B)"
    ) == algebra.dry_times("A : A")


@pytest.mark.parametrize(
    ("expression", "count"),
    [
        ("merge(A, A)", 4),
        ("merge(A {:,during} B, A {:,during} C)", 2),
        ("merge(A {:,during} B, A {!:,during} B)", 0),
    ],
)
def test_merge_warns_about_identical_maps(algebra, monkeypatch, expression, count):
    """capfd stays empty although the warning shows in the captured stderr of
    the report (observed 2026-10-11); probably the messenger, a process wide
    singleton, keeps the stderr of the first test that used it. The test
    records the calls instead"""
    warnings = []
    messenger = tgis.get_tgis_message_interface()
    monkeypatch.setattr(messenger, "warning", warnings.append)
    algebra.run(expression)
    if count:
        assert len(warnings) == 1
        assert f"keeps {count} maps of both operands only once" in warnings[0]
    else:
        assert not warnings


def fresh_triples(algebra, expression, **kwargs):
    """algebra.triples() with result maps that no earlier test has used"""
    return algebra.triples(expression, basename=fresh_basename(), **kwargs)


def fresh_values(algebra, expression, **kwargs):
    """algebra.values() with result maps that no earlier test has used"""
    return algebra.values(expression, basename=fresh_basename(), **kwargs)


# The tests from here on state the rules that the planned rewrite of the
# algebra core must meet. A case that the current code does not meet is
# marked later("Kern", ...); the reasons below name the rule in words.
NULL_WITHOUT_ELSE = (
    "an if without else gives null where a condition on map values is false, "
    "so a map that is false everywhere is left out as with a condition of "
    "time stamps"
)
AGGREGATE_WITH_OR = (
    "the relation takes an aggregation, {during,|} joins the conditions of "
    "the condition maps of one conclusion map with or"
)
AGGREGATE_WITH_AND = (
    "the relation takes an aggregation, {during,&} joins the conditions of "
    "the condition maps of one conclusion map with and"
)
ONE_RESULT_PER_CONCLUSION = (
    "a conditional gives one result per conclusion map and joins the "
    "conditions of its condition maps with and"
)
SELECT_WITH_PARTNER_EXTENT = (
    "a selection with the temporal operator r gives one map per related "
    "map with the extent of the related map, like the operator +"
)

TEMPORAL_OPERATORS = ["l", "r", "u", "i", "d"]
RELATION_SETS = [
    "equal", "during", "contains", "overlaps|overlapped",
    "starts|finishes|started|finished", "follows|precedes",
]  # fmt: skip
# Pairs and relations for which the selection and the operator + give no map
# at all. They are left out of test_select_has_the_time_stamps_of_the_operator,
# because comparing two empty lists proves nothing. Measured 2026-10-11 by
# running both dry for every pair, relation and temporal operator: the
# temporal operator does not change which maps are empty.
EMPTY_SELECTIONS = {
    ("A", "B", "contains"),
    ("A", "B", "equal"),
    ("A", "B", "overlaps|overlapped"),
    ("B", "A", "during"),
    ("B", "A", "equal"),
    ("B", "A", "overlaps|overlapped"),
    ("HB", "HA", "during"),
    ("HB", "HA", "equal"),
    ("HB", "HA", "overlaps|overlapped"),
}
# Cases of test_select_has_the_time_stamps_of_the_operator that differ today
# (measured 2026-10-11 in the same run): all use the temporal operator r.
SELECT_EXTENT_DIFFERS = {
    ("B", "A", "contains", "r"),
    ("B", "A", "starts|finishes|started|finished", "r"),
    ("HB", "HA", "contains", "r"),
    ("HB", "HA", "starts|finishes|started|finished", "r"),
    ("HB", "HA", "follows|precedes", "r"),
}


def select_extent_cases():
    cases = []
    for (left, right), relations, temporal in itertools.product(
        [("A", "B"), ("B", "A"), ("HB", "HA"), ("rel", "ref")],
        RELATION_SETS,
        TEMPORAL_OPERATORS,
    ):
        if (left, right, relations) in EMPTY_SELECTIONS:
            continue
        marks = []
        if (left, right, relations, temporal) in SELECT_EXTENT_DIFFERS:
            marks.append(later("Kern", SELECT_WITH_PARTNER_EXTENT))
        cases.append(pytest.param(left, right, relations, temporal, marks=marks))
    return cases


@pytest.mark.parametrize(
    ("left", "right", "relations", "temporal"), select_extent_cases()
)
def test_select_has_the_time_stamps_of_the_operator(
    algebra, left, right, relations, temporal
):
    """X {:,R,t} Y has the time stamps of X {+,R,t} Y"""
    selected = algebra.dry_times(f"{left} {{:,{relations},{temporal}}} {right}")
    assert selected
    assert selected == algebra.dry_times(f"{left} {{+,{relations},{temporal}}} {right}")


@later("Kern", SELECT_WITH_PARTNER_EXTENT)
def test_select_with_right_reference_gives_one_map_per_pair(algebra):
    """Each map of B contains two maps of A: two results per map of B, with
    the values of B and the time stamps of A"""
    assert fresh_triples(algebra, "B {:,contains,r} A") == [
        (1, 2, 5), (2, 3, 5), (3, 4, 6), (4, 5, 6),
    ]  # fmt: skip


@pytest.mark.parametrize(
    "temporal",
    [
        pytest.param(
            temporal,
            marks=later(
                "Kern",
                "an inverse selection with a temporal operator other than l is "
                "a syntax error, because its maps have no related map",
            ),
        )
        for temporal in ["r", "u", "i", "d"]
    ],
)
def test_inverse_select_rejects_temporal_operators(algebra, temporal):
    """Maps without partner have no extent to combine with"""
    with pytest.raises(SyntaxError, match="temporal operator"):
        algebra.parse(f"A {{!:,during,{temporal}}} B")


# ref R probe: the probes that the reference has the relation to, derived
# from PROBES (probe R ref) by inverting the relation.
REF_RELATION_PROBES = {
    "equal": [1], "contains": [2, 4, 6], "during": [3, 5, 7],
    "starts": [5], "started": [4], "finishes": [7], "finished": [6],
    "precedes": [9], "follows": [8], "overlaps": [11], "overlapped": [10],
}  # fmt: skip
INVERSE = {
    "equal": "equal", "contains": "during", "during": "contains",
    "starts": "started", "started": "starts", "finishes": "finished",
    "finished": "finishes", "precedes": "follows", "follows": "precedes",
    "overlaps": "overlapped", "overlapped": "overlaps",
}  # fmt: skip


def probes(algebra, expression):
    return sorted(int(value) for value in fresh_values(algebra, expression))


@pytest.mark.parametrize("relation", RELATIONS)
def test_reference_table_agrees_with_selection(algebra, relation):
    """The oracle of the direction tests, checked against the selection"""
    assert (
        probes(algebra, f"rel {{:,{INVERSE[relation]}}} ref")
        == REF_RELATION_PROBES[relation]
    )


@pytest.mark.parametrize("relation", RELATIONS)
@pytest.mark.parametrize(
    "condition", ["td(ref) > 0", 'start_date(ref) == "2001-01-10"']
)
def test_temporal_condition_relation_reads_condition_to_conclusion(
    algebra, relation, condition
):
    """if({R}, c, X) keeps the maps x of X for which c R x holds"""
    assert (
        probes(algebra, f"if({{{relation}}}, {condition}, rel)")
        == REF_RELATION_PROBES[relation]
    )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # b1 [1,3] has the conditions a1, a2 (during), b2 [3,5] a3, a4
        ("if({during}, start_day(A) > 1, B)", [(3, 5, 6)]),
        pytest.param(
            "if({during,&}, start_day(A) > 1, B)",
            [(3, 5, 6)],
            marks=later("Kern", AGGREGATE_WITH_AND),
        ),
        pytest.param(
            "if({during,|}, start_day(A) > 1, B)",
            [(1, 3, 5), (3, 5, 6)],
            marks=later("Kern", AGGREGATE_WITH_OR),
        ),
        ("if({during}, start_day(A) > 1, B, 0)", [(1, 3, 0), (3, 5, 6)]),
        pytest.param(
            "if({during,|}, start_day(A) > 2, B, 0)",
            [(1, 3, 0), (3, 5, 6)],
            marks=later("Kern", AGGREGATE_WITH_OR),
        ),
        # The manual example of t.select with A, B and C of this fixture: the
        # buffered maps of A are [k-1, k+2], all three days long. b1 [1,3] is
        # contained (finished, started) by the buffers of a1 and a2, b2 [3,5]
        # by those of a3 and a4: then. c1 [2,4] by those of a2 and a3, so
        # its condition is true and the else part gives nothing.
        ('if({contains}, td(buff_t(A, "1 days")) == 3, B, C)', [(1, 3, 5), (3, 5, 6)]),
    ],
)
def test_temporal_condition_aggregates_per_conclusion(algebra, expression, expected):
    """One result per conclusion map; the conditions of its condition maps
    are joined with & (default) or |"""
    assert fresh_triples(algebra, expression) == expected


def test_equal_time_conditions_are_broadcast_to_one_conclusion(algebra):
    """The four instants of E lie in b1; as one conclusion map b1 gets all
    of them"""
    assert fresh_triples(algebra, "if({during}, start_day(E) == 1, B)") == [(1, 3, 5)]


def test_relation_condition_in_relative_time(algebra):
    """Relative time behaves as absolute time"""

    def relative_values(expression):
        # triples() reads days of the month, which relative time has not
        rows = algebra.run(expression, fresh_basename())
        assert all(row.min == row.max for row in rows)
        return [row.min for row in rows]

    assert relative_values("if({equal}, td(RT) == 1, RT)") == [1, 2, 3]
    assert relative_values("if({during}, td(RT) == 1, RT)") == []


@pytest.mark.parametrize("relation", RELATIONS)
@pytest.mark.parametrize("condition", ["ref > 0", "ref > 0 && td(ref) > 0"])
def test_map_condition_relation_reads_condition_to_conclusion(
    algebra, relation, condition
):
    """The same direction as temporal conditions"""
    assert (
        probes(algebra, f"if({{{relation}}}, {condition}, rel)")
        == REF_RELATION_PROBES[relation]
    )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        pytest.param(
            "if({during}, A > 1, B)",
            # b1 has a1 > 1 false and a2 > 1 true: false with &. Without else
            # b1 is null then and left out.
            [(3, 5, 6)],
            marks=later("Kern", f"{ONE_RESULT_PER_CONCLUSION}; {NULL_WITHOUT_ELSE}"),
        ),
        pytest.param(
            "if({during,|}, A > 1, B)",
            [(1, 3, 5), (3, 5, 6)],
            marks=later("Kern", AGGREGATE_WITH_OR),
        ),
        pytest.param(
            "if({during}, A > 1, B, 0)",
            [(1, 3, 0), (3, 5, 6)],
            marks=later("Kern", ONE_RESULT_PER_CONCLUSION),
        ),
        pytest.param(
            "if({during,|}, A > 2, B, 0)",
            [(1, 3, 0), (3, 5, 6)],
            marks=later("Kern", AGGREGATE_WITH_OR),
        ),
        pytest.param(
            "if({during}, A > 1 || start_day(A) == 1, B)",
            [(1, 3, 5), (3, 5, 6)],
            marks=later("Kern", ONE_RESULT_PER_CONCLUSION),
        ),
    ],
)
def test_map_condition_aggregates_per_conclusion(algebra, expression, expected):
    assert fresh_triples(algebra, expression) == expected


@pytest.mark.parametrize(
    "aggregate",
    [
        pytest.param("", marks=later("Kern", ONE_RESULT_PER_CONCLUSION)),
        pytest.param(",|", marks=later("Kern", AGGREGATE_WITH_OR)),
    ],
)
def test_both_paths_agree_on_aggregation(algebra, aggregate):
    """A > 1 and start_day(A) > 1 are true for the same maps of A"""
    assert fresh_triples(algebra, f"if({{during{aggregate}}}, A > 1, B, 0)") == (
        fresh_triples(algebra, f"if({{during{aggregate}}}, start_day(A) > 1, B, 0)")
    )


@later("Kern", f"{ONE_RESULT_PER_CONCLUSION}; {NULL_WITHOUT_ELSE}")
def test_equal_time_map_conditions_are_broadcast(algebra):
    """Four condition maps of equal time, one conclusion: e1 > 2 and e2 > 2
    are false, so b1 is null and left out with &, and has the value of b1
    with |"""
    assert fresh_triples(algebra, "if({during}, E > 2, B)") == []
    assert fresh_triples(algebra, "if({during,|}, E > 2, B)") == [(1, 3, 5)]


@pytest.mark.parametrize(
    "condition",
    [
        "B > 0",
        "start_day(B) > 0",
        "B > 0 && start_day(B) > 0",
    ],
)
def test_instants_within_intervals(algebra, condition):
    """An instant lies in [start, end) of an interval; i1 and i2 in b1 [1,3],
    i3 in b2 [3,5]"""
    assert fresh_values(algebra, f"if({{contains}}, {condition}, I)") == [1, 2, 3]


@pytest.mark.parametrize(
    ("relations", "expected"),
    [
        # spa2 [20,50] contains spb3 [25,40]
        ("equal|contain", [3]),
        # spb2 [20,50] contains spa3 [25,40]
        ("equal|in", [2]),
    ],
)
def test_spatial_conditions_do_not_pair_by_order(
    algebra, large_region, relations, expected
):
    """With spatial topology the maps of equal time are told apart by space,
    so only the spatially related conclusion maps get a result"""
    assert (
        fresh_values(algebra, f"if({{{relations}}}, SA > 0, SB)", spatial=True)
        == expected
    )


@pytest.mark.parametrize(
    "expression",
    ["if({during}, A > 1, ref)", "if({during}, start_day(A) > 1, ref)"],
)
def test_condition_without_related_map_gives_empty_result(algebra, expression):
    """No traceback, an empty result dataset"""
    assert algebra.run(expression, fresh_basename()) == []


THEN_ELSE_OF_EQUAL_TIME = (
    "a condition on map values chooses per cell between then and else, so "
    "it stops with an error unless both have the same time stamps"
)


@pytest.mark.parametrize(
    "expression",
    [
        pytest.param(expression, marks=later("Kern", THEN_ELSE_OF_EQUAL_TIME))
        for expression in [
            "if({equal|during}, A > 2, B, A)",
            "if(A > 2, if(A > 3, A, N), B)",
            "if(A > 2, A, D)",
        ]
    ],
)
def test_map_condition_needs_then_and_else_of_equal_time(algebra, expression):
    with pytest.raises(algebra.errors, match="equal time stamps"):
        algebra.run(expression, fresh_basename())


@pytest.mark.parametrize(
    ("expression", "values"),
    [
        ("if(A > 2, A, N)", [11, 12, 3, 4]),
        ("if(E > 2, E, E * 10)", [3, 4, 10, 20]),
        ("if(A > 2, A, 0)", [0, 0, 3, 4]),
        ("if(A > 2, null(), N)", [11, 12]),
    ],
)
def test_map_condition_with_matching_then_and_else(algebra, expression, values):
    assert fresh_values(algebra, expression) == values


def test_temporal_condition_takes_then_and_else_independently(algebra):
    """For temporal conditions then and else need no common time.

    then B: b2 (start day 3) is true, b1 false. else A: a1 and a2 lie in
    b1 (false), so they are taken; a3 and a4 lie in b2 (true), so not.
    """
    assert fresh_triples(
        algebra, "if({equal|contains}, start_day(B) > 2, B, A)"
    ) == [
        (1, 2, 1), (2, 3, 2), (3, 5, 6),
    ]  # fmt: skip


def test_else_takes_maps_without_related_condition(algebra):
    """With a relation beyond equal, else also takes the maps that no
    condition is related to, as in figure A3 of the paper that introduced
    the algebra (Gebbert, Leppelt and Pebesma 2019, section 3.2.1); then
    leaves them out. d1 and d2 lie in b2 (true), d3 [5,6] is related to no
    map of B."""
    assert fresh_triples(algebra, "if({equal|contains}, start_day(B) > 2, B, D)") == [
        (3, 5, 6),
        (5, 6, 10),
    ]
    assert fresh_triples(algebra, "if({equal|contains}, start_day(B) > 2, D, 0)") == [
        (3, 4, 8),
        (4, 5, 9),
        (5, 6, 0),
    ]


@pytest.mark.parametrize("relation", ["", "{equal}, "])
def test_else_without_relation_beyond_equal_takes_no_unrelated_maps(algebra, relation):
    """if({equal}, ...) means the same as if(...): the condition speaks of
    maps of equal time only, and no map of D has the time of a map of B"""
    assert fresh_triples(algebra, f"if({relation}start_day(B) > 2, B, D)") == [
        (3, 5, 6)
    ]


# Atom name -> (temporal condition, map condition); both are true for the
# maps of T whose bit is set, see the T, PA, PB, PC datasets.
ATOMS = {
    "a": ("start_month(T) == 2", "PA == 1"),
    "b": ("start_day(T) == 2", "PB == 1"),
    "c": ("start_hour(T) == 12", "PC == 1"),
}
NEGATED = {
    "a": ("start_month(T) != 2", "PA != 1"),
    "b": ("start_day(T) != 2", "PB != 1"),
    "c": ("start_hour(T) != 12", "PC != 1"),
}
PARENTHESES = "conditions can be grouped with parentheses"
PRECEDENCE = "&& binds stronger than || in conditions of time stamps"


def bits(number):
    return {
        "a": bool(number >> 2 & 1),
        "b": bool(number >> 1 & 1),
        "c": bool(number & 1),
    }


def selected(python_formula):
    """The maps of T for which the formula is true; Python gives `and` a
    higher precedence than `or`, like the specification of && and ||"""
    return [k for k in range(8) if eval(python_formula, {}, bits(k))]  # noqa: S307


def null_without_else(python_formula, has_map_condition):
    """The mark of a case that the null rule decides

    Today a condition on map values gives 0 where it is false and keeps all
    eight maps, so such a case fails unless the formula is true for all maps.
    """
    if has_map_condition and selected(python_formula) != list(range(8)):
        return [later("Kern", NULL_WITHOUT_ELSE)]
    return []


def groups_with_parentheses(condition):
    """True if the condition has parentheses other than those of a function"""
    return "(" in re.sub(r"\w+\(T\)", "", condition)


def render(rng, depth, kind):
    """Return (algebra condition, Python formula, has a map atom) of a random
    formula

    kind is "time", "map" or "mixed" (each atom picks one at random).
    """
    if depth == 0 or rng.random() < 0.3:
        name = rng.choice("abc")
        negated = rng.random() < 0.3
        pick = kind if kind != "mixed" else rng.choice(["time", "map"])
        text = (NEGATED if negated else ATOMS)[name][pick == "map"]
        return text, f"(not {name})" if negated else name, pick == "map"
    operator = rng.choice(["&&", "||"])
    left = render(rng, depth - 1, kind)
    right = render(rng, depth - 1, kind)
    algebra_text = f"{left[0]} {operator} {right[0]}"
    python_text = f"{left[1]} {'and' if operator == '&&' else 'or'} {right[1]}"
    if rng.random() < 0.4:
        algebra_text, python_text = f"({algebra_text})", f"({python_text})"
    return algebra_text, python_text, left[2] or right[2]


FORMULAS = [
    ("{a} || {b} && {c}", "a or (b and c)"),
    ("{a} && {b} || {c}", "(a and b) or c"),
    ("({a} || {b}) && {c}", "(a or b) and c"),
    ("{a} || ({b} && {c})", "a or (b and c)"),
    ("{a} && ({b} || {c})", "a and (b or c)"),
    ("{a} || {b} || {c}", "a or b or c"),
    ("{a} && {b} && {c}", "a and b and c"),
    ("({a} || {b}) && ({c} || {a})", "(a or b) and (c or a)"),
]
# For each kind the atoms a, b, c are conditions of time stamps or of map values.
KINDS = {
    "time": ("time", "time", "time"), "map": ("map", "map", "map"),
    "mixed1": ("time", "map", "time"), "mixed2": ("map", "time", "map"),
}  # fmt: skip


def truth_table_cases():
    cases = []
    for (condition, formula), kind in itertools.product(FORMULAS, KINDS):
        marks = null_without_else(formula, kind != "time")
        if "(" in condition:
            marks.append(later("Kern", PARENTHESES))
        elif kind == "time" and condition == "{a} || {b} && {c}":
            # The map conditions are left to the precedence of r.mapcalc. The
            # case "a && b || c" of time stamps passes today by chance:
            # evaluated from left to right it gives the same maps.
            marks.append(later("Kern", PRECEDENCE))
        cases.append(pytest.param(condition, formula, kind, marks=marks))
    return cases


@pytest.mark.parametrize(("condition", "formula", "kind"), truth_table_cases())
def test_precedence_truth_table(algebra, condition, formula, kind):
    """&& before ||, parentheses group, in every kind of condition"""
    texts = {
        name: ATOMS[name][choice == "map"]
        for name, choice in zip("abc", KINDS[kind], strict=True)
    }
    expression = f"if({condition.format(**texts)}, T)"
    assert fresh_values(algebra, expression) == selected(formula)


def random_condition(seed):
    """(algebra condition, Python formula, has a map atom) of a seed"""
    rng = random.Random(seed)
    return render(rng, 3, rng.choice(["time", "map", "mixed"]))


def random_cases():
    cases = []
    for seed in range(40):
        condition, formula, has_map = random_condition(seed)
        marks = null_without_else(formula, has_map)
        if groups_with_parentheses(condition):
            marks.append(later("Kern", PARENTHESES))
        cases.append(pytest.param(seed, marks=marks))
    return cases


@pytest.mark.parametrize("seed", random_cases())
def test_random_conditions_match_python(algebra, seed):
    """Random formulas of temporal, map and mixed conditions"""
    condition, formula, _has_map = random_condition(seed)
    assert fresh_values(algebra, f"if({condition}, T)") == selected(formula), condition


# Conditions of time stamps, of map values, with || and with parentheses.
CONDITIONS = [
    "start_month(T) == 2", "PA == 1", "start_day(T) == 2 || PC == 1",
    "(PB == 1 && start_hour(T) == 12)",
]  # fmt: skip


PRECEDENCE_MIXED = (
    "&& binds stronger than || in conditions that mix time stamps and map values"
)


def law_pairs(operator):
    """Pairs of CONDITIONS joined by operator, marked for what the current
    code cannot do yet

    A pair passes without a mark where the missing precedence cannot change
    the result, e.g. when both conditions contain ||.
    """
    pairs = []
    for first, second in itertools.product(CONDITIONS, repeat=2):
        marks = []
        if first.startswith("(") or second.startswith("("):
            marks.append(later("Kern", PARENTHESES))
        elif operator == "&&" and ("||" in first) != ("||" in second):
            marks.append(later("Kern", PRECEDENCE_MIXED))
        pairs.append(pytest.param(first, second, marks=marks))
    return pairs


def has_map_value(condition):
    """True if the condition compares the values of maps (PA, PB or PC)"""
    return re.search(r"\bP[ABC]\b", condition) is not None


def conjunction_pairs():
    """law_pairs("&&"), with the null rule where only one condition uses map
    values: today the nested if lacks the maps that the condition of time
    stamps leaves out, while the && of both has them with the value 0"""
    pairs = []
    for pair in law_pairs("&&"):
        first, second = pair.values
        marks = list(pair.marks)
        if has_map_value(first) != has_map_value(second):
            marks.append(later("Kern", NULL_WITHOUT_ELSE))
        pairs.append(pytest.param(first, second, marks=marks))
    return pairs


@pytest.mark.parametrize(("first", "second"), conjunction_pairs())
def test_nested_if_is_conjunction(algebra, first, second):
    """if(c1, if(c2, X)) == if(c1 && c2, X)"""
    nested = fresh_values(algebra, f"if({first}, if({second}, T))")
    conjunction = fresh_values(algebra, f"if({first} && {second}, T)")
    assert nested == conjunction


@later("Kern", NULL_WITHOUT_ELSE)
@pytest.mark.parametrize(
    ("dataset", "condition"),
    [(dataset, condition) for _bit, dataset, condition in TRUTH_TABLE_BITS],
)
def test_map_conditions_select_like_time_stamp_conditions(algebra, dataset, condition):
    """A condition on map values and one of time stamps that are true for the
    same maps select the same maps"""
    assert fresh_values(algebra, f"if({dataset} == 1, T)") == fresh_values(
        algebra, f"if({condition}, T)"
    )


def commute_cases():
    return [
        pytest.param(operator, *pair.values, marks=pair.marks)
        for operator in ["&&", "||"]
        for pair in law_pairs(operator)
    ]


@pytest.mark.parametrize(("operator", "first", "second"), commute_cases())
def test_conditions_commute(algebra, operator, first, second):
    assert fresh_values(algebra, f"if({first} {operator} {second}, T)") == fresh_values(
        algebra, f"if({second} {operator} {first}, T)"
    )


def test_spatial_run_keeps_the_region(algebra):
    """The region of the session is the same before and after the run

    A spatial run computes with r.mapcalc region=union, which must use the
    union of the regions of the maps without writing it into the region of
    the mapset.
    """
    tools = Tools(session=algebra.session)
    before = tools.g_region(flags="g").keyval
    try:
        fresh_values(algebra, "SA + SB", spatial=True)
        after = tools.g_region(flags="g").keyval
    finally:
        # Later tests compute in this region, whatever the run did to it.
        tools.g_region(
            n=before["n"],
            s=before["s"],
            e=before["e"],
            w=before["w"],
            res=before["nsres"],
        )
    assert after == before


MANUAL = Path(__file__).parents[1] / "t.rast.algebra.md"


def manual_expressions():
    """Assignments 'X = ...' in the sh code blocks of the manual"""
    blocks = re.findall(r"```sh\n(.*?)```", MANUAL.read_text(), flags=re.DOTALL)
    return [
        line.strip()
        for block in blocks
        for line in block.splitlines()
        if re.match(r"^[A-Za-z_]\w* = ", line.strip())
    ]


# Single maps of the fixture; map() and tmap() of any other map cannot run.
FIXTURE_SINGLE_MAPS = {"singletmap", "sinst", "singlemap"}


def manual_cases():
    cases = []
    for assignment in manual_expressions():
        marks = []
        missing = sorted(
            set(re.findall(r"\bt?map\((\w+)\)", assignment)) - FIXTURE_SINGLE_MAPS
        )
        if missing:
            marks.append(pytest.mark.skip(reason=f"maps not in the fixture: {missing}"))
        cases.append(pytest.param(assignment, marks=marks))
    return cases


@pytest.mark.parametrize("assignment", manual_cases())
def test_manual_example_runs(algebra, assignment):
    """Every example of the manual on datasets of the fixture parses and plans
    (dry run)"""
    _name, expression = assignment.split(" = ", 1)
    # The default lexer does not know the arithmetic operators of the raster
    # algebra.
    names = TemporalAlgebraParser._stds_names_in(
        expression, TemporalRasterAlgebraLexer()
    )
    missing = [name for name in names if not algebra.exists(name)]
    if missing:
        pytest.skip(f"datasets not in the fixture: {missing}")
    algebra.dry_times(expression)
