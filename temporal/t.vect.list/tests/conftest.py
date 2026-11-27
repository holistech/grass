"""Fixture for t.vect.list test"""

from datetime import datetime
from io import StringIO
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, intervals, register_stds
from grass.tools import Tools


@pytest.fixture(scope="module")
def space_time_vector_dataset(xy_module_session):
    """Create a vector time series in the module session

    Returns object with attributes about the dataset.
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
    )
    names = [f"precipitation_{i}" for i in range(1, 7)]
    times = intervals(len(names))
    dataset_name = "precipitation"
    # make_map() would give the vector maps an attribute table, which these
    # maps never had, so they are made here and only registered.
    for i, name in enumerate(names, start=1):
        tools.v_in_ascii(
            input=StringIO(f"{i * 10}|{i * 10}"),
            output=name,
            format="point",
        )
    register_stds(
        tools,
        "stvds",
        dataset_name,
        [MapSpec(name, 0, *time) for name, time in zip(names, times, strict=True)],
        title="Precipitation",
        description="Random series generated for tests",
    )
    return SimpleNamespace(
        session=session,
        name=dataset_name,
        vector_names=names,
        start_times=[datetime(2001, month, 1) for month in range(1, 7)],
    )
