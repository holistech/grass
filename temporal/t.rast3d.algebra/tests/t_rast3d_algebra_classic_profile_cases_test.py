"""Cases where the classic profile once differed from the classic algebra

As t_rast_algebra_classic_profile_cases_test.py, for 3D raster maps, on the
datasets of the expression fuzzer: the classic profile (what -c runs) and the
classic algebra of the parser classes, the reference, must register the same
maps or fail with the same class of error.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.expressions import RUNNERS, compare, outcome, prepare

KIND = "raster3d"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# A partner whose box does not meet still sets the time of the result, with
# or without the spatial flag, and with null maps registered or not.
PARTNER_TIMES = [
    'A {+,equal|finishes,u} merge(B, buff_t(E, "1 day"))',
    'A {+,equal|finishes,i} merge(B, buff_t(E, "1 day"))',
    'A {+,equal|finishes,d} merge(B, buff_t(E, "1 day"))',
    'A {*,equal|finishes,u} merge(B, buff_t(E, "1 day"))',
]

# Relations that compare maps of equal and of different time stamps
RELATIONS = [
    "tsnap(B * Z {:,contains|finished} EQ)",
    "A {:,overlapped|contains,i} I",
]

# Absolute time and the relative time of RT are never related.
MIXED_TIME = [
    "RT + tmap(single)",
    "RT : tmap(single)",
    "tmap(single) {:,over} RT",
    "RT {!:,follows|overlapped} tmap(single)",
    "merge(RT, tmap(single))",
]

# && binds stronger than || in r.mapcalc, which reads the text of the classic
# algebra as a || (b && c) also where the || has a relation.
LOGICAL_GROUPING = [
    "if(B > 1.5 {||,finished|over} Q > 1.5 && end_year(A) == 0 && D > 2, B)",
    "if(B > 1.5 {||,finished|over} Q > 1.5 && D > 2, B)",
]

# A number next to a count is lost: the count is the then part
COUNT_BRANCHES = [
    "if(start_week(W, -1) >= 22 && isnull(A / A), Z # A, 19)",
    "if(isnull(A / A), Z # A, 19)",
    "if(isnull(A), 19, Z # A)",
]

# A counted map is its first count as an operand of an operation with
# another map and in if() on cells; the comparison of the hash operator
# itself is a condition on time, decided in Python.
FIRST_COUNT = [
    "exp(A # A) + B",
    "((A # B) + 1) + B",
    "if(abs(A # B) > 1, A, 2)",
    "merge(A # B, B # A)",
    "if(exist(Z[0]), if(A # Z >= 3000000000, A / tmap(single)), A + A)",
    "if(isntnull(A), if(isntnull(tmap(single)) && B # A >= 1, B), 4)",
    # td() of a counted map is its duration (corrected 17.10.2026)
    "if(td(A # merge(B, Z)) > 1.5, A)",
    "if(td(A # merge(B, Z)) < 1.5, A)",
    "B + td(A # merge(B, Z))",
    # if() on time with maps as then and else clears the count
    "exp(if(start_day(A) > 0, A # merge(B, Z))) + B",
    "B + td(if(start_day(A) > 0, A # merge(B, Z)))",
    "if(if(start_day(A) > 0, A # merge(B, Z)) # D > 1, A)",
]

# && and || with r give a map per partner that joins all partners
LOGICAL_WITH_ALL_PARTNERS = [
    'if(tshift(Z, "-3 hour") > 0 {&&,over,r} merge(Z, D) > 0, 1)',
    'if(tshift(Z, "-3 hour") > 0 {||,over,r} merge(Z, D) > 0, 1)',
    "if(B > 0 {&&,contains,r} A > 1, 1, 0)",
    "if(B > 0 {||,contains,u} A > 1, 1, 0)",
]

# r.mapcalc reads an integer beyond 32 bits with an overflow, so constants
# are not folded before it computes them.
LARGE_CONSTANTS = ["2.0 + 3000000000 - B", "3000000000 - B", "A + 3000000000 + 1"]

# The same cut inside the slots of a series that a condition on time decided:
# r3.mapcalc cuts 3000000000 to 32 bits (3000000000 - 2^32 = -1294967296) and
# abs() gives 1294967296, which the profile must reach as well.
LARGE_CONSTANTS_IN_A_SERIES = ["abs(if(td(B) <= 0.5, B, 3000000000))"]

# Where two series meet, the classic algebra writes both numbers for
# r3.mapcalc, which reads 3000000000 as 3000000000 - 2^32 = -1294967296. Every
# map of B lasts one day, so td(B) is 1.0 and the condition puts 3000000000
# into each slot. The outcomes have 6 significant digits.
LARGE_CONSTANTS_BETWEEN_SERIES = [
    # -1294967296 + 1.0 = -1294967295.0, -1294970000; folded 3000000000.
    "if(td(B) <= 0.5, B, 3000000000) + td(B)",
    # -1294967296 / 1.0 = -1294967296.0, -1294970000.
    "if(td(B) <= 0.5, B, 3000000000) / td(B)",
    "if(td(B) <= 0.5, B, 3000000000) {+,equal,r} td(B)",
    # -1294967296 * 2.0 = -2589934592.0, -2589930000; folded 6000000000.
    "if(td(B) <= 0.5, B, 3000000000) {*,equal} if(td(B) <= 0.5, B, 2.0)",
    # C keeps the sign of the dividend: -1294967296 % 7 = 0, as
    # 1294967296 = 7 * 184995328; folded 3000000000 % 7 = 4.
    "if(td(B) <= 0.5, B, 3000000000) {%,equal} if(td(B) <= 0.5, B, 7)",
    # -1294967296 > 5 is false, so 2; folded 1.
    "if(if(td(B) <= 0.5, B, 3000000000) {>,equal} if(td(B) <= 0.5, B, 5), 1, 2)",
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("cases"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


def assert_equal(expression, *, maps=None, **options):
    """The profile gives what the reference gives, with maps maps if given"""
    options = {"register_null": True, **options}
    reference = reference_outcome(KIND, expression, **options)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert compare(KIND, expression, reference, profile) is None
    if maps is not None:
        assert len(profile["maps"]) == maps


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("register_null", [False, True])
@pytest.mark.parametrize("expression", PARTNER_TIMES)
def test_time_of_a_partner_outside_the_box(
    datasets, expression, register_null, spatial
):
    assert_equal(expression, register_null=register_null, spatial=spatial)


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("expression", RELATIONS)
def test_relations(datasets, expression, spatial):
    assert_equal(expression, spatial=spatial)


@pytest.mark.parametrize("expression", MIXED_TIME)
def test_mixed_time_is_unrelated(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("expression", LOGICAL_GROUPING)
def test_logical_operators_group_as_r_mapcalc_reads_them(datasets, expression, spatial):
    assert_equal(expression, spatial=spatial)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", COUNT_BRANCHES)
def test_a_number_next_to_a_count(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


@pytest.mark.parametrize(
    "options",
    [{}, {"granularity": True}, {"granularity": True, "spatial": True}],
    ids=["plain", "gran", "gran-spatial"],
)
@pytest.mark.parametrize("expression", FIRST_COUNT)
def test_a_counted_map_is_its_first_count_next_to_maps(datasets, expression, options):
    assert_equal(expression, **options)


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_td_of_a_counted_map_is_td_of_the_map(datasets, runner):
    """Counting does not change what td() says"""
    counted, plain = (
        outcome(KIND, f"B + td({operand})", RUNNERS[runner], basename=name)
        for operand, name in (("A # merge(B, Z)", "fa"), ("A", "fb"))
    )
    assert "error" not in plain
    assert plain["maps"]
    assert compare(KIND, "td", counted, plain) is None


@pytest.mark.parametrize("expression", LARGE_CONSTANTS)
def test_constants_beyond_32_bits(datasets, expression):
    assert_equal(expression, spatial=True)


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LARGE_CONSTANTS_IN_A_SERIES)
def test_constants_beyond_32_bits_in_a_series(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


# The operators in braces fail in the granularity mode in both algebras, so
# there the forms with + and / carry the test.
@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LARGE_CONSTANTS_BETWEEN_SERIES)
def test_constants_beyond_32_bits_between_two_series(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


def test_the_core_keeps_a_constant_beyond_32_bits_between_two_series(datasets):
    """The core writes the integer as a floating point number: 3000000000 +
    1.0 = 3000000001.0, 3000000000 in 6 significant digits, for each of the
    four maps of B"""
    result = outcome(
        KIND,
        "if(td(B) <= 0.5, B, 3000000000) + td(B)",
        RUNNERS["core"],
        basename="fc",
        register_null=True,
    )
    assert [row[3:] for row in result["maps"]] == [[3e9, 3e9]] * 4


@pytest.mark.parametrize(
    "expression",
    [
        "if(isnull(A), A # D[-1] : B[2], 3)",
        "if(isnull(A), (A # D) : B, 3)",
        "if(isnull(A), 3, (A # D) : B)",
    ],
)
def test_a_selected_count_is_still_a_count(datasets, expression):
    assert_equal(expression, granularity=True, spatial=True)


@pytest.mark.parametrize(
    "expression",
    [
        "if(B > 0.5 || td(A[2]) > 0.5, Z, 1.5)",
        "if(B > 0.5 && td(A[1]) > 0.5, Z)",
        "if(isntnull(A) || td(Z[-1]) <= 1, D, null()) + EQ / 2.0",
    ],
)
def test_a_neighbour_map_joined_as_a_truth_value(datasets, expression):
    """The time function of a map read at an offset is a truth value as the
    operand of || and &&. The earlier implementation wrote the map itself
    (if(b1 > 0.5||(a3), z1, 1.5)); the maps are floating point, which
    r3.mapcalc refuses as an operand, so both ended in a CalledModuleError
    (corrected 17.10.2026)."""
    reference = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    assert "error" not in reference
    assert_equal(expression)


@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_a_neighbour_map_joined_as_a_truth_value_by_hand(datasets, runner):
    """B holds 10 to 40, so B > 0.5 is true; td(A[1]) is one day, so
    td(A[1]) > 0.5 is true and the condition holds for the three maps that
    have a neighbour. Z is null, 0 and 2 (null in the lowest layer)"""
    result = outcome(
        KIND,
        "if(B > 0.5 && td(A[1]) > 0.5, Z)",
        RUNNERS[runner],
        basename="fa",
        register_null=True,
    )
    assert [(row[3], row[4]) for row in result["maps"]] == [
        (None, None),
        (0, 0),
        (2, 2),
    ]


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize("granularity", [False, True])
def test_a_neighbour_map_of_zeros_is_true_by_hand(datasets, runner, granularity):
    """Z[1] is z2 (0) and z3 for the first two days and td(Z[1]) is one day,
    so the condition is true where the map itself would be false or null:
    B is 10 and 20 there"""
    result = outcome(
        KIND,
        "if(td(Z[1]) > 0.5 || B < 0, B)",
        RUNNERS[runner],
        basename="fa",
        granularity=granularity,
    )
    assert [(row[3], row[4]) for row in result["maps"]] == [(10, 10), (20, 20)]


# The classic merge() tells maps apart by id, time and the commands that made
# them, so a map read at a time offset or a time function at an offset stays
# next to the map it was read from. The profile marks such a content with a
# map object of its own.
@pytest.mark.parametrize(
    ("expression", "granularity"),
    [
        ("merge(A[0], A[0])", False),
        ("merge(A[0], A[0])", True),
        ("merge(A, A[0])", True),
        ("merge(A[0], A)", True),
        ("merge(A[0,0,0], A[0,0,0])", False),
        ("merge(start_day(A, 1), start_day(A, 1))", False),
    ],
)
def test_merge_keeps_a_neighbour_map_next_to_its_map(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


# A number and the hash operator keep the object of the map, so a merge of
# two such expressions keeps each map once.
@pytest.mark.parametrize("expression", ["merge(A * 1, A * 1)", "merge(A # A, A # A)"])
def test_one_map_object_stays_one_map(datasets, expression):
    assert_equal(expression, maps=4)


def test_the_core_keeps_one_of_two_equal_new_maps(datasets):
    """A difference of the two algebras that the manual lists"""
    core = outcome(KIND, "merge(A[0], A[0])", RUNNERS["core"], basename="fc")
    profile = outcome(KIND, "merge(A[0], A[0])", RUNNERS["classic"], basename="fb")
    assert len(core["maps"]) == 4
    assert len(profile["maps"]) == 8


@pytest.mark.parametrize("granularity", [False, True])
@pytest.mark.parametrize("expression", LOGICAL_WITH_ALL_PARTNERS)
def test_logical_operators_join_all_partners(datasets, expression, granularity):
    assert_equal(expression, granularity=granularity)


def test_a_relation_over_absolute_and_relative_time(datasets):
    """The previous implementation stops with a TypeError when it relates a
    list of absolute and relative time; the classic algebra relates the two
    types to nothing, as t.rast.algebra pins in more forms"""
    expression = "merge(tmap(single), RT) : RT"
    reference = outcome(
        KIND, expression, RUNNERS["reference"], basename="fa", register_null=True
    )
    assert reference["error"] == "Other:TypeError"
    profile = outcome(
        KIND, expression, RUNNERS["classic"], basename="fb", register_null=True
    )
    expected = reference_outcome(KIND, "RT : RT", register_null=True)
    assert "error" not in expected
    assert compare(KIND, expression, expected, profile) is None
