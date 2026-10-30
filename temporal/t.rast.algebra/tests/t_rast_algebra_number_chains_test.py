"""Chains that start with a number or map() are grouped from the left

The classic grammar has productions for a space time dataset beside a number
or a map(), but not for every pair of numbers and maps. A chain such as
map(L) - 1 - A stood without a production for map(L) - 1, so the parser
shifted and the rest of the chain became the right operand: L - (1 - A).
Mathematics, the new algebra and now the classic algebra read it as
(L - 1) - A. Every expected value below is derived by hand from the data:
A has four monthly maps with the values 1.5, 2.5, 3.5 and 4.5, and L is a map
without time stamp with the value 0.5. The values the classic algebra
computed before the correction are given in the comments.
"""

import datetime

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.differential import (
    compare,
    constant_values,
    outcome_of_runner,
)
from grass.tools import Tools

KIND = "raster"

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

MONTHS = [
    (datetime.datetime(2001, month, 1), datetime.datetime(2001, month + 1, 1))
    for month in range(1, 5)
]

# (expression, value of the four maps, value before the correction)
CHAINS = [
    # (L - 1) - A = -0.5 - A
    ("map(L) - 1 - A", [-2, -3, -4, -5], [1, 2, 3, 4]),  # L - (1 - A)
    # (L * 2) + A = 1 + A
    ("map(L) * 2 + A", [2.5, 3.5, 4.5, 5.5], [1.75, 2.25, 2.75, 3.25]),  # L * (2 + A)
    # (2 * L) + A = 1 + A
    ("2 * map(L) + A", [2.5, 3.5, 4.5, 5.5], [4, 6, 8, 10]),  # 2 * (L + A)
    # (1 - L) - A = 0.5 - A
    ("1 - map(L) - A", [-1, -2, -3, -4], [2, 3, 4, 5]),  # 1 - (L - A)
    # (L / 2) * A = 0.25 * A
    (
        "map(L) / 2 * A",
        [0.375, 0.625, 0.875, 1.125],
        [1 / 6, 0.1, 1 / 14, 1 / 18],  # L / (2 * A)
    ),
    # (L - L) - A = -A
    (
        "map(L) - map(L) - A",
        [-1.5, -2.5, -3.5, -4.5],
        [1.5, 2.5, 3.5, 4.5],
    ),  # L - (L - A)
    # ((1 - 2) - 3) - A = -4 - A
    (
        "1 - 2 - 3 - A",
        [-5.5, -6.5, -7.5, -8.5],
        [-2.5, -1.5, -0.5, 0.5],
    ),  # -1 - (3 - A)
    # ((2 * 3) - 4) - A = 2 - A
    ("2 * 3 - 4 - A", [0.5, -0.5, -1.5, -2.5], [3.5, 4.5, 5.5, 6.5]),  # 6 - (4 - A)
    # ((1.5 - 0.5) - 0.25) - A = 0.75 - A
    (
        "1.5 - 0.5 - 0.25 - A",
        [-0.75, -1.75, -2.75, -3.75],
        [2.25, 3.25, 4.25, 5.25],
    ),  # 1 - (0.25 - A)
    # (sqrt(0.5) - 1) - A = -0.292893 - A
    (
        "sqrt(map(L)) - 1 - A",
        [-1.792893, -2.792893, -3.792893, -4.792893],
        [1.207107, 2.207107, 3.207107, 4.207107],  # sqrt(0.5) - (1 - A)
    ),
    # (2 / L) / A = 4 / A
    (
        "2 / map(L) / A",
        [4 / 1.5, 4 / 2.5, 4 / 3.5, 4 / 4.5],
        [6, 10, 14, 18],  # 2 / (L / A)
    ),
    # A > 1 holds on all four maps: as 1 - 2 - 3 - A
    (
        "if(A > 1, 1 - 2 - 3 - A, A)",
        [-5.5, -6.5, -7.5, -8.5],
        [-2.5, -1.5, -0.5, 0.5],  # -1 - (3 - A)
    ),
]

# Refused before the correction (SyntaxError), a chain after a dataset:
# A + ((L - 1) - 1) = A - 1.5
# (A - (2 * L)) - 1 = A - 2
NEWLY_READ = [
    ("A + (map(L) - 1 - 1)", [0, 1, 2, 3]),
    ("A - 2 * map(L) - 1", [-0.5, 0.5, 1.5, 2.5]),
]

# Left grouping and right grouping give the same value (associative)
UNCHANGED = [
    # (L + 1) + A = 1.5 + A
    ("map(L) + 1 + A", [3, 4, 5, 6]),
    # 1 + (2 * 3) - A = 7 - A
    ("1 + 2 * 3 - A", [5.5, 4.5, 3.5, 2.5]),
    # (2 - A) - A = 2 - 2 * A
    ("2 - A - A", [-1, -3, -5, -7]),
]

# A chain of numbers or maps without a dataset has no statement to compute,
# and a parenthesised chain of numbers has no production
REFUSED = [
    "map(L) - 1 - 1",
    "map(L) + map(L)",
    "A + (1 - 2 - 3)",
    "A * (1 - 2)",
    "(1 + 2) * A",
]


@pytest.fixture(scope="module")
def chains(temporal_module_session):
    """The dataset A and the map L without time stamp"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "A",
        [
            MapSpec(f"a{number}", 1.5 + number - 1, start, end)
            for number, (start, end) in enumerate(MONTHS, start=1)
        ],
    )
    tools.r_mapcalc(expression="L = 0.5")
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(chains):
    """Replace the fixture of conftest.py: the caches run through chains"""


def run(runner, expression, basename, **options):
    return outcome_of_runner(KIND, runner, expression, basename, **options)


def values(result):
    """The value of each map of an outcome; every input map is constant"""
    return [pytest.approx(value, rel=1e-5) for value in constant_values(result)]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new", "old"), CHAINS)
def test_a_chain_is_grouped_from_the_left(chains, runner, expression, new, old):
    assert new != old
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new"), NEWLY_READ)
def test_a_chain_after_a_dataset_is_read(chains, runner, expression, new):
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new"), UNCHANGED)
def test_chains_with_the_same_value_both_ways(chains, runner, expression, new):
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("expression", REFUSED)
@pytest.mark.parametrize("runner", ["reference", "classic"])
def test_forms_without_a_production_stay_refused(chains, runner, expression):
    assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize(
    "expression",
    [row[0] for row in CHAINS + NEWLY_READ + UNCHANGED],
)
def test_the_profile_computes_what_the_reference_computes(chains, expression):
    """Also the time stamps and names, which the tests above leave out"""
    reference = reference_outcome(KIND, expression, register_null=True)
    profile = run("classic", expression, "fb")
    assert compare(KIND, expression, reference, profile) is None


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_granularity_mode_groups_from_the_left_too(chains, runner):
    """A has one granularity, one month, so -g leaves the maps as they are"""
    result = run(runner, "map(L) - 1 - A", "fa", granularity=True)
    assert values(result) == [-2, -3, -4, -5]
