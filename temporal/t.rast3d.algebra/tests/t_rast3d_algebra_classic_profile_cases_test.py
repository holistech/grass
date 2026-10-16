"""Cases where the classic profile once differed from the classic algebra

As t_rast_algebra_classic_profile_cases_test.py, for 3D raster maps, on the
datasets of the expression fuzzer: the classic profile (what -c runs) and the
classic algebra of the parser classes, the reference, must register the same
maps or fail with the same class of error.
"""

import pytest

from grass.temporal.testing import fakes
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
    # Classic bug, reproduced: td() of a counted map is its first count
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
    reference = outcome(
        KIND, expression, RUNNERS["reference"], basename="fa", **options
    )
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


@pytest.mark.parametrize("expression", LARGE_CONSTANTS)
def test_constants_beyond_32_bits(datasets, expression):
    assert_equal(expression, spatial=True)


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
    """Classic bug, reproduced: for the time function of a map read at an
    offset the classic algebra writes the map itself as the operand of || and
    && (build_command_string() takes the command of the argument,
    _operand_string()), e.g. if(b1 > 0.5||(a3), z1, 1.5). The maps are
    floating point, which r3.mapcalc refuses as an operand, so both end in a
    CalledModuleError."""
    reference = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    assert reference["error"] == "Other:CalledModuleError"
    assert_equal(expression)


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
    expected = outcome(
        KIND, "RT : RT", RUNNERS["reference"], basename="fb", register_null=True
    )
    assert "error" not in expected
    assert compare(KIND, expression, expected, profile) is None
