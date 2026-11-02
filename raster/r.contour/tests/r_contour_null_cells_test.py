"""Test that r.contour ends contour lines at null cells as at the region border

A null cell counts as a cell outside the region. The lines of a map whose null
cells surround a rectangle are therefore compared with the lines of the same
map in the region of that rectangle.
"""

import importlib.util
import itertools
import math
import os
from pathlib import Path

import pytest

import grass.script as gs
from grass.tools import Tools

TESTS = Path(__file__).parent

# The padded region is 12 rows by 14 columns from the origin. The rectangle
# with values covers rows 3 to 10 and columns 4 to 11 (row() and col()
# count from 1), so {i} and {j} below count its nodes from 1.
PADDED = {"n": 12, "s": 0, "w": 0, "e": 14}
RECTANGLE = {"n": 10, "s": 2, "w": 3, "e": 11}
INSIDE = "row() >= 3 && row() <= 10 && col() >= 4 && col() <= 11"
I = "(row() - 2)"
J = "(col() - 3)"

# name: (r.mapcalc expression in {i} and {j}, r.contour options)
FIELDS = {
    # Plane, lines that end on two sides of the rectangle.
    "ramp": ("float({i} + {j})", {"levels": [5, 8.5, 12]}),
    # Hills and hollows, closed lines and lines with ends.
    "hill": ("10 + 5 * sin({i} * 40.0) * cos({j} * 35.0)", {"step": 1.5}),
    # One dome whose closed lines run through the interior cells.
    "dome": ("100 - ({i} - 4.5)^2 - ({j} - 4.5)^2", {"levels": [90, 95, 99]}),
    # Saddles of unequal values and a slope.
    "waves": ("({i} * {j}) % 3 + 0.1 * {i}", {"levels": [0.75, 1.5]}),
}
# The chessboard of 1 and 0 is not compared with the smaller region, because
# the smaller region loses lines there: its search for closed lines starts
# only at the top edge of a cell off the border, so a closed line around a
# node next to the bottom border is not found. Within null cells it is found.
# The tests below compare the chessboard with lines derived by hand.
CHESSBOARD = "if(({i} + {j}) % 2 == 0, 1.0, 0.0)"


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


def in_rectangle(expression):
    """Return the expression in {i} and {j} in terms of row() and col()"""
    return expression.format(i=I, j=J)


def read_lines(tools):
    """Return the lines of the map lines as category and vertices, sorted

    The vertices keep the order r.contour writes them in, so the direction
    of each line is compared too. They are rounded to 1e-9: the two runs
    compute the coordinates from different region origins.
    """
    text = tools.v_out_ascii(input="lines", format="standard", precision=17).text
    lines = []
    rows = iter(text.splitlines())
    for row in rows:
        words = row.split()
        if not words or words[0] not in {"L", "B"}:
            continue
        vertices = []
        for _ in range(int(words[1])):
            x, y, z = (float(value) for value in next(rows).split()[:3])
            vertices.append((round(x, 9), round(y, 9), z))
        categories = [int(next(rows).split()[1]) for _ in range(int(words[2]))]
        lines.append((tuple(categories), tuple(vertices)))
    return sorted(lines)


def contour_lines(tools, **options):
    """Run r.contour on the map m and return what is compared

    That is the number of lines and nodes, the attribute table and the lines.
    """
    result = tools.r_contour(
        input="m", output="lines", overwrite=True, quiet=True, **options
    )
    info = tools.v_info(map="lines", flags="t").keyval
    return {
        "lines": info["lines"],
        "nodes": info["nodes"],
        "table": tools.v_db_select(map="lines").text,
        "vertices": read_lines(tools),
        "stderr": result.stderr,
    }


def assert_same_lines(padded, shrunk):
    """Compare the results of the padded and of the smaller region"""
    assert padded["vertices"] == shrunk["vertices"]
    assert padded["lines"] == shrunk["lines"]
    assert padded["nodes"] == shrunk["nodes"]
    assert padded["table"] == shrunk["table"]


def canonical(lines):
    """Return the lines with category, kind and vertices in one direction

    A closed line has no start, so it starts at its smallest vertex; both
    kinds run in the direction that gives the smaller sequence. Used where
    the expected lines are derived by hand, which gives no direction.
    """
    result = []
    for categories, vertices in lines:
        points = [vertex[:2] for vertex in vertices]
        if len(points) > 2 and points[0] == points[-1]:
            ring = points[:-1]
            forms = [ring[i:] + ring[:i] for i in range(len(ring))]
            forms += [form[::-1] for form in forms]
            result.append((categories, "closed", min(tuple(form) for form in forms)))
        else:
            form = min(tuple(points), tuple(points[::-1]))
            result.append((categories, "open", form))
    return sorted(result)


def chessboard_lines(rows, columns, west, north):
    """Return the lines of level 0.5 of a chessboard, derived by hand

    The node in row i and column j (from 1) has the value 1 if i + j is
    even, else 0, and lies at x = west + j - 0.5, y = north - i + 0.5. All
    four neighbours of a node of value 1 have the value 0, so the level
    crosses each edge from it in the middle, and in each saddle cell
    r.contour cuts off the corners of value 1 (the cell mean 0.5 counts as
    below the level). Every node of value 1 thus gets a line through the
    middles of its edges: closed around a node with four neighbours, with
    two ends on the border otherwise. The vertices run around the node
    west, south, east, north; a line with ends starts after the missing
    neighbours.
    """
    lines = []
    for i in range(1, rows + 1):
        for j in range(1, columns + 1):
            if (i + j) % 2:
                continue
            x, y = west + j - 0.5, north - i + 0.5
            around = [
                ((x - 0.5, y), j > 1),
                ((x, y - 0.5), i < rows),
                ((x + 0.5, y), j < columns),
                ((x, y + 0.5), i > 1),
            ]
            if all(present for _, present in around):
                points = [point for point, _ in around]
                lines.append(((1,), tuple(points + points[:1])))
                continue
            start = next(k for k in range(4) if not around[k - 1][1] and around[k][1])
            turned = around[start:] + around[:start]
            points = [point for point, present in turned if present]
            lines.append(((1,), tuple(points)))
    return lines


def assert_chessboard(result, expected):
    """Compare the result with the derived lines of a chessboard"""
    assert canonical(result["vertices"]) == canonical(expected)
    closed = sum(1 for _, points in expected if points[0] == points[-1])
    assert result["lines"] == len(expected)
    assert result["nodes"] == closed + 2 * (len(expected) - closed)
    assert result["table"].split() == ["cat|level", "1|0.5"]


@pytest.mark.parametrize("field", FIELDS)
def test_null_cells_around_a_rectangle_give_the_lines_of_the_smaller_region(
    tools, field
):
    expression, options = FIELDS[field]
    tools.g_region(**PADDED, res=1)
    tools.r_mapcalc(expression=f"m = if({INSIDE}, {in_rectangle(expression)}, null())")

    padded = contour_lines(tools, **options)
    tools.g_region(**RECTANGLE, res=1)
    shrunk = contour_lines(tools, **options)

    assert shrunk["lines"] > 0
    assert_same_lines(padded, shrunk)


@pytest.mark.parametrize("field", FIELDS)
def test_a_mask_gives_the_lines_of_the_smaller_region(tools, field):
    # The map has values everywhere; the cells outside the mask are read
    # as null cells.
    expression, options = FIELDS[field]
    tools.g_region(**PADDED, res=1)
    tools.r_mapcalc(expression=f"m = {in_rectangle(expression)}")
    tools.r_mapcalc(expression=f"rectangle = if({INSIDE}, 1, null())")

    tools.r_mask(raster="rectangle")
    masked = contour_lines(tools, **options)
    tools.r_mask(flags="r")
    tools.g_region(**RECTANGLE, res=1)
    shrunk = contour_lines(tools, **options)

    assert shrunk["lines"] > 0
    assert_same_lines(masked, shrunk)


@pytest.mark.parametrize("nulls", ["null cells", "mask"])
def test_a_chessboard_within_null_cells_gives_the_derived_lines(tools, nulls):
    # The smaller region of the rectangle loses three closed lines here (29
    # lines instead of 32), see CHESSBOARD, so the comparison with it does
    # not apply. Derived: the rectangle of 8 by 8 nodes has 32 nodes of
    # value 1: 18 inside (closed lines), 12 on the sides and 2 in corners
    # (lines with ends), 46 nodes in all.
    tools.g_region(**PADDED, res=1)
    expression = in_rectangle(CHESSBOARD)
    if nulls == "mask":
        tools.r_mapcalc(expression=f"m = {expression}")
        tools.r_mapcalc(expression=f"rectangle = if({INSIDE}, 1, null())")
        tools.r_mask(raster="rectangle")
    else:
        tools.r_mapcalc(expression=f"m = if({INSIDE}, {expression}, null())")

    result = contour_lines(tools, levels=0.5)

    expected = chessboard_lines(8, 8, RECTANGLE["w"], RECTANGLE["n"])
    assert len(expected) == 32
    assert_chessboard(result, expected)


