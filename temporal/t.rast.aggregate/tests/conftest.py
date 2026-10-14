"""Fixtures for the characterization tests of t.rast.aggregate

The datasets are built once per module with library registration, as the
t.rast.algebra fixtures do, which is several times faster than one tool call
per map.
"""

import os
from types import SimpleNamespace
from typing import NamedTuple

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.tools import Tools


class Row(NamedTuple):
    """A registered map of a result dataset, read back with t.rast.list"""

    name: str
    start: str
    end: str
    min: float | None
    max: float | None


class Reader:
    """Run t.rast.aggregate and read its result back"""

    def __init__(self, session):
        self.tools = Tools(session=session, overwrite=True)
        self.capturing = Tools(
            session=session,
            overwrite=True,
            capture_stderr=True,
            consistent_return_value=True,
        )

    def messages(self, output, **options):
        """The standard error output of one t.rast.aggregate run"""
        result = self.capturing.t_rast_aggregate(
            output=output, basename=output, **options
        )
        return result.stderr

    def aggregate(self, output, **options):
        self.tools.t_rast_aggregate(output=output, basename=output, **options)
        return self.rows(output)

    def rows(self, dataset):
        text = self.tools.t_rast_list(
            input=dataset,
            columns="name,start_time,end_time,min,max",
            separator="pipe",
            flags="u",
        ).text.strip()
        rows = []
        for line in text.splitlines():
            name, start, end, low, high = line.split("|")
            rows.append(
                Row(
                    name,
                    start,
                    end,
                    None if low == "None" else float(low),
                    None if high == "None" else float(high),
                )
            )
        return rows

    def datatype(self, raster):
        return self.tools.r_info(map=raster, flags="g").keyval["datatype"]

    def first_color(self, raster):
        return self.tools.r_colors_out(map=raster).text.strip().splitlines()[0]


def _register(dataset, temporaltype, rows, unit=None):
    """Create a STRDS and register maps from (name, start, end) rows"""
    tgis.open_new_stds(
        dataset, "strds", temporaltype, dataset, dataset, "mean", overwrite=True
    )
    for name, start, end in rows:
        kwargs = {"start": start} if end is None else {"start": start, "end": end}
        if unit is not None:
            kwargs["unit"] = unit
        tgis.register_maps_in_space_time_dataset("raster", dataset, name, **kwargs)


@pytest.fixture(scope="module")
def aggregate_data(tmp_path_factory):
    """Session with the datasets of the characterization tests

    - cells: CELL maps m1=1, m2=3, m3=5 on 12 hour intervals of days 1, 2, 3
      of January 2001; m1 has a grey color table. One map per day for the
      g.copy case, two maps in a two day granule for the r.series case.
    - nulls: na1=1, na2=2 on days 1 and 2, nz1 and nz2 null on day 3, so that
      a daily granule of day 3 aggregates to an all null map.
    - instants: ip1=1, ip2=2, ip3=3 as time instants on days 1, 2, 3.
    - relative: rx1..rx4 = 1..4 as relative day intervals [0,1]..[3,4].
    - ordering: oz=3 over [day 1, day 30], oa1=5 over [day 3, day 15], oa2=1
      over [day 4, day 15] and oa3=9 over [day 6, day 7]; oz fixes the grid
      start at day 1 without being related to the first granule.
    - tail: tl_long=7 over [day 1, day 30] and the instant tl_inst=2 on day 3.
    - probes: p-maps whose value is the probe number, with the time spans of
      the algebra PROBES, for the sampling list.
    """
    project = tmp_path_factory.mktemp("t_rast_aggregate") / "project"
    gs.create_project(project)
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as session,
    ):
        for key, value in session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tgis.init()
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=3, s=0, e=3, w=0, res=1)
        for name, value in [
            ("m1", 1), ("m2", 3), ("m3", 5),
            ("na1", 1), ("na2", 2), ("nz1", "null()"), ("nz2", "null()"),
            ("ip1", 1), ("ip2", 2), ("ip3", 3),
            ("rx1", 1), ("rx2", 2), ("rx3", 3), ("rx4", 4),
            ("oz", 3), ("oa1", 5), ("oa2", 1), ("oa3", 9),
            ("tl_long", 7), ("tl_inst", 2),
        ]:  # fmt: skip
            tools.r_mapcalc(expression=f"{name} = {value}")
        tools.r_colors(map="m1", color="grey")
        probes = {
            3: (5, 25),
            5: (10, 25),
            7: (5, 20),
            10: (5, 15),
            11: (15, 25),
            1: (10, 20),
            2: (12, 18),
        }
        for value in probes:
            tools.r_mapcalc(expression=f"p{value} = {value}")

        _register(
            "cells",
            "absolute",
            [
                ("m1", "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("m2", "2001-01-02 06:00:00", "2001-01-02 18:00:00"),
                ("m3", "2001-01-03 06:00:00", "2001-01-03 18:00:00"),
            ],
        )
        _register(
            "nulls",
            "absolute",
            [
                ("na1", "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("na2", "2001-01-02 06:00:00", "2001-01-02 18:00:00"),
                ("nz1", "2001-01-03 06:00:00", "2001-01-03 12:00:00"),
                ("nz2", "2001-01-03 13:00:00", "2001-01-03 18:00:00"),
            ],
        )
        _register(
            "instants",
            "absolute",
            [
                ("ip1", "2001-01-01", None),
                ("ip2", "2001-01-02", None),
                ("ip3", "2001-01-03", None),
            ],
        )
        _register(
            "relative",
            "relative",
            [("rx1", 0, 1), ("rx2", 1, 2), ("rx3", 2, 3), ("rx4", 3, 4)],
            unit="days",
        )
        _register(
            "ordering",
            "absolute",
            [
                ("oz", "2001-01-01", "2001-01-30"),
                ("oa1", "2001-01-03", "2001-01-15"),
                ("oa2", "2001-01-04", "2001-01-15"),
                ("oa3", "2001-01-06", "2001-01-07"),
            ],
        )
        _register(
            "tail",
            "absolute",
            [("tl_long", "2001-01-01", "2001-01-30"), ("tl_inst", "2001-01-03", None)],
        )
        _register(
            "probes",
            "absolute",
            [
                (f"p{v}", f"2001-01-{a:02d}", f"2001-01-{b:02d}")
                for v, (a, b) in probes.items()
            ],
        )
        yield SimpleNamespace(session=session, read=Reader(session))
