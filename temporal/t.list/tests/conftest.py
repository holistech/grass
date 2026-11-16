"""
Configuration and fixtures for t.list pytest suite.
"""

from datetime import datetime
from io import StringIO
from types import SimpleNamespace

import pytest

import grass.script as gs
from grass.temporal.testing.data import MapSpec, create_stds, register_stds
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture(scope="module")
def space_time_dataset(xy_module_session):
    """Create raster and vector time series in the module session.

    Returns an object with attributes about the datasets.
    """
    session = xy_module_session
    tools = Tools(session=session)

    tools.g_region(s=0, n=80, w=0, e=120, res=10)

    names = [f"temp_{i}" for i in range(1, 4)]
    times = [
        (datetime(2026, 1, 1), datetime(2026, 2, 1)),
        (datetime(2026, 2, 1), datetime(2026, 3, 1)),
        (datetime(2026, 3, 1), datetime(2026, 4, 1)),
    ]
    dataset_name = "temperature_dataset"
    create_stds(
        tools,
        "strds",
        dataset_name,
        [
            MapSpec(name, value, *time)
            for value, (name, time) in enumerate(
                zip(names, times, strict=True), start=1
            )
        ],
        title="Temperature",
        description="Random series generated for tests",
    )

    vector_names = [f"vect_{i}" for i in range(1, 3)]
    # make_map() would give the vector maps an attribute table, which these
    # maps never had, so they are made here and only registered.
    for i, name in enumerate(vector_names, start=1):
        tools.v_in_ascii(
            input=StringIO(f"{i * 10}|{i * 10}"),
            output=name,
            format="point",
        )
    stvds_name = "vector_dataset"
    register_stds(
        tools,
        "stvds",
        stvds_name,
        [
            MapSpec(name, 0, *time)
            for name, time in zip(vector_names, times[:2], strict=True)
        ],
        title="Vector dataset",
        description="Vector series generated for tests",
    )

    gs.run_command("g.mapset", mapset="user1", flags="c", env=session.env)

    raster_dataset_name = "precipitation_dataset"
    create_stds(
        tools,
        "strds",
        raster_dataset_name,
        [MapSpec("precip_1", 2, *times[0])],
        title="Precip",
        description="user1 Dataset",
    )

    gs.run_command("g.mapset", mapset="PERMANENT", env=session.env)

    return SimpleNamespace(
        session=session,
        name=dataset_name,
        raster_dataset1=dataset_name,
        raster_dataset2=raster_dataset_name,
        map_names=names,
        raster_dataset=raster_dataset_name,
        stvds_name=stvds_name,
        vector_names=vector_names,
    )


@pytest.fixture(scope="module")
def empty_session(tmp_path_factory):
    """Start an isolated session with no temporal database."""
    path = tmp_path_factory.mktemp("empty_time_series") / "empty_project"
    with project_session(path) as session:
        yield SimpleNamespace(session=session)
