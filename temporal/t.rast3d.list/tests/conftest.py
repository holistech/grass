"""Fixture for t.rast3d.list test"""

from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, intervals, register_stds
from grass.tools import Tools


@pytest.fixture(scope="module")
def space_time_raster3d_dataset(xy_module_session):
    """Create a 3D raster time series in the module session

    Returns an object with metadata attributes about the generated dataset.
    """
    session = xy_module_session
    tools = Tools(session=session)

    tools.g_region(
        s=0,
        n=80,
        w=0,
        e=120,
        b=0,
        t=50,
        res=10,
        res3=10,
        tbres=10,
    )

    names = [f"vol_{i}" for i in range(1, 7)]
    max_values = [550, 445, 320, 510, 300, 650]

    # The maps hold random values, which create_stds() cannot make, so only
    # the registration is shared.
    for name, value in zip(names, max_values, strict=True):
        tools.r3_mapcalc(
            expression=f"{name} = rand(0, {value})",
            seed=1,
        )

    std_dataset = "volume_abs1"
    register_stds(
        tools,
        "str3ds",
        std_dataset,
        # The value is not used: the maps exist already.
        [
            MapSpec(name, 0, *time)
            for name, time in zip(names, intervals(len(names)), strict=True)
        ],
        title="A test with sequential files",
    )

    return SimpleNamespace(
        session=session,
        name=std_dataset,
        raster_names=names,
    )
