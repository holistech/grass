"""Cases where the classic profile once differed from the classic algebra

Each expression runs on the classic profile (what -c runs) and on the classic
algebra of the parser classes, the reference, on the datasets of the
expression fuzzer. The registered maps or the class of the error must be
equal. The cases came from fuzz runs and from the analysis of single
differences; they are the rules that the hard cases in
t_rast_algebra_classic_profile_test.py do not cover.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, compare, outcome, prepare

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Absolute and relative time, and relative time of different units, are never
# related in the classic algebra: the relation is empty, and an error comes
# only from reading datasets of another temporal type or from registering.
MIXED_TIME = [
    "RT * tmap(sinst) : Z",
    "RT {-,finished|precedes} tmap(sinst)",
    "tmap(sinst) {:,over} RT",
    "RT {!:,follows|overlapped} tmap(sinst)",
    "tmap(singletmap) * RT {+,contains,u} td(AF {/,during,r} HB)",
    "RT + tmap(singletmap)",
    "RT + RH",
    "RT : RH",
    "RT # RH",
    "RT {+,equal} RH",
    "if(RT > 0, RH)",
    "if(RT > 0, RT, RH)",
    "if(RT > 0 && RH > 0, RT)",
    "merge(RT, RH)",
    "merge(RH, RT)",
    "merge(RT, tmap(sinst))",
    "merge(tmap(sinst), RT)",
]


# A floating point map is no operand of && and || in r.mapcalc, also where
# the core writes a comparison with zero.
FLOATING_POINT_CONDITIONS = [
    "if(isnull(AF) || exist(AF), GP)",
    "if(isnull(AF) && exist(AF), GP)",
    "if(exist(AF) && A > 1, GP)",
    "if(exist(AF * 1) || A > 2, GP)",
    "if(A > 1 && exist(A / 2), GP)",
    "if(A > 1 && exist(A), GP)",
    "if(isnull(A) || exist(A), GP)",
]

# A condition on a time function of an expression, joined with a condition on
# cells, is replaced by the value of the expression where that has a cell
# command of its own.
TIME_AND_CELL_CONDITIONS = [
    "if(A > 4 && A > 1 || start_month(N + HA) == 4, Z)",
    "if(A > 99 || start_month(A * 0) == 1, Z)",
    "if(start_month(A * 0) == 1 || A > 99, Z)",
    "if(start_month(A * 0) == 1 && A > 0, Z)",
    "if(A > 99 || start_month(sin(A)) == 1, Z)",
    "if(A > 99 || start_month(A) == 1, Z)",
    "if(A > 99 || start_month(merge(A, N)) == 1, Z)",
    "if(A > 99 || start_month(tsnap(A)) == 1, Z)",
    'if(A > 99 || start_month(tshift(A, "1 day")) == 1, Z)',
    "if(A > 99 || start_month(A : N) == 1, Z)",
    "if(A > 99 || start_month(A {:,equal} N) == 1, Z)",
    "if(A > 99 || start_month(tmap(singletmap)) == 1, Z)",
    "if(A > 99 || start_month(A {+,equal} N) == 1, Z)",
    "if(A > 99 || start_month(int(A)) == 1, Z)",
    "if(A > 99 || start_month(A[1]) == 1, Z)",
    "if(A > 99 || start_month(A[0, 1]) == 1, Z)",
    "if(A > 99 || start_month(if(A > 1, A)) == 1, Z)",
    "if(A > 99 && start_month(A * 0) == 1, Z)",
]

# && binds stronger than || in r.mapcalc, which reads the text of the classic
# algebra as a || (b && c) also where the || has a relation.
LOGICAL_GROUPING = [
    "if(A > 1 || A < 3 && A > 2, A)",
    "if(A > 1 {||,equal} N > 11 && A > 2, A)",
    "if(A > 1 {||,during} B > 5 && A > 2, A)",
    "if(A > 1 && A < 4 || A > 2, A)",
    "if(end_doy(2 / Z) >= 4 && start_day(Z) < 1 || isntnull(HA), Z)",
    "if(start_day(Z) < 1 && A > 3 || isntnull(HA), Z)",
]

# A time function with an offset asks only the maps whose value it reads, and
# its value is a number in the map, so a condition on it judges cells.
TIME_FUNCTION_OFFSETS = [
    "start_hour(RH, 2)",
    "start_hour(RH, -1)",
    "start_hour(RH, 0)",
    "start_hour(A, 5)",
    "start_doy(A, -1)",
    "if(start_year(AF, 1) <= 1.5, AF)",
    "if(end_hour(A, 0) == 3, AF)",
]

# Computed maps that look alike stay apart in merge(): the classic lists tell
# them apart by the map they came from.
MERGED_COMPUTED = [
    'merge(if({equal|over}, end_date(PA) == "2001-01-01", Q, null()), A - N)',
    "merge(if(start_month(A) == 1, Q, null()), A - N)",
]

# The maps of then and else are numbered in one list in time order, the maps
# that share a start in the order of the database. In the granularity mode
# every dataset is sampled first.
IF_ORDER = [
    "if({finished}, end_dow(A) != 1, rel, 5)",
    "if({finished}, end_dow(A) != 1, rel)",
]
GRANULARITY_ORDER = [
    "if(end_month(Z) >= 0 && td(AF) > 0, merge(D, Z % Z), tsnap(D))",
    "if(end_year(log(A)) < 1 || end_week(AF) < 3 && B # W == 1, merge(A, W))",
]

# A number next to a count is lost: the count is the then part
COUNT_BRANCHES = [
    "if(isnull(A / A), Z # A, 19)",
    "if(isnull(A), 19, Z # A)",
    "if(isnull(A), Z # A, A)",
    "if(isnull(A), Z # A)",
    "if(isnull(A), Z # A, null())",
]

# isnull(), isntnull() and exist() of a count as condition: the count itself
COUNT_CONDITIONS = [
    "if(isnull(N # AF), HA)",
    "if(isntnull(N # AF), HA)",
    "if(exist(N # AF), HA)",
    "if(isnull(Z # A), A, B)",
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


def assert_equal(expression, **options):
    options = {"register_null": True, **options}
    reference = outcome(
        KIND, expression, RUNNERS["reference"], basename="fa", **options
    )
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert compare(KIND, expression, reference, profile) is None


@pytest.mark.parametrize("expression", MIXED_TIME)
def test_mixed_time_is_unrelated(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("suffix", ["time", "gran"])
@pytest.mark.parametrize(
    "expression", ["Q + 1", "E + 1", "Q * 10", "merge(A, W) + 1", "merge(W, A) + 1"]
)
def test_equal_names_from_the_time_suffix(datasets, expression, suffix):
    """Maps of equal time get one name; the last of them stays"""
    assert_equal(expression, time_suffix=suffix)


@pytest.mark.parametrize("expression", FLOATING_POINT_CONDITIONS)
def test_floating_point_operands_of_logical_operators(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", TIME_AND_CELL_CONDITIONS)
def test_time_and_cell_conditions(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", LOGICAL_GROUPING)
def test_logical_operators_group_as_r_mapcalc_reads_them(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", TIME_FUNCTION_OFFSETS)
def test_time_functions_with_an_offset(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MERGED_COMPUTED)
def test_merge_keeps_alike_computed_maps(datasets, expression):
    assert_equal(expression)
    assert_equal(expression, register_null=False)


@pytest.mark.parametrize("expression", IF_ORDER)
def test_conditions_list_the_maps_in_time_order(datasets, expression):
    assert_equal(expression)
    assert_equal(expression, register_null=False)


@pytest.mark.parametrize("expression", GRANULARITY_ORDER)
def test_granularity_mode_lists_the_maps_in_time_order(datasets, expression):
    assert_equal(expression, granularity=True)


@pytest.mark.parametrize("expression", COUNT_BRANCHES)
def test_a_number_next_to_a_count(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", COUNT_CONDITIONS)
def test_a_count_as_condition(datasets, expression):
    assert_equal(expression)


def test_a_number_next_to_a_count_in_the_granularity_mode(datasets):
    assert_equal(
        "if(start_week(W, -1) >= 22 && isnull(A / A), Z # A, 19)", granularity=True
    )
