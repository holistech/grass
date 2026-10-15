"""Fixtures for t.select tests

The fixture builds the same time series for the three dataset types (strds,
stvds, str3ds). All intervals are given in days relative to 2001-01-01
(day 0), start inclusive, end exclusive:

=====  ==========  =============================================
STDS   map         interval
=====  ==========  =============================================
A      a1..a4      [0,10) [10,20) [20,30) [30,40)
B      b1          [10,20)
B      b2          [22,27)
B      b3          [25,35)
B      b4          [0,4)
B      b5          [35,40)
B      b6          [40,50)
B      b7          [-10,0)
B      b8          [0,20)
B      b9          [28,29)
D      d1          [5,45)
=====  ==========  =============================================

Relations of the A maps to the B maps (from the temporal extent definitions,
with the topology builder counting starts and finishes as "during" and
started and finished as "contains"):

=========  =========  =================================
A map      B map      relation
=========  =========  =================================
a1         b1         precedes
a1         b4         started
a1         b7         follows
a1         b8         starts
a2         b1         equal
a2         b8         finishes
a3         b1, b8     follows
a3         b2, b9     contains
a3         b3         overlaps
a4         b3         overlapped
a4         b5         finished
a4         b6         precedes
=========  =========  =================================

The strds fixture has two more datasets, see the series fixture.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    make_map,
    register_stds,
)
from grass.tools import Tools

INTERVALS = {
    "A": [(0, 10), (10, 20), (20, 30), (30, 40)],
    "B": [(10, 20), (22, 27), (25, 35), (0, 4), (35, 40), (40, 50), (-10, 0), (0, 20)]
    + [(28, 29)],
    "D": [(5, 45)],
}

# Map type that each dataset type holds
KINDS = {"strds": "raster", "stvds": "vector", "str3ds": "raster_3d"}

# Tests that skip themselves on the classic algebra. They are the only ones in
# this directory that "-m fixed_algebra" has to leave out, see
# pytest_collection_modifyitems.
SKIP_ON_CLASSIC = {
    "test_dataset_type_function_hints_at_the_classic_flag",
    "test_other_unknown_function_has_no_classic_hint",
    "test_dataset_type_function_works_with_the_classic_flag",
}


def specs(intervals, prefix):
    """MapSpec of the maps <prefix><number>, valued by their number"""
    return [
        MapSpec(f"{prefix}{number}", number, day(start), day(end))
        for number, (start, end) in enumerate(intervals, 1)
    ]


def create_series(tools, kind, stds, intervals, prefix=None):
    """Create a STDS with one map per interval; maps are named <prefix><number>"""
    maps = specs(intervals, prefix or stds.lower())
    if kind == "stvds":
        # v.random points: the shared make_map() writes other geometry.
        for spec in maps:
            tools.v_random(output=spec.name, npoints=1, seed=spec.value)
        register_stds(tools, kind, stds, maps)
    else:
        create_stds(tools, kind, stds, maps)


@pytest.fixture(scope="module")
def series(temporal_module_session):
    """Session with the datasets A, B and D of each type, see module docstring

    For strds there are also

    - S: s1 has the time of a2 but lies outside the computational region of
      the other maps, s2 has the time of a3 and lies inside it
    - the mapset "other" with the dataset X: x1 with the time of a2 and x2
      with the time of a4; it is in the mapset search path

    The session mirrors its environment into os.environ for the module; the
    differential test runs the parsers in this process.
    """
    session = temporal_module_session
    tools = Tools(session=session, overwrite=True)
    tools.g_region(n=3, s=0, e=3, w=0, b=0, t=3, res=1, res3=1, tbres=1)

    for kind in KINDS:
        for stds, intervals in INTERVALS.items():
            create_series(tools, kind, stds, intervals)

    make_map(
        tools,
        "raster",
        "s1",
        1,
        region={"n": 103, "s": 100, "e": 103, "w": 100, "res": 1},
    )
    make_map(tools, "raster", "s2", 2)
    register_stds(
        tools,
        "strds",
        "S",
        [
            MapSpec("s1", 1, day(10), day(20)),
            MapSpec("s2", 2, day(20), day(30)),
        ],
    )

    tools.g_mapset(mapset="other", flags="c")
    create_series(tools, "strds", "X", [(10, 20), (30, 40)], prefix="x")
    tools.g_mapset(mapset="PERMANENT")
    tools.g_mapsets(mapset="other", operation="add")
    return SimpleNamespace(session=session)


@pytest.fixture(autouse=True)
def algebra(series, algebra_setting):
    """Run every test once on the core and once on the classic algebra

    t.select reads the environment variable from the session the tools use.
    """
    series.session.env[ALGEBRA_VARIABLE] = algebra_setting
    yield algebra_setting
    series.session.env.pop(ALGEBRA_VARIABLE, None)


def pytest_collection_modifyitems(items):
    """Mark the tests of this directory that choose their algebra themselves

    Every test here does, by the fixture above or in its own body, except the
    classic variants that skip themselves: "-m fixed_algebra" collects
    the 371 tests that pass. A hook is used because a module-level mark would
    include the skipped ones. Called with the items of the whole session, so
    only the items below this directory are touched.
    """
    here = Path(__file__).parent
    for item in items:
        if item.path.parent != here:
            continue
        params = getattr(item, "callspec", None)
        classic = (
            params is not None and params.params.get("algebra_setting") == "classic"
        )
        if classic and item.originalname in SKIP_ON_CLASSIC:
            continue
        item.add_marker(pytest.mark.fixed_algebra)
