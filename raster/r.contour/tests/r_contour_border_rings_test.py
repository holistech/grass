"""Test closed lines and saddle lines at the border of the region

A closed line is searched from the top edge of a cell. Before 2026-11-04
only the cells off the border of the region were searched, so a closed line
whose crossings of top edges all lie in cells on the border was lost. A
line with ends whose end cells are saddles was lost at the border of the
region when the other segment of the saddle had marked the cell as hit;
the passes along the border now ask whether the start edge was passed.
Along null cells both were already found.
"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def tools(tmp_path):
    """Tools in a session of an XY project"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        yield tools


def read_lines(tools):
    """Return the vertices (x, y) of each line of the map lines"""
    text = tools.v_out_ascii(input="lines", format="standard").text
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if not words or words[0] not in {"L", "B"}:
            continue
        lines.append(
            tuple(
                tuple(round(float(value), 9) for value in next(rows).split()[:2])
                for _ in range(int(words[1]))
            )
        )
        for _ in range(int(words[2])):
            next(rows)
    return lines


def canonical(lines):
    """Return the lines without direction and, if closed, without start"""
    result = []
    for points in lines:
        if len(points) > 2 and points[0] == points[-1]:
            ring = list(points[:-1])
            forms = [ring[i:] + ring[:i] for i in range(len(ring))]
            forms += [form[::-1] for form in forms]
            result.append(("closed", min(tuple(form) for form in forms)))
        else:
            result.append(("open", min(tuple(points), tuple(points[::-1]))))
    return sorted(result)


CHESSBOARD = "if((row() + col()) % 2 == 0, 1.0, 0.0)"

# name: (rows and columns, r.mapcalc expression, level, lines, closed lines)
# Chessboard: every node of value 1 gets a line through the middles of its
# edges (each cell is a saddle whose mean 0.5 counts as below the level,
# so it cuts off its corners of value 1). The line is closed around a node
# off the border and has two ends otherwise. 4 by 4 nodes: 8 of value 1,
# 2 off the border; 8 by 8: 32, 18 off the border. The dome of 6 by 6: the
# inner 4 by 4 nodes have values of 45.5 and more, the outer ring 43.5 and
# less, so the level 45 gives one closed line through the cells of the
# outer ring only.
RINGS = {
    "dome of 3 by 3": (3, "if(row() == 2 && col() == 2, 1.0, 0.0)", 0.5, 1, 1),
    "chessboard of 4 by 4": (4, CHESSBOARD, 0.5, 8, 2),
    "chessboard of 8 by 8": (8, CHESSBOARD, 0.5, 32, 18),
    "dome of 6 by 6": (6, "50 - (row() - 3.5)^2 - (col() - 3.5)^2", 45, 1, 1),
}


@pytest.mark.parametrize("name", RINGS)
def test_ring_through_border_cells(tools, name):
    size, expression, level, count, closed = RINGS[name]
    tools.g_region(n=size, s=0, w=0, e=size, res=1)
    tools.r_mapcalc(expression=f"m = {expression}")

    tools.r_contour(input="m", output="lines", levels=level)

    lines = canonical(read_lines(tools))
    assert len(lines) == count
    assert sum(1 for kind, _ in lines if kind == "closed") == closed
    info = tools.v_info(map="lines", flags="t").keyval
    assert info["lines"] == count
    assert info["nodes"] == closed + 2 * (count - closed)


def test_ring_of_the_dome_of_three_by_three(tools):
    # The four edges from the centre node (value 1) to its neighbours (0)
    # are crossed in the middle. Node centres lie at x = col - 0.5,
    # y = 3.5 - row.
    tools.g_region(n=3, s=0, w=0, e=3, res=1)
    tools.r_mapcalc(expression="m = if(row() == 2 && col() == 2, 1.0, 0.0)")

    tools.r_contour(input="m", output="lines", levels=0.5)

    ring = ((1.0, 1.5), (1.5, 1.0), (2.0, 1.5), (1.5, 2.0))
    assert canonical(read_lines(tools)) == canonical([(*ring, ring[0])])


def test_saddle_ends_at_region_border(tools):
    # Nodes 0 0 0 / 1 1 0 / 1 0 1, level 0.5, every crossing in the middle
    # of its edge; node centres at x = col - 0.5, y = 3.5 - row. The saddle
    # cell at the bottom right has the mean 0.5, which counts as below the
    # level, so it cuts off its corners of value 1. The first line runs
    # around the nodes (2, 1), (2, 2), (3, 1) from the bottom to the left
    # border, the second cuts off the node (3, 3). Both segments of that
    # saddle end on border edges, and the first line marked the cell as hit,
    # so the second was lost before.
    tools.g_region(n=3, s=0, w=0, e=3, res=1)
    tools.r_mapcalc(
        expression="m = if((row() == 2 && col() <= 2) || (row() == 3 && col() != 2),"
        " 1.0, 0.0)"
    )

    tools.r_contour(input="m", output="lines", levels=0.5)

    expected = [
        ((1.0, 0.5), (1.5, 1.0), (2.0, 1.5), (1.5, 2.0), (0.5, 2.0)),
        ((2.0, 0.5), (2.5, 1.0)),
    ]
    assert canonical(read_lines(tools)) == canonical(expected)
    info = tools.v_info(map="lines", flags="t").keyval
    assert info["lines"] == 2
    assert info["nodes"] == 4
