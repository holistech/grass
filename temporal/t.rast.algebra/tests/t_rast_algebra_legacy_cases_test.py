"""The cases of the earlier gunittest files of t.rast.algebra

The cases are the expressions of the files test_raster_algebra_arithmetic,
_operators, _granularity, _fails and _granularity_fails, with the data of
their setUpClass: the datasets A to D of the algebra fixture in conftest.py
(daily and two-day intervals of January 2001) and, for the granularity cases,
the monthly datasets GA to GD below. The expected maps are those the old
tests asserted (number of maps, smallest and largest value, first start and
last end), written out per map: every map is constant, so a case lists
(start, end, value, value). The per-map values follow from the values of the
maps, which are given beside the cases.

Every case runs in the earlier implementation (reference), in the classic
profile and in the new algebra (core). CORE holds the cases where the core
differs, with the item of the section "Core and classic algebra" in the
manual of t.rast.algebra that documents the difference.
"""

import datetime
import re

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.expressions import RUNNERS, outcome
from grass.tools import Tools

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra


def span(start, end, value):
    """A constant map from start to end (dates), as (start, end, min, max)"""
    return (f"{start}T00:00:00", f"{end}T00:00:00", value, value)


def day(first, last, value):
    """A constant map from the day first to the day last of January 2001"""
    return span(f"2001-01-{first:02d}", f"2001-01-{last:02d}", value)


def month(first, last, value):
    """A constant map from the first of the month first to that of last"""
    return span(f"2001-{first:02d}-01", f"2001-{last:02d}-01", value)


# Datasets of the conftest: A a1..a4 = 1..4 on the days [1,2) .. [4,5);
# B b1 = 5 [1,3), b2 = 6 [3,5); C c1 = 7 [2,4); D d1..d3 = 8..10 [3,4) .. [5,6);
# singletmap = 99 [3,4) in no dataset; singlemap = 100 without time.
#
# The cases are (expression, options of the runner, expected maps or the name
# of the error class).
ARITHMETIC = [
    pytest.param(
        "A + (A {#, equal,l} A)",
        {},
        [day(1, 2, 2), day(2, 3, 3), day(3, 4, 4), day(4, 5, 5)],
        id="hash 1: a + one equal map",
    ),
    pytest.param(
        "A + td(A)",
        {},
        [day(1, 2, 2), day(2, 3, 3), day(3, 4, 4), day(4, 5, 5)],
        id="td 1: a + one day",
    ),
    pytest.param(
        "A / td(A)",
        {},
        [day(1, 2, 1), day(2, 3, 2), day(3, 4, 3), day(4, 5, 4)],
        id="td 2: a / one day",
    ),
    pytest.param(
        "A {+,equal} td(A)",
        {},
        [day(1, 2, 2), day(2, 3, 3), day(3, 4, 4), day(4, 5, 5)],
        id="td 3: operator with relation",
    ),
    pytest.param(
        "A {/, equal} td(A)",
        {},
        [day(1, 2, 1), day(2, 3, 2), day(3, 4, 3), day(4, 5, 4)],
        id="td 4: operator with relation",
    ),
    # start_doy(A, 0) is the day of the year of the start of a map: 1 to 4;
    # the condition a >= 3 holds for a3 and a4, so the others are 0
    pytest.param(
        "if(A >= 3, start_doy(A, 0), 0)",
        {},
        [day(1, 2, 0), day(2, 3, 0), day(3, 4, 3), day(4, 5, 4)],
        id="time function in a condition",
    ),
    # a2 to a4 start on or after January 2
    pytest.param(
        'if({equal}, start_date(A) >= "2001-01-02", A + A)',
        {},
        [day(2, 3, 4), day(3, 4, 6), day(4, 5, 8)],
        id="if 1: start date",
    ),
    pytest.param(
        "if({equal}, A#A == 1, A - A)",
        {},
        [day(1, 2, 0), day(2, 3, 0), day(3, 4, 0), day(4, 5, 0)],
        id="if 2: hash in a condition",
    ),
    # The condition holds for a1 and a2. a2 starts c1 (2 + 7), a1 has no
    # relation to c1. Of a3 and a4 only a3 finishes c1 (3 + 7).
    pytest.param(
        'if(start_date(A) < "2001-01-03" && A#A == 1,'
        " A{+, starts,l}C, A{+, finishes,l}C)",
        {},
        [day(2, 3, 9), day(3, 4, 10)],
        id="complex if",
    ),
    pytest.param(
        "A {*, equal} A {+, equal} A",
        {},
        [day(1, 2, 2), day(2, 3, 6), day(3, 4, 12), day(4, 5, 20)],
        id="arithmetic 1: left to right",
    ),
    pytest.param(
        "A {*, during} A {+, during} A", {}, [], id="arithmetic 2: empty result"
    ),
    pytest.param(
        "A / A + A*A/A",
        {},
        [day(1, 2, 2), day(2, 3, 3), day(3, 4, 4), day(4, 5, 5)],
        id="arithmetic 3: a / a + a",
    ),
    pytest.param(
        "map(singlemap) + A",
        {},
        [day(1, 2, 101), day(2, 3, 102), day(3, 4, 103), day(4, 5, 104)],
        id="map function 1",
    ),
    pytest.param(
        "A * map(singlemap)",
        {},
        [day(1, 2, 100), day(2, 3, 200), day(3, 4, 300), day(4, 5, 400)],
        id="map function 2",
    ),
    # b1 contains a1 and a2: 5 + 1 + 2; b2 contains a3 and a4: 6 + 3 + 4
    pytest.param(
        "B {+,contains,l} A", {}, [day(1, 3, 8), day(3, 5, 13)], id="relation 1: sum"
    ),
    pytest.param(
        "B {*,contains,l} A",
        {},
        [day(1, 3, 10), day(3, 5, 72)],
        id="relation 2: product",
    ),
    # Right reference: the old and classic result is b + all contained maps in
    # every map of A; the core gives one map per pair (b1 + a1, b1 + a2,
    # b2 + a3, b2 + a4), see CORE.
    pytest.param(
        "B {+,contains,r} A",
        {},
        [day(1, 2, 8), day(2, 3, 8), day(3, 4, 13), day(4, 5, 13)],
        id="relation 4: right reference",
    ),
    # tmap(singletmap) [3,4) is equal to a3, precedes a4 and follows a2:
    # 99 + 3 + 4 + 2, then + 100
    pytest.param(
        "tmap(singletmap) {+,equal| precedes| follows,l} A + map(singlemap)",
        {},
        [day(3, 4, 208)],
        id="relation 5: several relations",
    ),
]