# The dome of the rectangle of 6 by 6 nodes, rows and columns 3 to 8 of a
# region of 10 by 10 whose other cells are null.
FRAMED_DOME = (
    "if(row() >= 3 && row() <= 8 && col() >= 3 && col() <= 8,"
    " 50 - (row() - 5.5)^2 - (col() - 5.5)^2, null())"
)


def test_a_closed_line_inside_a_frame_of_null_cells_is_kept(tools):
    # The comparison with the smaller region does not apply: in the region
    # of the rectangle the closed line runs only through cells on its
    # border, where no closed line is searched, so that region gives no
    # line. Before 2026-11-02 r.contour found this line within the null
    # cells, and it still does.
    # Derived by hand: the inner 4 by 4 nodes have values of 45.5 and more,
    # the outer ring 43.5 and less, so the level 45 crosses each edge from
    # the outer ring inwards: 4 on each side. On the edge from 41.5 to 45.5
    # at 3.5 / 4 = 0.875, from 43.5 to 47.5 at 1.5 / 4 = 0.375 of the way
    # in. Node centres lie at x = col - 0.5, y = 10.5 - row.
    tools.g_region(n=10, s=0, w=0, e=10, res=1)
    tools.r_mapcalc(expression=f"m = {FRAMED_DOME}")

    result = contour_lines(tools, levels=45)

    ring = [
        (3.5, 6.625),
        (4.5, 7.125),
        (5.5, 7.125),
        (6.5, 6.625),
        (6.625, 6.5),
        (7.125, 5.5),
        (7.125, 4.5),
        (6.625, 3.5),
        (6.5, 3.375),
        (5.5, 2.875),
        (4.5, 2.875),
        (3.5, 3.375),
        (3.375, 3.5),
        (2.875, 4.5),
        (2.875, 5.5),
        (3.375, 6.5),
    ]
    assert canonical(result["vertices"]) == canonical([((1,), (*ring, ring[0]))])
    assert result["lines"] == 1
    assert result["nodes"] == 1


def test_a_line_lost_at_saddles_leaves_no_piece_within_null_cells(tools):
    # Nodes 0 0 1 / 0 2 0 / 1 0 0 inside two rows and columns of null cells,
    # level 0.5. The two saddle cells join the nodes above the level (cell
    # mean 0.75), so two lines with ends cut off the zeros at the top left
    # and at the bottom right. The comparison with the region of 3 by 3 does
    # not apply: the region draws only the first line, because the second
    # starts and ends in the saddle cells, whose hit flag the first line set.
    # Within null cells the border passes ask the start edge instead, so the
    # second line is drawn whole; the search for closed lines, which meets
    # it in the middle, must not add a piece of it that ends inside.
    # Derived by hand (node centres at x = col + 1.5, y = 5.5 - row for row
    # and column from 1): an edge from 0 to 1 is crossed in the middle, one
    # from 0 to 2 at a quarter of its length from the 0.
    tools.g_region(n=7, s=0, w=0, e=7, res=1)
    tools.r_mapcalc(
        expression="m = if(row() < 3 || row() > 5 || col() < 3 || col() > 5,"
        " null(), if((row() == 3 && col() == 5) || (row() == 5 && col() == 3),"
        " 1.0, if(row() == 4 && col() == 4, 2.0, 0.0)))"
    )

    result = contour_lines(tools, levels=0.5)

    expected = [
        ((1,), ((4.0, 4.5), (3.5, 4.25), (2.75, 3.5), (2.5, 3.0))),
        ((1,), ((3.0, 2.5), (3.5, 2.75), (4.25, 3.5), (4.5, 4.0))),
    ]
    assert canonical(result["vertices"]) == canonical(expected)
    assert result["lines"] == 2
    assert result["nodes"] == 4


