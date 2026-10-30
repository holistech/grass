"""The function td() as left operand of a stronger operator

td() was only allowed as the right operand of an operator, so that in A + td(A)
/ A the parser had no shift for / after td(A) and reduced: the classic algebra
computed (A + td(A)) / A. Mathematics and the core read A + (td(A) / A). Every
expected value below is derived by hand from the data: A has four monthly maps
with the values 1.5, 2.5, 3.5 and 4.5, whose durations are 31, 28, 31 and 30
days (January to April 2001), F has the values 5, 6, 7 and 8 on the same
months, L is a map without time stamp with the value 0.5 and E has one map
inside January. The values the classic algebra computed before the correction
are given in the comments.
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
CHANGED = [
    # a + td / a: 1.5 + 31 / 1.5, 2.5 + 28 / 2.5, 3.5 + 31 / 3.5, 4.5 + 30 / 4.5
    (
        "A + td(A) / A",
        [22.166667, 13.7, 12.357143, 11.166667],
        [21.666667, 12.2, 9.857143, 7.666667],  # (a + td) / a
    ),
    # a - 2 td: 1.5 - 62, 2.5 - 56, 3.5 - 62, 4.5 - 60
    ("A - td(A) * 2", [-60.5, -53.5, -58.5, -55.5], [-59, -51, -55, -51]),  # (a - td) 2
    # a + td / 2: 1.5 + 15.5, 2.5 + 14, 3.5 + 15.5, 4.5 + 15
    (
        "A + td(A) / 2",
        [17, 16.5, 19, 19.5],
        [16.25, 15.25, 17.25, 17.25],
    ),  # (a + td) / 2
    # a + td * 0.5, the same numbers
    ("A + td(A) * map(L)", [17, 16.5, 19, 19.5], [16.25, 15.25, 17.25, 17.25]),
    # a + td^2: 1.5 + 961, 2.5 + 784, 3.5 + 961, 4.5 + 900
    (
        "A + td(A) * td(A)",
        [962.5, 786.5, 964.5, 904.5],
        [1007.5, 854, 1069.5, 1035],  # (a + td) td
    ),
    # a + td / td = a + 1
    (
        "A + td(A) / td(A)",
        [2.5, 3.5, 4.5, 5.5],
        [32.5 / 31, 30.5 / 28, 34.5 / 31, 34.5 / 30],  # (a + td) / td
    ),
    # a + td f: 1.5 + 31 * 5, 2.5 + 28 * 6, 3.5 + 31 * 7, 4.5 + 30 * 8
    (
        "A + td(A) {*,equal} F",
        [156.5, 170.5, 220.5, 244.5],
        [162.5, 183, 241.5, 276],  # (a + td) f
    ),
    # a + 2 td: 1.5 + 62, 2.5 + 56, 3.5 + 62, 4.5 + 60
    ("A {+,equal} td(A) * 2", [63.5, 58.5, 65.5, 64.5], [65, 61, 69, 69]),  # (a + td) 2
    # The same as A + td(A) / A whatever td() is the duration of
    (
        "A + td(A * 2) / A",
        [22.166667, 13.7, 12.357143, 11.166667],
        [21.666667, 12.2, 9.857143, 7.666667],
    ),
    # f + td % 4: 5 + 31 % 4, 6 + 28 % 4, 7 + 31 % 4, 8 + 30 % 4 = 5 + 3, 6 + 0,
    # 7 + 3, 8 + 2
    (
        "F + td(A) % 4",
        [8, 6, 10, 10],
        [0, 2, 2, 2],  # (f + td) % 4: 36 % 4, 34 % 4, 38 % 4, 38 % 4
    ),
    # a + td / td with the temporal operator between two td(): a + 1
    (
        "A + td(A) {/,equal} td(A)",
        [2.5, 3.5, 4.5, 5.5],
        [32.5 / 31, 30.5 / 28, 34.5 / 31, 34.5 / 30],  # (a + td) / td
    ),
    # a + 2 td = 63.5, 58.5, 65.5, 64.5 is greater than 64 on March and April
    (
        "if(A + td(A) * 2 > 64, A, 0)",
        [0, 0, 3.5, 4.5],
        [1.5, 0, 3.5, 4.5],
    ),  # 2 (a + td)
]

# Forms with td() left of the operator that no version read: the result is the
# duration, times a number or divided by a map
NEWLY_READ = [
    # 2 td: 62, 56, 62, 60
    ("td(A) * 2", [62, 56, 62, 60]),
    # td / a: 31 / 1.5, 28 / 2.5, 31 / 3.5, 30 / 4.5
    ("td(A) / A", [20.666667, 11.2, 8.857143, 6.666667]),
    # 2 td + a: 62 + 1.5, 56 + 2.5, 62 + 3.5, 60 + 4.5
    ("td(A) * 2 + A", [63.5, 58.5, 65.5, 64.5]),
    # 62 > 60 on January and March only
    ("if(td(A) * 2 > 60, A, 0)", [1.5, 0, 3.5, 0]),
]

# The tree and the value of these did not change
UNCHANGED = [
    # a * td * 2: 1.5 * 62, 2.5 * 56, 3.5 * 62, 4.5 * 60
    ("A * td(A) * 2", [93, 140, 217, 270]),
    # a - td - 1: 1.5 - 32, 2.5 - 29, 3.5 - 32, 4.5 - 31
    ("A - td(A) - 1", [-30.5, -26.5, -28.5, -26.5]),
    # (a + td) / a: 32.5 / 1.5, 30.5 / 2.5, 34.5 / 3.5, 34.5 / 4.5
    ("(A + td(A)) / A", [21.666667, 12.2, 9.857143, 7.666667]),
    # a temporal condition: 31 > 30 on January and March only
    ("if(td(A) > 30, A, 0)", [1.5, 0, 3.5, 0]),
]

# Forms with td() behind a number or left of a weaker operator are no
# productions and stay refused
REFUSED = ["A + 2 * td(A)", "td(A) + A"]


@pytest.fixture(scope="module")
def durations(temporal_module_session):
    """The datasets A, F and E and the map L without time stamp"""
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
    create_stds(
        tools,
        "strds",
        "F",
        [
            MapSpec(f"f{number}", 4 + number, start, end)
            for number, (start, end) in enumerate(MONTHS, start=1)
        ],
    )
    create_stds(
        tools,
        "strds",
        "E",
        [
            MapSpec(
                "e1",
                1,
                datetime.datetime(2001, 1, 5),
                datetime.datetime(2001, 1, 6),
            )
        ],
    )
    tools.r_mapcalc(expression="L = 0.5")
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(durations):
    """Replace the fixture of conftest.py: the caches run through durations"""


def run(runner, expression, basename, **options):
    return outcome_of_runner(KIND, expression, runner, basename, **options)


def values(result):
    """The value of each map of an outcome; every input map is constant"""
    return [pytest.approx(value, rel=1e-5) for value in constant_values(result)]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new", "old"), CHANGED)
def test_td_binds_as_operand_of_the_stronger_operator(
    durations, runner, expression, new, old
):
    assert new != old
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new"), NEWLY_READ)
def test_td_as_left_operand_is_read(durations, runner, expression, new):
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize(("expression", "new"), UNCHANGED)
def test_forms_with_td_that_were_right_keep_their_value(
    durations, runner, expression, new
):
    assert values(run(runner, expression, "fa")) == new


@pytest.mark.parametrize("runner", ["reference", "classic"])
@pytest.mark.parametrize("expression", REFUSED)
def test_forms_without_a_production_stay_refused(durations, runner, expression):
    assert run(runner, expression, "fa")["error"] == "SyntaxError"


@pytest.mark.parametrize(
    "expression",
    [row[0] for row in CHANGED + NEWLY_READ + UNCHANGED],
)
def test_the_profile_computes_what_the_reference_computes(durations, expression):
    """Also the time stamps and names, which the tests above leave out"""
    reference = reference_outcome(KIND, expression, register_null=True)
    profile = run("classic", expression, "fb")
    assert compare(KIND, expression, reference, profile) is None


# The argument of td() does not matter. The dataset A has the maps a1 to a4.
@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_td_of_a_neighbour_map(durations, runner):
    """A[1] has no successor for April; the duration is that of the result map

    January to March: a + td / a as in the first row, 1.5 + 31 / 1.5,
    2.5 + 28 / 2.5, 3.5 + 31 / 3.5. Before the correction (a + td) / a:
    32.5 / 1.5, 30.5 / 2.5, 34.5 / 3.5.
    """
    result = run(runner, "A + td(A[1]) / A", "fa")
    assert values(result) == [22.166667, 13.7, 12.357143]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_td_of_a_counted_map(durations, runner):
    """A {#,contains} E counts E in the January map only; td() is its duration

    1.5 + 31 / 1.5 = 22.1667. Before the correction (1.5 + 31) / 1.5 = 21.6667.
    """
    result = run(runner, "A + td(A {#,contains} E) / A", "fa")
    assert values(result) == [22.166667]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_td_of_a_map_with_a_time_stamp(durations, runner):
    """tmap(a1) is the January map: 1.5 + 31 / 1.5 on January only"""
    result = run(runner, "A + td(tmap(a1)) / A", "fa")
    assert values(result) == [22.166667]


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
def test_the_granularity_mode_groups_td_too(durations, runner):
    """A has one granularity, one month, so -g leaves the maps as they are"""
    result = run(runner, "A + td(A) / A", "fa", granularity=True)
    assert values(result) == [22.166667, 13.7, 12.357143, 11.166667]
