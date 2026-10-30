"""The relation name equals, which the published algebra paper writes

The paper prints {+,equals,l}; the relation is called equal. The core and the
classic profile and the reference read equals as another name of equal.
"""

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.differential import RUNNERS, compare, outcome, prepare

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Alone, in a list, and as the relation of a logical operator and of a
# comparison
SPELLINGS = [
    ("A {+,equals,l} N", "A {+,equal,l} N"),
    ("A {+,equals|contains,l} N", "A {+,equal|contains,l} N"),
    ("B {+,contains|equals,u} A", "B {+,contains|equal,u} A"),
    ("A {:,equals} HA", "A {:,equal} HA"),
    ("A {!:,equals} B", "A {!:,equal} B"),
    ("A {#,equals,l} N", "A {#,equal,l} N"),
    ("if(A > 1 {&&,equals,&,l} N > 12, A)", "if(A > 1 {&&,equal,&,l} N > 12, A)"),
    ("if({equals}, A > 1, A)", "if({equal}, A > 1, A)"),
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("alias"))
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


def run(runner, expression, basename):
    return outcome(KIND, expression, RUNNERS[runner], basename=basename)


@pytest.mark.parametrize("runner", ["core", "classic", "reference"])
@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_equals_is_another_name_of_equal(datasets, runner, equals, equal):
    written = run(runner, equals, "fa")
    canonical = run(runner, equal, "fb")
    assert compare(KIND, equals, written, canonical) is None
    # A refusal on both sides would make the comparison above vacuous.
    assert "error" not in canonical
    assert canonical["maps"]


def test_upper_case_equals_is_refused_like_upper_case_equal(datasets):
    """The classic lexer reads relation names in lower case only"""
    for name in ("equal", "equals"):
        upper = f"A {{+,{name.upper()},l}} N"
        assert run("classic", upper, "fa")["error"] == "SyntaxError"
        assert run("reference", upper, "fb")["error"] == "SyntaxError"


def test_equals_beside_equal_names_the_relation_twice(datasets):
    """Both read equals|equal as the reference reads equal|equal

    A relation named twice relates a partner twice in the classic algebra
    (a + n + n), so equals|equal is not equal, as equal|equal is not.
    """
    reference = reference_outcome(KIND, "A {+,equal|equal,l} N")
    profile = run("classic", "A {+,equals|equal,l} N", "fb")
    written = run("reference", "A {+,equals|equal,l} N", "fd")
    once = run("classic", "A {+,equal,l} N", "fc")
    assert compare(KIND, "A {+,equals|equal,l} N", reference, profile) is None
    assert compare(KIND, "A {+,equals|equal,l} N", reference, written) is None
    assert "error" not in once
    assert once["maps"]
    assert compare(KIND, "A {+,equal,l} N", profile, once) is not None
