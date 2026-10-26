"""Test that t.register stores time stamps in whole seconds

The temporal database has the resolution of one second. A start time with a
fraction of a second is cut to the second, not rounded, and read back as such.
"""

import pytest

from grass.temporal.testing.readback import list_maps


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ("2001-01-01 10:00:00.5", "2001-01-01 10:00:00"),
        ("2001-01-01 10:00:00.999999", "2001-01-01 10:00:00"),
        ("2001-01-01 10:00:00.000001", "2001-01-01 10:00:00"),
    ],
)
def test_a_fraction_of_a_second_is_cut(
    tools, prefix, make_maps, dataset, start, expected
):
    name = dataset()
    (raster,) = make_maps(1)

    tools.t_register(type="raster", input=name, maps=raster, start=start)

    assert [row.start for row in list_maps(tools, "strds", name)] == [expected]
