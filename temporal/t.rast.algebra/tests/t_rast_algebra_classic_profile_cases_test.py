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
