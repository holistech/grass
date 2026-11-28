"""Test how extract_dataset hands out its jobs

The tools run in a process of their own and cannot show how many processes the
library starts at once, so the runner of the batches is replaced here by one
that records its arguments.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal import extract
from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    small_region(tools, 2, 3, depths=2)
    for stds_type, name in (("strds", "bat"), ("str3ds", "bat3")):
        create_stds(
            tools,
            stds_type,
            name,
            [
                MapSpec(f"{name}{n}", n, datetime(2001, n, 1), datetime(2001, n + 1, 1))
                for n in range(1, 6)
            ],
        )
    return tools


@pytest.mark.parametrize(
    ("nprocs", "sizes"), [(2, [2, 2, 1]), (5, [5]), (0, [5]), (1, [1] * 5)]
)
def test_the_jobs_are_run_in_groups_of_nprocs(tools, monkeypatch, nprocs, sizes):
    seen = []
    run_in_batches = extract.run_in_batches

    def recording(ctx, runner, statements, size, **kwargs):
        seen.append(len(statements))
        return run_in_batches(ctx, runner, statements, size, **kwargs)

    monkeypatch.setattr(extract, "run_in_batches", recording)

    tgis.extract_dataset(
        "bat", f"out{nprocs}", "raster", None, "bat * 2", f"res{nprocs}", "num", nprocs
    )

    assert seen == sizes


def test_an_invalid_where_condition_stops_with_a_fatal_error(tools):
    # The messenger raises FatalError when the framework is asked to raise; a
    # run of the tool exits with the message instead.
    with pytest.raises(FatalError, match="Invalid where condition <nonsense \\[>"):
        tgis.extract_dataset("bat", "never", "raster", "nonsense [", None, None, "num")
