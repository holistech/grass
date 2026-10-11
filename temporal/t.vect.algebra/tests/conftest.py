"""Fixtures for t.vect.algebra tests"""

import os
from types import SimpleNamespace

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.tools import Tools

DAYS = ["2001-01-01", "2001-01-02", "2001-01-03", "2001-01-04", "2001-01-05"]


def write_squares(path, squares):
    """Write 10x10 squares given by their lower left corner in standard format"""
    lines = []
    for x, y in squares:
        corners = [(x, y), (x + 10, y), (x + 10, y + 10), (x, y + 10), (x, y)]
        lines.append(f"B {len(corners)}")
        lines.extend(f" {cx} {cy}" for cx, cy in corners)
        lines.append(f"C 1 1\n {x + 5} {y + 5}\n 1 1")
    path.write_text("\n".join(lines) + "\n")


def import_standard(tools, tmp_path, name, body):
    """Import vector features written in the GRASS ASCII standard format"""
    path = tmp_path / f"{name}.txt"
    path.write_text(body)
    tools.v_in_ascii(input=path, output=name, format="standard", flags="n")


def import_points(tools, tmp_path, name, points):
    """Import points given as (x, y) tuples"""
    path = tmp_path / f"{name}.txt"
    path.write_text("".join(f"{x}|{y}|{i}\n" for i, (x, y) in enumerate(points, 1)))
    tools.v_in_ascii(input=path, output=name, format="point", separator="pipe")


def import_square(tools, tmp_path, name, x, y):
    """Import one 10x10 area with centroid"""
    import_standard(
        tools,
        tmp_path,
        name,
        f"B 5\n {x} {y}\n {x + 10} {y}\n {x + 10} {y + 10}\n {x} {y + 10}\n"
        f" {x} {y}\nC 1 1\n {x + 5} {y + 5}\n 1 1\n",
    )


def import_line(tools, tmp_path, name, x, y):
    """Import one horizontal line of length 10"""
    import_standard(tools, tmp_path, name, f"L 2 1\n {x} {y}\n {x + 10} {y}\n 1 1\n")


def create_stvds(tools, name, maps_and_times):
    """Create a STVDS and register maps with (map, start, end) triples"""
    tools.t_create(
        output=name, type="stvds", temporaltype="absolute", title=name, description=name
    )
    for vector, start, end in maps_and_times:
        tools.t_register(input=name, type="vector", maps=vector, start=start, end=end)


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
    aa       1-3  one square each at x=0, 20, 40 (y=0)
    ab       1-3  one square each at x=5, 25, 70 (y=0); the third
                  one does not overlap the third map of aa
    ac       1-3  two squares each, at x=0 and x=50 (y=0 and y=20)
    la       1-3  one line each at y=5, x=0, 20, 40
    wide     1-4  aa/ab-like squares with a 2-day interval:
                  w1 = days 1-2 (x=5), w2 = days 3-4 (x=45)
    ======== ==== ================================================

    The single map "ev" (square at x=2) has the time stamp 2001-01-02.
    """
    tmp_path = tmp_path_factory.mktemp("t_vect_algebra")
    project = tmp_path / "project"
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
        tools.g_region(n=100, s=0, e=100, w=0, res=10)
        day = DAYS

        pa = []
        for i in (1, 2, 3):
            import_points(
                tools, tmp_path, f"pa{i}", [(10 * j, 10 * i) for j in range(i)]
            )
            pa.append((f"pa{i}", day[i - 1], day[i]))
        create_stvds(tools, "pa", pa)

        pb = []
        for i in (1, 2, 3):
            import_points(tools, tmp_path, f"pb{i}", [(3 + 10 * i, 5), (4 + 10 * i, 6)])
            pb.append((f"pb{i}", day[i - 1], day[i]))
        create_stvds(tools, "pb", pb)

        aa, ab, la = [], [], []
        for i, (xa, xb) in enumerate([(0, 5), (20, 25), (40, 70)], 1):
            import_square(tools, tmp_path, f"aa{i}", xa, 0)
            import_square(tools, tmp_path, f"ab{i}", xb, 0)
            import_line(tools, tmp_path, f"la{i}", xa, 5)
            aa.append((f"aa{i}", day[i - 1], day[i]))
            ab.append((f"ab{i}", day[i - 1], day[i]))
            la.append((f"la{i}", day[i - 1], day[i]))
        create_stvds(tools, "aa", aa)
        create_stvds(tools, "ab", ab)
        create_stvds(tools, "la", la)

        ac = []
        for i in (1, 2, 3):
            import_standard(
                tools,
                tmp_path,
                f"ac{i}",
                "B 5\n 0 0\n 10 0\n 10 10\n 0 10\n 0 0\nC 1 1\n 5 5\n 1 1\n"
                "B 5\n 50 20\n 60 20\n 60 30\n 50 30\n 50 20\nC 1 1\n 55 25\n 1 1\n",
            )
            ac.append((f"ac{i}", day[i - 1], day[i]))
        create_stvds(tools, "ac", ac)

        import_square(tools, tmp_path, "wide1", 5, 0)
        import_square(tools, tmp_path, "wide2", 45, 0)
        create_stvds(
            tools,
            "wide",
            [("wide1", day[0], day[2]), ("wide2", day[2], day[4])],
        )

        import_square(tools, tmp_path, "ev", 2, 0)
        tools.t_register(type="vector", maps="ev", start=day[1], end=day[2])

        tgis.init(True)
        yield SimpleNamespace(session=session, tools=tools, tmp_path=tmp_path)
