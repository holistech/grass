"""Fixture for t.vect.db.select tests"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, intervals
from grass.tools import Tools


@pytest.fixture(scope="module")
def space_time_vector_dataset(xy_module_session):
    """Create space time vector datasets in the module session.

    Returns an object containing metadata attributes about the generated datasets.
    """
    session = xy_module_session
    tools = Tools(session=session)

    tools.g_region(s=0, n=80, w=0, e=120, b=0, t=50, res=10, res3=10)

    tools.v_random(output="prec_points", n=3, seed=1, flags="z", overwrite=True)

    interval_strds = "precip_abs1"
    create_stds(
        tools,
        "strds",
        interval_strds,
        [
            MapSpec(f"prec_int_{i}", i * 100.0, *time)
            for i, time in enumerate(intervals(3, start=2), start=1)
        ],
        title="A test",
    )

    interval_stvds = "prec_observer_interval"
    tools.t_vect_observe_strds(
        input="prec_points",
        strds=interval_strds,
        output=interval_stvds,
        vector=interval_stvds,
        column="observation",
    )

    instance_strds = "precip_abs2"
    create_stds(
        tools,
        "strds",
        instance_strds,
        [
            MapSpec(f"prec_inst_{i}", i * 100.0, start)
            for i, start in enumerate(
                [datetime(2004, 1, 1), datetime(2004, 4, 1), datetime(2004, 7, 1)],
                start=1,
            )
        ],
        title="B test",
    )

    instance_stvds = "prec_observer_instance"
    tools.t_vect_observe_strds(
        input="prec_points",
        strds=instance_strds,
        output=instance_stvds,
        vector=instance_stvds,
        column="observation",
    )

    return SimpleNamespace(
        session=session,
        interval_name=interval_stvds,
        instance_name=instance_stvds,
    )
