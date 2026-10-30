"""Fixtures for t.vect.algebra tests"""

from types import SimpleNamespace

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.data import (
    MapSpec,
    day,
    horizontal_line,
    import_ascii_vector,
    points_map,
    register_stds,
    square_area,
    timestamp,
)
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools


def create_stvds(tools, name, maps_and_times, **options):
    """Create a STVDS and register maps with (map, start, end) triples

    The maps exist already; their coordinates are the point of the datasets,
    so they are not made by make_map(), which writes one point per map.
    """
    register_stds(
        tools,
        "stvds",
        name,
        [MapSpec(vector, None, start, end) for vector, start, end in maps_and_times],
        **options,
    )


@pytest.fixture(scope="module")
def vector_series(tmp_path_factory):
    """Session with space time vector datasets of points, lines and areas.

    All datasets use daily intervals starting 2001-01-01 unless noted. Areas
    are 10x10 squares given by the lower left corner; lines are horizontal
    with length 10.

    ======== ==== ================================================
    dataset  days content
    ======== ==== ================================================
    pa       1-3  map i has i points (1, 2, 3 points)
    pb       1-3  map i has 2 points
    pc       1-3  two points at (0, 0) and (10, 10), so the extent is a square
    aa       1-3  one square each at x=0, 20, 40 (y=0)
    ab       1-3  one square each at x=5, 25, 70 (y=0); the third
                  one does not overlap the third map of aa
    ac       1-3  two squares each, at x=0 and x=50 (y=0 and y=20)
    la       1-3  one line each at y=5, x=0, 20, 40
    wide     1-4  aa/ab-like squares with a 2-day interval:
                  w1 = days 1-2 (x=5), w2 = days 3-4 (x=45)
    ======== ==== ================================================

    rel      0-2  relative time, copies of pa1 and pa2 (days 0-1 and 1-2)

    The single map "ev" (square at x=2) has the time stamp 2001-01-02.
    """
    tmp_path = tmp_path_factory.mktemp("t_vect_algebra")
    # The algebra parsers of the tests run in this process, which is much
    # faster than one tool call per expression. That needs the session in
    # os.environ and grass.temporal initialised, which temporal_session does.
    with temporal_session(tmp_path / "project") as session:
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=100, s=0, e=100, w=0, res=10)
        days = [day(n) for n in range(5)]

        pa = []
        for i in (1, 2, 3):
            points_map(tools, tmp_path, f"pa{i}", [(10 * j, 10 * i) for j in range(i)])
            pa.append((f"pa{i}", days[i - 1], days[i]))
        create_stvds(tools, "pa", pa)

        pb = []
        for i in (1, 2, 3):
            points_map(tools, tmp_path, f"pb{i}", [(3 + 10 * i, 5), (4 + 10 * i, 6)])
            pb.append((f"pb{i}", days[i - 1], days[i]))
        create_stvds(tools, "pb", pb)

        pc = []
        for i in (1, 2, 3):
            points_map(tools, tmp_path, f"pc{i}", [(0, 0), (10, 10)])
            pc.append((f"pc{i}", days[i - 1], days[i]))
        create_stvds(tools, "pc", pc)

        aa, ab, la = [], [], []
        for i, (xa, xb) in enumerate([(0, 5), (20, 25), (40, 70)], 1):
            square_area(tools, tmp_path, f"aa{i}", xa, 0)
            square_area(tools, tmp_path, f"ab{i}", xb, 0)
            horizontal_line(tools, tmp_path, f"la{i}", xa, 5)
            aa.append((f"aa{i}", days[i - 1], days[i]))
            ab.append((f"ab{i}", days[i - 1], days[i]))
            la.append((f"la{i}", days[i - 1], days[i]))
        create_stvds(tools, "aa", aa)
        create_stvds(tools, "ab", ab)
        create_stvds(tools, "la", la)

        ac = []
        for i in (1, 2, 3):
            import_ascii_vector(
                tools,
                tmp_path,
                f"ac{i}",
                "standard",
                "B 5\n 0 0\n 10 0\n 10 10\n 0 10\n 0 0\nC 1 1\n 5 5\n 1 1\n"
                "B 5\n 50 20\n 60 20\n 60 30\n 50 30\n 50 20\nC 1 1\n 55 25\n 1 1\n",
                flags="n",
            )
            ac.append((f"ac{i}", days[i - 1], days[i]))
        create_stvds(tools, "ac", ac)

        square_area(tools, tmp_path, "wide1", 5, 0)
        square_area(tools, tmp_path, "wide2", 45, 0)
        create_stvds(
            tools,
            "wide",
            [("wide1", days[0], days[2]), ("wide2", days[2], days[4])],
        )

        tools.g_copy(vector="pa1,rp1")
        tools.g_copy(vector="pa2,rp2")
        create_stvds(
            tools,
            "rel",
            [("rp1", 0, 1), ("rp2", 1, 2)],
            temporaltype="relative",
            unit="days",
        )

        square_area(tools, tmp_path, "ev", 2, 0)
        tools.t_register(type="vector", maps="ev", start=timestamp(1), end=timestamp(2))
        yield SimpleNamespace(session=session, tools=tools, tmp_path=tmp_path)


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
