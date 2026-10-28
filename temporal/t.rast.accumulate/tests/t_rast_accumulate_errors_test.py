"""Test the refusals of t.rast.accumulate, and the cases around them

Wrong input ends with a message, not with a traceback, and the run ends.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session, run_with_timeout
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
def test_limits_that_do_not_rise_are_refused_with_a_message(tools, daily, limits):
    with pytest.raises(ToolError) as error:
        _run(tools, "err_limits", limits=limits)

    assert "The upper limit must be above the lower limit" in message(error.value)
    assert "Traceback" not in message(error.value)


@pytest.mark.parametrize("option", ["start", "stop"])
def test_a_wrong_date_is_refused_with_a_message(tools, daily, option):
    with pytest.raises(ToolError) as error:
        _run(tools, f"err_{option}_x", **{option: "garbage"})

    assert f"Invalid date <garbage> of the option <{option}>" in message(error.value)
    assert "Traceback" not in message(error.value)


@pytest.mark.parametrize("option", ["start", "stop"])
def test_a_wrong_number_of_relative_time_is_refused_with_a_message(
    tools, relative, option
):
    options = {"start": "0", "cycle": "3", "granularity": "1", option: "garbage"}

    with pytest.raises(ToolError) as error:
        _run(tools, f"err_rel_{option}", input="err_relative", **options)

    assert "The options start and stop must be integers" in message(error.value)
    assert "Traceback" not in message(error.value)


def test_a_failing_series_run_is_reported_with_a_message(tools, daily):
    # The map is registered but gone, so r.series.accumulate cannot open it.
    create_stds(
        tools,
        "strds",
        "err_gone",
        [MapSpec("err_gone0", 5, day(0), day(1))],
    )
    tools.g_remove(type="raster", name="err_gone0", flags="f")

    with pytest.raises(ToolError) as error:
        _run(tools, "err_gone_out", input="err_gone")

    assert "Error running r.series.accumulate" in message(error.value)
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


def test_relative_time_restarts_after_the_cycle_and_the_offset(tools, relative):
    # Six maps of one day with the value 5 and the lower limit 0. The first
    # cycle [0, 3) sums 5 10 15, the offset 1 moves the next cycle to [4, 7),
    # which holds the maps of the days 4 and 5 and restarts at 5.
    create_stds(
        tools,
        "strds",
        "err_relative_six",
        [MapSpec(f"err_s{k}", 5, k, k + 1) for k in range(6)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_accumulate(
        input="err_relative_six",
        output="err_rel_off",
        basename="err_rel_off",
        start="0",
        cycle="3",
        offset="1",
        granularity="1",
        limits="0,40",
        method="gdd",
    )

    assert [
        (row.start, row.end, row.min)
        for row in list_maps(tools, "strds", "err_rel_off")
    ] == [(0, 1, 5), (1, 2, 10), (2, 3, 15), (4, 5, 5), (5, 6, 10)]


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
def test_a_cycle_without_a_map_is_skipped(gap):
    assert run_with_timeout(gap, ARGUMENTS, 8)[0] == 0

    # The cycle of the days 1 to 3 holds two maps (sums 5, 10), the next two
    # cycles hold none, and the cycle from day 10 restarts at 5.
    tools = Tools(session=gap, consistent_return_value=True)
    rows = [(row.start, row.min) for row in list_maps(tools, "strds", "gap_out")]
    assert rows == [
        ("2001-01-01 00:00:00", 5.0),
        ("2001-01-02 00:00:00", 10.0),
        ("2001-01-10 00:00:00", 5.0),
    ]


@pytest.mark.slow
@pytest.mark.parametrize(
    ("option", "value", "text"),
    [
        ("cycle", "0 days", "The cycle must be longer than zero"),
        ("cycle", "-3 days", "The cycle must be longer than zero"),
        ("granularity", "0 days", "The granularity must be longer than zero"),
        ("granularity", "-1 days", "The granularity must be longer than zero"),
        ("offset", "-3 days", "The offset must not move the next cycle back"),
        ("offset", "-5 days", "The offset must not move the next cycle back"),
    ],
)
def test_a_length_of_time_that_does_not_move_forward_is_refused(
    gap, option, value, text
):
    # Each of these ran until it was killed (checked 20.10.2026 with a timeout
    # of 10 s per call).
    arguments = [a for a in ARGUMENTS if not a.startswith(f"{option}=")]

    result = run_with_timeout(gap, [*arguments, f"{option}={value}"], 8)

    assert result is not None, "the tool did not end"
    code, messages = result
    assert code != 0
    assert text in messages
    assert "Traceback" not in messages


@pytest.mark.parametrize(
    ("option", "text"),
    [
        ("cycle", "The cycle must be longer than zero"),
        ("granularity", "The granularity must be longer than zero"),
    ],
)
def test_a_relative_length_of_time_of_zero_is_refused(tools, relative, option, text):
    options = {"start": "0", "cycle": "3", "granularity": "1", option: "0"}

    with pytest.raises(ToolError) as error:
        _run(tools, f"err_rel_zero_{option}", input="err_relative", **options)

    assert text in message(error.value)


def test_an_empty_input_dataset_ends_with_a_warning(tools, daily):
    # As t.rast.contour, t.rast.to.vect and t.rast.neighbors: a warning, no
    # output dataset, and the run ends without an error.
    tools.t_create(
        output="err_empty",
        type="strds",
        temporaltype="absolute",
        title="empty",
        description="empty",
    )

    result = _run(tools, "err_empty_out", input="err_empty")

    assert "Space time raster dataset <err_empty@PERMANENT> is empty" in (result.stderr)
    assert "Traceback" not in result.stderr
    assert "err_empty_out@" not in tools.t_list(type="strds").text
