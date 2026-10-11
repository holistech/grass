"""Fixtures for t.rast3d.algebra tests"""

import os
from types import SimpleNamespace

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.tools import Tools


def create_str3ds(tools, name, maps_and_times):
    """Create a STR3DS and register maps given as (map, start, end) triples"""
    tools.t_create(
        output=name,
        type="str3ds",
        temporaltype="absolute",
        title=name,
        description=name,
    )
    for raster, start, end in maps_and_times:
        tools.t_register(
            input=name, type="raster_3d", maps=raster, start=start, end=end
        )


@pytest.fixture(scope="module")
def series_3d(tmp_path_factory):
    """Session with space time 3D raster datasets on a 3x3x3 grid.

    All cells of a map have one value, unless noted. Daily intervals start on
    2001-01-01.

    ======== ==== =================================================
    dataset  days content
    ======== ==== =================================================
    A        1-4  value = map number (1, 2, 3, 4)
    B        1-4  value = 10 * map number
    W        1-4  w1 = 100 on days 1-3, w2 = 200 on days 3-5
    D        1-3  d1..d3: value is the depth of the cell (1..3)
    ======== ==== =================================================

    E        e1 = 7, e2 = 8 on days 1-2, but located east of A (x 10 to 13)
    Q        q1 = 5 from 2001-01-01 12:00 to 2001-01-02 12:00
    Q2       q2 = 50 from 2001-01-04 12:00 to 2001-01-05 12:00

    The single map "single" (value 1000) has the time stamp 2001-01-02.
    """
    project = tmp_path_factory.mktemp("t_rast3d_algebra") / "project"
    gs.create_project(project)

    # tgis reads the session from os.environ, so it is mirrored there for the
    # duration of the module; the algebra parsers then run in this process,
    # which is much faster than one tool call per expression.
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=3, s=0, e=3, w=0, t=3, b=0, res=1, res3=1, tbres=1)
        days = [f"2001-01-{n:02d}" for n in range(1, 7)]

        for i in range(1, 5):
            tools.r3_mapcalc(expression=f"a{i} = {i}")
            tools.r3_mapcalc(expression=f"b{i} = {10 * i}")
        for i in range(1, 4):
            tools.r3_mapcalc(expression=f"d{i} = depth()")
        tools.r3_mapcalc(expression="w1 = 100")
        tools.r3_mapcalc(expression="w2 = 200")
        tools.r3_mapcalc(expression="single = 1000")
        tools.g_region(w=10, e=13)
        tools.r3_mapcalc(expression="e1 = 7")
        tools.r3_mapcalc(expression="e2 = 8")
        tools.g_region(w=0, e=3)
        tools.r3_mapcalc(expression="q1 = 5")
        tools.r3_mapcalc(expression="q2 = 50")

        create_str3ds(
            tools, "A", [(f"a{i}", days[i - 1], days[i]) for i in range(1, 5)]
        )
        create_str3ds(
            tools, "B", [(f"b{i}", days[i - 1], days[i]) for i in range(1, 5)]
        )
        create_str3ds(
            tools, "D", [(f"d{i}", days[i - 1], days[i]) for i in range(1, 4)]
        )
        create_str3ds(tools, "W", [("w1", days[0], days[2]), ("w2", days[2], days[4])])
        create_str3ds(tools, "E", [("e1", days[0], days[1]), ("e2", days[1], days[2])])
        create_str3ds(
            tools,
            "Q",
            [("q1", "2001-01-01 12:00:00", "2001-01-02 12:00:00")],
        )
        create_str3ds(
            tools,
            "Q2",
            [("q2", "2001-01-04 12:00:00", "2001-01-05 12:00:00")],
        )
        tools.t_register(type="raster_3d", maps="single", start=days[1], end=days[2])

        tgis.init(True)
        yield SimpleNamespace(session=session, tools=tools)
