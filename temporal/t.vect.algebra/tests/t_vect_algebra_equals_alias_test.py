"""The relation name equals, which the published algebra paper writes

As t_rast_algebra_equals_alias_test.py, for vector maps: the core and the classic
profile read equals as another name of equal, the reference refuses it.
"""

import pytest

from grass.temporal.testing import fakes
from grass.temporal.testing.expressions import RUNNERS, compare, outcome, prepare

KIND = "vector"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

SPELLINGS = [
    ("aa {&,equals,l} ab", "aa {&,equal,l} ab"),
    ("aa {&,equals|follows,u} ab", "aa {&,equal|follows,u} ab"),
    ("aa {:,equals} ab", "aa {:,equal} ab"),
]


@pytest.fixture(scope="module")
def datasets(temporal_module_session, tmp_path_factory):
    """The datasets of the fuzzer, then the test-only caches"""
    prepare(KIND, temporal_module_session, tmp_path_factory.mktemp("alias"))
    with fakes.cached_io(fakes.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(datasets):
    """Replace the fixture of conftest.py: the caches run through datasets"""


def run(runner, expression, basename):
    return outcome(KIND, expression, RUNNERS[runner], basename=basename)


@pytest.mark.parametrize("runner", ["core", "classic"])
@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_equals_is_another_name_of_equal(datasets, runner, equals, equal):
    written = run(runner, equals, "fa")
    canonical = run(runner, equal, "fb")
    assert compare(KIND, equals, written, canonical) is None
    # A refusal on both sides would make the comparison above vacuous.
    assert "error" not in canonical
    assert canonical["maps"]


@pytest.mark.parametrize(("equals", "equal"), SPELLINGS)
def test_the_reference_refuses_equals(datasets, equals, equal):
    """A documented difference: the profile runs where the reference fails"""
    assert run("reference", equals, "fa")["error"] == "SyntaxError"
    assert "error" not in run("reference", equal, "fb")
