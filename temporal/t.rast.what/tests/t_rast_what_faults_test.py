"""Test the message of an empty sample and the coordinates of t.rast.what

The data are described in conftest.py.
"""

from io import StringIO

import pytest

from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

# Cell (1, 1) of the region has its centre at (0.5, 2.5). The point lies inside
# the cell, so the value is the one of the cell: 11, 111 and 211 for the maps.
X = "0.123456789012"
Y = "2.5"
TIMES = [
    ("2001-01-01 00:00:00", "2001-01-02 00:00:00"),
    ("2001-01-02 00:00:00", "2001-01-03 00:00:00"),
    ("2001-01-03 00:00:00", "2001-01-04 00:00:00"),
]


def test_message_without_separator_hint(tools, sampled):
    """The message of an empty sample does not name the separator

    A map without points gives no line for any reason that a separator could
    cure, so the hint would lead astray.
    """
    tools.v_edit(map="wh_faults_empty", tool="create")
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_what(strds=sampled, points="wh_faults_empty")

    text = message(error.value)
    assert (
        "No location was sampled: r.what returned no line. Check the locations." in text
    )
    assert "separator" not in text
    assert inventory(tools) == before


@pytest.mark.parametrize("layout", ["row", "col", "timerow"])
def test_coordinates_keep_input_precision(tools, sampled, layout):
    """The coordinates are written as given, 12 decimals stay and none are added"""
    result = tools.t_rast_what(
        strds=sampled, coordinates=f"{X},{Y}", layout=layout, flags="n"
    )

    lines = result.stdout.splitlines()
    if layout == "row":
        assert lines == [
            "x|y|start|end|value",
            *(
                f"{X}|{Y}|{start}|{end}|{value}"
                for (start, end), value in zip(TIMES, (11, 111, 211), strict=True)
            ),
        ]
    elif layout == "col":
        assert lines[0] == f"start|end|{X},{Y}"
    else:
        assert lines[1] == f"{X}|{Y}|11|111|211"


def test_site_coordinates_keep_input_precision(tools, sampled):
    result = tools.t_rast_what(
        strds=sampled, flags="i", stdin=StringIO(f"{X} {Y} site1\n")
    )

    assert (
        result.stdout.splitlines()[0] == f"{X}|{Y}|site1|{TIMES[0][0]}|{TIMES[0][1]}|11"
    )
