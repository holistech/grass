"""Test that a level equal to the lowest or highest value gets a contour line

A cell whose value equals a level is moved off the level before the lines
are traced, so that no line runs exactly through a cell centre. The move is
value * DBL_EPSILON: up for a positive value, down for a negative one and
none for 0; a cell left on the level counts as below it. Before 2026-11-04 a
level equal to the lowest value of a positive map thus had no cell below it
and no line, as had a level equal to the highest value of a negative map or
the highest value 0. These cells are now moved outwards while the line of
that level is traced, so the level gets a line through them.
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
    """Return the level and the vertices of each line of the map lines

    The coordinates are read with 17 digits, which give back the double.
    """
    text = tools.v_out_ascii(input="lines", format="standard", precision=17).text
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if not words or words[0] not in {"L", "B"}:
            continue
        vertices = [
            tuple(float(value) for value in next(rows).split()[:3])
            for _ in range(int(words[1]))
        ]
        for _ in range(int(words[2])):
            next(rows)
        lines.append(vertices)
    return lines


def contour(tools, expression, **options):
    """Make the map m of 3 rows by 9 columns and return its lines"""
    tools.g_region(n=3, s=0, w=0, e=9, res=1)
    tools.r_mapcalc(expression=f"m = {expression}", overwrite=True)
    tools.r_contour(input="m", output="lines", overwrite=True, quiet=True, **options)
    return read_lines(tools)


def assert_line_along_first_column(lines, level):
    """Assert one line through the centres of the cells of the first column

    The cells of the first column hold the level. The line crosses the
    edges from these cells within a few units in the last place of the cell
    centre, x = 0.5, from the top row (y = 2.5) to the bottom row (y = 0.5)
    or the other way round.
    """
    assert len(lines) == 1
    (vertices,) = lines
    assert sorted(y for _, y, _ in vertices) == [0.5, 1.5, 2.5]
    for x, _, z in vertices:
        assert x == pytest.approx(0.5, abs=1e-12)
        assert z == level


def test_level_equal_to_minimum_gets_a_line(tools):
    # Values 7 to 15
    lines = contour(tools, "float(col() + 6)", levels=7)

    assert_line_along_first_column(lines, 7)


def test_level_equal_to_minimum_of_a_step_gets_a_line(tools):
    # Values 7 to 15, the step gives the levels 7 to 15. The level 15 at
    # the maximum had its line before, the level 7 did not.
    lines = contour(tools, "float(col() + 6)", step=1)

    assert len(lines) == 9
    assert sorted(vertices[0][2] for vertices in lines) == list(range(7, 16))


def test_level_equal_to_maximum_of_negative_map(tools):
    # Values -15 to -7
    lines = contour(tools, "-float(col() + 6)", levels=-7)

    assert_line_along_first_column(lines, -7)


def test_level_zero_at_maximum(tools):
    # Values -8 to 0
    lines = contour(tools, "float(1 - col())", levels=0)

    assert_line_along_first_column(lines, 0)


def test_level_zero_at_minimum(tools):
    # Values 0 to 8. The cells of 0 stay on the level and count as below
    # it, so this level had its line before; it is unchanged.
    lines = contour(tools, "float(col() - 1)", levels=0)

    assert_line_along_first_column(lines, 0)


@pytest.mark.parametrize(
    ("expression", "level"),
    [("float(col() + 6)", 15), ("-float(col() + 6)", -15)],
)
def test_levels_moved_outwards_before_keep_their_line(tools, expression, level):
    # The highest value of a positive map and the lowest of a negative map
    # were moved outwards before; their line is the same as before. The
    # last column holds the level, the line runs along x = 8.5.
    lines = contour(tools, expression, levels=level)

    assert len(lines) == 1
    assert sorted(y for _, y, _ in lines[0]) == [0.5, 1.5, 2.5]
    assert all(x == pytest.approx(8.5, abs=1e-12) for x, _, _ in lines[0])


def test_inner_levels_unchanged(tools):
    # The first column holds the lowest value 7, which is a level, and the
    # line of the level 11.5 crosses the edges from it. Moving the cells of
    # value 7 down for all levels would change the vertices of that line in
    # the last bits (rows 3 and 4 below), so they are moved down only while
    # the line of the level 7 is traced. The expected vertices are those of
    # r.contour before the change, read with 17 digits (2026-11-04, binary
    # of commit bf340c313e).
    tools.g_region(n=4, s=0, w=0, e=5, res=1)
    tools.r_mapcalc(
        expression="m = if(col() == 1, 7.0, 10.0 + col() * 1.3 + row() * 0.7)"
    )

    tools.r_contour(input="m", output="lines", levels=[7, 11.5])

    lines = sorted(read_lines(tools), key=lambda vertices: vertices[0][2])
    assert len(lines) == 2
    assert lines[1] == [
        (1.2142857142857144, 3.5, 11.5),
        (1.1428571428571428, 2.5, 11.5),
        (1.0844155844155843, 1.5, 11.5),
        (1.0357142857142856, 0.5, 11.5),
    ]
    assert all(x == pytest.approx(0.5, abs=1e-12) for x, _, _ in lines[0])
