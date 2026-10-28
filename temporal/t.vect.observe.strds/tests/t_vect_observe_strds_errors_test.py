"""Test the refusals of t.vect.observe.strds"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, vector_points
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

    # The message names the empty input dataset, not the output dataset.
    assert f"Space time raster dataset <{prefix}_void@PERMANENT> is empty" in text
    assert f"<{prefix}@PERMANENT>" not in text


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


def test_a_failed_run_leaves_no_vector_map_and_no_dataset(
    tools, rasters, points, prefix
):
    _refused(tools, points, prefix, columns="1bad")

    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
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


def test_a_where_that_v_extract_refuses_is_reported(tools, rasters, points, prefix):
    text = _refused(tools, points, prefix, where="nonsense =")

    assert f"Unable to select the points of <{points}> with where" in text
    assert "Traceback" not in text


def test_a_where_with_an_input_of_several_layers_is_refused_before_any_write(
    tools, rasters, prefix
):
    name = f"{prefix}_two"
    vector_points(
        tools, name, [(0.5, 1.5), (1.5, 0.5)], attributes={"h": [1, 2]}, layers=(1, 2)
    )

    text = _refused(tools, name, prefix, where="h > 2")

    # v.extract keeps only layer 1 of its input, so the layers 2 and following
    # of the input would be lost silently.
    assert f"<{name}>" in text
    assert "where" in text
    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


@pytest.mark.parametrize("kind", ["categories", "table"])
def test_a_where_with_an_input_layer_of_only_categories_or_a_table_is_refused(
    tools, rasters, points, prefix, kind
):
    # Layer 3 has either the categories of layer 1 and no table, or a table
    # and no categories. v.extract keeps the categories and the table of
    # layer 1 only, so either would be lost.
    name = f"{prefix}_{kind}"
    if kind == "categories":
        tools.v_category(input=points, output=name, option="transfer", layer="1,3")
    else:
        tools.g_copy(vector=(points, name))
        tools.db_copy(from_table=name, to_table=f"{name}_3")
        tools.v_db_connect(map=name, table=f"{name}_3", layer=3, key="cat")

    text = _refused(tools, name, prefix, where="h > 2")

    assert f"<{name}>" in text
    assert "layers 3 besides layer 1" in text
    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


def test_overwrite_after_a_failed_run_removes_the_previous_output_too(
    tools, rasters, points, prefix
):
    # The first run makes the output map and dataset.
    tools.t_vect_observe_strds(
        input=points,
        strds="ob_a",
        output=prefix,
        vector_output=f"{prefix}_v",
        columns="obs",
    )
    assert f"{prefix}_v" in tools.g_list(type="vector").stdout.split()
    # In the second dataset the map of the second granule is gone: the first
    # granule is sampled, the second one fails, after v.category has replaced
    # the previous output map.
    create_stds(
        tools,
        "strds",
        f"{prefix}_part",
        [
            MapSpec(f"{prefix}_p1", "1", datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec(f"{prefix}_p2", "2", datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    tools.g_remove(type="raster", name=f"{prefix}_p2", flags="f")

    with pytest.raises(ToolError) as error:
        tools.t_vect_observe_strds(
            input=points,
            strds=f"{prefix}_part",
            output=prefix,
            vector_output=f"{prefix}_v",
            columns="obs",
            overwrite=True,
        )

    # The failure is in the sampling step, after the output was replaced.
    assert "Unable to run v.what.rast" in message(error.value)
    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout


def test_a_failing_v_category_is_reported(broken_tools, rasters, points, prefix):
    text = _refused(broken_tools("v.category"), points, prefix)

    assert "Unable to create new layers for vector map" in text
    assert prefix not in broken_tools().t_list(type="stvds", columns="name").stdout


def test_a_failing_v_db_addcolumn_is_reported(broken_tools, rasters, points, prefix):
    text = _refused(broken_tools("v.db.addcolumn"), points, prefix)

    assert "Unable to add column" in text
    assert "Traceback" not in text


def test_a_failing_name_of_layer_one_removes_the_vector_output(
    broken_tools, rasters, points, prefix
):
    # With where, layer 1 of the output is connected again under the layer
    # name of the input. Only that call fails; v.db.connect -g, which reads
    # the connections before it, runs the real tool.
    broken = broken_tools("v.db.connect", passing="-g")

    text = _refused(broken, points, prefix, where="h > 2")

    assert f"Unable to name layer 1 of vector map <{prefix}_v>" in text
    assert "Traceback" not in text
    assert broken.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
    assert prefix not in broken.t_list(type="stvds", columns="name").stdout


def test_a_column_that_differs_only_in_case_fails_at_v_what_rast(
    tools, rasters, points, prefix
):
    text = _refused(tools, points, prefix, columns="H", overwrite=True)

    # The column h of the input table is taken for H, as SQLite does, and
    # passes with overwrite. v.what.rast looks for H as written, does not
    # find it and fails to add it to the table.
    assert "duplicate column name: H" in text
    assert f"Unable to run v.what.rast for vector map <{prefix}_v> with layer 1" in text
    assert tools.g_list(type="vector", pattern=f"{prefix}_v").stdout.split() == []
    assert prefix not in tools.t_list(type="stvds", columns="name").stdout
