"""Test the spatial topology of t.rast3d.algebra: flag -s and spatial relations

The datasets P (p1, p2) and Q (q1, q2) hold constant maps with the value
p1=1, p2=2, q1=10, q2=20. The maps p1/q1 share day 1 and p2/q2 share day 2.
p1 and q1 overlap in x, y and depth (the depth ranges 0-3 and 1-4 differ,
because maps with equal depth are not related as "overlap"), p2 and q2 are
far apart.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, register_stds
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture(scope="module")
def spatial_series(tmp_path_factory):
    """Session with the 3D datasets P and Q of the module docstring"""
    tmp_path = tmp_path_factory.mktemp("spatial_operator_3d")
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, overwrite=True)
        extents = {
            "p1": (0, 3, 0, 3),
            "p2": (0, 3, 0, 3),
            "q1": (2, 5, 1, 4),
            "q2": (100, 103, 1, 4),
        }
        values = {"p1": 1, "p2": 2, "q1": 10, "q2": 20}
        for name, (low, high, bottom, top) in extents.items():
            tools.g_region(
                w=low, e=high, s=low, n=high, t=top, b=bottom, res=1, res3=1, tbres=1
            )
            tools.r3_mapcalc(expression=f"{name} = {values[name]}")
        tools.g_region(w=0, e=103, s=0, n=103, t=4, b=0, res=1, res3=1, tbres=1)
        for dataset, maps in (("P", ("p1", "p2")), ("Q", ("q1", "q2"))):
            register_stds(
                tools,
                "str3ds",
                dataset,
                [
                    MapSpec(name, values[name], day(number - 1), day(number))
                    for number, name in enumerate(maps, start=1)
                ],
            )
        yield session


def result_values(session, expression, flags="", env=None):
    """Run the tool and return the cell values of the result maps in time order

    env replaces the environment of the session, if given.
    """
    tools = Tools(session=session, env=env, overwrite=True)
    tools.t_rast3d_algebra(expression=f"R = {expression}", basename="r", flags=flags)
    listing = tools.t_rast3d_list(input="R", columns="min,max", format="json")
    assert all(row["min"] == row["max"] for row in listing["data"])
    return [row["min"] for row in listing["data"]]


@pytest.mark.parametrize(
    ("expression", "flags", "expected"),
    [
        # r3.mapcalc gives an all-null map for the disjoint pair p2/q2, and
        # such a map is not registered, so only the overlapping pair remains.
        ("P {+,equal} Q", "", [11]),
        ("P {+,equal} Q", "s", [11]),
        ("P {+,equal|overlap} Q", "s", [11]),
        # p1 and q1 overlap, they do not cover each other
        ("P {+,equal|cover} Q", "s", []),
        # the condition yields P itself, so the disjoint pair shows up as p2
        ("if(P {#} Q == 1, P)", "", [1, 2]),
        ("if(P {#} Q == 1, P)", "s", [1]),
    ],
)
def test_spatial_topology(spatial_series, expression, flags, expected):
    """-s and spatial relations restrict the related maps to spatially related"""
    assert result_values(spatial_series, expression, flags) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("P {+,equal|overlap} Q", [11]),
        ("P {+,equal|cover} Q", []),
        # p2 has no spatially related map, as q2 is far away
        ("if(P {#,equal|overlap} Q == 1, P)", [1]),
    ],
)
@pytest.mark.parametrize("flags", ["", "c"])
def test_spatial_relation_without_spatial_flag(
    spatial_series, expression, expected, flags
):
    """The name of a spatial relation builds the spatial topology without -s,
    in the classic and in the new algebra"""
    assert result_values(spatial_series, expression, flags) == expected
