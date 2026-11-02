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
    # Saddle cells everywhere: nodes 1 and 0 as on a chessboard.
    "saddles": ("if(({i} + {j}) % 2 == 0, 1.0, 0.0)", {"levels": [0.5]}),
    # Saddles of unequal values and a slope.
    "waves": ("({i} * {j}) % 3 + 0.1 * {i}", {"levels": [0.75, 1.5]}),
}


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


@pytest.mark.parametrize(
    ("expression", "level"),
    [
        *(
            (expression, level)
            for expression in NARROW_EXPRESSIONS
            for level in NARROW_LEVELS
        ),
        (SADDLES, 0.5),
    ],
)
@pytest.mark.parametrize(("rows", "columns"), NARROW_REGIONS)
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