# Item 4 "Right reference" of the section "Core and classic algebra" in
# t.rast.algebra.md: one map per related pair with the time stamp of the right
# map and the value of this pair.
CORE = {
    "relation 4: right reference": [
        day(1, 2, 6),
        day(2, 3, 7),
        day(3, 4, 9),
        day(4, 5, 10),
    ],
}

OPERATORS = [
    # B == 5 holds for b1 only. a1 and a2 are in b1 (a - 1), a3 and a4 in b2
    # (a + 1)
    pytest.param(
        "if({contains}, B == 5, A - 1,  A + 1)",
        {},
        [day(1, 2, 0), day(2, 3, 1), day(3, 4, 4), day(4, 5, 5)],
        id="conditional in the time dimension",
    ),
    pytest.param("A {+,equal,i} B", {}, [], id="intersection 1: nothing equal"),
    # A during B includes starts and finishes: a1 and a2 in b1, a3 and a4 in
    # b2. The intersection of the extents is the extent of a.
    pytest.param(
        "A {+,during,i} B",
        {},
        [day(1, 2, 6), day(2, 3, 7), day(3, 4, 9), day(4, 5, 10)],
        id="intersection 2: during",
    ),
    pytest.param(
        "A {+,starts,i} B",
        {},
        [day(1, 2, 6), day(3, 4, 9)],
        id="intersection 3: starts",
    ),
    pytest.param(
        "A {+,finishes,intersect} B",
        {},
        [day(2, 3, 7), day(4, 5, 10)],
        id="intersection 4: finishes",
    ),
    pytest.param(
        "A {+,starts|finishes,i} B",
        {},
        [day(1, 2, 6), day(2, 3, 7), day(3, 4, 9), day(4, 5, 10)],
        id="intersection 5: starts or finishes",
    ),
    # b1 [1,3) overlaps c1 [2,4): union [1,4), 5 + 7
    pytest.param(
        "B {+,overlaps,u} C", {}, [day(1, 4, 12)], id="intersection 6: overlaps"
    ),
    # b2 [3,5) is overlapped by c1 [2,4): union [2,5), 6 + 7
    pytest.param(
        "B {+,overlapped,u} C", {}, [day(2, 5, 13)], id="intersection 7: overlapped"
    ),
    # buff_t(C, "1 day") is [1,5): every map of A is in it
    pytest.param(
        'A {+,during,l} buff_t(C, "1 day") ',
        {},
        [day(1, 2, 8), day(2, 3, 9), day(3, 4, 10), day(4, 5, 11)],
        id="intersection 8: buffered",
    ),
    # a2 + ... : a map with both neighbours is a2 (a1 + a3) and a3 (a2 + a4)
    pytest.param(
        "A[-1] + A[1]",
        {},
        [day(2, 3, 4), day(3, 4, 6)],
        id="neighbors 1",
    ),
    pytest.param(
        "A[0,0,-1] + A[0,0,1]",
        {},
        [day(2, 3, 4), day(3, 4, 6)],
        id="neighbors 2",
    ),
    pytest.param("tmap(singletmap)", {}, [day(3, 4, 99)], id="tmap 1"),
    pytest.param("tmap(singletmap) + 1", {}, [day(3, 4, 100)], id="tmap 2"),
    pytest.param(
        "A : A",
        {},
        [day(1, 2, 1), day(2, 3, 2), day(3, 4, 3), day(4, 5, 4)],
        id="select 1: one dataset",
    ),
    # a3 and a4 are equal to d1 and d2
    pytest.param(
        "A : D", {}, [day(3, 4, 3), day(4, 5, 4)], id="select 2: two datasets"
    ),
    # a2 and a3 are in c1 [2,4) (starts, finishes), so a1 and a4 remain
    pytest.param(
        "A {!:,during} C", {}, [day(1, 2, 1), day(4, 5, 4)], id="inverse selection"
    ),
    # Disjoint union: the maps of A in b1 get the extent of b1, and so on
    pytest.param(
        "A {:,during,d} B",
        {},
        [day(1, 3, 1), day(1, 3, 2), day(3, 5, 3), day(3, 5, 4)],
        id="select with disjoint union",
    ),
    # a2 and a3 are in c1: right reference, the extent of c1
    pytest.param(
        "A {:,equal|during,r} C",
        {},
        [day(2, 4, 2), day(2, 4, 3)],
        id="select with right reference",
    ),
    # a3 and a4 have one equal map of D each
    pytest.param(
        "if(A # D == 1, A)", {}, [day(3, 4, 3), day(4, 5, 4)], id="hash 1: condition"
    ),
    pytest.param(
        "A # D", {}, [day(3, 4, 1), day(4, 5, 1)], id="hash 2: count of equal maps"
    ),
    # c1 contains a2 and a3
    pytest.param("C {#,contains} A", {}, [day(2, 4, 2)], id="hash 3: contained maps"),
    pytest.param(
        "if({during},A # D == 1, C {#,contains} A)",
        {},
        [day(2, 4, 2)],
        id="hash 4: in a condition",
    ),
]

