"""Test the refusals of t.vect.what.strds and the cases it lets pass"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    register_stds,
    vector_points,
)
from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Most tests take more than a second (measured 19.10.2026 with a serial
# pytest --durations=0): every test makes its own vector maps.
pytestmark = pytest.mark.slow

# The points of the maps from the fixture vectors() in conftest.py
CENTRES = [(0.5, 1.5), (1.5, 1.5), (0.5, 0.5), (1.5, 0.5)]


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


def test_a_second_run_with_overwrite_writes_the_values_again(tools, rasters, vectors):
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


@pytest.mark.parametrize("overwrite", [False, True])
def test_a_later_map_without_a_table_stops_the_run_before_the_first_write(
    tools, rasters, vectors, overwrite
):
    data = vectors()
    first, second, third = data.maps
    tools.v_db_droptable(map=third, flags="f")

    text = _refused(
        tools, input=data.dataset, strds="wh_a", column="m", overwrite=overwrite
    )

    # Adding the column to the third map fails; found only there, the first
    # two maps would already have the column and their values.
    assert f"Vector map <{third}@" in text
    assert "has no attribute table in layer 1" in text
    assert "m" not in _names(tools, first)
    assert "m" not in _names(tools, second)


# Unchecked, v.db.addcolumn fails on the map of the other mapset, or, with
# overwrite and m already there, v.what.rast; both after the first map was
# written.
@pytest.mark.parametrize(
    ("overwrite", "column", "foreign_first"),
    [(False, "h", False), (True, "m", False), (False, "h", True)],
)
def test_a_map_of_another_mapset_stops_the_run_before_the_first_write(
    two_mapsets, prefix, overwrite, column, foreign_first
):
    work, other = two_mapsets
    times = [(datetime(2001, 1, 1), datetime(2001, 2, 1))]
    times.append((datetime(2001, 2, 1), datetime(2001, 3, 1)))
    create_stds(
        work,
        "strds",
        f"{prefix}_r",
        [MapSpec(f"{prefix}_r{k}", k, *time) for k, time in enumerate(times, 1)],
    )
    vector_points(work, f"{prefix}_v1", [(0.5, 0.5)], attributes={"h": [1]})
    vector_points(other, f"{prefix}_v2", [(0.5, 0.5)], attributes={column: [7]})
    local = MapSpec(f"{prefix}_v1", None, *times[0])
    foreign = MapSpec(f"{prefix}_v2@other", None, *times[1])
    if foreign_first:
        # The foreign map takes the first interval
        local = MapSpec(f"{prefix}_v1", None, *times[1])
        foreign = MapSpec(f"{prefix}_v2@other", None, *times[0])
    register_stds(work, "stvds", f"{prefix}_ds", [local, foreign])

    with pytest.raises(ToolError) as error:
        work.t_vect_what_strds(
            input=f"{prefix}_ds",
            strds=f"{prefix}_r",
            column="m",
            overwrite=overwrite,
        )

    # v.db.addcolumn and v.what.rast write only in the current mapset.
    assert f"Vector map <{prefix}_v2@other> is not in the current mapset" in (
        message(error.value)
    )
    assert "Traceback" not in message(error.value)
    assert "m" not in work.db_columns(table=f"{prefix}_v1").stdout.split()


def test_overwrite_keeps_the_type_of_an_integer_column(tools, rasters, vectors, prefix):
    # The maps are the constant k, one month each from 2001-03-01, so the
    # average during May (k = 3) and June (k = 4) is 3.5.
    create_stds(
        tools,
        "strds",
        f"{prefix}_k",
        [
            MapSpec(
                f"{prefix}_k{k}",
                f"{k}",
                datetime(2001, k + 2, 1),
                datetime(2001, k + 3, 1),
            )
            for k in range(1, 7)
        ],
    )
    data = vectors()
    options = {
        "input": data.dataset,
        "strds": f"{prefix}_k",
        "column": "m",
        "sampling": "during",
    }
    # The integer map of May makes m an INTEGER column.
    tools.t_vect_what_strds(**options)
    tools.v_db_update(map=data.maps[1], column="m", value="0")

    result = tools.t_vect_what_strds(**options, method="average", overwrite=True)

    # The column is not replaced. SQLite keeps 3.5 (probe 23.10.2026 with
    # CAST(m AS TEXT) in db.select), but GRASS reads the INTEGER column as 3;
    # v.what.rast warns about it.
    assert "some data lost" in message(result)
    assert "m:INTEGER" in tools.db_describe(table=data.maps[1], flags="c").stdout
    assert _values(tools, data.maps[1]) == ["3"] * 4


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


def test_a_where_that_fails_at_a_later_table_is_refused(tools, rasters, vectors):
    data = vectors()
    first, second, third = data.maps
    # Only the third table lacks the column foo, so the condition holds at
    # the first two and fails at the last one. Two failing tables would leave
    # open which one is named, as the where pre-check runs in dataset order.
    for name in (first, second):
        tools.v_db_addcolumn(map=name, columns="foo integer")

    text = _refused(
        tools, input=data.dataset, strds="wh_a", column="m", where="foo = 1"
    )

    assert f"Invalid where condition <foo = 1> for vector map <{third}@" in text
    # Nothing is written before the third map is found to fail.
    assert "m" not in _names(tools, first)
    assert "m" not in _names(tools, second)


@pytest.fixture
def one_layer_twice(tools, rasters, prefix):
    """The map <prefix>_c under the ids c and c:1, one month each

    The raster dataset wh_a has wr_1 for March and wr_2 for April 2001, so
    c (March) samples wr_1 and c:1 (April) samples wr_2. Both ids name layer
    1 of one map.
    """
    vector_points(tools, f"{prefix}_c", CENTRES, attributes={"h": [1, 2, 3, 4]})
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [
            MapSpec(f"{prefix}_c", None, datetime(2001, 3, 1), datetime(2001, 4, 1)),
            MapSpec(f"{prefix}_c:1", None, datetime(2001, 4, 1), datetime(2001, 5, 1)),
        ],
    )
    return SimpleNamespace(dataset=f"{prefix}_ds", vector=f"{prefix}_c")


def test_one_layer_under_two_ids_with_column_is_refused(
    tools, rasters, one_layer_twice, prefix
):
    text = _refused(tools, input=one_layer_twice.dataset, strds="wh_a", column="w")

    # Both ids would write the column w of one table; the value of the
    # earlier interval would be lost without a word.
    assert f"<{prefix}_c@" in text
    assert f"<{prefix}_c:1@" in text
    assert "would both write column <w>" in text
    assert "w" not in _names(tools, one_layer_twice.vector)


def test_one_layer_under_two_ids_without_column_is_allowed(
    tools, rasters, one_layer_twice
):
    tools.t_vect_what_strds(input=one_layer_twice.dataset, strds="wh_a")

    # Each raster map has its own column, so nothing is overwritten: the
    # points read 100 k + cell for the map k.
    assert _values(tools, one_layer_twice.vector, "wr_1") == [
        "111",
        "112",
        "121",
        "122",
    ]
    assert _values(tools, one_layer_twice.vector, "wr_2") == [
        "211",
        "212",
        "221",
        "222",
    ]


def test_two_layers_of_one_map_with_column_are_allowed(tools, rasters, prefix):
    vector_points(
        tools,
        f"{prefix}_c",
        CENTRES,
        attributes={"h": [1, 2, 3, 4]},
        layers=(1, 2),
    )
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [
            MapSpec(f"{prefix}_c:1", None, datetime(2001, 3, 1), datetime(2001, 4, 1)),
            MapSpec(f"{prefix}_c:2", None, datetime(2001, 4, 1), datetime(2001, 5, 1)),
        ],
    )

    tools.t_vect_what_strds(input=f"{prefix}_ds", strds="wh_a", column="w")

    # Each layer has its own table, so w is written once in each: wr_1 for
    # layer 1 and wr_2 for layer 2.
    assert _values(tools, f"{prefix}_c", "w") == ["111", "112", "121", "122"]
    assert tools.db_select(
        sql=f"SELECT w FROM {prefix}_c_2", flags="c"
    ).stdout.split() == ["211", "212", "221", "222"]


def test_a_where_failing_at_two_tables_names_the_first_in_dataset_order(
    tools, rasters, vectors
):
    data = vectors()
    first, second, third = data.maps
    tools.v_db_addcolumn(map=first, columns="foo integer")

    text = _refused(
        tools, input=data.dataset, strds="wh_a", column="m", where="foo = 1"
    )

    # The second and the third table lack foo. The dataset lists the second
    # map before the third (May before August), so it is the one named.
    assert f"for vector map <{second}@" in text
    assert f"<{third}@" not in text


def test_one_layer_under_two_ids_hitting_one_raster_map_is_refused(
    tools, rasters, prefix
):
    vector_points(tools, f"{prefix}_c", CENTRES, attributes={"h": [1, 2, 3, 4]})
    register_stds(
        tools,
        "stvds",
        f"{prefix}_ds",
        [
            MapSpec(f"{prefix}_c", None, datetime(2001, 3, 1), datetime(2001, 4, 1)),
            MapSpec(f"{prefix}_c:1", None, datetime(2001, 3, 1), datetime(2001, 4, 1)),
        ],
    )

    text = _refused(tools, input=f"{prefix}_ds", strds="wh_a")

    # Both intervals are March, so both ids would write the column wr_1.
    assert "would both write column <wr_1>" in text
    assert "wr_1" not in _names(tools, f"{prefix}_c")


def test_a_where_with_a_map_without_a_table_names_the_missing_table(
    tools, rasters, vectors
):
    data = vectors()
    first, second, third = data.maps
    tools.v_db_droptable(map=third, flags="f")

    text = _refused(tools, input=data.dataset, strds="wh_a", column="m", where="h > 2")

    # The where condition is tried on the tables there are; the map without
    # one is refused by the check of the target columns after it.
    assert f"Vector map <{third}@" in text
    assert "has no attribute table in layer 1" in text
    assert "Invalid where condition" not in text
    assert "m" not in _names(tools, first)
    assert "m" not in _names(tools, second)


def test_a_failing_v_db_addcolumn_is_reported(broken_tools, rasters, vectors):
    data = vectors()

    text = _refused(
        broken_tools("v.db.addcolumn"), input=data.dataset, strds="wh_a", column="m"
    )

    assert f"Unable to add column m to vector map <{data.maps[0]}@" in text
    assert "Traceback" not in text


def test_a_failing_v_what_rast_is_reported(broken_tools, rasters, vectors):
    data = vectors()

    text = _refused(
        broken_tools("v.what.rast"), input=data.dataset, strds="wh_a", column="m"
    )

    assert (
        f"Unable to run v.what.rast for vector map <{data.maps[0]}@PERMANENT> and "
        "raster map <wr_1@PERMANENT>"
    ) in text
    assert "Traceback" not in text


def test_a_failing_removal_of_the_aggregate_map_is_reported(
    broken_tools, rasters, vectors
):
    data = vectors()

    # The second interval, May to July, holds wr_3 and wr_4; their average is
    # a temporary map, which g.remove fails to remove.
    text = _refused(
        broken_tools("g.remove"),
        input=data.dataset,
        strds="wh_a",
        column="m",
        method="average",
    )

    assert "Unable to remove raster map <aggreagated_map_name_" in text
    assert "Traceback" not in text


def test_a_column_that_differs_only_in_case_fails_at_v_what_rast(
    tools, rasters, vectors
):
    data = vectors()

    text = _refused(tools, input=data.dataset, strds="wh_a", column="H", overwrite=True)

    # The check of the target columns takes H for the column h, as SQLite
    # does, and lets it pass with overwrite. v.what.rast looks for H as
    # written, does not find it and fails to add it to the table.
    assert "duplicate column name: H" in text
    assert (
        f"Unable to run v.what.rast for vector map <{data.maps[0]}@PERMANENT> and "
        "raster map <wr_1@PERMANENT>"
    ) in text
    assert _values(tools, data.maps[0], "h") == ["1", "2", "3", "4"]
