"""Fixture for t.rast.list test"""

from datetime import datetime
from types import SimpleNamespace

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, intervals, register_stds
from grass.tools import Tools


@pytest.fixture(scope="module")
def space_time_raster_dataset(xy_module_session):
    """Create a raster time series in the module session

    Returns object with attributes about the dataset.
    """
    session = xy_module_session
    gs.run_command(
        "g.region",
        s=0,
        n=80,
        w=0,
        e=120,
        b=0,
        t=50,
        res=10,
        res3=10,
        env=session.env,
    )
    names = [f"precipitation_{i}" for i in range(1, 7)]
    max_values = [550, 450, 320, 510, 300, 650]
    # The maps hold random values, which create_stds() cannot make, so only
    # the registration is shared.
    for name, value in zip(names, max_values, strict=False):
        gs.mapcalc(f"{name} = rand(0, {value})", seed=1, env=session.env)
    dataset_name = "precipitation"
    times = intervals(len(names))
    register_stds(
        Tools(session=session),
        "strds",
        dataset_name,
        # The value is not used: the maps exist already.
        [MapSpec(name, 0, *time) for name, time in zip(names, times, strict=True)],
        title="Precipitation",
        description="Random series generated for tests",
    )
    full_names = [f"{name}@PERMANENT" for name in names]
    return SimpleNamespace(
        session=session,
        name=dataset_name,
        raster_names=names,
        full_raster_names=full_names,
        start_times=[datetime(2001, month, 1) for month in range(1, 7)],
        env=session,
    )