def test_a_line_with_a_saddle_at_its_end_is_kept_at_null_cells(tools):
    # Nodes 0 0 0 / 1 1 0 / 1 0 1 inside two rows and columns of null cells,
    # level 0.5. The comparison with the region of 3 by 3 does not apply:
    # there the corner line at the bottom right is lost. Its only cell, a
    # saddle, is marked hit by its other segment, and the border passes of
    # the region ask that flag. Before 2026-11-02 r.contour drew this line
    # within null cells. Derived by hand (nodes 0 and 1, every crossing in
    # the middle of its edge; node centres at x = col + 1.5 and
    # y = 5.5 - row for row and column from 1): the saddle cell at the bottom
    # right has the mean 0.5, which counts as below the level, so it cuts
    # off its corners of value 1. The first line runs around the nodes
    # (2, 1), (2, 2), (3, 1) from the bottom to the left border, the second
    # cuts off the node (3, 3).
    tools.g_region(n=7, s=0, w=0, e=7, res=1)
    tools.r_mapcalc(
        expression="m = if(row() < 3 || row() > 5 || col() < 3 || col() > 5,"
        " null(), if((row() == 4 && col() <= 4) || (row() == 5 && col() != 4),"
        " 1.0, 0.0))"
    )

    result = contour_lines(tools, levels=0.5)

    expected = [
        ((1,), ((3.0, 2.5), (3.5, 3.0), (4.0, 3.5), (3.5, 4.0), (2.5, 4.0))),
        ((1,), ((4.0, 2.5), (4.5, 3.0))),
    ]
    assert canonical(result["vertices"]) == canonical(expected)
    assert result["lines"] == 2
    assert result["nodes"] == 4


def test_no_crossings_warning_at_null_cells(tools):
    # Before 2026-11-02 this map gave "2 crossings found", and its line ran
    # in the other direction than in the region of the rectangle.
    tools.g_region(n=6, s=0, w=0, e=6, res=1)
    tools.r_mapcalc(
        expression="m = if(row() >= 2 && row() <= 5 && col() >= 2 && col() <= 5,"
        " float(row() + col()), null())"
    )

    result = contour_lines(tools, levels=7)

    assert result["lines"] == 1
    assert "crossing" not in result["stderr"]


# A dome of 10 by 10 cells, 50 at the centre, cut by an L of null cells:
# column 6 from row 1 to row 6 and row 6 from column 6 to column 10. The
# closed line of level 45 around the centre meets each arm of the L once,
# so the L cuts it into two pieces.
DOME = "50 - (row() - 5.5)^2 - (col() - 5.5)^2"
L_NULLS = "(col() == 6 && row() <= 6) || (row() == 6 && col() >= 6)"


def is_null(row, col):
    """Return True if the node (0-based row and column) is a cell of the L"""
    return (col == 5 and row <= 5) or (row == 5 and col >= 5)


def has_value(row, col):
    """Return True if the node lies in the 10 by 10 region and is not null"""
    return 0 <= row < 10 and 0 <= col < 10 and not is_null(row, col)


def on_surface(row, col):
    """Return True if the cell with the top left node (row, col) has four values"""
    return all(
        has_value(row + down, col + right) for down in (0, 1) for right in (0, 1)
    )


def edge_of(x, y):
    """Return the two nodes of the edge between cell centres the vertex lies on"""
    # Node (row, col) is the centre of a cell: x = col + 0.5, y = 9.5 - row.
    col, row = x - 0.5, 9.5 - y
    if row == int(row):
        return (int(row), math.floor(col)), (int(row), math.floor(col) + 1)
    assert col == int(col), f"vertex {x}, {y} is not on an edge"
    return (math.floor(row), int(col)), (math.floor(row) + 1, int(col))


def cells_at(edge):
    """Return the top left nodes of the two cells that share the edge"""
    (row1, col1), (row2, col2) = edge
    if row1 == row2:
        return [(row1 - 1, col1), (row1, col1)]
    return [(row1, col1 - 1), (row1, col1)]


def test_a_line_ends_at_an_irregular_null_area(tools):
    tools.g_region(n=10, s=0, w=0, e=10, res=1)
    tools.r_mapcalc(expression=f"m = if({L_NULLS}, null(), {DOME})")

    result = contour_lines(tools, levels=45)

    lines = [vertices for _, vertices in result["vertices"]]
    for vertices in lines:
        assert vertices[0][:2] != vertices[-1][:2], "a closed line"
        for x, y, _ in vertices:
            assert all(has_value(*node) for node in edge_of(x, y))
        for start, end in itertools.pairwise(vertices):
            # The middle of a segment lies in the cell the segment crosses.
            x = (start[0] + end[0]) / 2
            y = (start[1] + end[1]) / 2
            assert on_surface(math.floor(9.5 - y), math.floor(x - 0.5))
        for x, y, _ in (vertices[0], vertices[-1]):
            # An end lies on an edge with a cell off the surface on one side.
            cells = cells_at(edge_of(x, y))
            assert not all(on_surface(*cell) for cell in cells)
    # The ends derived by hand (row and column count from 1, the centre of
    # row r lies at y = 10.5 - r, of column c at x = c - 0.5):
    # row 7, columns 7 (45.5) and 8 (41.5): x = 6.5 + 0.5 / 4 = 6.625;
    # column 5, rows 3 (43.5) and 4 (47.5): y = 7.5 - 1.5 / 4 = 7.125;
    # row 5, columns 7 (47.5) and 8 (43.5): x = 6.5 + 2.5 / 4 = 7.125;
    # column 7, rows 4 (45.5) and 3 (41.5): y = 6.5 + 0.5 / 4 = 6.625.
    ends = sorted(sorted([line[0][:2], line[-1][:2]]) for line in lines)
    assert ends == [[(4.5, 7.125), (6.625, 3.5)], [(6.5, 6.625), (7.125, 5.5)]]
    assert result["lines"] == 2
    assert result["nodes"] == 4
    assert "crossing" not in result["stderr"]