# What the old tests asserted besides the maps: check_temporal_topology() and
# get_granularity() of the result, by expression
SHAPE = {
    "A + td(A)": (True, "1 day"),
    "map(singlemap) + A": (True, "1 day"),
    "A * map(singlemap)": (True, "1 day"),
    "B {+,contains,l} A": (True, "2 days"),
    "B {*,contains,l} A": (True, "2 days"),
    "if({contains}, B == 5, A - 1,  A + 1)": (True, "1 day"),
    "tmap(singletmap)": (True, "1 day"),
    "tmap(singletmap) + 1": (True, "1 day"),
    "A : A": (True, "1 day"),
    "A : D": (True, "1 day"),
    "A {!:,during} C": (True, "1 day"),
    "A {:,during,d} B": (False, "2 days"),
    "A {:,equal|during,r} C": (False, "2 days"),
    "if(A # D == 1, A)": (True, "1 day"),
    "A # D": (True, "1 day"),
    "C {#,contains} A": (True, "2 days"),
    "if({during},A # D == 1, C {#,contains} A)": (True, "2 days"),
}


@pytest.fixture(scope="module")
def monthly(algebra):
    """The monthly datasets of test_raster_algebra_granularity

    GA ga1..ga6 = 1..6 on the months January to June 2001; GB gb1 = 7 for
    January to March, gb2 = 8 for April to June; GC gc1 = 9 for the year;
    GD gd1..gd3 = 10, 11, 12 on five days from January 1, March 1 and
    May 1; GO go1 = 7 for February and March, go2 = 8 for March and April;
    gsingle = 99 for March.
    """
    tools = Tools(session=algebra.session, overwrite=True, quiet=True)

    def date(month_number, day_number=1, year=2001):
        return datetime.datetime(year, month_number, day_number)

    create_stds(
        tools,
        "strds",
        "GA",
        [MapSpec(f"ga{k}", k, date(k), date(k + 1)) for k in range(1, 7)],
    )
    create_stds(
        tools,
        "strds",
        "GB",
        [MapSpec("gb1", 7, date(1), date(4)), MapSpec("gb2", 8, date(4), date(7))],
    )
    create_stds(tools, "strds", "GC", [MapSpec("gc1", 9, date(1), date(1, 1, 2002))])
    create_stds(
        tools,
        "strds",
        "GD",
        [
            MapSpec(f"gd{k}", 9 + k, date(m), date(m, 6))
            for k, m in enumerate((1, 3, 5), 1)
        ],
    )
    # Two maps that overlap, so the dataset has no valid temporal topology
    create_stds(
        tools,
        "strds",
        "GO",
        [MapSpec("go1", 7, date(2), date(4)), MapSpec("go2", 8, date(3), date(5))],
    )
    tools.r_mapcalc(expression="gsingle = 99")
    tools.t_register(
        type="raster",
        maps="gsingle",
        start="2001-03-01",
        end="2001-04-01",
    )
    return algebra


