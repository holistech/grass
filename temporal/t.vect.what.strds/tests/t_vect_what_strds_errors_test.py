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


def test_a_where_with_a_syntax_error_is_refused(tools, rasters, vectors):
    assert "incomplete input" in _refused(
        tools, input=vectors().dataset, strds="wh_a", column="m", where="h >"
    )


def _values(tools, vector, column="m"):
    return tools.v_db_select(map=vector, columns=column, flags="c").stdout.split()


def _names(tools, vector):
    return tools.db_columns(table=vector).stdout.split()


def test_a_second_run_with_the_same_column_writes_the_values_again(
    tools, rasters, vectors
):
    data = vectors()
    options = {"input": data.dataset, "strds": "wh_a", "column": "m"}
    tools.t_vect_what_strds(**options)
    tools.v_db_update(map=data.maps[0], column="m", value="0")

    result = tools.t_vect_what_strds(**options, overwrite=True)

    # The values are read again; the column exists, so v.db.addcolumn is not
    # called and has no error to report.
    assert "ERROR" not in message(result)
    assert _values(tools, data.maps[0]) == ["111", "112", "121", "122"]


def test_a_second_run_with_the_same_column_is_refused_without_overwrite(
    tools, rasters, vectors
):
    data = vectors()
    options = {"input": data.dataset, "strds": "wh_a", "column": "m"}
    tools.t_vect_what_strds(**options)
    tools.v_db_update(map=data.maps[0], column="m", value="0")

    text = _refused(tools, **options)

    assert "Column <m> exists in the table of vector map" in text
    assert _values(tools, data.maps[0]) == ["0", "0", "0", "0"]


def test_a_column_of_the_second_map_stops_the_run_before_the_first_write(
    tools, rasters, vectors
):
    data = vectors()
    first, second, _third = data.maps
    tools.v_db_addcolumn(map=second, column="m INT")
    tools.v_db_update(map=second, column="m", value="999")

    text = _refused(tools, input=data.dataset, strds="wh_a", column="m")

    # The first map is checked and written before the second one in the
    # loop, so a check done only when a map is written leaves it changed.
    assert f"<{second}@" in text
    assert "m" not in _names(tools, first)
    assert _values(tools, first, "h") == ["1", "2", "3", "4"]
    assert _values(tools, second) == ["999"] * 4


def test_overwrite_writes_all_maps_when_a_column_exists_in_one(tools, rasters, vectors):
    data = vectors()
    first, second, third = data.maps
    tools.v_db_addcolumn(map=second, column="m INT")
    tools.v_db_update(map=second, column="m", value="999")

    result = tools.t_vect_what_strds(
        input=data.dataset, strds="wh_a", column="m", overwrite=True
    )

    assert "ERROR" not in message(result)
    # The raster values of the intervals: wr_1 (first), wr_3 (second, the first
    # map found in the interval) and wr_6 (third), 100 k + cell.
    assert _values(tools, first) == ["111", "112", "121", "122"]
    assert _values(tools, second) == ["311", "312", "321", "322"]
    assert _values(tools, third) == ["611", "612", "621", "622"]


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
