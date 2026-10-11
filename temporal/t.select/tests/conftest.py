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

import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import grass.script as gs
from grass.tools import Tools

DAY0 = datetime(2001, 1, 1)

INTERVALS = {
    "A": [(0, 10), (10, 20), (20, 30), (30, 40)],
    "B": [(10, 20), (22, 27), (25, 35), (0, 4), (35, 40), (40, 50), (-10, 0), (0, 20)]
    + [(28, 29)],
    "D": [(5, 45)],
}

# type option, map type of t.register, name of the list module
KINDS = {
    "strds": ("raster", "t_rast_list"),
    "stvds": ("vector", "t_vect_list"),
    "str3ds": ("raster_3d", "t_rast3d_list"),
}


def timestamp(day):
    """Date string of the day offset relative to 2001-01-01"""
    return (DAY0 + timedelta(days=day)).strftime("%Y-%m-%d")


def create_map(tools, kind, name, number):
    """Create one map of the given STDS type"""
    if kind == "strds":
        tools.r_mapcalc(expression=f"{name} = {number}")
    elif kind == "str3ds":
        tools.r3_mapcalc(expression=f"{name} = {number}")
    else:
        tools.v_random(output=name, npoints=1, seed=number)


def create_series(tools, kind, stds, intervals, tmp_path, prefix=None):
    """Create a STDS with one map per interval; maps are named <prefix><number>"""
    prefix = prefix or stds.lower()
    tools.t_create(
        type=kind,
        output=stds,
        temporaltype="absolute",
        title=stds,
        description=stds,
    )
    lines = []
    for number, (start, end) in enumerate(intervals, 1):
        name = f"{prefix}{number}"
        create_map(tools, kind, name, number)
        lines.append(f"{name}|{timestamp(start)}|{timestamp(end)}")
    file = tmp_path / f"{kind}_{stds}.txt"
    file.write_text("\n".join(lines) + "\n")
    tools.t_register(type=KINDS[kind][0], input=stds, file=file)


@pytest.fixture(scope="module")
def series(tmp_path_factory):
    """Session with the datasets A, B and D of each type, see module docstring

    For strds there are also

    - S: s1 has the time of a2 but lies outside the computational region of
      the other maps, s2 has the time of a3 and lies inside it
    - the mapset "other" with the dataset X: x1 with the time of a2 and x2
      with the time of a4; it is in the mapset search path
    """
    tmp_path = tmp_path_factory.mktemp("t_select")
    project = tmp_path / "project"
    gs.create_project(project)

    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=3, s=0, e=3, w=0, b=0, t=3, res=1, res3=1, tbres=1)

        for kind in KINDS:
            for stds, intervals in INTERVALS.items():
                create_series(tools, kind, stds, intervals, tmp_path)

        tools.t_create(
            type="strds",
            output="S",
            temporaltype="absolute",
            title="S",
            description="S",
        )
        tools.g_region(n=103, s=100, e=103, w=100, res=1)
        tools.r_mapcalc(expression="s1 = 1")
        tools.g_region(n=3, s=0, e=3, w=0, res=1)
        tools.r_mapcalc(expression="s2 = 2")
        spatial = tmp_path / "S.txt"
        spatial.write_text(
            f"s1|{timestamp(10)}|{timestamp(20)}\ns2|{timestamp(20)}|{timestamp(30)}\n"
        )
        tools.t_register(input="S", file=spatial)

        tools.g_mapset(mapset="other", flags="c")
        create_series(
            tools,
            "strds",
            "X",
            [(10, 20), (30, 40)],
            tmp_path,
            prefix="x",
        )
        tools.g_mapset(mapset="PERMANENT")
        tools.g_mapsets(mapset="other", operation="add")

        yield SimpleNamespace(session=session)
