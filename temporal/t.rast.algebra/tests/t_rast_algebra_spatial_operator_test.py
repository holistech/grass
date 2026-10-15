"""Test the spatial topology of t.rast.algebra: flag -s and spatial relations

Datasets (all maps are constant, the value is given in brackets, region in
x/y; times are days of January 2001):

====  ===========================  ===========================
STRDS day 1                        day 2
====  ===========================  ===========================
P     p1 (1) x 0-3, y 0-3          p2 (2) x 0-3, y 0-3
Q     q1 (10) x 2-5, y 2-5         q2 (20) x 100-103, y 100-103
====  ===========================  ===========================

p1 and q1 overlap spatially, p2 and q2 are far apart. The maps of the same
day are temporally equal.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.tools import ToolError, Tools

ALGEBRA = "GRASS_TEMPORAL_ALGEBRA"


@pytest.fixture(scope="module")
def spatial_series(xy_module_session):
    """Session with the datasets P and Q of the module docstring"""
    tools = Tools(session=xy_module_session)
    regions = {
        "p1": (0, 3, 0, 3),
        "p2": (0, 3, 0, 3),
        "q1": (2, 5, 2, 5),
        "q2": (100, 103, 100, 103),
    }
    values = {"p1": 1, "p2": 2, "q1": 10, "q2": 20}
    for name, (west, east, south, north) in regions.items():
        make_map(
            tools,
            "raster",
            name,
            values[name],
            region={"w": west, "e": east, "s": south, "n": north, "res": 1},
        )
    tools.g_region(w=0, e=103, s=0, n=103, res=1)
    for dataset, maps in (("P", ("p1", "p2")), ("Q", ("q1", "q2"))):
        register_stds(
            tools,
            "strds",
            dataset,
            [
                MapSpec(maps[0], values[maps[0]], day(0), day(1)),
                MapSpec(maps[1], values[maps[1]], day(1), day(2)),
            ],
        )
    return xy_module_session


def result_values(session, expression, flags="", algebra=None):
    """Run the tool and return the cell values of the result maps in time order

    algebra sets GRASS_TEMPORAL_ALGEBRA for the tool; the flag c selects the
    classic algebra whatever the variable says.
    """
    env = session.env if algebra is None else {**session.env, ALGEBRA: algebra}
    tools = Tools(env=env, overwrite=True)
    tools.t_rast_algebra(expression=f"R = {expression}", basename="r", flags=flags)
    listing = tools.t_rast_list(input="R", columns="min,max", format="json")
    assert all(row["min"] == row["max"] for row in listing["data"])
    return [row["min"] for row in listing["data"]]


@pytest.mark.parametrize(
    ("expression", "flags", "expected"),
    [
        # r.mapcalc gives an all-null map for the disjoint pair p2/q2, and
        # such a map is not registered, so only the overlapping pair remains.
        ("P {+,equal} Q", "", [11]),
        ("P {+,equal} Q", "s", [11]),
        # The classic algebra builds no spatial topology without -s and
        # ignores the spatial relation then; the core needs -s for it.
        pytest.param(
            "P {+,equal|overlap} Q", "c", [11], marks=pytest.mark.fixed_algebra
        ),
        ("P {+,equal|overlap} Q", "s", [11]),
        # p1 and q1 overlap, they do not cover each other
        pytest.param("P {+,equal|cover} Q", "c", [], marks=pytest.mark.fixed_algebra),
        ("P {+,equal|cover} Q", "s", []),
        # the hash operator counts the temporally related maps; the result of
        # the condition is P itself, so the disjoint pair shows up as p2
        ("if(P {#} Q == 1, P)", "", [1, 2]),
        ("if(P {#} Q == 1, P)", "s", [1]),
    ],
)
def test_spatial_topology(spatial_series, expression, flags, expected):
    """-s and spatial relations restrict the related maps to spatially related"""
    assert result_values(spatial_series, expression, flags) == expected


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("relations", ["equal|overlap", "equal|cover"])
def test_spatial_relation_needs_the_spatial_flag(spatial_series, relations):
    """Without -s no spatial topology is built, so a spatial relation name
    is an error instead of an empty or unrestricted result"""
    with pytest.raises(ToolError, match="need the spatial flag"):
        result_values(spatial_series, f"P {{+,{relations}}} Q", algebra="core")
