"""Test that r.contour writes no contour line of a single point

A level that touches the surface only around one node is crossed by every
cell around that node so close to the node that the crossings round to the
node itself, and the traced line has one point. This happens at a node whose
neighbors all lie on one side of the level and whose value is the level or
differs from it by a few units in the last place, and at nodes of the level
that no cell with four values joins, as on a staircase along null cells.
Such a line used to be written and ended r.contour with "Intersection with
points is not yet supported" when the lines were broken at intersections.
"""

import os

import pytest

import grass.script as gs
from grass.tools import Tools

# Ten by ten cells, once with small coordinates and once with coordinates and
# cells of a projected map. The size matters for levels other than 0: a value
# equal to a level is moved by a relative DBL_EPSILON, which leaves a ring of
# distinct points around the node at small coordinates, but one point at
# large coordinates.
REGIONS = {
    "small": {"n": 10, "s": 0, "w": 0, "e": 10, "res": 1},
    "large": {"n": 228500, "s": 223500, "w": 635000, "e": 640000, "res": 500},
}
NODE = "row() == 5 && col() == 5"
# Null cells above the diagonal row() + col() = 10. The first diagonal of
# cells with values holds the level, all other cells lie on one side of it,
# so the level touches the surface in a staircase of single nodes.
STAIR = "if(row() + col() < 10, null(), {})"
STEPS = "(row() + col() - 10) * 0.1"

# name: (r.mapcalc expression, level)
SINGLE_NODES = {
    "pit at 0": (f"if({NODE}, 0, 1)", 0),
    "peak at 5": (f"if({NODE}, 5, 4)", 5),
    "pit at -5": (f"if({NODE}, -5, -4)", -5),
    # Not equal to the level, so displaceMatrix() leaves it alone, but the
    # crossings lie within one unit in the last place of the node even at
    # small coordinates. r.mapcalc reads only the decimal notation of 2^-52.
    "peak just above 0": (f"if({NODE}, 0.0000000000000002220446049250313, -1)", 0),
    "stair at 0 along null cells": (STAIR.format(STEPS), 0),
    "stair at 5 along null cells": (STAIR.format(f"5 - {STEPS}"), 5),
    "stair at -5 along null cells": (STAIR.format(f"-5 + {STEPS}"), -5),
}


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


def vertex_counts(tools):
    """Return the number of vertices of each line of the map lines, sorted"""
    text = tools.v_out_ascii(input="lines", format="standard").text
    return sorted(
        int(row.split()[1]) for row in text.splitlines() if row.startswith("L ")
    )


@pytest.mark.parametrize("cut", [0, 1])
@pytest.mark.parametrize("region", REGIONS)
@pytest.mark.parametrize("name", SINGLE_NODES)
def test_a_level_touching_single_nodes_gives_no_line(tools, name, region, cut):
    # Every cell around such a node crosses the level at the node, so the
    # level has no line there, only a point. The stair along null cells had a
    # line through the cells with a null node before null cells ended the
    # lines; those cells are not part of the surface now, so its single nodes
    # are left. A single point gives no line with cut=2 either, which has
    # always been the default.
    expression, level = SINGLE_NODES[name]
    tools.g_region(**REGIONS[region])
    tools.r_mapcalc(expression=f"m = {expression}")

    tools.r_contour(input="m", output="lines", levels=level, cut=cut)

    assert vertex_counts(tools) == []


@pytest.mark.parametrize("cut", [0, 1, 2])
@pytest.mark.parametrize("region", REGIONS)
def test_a_line_of_two_points_is_kept(tools, region, cut):
    # Only the top left cell has a node below the level, so the level
    # crosses its top and left edge: one line of two points. The rule that
    # leaves out single points must not drop it, whatever cut up to 2.
    tools.g_region(**REGIONS[region])
    tools.r_mapcalc(expression="m = if(row() == 1 && col() == 1, 0, 1)")

    tools.r_contour(input="m", output="lines", levels=0.5, cut=cut)

    assert vertex_counts(tools) == [2]


def test_cut_above_two_still_leaves_out_a_line_of_two_points(tools):
    tools.g_region(**REGIONS["small"])
    tools.r_mapcalc(expression="m = if(row() == 1 && col() == 1, 0, 1)")

    tools.r_contour(input="m", output="lines", levels=0.5, cut=3)

    assert vertex_counts(tools) == []
