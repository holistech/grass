"""Test the refusals of t.rast.to.vect"""

import pytest

from grass.temporal.testing.data import create_daily_stds, small_region
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_to_vect(**options)
    return message(error.value)


def _datasets(tools):
    return tools.t_list(type="stvds", format="json").stdout


@pytest.mark.parametrize("missing", ["input", "output", "basename", "type"])
def test_a_required_option_is_checked_by_the_parser(tools, shapes, prefix, missing):
    options = {"input": shapes, "output": prefix, "basename": prefix, "type": "point"}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_type_is_refused_by_the_parser(tools, shapes, prefix):
    text = _refused(tools, input=shapes, output=prefix, basename=prefix, type="curve")

    assert "Value <curve> out of range for parameter <type>" in text


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(
        tools, input="tv_missing", output=prefix, basename=prefix, type="point"
    )

    assert "Space time dataset <tv_missing> of type <strds> not found" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(tools, shapes, prefix):
    options = {"input": shapes, "output": prefix, "basename": prefix, "type": "point"}
    tools.t_rast_to_vect(**options)

    text = _refused(tools, **options)

    assert f"Space time vector dataset <{prefix}> is already in the database" in text
    assert len(list_maps(tools, "stvds", prefix)) == 3


def test_a_failing_conversion_ends_with_a_message(tools, shapes, prefix):
    text = _refused(
        tools,
        input=shapes,
        output=prefix,
        basename=prefix,
        type="area",
        flags="z",
    )

    assert "Traceback" not in text
    assert "Error running r.to.vect" in text
    assert prefix not in _datasets(tools)


def test_lines_of_a_map_that_is_not_thin_are_refused_with_a_message(
    tools, shapes, prefix
):
    # The first map is filled in every cell; r.to.vect finds no lines in it.
    text = _refused(tools, input=shapes, output=prefix, basename=prefix, type="line")

    assert "Traceback" not in text
    assert "Error running r.to.vect" in text
    assert prefix not in _datasets(tools)


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, shapes, prefix):
    text = _refused(
        tools,
        input=shapes,
        output=prefix,
        basename=prefix,
        type="point",
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout


def test_a_failing_r_to_vect_is_reported(broken_tools, shapes, prefix):
    with pytest.raises(ToolError) as error:
        broken_tools("r.to.vect").t_rast_to_vect(
            input=shapes, output=prefix, basename=prefix, type="point"
        )

    assert "Error running r.to.vect" in message(error.value)


def test_a_failing_r_to_vect_is_reported_when_the_processes_are_waited_for(
    broken_tools, shapes, prefix
):
    # Three maps and four processes: nothing is waited for while the maps are
    # queued, so the failure shows when the tool waits for the end of all.
    with pytest.raises(ToolError) as error:
        broken_tools("r.to.vect").t_rast_to_vect(
            input=shapes,
            output=prefix,
            basename=prefix,
            type="point",
            nprocs=4,
            flags="t",
        )

    assert "Error running r.to.vect" in message(error.value)


def test_the_progress_is_reported_every_ten_maps(tools, prefix):
    small_region(tools, 3, 3)
    create_daily_stds(tools, "strds", [f"{prefix}_in"], 10, map_prefix=prefix)

    result = tools.t_rast_to_vect(
        input=f"{prefix}_in", output=prefix, basename=prefix, type="point"
    )

    # Once when the tenth process is queued, once when the tenth map is
    # registered and once at the end.
    assert result.stderr.count("100%") == 3