def days_of(month_number, first, last, value):
    """One-day maps from the day first to the day last of a month of 2001"""
    return [
        span(
            f"2001-{month_number:02d}-{number:02d}",
            f"2001-{month_number:02d}-{number + 1:02d}",
            value,
        )
        for number in range(first, last + 1)
    ]


GRANULARITY = [
    # C holds 9 all year, so the condition holds in each month of A
    pytest.param(
        "if(GC == 9,  GA - 1)",
        {"granularity": True},
        [month(m, m + 1, m - 1) for m in range(1, 7)],
        id="g 1: condition on the year",
    ),
    # The common granule of A and D is a day. D holds 10, 11, 12 on the days
    # 1 to 5 of January, March and May: where d is 11 (March) the value is
    # a3 - 1 = 2, elsewhere a + 1: a1 + 1 = 2 in January, a5 + 1 = 6 in May.
    pytest.param(
        "if(GD == 11,  GA - 1, GA + 1)",
        {"granularity": True},
        days_of(1, 1, 5, 2) + days_of(3, 1, 5, 2) + days_of(5, 1, 5, 6),
        id="g 2: condition on days",
    ),
    pytest.param(
        "GA + (GA # GA)",
        {"granularity": True},
        [month(m, m + 1, m + 1) for m in range(1, 7)],
        id="g hash 1",
    ),
    # td of the selection is one day (the granule); a is 1, 3, 5 in the three
    # periods of D
    pytest.param(
        "GA + td(GA:GD)",
        {"granularity": True},
        days_of(1, 1, 5, 2) + days_of(3, 1, 5, 4) + days_of(5, 1, 5, 6),
        id="g td 1",
    ),
    pytest.param(
        'if(start_date(GA) >= "2001-02-01", GA + GA)',
        {"granularity": True},
        [month(m, m + 1, 2 * m) for m in range(2, 7)],
        id="g if 1: start date",
    ),
    pytest.param(
        "if(GA#GA == 1, GA - GA)",
        {"granularity": True},
        [month(m, m + 1, 0) for m in range(1, 7)],
        id="g if 2: hash in a condition",
    ),
    # c is 9: January and February (condition true) a + 9 = 10, 11; the other
    # months a - 9 = -6 to -3
    pytest.param(
        'if(start_date(GA) < "2001-03-01" && GA#GA == 1, GA+GC, GA-GC)',
        {"granularity": True},
        [month(1, 2, 10), month(2, 3, 11)]
        + [month(m, m + 1, m - 9) for m in range(3, 7)],
        id="g complex if",
    ),
    # Within the days of D (the selection) a neighbour is the map of the day
    # before and the day after. January 1 has no day before. March 1: a2 + a3
    # = 5, March 2 to 5: 3 + 3, May 1: a4 + a5 = 9, May 2 to 5: 5 + 5.
    pytest.param(
        "(GA[0,0,-1] : GD) + (GA[0,0,1] : GD)",
        {"granularity": True},
        days_of(1, 2, 5, 2)
        + days_of(3, 1, 1, 5)
        + days_of(3, 2, 5, 6)
        + days_of(5, 1, 1, 9)
        + days_of(5, 2, 5, 10),
        id="g temporal neighbors",
    ),
    pytest.param(
        "GA + map(gsingle)",
        {"granularity": True},
        [month(m, m + 1, m + 99) for m in range(1, 7)],
        id="g map",
    ),
    # March: tmap [Mar 1, Apr 1) + ga3 + 99
    pytest.param(
        "tmap(gsingle) + GA + map(gsingle)",
        {"granularity": True},
        [month(3, 4, 201)],
        id="g tmap and map",
    ),
]

