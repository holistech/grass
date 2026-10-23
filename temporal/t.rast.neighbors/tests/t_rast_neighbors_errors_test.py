"""Test the refusals of t.rast.neighbors and the quantile handling"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_daily_stds,
    create_stds,
    small_region,
)
from grass.temporal.testing.readback import cell_values, list_maps, message, stds_info
from grass.tools import ToolError


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output", "basename"])
def test_a_required_option_is_checked_by_the_parser(tools, ramp, prefix, missing):
    options = {"input": ramp, "output": prefix, "basename": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


@pytest.mark.parametrize(
    ("option", "value"),
    [
        ("method", "bogus"),
        ("weighting_function", "bogus"),
        ("semantic_labels", "bogus"),
        ("quantile", "1.5"),
    ],
)
def test_a_wrong_value_is_refused_by_the_parser(tools, ramp, prefix, option, value):
    text = _refused(
        tools, input=ramp, output=prefix, basename=prefix, **{option: value}
    )

    assert f"Value <{value}> out of range for parameter <{option}>" in text


def test_a_wrong_region_relation_is_refused_by_the_parser(tools, ramp, prefix):
    text = _refused(
        tools, input=ramp, output=prefix, basename=prefix, region_relation="bogus"
    )

    assert "Value <bogus> out of range for parameter <region_relation>" in text


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="nbr_missing", output=prefix, basename=prefix)

    assert "Space time dataset <nbr_missing> of type <strds> not found" in text


def test_the_quantile_method_needs_a_quantile(tools, ramp, prefix):
    text = _refused(
        tools, input=ramp, output=prefix, basename=prefix, method="quantile"
    )

    assert "The method <quantile> requires input in the 'quantile' option." in text


def test_a_list_of_quantiles_is_refused_by_the_parser(tools, ramp, prefix):
    # r.neighbors computes one quantile per output map, so the option takes
    # one value instead of a list of which only the first would count. The
    # parser lets the list through, the tool refuses it.
    text = _refused(
        tools,
        input=ramp,
        output=prefix,
        basename=prefix,
        method="quantile",
        quantile="0.25,0.5",
    )

    assert "Option <quantile> takes a single number, not <0.25,0.5>." in text
    assert "Traceback" not in text
    assert tools.t_list(type="strds", columns="name").stdout.count(prefix) == 0


def test_one_quantile_is_calculated(tools, ramp, prefix):
    # The 0.25 quantile of the corner window 1, 2, 4, 5 of the ramp: 1.75.
    tools.t_rast_neighbors(
        input=ramp, output=prefix, basename=prefix, method="quantile", quantile=0.25
    )

    (row,) = list_maps(tools, "strds", prefix)
    assert cell_values(tools, row.name)[0] == pytest.approx(1.75)


def test_a_quantile_without_the_method_is_ignored(tools, ramp, prefix):
    tools.t_rast_neighbors(
        input=ramp, output=prefix, basename=prefix, method="maximum", quantile=0.5
    )

    (row,) = list_maps(tools, "strds", prefix)
    assert cell_values(tools, row.name)[4] == 9.0


def test_an_existing_output_is_refused_without_overwrite(tools, ramp, prefix):
    tools.t_rast_neighbors(input=ramp, output=prefix, basename=prefix)

    text = _refused(tools, input=ramp, output=prefix, basename=prefix)

    assert f"Space time raster dataset <{prefix}> is already in the database" in text


def test_a_selection_without_a_map_warns_and_makes_no_dataset(tools, ramp, prefix):
    result = tools.t_rast_neighbors(
        input=ramp,
        output=prefix,
        basename=prefix,
        where="start_time > '2030-01-01'",
    )

    assert f"Space time raster dataset <{ramp}@PERMANENT> is empty" in message(result)
    assert tools.t_list(type="strds", columns="name").stdout.count(prefix) == 0


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_relative_time_gets_numeric_names(tools, prefix):
    # Two maps of relative time; the suffix gran has no meaning for them, so
    # the names are numbered with five digits.
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", "double((row() - 1) * 3 + col())", 0, 1),
            MapSpec(f"{prefix}_b", "double((row() - 1) * 3 + col() + 10)", 1, 2),
        ],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_neighbors(input=f"{prefix}_in", output=prefix, basename=prefix)

    rows = list_maps(tools, "strds", prefix)
    assert [(row.name, row.start) for row in rows] == [
        (f"{prefix}_00001", 0),
        (f"{prefix}_00002", 1),
    ]
    assert cell_values(tools, rows[1].name)[4] == 15.0
    assert stds_info(tools, "strds", prefix)["temporal_type"] == "relative"


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, ramp, prefix):
    text = _refused(
        tools, input=ramp, output=prefix, basename=prefix, where="nonsense ="
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout


def test_a_failing_r_neighbors_is_reported(broken_tools, ramp, prefix):
    with pytest.raises(ToolError) as error:
        broken_tools("r.neighbors").t_rast_neighbors(
            input=ramp, output=prefix, basename=prefix
        )

    assert "Error running r.neighbors" in message(error.value)


def test_a_failing_r_neighbors_is_reported_when_the_processes_are_waited_for(
    tools, broken_tools, prefix
):
    # Three maps and four processes: nothing is waited for while the maps are
    # queued, so the failure shows when the tool waits for the end of all.
    small_region(tools, 3, 3)
    create_daily_stds(tools, "strds", [f"{prefix}_in"], 3, map_prefix=prefix)

    with pytest.raises(ToolError) as error:
        broken_tools("r.neighbors").t_rast_neighbors(
            input=f"{prefix}_in", output=prefix, basename=prefix, nprocs=4
        )

    assert "Error running r.neighbors" in message(error.value)


def test_the_progress_is_reported_every_ten_maps(tools, prefix):
    small_region(tools, 3, 3)
    create_daily_stds(tools, "strds", [f"{prefix}_in"], 10, map_prefix=prefix)

    result = tools.t_rast_neighbors(
        input=f"{prefix}_in", output=prefix, basename=prefix
    )

    # Once when the tenth map is registered and once at the end.
    assert result.stderr.count("100%") == 2