# The fields of the tests for regions of one or two rows or columns, as
# expressions of row and column of the region they were written for.
NARROW_EXPRESSIONS = ["row() + col()", "row()", "col()", "row() * col()"]
NARROW_LEVELS = [1.5, 2.5, 3.5]
NARROW_REGIONS = [(2, 2), (2, 3), (3, 2), (3, 3)]
SADDLES = "if((row() + col()) % 2 == 0, 1.0, 0.0)"
PAD = 2


# The region of 3 by 3 loses the closed line of the chessboard around its
# centre, so that case is compared with derived lines instead, see
# test_a_padded_chessboard_of_three_by_three_keeps_its_centre.
NARROW_CASES = [
    (rows, columns, expression, level)
    for rows, columns in NARROW_REGIONS
    for expression, level in [
        *(
            (expression, level)
            for expression in NARROW_EXPRESSIONS
            for level in NARROW_LEVELS
        ),
        (SADDLES, 0.5),
    ]
    if (rows, columns, expression) != (3, 3, SADDLES)
]


@pytest.mark.parametrize(("rows", "columns", "expression", "level"), NARROW_CASES)
def test_narrow_region_padded_with_nulls_gives_the_same_lines(
    tools, rows, columns, expression, level
):
    # The map of the narrow region gets PAD rows and columns of null cells
    # on every side; row() and col() are shifted so that the values are those
    # of the narrow region.
    shifted = expression.replace("row()", f"(row() - {PAD})").replace(
        "col()", f"(col() - {PAD})"
    )
    inside = (
        f"row() > {PAD} && row() <= {PAD + rows}"
        f" && col() > {PAD} && col() <= {PAD + columns}"
    )
    tools.g_region(n=rows + 2 * PAD, s=0, w=0, e=columns + 2 * PAD, res=1)
    tools.r_mapcalc(expression=f"m = if({inside}, {shifted}, null())")

    padded = contour_lines(tools, levels=level)
    tools.g_region(n=rows + PAD, s=PAD, w=PAD, e=columns + PAD, res=1)
    shrunk = contour_lines(tools, levels=level)

    assert_same_lines(padded, shrunk)


def test_a_padded_chessboard_of_three_by_three_keeps_its_centre(tools):
    # The comparison with the region of 3 by 3 does not apply: there every
    # cell lies on the border, no closed line is searched and the line
    # around the centre node is lost (4 lines instead of 5). Within null
    # cells it is found. Derived: nodes of value 1 at the four corners
    # (lines with two vertices) and at the centre (closed line), 9 nodes.
    tools.g_region(n=3 + 2 * PAD, s=0, w=0, e=3 + 2 * PAD, res=1)
    shifted = SADDLES.replace("row()", f"(row() - {PAD})").replace(
        "col()", f"(col() - {PAD})"
    )
    inside = (
        f"row() > {PAD} && row() <= {PAD + 3} && col() > {PAD} && col() <= {PAD + 3}"
    )
    tools.r_mapcalc(expression=f"m = if({inside}, {shifted}, null())")

    result = contour_lines(tools, levels=0.5)

    expected = chessboard_lines(3, 3, PAD, 3 + PAD)
    assert len(expected) == 5
    assert_chessboard(result, expected)


def load_recorder():
    """Import record_lines.py, which pytest does not collect"""
    spec = importlib.util.spec_from_file_location(
        "record_lines", TESTS / "record_lines.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lines_without_nulls_are_unchanged_after_the_null_cell_fix(
    session, monkeypatch
):
    # The recording was made before r.contour changed, see record_lines.py.
    # record_lines.py calls grass.script without an env, so the session
    # is mirrored into the environment of the process.
    for key, value in session.env.items():
        monkeypatch.setenv(key, value)
    load_recorder().assert_cases_as_recorded()