GRANULARITY_SHAPE = {
    "if(GC == 9,  GA - 1)": (True, "1 month"),
    "if(GD == 11,  GA - 1, GA + 1)": (True, "1 day"),
    "GA + td(GA:GD)": (True, "1 day"),
    "tmap(gsingle) + GA + map(gsingle)": (True, "1 month"),
}


GRANULARITY_ONLY = {"granularity": True}

# The cases of test_raster_algebra_fails and _granularity_fails that an
# expression can show; the missing basename is an option of the tool, tested in
# t_rast_algebra_options_test.py. The old test calls "R == ..." a syntax
# error, here the doubled sign is the expression. The old tests only asked for
# a failure (assertModuleFail). In granularity mode the pre-pass that samples
# the datasets fails first, with "Unable to process the expression in
# granularity algebra mode" (FatalError) in all three runners: for a missing
# brace, for operators with temporal relations in curly brackets, which the
# manual rules out in this mode, and for maps that overlap (GO), checked
# 19.10.2026.
FAILS = [
    pytest.param(
        "= A {+,equal| precedes| follows,l} B",
        {},
        "SyntaxError",
        id="double equal sign",
    ),
    pytest.param("NoSTRDS + NoSTRDS", {}, "FatalError", id="unknown dataset"),
    pytest.param(
        "strds(A) + strds(B)", {}, "SyntaxError", id="strds() in the raster algebra"
    ),
    pytest.param(
        "A {+,equal| precedes| follows,l A",
        GRANULARITY_ONLY,
        "FatalError",
        id="g: brace not closed",
    ),
    pytest.param(
        "A {+,equal| precedes| follows,l} A",
        GRANULARITY_ONLY,
        "FatalError",
        id="g: topological operator",
    ),
    pytest.param("= A + A", GRANULARITY_ONLY, "SyntaxError", id="g: double equal sign"),
    pytest.param(
        "NoSTRDS + NoSTRDS", GRANULARITY_ONLY, "FatalError", id="g: unknown dataset"
    ),
    pytest.param("GO + GO", GRANULARITY_ONLY, "FatalError", id="g: overlapping maps"),
]


def run(runner, expression, options, name):
    return outcome(KIND, expression, RUNNERS[runner], basename=name, **options)


def maps_of(result):
    assert "error" not in result, result
    return sorted(
        (start, end, low, high) for _, start, end, low, high in result["maps"]
    )


