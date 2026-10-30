"""Fixtures for t.rast.algebra tests"""

import datetime
from types import SimpleNamespace
from typing import NamedTuple

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.exceptions import FatalError as TemporalAlgebraFatalError
from grass.temporal.testing import io_cache
from grass.temporal.testing.data import MapSpec, create_stds, day, register_stds
from grass.tools import Tools

# Probe maps of the "rel" dataset: (value, first day, last day) in January 2001.
# The reference map "ref1" covers days 10 to 20. The value identifies the
# temporal relation of the probe to the reference.
PROBES = {
    1: (10, 20),  # equal
    2: (12, 18),  # during
    3: (5, 25),  # contains
    4: (10, 15),  # starts
    5: (10, 25),  # started
    6: (15, 20),  # finishes
    7: (5, 20),  # finished
    8: (5, 10),  # precedes (adjacent)
    9: (20, 25),  # follows (adjacent)
    10: (5, 15),  # overlaps
    11: (15, 25),  # overlapped
    12: (1, 3),  # before with a gap
    13: (27, 30),  # after with a gap
}


class Row(NamedTuple):
    """A map of a result dataset"""

    start: datetime.datetime
    end: datetime.datetime | None
    min: float | None
    max: float | None


@pytest.fixture(scope="module")
def time_series(xy_module_session):
    """Session with three raster time series of different temporal types.

    - "intervals": absolute time intervals whose start and end times have
      different hours of the day; the map value is the map number:

      ===  ===================  ===================
      map  start                end
      ===  ===================  ===================
      1    2001-01-01 06:00:00  2001-02-01 06:00:00
      2    2001-02-01 15:00:00  2001-03-01 15:00:00
      3    2001-03-01 23:00:00  2001-04-01 23:00:00
      ===  ===================  ===================

    - "instants": absolute time instances (no end time) on 2001-01-10
      (value 1) and 2001-03-15 (value 2)
    - "relative": relative time intervals of one day
    """
    tools = Tools(session=xy_module_session)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "intervals",
        [
            MapSpec(
                "m1",
                1,
                datetime.datetime(2001, 1, 1, 6),
                datetime.datetime(2001, 2, 1, 6),
            ),
            MapSpec(
                "m2",
                2,
                datetime.datetime(2001, 2, 1, 15),
                datetime.datetime(2001, 3, 1, 15),
            ),
            MapSpec(
                "m3",
                3,
                datetime.datetime(2001, 3, 1, 23),
                datetime.datetime(2001, 4, 1, 23),
            ),
        ],
    )
    create_stds(
        tools,
        "strds",
        "instants",
        [
            MapSpec("i1", 1, datetime.datetime(2001, 1, 10)),
            MapSpec("i2", 2, datetime.datetime(2001, 3, 15)),
        ],
    )
    create_stds(
        tools,
        "strds",
        "relative",
        [MapSpec("r1", 1, 0, 1)],
        temporaltype="relative",
        unit="days",
    )
    return SimpleNamespace(session=xy_module_session)


