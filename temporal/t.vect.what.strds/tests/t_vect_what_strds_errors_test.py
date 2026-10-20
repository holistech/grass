"""Test the refusals of t.vect.what.strds and the cases it lets pass"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points
from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Most tests take more than a second (measured 19.10.2026 with a serial
# pytest --durations=0): every test makes its own vector maps.
pytestmark = pytest.mark.slow


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_vect_what_strds(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "strds"])
def test_a_required_option_is_checked_by_the_parser(tools, rasters, missing):
    options = {"input": "wh_dummy", "strds": "wh_a"}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


@pytest.mark.parametrize(
    "option",
    [{"method": "nothing"}, {"sampling": "sometimes"}],
)
def test_the_parser_refuses_values_outside_the_lists(tools, rasters, option):
    ((name, value),) = option.items()

    text = _refused(tools, input="wh_dummy", strds="wh_a", **option)

    assert f"Value <{value}> out of range for parameter <{name}>" in text


def test_an_unknown_vector_dataset_is_refused(tools, rasters):
    text = _refused(tools, input="wh_missing", strds="wh_a")

    assert "Space time dataset <wh_missing> of type <stvds> not found" in text


def test_an_unknown_raster_dataset_is_refused(tools, rasters, vectors):
    text = _refused(tools, input=vectors().dataset, strds="wh_missing")

    assert "Space time dataset <wh_missing> of type <strds> not found" in text


def test_instants_are_refused(tools, rasters, prefix):
    vector_points(tools, f"{prefix}_i", [(0.5, 0.5)], attributes={"h": [1]})
    register_stds(
        tools,
        "stvds",
        f"{prefix}_inst",
        [MapSpec(f"{prefix}_i", None, datetime(2001, 3, 1))],
    )

    text = _refused(tools, input=f"{prefix}_inst", strds="wh_a")

    assert (
        "All registered maps of the space time vector dataset must have time intervals"
        in text
    )


def test_today_an_empty_dataset_is_refused_as_a_dataset_of_instants(
    tools, rasters, prefix
):
    tools.t_create(
        type="stvds",
        temporaltype="absolute",
        output=f"{prefix}_void",
        title="void",
        description="no maps",
    )

    text = _refused(tools, input=f"{prefix}_void", strds="wh_a")

    assert "must have time intervals" in text


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.what.strds refuses an empty dataset as one that needs time intervals instead of saying it is empty",
)
def test_an_empty_dataset_is_reported_as_empty(tools, rasters, prefix):
    tools.t_create(
        type="stvds",
        temporaltype="absolute",
        output=f"{prefix}_void",
        title="void",
        description="no maps",
    )

    assert "is empty" in _refused(tools, input=f"{prefix}_void", strds="wh_a")


def test_a_t_where_without_a_map_says_the_dataset_is_empty(tools, rasters, vectors):
    text = _refused(
        tools,
        input=vectors().dataset,
        strds="wh_a",
        t_where="start_time > '2030-01-01'",
    )

    assert "is empty" in text


def test_the_temporal_types_must_match(tools, rasters, vectors):
    text = _refused(tools, input=vectors().dataset, strds="wh_rel")

    assert "Input and aggregation dataset must have the same temporal type" in text


def test_today_a_where_with_a_syntax_error_leaves_every_value_empty(
    tools, rasters, vectors
):
    data = vectors()

    result = tools.t_vect_what_strds(
        input=data.dataset, strds="wh_a", column="m", where="h >"
    )

    # v.what.rast reports the SQL errors and the tool ends with status 0.
    assert "incomplete input" in message(result)
    assert (
        tools.v_db_select(map=data.maps[0], columns="m", flags="c").stdout.splitlines()
        == [""] * 4
    )


@pytest.mark.xfail(
    strict=True,
    reason="t.vect.what.strds ends with status 0 for a where with a syntax error and leaves every value empty",
)
def test_a_where_with_a_syntax_error_is_refused(tools, rasters, vectors):
    assert "incomplete input" in _refused(
        tools, input=vectors().dataset, strds="wh_a", column="m", where="h >"
    )


def test_today_a_second_run_with_the_same_column_writes_the_values_again(
    tools, rasters, vectors
):
    data = vectors()
    options = {"input": data.dataset, "strds": "wh_a", "column": "m"}
    tools.t_vect_what_strds(**options)

    result = tools.t_vect_what_strds(**options)

    # v.db.addcolumn reports an error for the existing column, which the tool
    # does not treat as one; v.what.rast reads the values again.
    assert "Column <m> is already in the table" in message(result)
    assert tools.v_db_select(
        map=data.maps[0], columns="m", flags="c"
    ).stdout.split() == [
        "111",
        "112",
        "121",
        "122",
    ]


def test_a_t_where_with_a_syntax_error_is_reported_as_a_message(
    tools, rasters, vectors
):
    text = _refused(
        tools,
        input=vectors().dataset,
        strds="wh_a",
        column="m",
        t_where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid t_where condition <nonsense =>" in text
    assert "syntax error" in text
