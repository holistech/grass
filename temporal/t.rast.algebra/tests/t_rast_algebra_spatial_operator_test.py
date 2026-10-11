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

import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture(scope="module")
def spatial_series(tmp_path_factory):
    """Session with the datasets P and Q of the module docstring"""
    tmp_path = tmp_path_factory.mktemp("spatial_operator")
    project = tmp_path / "project"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session, overwrite=True)
        regions = {
            "p1": (0, 3, 0, 3),
            "p2": (0, 3, 0, 3),
            "q1": (2, 5, 2, 5),
            "q2": (100, 103, 100, 103),
        }
        values = {"p1": 1, "p2": 2, "q1": 10, "q2": 20}
        for name, (west, east, south, north) in regions.items():
            tools.g_region(w=west, e=east, s=south, n=north, res=1)
            tools.r_mapcalc(expression=f"{name} = {values[name]}")
        tools.g_region(w=0, e=103, s=0, n=103, res=1)
        for dataset, maps in (("P", ("p1", "p2")), ("Q", ("q1", "q2"))):
            tools.t_create(
                output=dataset, type="strds", title=dataset, description=dataset
            )
            listing = tmp_path / f"{dataset}.txt"
            listing.write_text(
                f"{maps[0]}|2001-01-01|2001-01-02\n{maps[1]}|2001-01-02|2001-01-03\n"
            )
            tools.t_register(input=dataset, file=listing)
        yield session


def result_values(session, expression, flags=""):
    """Run the tool and return the cell values of the result maps in time order"""
    tools = Tools(session=session, overwrite=True)
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
        ("P {+,equal|overlap} Q", "", [11]),
        ("P {+,equal|overlap} Q", "s", [11]),
        # p1 and q1 overlap, they do not cover each other
        ("P {+,equal|cover} Q", "", []),
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
