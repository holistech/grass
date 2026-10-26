"""Test how extract_dataset and dataset_mapcalculator hand out their jobs

The tools run in a process of their own and cannot show how many processes the
library starts at once, or which options r.mapcalc and r3.mapcalc get, so the
runner of the batches is replaced here by one that records its arguments.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal import extract, mapcalc
from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")


class Stopped(Exception):
    """Raised by the recording runner to end the run after the first call"""


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


@pytest.mark.parametrize(
    ("type_", "name", "module", "options"),
    [
        ("raster", "bat", "r.mapcalc", {"nprocs": 1}),
        # None leaves the option out, so r3.mapcalc decides its number of threads.
        ("raster3d", "bat3", "r3.mapcalc", {"nprocs": None}),
    ],
)
def test_the_options_of_the_mapcalc_module_in_a_map_calculation(
    tools, monkeypatch, type_, name, module, options
):
    seen = []

    def stop(ctx, runner, statements, nprocs, **kwargs):
        seen.append(runner)
        raise Stopped

    monkeypatch.setattr(mapcalc, "run_in_batches", stop)

    with pytest.raises(Stopped):
        tgis.dataset_mapcalculator(
            name, "mc_out", type_, f"{name} * 2", "mc", ["equal"]
        )

    (runner,) = seen
    assert runner.args == (module,)
    assert runner.keywords == options


def test_an_invalid_where_condition_stops_with_a_fatal_error(tools):
    # The messenger raises FatalError when the framework is asked to raise; a
    # run of the tool exits with the message instead.
    with pytest.raises(FatalError, match="Invalid where condition <nonsense \\[>"):
        tgis.extract_dataset("bat", "never", "raster", "nonsense [", None, None, "num")
