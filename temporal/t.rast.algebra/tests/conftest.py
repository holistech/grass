"""Fixtures for t.rast.algebra tests"""

import datetime
import os
from types import SimpleNamespace
from typing import NamedTuple

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal.temporal_algebra import FatalError as TemporalAlgebraFatalError
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
def time_series(tmp_path_factory):
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
    project = tmp_path_factory.mktemp("t_rast_algebra") / "project"
    gs.create_project(project)

    with gs.setup.init(project, env=os.environ.copy()) as session:
        tools = Tools(session=session)
        tools.g_region(n=3, s=0, e=3, w=0, res=1)
        for name, value in [("m1", 1), ("m2", 2), ("m3", 3), ("i1", 1), ("i2", 2)]:
            tools.r_mapcalc(expression=f"{name} = {value}")
        tools.r_mapcalc(expression="r1 = 1")

        for output, temporaltype in [
            ("intervals", "absolute"),
            ("instants", "absolute"),
            ("relative", "relative"),
        ]:
            tools.t_create(
                output=output,
                type="strds",
                temporaltype=temporaltype,
                title=output,
                description=output,
            )

        intervals_file = tmp_path_factory.mktemp("register") / "intervals.txt"
        intervals_file.write_text(
            "m1|2001-01-01 06:00:00|2001-02-01 06:00:00\n"
            "m2|2001-02-01 15:00:00|2001-03-01 15:00:00\n"
            "m3|2001-03-01 23:00:00|2001-04-01 23:00:00\n"
        )
        tools.t_register(input="intervals", file=intervals_file)
        tools.t_register(input="instants", maps="i1", start="2001-01-10")
        tools.t_register(input="instants", maps="i2", start="2001-03-15")
        tools.t_register(
            input="relative", maps="r1", start=0, increment=1, unit="days", flags="i"
        )

        yield SimpleNamespace(session=session)


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

    def create(name, temporaltype="absolute"):
        tgis.open_new_stds(
            name, "strds", temporaltype, name, name, "mean", overwrite=True
        )

    def register(dataset, maps, first_day, step=1):
        """Register maps as consecutive intervals of step days"""
        tgis.register_maps_in_space_time_dataset(
            "raster",
            dataset,
            maps,
            start=f"2001-01-{first_day:02d}",
            increment=f"{step} days",
            interval=True,
        )

    for name in [
        "A",
        "B",
        "C",
        "D",
        "G",
        "GR",
        "E",
        "I",
        "N",
        "ref",
        "rel",
        "HA",
        "HB",
    ]:
        create(name)
    create("RT", "relative")

    register("A", "a1,a2,a3,a4", 1)
    register("N", "n1,n2,n3,n4", 1)
    register("B", "b1,b2", 1, step=2)
    register("C", "c1", 2, step=2)
    register("D", "d1,d2,d3", 3)
    register("G", "g1,g2", 1)
    register("GR", "gr1", 1)
    register("HA", ",".join(f"ha{n}" for n in range(1, 7)), 1)
    register("HB", "hb1,hb2", 2, step=2)
    for number, name in enumerate(["i1", "i2", "i3"], start=1):
        tgis.register_maps_in_space_time_dataset(
            "raster", "I", name, start=f"2001-01-{number:02d}"
        )
    tgis.register_maps_in_space_time_dataset(
        "raster", "E", "e1,e2,e3,e4", start="2001-01-01"
    )
    for name in ["T", "PA", "PB", "PC"]:
        create(name)
    lines = {"T": [], "PA": [], "PB": [], "PC": []}
    for number in range(8):
        start = datetime.datetime(
            2001, 1 + (number >> 2 & 1), 1 + (number >> 1 & 1), 12 * (number & 1)
        )
        end = start + datetime.timedelta(hours=1)
        for dataset, prefix in [("T", "pt"), ("PA", "pa"), ("PB", "pb"), ("PC", "pc")]:
            lines[dataset].append(f"{prefix}{number}|{start}|{end}\n")
    for dataset, rows in lines.items():
        register_file = directory / f"{dataset}.txt"
        register_file.write_text("".join(rows))
        tgis.register_maps_in_space_time_dataset(
            "raster", dataset, file=str(register_file)
        )
    tgis.register_maps_in_space_time_dataset(
        "raster", "ref", "ref1", start="2001-01-10", end="2001-01-20"
    )
    for value, (first, last) in PROBES.items():
        tgis.register_maps_in_space_time_dataset(
            "raster",
            "rel",
            f"p{value}",
            start=f"2001-01-{first:02d}",
            end=f"2001-01-{last:02d}",
        )
    tgis.register_maps_in_space_time_dataset(
        "raster", "RT", "x1,x2,x3", start=0, increment=1, unit="days", interval=True
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
    create("SA")
    create("SB")
    tgis.register_maps_in_space_time_dataset(
        "raster", "SA", "spa1,spa2,spa3,spa4", start="2001-01-01"
    )
    tgis.register_maps_in_space_time_dataset(
        "raster", "SB", "spb1,spb2,spb3,spb4", start="2001-01-01"
    )


class Algebra:
    """Run the temporal raster algebra in the test session"""

    # The algebra raises its own FatalError, other library code the one of
    # grass.exceptions.
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

    def parse(self, expression, basename="r", **kwargs):
        """Run "R = <expression>" in-process without reading the result back"""
        self.remove("R")
        parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False, **kwargs)
        return parser.parse(f"R = {expression}", basename, True)

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


@pytest.fixture(scope="module")
def algebra(tmp_path_factory):
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
    project = tmp_path_factory.mktemp("algebra") / "project"
    gs.create_project(project)

    # tgis reads the session from os.environ; see the comment in
    # python/grass/temporal/tests/grass_temporal_gui_support_test.py.
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        previous = tgis.get_raise_on_error()
        tgis.init(True)
        # The messenger is created once per process with the mode of the first
        # init(); other test modules may have set it to exit on fatal errors.
        tgis.set_raise_on_error(True)
        try:
            _create_datasets(Tools(session=session), tmp_path_factory.mktemp("maps"))
            fixture = Algebra(session)
            fixture.tools = Tools(session=session, overwrite=True)
            yield fixture
        finally:
            tgis.set_raise_on_error(previous)


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
