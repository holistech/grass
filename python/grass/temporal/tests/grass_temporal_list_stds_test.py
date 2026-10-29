"""Test which errors list_maps_of_stds() turns into a message"""

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal import list_stds
from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.tools import Tools


def test_an_error_of_the_code_keeps_its_traceback(monkeypatch):
    # Only a combination of columns, method and format that cannot be listed
    # is reported as a message; any other ValueError is a bug in the code.
    def broken(**kwargs):
        msg = "a bug"
        raise ValueError(msg)

    monkeypatch.setattr(list_stds, "_get_list_of_maps_stds", broken)

    with pytest.raises(ValueError, match="a bug"):
        list_stds.list_maps_of_stds(
            type="strds",
            input="a",
            columns=None,
            order=None,
            where=None,
            separator=None,
            method="delta",
        )


@pytest.fixture(scope="module")
def listed_strds(temporal_module_session):
    tgis.init(raise_fatal_error=True)
    tools = Tools(session=temporal_module_session, consistent_return_value=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    make_map(tools, "raster", "ls_map", 1)
    register_stds(
        tools,
        "strds",
        "ls_ds",
        [MapSpec("ls_map", None, day(0), day(1))],
        via="library",
    )
    return "ls_ds"


@pytest.mark.parametrize(
    "where",
    [
        pytest.param("this is not sql (", id="invalid-condition"),
        pytest.param("name = 'nothing'", id="nothing-found"),
    ],
)
def test_a_given_connection_stays_open_when_the_listing_ends_in_a_message(
    listed_strds, where
):
    # The connection belongs to the caller; the message must not close it.
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    with pytest.raises(FatalError):
        list_stds.list_maps_of_stds(
            type="strds",
            input=listed_strds,
            columns="name",
            order=None,
            where=where,
            separator=",",
            method="comma",
            dbif=dbif,
        )

    assert dbif.is_connected()
    dbif.close()


def test_every_column_of_the_delta_method_is_listed(listed_strds):
    columns = [
        "id",
        "name",
        "mapset",
        "start_time",
        "end_time",
        "interval_length",
        "distance_from_begin",
    ]

    rows, listed = list_stds._get_list_of_maps_stds(
        element_type="strds",
        name=listed_strds,
        columns=columns,
        order=None,
        where=None,
        method="delta",
        output_format="plain",
    )

    assert listed == columns
    assert [list(row) for row in rows] == [
        ["ls_map@PERMANENT", "ls_map", "PERMANENT", day(0), day(1), 1.0, 0.0]
    ]


def test_a_column_the_delta_method_cannot_list_is_refused_by_name(listed_strds):
    with pytest.raises(FatalError, match="Unsupported column 'nonsense'"):
        list_stds.list_maps_of_stds(
            type="strds",
            input=listed_strds,
            columns="id,nonsense",
            order=None,
            where=None,
            separator=None,
            method="delta",
        )


@pytest.mark.parametrize(
    ("columns", "expected"),
    [
        pytest.param("name,id", ["name", "id"], id="order"),
        pytest.param("name, id", ["name", "id"], id="blanks"),
        pytest.param("type,name", ["name"], id="type-is-no-column"),
    ],
)
def test_listed_columns_are_the_requested_ones(listed_strds, columns, expected):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        mapset = tgis.get_current_mapset()
        result = list_stds.listed_columns(dbif, "strds", "absolute", columns, mapset)
    finally:
        dbif.close()

    assert result == expected


@pytest.mark.parametrize("columns", [None, "all", "name,all"])
def test_listed_columns_are_all_the_shared_ones(listed_strds, columns):
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()
    try:
        mapset = tgis.get_current_mapset()
        result = list_stds.listed_columns(dbif, "strds", "absolute", columns, mapset)
        rows = tgis.get_dataset_list("strds", "absolute", columns, dbif=dbif)[mapset]
    finally:
        dbif.close()

    # The rows of a listing carry exactly these columns, in this order.
    assert result == list(rows[0].keys())
    assert result[0] == "id"
    assert len(result) > 3
