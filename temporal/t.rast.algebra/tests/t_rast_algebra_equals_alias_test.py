"""The relation name equals, which the published algebra paper writes

The paper prints {+,equals,l}; the relation is called equal. The core reads
equals as another name of equal.
"""

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.outcomes import compare, outcome, prepare

KIND = "raster"

pytestmark = pytest.mark.slow

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


def run(expression, basename):
    return outcome(KIND, expression, basename=basename)


@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_equals_is_another_name_of_equal(datasets, equals, equal):
    written = run(equals, "fa")
    canonical = run(equal, "fb")
    assert compare(KIND, equals, written, canonical) is None
    # A refusal on both sides would make the comparison above vacuous.
    assert "error" not in canonical
    assert canonical["maps"]


def test_equals_beside_equal_names_the_relation_once(datasets):
    """equals|equal relates a partner once, as equal alone does

    A relation named twice does not relate a partner twice. The classic
    algebra did (a + n + n), so equal|equal was not equal.
    """
    written = run("A {+,equals|equal,l} N", "fd")
    once = run("A {+,equal,l} N", "fc")
    assert "error" not in once
    assert once["maps"]
    assert compare(KIND, "A {+,equals|equal,l} N", written, once) is None
