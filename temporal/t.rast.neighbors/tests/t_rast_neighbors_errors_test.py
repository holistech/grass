"""Test the refusals of t.rast.neighbors and the quantile handling"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
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


def test_today_a_wrong_region_relation_is_refused_by_the_library(tools, ramp, prefix):
    # The parser does not refuse the value although the parameter lists its
    # options: the option block has no "type" line, so the type stays 0 and
    # the parser checks the options only for integer, double and string
    # (lib/gis/parser.c, check_an_opt()). The library refuses the value with
    # its own message and a traceback.
    text = _refused(
        tools, input=ramp, output=prefix, basename=prefix, region_relation="bogus"
    )

    assert (
        "Invalid spatial relation <bogus> requested. Only values 'overlaps', "
        "'is_contained', and 'contains' are allowed." in text
    )
    assert "Traceback" in text


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
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


def test_today_further_quantiles_are_ignored(tools, ramp, prefix):
    # r.neighbors computes one quantile per output map; the tool gives it the
    # whole list and gets the first, the 0.25 quantile of the corner window
    # 1, 2, 4, 5: 1.75.
    tools.t_rast_neighbors(
        input=ramp,
        output=prefix,
        basename=prefix,
        method="quantile",
        quantile="0.25,0.5",
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
