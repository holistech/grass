"""Test the layers, the end and the refusals of t.rast.to.rast3

The series from 31 January has the granularity "1 month", so the cube has a
layer per month, not per day. A dataset of a single time instance has no
granularity and is refused with a message. The cube of time instants ends one
granularity after the last instant, where its top is. Maps that overlap are
refused, and so are more maps than the limit of open files allows.
"""

import os
import shutil
import sys
from datetime import datetime, timedelta
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, map_info, message
from grass.tools import ToolError, Tools

D = datetime


def test_month_end_series_has_a_layer_per_month(tools):
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    tools.t_rast_to_rast3(input="month_ends", output="month_cube")
    info = tools.r3_info(map="month_cube", flags="g").keyval
    assert (info["depths"], info["tbres"]) == (3, 1)


@pytest.mark.parametrize(
    ("name", "start", "options"),
    [
        ("absolute_instant", D(2026, 3, 1), {}),
        # Before 05.11.2026 this ended in a TypeError: the stored granularity
        # 0 gave no granule.
        ("relative_instant", 5, {"temporaltype": "relative", "unit": "days"}),
    ],
    ids=["absolute", "relative"],
)
def test_single_instant_is_refused_with_a_message(tools, name, start, options):
    create_stds(tools, "strds", name, [MapSpec(f"{name}_1", 1, start)], **options)
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_to_rast3(input=name, output=f"{name}_cube")
    text = message(error.value)
    assert f"Space time dataset <{name}@" in text
    assert "has no granularity" in text
    assert "granule" not in text
    assert "Traceback" not in text
    assert inventory(tools) == before


@pytest.mark.parametrize(
    ("times", "options", "end"),
    [
        (
            [D(2026, 3, 1), D(2026, 3, 2), D(2026, 3, 3)],
            {},
            "'2026-03-04 00:00:00'",
        ),
        # The month steps count from the first instant with a cut per step.
        (
            [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31)],
            {},
            "'2026-04-30 00:00:00'",
        ),
        ([5, 6, 7], {"temporaltype": "relative", "unit": "days"}, "'8'"),
    ],
    ids=["days", "month ends", "relative"],
)
def test_cube_of_instants_ends_after_last_plus_granularity(
    tools, prefix, times, options, end
):
    """The cube of time instants ends where its top is, a granularity later"""
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_i{number}", number, time)
            for number, time in enumerate(times)
        ],
        **options,
    )

    tools.t_rast_to_rast3(input=f"{prefix}_in", output=f"{prefix}_cube")

    info = map_info(tools, "raster_3d", f"{prefix}_cube")
    assert info["end_time"] == end
    assert tools.r3_info(map=f"{prefix}_cube", flags="g").keyval["depths"] == 3


@pytest.mark.parametrize(
    "spans",
    [
        [(1, 3), (2, 4)],
        # The same time twice, and a map inside another.
        [(1, 3), (1, 3)],
        [(1, 5), (2, 3)],
    ],
    ids=["overlap", "equal", "inside"],
)
def test_overlapping_maps_are_refused(tools, prefix, spans):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m{number}", number, D(2026, 3, start), D(2026, 3, end))
            for number, (start, end) in enumerate(spans, start=1)
        ],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_to_rast3(input=f"{prefix}_in", output=f"{prefix}_cube")

    assert (
        f"The maps of the space time raster dataset <{prefix}_in@PERMANENT> overlap, "
        "include each other or have the same time" in message(error.value)
    )
    assert inventory(tools) == before
    assert map_info(tools, "raster_3d", f"{prefix}_cube") is None


@pytest.mark.skipif(sys.platform == "win32", reason="The stand-in is a sh script")
def test_open_file_limit(tools, prefix, tmp_path):
    """More maps than the limit of open files allows end with a message

    The whole tool runs under ulimit -n 48, set by a stand-in in front of it in
    PATH that executes the real tool. r.to.rast3 opens all maps at once.
    Measured 05.11.2026 with ulimit -n and the whole tool on 28 maps: it ran
    from a limit of 64 on and ended with "Too many open files" from r.to.rast3
    at 48 and below. The test uses 64 maps, so the files of the maps alone
    exceed the limit and the result does not depend on how many descriptors
    the processes hold otherwise. The tool ends with that message and leaves
    neither the cube nor its temporary map of null cells behind.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_m{number}",
                number,
                D(2026, 3, 1) + timedelta(days=number),
                D(2026, 3, 1) + timedelta(days=number + 1),
            )
            for number in range(64)
        ],
    )
    real = shutil.which("t.rast.to.rast3", path=tools._original_env["PATH"])  # noqa: SLF001
    stand_in = tmp_path / "t.rast.to.rast3"
    stand_in.write_text(f'#!/bin/sh\nulimit -n 48\nexec "{real}" "$@"\n')
    stand_in.chmod(0o755)
    env = dict(tools._original_env)  # noqa: SLF001
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    limited = Tools(env=env, consistent_return_value=True, capture_stderr=True)
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        limited.t_rast_to_rast3(input=f"{prefix}_in", output=f"{prefix}_cube")

    text = message(error.value)
    assert "Too many open files" in text
    assert f"Unable to create 3D raster map <{prefix}_cube>" in text
    assert inventory(tools) == before
    assert map_info(tools, "raster_3d", f"{prefix}_cube") is None
