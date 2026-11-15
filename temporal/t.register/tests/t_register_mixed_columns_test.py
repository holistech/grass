"""Test t.register file= with lines that have different numbers of columns

Each map gets the time of its own line; the start and increment options apply
to the lines that carry no time of their own.
"""

import pytest

from grass.temporal.testing.data import register_file
from grass.temporal.testing.readback import list_maps

pytestmark = pytest.mark.slow


def _times(tools, name):
    return {row.name: (row.start, row.end) for row in list_maps(tools, "strds", name)}


@pytest.mark.parametrize("last", ["with_time", "name_only"])
def test_every_map_gets_the_time_of_its_line(tools, make_maps, dataset, tmp_path, last):
    first, second, third = make_maps(3)
    name = dataset()
    rows = [(first, "2001-01-01"), second, (third, "2001-01-05", "2001-01-06")]
    if last == "name_only":
        rows = [(first, "2001-01-01"), (third, "2001-01-05", "2001-01-06"), second]
    file = register_file(tmp_path / "maps.txt", rows)

    tools.t_register(
        type="raster",
        input=name,
        file=file,
        start="2001-03-01",
        increment="1 days",
    )

    # The line without a time takes the start of the command line, counted
    # up by its place in the file; the others keep their own times.
    place = 1 if last == "with_time" else 2
    assert _times(tools, name) == {
        first: ("2001-01-01 00:00:00", None),
        second: (f"2001-03-0{1 + place} 00:00:00", None),
        third: ("2001-01-05 00:00:00", "2001-01-06 00:00:00"),
    }