def _create_datasets(tools, directory):
    """Create the maps and datasets described in the algebra fixture

    Library calls and one r.mapcalc file are used instead of one tool call
    per map, which makes the setup several times faster.
    """
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    values = {
        "a1": 1, "a2": 2, "a3": 3, "a4": 4, "b1": 5, "b2": 6, "c1": 7,
        "d1": 8, "d2": 9, "d3": 10, "singletmap": 99, "sinst": 100, "singlemap": 100,
        "e1": 1, "e2": 2, "e3": 3, "e4": 4, "i1": 1, "i2": 2, "i3": 3,
        "x1": 1, "x2": 2, "x3": 3, "ref1": 100, "hb1": 7, "hb2": 8,
        "g1": "col()", "g2": "col() * 10", "gr1": "row()", "n1": 11, "n2": 12, "n3": 13, "n4": 14,
    }  # fmt: skip
    values.update({f"p{value}": value for value in PROBES})
    values.update({f"ha{number}": number for number in range(1, 7)})
    # Truth table series, map k = 4a + 2b + c: T has the value k, PA, PB and
    # PC the bits a, b and c. The time stamp encodes the bits as well, so that
    # temporal conditions can test them: month 1 + a, day 1 + b, hour 12 * c.
    for number in range(8):
        values[f"pt{number}"] = number
        values[f"pa{number}"] = number >> 2 & 1
        values[f"pb{number}"] = number >> 1 & 1
        values[f"pc{number}"] = number & 1
    script = directory / "maps.txt"
    script.write_text("".join(f"{name} = {value}\n" for name, value in values.items()))
    tools.r_mapcalc(file=script)

    def register(dataset, names, first_day, step=1, *, instants=False):
        """Register maps as consecutive intervals of step days, or as instants

        Instants all lie on first_day; the intervals start there and follow
        each other.
        """
        specs = []
        for number, name in enumerate(names):
            if instants:
                start, end = day(first_day - 1), None
            else:
                start = day(first_day - 1 + number * step)
                end = day(first_day - 1 + (number + 1) * step)
            specs.append(MapSpec(name, values[name], start, end))
        register_stds(tools, "strds", dataset, specs, via="library")

    register("A", ["a1", "a2", "a3", "a4"], 1)
    register("N", ["n1", "n2", "n3", "n4"], 1)
    register("B", ["b1", "b2"], 1, step=2)
    register("C", ["c1"], 2, step=2)
    register("D", ["d1", "d2", "d3"], 3)
    register("G", ["g1", "g2"], 1)
    register("GR", ["gr1"], 1)
    register("HA", [f"ha{n}" for n in range(1, 7)], 1)
    register("HB", ["hb1", "hb2"], 2, step=2)
    # I holds one instant per day, E four instants on one day.
    register_stds(
        tools,
        "strds",
        "I",
        [MapSpec(f"i{n}", n, day(n - 1)) for n in (1, 2, 3)],
        via="library",
    )
    register("E", ["e1", "e2", "e3", "e4"], 1, instants=True)
    for dataset, prefix in [("T", "pt"), ("PA", "pa"), ("PB", "pb"), ("PC", "pc")]:
        specs = []
        for number in range(8):
            start = datetime.datetime(
                2001, 1 + (number >> 2 & 1), 1 + (number >> 1 & 1), 12 * (number & 1)
            )
            specs.append(
                MapSpec(
                    f"{prefix}{number}",
                    values[f"{prefix}{number}"],
                    start,
                    start + datetime.timedelta(hours=1),
                )
            )
        register_stds(tools, "strds", dataset, specs, via="library")
    register_stds(
        tools, "strds", "ref", [MapSpec("ref1", 100, day(9), day(19))], via="library"
    )
    register_stds(
        tools,
        "strds",
        "rel",
        [
            MapSpec(f"p{value}", value, day(first - 1), day(last - 1))
            for value, (first, last) in PROBES.items()
        ],
        via="library",
    )
    register_stds(
        tools,
        "strds",
        "RT",
        [MapSpec(f"x{n}", n, n - 1, n) for n in (1, 2, 3)],
        temporaltype="relative",
        unit="days",
        via="library",
    )
    tgis.register_maps_in_space_time_dataset(
        "raster", None, "singletmap", start="2001-01-03", end="2001-01-04"
    )
    tgis.register_maps_in_space_time_dataset(
        "raster", None, "sinst", start="2001-01-01"
    )

    # Spatial dataset pairs with identical time stamps. The map extents are
    # chosen so that the spatial relation of the pair members is known:
    # spa<i> and spb<i> are spatially equal, spa2 contains spb3.
    extents = {1: (0, 30), 2: (20, 50), 3: (25, 40), 4: (40, 60)}
    for number, (low, high) in extents.items():
        tools.g_region(n=high, s=low, e=high, w=low, res=10)
        tools.r_mapcalc(expression=f"spa{number} = {number}")
        tools.r_mapcalc(expression=f"spb{number} = {number}")
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    for dataset, prefix in [("SA", "spa"), ("SB", "spb")]:
        register_stds(
            tools,
            "strds",
            dataset,
            [MapSpec(f"{prefix}{n}", n, day(0)) for n in extents],
            via="library",
        )


# Datasets of the figures and examples in Gebbert, Leppelt and Pebesma
# (2019), Data 4(2), 86, rebuilt with constant 3x3 maps in January 2001:
# name: (times, values), a time is an interval (first day, end day) or the
# day of an instant.
PAPER_DAILY = [(day, day + 1) for day in range(1, 11)]
PAPER = {
    "A1A": ([(1, 3), (3, 5), (5, 7), (7, 11)], [10, 20, 30, 40]),
    "A1B": (PAPER_DAILY, list(range(1, 11))),
    "A3A": ([(1, 3), (3, 5), (5, 7)], [10, 20, 30]),
    "A4A": ([(1, 3), (3, 5), (5, 7), (7, 11)], [-1, 0, 1, 2]),
    "A5A": ([(1, 6), (6, 11)], [1, 1]),
    "A5B": (PAPER_DAILY, [1] * 10),
    "A7A": ([(4, 8)], [1]),
    "A7B": ([(1, 4), (8, 11)], [1, 1]),
    "A8A": ([(4, 9)], [1]),
    "A8B": ([(1, 6)], [1]),
    "SA9A": ([1, 1, 8, 8], [1, 3, 2, 4]),
    "SA9B": ([1, 1, 8, 8], [1, 3, 2, 4]),
    "S2B08": ([1, 1, 8, 8], [0.8, 0.6, 0.7, 0.9]),
    "S2B04": ([1, 1, 8, 8], [0.2, 0.2, 0.3, 0.1]),
    "T": (PAPER_DAILY, [5, 15, 12, 8, 20, 11, 9, 14, 16, 7]),
    "P": (PAPER_DAILY, list(range(1, 11))),
    "D": ([(1, 11)], [0]),
    "NIR": ([(1, 2), (2, 3), (3, 4)], [0.5, 0.6, 0.7]),
    "RED": ([(1, 2), (2, 3), (3, 4)], [0.1, 0.2, 0.3]),
}
# The second and fourth map of these datasets lie east of the others, so
# that two maps of equal time are related by their extent only.
PAPER_EAST = ("SA9A", "SA9B", "S2B08", "S2B04")
PAPER_REGION = {"n": 3, "s": 0, "e": 3, "w": 0, "res": 1}
PAPER_EAST_REGION = {"n": 3, "s": 0, "e": 13, "w": 10, "res": 1}


