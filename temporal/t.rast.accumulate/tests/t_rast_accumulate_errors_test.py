"""Test the refusals of t.rast.accumulate, and the defects around them

Most wrong input ends with a traceback instead of a message, or does not end
at all; each such case is a test of the current behaviour and a strict xfail
of the expected one.
"""

import os
import signal
import subprocess

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

OPTIONS = {
    "start": "2001-01-01",
    "cycle": "7 days",
    "limits": "0,40",
    "method": "gdd",
}


@pytest.fixture(scope="module")
def daily(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "err_daily",
        [MapSpec(f"err_d{k}", 5 * (k + 1), day(k), day(k + 1)) for k in range(3)],
    )
    return "err_daily"


def _run(tools, name, **options):
    options = {"input": "err_daily", **OPTIONS, **options}
    return tools.t_rast_accumulate(output=name, basename=name, **options)


def test_an_unknown_input_is_refused(tools, daily):
    with pytest.raises(ToolError) as error:
        _run(tools, "err_a", input="no_such_dataset")

    assert "Space time raster dataset <no_such_dataset@PERMANENT> not found" in message(
        error.value
    )


def test_an_existing_output_is_not_overwritten(tools, daily):
    _run(tools, "err_exists")

    with pytest.raises(ToolError) as error:
        _run(tools, "err_exists")

    assert "is already in the database, use overwrite flag to overwrite" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("option", "value", "text"),
    [
        ("granularity", "x", "Invalid granularity"),
        ("cycle", "x", "Invalid cycle"),
        ("offset", "x", "Invalid offset"),
    ],
)
def test_a_wrong_length_of_time_is_refused(tools, daily, option, value, text):
    with pytest.raises(ToolError) as error:
        _run(tools, f"err_{option}", **{option: value})

    assert text in message(error.value)


@pytest.mark.parametrize("missing", ["input", "start", "cycle", "limits"])
def test_the_required_options(tools, daily, missing):
    options = {"input": "err_daily", **OPTIONS}
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(output="err_req", basename="err_req", **options)

    assert f"Required parameter <{missing}> not set" in message(error.value)


@pytest.mark.parametrize(("option", "value"), [("method", "bogus"), ("limits", "5")])
def test_a_wrong_value_is_refused_by_the_parser(tools, daily, option, value):
    with pytest.raises(ToolError) as error:
        _run(tools, "err_value", **{option: value})

    assert option in message(error.value)


@pytest.mark.parametrize("limits", ["40,0", "10,10"])
def test_today_limits_that_do_not_rise_end_with_a_traceback(tools, daily, limits):
    # r.series.accumulate refuses an upper limit that is not above the lower
    # one, and the tool does not catch the error of the call.
    with pytest.raises(ToolError) as error:
        _run(tools, "err_limits", limits=limits)

    assert "CalledModuleError" in message(error.value)


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("limits", ["40,0", "10,10"])
def test_limits_that_do_not_rise_are_refused_with_a_message(tools, daily, limits):
    with pytest.raises(ToolError) as error:
        _run(tools, "err_limits", limits=limits)

    assert "Traceback" not in message(error.value)


@pytest.mark.parametrize(
    ("option", "value", "text"),
    [
        ("start", "garbage", "AttributeError"),
        ("stop", "garbage", "TypeError"),
    ],
)
def test_today_a_wrong_date_ends_with_a_traceback(tools, daily, option, value, text):
    with pytest.raises(ToolError) as error:
        _run(tools, f"err_{option}", **{option: value})

    assert text in message(error.value)


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("option", ["start", "stop"])
def test_a_wrong_date_is_refused_with_a_message(tools, daily, option):
    with pytest.raises(ToolError) as error:
        _run(tools, f"err_{option}_x", **{option: "garbage"})

    assert "Traceback" not in message(error.value)


@pytest.fixture(scope="module")
def relative(tools, daily):
    create_stds(
        tools,
        "strds",
        "err_relative",
        [MapSpec(f"err_r{k}", 5 * (k + 1), k, k + 1) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )


def test_today_relative_time_ends_with_a_traceback(tools, relative):
    # The cycle is added to the start as text.
    with pytest.raises(ToolError) as error:
        tools.t_rast_accumulate(
            input="err_relative",
            output="err_rel",
            basename="err_rel",
            start="0",
            cycle="3",
            granularity="1",
            limits="0,40",
            method="gdd",
        )

    assert "unsupported operand type(s) for +: 'int' and 'str'" in message(error.value)


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_relative_time_accumulates(tools, relative):
    # Three maps of one day with 5, 10, 15 and the lower limit 0: sums 5, 15, 30.
    tools.t_rast_accumulate(
        input="err_relative",
        output="err_rel_ok",
        basename="err_rel_ok",
        start="0",
        cycle="3",
        granularity="1",
        limits="0,40",
        method="gdd",
    )

    assert [
        (row.start, row.end, row.min) for row in list_maps(tools, "strds", "err_rel_ok")
    ] == [
        (0, 1, 5),
        (1, 2, 15),
        (2, 3, 30),
    ]


def _run_with_timeout(session, arguments, seconds):
    """Run a tool in a process group of its own; None if it did not end in time

    The tool starts a Python process below the wrapper that subprocess knows,
    so the whole group is killed.
    """
    process = subprocess.Popen(
        arguments,
        env=session.env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        return process.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
        return None


@pytest.fixture
def gap(tmp_path):
    """A project whose dataset has a gap of more than the cycle (3 days)

    The maps lie on the days 1, 2 and 10, so the cycle [4,7) holds none.
    """
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools,
            "strds",
            "gap",
            [
                MapSpec(f"gap{k}", 5, day(offset), day(offset + 1))
                for k, offset in enumerate([0, 1, 9])
            ],
        )
        yield session


ARGUMENTS = [
    "t.rast.accumulate",
    "input=gap",
    "output=gap_out",
    "basename=gap_out",
    "start=2001-01-01",
    "cycle=3 days",
    "limits=0,40",
    "method=gdd",
]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_a_cycle_without_a_map_never_ends(gap):
    # The loop leaves the cycle through "continue" before it advances the
    # start, so it asks for the same empty cycle again and again. It had not
    # ended after 8 seconds (measured 18.10.2026 with this test).
    assert _run_with_timeout(gap, ARGUMENTS, 8) is None


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_a_cycle_without_a_map_is_skipped(gap):
    assert _run_with_timeout(gap, ARGUMENTS, 8) == 0
