"""t.select on four vector datasets of one-day and three-day maps in 2013

The datasets and the expressions are those of the old shell test. test1 has
the 20 one-day maps testpoint1_1 to testpoint1_20 from January 1, test2 the
maps testpoint2_21 to testpoint2_40 of one day from January 10, test3 the maps
testpoint3_41 to testpoint3_60 of three days from January 1 and test4 the maps
testpoint4_41 to testpoint4_60 of three days from January 10. Days are counted
from January 1, so test1 holds [0, 1) to [19, 20), test2 [9, 10) to [28, 29),
test3 [0, 3) to [57, 60) and test4 [9, 12) to [66, 69). The expected maps are
derived from these extents.
"""

import itertools
from datetime import datetime, timedelta

import pytest

from grass.temporal.testing.data import MapSpec, register_stds
from grass.tools import Tools

YEAR0 = datetime(2013, 1, 1)

# dataset -> (prefix, first map number, length in days, first day)
DATASETS = {
    "test1": ("testpoint1_", 1, 1, 0),
    "test2": ("testpoint2_", 21, 1, 9),
    "test3": ("testpoint3_", 41, 3, 0),
    "test4": ("testpoint4_", 41, 3, 9),
}


def _extents(dataset):
    """(name, start, end) of the 20 maps of a dataset, in days from January 1"""
    prefix, first, length, start = DATASETS[dataset]
    return [
        (f"{prefix}{first + k}", start + length * k, start + length * (k + 1))
        for k in range(20)
    ]


@pytest.fixture(scope="module")
def vectors(series):
    """The four datasets, made in the session of the series fixture"""
    tools = Tools(session=series.session, overwrite=True)
    for dataset in DATASETS:
        rows = _extents(dataset)
        for name, _, _ in rows:
            tools.v_random(output=name, npoints=3, seed=int(name.rsplit("_", 1)[1]))
        register_stds(
            tools,
            "stvds",
            dataset,
            [
                MapSpec(name, 1, YEAR0 + timedelta(days=s), YEAR0 + timedelta(days=e))
                for name, s, e in rows
            ],
        )
    return series.session


def _day(text):
    """Days from January 1, 2013 of a time stamp"""
    return (datetime.strptime(text, "%Y-%m-%d %H:%M:%S") - YEAR0).days


_results = itertools.count(1)


def _rows(session, expression):
    """(name, start, end) of the result of t.select, in days from January 1"""
    result = f"scenario{next(_results)}"
    tools = Tools(session=session, overwrite=True)
    tools.t_select(expression=f"{result} = {expression}", type="stvds")
    listing = tools.t_vect_list(
        input=result, columns="name,start_time,end_time", format="json"
    )
    return sorted(
        (row["name"], _day(row["start_time"]), _day(row["end_time"]))
        for row in listing["data"]
    )


def _maps(dataset, numbers):
    """The rows (name, start, end) of a dataset for the given map numbers"""
    wanted = {f"{DATASETS[dataset][0]}{number}" for number in numbers}
    return [row for row in _extents(dataset) if row[0] in wanted]


def _expected(*parts):
    """The sorted rows of (dataset, numbers) parts"""
    return sorted(row for dataset, numbers in parts for row in _maps(dataset, numbers))


def _ones(first, last):
    return range(first, last + 1)


