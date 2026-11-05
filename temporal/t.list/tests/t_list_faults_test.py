"""Test the messages and the exit codes of t.list for options that name something wrong

An order that the type has no column for is reported as an order, not as a
where condition. A mapset that the project does not have is an error, while
a mapset without a temporal database lists nothing.
"""

import pytest

from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError


def test_invalid_order_names_order(tools, prefix, make_stds):
    make_stds(1)
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_list(
            type="raster",
            order="number_of_maps",
            where=f"name LIKE '{prefix}%'",
        )
    text = message(error.value)
    assert "Invalid order <number_of_maps>" in text
    assert "no such column: number_of_maps" in text
    assert "Invalid where condition" not in text
    assert inventory(tools) == before


def test_invalid_where_still_names_where(tools, prefix, make_stds):
    make_stds(1)
    with pytest.raises(ToolError) as error:
        tools.t_list(type="raster", order="name", where="nosuchcolumn = 1")
    text = message(error.value)
    assert "Invalid where condition <nosuchcolumn = 1>" in text
    assert "Invalid order" not in text


def test_invalid_where_and_order_name_where(tools, prefix, make_stds):
    make_stds(1)
    with pytest.raises(ToolError) as error:
        tools.t_list(type="raster", order="number_of_maps", where="nosuchcolumn = 1")
    assert "Invalid where condition <nosuchcolumn = 1>" in message(error.value)


@pytest.mark.parametrize("mapset", ["nosuchmapset", "PERMANENT,nosuchmapset"])
def test_unknown_mapset_fails(tools, mapset):
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_list(type="strds", mapset=mapset)
    assert error.value.returncode != 0
    assert "Mapset <nosuchmapset> not found in the project." in message(error.value)
    assert inventory(tools) == before


def test_known_mapset_without_database_lists_nothing(tools):
    result = tools.t_list(type="strds", mapset="PERMANENT", columns="id")
    assert result.returncode == 0
