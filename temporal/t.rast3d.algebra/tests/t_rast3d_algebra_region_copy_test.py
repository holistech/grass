"""A copy of a map that comes out empty because of the current region

r3.mapcalc computes a map in the current 3D region. A map that the algebra
copies unchanged, such as a map that a selection stamps with a new time,
comes out empty when its box lies outside the region, and an empty map is
not registered unless -n is given. Unlike r.mapcalc, r3.mapcalc has no option
to compute in the union of the regions of its inputs, so this holds with -s
as well (measured 24.10.2026 with a selection under -s on the earlier
implementation, the classic profile and the core). Decision of 24.10.2026:
the results stay as they are, the core and the classic profile warn and name
each such copy.

The maps are single voxels of 10 by 10 by 10 units, of the height 0..10.
Boxes (x range, y range) and times (2001-01-DD):

=====  =====  ==================  ===========
map    value  box                 time
=====  =====  ==================  ===========
a1     1      0..10, 0..10        01.-02.01.
a2     2      100..110, 0..10     01.-02.01.
a3     3      0..10, 100..110     01.-02.01.
a4     4      10..20, 0..10       01.-02.01.
b1     11     0..10, 0..10        02.-03.01.
w1     21     0..20, 0..10        02.-03.01.
z1     null   0..10, 0..10        01.-02.01.
=====  =====  ==================  ===========

A holds a1 to a3, B holds b1, Z holds z1 and P holds a2. Every map of A, Z
and P precedes b1, so "X {:,precedes,r} B" copies each of them with the time
of b1, 02.-03.01., and "X {:,precedes} B" with its own time; one copy per map
in the core and in the classic profile alike, as B has one map.

Q holds a1 and a4, W holds w1. The box of w1 contains those of a1 and a4,
so both are related to w1 in space as well, and "Q {:,precedes,r} W" under
-s copies both with the time of w1.
"""

import re
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, day, make_map, register_stds
from grass.temporal.testing.readback import list_maps, message
from grass.tools import Tools

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = pytest.mark.fixed_algebra

# name: (value, west, east, south, north, first day, last day)
MAPS = {
    "a1": (1, 0, 10, 0, 10, 1, 2),
    "a2": (2, 100, 110, 0, 10, 1, 2),
    "a3": (3, 0, 10, 100, 110, 1, 2),
    "a4": (4, 10, 20, 0, 10, 1, 2),
    "b1": (11, 0, 10, 0, 10, 2, 3),
    "w1": (21, 0, 20, 0, 10, 2, 3),
    "z1": ("null()", 0, 10, 0, 10, 1, 2),
}
DATASETS = {
    "A": ["a1", "a2", "a3"],
    "B": ["b1"],
    "Z": ["z1"],
    "P": ["a2"],
    "Q": ["a1", "a4"],
    "W": ["w1"],
}
FLAGS = {"core": "", "classic": "c"}
WARNING = re.compile(
    r"Map <(\S+)> is empty in the current region and is not registered; it "
    r"copies <(\S+)>, which has data outside the region\. Set the region with "
    r"g\.region, or register empty maps with -n where the tool offers it\."
)


@pytest.fixture(scope="module")
def maps(xy_module_session):
    """Tools in a session with the maps and datasets of the table above, and
    the mapset of the session"""
    tools = Tools(
        session=xy_module_session, consistent_return_value=True, capture_stderr=True
    )
    for name, (value, west, east, south, north, *_) in MAPS.items():
        region = {"n": north, "s": south, "e": east, "w": west}
        region.update(t=10, b=0, res=10, res3=10)
        make_map(tools, "raster_3d", name, value, region=region)
    for stds, names in DATASETS.items():
        specs = [
            MapSpec(name, None, day(MAPS[name][5] - 1), day(MAPS[name][6] - 1))
            for name in names
        ]
        register_stds(tools, "str3ds", stds, specs)
    return SimpleNamespace(tools=tools, mapset=tools.g_gisenv(get="MAPSET").text)


def run(tools, name, expression, runner, *, flags=""):
    """Run t.rast3d.algebra; return its messages and the (value, start, end) of
    the registered maps, sorted, with -1 for a map without data"""
    result = tools.t_rast3d_algebra(
        expression=f"{name} = {expression}",
        basename=name.lower(),
        flags=FLAGS[runner] + flags,
    )
    rows = list_maps(tools, "str3ds", name)
    registered = sorted(
        (-1 if row.min is None else row.min, row.start[:10], row.end[:10])
        for row in rows
    )
    return message(result), registered