# Selection by the equal relation and its complement. test1 [i-1, i) equals a
# test2 map [j-12, j-11) for the days 9 to 19, which are test1_10 to test1_20 and
# test2_21 to test2_31.
SELECTIONS = [
    ("test1 : test2", [("test1", _ones(10, 20))]),
    ("test1 !: test2", [("test1", _ones(1, 9))]),
    ("test2 {:,equal} test1", [("test2", _ones(21, 31))]),
    # buff_t widens a test2 map [s, s + 1) to [s - 1, s + 2); test1 maps that
    # lie in one of them are those with the days 8 to 19.
    (
        'test1 {:,during} buff_t(test2, "1 days")',
        [("test1", _ones(9, 20))],
    ),
    (
        'tsnap(test1 {:,during} buff_t(test2, "1 days"))',
        [("test1", _ones(9, 20))],
    ),
    # test1 and test3 cover the days 0 to 19 and 0 to 59 without a gap, test4
    # the days 9 to 68; test1 maps from the day 9 on lie in a test4 map.
    ("test1 {:,during} test3", [("test1", _ones(1, 20))]),
    ("test1 {:,during} test4", [("test1", _ones(10, 20))]),
    # A test4 map [s, s + 3) with s = 9, 12, 15, 18 has a test1 map that starts
    # at s (days 9, 12, 15, 18), one that finishes with it (days 11, 14, 17;
    # the day 20 does not exist) and so on.
    ("test1 {:,starts} test4", [("test1", [10, 13, 16, 19])]),
    ("test1 {:,finishes} test4", [("test1", [12, 15, 18])]),
    ("test4 {:,finished} test1", [("test4", [41, 42, 43])]),
    ("test4 {:,started} test1", [("test4", [41, 42, 43, 44])]),
]


@pytest.mark.parametrize(("expression", "parts"), SELECTIONS)
def test_selection_of_vector_maps(vectors, expression, parts):
    assert _rows(vectors, expression) == _expected(*parts)


# Conditions on the temporal variables of test2 (map j starts on January
# j - 11, so start_day > 15 are the maps 27 to 40 and start_day < 20 the maps
# 21 to 30) and on td(test1), which is 1 for every test1 map.
CONDITIONS = [
    ("if(td(test1) == 1, test2)", [("test2", _ones(21, 31))]),
    ("if(start_year(test2) == 2013, test2)", [("test2", _ones(21, 40))]),
    (
        "if(start_year(test2) == 2013 && start_day(test2) < 20, test2)",
        [("test2", _ones(21, 30))],
    ),
    (
        "if(start_year(test2) == 2013 && start_day(test2) < 20"
        " && start_day(test2) > 15, test2)",
        [("test2", _ones(27, 30))],
    ),
    (
        "if(td(test1) == 1 || start_day(test2) < 20, test2)",
        [("test2", _ones(21, 31))],
    ),
    # Nested: of the test2 maps with start_day > 15 (27 to 40) those equal to
    # a test1 map (days 15 to 19)
    (
        "if(td(test1) == 1, if(start_day(test2) > 15, test2))",
        [("test2", _ones(27, 31))],
    ),
    # Else: the test2 maps from the 16th on, and the test1 maps equal to the
    # others (the days 9 to 14, test1_10 to test1_15)
    (
        "if(start_day(test2) > 15, test2, test1)",
        [("test2", _ones(27, 40)), ("test1", _ones(10, 15))],
    ),
    # With a relation beyond equal the else part also takes the maps that no
    # condition map is related to (t.select.md): the test1 maps of the days 0
    # to 8 lie outside the test2 maps and those of the days 9 to 14 lie in
    # (equal) a false test2 map, while the days 15 to 19 equal a true one.
    (
        "if({equal|during}, start_day(test2) > 15, test2, test1)",
        [("test2", _ones(27, 40)), ("test1", _ones(1, 15))],
    ),
    # No test1 map lies during a one-day test2 map, so only the else part
    # remains and it takes every test1 map as one that no condition map
    # is related to.
    (
        "if({during}, start_day(test2) > 15, test2, test1)",
        [("test1", _ones(1, 20))],
    ),
    (
        "if({during}, td(test1) == 1, test2, test1)",
        [("test1", _ones(1, 20))],
    ),
    # The hash operator: test1 maps with exactly one equal test2 map
    ("if(test1 {#} test2 == 1, test1)", [("test1", _ones(10, 20))]),
    # test3 maps (3 days) with more than one test2 map inside: [3k, 3k + 3)
    # holds the test2 days 9 to 28, so k = 3 to 9, which are test3_44 to test3_50
    ("if(test3 {#,contains} test2 > 1, test3)", [("test3", _ones(44, 50))]),
]


