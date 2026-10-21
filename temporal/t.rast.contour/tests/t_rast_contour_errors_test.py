"""Test the refusals of t.rast.contour and the cases of an empty input"""

import pytest

from grass.temporal.testing.readback import message, stds_info
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_contour(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output", "basename"])
def test_a_required_option_is_checked_by_the_parser(tools, quarterly, prefix, missing):
    options = {"input": quarterly, "output": prefix, "basename": prefix, "step": 1}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="ctr_missing", output=prefix, basename=prefix, step=1)

    assert "Space time dataset <ctr_missing> of type <strds> not found" in text


def test_levels_or_step_are_needed_and_the_refusal_is_a_message(
    tools, quarterly, prefix
):
    text = _refused(tools, input=quarterly, output=prefix, basename=prefix)

    assert "Either <levels> or <step> option must be specified" in text
    assert "Traceback" not in text
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


def test_a_step_of_zero_is_refused(tools, ramps, prefix):
    text = _refused(tools, input=ramps, output=prefix, basename=prefix, step=0)

    assert "This step value is not allowed" in text
    assert "Traceback" not in text
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


def test_a_level_that_is_no_number_is_refused_by_the_parser(tools, ramps, prefix):
    text = _refused(tools, input=ramps, output=prefix, basename=prefix, levels="a")

    assert "Invalid value <a> for parameter <levels>" in text


def test_a_step_leaves_a_map_without_values_empty(tools, quarterly, prefix):
    # The three maps with values and, with -n, the empty one.
    tools.t_rast_contour(
        input=quarterly, output=prefix, basename=prefix, step=1, flags="n"
    )

    assert stds_info(tools, "stvds", prefix)["number_of_maps"] == 4


def test_a_selection_without_a_map_warns(tools, quarterly, prefix):
    result = tools.t_rast_contour(
        input=quarterly,
        output=prefix,
        basename=prefix,
        levels="2",
        where="start_time > '2010-01-01'",
    )

    assert f"Space time raster dataset <{quarterly}@PERMANENT> is empty" in message(
        result
    )
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": prefix, "levels": "2"}
    tools.t_rast_contour(**options)

    text = _refused(tools, **options)

    assert f"Space time vector dataset <{prefix}> is already in the database" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_several_empty_maps_are_all_dropped(tools, ramps, prefix):
    # Three maps without values in front of the two ramps: the names of the
    # empty maps are joined for the removal, and none of them stays.
    from datetime import datetime

    from grass.temporal.testing.data import MapSpec, create_stds, small_region

    small_region(tools, 4, 4)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_n{k}",
                "double(null())",
                datetime(2001, 1, k + 1),
                datetime(2001, 1, k + 2),
            )
            for k in range(3)
        ],
    )

    tools.t_rast_contour(
        input=f"{prefix}_in", output=prefix, basename=prefix, levels="2"
    )

    assert tools.g_list(type="vector", pattern=f"{prefix}_*").stdout.split() == []


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, quarterly, prefix):
    text = _refused(
        tools,
        input=quarterly,
        output=prefix,
        basename=prefix,
        step=1,
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout
