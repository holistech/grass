"""Test the feature types of t.rast.to.vect on maps of three by three cells

The cells of the maps are described in conftest.py. For type=point every cell
with a value is a point. For type=area the cells of one value that touch along
an edge form one area, so the two halves make two areas with a shared boundary,
the plus sign one area and the middle row one area. For type=line r.to.vect
thins the cells to lines between the cell centres.
"""

import re

import pytest

from grass.temporal.testing.readback import list_maps

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow

KEYS = ("points", "lines", "boundaries", "centroids", "areas", "islands", "nodes")

HALVES, PLUS, ROW = 0, 1, 2

# The outline of the plus sign (the cells x 1..2 and y 0..3, and x 0..3 and
# y 1..2) in the order in which it is walked.
OUTLINE_OF_PLUS = [
    (2, 0), (1, 0), (1, 1), (0, 1), (0, 2), (1, 2),
    (1, 3), (2, 3), (2, 2), (3, 2), (3, 1), (2, 1),
]  # fmt: skip
CORNERS_OF_PLUS = set(OUTLINE_OF_PLUS)


def _maps(tools, name):
    return [row.name for row in list_maps(tools, "stvds", name)]


def _features(tools, name):
    info = tools.v_info(map=name, flags="t").keyval
    return {key: info[key] for key in KEYS}


def _only(**counts):
    return {key: counts.get(key, 0) for key in KEYS}


def _vertices(tools, name):
    text = tools.v_out_ascii(input=name, format="wkt").stdout
    return {
        (float(x), float(y)) for x, y in re.findall(r"(-?\d+\.\d+) (-?\d+\.\d+)", text)
    }


def test_points_are_the_cells_with_a_value(tools, shapes, prefix):
    tools.t_rast_to_vect(input=shapes, output=prefix, basename=prefix, type="point")

    names = _maps(tools, prefix)
    # 9 cells, the 5 cells of the plus sign and the 3 cells of the row
    assert [_features(tools, name)["points"] for name in names] == [9, 5, 3]


def test_a_point_lies_on_the_centre_of_its_cell(tools, shapes, prefix):
    tools.t_rast_to_vect(input=shapes, output=prefix, basename=prefix, type="point")

    box = tools.v_info(map=_maps(tools, prefix)[ROW], flags="g").keyval
    # The row holds the cells in the middle of the region: y = 1.5
    assert (box["west"], box["east"], box["south"], box["north"]) == (
        0.5,
        2.5,
        1.5,
        1.5,
    )


def test_areas_follow_the_cell_borders(tools, shapes, prefix):
    tools.t_rast_to_vect(input=shapes, output=prefix, basename=prefix, type="area")

    names = _maps(tools, prefix)
    # Two rectangles share one boundary; each has an own part of the outer
    # boundary, and the two nodes lie where the shared boundary meets it.
    assert _features(tools, names[HALVES]) == _only(
        boundaries=3, centroids=2, areas=2, islands=1, nodes=2
    )
    assert _features(tools, names[PLUS]) == _only(
        boundaries=1, centroids=1, areas=1, islands=1, nodes=1
    )
    assert _features(tools, names[ROW]) == _only(
        boundaries=1, centroids=1, areas=1, islands=1, nodes=1
    )


def test_the_area_of_the_plus_sign_has_its_twelve_corners(tools, shapes, prefix):
    tools.t_rast_to_vect(input=shapes, output=prefix, basename=prefix, type="area")

    assert _vertices(tools, _maps(tools, prefix)[PLUS]) == CORNERS_OF_PLUS


def test_the_s_flag_cuts_the_corners_through_the_edge_midpoints(tools, shapes, prefix):
    tools.t_rast_to_vect(
        input=shapes, output=prefix, basename=prefix, type="area", flags="s"
    )

    vertices = _vertices(tools, _maps(tools, prefix)[PLUS])
    midpoints = {
        ((ax + bx) / 2, (ay + by) / 2)
        for (ax, ay), (bx, by) in zip(
            OUTLINE_OF_PLUS,
            OUTLINE_OF_PLUS[1:] + OUTLINE_OF_PLUS[:1],
            strict=True,
        )
    }
    # Every edge of the plus sign has length 1 and a midpoint as a vertex of
    # the smoothed outline; the corners themselves are gone, except the one
    # where r.to.vect starts the outline (see the findings of this tool).
    assert midpoints <= vertices
    assert len(CORNERS_OF_PLUS & vertices) <= 1


def test_the_s_flag_keeps_the_counts_of_the_features(tools, shapes, prefix):
    tools.t_rast_to_vect(
        input=shapes, output=prefix, basename=prefix, type="area", flags="s"
    )

    names = _maps(tools, prefix)
    assert _features(tools, names[HALVES]) == _only(
        boundaries=3, centroids=2, areas=2, islands=1, nodes=2
    )


def test_lines_are_thinned_between_the_cell_centres(tools, thin, prefix):
    tools.t_rast_to_vect(input=thin, output=prefix, basename=prefix, type="line")

    plus, row = _maps(tools, prefix)
    # Four arms from the centre cell to the four outer cells: four lines and
    # five nodes. The row is one line from the first to the last cell.
    assert _features(tools, plus) == _only(lines=4, nodes=5)
    assert _features(tools, row) == _only(lines=1, nodes=2)
    box = tools.v_info(map=row, flags="g").keyval
    assert (box["west"], box["east"], box["south"], box["north"]) == (
        0.5,
        2.5,
        1.5,
        1.5,
    )


def test_the_z_flag_writes_the_value_as_z(tools, shapes, prefix):
    tools.t_rast_to_vect(
        input=shapes,
        output=prefix,
        basename=prefix,
        type="point",
        flags="z",
        where="start_time < '2001-01-02'",
    )

    (name,) = _maps(tools, prefix)
    box = tools.v_info(map=name, flags="g").keyval
    assert (box["bottom"], box["top"]) == (10, 20)
    assert _features(tools, name)["points"] == 9