@pytest.mark.parametrize(("expression", "parts"), CONDITIONS)
def test_conditions_on_vector_maps(vectors, expression, parts):
    assert _rows(vectors, expression) == _expected(*parts)


# && binds more strongly than || in the core; the classic algebra evaluates
# conditions on temporal variables from left to right (t.select.md), so the
# same text means something else there. A condition on two datasets is true
# for the maps of either, and the then part takes the test2 maps equal to them.
PRECEDENCE = [
    # test2 days: always true || (days 16 to 19) is every map; from left to
    # right (true || < 20) && > 15 leaves the days 16 to 29
    (
        "if(start_year(test2) == 2013 || start_day(test2) < 20"
        " && start_day(test2) > 15, test2)",
        [("test2", _ones(21, 40))],
        [("test2", _ones(27, 40))],
    ),
    # (days 10 and 11) or (days 16 to 19) against ((days 10 to 19) and > 15),
    # the days 16 to 19
    (
        "if(start_day(test2) < 12 || start_day(test2) < 20"
        " && start_day(test2) > 15, test2)",
        [("test2", [21, 22, 27, 28, 29, 30])],
        [("test2", _ones(27, 30))],
    ),
    # test1 is true on the days 0 to 19, test2 on the days 16 to 19 (core): the
    # test2 maps equal to either are the days 9 to 19. From left to right,
    # (test1 or the test2 days before the 20th) and the days after the 15th
    # leave the days 15 to 19 (maps 27 to 31).
    (
        "if(td(test1) == 1 || start_day(test2) < 20 && start_day(test2) > 15, test2)",
        [("test2", _ones(21, 31))],
        [("test2", _ones(27, 31))],
    ),
]


@pytest.mark.parametrize(("expression", "core", "classic"), PRECEDENCE)
def test_and_binds_stronger_than_or_only_in_the_core(
    vectors, algebra, expression, core, classic
):
    parts = core if algebra == "core" else classic
    assert _rows(vectors, expression) == _expected(*parts)


def test_else_part_of_a_hash_condition_with_two_relations(vectors):
    """if({equal|during}, test3 {#,contains} test2 > 1, test3, test1)

    The then part is derived: the seven test3 maps with more than one test2
    map inside (test3_44 to test3_50, see above), each equal to itself. The
    else part is not: test1 maps of the days 0 to 8 lie in no condition map and
    so belong to it by the rule of the manual, but those of the days 9 to 19
    lie during true condition maps and are listed as well. The reference
    implementation, the classic profile and the core agree on this (measured
    19.10.2026 with grass.temporal.testing.expressions.outcome), so the
    result is pinned as it is and the question is in OFFENE_PUNKTE.
    """
    rows = _rows(
        vectors,
        "if({equal|during}, test3 {#,contains} test2 > 1, test3, test1)",
    )
    assert rows == _expected(("test3", _ones(44, 50)), ("test1", _ones(1, 20)))


EMPTY = [
    'test1 : buff_t(test2, "1 days")',
    "if(td(test1) == 2, test2)",
]


@pytest.mark.parametrize("expression", EMPTY)
def test_a_selection_without_maps_gives_the_result_the_algebra_makes(
    vectors, algebra, expression
):
    """The core registers nothing in a new, empty dataset and warns; the
    classic algebra creates no dataset at all for vector data (it does for
    raster data), as the reference implementation did, measured 19.10.2026"""
    tools = Tools(session=vectors, overwrite=True, consistent_return_value=True)
    tools.t_select(expression=f"empty_{algebra} = {expression}", type="stvds")
    created = "empty_%s@PERMANENT" % algebra in tools.t_list(type="stvds").text.split()
    assert created == (algebra == "core")
