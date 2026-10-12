"""Test the temporal functions td(), buff_t(), tshift(), tsnap(), tmap(),
merge() and the neighbourhood modifier of t.rast.algebra

The datasets are described in the algebra fixture in conftest.py.
"""

import datetime

import pytest


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A + td(A)", [(1, 2, 2), (2, 3, 3), (3, 4, 4), (4, 5, 5)]),
        ("A / td(A)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ("A {+,equal} td(A)", [(1, 2, 2), (2, 3, 3), (3, 4, 4), (4, 5, 5)]),
        ("A {*,equal,l} td(A)", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        # td() is the number of days of the interval
        ("B + td(B)", [(1, 3, 7), (3, 5, 8)]),
        ("B * td(B)", [(1, 3, 10), (3, 5, 12)]),
        # td(D) only exists where D has a map equal to the map of A
        ("A + td(D)", [(3, 4, 4), (4, 5, 5)]),
        ("A + td(B)", []),
    ],
)
def test_td_in_arithmetic(algebra, expression, expected):
    """td(A) returns the length of the intervals in days and is combined
    with the maps that are equal in time"""
    assert algebra.triples(expression) == expected


@pytest.mark.parametrize(("expression", "count"), [("E + td(E)", 4), ("I + td(I)", 3)])
def test_td_of_time_instants_is_null(algebra, expression, count):
    """Instants have no length, so td() is null and so is the sum; such maps
    are registered only with register_null"""
    assert algebra.run(expression) == []
    rows = algebra.run(expression, register_null=True)
    assert [row.min for row in rows] == [None] * count


def test_buff_t_buffers_both_sides(algebra):
    """buff_t(B, "1 day") extends every interval by one day on each side"""
    rows = algebra.run('buff_t(B, "1 day")')
    assert [(row.start, row.end, row.min) for row in rows] == [
        (datetime.datetime(2000, 12, 31), algebra.day(4), 5),
        (algebra.day(2), algebra.day(6), 6),
    ]


def test_buff_t_on_time_instants(algebra):
    """An instant becomes an interval around the instant"""
    rows = algebra.run('buff_t(I, "1 day")')
    assert [(row.start.day, row.end.day, row.min) for row in rows] == [
        (31, 2, 1),
        (1, 3, 2),
        (2, 4, 3),
    ]


def test_buff_t_selection_with_buffered_dataset(algebra):
    """C [2,4] buffered by a day is [1,5]; a1 starts and a4 finishes it"""
    assert algebra.values('A {:,during} buff_t(C, "1 day")') == [1, 2, 3, 4]
    assert algebra.values('A {+,during,l} buff_t(C, "1 day")') == [8, 9, 10, 11]


def test_buff_t_of_expression(algebra):
    """buff_t() can wrap a selection: a3 [3,4] and a4 [4,5] are equal to D"""
    assert algebra.triples('buff_t(A {:,equal} D, "1 day")') == [
        (2, 5, 3),
        (3, 6, 4),
    ]


def test_buff_t_without_size_keeps_extent(algebra):
    """A buffer of zero days changes nothing"""
    assert algebra.triples('buff_t(A, "0 days")') == [
        (1, 2, 1),
        (2, 3, 2),
        (3, 4, 3),
        (4, 5, 4),
    ]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('tshift(A, "1 day")', [(2, 3, 1), (3, 4, 2), (4, 5, 3), (5, 6, 4)]),
        ('tshift(A, "10 days")', [(11, 12, 1), (12, 13, 2), (13, 14, 3), (14, 15, 4)]),
        ('tshift(A, "0 days")', [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ('tshift(I, "1 day")', [(2, None, 1), (3, None, 2), (4, None, 3)]),
        # the shifted maps are equal to the next map of A
        ('tshift(A, "1 day") + A', [(2, 3, 3), (3, 4, 5), (4, 5, 7)]),
        ('tshift(A {:,equal} D, "1 day")', [(4, 5, 3), (5, 6, 4)]),
        ('A {+,equal,l} tshift(A, "1 day")', [(2, 3, 3), (3, 4, 5), (4, 5, 7)]),
    ],
)
def test_tshift(algebra, expression, expected):
    """tshift() moves the time stamps of every map by the granule"""
    assert algebra.triples(expression) == expected


def test_tshift_backwards_and_by_months(algebra):
    """Negative and calendar granules work"""
    backwards = algebra.run('tshift(A, "-1 day")')
    assert [(row.start, row.end, row.min) for row in backwards][:2] == [
        (datetime.datetime(2000, 12, 31), algebra.day(1), 1),
        (algebra.day(1), algebra.day(2), 2),
    ]
    months = algebra.run('tshift(A, "1 month")')
    assert [(row.start.month, row.start.day, row.min) for row in months] == [
        (2, 1, 1),
        (2, 2, 2),
        (2, 3, 3),
        (2, 4, 4),
    ]


def test_tsnap_keeps_a_gapless_dataset(algebra):
    """A dataset without gaps is not changed"""
    assert algebra.triples("tsnap(A)") == [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]


def test_tsnap_turns_instants_into_intervals(algebra):
    """Each time instant lasts until the next one; the last one gets the
    granularity of the dataset"""
    assert algebra.triples("tsnap(I)") == [(1, 2, 1), (2, 3, 2), (3, 4, 3)]


def test_tsnap_closes_gaps(algebra):
    """The last map before a gap is extended up to the next map"""
    assert algebra.triples('tsnap(merge(A, tshift(A, "10 days")))') == [
        (1, 2, 1),
        (2, 3, 2),
        (3, 4, 3),
        (4, 11, 4),
        (11, 12, 1),
        (12, 13, 2),
        (13, 14, 3),
        (14, 15, 4),
    ]


