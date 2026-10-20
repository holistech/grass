"""Test the refusals of t.rast.accdetect, and the defects around them

The tool raises every error as a Python exception, so a refusal reaches the
user inside a traceback; the messages are checked for what they say, and the
traceback is one defect (the current behavior and the expected one).
"""

import os
import signal
import subprocess

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools

OPTIONS = {"start": "2001-01-01", "cycle": "6 days", "range": "10,50"}


def _run(tools, cells, name, **options):
    options = {"input": cells, **OPTIONS, **options}
    return tools.t_rast_accdetect(occurrence=name, basename=name, **options)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_occurrence_is_not_overwritten(tools, cells):
    _run(tools, cells, "err_exists")

    with pytest.raises(ToolError) as error:
        _run(tools, cells, "err_exists")

    assert "err_exists@PERMANENT> is already in the database" in message(error.value)


def test_without_a_range_the_datasets_must_be_given(tools, cells):
    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=cells,
            occurrence="err_norange",
            basename="err_norange",
            start="2001-01-01",
            cycle="6 days",
        )

    assert "You need to set the range to compute the occurrence" in message(error.value)


@pytest.mark.parametrize("option", ["minimum", "maximum"])
def test_an_unknown_threshold_dataset_is_refused(tools, cells, option):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, f"err_{option}", **{option: "no_such_dataset"})

    assert "Space time raster dataset <no_such_dataset@PERMANENT> not found" in message(
        error.value
    )


@pytest.mark.parametrize(
    "missing", ["input", "start", "cycle", "basename", "occurrence"]
)
def test_the_required_options(tools, cells, missing):
    options = {
        "input": cells,
        "occurrence": "err_req",
        "basename": "err_req",
        "start": "2001-01-01",
        "cycle": "6 days",
        "range": "10,50",
    }
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(**options)

    assert f"Required parameter <{missing}> not set" in message(error.value)


@pytest.mark.parametrize(("option", "value"), [("range", "15"), ("staend", "1,2")])
def test_a_value_of_the_wrong_length_is_refused_by_the_parser(
    tools, cells, option, value
):
    options = {"range": "10,50", option: value}
    if option == "staend":
        options["indicator"] = "err_ind_len"

    with pytest.raises(ToolError) as error:
        _run(tools, cells, "err_len", **options)

    assert f"Option <{option}> must be provided in multiples of" in message(error.value)


def test_a_refusal_comes_without_a_traceback(tools, cells):
    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=cells,
            occurrence="err_tb2",
            basename="err_tb2",
            start="2001-01-01",
            cycle="6 days",
        )

    assert "You need to set the range to compute the occurrence" in message(error.value)
    assert "Traceback" not in message(error.value)


def test_today_an_unknown_input_ends_with_an_attribute_error(tools, cells):
    # The message names a method (get_output_map_instance) that the dataset
    # does not have.
    with pytest.raises(ToolError) as error:
        _run(tools, "no_such_dataset", "err_input")

    assert "AttributeError" in message(error.value)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect with an unknown input ends in an AttributeError (get_output_map_instance) instead of naming the missing dataset",
)
def test_an_unknown_input_is_refused_with_a_message(tools, cells):
    with pytest.raises(ToolError) as error:
        _run(tools, "no_such_dataset", "err_input2")

    assert "Space time raster dataset <no_such_dataset@PERMANENT> not found" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("option", "value"), [("start", "garbage"), ("cycle", "garbage")]
)
def test_today_a_wrong_time_ends_with_a_traceback(tools, cells, option, value):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, f"err_{option}", **{option: value})

    assert "TypeError" in message(error.value)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect with a wrong start or cycle ends in a TypeError traceback instead of a message",
)
@pytest.mark.parametrize("option", ["start", "cycle"])
def test_a_wrong_time_is_refused_with_a_message(tools, cells, option):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, f"err_{option}_x", **{option: "garbage"})

    assert "TypeError" not in message(error.value)


@pytest.fixture(scope="module")
def relative(tools, cells):
    create_stds(
        tools,
        "strds",
        "det_relative",
        [MapSpec(f"det_r{k}", 20, k, k + 1) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )
    create_stds(
        tools,
        "strds",
        "det_rel_min",
        [MapSpec("det_rel_min_a", 5, 0, 10)],
        temporaltype="relative",
        unit="days",
    )


def test_today_relative_time_ends_with_a_traceback(tools, relative):
    # The cycle is added to the start as text.
    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input="det_relative",
            occurrence="err_rel",
            basename="err_rel",
            start="0",
            cycle="3",
            range="10,50",
        )

    assert "unsupported operand type(s) for +: 'int' and 'str'" in message(error.value)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect with relative time fails because the cycle is added to the start as text",
)
def test_relative_time_detects(tools, relative):
    # Three maps of 20 days, one per day: the occurrence is the day number.
    tools.t_rast_accdetect(
        input="det_relative",
        occurrence="err_rel_ok",
        basename="err_rel_ok",
        start="0",
        cycle="3",
        range="10,50",
    )

    assert [
        (row.start, row.min) for row in list_maps(tools, "strds", "err_rel_ok")
    ] == [
        (0, 0),
        (1, 1),
        (2, 2),
    ]


def test_today_a_threshold_dataset_of_the_other_time_type_is_accepted(
    tools, cells, relative
):
    # The tool means to refuse it (see t.rast.accumulate); no map of the
    # dataset relates to a granule, so the range applies.
    _run(tools, cells, "err_type", minimum="det_rel_min")


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect accepts a threshold dataset of the other time type, the check compares the type before the dataset is read",
)
def test_a_threshold_dataset_of_the_other_time_type_is_refused(tools, cells, relative):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, "err_type2", minimum="det_rel_min")

    assert "Temporal type of input strds and minimum strds must be equal" in message(
        error.value
    )


def _run_with_timeout(session, arguments, seconds):
    """Run a tool in a process group of its own; None if it did not end in time"""
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
                MapSpec(f"gap{k}", 20, day(offset), day(offset + 1))
                for k, offset in enumerate([0, 1, 9])
            ],
        )
        yield session


ARGUMENTS = [
    "t.rast.accdetect",
    "input=gap",
    "occurrence=gap_out",
    "basename=gap_out",
    "start=2001-01-01",
    "cycle=3 days",
    "range=10,50",
]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_a_cycle_without_a_map_never_ends(gap):
    # Same loop as in t.rast.accumulate: "continue" before the start advances.
    # It had not ended after 8 seconds (measured 18.10.2026 with this test).
    assert _run_with_timeout(gap, ARGUMENTS, 8) is None


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="t.rast.accdetect loops forever on a cycle without a map, the loop continues before the start advances",
)
def test_a_cycle_without_a_map_is_skipped(gap):
    assert _run_with_timeout(gap, ARGUMENTS, 8) == 0