def _create_paper_datasets(tools, directory):
    """Create the datasets of PAPER and the map L (0.5) without time stamp"""
    expressions = {True: [], False: ["L = 0.5\n"]}
    specs = {}
    for name, (times, values) in PAPER.items():
        specs[name] = []
        for number, (time, value) in enumerate(zip(times, values, strict=True), 1):
            map_name = f"{name.lower()}_{number}"
            east = name in PAPER_EAST and number % 2 == 0
            expressions[east].append(f"{map_name} = {value}\n")
            first, end = time if isinstance(time, tuple) else (time, None)
            specs[name].append(
                MapSpec(
                    map_name,
                    value,
                    day(first - 1),
                    None if end is None else day(end - 1),
                )
            )
    # The base region comes last, so that it is the region of the tests.
    for east, region in [(True, PAPER_EAST_REGION), (False, PAPER_REGION)]:
        tools.g_region(**region)
        script = directory / f"maps_{'east' if east else 'base'}.txt"
        script.write_text("".join(expressions[east]))
        tools.r_mapcalc(file=script)
    for name, maps in specs.items():
        register_stds(tools, "strds", name, maps, via="library")


class Algebra:
    """Run the temporal raster algebra in the test session"""

    # The classic algebra raises its own FatalError, other library code the
    # one of grass.exceptions. The core raises ValueError, TypeError or
    # SyntaxError instead, which tests name where they expect them.
    errors = (FatalError, TemporalAlgebraFatalError)

    def __init__(self, session):
        self.session = session

    def run(self, expression, basename="r", **kwargs):
        """Run "R = <expression>" in-process and return the maps of R

        The keyword arguments are passed to the TemporalRasterAlgebraParser
        (spatial, register_null, nprocs, ...). Using the library instead of
        the tool keeps the many expression tests fast; the tool itself is
        covered by the options tests.
        """
        self.parse(expression, basename, **kwargs)
        return self.maps("R")

    def parse(self, expression, basename="r", granularity=False, **kwargs):
        """Run "R = <expression>" in-process without reading the result back

        With granularity the datasets are first sampled with their common
        granularity, as t.rast.algebra -g does.
        """
        self.remove("R")
        kwargs.setdefault("debug", False)
        parser = tgis.TemporalRasterAlgebraParser(run=True, **kwargs)
        statement = f"R = {expression}"
        if granularity:
            assert parser.setup_common_granularity(
                expression=statement, lexer=tgis.TemporalRasterAlgebraLexer()
            )
        return parser.parse(statement, basename, True)

    def dry_times(self, expression, **kwargs):
        """Return the sorted (start, end) strings of the maps that "R =
        <expression>" would register, without computing any map

        Much faster than run(); use it to compare the time stamps of many
        expressions.
        """
        chain = self.parse(expression, dry_run=True, **kwargs)
        return sorted((start, end) for _name, start, end in chain["register"])

    @staticmethod
    def remove(name):
        """Remove a STRDS so that no result of an earlier run is left

        The raster maps stay; the next run overwrites them. Deleting them
        would cost one process per map.
        """
        dataset = tgis.SpaceTimeRasterDataset(f"{name}@PERMANENT")
        if dataset.is_in_db():
            dataset.delete()

    @staticmethod
    def day(number):
        """Return a day of January 2001 as datetime"""
        return datetime.datetime(2001, 1, number)

    def exists(self, name="R"):
        """Return True if the STRDS exists"""
        return tgis.SpaceTimeRasterDataset(f"{name}@PERMANENT").is_in_db()

    def maps(self, name="R"):
        """Return the maps of a STRDS as Rows sorted by time and value"""
        dataset = tgis.open_old_stds(name, "strds")
        rows = []
        for raster in dataset.get_registered_maps_as_objects(order="start_time"):
            raster.select()
            start, end = raster.get_temporal_extent_as_tuple()
            rows.append(
                Row(start, end, raster.metadata.get_min(), raster.metadata.get_max())
            )
        return sorted(
            rows, key=lambda row: (row.start, row.end or row.start, row.min or 0)
        )

    def triples(self, expression, **kwargs):
        """Run the algebra and return (start day, end day, value) per map

        Days are days of the month, the value is the (constant) cell value.
        Fails if a map is not constant. Use this for January 2001 data.
        """
        result = []
        for row in self.run(expression, **kwargs):
            assert row.min == row.max, f"map is not constant: {row}"
            result.append((row.start.day, row.end.day if row.end else None, row.min))
        return result

    def values(self, expression, **kwargs):
        """Run the algebra and return only the cell values, sorted by time"""
        return [value for _, _, value in self.triples(expression, **kwargs)]


