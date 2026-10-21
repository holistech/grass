"""Test the refusals of t.vect.observe.strds"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import message
from grass.tools import ToolError


def _refused(tools, points, prefix, **options):
    options = {
        "input": points,
        "strds": "ob_a",
        "output": prefix,
        "vector_output": f"{prefix}_v",
        "columns": "obs",
        **options,
    }
    with pytest.raises(ToolError) as error:
        tools.t_vect_observe_strds(**options)
    return message(error.value)


@pytest.mark.parametrize(
    "missing", ["input", "strds", "output", "vector_output", "columns"]
)
def test_a_required_option_is_checked_by_the_parser(
    tools, rasters, points, prefix, missing
):
    options = {
        "input": points,
        "strds": "ob_a",
        "output": prefix,
        "vector_output": f"{prefix}_v",
        "columns": "obs",
    }
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_vect_observe_strds(**options)

    assert f"Required parameter <{missing}> not set" in message(error.value)


@pytest.mark.parametrize(("strds", "columns"), [("ob_a", "a,b"), ("ob_a,ob_b", "a")])
def test_the_columns_must_match_the_datasets(
    tools, rasters, points, prefix, strds, columns
):
    text = _refused(tools, points, prefix, strds=strds, columns=columns)

    assert (
        "The number of columns must be equal to the number of space time raster "
        "datasets"
    ) in text


def test_an_unknown_dataset_is_refused(tools, rasters, points, prefix):
    text = _refused(tools, points, prefix, strds="ob_missing")

    assert "Space time dataset <ob_missing> of type <strds> not found" in text


def test_the_datasets_must_have_the_same_temporal_type(tools, rasters, points, prefix):
    text = _refused(tools, points, prefix, strds="ob_a,ob_rel", columns="a,b")

    assert "Temporal type of space time raster datasets must be equal" in text
    assert (
        "<ob_a@PERMANENT> of type absolute do not match <ob_rel@PERMANENT> of type relative"
        in text
    )


def test_an_empty_dataset_is_refused(tools, rasters, points, prefix):
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_void",
        title="void",
        description="no maps",
    )

    text = _refused(tools, points, prefix, strds=f"{prefix}_void")

    # The message names the output dataset and not the empty one (the tool
    # passes the wrong id).
    assert f"Space time raster dataset <{prefix}@PERMANENT> is empty" in text


def test_an_existing_output_dataset_is_refused_without_overwrite(
    tools, rasters, points, prefix
):
    tools.t_vect_observe_strds(
        input=points,
        strds="ob_a",
        output=prefix,
        vector_output=f"{prefix}_v",
        columns="obs",
    )

    text = _refused(tools, points, prefix, vector_output=f"{prefix}_w")

    assert (
        f"Space time vector dataset <{prefix}> is already in the database. Use the "
        "overwrite flag."
    ) in text


def test_an_existing_vector_output_is_refused_without_overwrite(
    tools, rasters, points, prefix
):
    text = _refused(tools, points, prefix, vector_output=points)

    assert f"<{points}> exists. To overwrite, use the --overwrite flag" in text


def test_an_unknown_input_map_is_reported_as_a_message(tools, rasters, points, prefix):
    assert "Traceback" not in _refused(tools, points, prefix, input="ob_nothere")


def test_a_failed_run_leaves_the_vector_map_but_no_dataset_or_map_entries(
    tools, rasters, points, prefix
):
    _refused(tools, points, prefix, columns="1bad")

    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == [
        f"{prefix}_v"
    ]
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


def test_a_failed_run_leaves_no_output_dataset(tools, rasters, points, prefix):
    _refused(tools, points, prefix, columns="1bad")

    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


def test_a_column_that_the_input_table_has_is_overwritten_with_the_flag(
    tools, rasters, points, prefix
):
    # Without the column in the output table v.what.rast replaces the values
    # (1 to 4) of the copy with those of ra_1 (111 to 122).
    tools.t_vect_observe_strds(
        input=points,
        strds="ob_a",
        output=prefix,
        vector_output=f"{prefix}_v",
        columns="h",
        overwrite=True,
    )

    text = tools.v_db_select(map=f"{prefix}_v", layer=1, columns="h", flags="c").stdout
    assert text.split() == ["111", "112", "121", "122"]


def test_a_column_that_the_input_table_has_is_refused(tools, rasters, points, prefix):
    text = _refused(tools, points, prefix, columns="h")

    assert "Unable to add column" in text


def test_a_raster_map_that_is_gone_ends_the_run(tools, points, prefix):
    create_stds(
        tools,
        "strds",
        f"{prefix}_gone",
        [MapSpec(f"{prefix}_g1", "1", datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    tools.g_remove(type="raster", name=f"{prefix}_g1", flags="f")

    with pytest.raises(ToolError):
        tools.t_vect_observe_strds(
            input=points,
            strds=f"{prefix}_gone",
            output=prefix,
            vector_output=f"{prefix}_v",
            columns="obs",
        )
