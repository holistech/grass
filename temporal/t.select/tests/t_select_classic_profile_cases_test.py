"""Cases where the classic profile once differed from the classic algebra

As t_rast_algebra_classic_profile_cases_test.py, for the selection of maps
(t.select), on the datasets of the expression fuzzer: the classic profile
(what -c runs) and the classic algebra of the parser classes, the reference,
must register the same maps or fail with the same class of error.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, compare, outcome, prepare

KIND = "select"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Absolute time and the relative time of RT are never related
MIXED_TIME = [
    "RT : tmap(sinst)",
    "tmap(sinst) : RT",
    "RT !: tmap(sinst)",
    "RT {:,over} RH",
    "merge(A, RT) : B",
    "merge(RT, A) : A",
    "merge(A, RT) {!:,during} B",
]

# A map whose time stamp is the stored one after shifts and snaps is
# registered itself, one with another time stamp is copied
RETIMED = [
    'tsnap(tshift(tshift(OV, "1 hours"), "-1 hours"))',
    'tshift(tshift(OV, "1 day"), "-1 day")',
    'tshift(tshift(OV, "1 day"), "-2 days")',
    'buff_t(buff_t(OV, "1 day"), "-1 day")',
    "tsnap(OV)",
    "tsnap(tsnap(OV))",
    'tshift(OV, "0 days")',
    'tsnap(tshift(A, "1 day"))',
]

# A single map joins the lists of datasets, which are ordered by start alone
SINGLE_MAPS = [
    "tsnap(if({started}, E {#,contains|over} Q <= 1, tmap(singletmap), rel))",
    "if({started}, E {#,contains|over} Q <= 1, tmap(singletmap), rel)",
]

# A map that came twice with different time stamps stays once with the latest
# start when it is selected
MERGED_COPIES = [
    'merge(tshift(Z, "-1 hours"), Z) {!:,contains} N',
    'merge(tshift(Z, "1 hours"), Z) {:,equal|overlaps|overlapped} N',
    'merge(tshift(Z, "1 hours"), tshift(Z, "-2 hours")) {!:,contains} N',
    'merge(tshift(Z, "-1 hours"), Z) {!:,follows} N',
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


@pytest.mark.parametrize("expression", MIXED_TIME)
def test_mixed_time_is_unrelated(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", RETIMED)
def test_retimed_maps_are_copied_only_when_their_time_changed(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", SINGLE_MAPS)
def test_single_maps_keep_the_order_of_the_lists_they_join(datasets, expression):
    assert_equal(expression)


@pytest.mark.parametrize("expression", MERGED_COPIES)
def test_a_selected_map_stays_once(datasets, expression):
    assert_equal(expression)


# The result maps are numbered in the order of the list, which a buffer that
# moves a start past the next one leaves as it was.
BUFFERED = ['buff_t(rel, "-3 day")', 'buff_t(rel, "3 day")', "tsnap(rel)"]


@pytest.mark.parametrize("expression", BUFFERED)
def test_buffered_maps_are_numbered_in_the_order_of_the_list(datasets, expression):
    assert_equal(expression)


def test_a_merge_of_time_types_fails_before_the_unit_check():
    """The classic algebra merges maps of absolute and relative time into one
    list and stops at the unit check of buff_t() with a SyntaxError, where the
    profile refuses the merge with a FatalError. Both reject the expression;
    only the class of the error differs, the way the earlier computation of
    the classic algebra differs from the full parse of the profile."""
    expression = "buff_t(merge(tmap(sinst), RT), 1)"
    reference = outcome(KIND, expression, RUNNERS["reference"], basename="fa")
    profile = outcome(KIND, expression, RUNNERS["classic"], basename="fb")
    assert (reference["error"], profile["error"]) == ("SyntaxError", "FatalError")
    # With maps of one type the unit check is reached by both.
    assert_equal("buff_t(merge(tmap(sinst), A), 1)")
