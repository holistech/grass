"""Invariants and laws of the temporal algebra semantics

The tests compare expressions with each other (metamorphic tests) and with
an independent oracle (Python booleans, hand written relation tables)
instead of fixing single outputs, so that they find inconsistencies nobody
thought of. The datasets are described in the algebra fixture.
"""

import itertools

import pytest

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


@pytest.mark.parametrize(
    ("bit", "dataset", "condition"),
    [
        (2, "PA", "start_month(T) == 2"),
        (1, "PB", "start_day(T) == 2"),
        (0, "PC", "start_hour(T) == 12"),
    ],
)
def test_truth_table_datasets(algebra, bit, dataset, condition):
    """The bits of the truth table maps are readable by value and by time"""
    selected = [number for number in range(8) if number >> bit & 1]
    assert algebra.values("T * 1") == list(range(8))
    # r.mapcalc gives 0 where the condition is false, so a map value
    # condition keeps all maps; a time condition keeps only the selected ones.
    assert algebra.values(f"if({dataset} == 1, T)") == [
        number if number in selected else 0 for number in range(8)
    ]
    assert algebra.values(f"if({condition}, T)") == selected


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
