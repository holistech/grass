"""Test that r.contour ends on regions of one or two rows or columns"""

import os
import signal
import subprocess

import pytest

import grass.script as gs
from grass.tools import Tools

TIMEOUT = 30

EXPRESSIONS = ["row() + col()", "row()", "col()", "row() * col()"]
LEVELS = [1.5, 2.5, 3.5]
REGIONS = [(2, 2), (2, 3), (3, 2), (3, 3)]


@pytest.fixture
def session(tmp_path):
    """A session in an XY project"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        yield session


@pytest.fixture
def tools(session):
    """Tools in the session"""
    with Tools(session=session, consistent_return_value=True) as tools:
        yield tools


def run_contour(session, level):
    """Run r.contour with a time limit and return its exit code

    A hung process would block the test run, so it gets its own process
    group and the whole group is killed when the limit passes.
    """
    process = subprocess.Popen(
        [
            "r.contour",
            "input=m",
            "output=lines",
            f"levels={level}",
            "--overwrite",
            "--quiet",
        ],
        env=session.env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        _, stderr = process.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        pytest.fail(f"r.contour did not end within {TIMEOUT} s")
    assert process.returncode == 0, stderr
    return process.returncode


def make_map(tools, rows, columns, expression):
    """Make the map m of the given size, cells of 1 by 1 from the origin"""
    tools.g_region(n=rows, s=0, w=0, e=columns, res=1)
    tools.r_mapcalc(expression=f"m = {expression}", overwrite=True)


def read_lines(tools):
    """Return the vertices of every line in the map lines"""
    text = tools.v_out_ascii(input="lines", format="standard").text
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if not words or words[0] != "L":
            continue
        vertices = []
        for _ in range(int(words[1])):
            x, y = next(rows).split()[:2]
            vertices.append((float(x), float(y)))
        lines.append(vertices)
    return lines


def assert_one_line(lines, expected):
    """Compare the single line with the expected vertices, in either direction"""
    assert len(lines) == 1
    forward = lines[0] == pytest.approx(expected)
    backward = lines[0][::-1] == pytest.approx(expected)
    assert forward or backward


# For m = row() + col() the nodes are the cell centers. A line of level 2.5
# crosses only the edges between the node of the corner (value 2) and its two
# neighbours (value 3), once at the middle of each edge: the interpolation
# (2.5 - 2) / (3 - 2) is one half. On x, a node of column c lies at
# c + 0.5, on y a node of row r at north - r - 0.5.


def test_two_rows_end_with_the_derived_line(session, tools):
    # Region 2 rows by 3 columns, north = 2. The corner node (row 0, col 0)
    # is at (0.5, 1.5); its neighbours are (1.5, 1.5) and (0.5, 0.5). The
    # crossings lie at (1.0, 1.5) and (0.5, 1.0). The other cells have only
    # values above 2.5, so there is exactly one line of two vertices.
    make_map(tools, 2, 3, "row() + col()")

    run_contour(session, 2.5)

    assert_one_line(read_lines(tools), [(1.0, 1.5), (0.5, 1.0)])


def test_two_columns_end_with_the_derived_line(session, tools):
    # Region 3 rows by 2 columns, north = 3. The corner node (row 0, col 0)
    # is at (0.5, 2.5); its neighbours are (1.5, 2.5) and (0.5, 1.5). The
    # crossings lie at (1.0, 2.5) and (0.5, 2.0).
    make_map(tools, 3, 2, "row() + col()")

    run_contour(session, 2.5)

    assert_one_line(read_lines(tools), [(1.0, 2.5), (0.5, 2.0)])


def test_one_row_ends(session, tools):
    # A contour line is traced through the cells between four nodes (two
    # rows and two columns). One row of nodes has no such cell, so the
    # algorithm defines no line and the map stays empty. This is what the
    # old code does on three rows and one column too.
    make_map(tools, 1, 4, "col()")

    run_contour(session, 2.5)

    assert read_lines(tools) == []


def test_one_column_ends(session, tools):
    make_map(tools, 4, 1, "row()")

    run_contour(session, 2.5)

    assert read_lines(tools) == []


def test_one_cell_gives_an_empty_map(session, tools):
    make_map(tools, 1, 1, "col()")

    run_contour(session, 0.5)

    assert read_lines(tools) == []


def canonical(lines):
    """Return the lines with both directions merged, rounded and sorted"""
    result = []
    for line in lines:
        forward = tuple((round(x, 9), round(y, 9)) for x, y in line)
        result.append(min(forward, forward[::-1]))
    return sorted(result)


# Saddle fields: nodes of value 1 and 0 in a chessboard, level 0.5. Every
# edge between two nodes is crossed in its middle. A cell with the corners
# 1 0 / 0 1 has four crossings, and r.contour joins them so that the corners
# of value 1 are cut off (the cell mean 0.5 counts as below the level). On
# two rows or columns both segments of such a cell start on the border, and
# a cell marked as hit after the first one lost the second.


def test_two_rows_keep_both_segments_of_a_saddle(session, tools):
    # 2 rows by 2 columns, north = 2, cell corners TL=1 TR=0 / BL=0 BR=1.
    # The crossings are top (1.0, 1.5), right (1.5, 1.0), bottom (1.0, 0.5)
    # and left (0.5, 1.0). The corner TL is cut off by top-left, BR by
    # right-bottom: two lines.
    make_map(tools, 2, 2, "if((row() + col()) % 2 == 0, 1.0, 0.0)")

    run_contour(session, 0.5)

    assert canonical(read_lines(tools)) == canonical(
        [[(1.0, 1.5), (0.5, 1.0)], [(1.5, 1.0), (1.0, 0.5)]]
    )


def test_two_rows_join_the_segments_of_neighbouring_saddles(session, tools):
    # 2 rows by 3 columns. The second cell is the first one mirrored: the
    # corners TR and BL are cut off. Its left crossing (1.5, 1.0) is the
    # right crossing of the first cell, so the segments right-bottom of the
    # first and left-bottom of the second cell form one line through
    # (1.0, 0.5), (1.5, 1.0), (2.0, 0.5). The cut off corners TL and TR
    # give the lines (1.0, 1.5)-(0.5, 1.0) and (2.0, 1.5)-(2.5, 1.0).
    make_map(tools, 2, 3, "if((row() + col()) % 2 == 0, 1.0, 0.0)")

    run_contour(session, 0.5)

    assert canonical(read_lines(tools)) == canonical(
        [
            [(1.0, 1.5), (0.5, 1.0)],
            [(1.0, 0.5), (1.5, 1.0), (2.0, 0.5)],
            [(2.0, 1.5), (2.5, 1.0)],
        ]
    )


def test_two_columns_keep_both_segments_of_a_saddle(session, tools):
    # 3 rows by 2 columns, north = 3. The first cell cuts off TL and BR,
    # the second (below) cuts off TR and BL. Its top crossing (1.0, 1.5) is
    # the bottom crossing of the first cell, so right-bottom of the first
    # and top-right of the second cell form the line (1.5, 2.0), (1.0, 1.5),
    # (1.5, 1.0). The other lines are (1.0, 2.5)-(0.5, 2.0) and
    # (0.5, 1.0)-(1.0, 0.5).
    make_map(tools, 3, 2, "if((row() + col()) % 2 == 0, 1.0, 0.0)")

    run_contour(session, 0.5)

    assert canonical(read_lines(tools)) == canonical(
        [
            [(1.0, 2.5), (0.5, 2.0)],
            [(1.5, 2.0), (1.0, 1.5), (1.5, 1.0)],
            [(0.5, 1.0), (1.0, 0.5)],
        ]
    )


@pytest.mark.parametrize("expression", EXPRESSIONS)
@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize(("rows", "columns"), REGIONS)
def test_the_measured_cases_all_end(session, tools, rows, columns, level, expression):
    # The 48 runs of the series that found the hang.
    make_map(tools, rows, columns, expression)

    run_contour(session, level)
