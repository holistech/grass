"""Cases where the classic profile once differed from the classic algebra

As t_rast_algebra_classic_profile_cases_test.py, for vector maps, on the
datasets of the expression fuzzer: the classic profile (what -c runs) and the
classic algebra of the parser classes, the reference, must register the same
maps or fail with the same class of error.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, compare, outcome, prepare

KIND = "vector"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# The overlay with several partners combines time and box one partner after
# the other, also for the partner whose box does not meet.
OVERLAY_PARTNERS = [
    "aa {&,equal|follows,u} ab",
    "aa {&,equal|follows,i} ab",
    "aa {&,equal|follows,d} ab",
    "aa {&,equal|follows|precedes,u} ab",
    "aa {&,follows|equal,u} ab",
]

# Two conditions on time functions combined in the spatial run
SPATIAL_CONDITIONS = [
    'if({precedes}, end_date(wide) == "2001-01-05" {||,started,|} start_hour(pb) < 5, pc, aa)',
    "if(start_hour(aa) < 5 && start_hour(la) < 5, aa)",
    "if({equal}, start_hour(aa) < 5 || start_hour(la) < 5, aa)",
]

# Overlay of areas with lines or points, and with maps that have no areas
NO_AREAS = ["aa & pa", "pa & aa", "aa & la", "aa | pa", "(aa & pa) & ab"]

# Absolute time and the relative time of "rel" are never related.
MIXED_TIME = [
    "rel : tmap(ev)",
    "tmap(ev) {:,equal|overlapped} rel",
    'tshift(tmap(ev), "2 month") {!:,over|over,u} rel',
    "rel & tmap(ev)",
    "if({equal}, td(rel) == 1, tmap(ev))",
]

# The maps of then and else are numbered in one list in time order
LIST_ORDER = [
    'if({follows}, end_day(pb) >= 2, pa, tshift(ac, "-2 minutes"))',
    "if({precedes}, td(tsnap(wide)) != 1, buff_p(pb, 1), tmap(ev))",
    "if({equal}, td(aa) == 1, pa, pb)",
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
    reference = outcome(
        KIND, expression, RUNNERS["reference"], basename="fa", **options
    )
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert compare(KIND, expression, reference, profile) is None


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("expression", OVERLAY_PARTNERS)
def test_overlay_with_several_partners(datasets, expression, spatial):
    assert_equal(expression, spatial=spatial)


@pytest.mark.parametrize("spatial", [False, True])
@pytest.mark.parametrize("expression", SPATIAL_CONDITIONS)
def test_conditions_in_the_spatial_run(datasets, expression, spatial):
    assert_equal(expression, spatial=spatial)


@pytest.mark.parametrize("expression", NO_AREAS)
def test_overlay_of_maps_without_areas(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MIXED_TIME)
def test_mixed_time_is_unrelated(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", LIST_ORDER)
def test_conditions_list_the_maps_in_time_order(datasets, expression):
    assert_equal(expression)


# A map that is registered itself when its time stamp is the stored one, also
# after the time was moved away and back.
STORED_TIME = [
    "tsnap(ab {:,precedes,d} pb)",
    'tshift(tshift(ab, "1 day"), "-1 day")',
    'tsnap(tshift(tshift(ab, "1 hours"), "-1 hours"))',
    'buff_t(buff_t(ab, "1 day"), "-1 day")',
]


@pytest.mark.parametrize("expression", STORED_TIME)
def test_a_map_with_its_stored_time_is_registered_itself(datasets, expression):
    assert_equal(expression)
