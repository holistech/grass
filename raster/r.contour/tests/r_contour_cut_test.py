"""Test that cut applies to the lines of the output map

The traced lines are snapped, broken at intersections, freed of duplicates
and merged before the map is closed. Snapping joins vertices that lie closer
together than the snapping distance, and a closed line that runs there and
back along cells equal to its level is broken into two equal halves, one of
which is removed. A line traced with enough points can thus end with fewer.
Before 2026-11-04 cut was applied only while tracing, and the map could hold
such lines. Breaking also splits a line where it touches another one, so cut
applies to groups of lines joined at end nodes: a group is kept or deleted
whole, its points counted with each joint once, and no gap is cut into a
line.
"""

import collections
import io
import os

import pytest

import grass.script as gs
from grass.tools import Tools

# A map of whole numbers with step 1: many cells equal a level. Measured
# 2026-11-04: before the change, cut 3 left a line of 2 points that shares
# no end with another line, cut 4 lines of 2 and 3 points.
ROUNDED = "round(20 + 8 * sin(row() * 7.0) * cos(col() * 11.0))"
# The closed line of level 12 around column 6 runs there and back: 13 points
# as traced, 9 after snapping, one half of 5 points after breaking and
# removing duplicates (measured 2026-11-04 with a build that printed the
# lines after each step).
THERE_AND_BACK = "round(20 + 8 * sin(row() * 7.0) * cos(col() * 29.0))"
PIECES = "round(20 + 8 * sin(row() * 37.0) * cos(col() * 11.0))"


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
    text = tools.v_out_ascii(input="lines", format="standard", precision=17).text
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if not words or words[0] not in {"L", "B"}:
            continue
        lines.append(
            [
                tuple(float(v) for v in next(rows).split()[:2])
                for _ in range(int(words[1]))
            ]
        )
        for _ in range(int(words[2])):
            next(rows)
    return lines


def groups_below(lines, cut):
    """Return the groups of lines joined at end nodes with fewer than cut points

    A group counts the points of its lines minus one for every line after the
    first, the rule of r.contour; a single line counts its points.
    """
    parent = {}

    def root(point):
        while parent.setdefault(point, point) != point:
            point = parent[point]
        return point

    for line in lines:
        parent[root(line[0])] = root(line[-1])
    groups = collections.defaultdict(list)
    for line in lines:
        groups[root(line[0])].append(line)
    return [
        group
        for group in groups.values()
        if sum(len(line) for line in group) - len(group) + 1 < cut
    ]


@pytest.mark.parametrize("expression", [ROUNDED, THERE_AND_BACK])
@pytest.mark.parametrize("cut", [3, 4, 5, 8])
def test_cut_applies_after_snapping(tools, expression, cut):
    tools.g_region(n=20, s=0, w=0, e=20, res=1)
    tools.r_mapcalc(expression=f"m = {expression}")

    tools.r_contour(input="m", output="lines", step=1, cut=cut)

    lines = read_lines(tools)
    assert lines
    assert groups_below(lines, cut) == []


def test_pieces_of_a_longer_line_are_kept(tools):
    # The lines of this map touch each other after snapping and are broken
    # there into pieces; with cut 5 pieces of 2 and 3 points remain, because
    # their groups have 5 points or more (measured 2026-11-05). Every end of
    # a line inside the region meets another line, none is left open by a
    # removed piece. A line ends alone only at the border of the region,
    # where the node centres lie at 0.5 and 19.5; the tolerance covers the
    # snapping distance of 0.001.
    tools.g_region(n=20, s=0, w=0, e=20, res=1)
    tools.r_mapcalc(expression=f"m = {PIECES}")

    tools.r_contour(input="m", output="lines", step=1, cut=5)

    lines = read_lines(tools)
    assert any(len(line) < 5 for line in lines)
    ends = collections.Counter(point for line in lines for point in (line[0], line[-1]))
    for point, count in ends.items():
        if count == 1:
            assert any(
                abs(value - border) < 0.002 for value in point for border in (0.5, 19.5)
            ), point


# Level 0 is the lowest value; its cells give a closed line of 4 points and a
# spur of 2 points joined at one node, 5 points in all (found in the review
# of 2026-11-05 on a larger random map, of which this is a window).
TRIANGLE_AND_SPUR = [
    [3, 5, 1, 3, 2],
    [3, 1, 0, 1, 2],
    [3, 3, 0, 1, 1],
    [0, 5, 0, 0, 1],
    [3, 4, 2, 1, 2],
]


def contour_lines_of_level_zero(tools, cut):
    """Run r.contour on TRIANGLE_AND_SPUR and return the lines of level 0"""
    body = "\n".join(" ".join(str(value) for value in row) for row in TRIANGLE_AND_SPUR)
    tools.g_region(n=5, s=0, w=0, e=5, res=1)
    tools.r_in_ascii(
        input=io.StringIO(
            "north: 5\nsouth: 0\neast: 5\nwest: 0\nrows: 5\ncols: 5\n"
            f"type: dcell\n{body}\n"
        ),
        output="m",
        overwrite=True,
    )
    tools.r_contour(input="m", output="lines", step=1, cut=cut, overwrite=True)
    text = tools.v_out_ascii(input="lines", format="standard", where="level = 0").text
    return [
        [tuple(float(v) for v in vertex.split()[:2]) for vertex in block]
        for block in _vertex_blocks(text)
    ]


def _vertex_blocks(text):
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if words and words[0] in {"L", "B"}:
            yield [next(rows) for _ in range(int(words[1]))]
            for _ in range(int(words[2])):
                next(rows)


def test_a_group_of_short_pieces_is_removed(tools):
    # Each piece meets the other, so a rule that keeps a short line with a
    # neighbour kept both (before the review of 2026-11-05).
    assert contour_lines_of_level_zero(tools, 6) == []


def test_a_group_with_cut_points_is_kept(tools):
    lines = contour_lines_of_level_zero(tools, 5)

    assert sorted(lines) == [
        [(2.5, 2.5), (2.5, 1.5), (3.5, 1.5), (2.5, 2.5)],
        [(2.5, 2.5), (2.5, 3.5)],
    ]
