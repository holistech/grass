"""Test which errors list_maps_of_stds() turns into a message"""

import pytest

import grass.temporal as tgis
from grass.exceptions import ScriptError
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

    with pytest.raises((SystemExit, ScriptError)):
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