@pytest.mark.parametrize("runner", ["core", "classic"])
@pytest.mark.parametrize(
    ("label", "expression", "start", "end"),
    [
        # The selection stamps each copy with the time of b1.
        ("new", "A {:,precedes,r} B", "2001-01-02", "2001-01-03"),
        # Each copy keeps the time of its map, but is still a copy.
        ("own", "A {:,precedes} B", "2001-01-01", "2001-01-02"),
    ],
)
def test_a_copy_outside_the_region_is_reported(
    maps, runner, label, expression, start, end
):
    # The region covers the box of a1 only. The copy of a1 holds 1; those of
    # a2 and a3 lie outside the region, come out without data and are not
    # registered. That is what the earlier implementation, the classic
    # profile and the core registered before the warning existed (measured
    # 24.10.2026 with the maps of the spatial touch tests and a region over
    # their a1: only the copy of a1).
    maps.tools.g_region(w=0, e=10, s=0, n=10, res=10, res3=10, t=10, b=0)
    name = f"OUT_{label}_{runner}"
    text, registered = run(maps.tools, name, expression, runner)
    assert registered == [(1, start, end)]
    reported = {source: copy for copy, source in WARNING.findall(text)}
    assert set(reported) == {f"a2@{maps.mapset}", f"a3@{maps.mapset}"}
    assert len(WARNING.findall(text)) == 2
    for copy in reported.values():
        copy_name, _, mapset = copy.partition("@")
        assert copy_name.startswith(f"{name.lower()}_")
        assert mapset == maps.mapset
        assert not maps.tools.g_list(type="raster_3d", pattern=copy_name).stdout.split()


@pytest.mark.parametrize("runner", ["core", "classic"])
def test_a_copy_outside_the_region_is_reported_under_s(maps, runner):
    # r3.mapcalc has no union of regions, so under -s the copy of a4 is made
    # in the region over a1 as well, has no data and is dropped.
    maps.tools.g_region(w=0, e=10, s=0, n=10, res=10, res3=10, t=10, b=0)
    name = f"SPATIAL_{runner}"
    text, registered = run(maps.tools, name, "Q {:,precedes,r} W", runner, flags="s")
    assert registered == [(1, "2001-01-02", "2001-01-03")]
    reported = WARNING.findall(text)
    assert [source for _, source in reported] == [f"a4@{maps.mapset}"]
    assert reported[0][0].startswith(f"{name.lower()}_")


@pytest.mark.parametrize("runner", ["core", "classic"])
def test_a_copy_inside_the_region_is_not_reported(maps, runner):
    maps.tools.g_region(w=0, e=110, s=0, n=110, res=10, res3=10, t=10, b=0)
    text, registered = run(maps.tools, f"IN_{runner}", "A {:,precedes,r} B", runner)
    assert registered == [
        (1, "2001-01-02", "2001-01-03"),
        (2, "2001-01-02", "2001-01-03"),
        (3, "2001-01-02", "2001-01-03"),
    ]
    assert "is empty in the current region" not in text


@pytest.mark.parametrize("runner", ["core", "classic"])
def test_a_kept_empty_copy_is_not_reported(maps, runner):
    # With -n the copies of a2 and a3 are registered without data.
    maps.tools.g_region(w=0, e=10, s=0, n=10, res=10, res3=10, t=10, b=0)
    text, registered = run(
        maps.tools, f"KEPT_{runner}", "A {:,precedes,r} B", runner, flags="n"
    )
    assert registered == [
        (-1, "2001-01-02", "2001-01-03"),
        (-1, "2001-01-02", "2001-01-03"),
        (1, "2001-01-02", "2001-01-03"),
    ]
    assert "is empty in the current region" not in text


@pytest.mark.parametrize("runner", ["core", "classic"])
def test_a_copy_of_an_empty_map_is_not_reported(maps, runner):
    # z1 lies in the region but has no data, so its copy has none either and
    # is dropped; the region is not the cause.
    maps.tools.g_region(w=0, e=110, s=0, n=110, res=10, res3=10, t=10, b=0)
    text, registered = run(maps.tools, f"NULL_{runner}", "Z {:,precedes,r} B", runner)
    assert registered == []
    assert "Empty result space time dataset" in text
    assert "is empty in the current region" not in text


@pytest.mark.parametrize("runner", ["core", "classic"])
def test_a_map_partly_inside_the_region_is_not_reported(maps, runner):
    # The region covers the western half of the box of a2 in voxels of 5
    # units, which r3.mapcalc fills with the value 2 of a2.
    maps.tools.g_region(w=100, e=105, s=0, n=10, res=5, res3=5, t=10, b=0)
    text, registered = run(maps.tools, f"PART_{runner}", "P {:,precedes,r} B", runner)
    assert registered == [(2, "2001-01-02", "2001-01-03")]
    assert "is empty in the current region" not in text
