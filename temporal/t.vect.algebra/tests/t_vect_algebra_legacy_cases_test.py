"""The cases of the earlier gunittest file of t.vect.algebra

The cases are those of test_vector_algebra.py, on the datasets of its
setUpClass: A a1..a4 on the days [1,2) .. [4,5) of January 2001, B b1, b2 on
[1,3) and [3,5), C c1 on [2,4), D d1..d3 on [3,4) .. [5,6), every map 20 random
points (seeds 1, 1, 1, 1 for A, 2, 2 for B, 3 for C and 4, 4, 4 for D, so the
maps of a dataset are copies of each other). The format is that of
t_rast_algebra_legacy_cases_test.py, with the numbers of points, lines and
areas of a map in place of its minimum and maximum: (start, end, points, lines,
areas). Every case runs in the reference implementation
(grass.temporal.classic), in the classic profile and in the core; the three
agree on all of them, so there is no CORE table.

The old test asserted the numbers of areas of a dataset, not of a map. Where a
case yields maps built from identical inputs the sum divides equally; the
overlay of buffers is the one case where this is a claim about geometry: all
maps of A (and of B) are copies, so the intersection of each pair is the same.
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, register_stds
from grass.temporal.testing.differential import RUNNERS, outcome
from grass.tools import Tools

KIND = "vector"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra


def day(first, last, points=0, areas=0):
    """A map from the day first to the day last of January 2001"""
    return (
        f"2001-01-{first:02d}T00:00:00",
        f"2001-01-{last:02d}T00:00:00",
        points,
        0,
        areas,
    )


# The old test summed 80 points for four maps, 40 for two.
CASES = [
    pytest.param(
        "A : A",
        {},
        [day(1, 2, 20), day(2, 3, 20), day(3, 4, 20), day(4, 5, 20)],
        id="select one dataset",
    ),
    # a2 and a3 are in c1 [2,4) (starts, finishes)
    pytest.param(
        "A {:,during} C", {}, [day(2, 3, 20), day(3, 4, 20)], id="select with during"
    ),
    # The buffer of each of the 20 points is one area (80 areas in four maps)
    pytest.param(
        "buff_p(A,0.5)",
        {},
        [
            day(1, 2, areas=20),
            day(2, 3, areas=20),
            day(3, 4, areas=20),
            day(4, 5, areas=20),
        ],
        id="buffer of points",
    ),
    # The old test counted 20 areas in the four maps: the large buffers merge
    # to five areas in each copy
    pytest.param(
        "buff_a(buff_p(A,1),10)",
        {},
        [
            day(1, 2, areas=5),
            day(2, 3, areas=5),
            day(3, 4, areas=5),
            day(4, 5, areas=5),
        ],
        id="buffer of areas",
    ),
    # a3 and a4 meet d1 and d2: 6 areas in two maps
    pytest.param(
        "buff_p(A,2) & buff_p(D,2)",
        {},
        [day(3, 4, areas=3), day(4, 5, areas=3)],
        id="overlay of equal maps",
    ),
    # Right reference: a1 and a2 in b1, a3 and a4 in b2 with the extent of b
    # (8 areas in four maps)
    pytest.param(
        "buff_p(A,1.5) {&,during,r} buff_p(B,1.5)",
        {},
        [
            day(1, 3, areas=2),
            day(1, 3, areas=2),
            day(3, 5, areas=2),
            day(3, 5, areas=2),
        ],
        id="overlay with right reference",
    ),
    # a2 and a3 in c1, left reference (8 areas in two maps)
    pytest.param(
        "buff_p(A,2.5) {&,during,l} buff_p(C,2.5)",
        {},
        [day(2, 3, areas=4), day(3, 4, areas=4)],
        id="overlay with left reference",
    ),
]

# What the old tests asserted besides the maps: check_temporal_topology() and
# get_granularity() of the result, by expression
SHAPE = {
    "A : A": (True, "1 day"),
    "A {:,during} C": (True, "1 day"),
    "buff_p(A,0.5)": (True, "1 day"),
    "buff_a(buff_p(A,1),10)": (True, "1 day"),
    "buff_p(A,2) & buff_p(D,2)": (True, "1 day"),
    "buff_p(A,1.5) {&,during,r} buff_p(B,1.5)": (False, "2 days"),
    "buff_p(A,2.5) {&,during,l} buff_p(C,2.5)": (True, "1 day"),
}


@pytest.fixture(scope="module")
def legacy(vector_series):
    """The datasets A to D of the old setUpClass in the session of the module"""
    tools = Tools(session=vector_series.session, overwrite=True, quiet=True)
    previous = tools.g_region(flags="g").keyval
    tools.g_region(n=80, s=0, e=120, w=0, res=10)
    try:
        datasets = {
            "A": [("a1", 1, 1, 2), ("a2", 1, 2, 3), ("a3", 1, 3, 4), ("a4", 1, 4, 5)],
            "B": [("b1", 2, 1, 3), ("b2", 2, 3, 5)],
            "C": [("c1", 3, 2, 4)],
            "D": [("d1", 4, 3, 4), ("d2", 4, 4, 5), ("d3", 4, 5, 6)],
        }
        for name, maps in datasets.items():
            for vector, seed, _, _ in maps:
                tools.v_random(output=vector, npoints=20, seed=seed)
            register_stds(
                tools,
                "stvds",
                name,
                [
                    MapSpec(
                        vector,
                        None,
                        datetime.datetime(2001, 1, start),
                        datetime.datetime(2001, 1, end),
                    )
                    for vector, _, start, end in maps
                ],
            )
    finally:
        tools.g_region(
            n=previous["n"],
            s=previous["s"],
            e=previous["e"],
            w=previous["w"],
            res=previous["nsres"],
        )
    return vector_series


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "options", "expected"), CASES)
def test_cases(legacy, runner, expression, options, expected):
    result = outcome(
        KIND, expression, RUNNERS[runner], basename=f"lv{runner[:2]}", **options
    )
    assert "error" not in result, result
    assert sorted(tuple(row[1:]) for row in result["maps"]) == sorted(expected)
    result_set = tgis.open_old_stds(f"Rlv{runner[:2]}", "stvds")
    assert (
        result_set.check_temporal_topology(),
        result_set.get_granularity(),
    ) == SHAPE[expression]


def test_every_case_has_one_shape():
    # SHAPE is looked up by the expression of each case.
    assert set(SHAPE) == {case.values[0] for case in CASES}
