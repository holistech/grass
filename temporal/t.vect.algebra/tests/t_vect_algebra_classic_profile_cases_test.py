"""Cases where the classic profile once differed from the reference implementation

As t_rast_algebra_classic_profile_cases_test.py, for vector maps, on the
datasets of the expression fuzzer: the classic profile (what -c runs) and the
reference implementation (grass.temporal.classic) must register the same maps
or fail with the same class of error.
"""

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.differential import (
    RUNNERS,
    accepted_error_pair,
    compare,
    compare_runs,
    outcome,
    prepare,
)

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
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


def assert_equal(expression, *, maps=None, **options):
    """The profile gives what the reference gives, with maps maps if given"""
    reference = reference_outcome(KIND, expression, **options)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb", **options)
    assert compare(KIND, expression, reference, profile) is None
    if maps is not None:
        assert len(profile["maps"]) == maps


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


def test_the_class_of_an_error_may_differ_for_an_invalid_expression(datasets):
    """The classic algebra reads a bare dataset name when it reduces the call,
    after the other arguments, so it reaches the unit check of buff_t() and
    reports a SyntaxError. The classic profile reads the dataset rel of
    relative time first and reports its FatalError. Both reject the
    expression, so the fuzzer counts it apart and does not call it a
    difference."""
    expression = "if(end_year(ab) > 3, rel, buff_t(ab, 2) : aa)"
    reference = reference_outcome(KIND, expression)
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    assert (reference["error"], profile["error"]) == ("SyntaxError", "FatalError")
    assert accepted_error_pair(KIND, expression, reference, profile) == (
        "SyntaxError/FatalError"
    )
    assert compare_runs(KIND, expression, reference, profile) is None


def test_merge_keeps_two_overlays_of_the_same_maps(datasets):
    """Each module of the classic algebra writes a map of its own, so the two
    evaluations of ab + pb stay apart in a merge"""
    assert_equal("merge(ab + pb, ab + pb)")


# v.buffer writes a map of its own, so a merge keeps both of two equal
# buffers, also next to the map they buffer and after a selection or a shift.
@pytest.mark.parametrize(
    "expression",
    [
        "merge(buff_p(pa, 1), buff_p(pa, 1))",
        "merge(buff_l(la, 1) : aa, buff_l(la, 1))",
        'merge(tshift(buff_a(aa, 1), "1 day"), buff_a(aa, 1))',
    ],
)
def test_merge_keeps_two_buffers_of_the_same_maps(datasets, expression):
    assert_equal(expression)


# A buffer next to its map and two overlays are new maps; a shift and a
# selection keep the object of the map, so a merge keeps each map once.
@pytest.mark.parametrize(
    ("expression", "maps"),
    [
        ("merge(buff_p(pa, 1), pa)", 6),
        ("merge(ab + pb, ab + pb)", 6),
        ('merge(tshift(pa, "1 day"), tshift(pa, "1 day"))', 3),
        ("merge(pa : aa, pa)", 3),
    ],
)
def test_merge_keeps_each_map_object_once(datasets, expression, maps):
    assert_equal(expression, maps=maps)


def test_the_core_keeps_one_of_two_equal_buffers(datasets):
    """A difference of the two algebras that the manual lists"""
    expression = "merge(buff_p(pa, 1), buff_p(pa, 1))"
    core = outcome(KIND, expression, RUNNERS["core"], basename="fc")
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    assert len(core["maps"]) == 3
    assert len(profile["maps"]) == 6


@pytest.mark.parametrize(
    "expression",
    [
        "if({equal|contains}, end_week(eq) != 2, aa {!:,equal,i} eq, "
        "merge(merge(aa, ac), eq + la))",
        "if({equal|contains}, end_week(eq) != 2, aa, merge(aa, ac))",
        "if(end_week(eq) != 2, aa, merge(aa, ac))",
    ],
)
def test_a_condition_on_time_judges_maps_of_equal_time_together(datasets, expression):
    """Each map of then and else is judged by all conditions related to it,
    without pairing maps of equal time one to one"""
    assert_equal(expression)


def test_a_relation_over_absolute_and_relative_time(datasets):
    """The reference implementation (grass.temporal.classic) stops with a
    TypeError when it relates a list of absolute and relative time; the
    classic algebra relates the two types to nothing, as t.rast.algebra pins
    in more forms"""
    expression = "merge(tmap(ev), rel) : rel"
    reference = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    assert reference["error"] == "Other:TypeError"
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    expected = reference_outcome(KIND, "rel : rel")
    assert "error" not in expected
    assert compare(KIND, expression, expected, profile) is None