def test_merge_joins_datasets(algebra):
    """merge() keeps the maps of both datasets, also with equal time stamps"""
    assert algebra.triples("merge(A, D)") == [
        (1, 2, 1),
        (2, 3, 2),
        (3, 4, 3),
        (3, 4, 8),
        (4, 5, 4),
        (4, 5, 9),
        (5, 6, 10),
    ]
    assert algebra.triples("merge(A, B)") == [
        (1, 2, 1),
        (1, 3, 5),
        (2, 3, 2),
        (3, 4, 3),
        (3, 5, 6),
        (4, 5, 4),
    ]


def test_merge_nested_and_with_shift(algebra):
    """merge() of merge() and of a shifted dataset"""
    assert len(algebra.run("merge(B, merge(A, D))")) == 9
    assert algebra.values('merge(A, tshift(A, "10 days"))') == [1, 2, 3, 4, 1, 2, 3, 4]


def test_merged_dataset_can_be_selected(algebra):
    """The result of merge() takes part in later temporal operations"""
    assert algebra.values("merge(A, B) {:,equal} A") == [1, 2, 3, 4]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("tmap(singletmap)", [(3, 4, 99)]),
        ("tmap(singletmap) + 1", [(3, 4, 100)]),
        ("tmap(singletmap) * 2", [(3, 4, 198)]),
        ("A {:,equal} tmap(singletmap)", [(3, 4, 3)]),
        ("A {:,during} tmap(singletmap)", []),
        ("tmap(singletmap) {:,equal} A", [(3, 4, 99)]),
        ("tmap(singletmap) {+,equal,l} A", [(3, 4, 102)]),
        ("D {+,equal,l} tmap(singletmap)", [(3, 4, 107)]),
        # 99 + a3 (equal) + a2 (follows) + a4 (precedes) + 100
        (
            "tmap(singletmap) {+,equal|precedes|follows,l} A + map(singlemap)",
            [(3, 4, 208)],
        ),
        (
            'A {:,during} buff_t(tmap(singletmap), "1 day")',
            [(2, 3, 2), (3, 4, 3), (4, 5, 4)],
        ),
    ],
)
def test_tmap(algebra, expression, expected):
    """tmap() puts a single map with time stamp into the algebra"""
    assert algebra.triples(expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A[1]", [(1, 2, 2), (2, 3, 3), (3, 4, 4)]),
        ("A[2]", [(1, 2, 3), (2, 3, 4)]),
        ("A[-1]", [(2, 3, 1), (3, 4, 2), (4, 5, 3)]),
        ("A[-2]", [(3, 4, 1), (4, 5, 2)]),
        ("A[0]", [(1, 2, 1), (2, 3, 2), (3, 4, 3), (4, 5, 4)]),
        ("A[5]", []),
        ("A[-1] + A[1]", [(2, 3, 4), (3, 4, 6)]),
        ("A[0,0,1]", [(1, 2, 2), (2, 3, 3), (3, 4, 4)]),
        ("A[0,0,-1]", [(2, 3, 1), (3, 4, 2), (4, 5, 3)]),
        ("A[0,0,-1] + A[0,0,1]", [(2, 3, 4), (3, 4, 6)]),
        ("A[1] * 2 + A", [(1, 2, 5), (2, 3, 8), (3, 4, 11)]),
    ],
)
def test_temporal_neighbour(algebra, expression, expected):
    """A[n] is the n-th successor, A[-n] the n-th predecessor; the result has
    the time stamp of the current map, maps without neighbour are dropped"""
    assert algebra.triples(expression) == expected


def test_temporal_neighbour_in_condition(algebra):
    """The neighbour modifier can be used in conditions; without else a2,
    whose predecessor a1 is not greater than 1, is null and left out"""
    assert algebra.triples("if(A[-1] > 1, A)") == [(3, 4, 3), (4, 5, 4)]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # one argument: temporal offset
        ("G[1]", [(1, 2, 10, 30)]),
        # two arguments: row and column offset; cells outside are NULL
        ("G[0,1]", [(1, 2, 2, 3), (2, 3, 20, 30)]),
        ("GR[1,0]", [(1, 2, 2, 3)]),
        ("GR[-1,0]", [(1, 2, 1, 2)]),
        ("GR[0,1]", [(1, 2, 1, 3)]),
        # three arguments: row, column and temporal offset
        ("G[0,0,1]", [(1, 2, 10, 30)]),
        ("G[0,1,0]", [(1, 2, 2, 3), (2, 3, 20, 30)]),
        ("G[1,0,0]", [(1, 2, 1, 3), (2, 3, 10, 30)]),
        ("G[0,1,1]", [(1, 2, 20, 30)]),
        ("GR[1,1,0]", [(1, 2, 2, 3)]),
    ],
)
def test_spatial_and_temporal_neighbour(algebra, expression, expected):
    """The order of three offsets is row, column, time as in r.mapcalc; the
    manual describes strds[t,r,c] instead"""
    rows = algebra.run(expression)
    assert [(row.start.day, row.end.day, row.min, row.max) for row in rows] == expected


def test_neighbour_values_outside_are_null(algebra):
    """A row shift leaves one row of three NULL, a cell shift one column"""
    tools = algebra.tools
    for expression, null_cells in [("GR[1,0]", 3), ("G[0,1]", 3), ("GR[1,1]", 5)]:
        rows = algebra.run(expression)
        assert rows
        name = tools.t_rast_list(input="R", columns="name", format="json")["data"][0][
            "name"
        ]
        stats = tools.r_univar(map=name, flags="g").keyval
        assert int(stats["null_cells"]) == null_cells