def check_shape(result_name, shape):
    stds = tgis.open_old_stds(result_name, "strds")
    assert (stds.check_temporal_topology(), stds.get_granularity()) == shape


def check(runner, request, expression, options, expected, shapes):
    if runner == "core":
        expected = CORE.get(request.node.callspec.id.rsplit("-", 1)[0], expected)
    result = run(runner, expression, options, f"lc{runner[:2]}")
    assert maps_of(result) == sorted(expected)
    if expression in shapes and expected:
        check_shape(f"Rlc{runner[:2]}", shapes[expression])


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "expected"), ARITHMETIC)
def test_arithmetic_cases(algebra, request, runner, expression, options, expected):
    check(runner, request, expression, options, expected, SHAPE)


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "expected"), OPERATORS)
def test_operator_cases(algebra, request, runner, expression, options, expected):
    check(runner, request, expression, options, expected, SHAPE)


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "expected"), GRANULARITY)
def test_granularity_cases(monthly, request, runner, expression, options, expected):
    check(runner, request, expression, options, expected, GRANULARITY_SHAPE)


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "error"), FAILS)
def test_failing_cases(monthly, runner, expression, options, error):
    assert run(runner, expression, options, f"lf{runner[:2]}")["error"] == error


def test_every_shape_belongs_to_a_case():
    # SHAPE is looked up by the expression; a key that matches no case would
    # be skipped without notice.
    def expressions(cases):
        return {case.values[0] for case in cases}

    assert set(SHAPE) <= expressions(ARITHMETIC + OPERATORS)
    assert set(GRANULARITY_SHAPE) <= expressions(GRANULARITY)


# The old tests ran the conditional case and every granularity case also with
# the flag -d, which prints the computation instead of running it; they only
# asked that this run succeeds.
PRINT_RUNS = [
    pytest.param("if({contains}, B == 5, A - 1,  A + 1)", "d", id="conditional"),
    *(pytest.param(case.values[0], "gd", id=case.id) for case in GRANULARITY),
]


@pytest.mark.real_io
@pytest.mark.parametrize(("expression", "flags"), PRINT_RUNS)
def test_the_print_flag_runs_the_old_cases(monthly, expression, flags):
    env = {**monthly.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tool = Tools(env=env, consistent_return_value=True)
    printed = tool.t_rast_algebra(
        expression=f"R = {expression}", basename="r", flags=flags
    ).stdout
    assert printed.strip()


# The printed r.mapcalc calls of test_simple_arithmetic_time_function_expressions
# (core) and _classic: the time function is evaluated for every map and
# replaced by its value (the day of the year of the start: 1 to 4), so the
# condition of a map reads its own value. "..." stands for text that varies.
PRINTED = [
    pytest.param(
        "d",
        '...r_2001_01_01"=if(((...a1@...>=3)!=0),1,0)'
        '...r_2001_01_02"=if(((...a2@...>=3)!=0),2,0)'
        '...r_2001_01_03"=if(((...a3@...>=3)!=0),3,0)'
        '...r_2001_01_04"=if(((...a4@...>=3)!=0),4,0)...',
        id="core",
    ),
    pytest.param(
        "dc",
        "...r_2001_01_01=if(a1@...>=3,1,0)...r_2001_01_02=if(a2@...>=3,2,0)"
        "...r_2001_01_03=if(a3@...>=3,3,0)...r_2001_01_04=if(a4@...>=3,4,0)...",
        id="classic",
    ),
]


@pytest.mark.real_io
@pytest.mark.parametrize(("flags", "pattern"), PRINTED)
def test_the_printed_calls_of_a_time_function(algebra, flags, pattern):
    env = {**algebra.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tool = Tools(env=env, consistent_return_value=True)
    printed = tool.t_rast_algebra(
        expression="R = if(A >= 3, start_doy(A, 0), 0)",
        basename="r",
        flags=flags,
        suffix="gran",
    ).stdout
    # pprint splits a long expression string in two quoted parts after a name
    text = "".join(printed.split()).replace("''", "")
    regex = ".*".join(re.escape(part) for part in pattern.split("..."))
    assert re.fullmatch(regex, text, re.DOTALL)
