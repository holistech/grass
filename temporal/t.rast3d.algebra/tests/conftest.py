"""Fixtures for t.rast3d.algebra tests"""

from types import SimpleNamespace

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    register_stds,
    timestamp,
)
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


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
    # The algebra parsers of the tests run in this process, which is much
    # faster than one tool call per expression. That needs the session in
    # os.environ and grass.temporal initialised, which temporal_session does.
    project = tmp_path_factory.mktemp("t_rast3d_algebra") / "project"
    with temporal_session(project) as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=3, s=0, e=3, w=0, t=3, b=0, res=1, res3=1, tbres=1)

        create_stds(
            tools,
            "str3ds",
            "A",
            [MapSpec(f"a{i}", i, day(i - 1), day(i)) for i in range(1, 5)],
        )
        create_stds(
            tools,
            "str3ds",
            "B",
            [MapSpec(f"b{i}", 10 * i, day(i - 1), day(i)) for i in range(1, 5)],
        )
        # The value of a D map is the depth of the cell, not a constant, so
        # the maps are made here and only registered.
        for i in range(1, 4):
            tools.r3_mapcalc(expression=f"d{i} = depth()")
        register_stds(
            tools,
            "str3ds",
            "D",
            [MapSpec(f"d{i}", None, day(i - 1), day(i)) for i in range(1, 4)],
        )
        create_stds(
            tools,
            "str3ds",
            "W",
            [MapSpec("w1", 100, day(0), day(2)), MapSpec("w2", 200, day(2), day(4))],
        )
        tools.r3_mapcalc(expression="single = 1000")
        # E lies east of A, so its maps are made in a shifted region.
        tools.g_region(w=10, e=13)
        tools.r3_mapcalc(expression="e1 = 7")
        tools.r3_mapcalc(expression="e2 = 8")
        tools.g_region(w=0, e=3)
        register_stds(
            tools,
            "str3ds",
            "E",
            [MapSpec("e1", 7, day(0), day(1)), MapSpec("e2", 8, day(1), day(2))],
        )
        create_stds(
            tools,
            "str3ds",
            "Q",
            [MapSpec("q1", 5, day(0, hours=12), day(1, hours=12))],
        )
        create_stds(
            tools,
            "str3ds",
            "Q2",
            [MapSpec("q2", 50, day(3, hours=12), day(4, hours=12))],
        )
        tools.t_register(
            type="raster_3d", maps="single", start=timestamp(1), end=timestamp(2)
        )
        yield SimpleNamespace(session=session, tools=tools)


@pytest.fixture(scope="module")
def io_cache_storage():
    """Answers of the test-only caches, shared by the tests of one module"""
    return io_cache.CacheStorage()


@pytest.fixture(autouse=True)
def cached_io(request, io_cache_storage):
    """Run the test with the caches of grass.temporal.testing.io_cache.cached_io"""
    if request.node.get_closest_marker("real_io"):
        yield
        return
    with io_cache.cached_io(io_cache_storage):
        yield