def _algebra_runner(session, directory, create):
    """Return an Algebra runner on session with the maps of create()"""
    create(Tools(session=session), directory)
    runner = Algebra(session)
    runner.tools = Tools(session=session, overwrite=True)
    return runner


@pytest.fixture(scope="module")
def algebra(temporal_module_session, tmp_path_factory):
    """Algebra runner on a session with the datasets of the test series

    All maps are 3x3 constant rasters whose value is given below. The time
    stamps are days of January 2001; an interval is written [start, end].

    =======  ==========================================================
    dataset  maps (value)
    =======  ==========================================================
    A        a1..a4 (1..4), daily intervals [1,2] .. [4,5]
    N        n1..n4 (11..14), the same daily intervals as A
    B        b1 (5) [1,3], b2 (6) [3,5]
    C        c1 (7) [2,4]
    D        d1..d3 (8..10), daily intervals [3,4] .. [5,6]
    G        g1 = col(), g2 = col() * 10, daily intervals [1,2], [2,3]
    GR       gr1 = row(), interval [1,2]
    E        e1..e4 (1..4), four instants at day 1
    I        i1..i3 (1..3), instants at day 1, 2, 3
    RT       x1..x3 (1..3), relative intervals [0,1] .. [2,3] days
    ref      ref1 (100) [10,20]
    rel      p1..p13: value = probe number, see PROBES
    HA       ha1..ha6 (1..6), daily intervals [1,2] .. [6,7]
    HB       hb1 (7) [2,4], hb2 (8) [4,6]
    T        pt0..pt7 (0..7), map k = 4a + 2b + c is one hour long and starts
             in month 1 + a, on day 1 + b, at hour 12 * c of 2001
    PA,PB,PC pa0..7, pb0..7, pc0..7: the bits a, b, c of k, times as T
    SA, SB   spa1..4 / spb1..4 (value 1..4), instants at day 1 with
             the spatial extents described in _create_datasets
    =======  ==========================================================

    Single maps: singletmap (99) is time stamped [3,4] and sinst (100) is
    an instant at day 1, both in no dataset; singlemap (100) has no time stamp.
    """
    return _algebra_runner(
        temporal_module_session,
        tmp_path_factory.mktemp("algebra_maps"),
        _create_datasets,
    )


@pytest.fixture(scope="module")
def paper(temporal_module_session, tmp_path_factory):
    """Algebra runner on the datasets of PAPER and the map L (0.5)"""
    return _algebra_runner(
        temporal_module_session,
        tmp_path_factory.mktemp("paper_maps"),
        _create_paper_datasets,
    )


@pytest.fixture
def large_region(algebra):
    """Region that covers all the maps of the spatial datasets SA and SB

    Restores the region afterwards: a run with spatial=True leaves the region
    set to the extent of the maps it used (checked 2026-10-11), which would
    make the following runs of the module compute in the wrong region.
    """
    tools = Tools(session=algebra.session)
    original = tools.g_region(flags="g").keyval
    tools.g_region(n=60, s=0, e=60, w=0, res=10)
    yield
    tools.g_region(
        n=original["n"],
        s=original["s"],
        e=original["e"],
        w=original["w"],
        res=original["nsres"],
    )


@pytest.fixture(scope="module")
def io_cache_storage():
    """Answers of the test-only caches, shared by the tests of one module"""
    return io_cache.CacheStorage()


@pytest.fixture(autouse=True)
def cached_io(request, io_cache_storage):
    """Run the test with the caches of grass.temporal.testing.io_cache.cached_io"""
    if request.node.get_closest_marker("real_io"):
        yield
        return
    with io_cache.cached_io(io_cache_storage):
        yield
