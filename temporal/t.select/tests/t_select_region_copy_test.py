"""A selection that stamps a new time copies maps whatever the region

t.rast.algebra and t.rast3d.algebra copy such a map with r.mapcalc or
r3.mapcalc in the current region, so a map outside the region comes out
empty and is dropped with a warning. t.select copies it with g.copy, which
takes the whole map regardless of the region. This test holds that: the
copies keep their data and no warning about the region appears.

The maps are single cells of 10 by 10 units. Boxes (x range, y range) and
times (2001-01-DD):

=====  =====  ==================  ===========
map    value  box                 time
=====  =====  ==================  ===========
a1     1      0..10, 0..10        01.-02.01.
a2     2      100..110, 0..10     01.-02.01.
a3     3      0..10, 100..110     01.-02.01.
b1     11     0..10, 0..10        02.-03.01.
=====  =====  ==================  ===========

A holds a1 to a3, B holds b1. Every map of A precedes b1, so
"A {:,precedes,r} B" copies each of them with the time of b1, 02.-03.01., one
copy per map in the core and in the classic profile alike, as B has one map.
Because conftest.py already makes the datasets A and B and the maps a1 to b9,
the datasets here are called RA and RB and the maps ra1 to rb1.
"""

import pytest

from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.temporal.testing.readback import list_maps, message
from grass.tools import Tools

# name: (value, west, east, south, north, first day, last day)
MAPS = {
    "ra1": (1, 0, 10, 0, 10, 1, 2),
    "ra2": (2, 100, 110, 0, 10, 1, 2),
    "ra3": (3, 0, 10, 100, 110, 1, 2),
    "rb1": (11, 0, 10, 0, 10, 2, 3),
}
DATASETS = {"RA": ["ra1", "ra2", "ra3"], "RB": ["rb1"]}


@pytest.fixture(scope="module")
def copies(series):
    """The session of series with the maps and datasets of the table above"""
    tools = Tools(session=series.session)
    for name, (value, west, east, south, north, *_) in MAPS.items():
        region = {"n": north, "s": south, "e": east, "w": west, "res": 10}
        make_map(tools, "raster", name, value, region=region)
    for stds, names in DATASETS.items():
        specs = [
            MapSpec(name, None, day(MAPS[name][5] - 1), day(MAPS[name][6] - 1))
            for name in names
        ]
        register_stds(tools, "strds", stds, specs)
    return series.session


def test_a_copy_outside_the_region_keeps_its_data(copies, algebra):
    # The region covers the box of ra1 only; g.copy copies ra2 and ra3 all
    # the same, with their values.
    tools = Tools(session=copies, consistent_return_value=True, capture_stderr=True)
    tools.g_region(w=0, e=10, s=0, n=10, res=10)
    name = f"OUT_{algebra}"
    result = tools.t_select(expression=f"{name} = RA {{:,precedes,r}} RB")
    registered = sorted(
        (row.min, row.start[:10], row.end[:10])
        for row in list_maps(tools, "strds", name)
    )
    assert registered == [
        (1, "2001-01-02", "2001-01-03"),
        (2, "2001-01-02", "2001-01-03"),
        (3, "2001-01-02", "2001-01-03"),
    ]
    assert "is empty in the current region" not in message(result)
