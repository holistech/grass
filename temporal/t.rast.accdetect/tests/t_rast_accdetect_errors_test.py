"""Test the refusals of t.rast.accdetect, and the defects around them

The tool raises every error as a Python exception, so a refusal reaches the
user inside a traceback; the messages are checked for what they say, and the
traceback is one defect (the current behavior and the expected one).
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps, message
from grass.temporal.testing.session import project_session, run_with_timeout
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


def test_an_unknown_input_is_refused_with_a_message(tools, cells):
    with pytest.raises(ToolError) as error:
        _run(tools, "no_such_dataset", "err_input2")

    assert "Space time raster dataset <no_such_dataset@PERMANENT> not found" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("option", "text"),
    [
        ("start", "Invalid date <garbage> of the option <start>"),
        ("stop", "Invalid date <garbage> of the option <stop>"),
        ("cycle", "Invalid cycle"),
        ("offset", "Invalid offset"),
    ],
)
def test_a_wrong_time_is_refused_with_a_message(tools, cells, option, text):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, f"err_{option}_x", **{option: "garbage"})

    assert text in message(error.value)
    assert "Traceback" not in message(error.value)


@pytest.mark.parametrize("option", ["start", "stop"])
def test_a_wrong_number_of_relative_time_is_refused_with_a_message(
    tools, relative, option
):
    options = {"start": "0", "cycle": "3", option: "garbage"}

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input="det_relative",
            occurrence=f"err_rel_{option}",
            basename=f"err_rel_{option}",
            range="10,50",
            **options,
        )

    assert "The options start and stop must be integers" in message(error.value)
    assert "Traceback" not in message(error.value)


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


def test_relative_time_restarts_after_the_cycle_and_the_offset(tools, relative):
    # Six maps of 20 days, one per day. The first cycle [0, 3) counts 0 1 2,
    # the offset 1 moves the next cycle to [4, 7), which holds the maps of
    # the days 4 and 5 and counts 0 1 from its start.
    create_stds(
        tools,
        "strds",
        "det_relative_six",
        [MapSpec(f"det_s{k}", 20, k, k + 1) for k in range(6)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_accdetect(
        input="det_relative_six",
        occurrence="err_rel_off",
        basename="err_rel_off",
        start="0",
        cycle="3",
        offset="1",
        range="10,50",
    )

    assert [
        (row.start, row.min) for row in list_maps(tools, "strds", "err_rel_off")
    ] == [(0, 0), (1, 1), (2, 2), (4, 0), (5, 1)]


@pytest.mark.parametrize("option", ["minimum", "maximum"])
def test_a_threshold_dataset_of_the_other_time_type_is_refused(
    tools, cells, relative, option
):
    with pytest.raises(ToolError) as error:
        _run(tools, cells, f"err_type_{option}", **{option: "det_rel_min"})

    assert f"Temporal type of input strds and {option} strds must be equal" in message(
        error.value
    )


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
def test_a_cycle_without_a_map_is_skipped(gap):
    assert run_with_timeout(gap, ARGUMENTS, 8)[0] == 0

    # The cycle of the days 1 to 3 holds two maps, the next two cycles hold
    # none, and the cycle from day 10 counts its days from 0 again: the
    # occurrence is the number of days from the start of the cycle.
    tools = Tools(session=gap, consistent_return_value=True)
    rows = [(row.start, row.min) for row in list_maps(tools, "strds", "gap_out")]
    assert rows == [
        ("2001-01-01 00:00:00", 0.0),
        ("2001-01-02 00:00:00", 1.0),
        ("2001-01-10 00:00:00", 0.0),
    ]


@pytest.mark.slow
@pytest.mark.parametrize(
    ("option", "value", "text"),
    [
        ("cycle", "0 days", "The cycle must be longer than zero"),
        ("cycle", "-3 days", "The cycle must be longer than zero"),
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


@pytest.mark.slow
def test_a_relative_cycle_of_zero_is_refused(gap):
    # Same timeout as above: without the check the tool runs until killed.
    tools = Tools(session=gap, consistent_return_value=True)
    create_stds(
        tools,
        "strds",
        "gap_rel",
        [MapSpec(f"gap_r{k}", 20, k, k + 1) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )
    arguments = [
        "t.rast.accdetect",
        "input=gap_rel",
        "occurrence=gap_rel_out",
        "basename=gap_rel_out",
        "start=0",
        "cycle=0",
        "range=10,50",
    ]

    result = run_with_timeout(gap, arguments, 8)

    assert result is not None, "the tool did not end"
    assert "The cycle must be longer than zero" in result[1]


def test_an_empty_input_dataset_ends_with_a_warning(tools, cells):
    # As t.rast.contour, t.rast.to.vect and t.rast.neighbors: a warning, no
    # output dataset, and the run ends without an error.
    tools.t_create(
        output="det_empty",
        type="strds",
        temporaltype="absolute",
        title="empty",
        description="empty",
    )

    result = _run(
        tools, cells, "err_empty_out", input="det_empty", indicator="err_empty_ind"
    )

    assert "Space time raster dataset <det_empty@PERMANENT> is empty" in (result.stderr)
    assert "Traceback" not in result.stderr
    listed = tools.t_list(type="strds").text
    assert "err_empty_out@" not in listed
    assert "err_empty_ind@" not in listed
