"""Test the refusals of t.rast.to.vect"""

import pytest

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


def test_today_a_failing_conversion_ends_with_a_traceback_and_leaves_nothing(
    tools, shapes, prefix
):
    # The area of the first map (all cells filled) cannot be written with -z.
    text = _refused(
        tools,
        input=shapes,
        output=prefix,
        basename=prefix,
        type="area",
        flags="z",
    )

    assert "Traceback" in text
    assert "r.to.vect" in text
    assert prefix not in _datasets(tools)


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.to.vect ends in an r.to.vect traceback when the conversion fails instead of a message",
)
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


def test_today_lines_of_a_map_that_is_not_thin_end_with_a_traceback(
    tools, shapes, prefix
):
    # The first map is filled in every cell; r.to.vect finds no lines in it.
    text = _refused(tools, input=shapes, output=prefix, basename=prefix, type="line")

    assert "Traceback" in text
    assert prefix not in _datasets(tools)
