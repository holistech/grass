"""Fixtures for the characterization tests of t.rast.aggregate.ds"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    intervals,
    register_stds,
)
from grass.temporal.testing.readback import list_maps
from grass.tools import Tools


class Reader:
    """Run t.rast.aggregate.ds and read its result back"""

    def __init__(self, session):
        self.tools = Tools(session=session, overwrite=True)
        self.refusing = Tools(
            session=session,
            overwrite=False,
            capture_stderr=True,
            consistent_return_value=True,
            errors="ignore",
        )

    def refused(self, output, **options):
        """The result of a run without overwrite, which may fail"""
        return self.refusing.t_rast_aggregate_ds(
            output=output, basename=output, **options
        )

    def aggregate(self, output, **options):
        self.tools.t_rast_aggregate_ds(output=output, basename=output, **options)
        return self.names(output)

    def rows_after(self, output, **options):
        self.tools.t_rast_aggregate_ds(output=output, basename=output, **options)
        return self.rows(output)

    def names(self, dataset):
        return [row.name for row in list_maps(self.tools, "strds", dataset)]

    def rows(self, dataset):
        """The maps as [name, start, end, min, max] text, None as "None"

        The tests compare the text that t.rast.list prints; list_maps gives
        typed values, which are rendered back to that form here.
        """
        return [
            [str(value) for value in (row.name, row.start, row.end, row.min, row.max)]
            for row in list_maps(self.tools, "strds", dataset)
        ]


def _specs(*rows):
    """MapSpecs from (name, value, start, end) rows, times as ISO text"""
    return [
        MapSpec(
            name,
            value,
            datetime.fromisoformat(start),
            None if end is None else datetime.fromisoformat(end),
        )
        for name, value, start, end in rows
    ]


@pytest.fixture(scope="module")
def aggregate_ds_data(temporal_module_session):
    """Session with input and sampler datasets

    - input: m1=1, m2=2 on days 1 and 2, nz1 and nz2 null on day 3, so that
      the day 3 sampler interval aggregates to an all null map.
    - samp: an strds of daily interval maps s1, s2, s3 on days 1, 2, 3.
    - precip and vsoil: the deterministic part of the legacy shell test, a
      monthly precip strds (six maps from 2001-03-01) and an stvds sampler of
      three intervals, for the vector sampler path.
    - gapin: g1 on day 1 and g3 on day 3, so that the day 2 sampler interval
      of samp relates to no map and leaves a gap in numbered output names.
    - ordin and osamp: ct=9 on 2001-01-05 .. 2001-01-06 lies inside and
      ov1=1 on 2001-01-02 .. 2001-01-15 overlaps the single sampler interval
      2001-01-01 .. 2001-01-11, so that one granule collects maps through
      the two relations contains and overlaps.
    - instants: pp1 and pp2 (10, 20) at 12:00 and 18:00 of day 1, pp3 (30)
      exactly at midnight starting day 3, pp4 (40) on day 5, all without end
      time, for the time instant input of the sampling relations.

    The computational region is 3x3 cells of size 1.
    """
    session = temporal_module_session
    tools = Tools(session=session, overwrite=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    for name, rows in [
        (
            "input",
            [
                ("m1", 1, "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("m2", 2, "2001-01-02 06:00:00", "2001-01-02 18:00:00"),
                ("nz1", "null()", "2001-01-03 06:00:00", "2001-01-03 12:00:00"),
                ("nz2", "null()", "2001-01-03 13:00:00", "2001-01-03 18:00:00"),
            ],
        ),
        (
            "gapin",
            [
                ("g1", 1, "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("g3", 3, "2001-01-03 06:00:00", "2001-01-03 18:00:00"),
            ],
        ),
        (
            "ordin",
            [
                ("ov1", 1, "2001-01-02 00:00:00", "2001-01-15 00:00:00"),
                ("ct", 9, "2001-01-05 00:00:00", "2001-01-06 00:00:00"),
            ],
        ),
        ("osamp", [("os1", 1, "2001-01-01 00:00:00", "2001-01-11 00:00:00")]),
        (
            "instants",
            [
                ("pp1", 10, "2001-01-01 12:00:00", None),
                ("pp2", 20, "2001-01-01 18:00:00", None),
                ("pp3", 30, "2001-01-03 00:00:00", None),
                ("pp4", 40, "2001-01-05 00:00:00", None),
            ],
        ),
        (
            "samp",
            [
                ("s1", 1, "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
                ("s2", 2, "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
                ("s3", 3, "2001-01-03 00:00:00", "2001-01-04 00:00:00"),
            ],
        ),
    ]:
        create_stds(tools, "strds", name, _specs(*rows), via="library")

    # Deterministic part of the legacy shell test: a monthly precip strds
    # and an stvds sampler of three fixed intervals. The vector content is
    # irrelevant; only the time stamps are used.
    precip = [100, 150, 250, 250, 150, 100]
    create_stds(
        tools,
        "strds",
        "precip",
        [
            MapSpec(f"prec_{i}", value, start, end)
            for i, (value, (start, end)) in enumerate(
                zip(precip, intervals(6, start=2), strict=True), start=1
            )
        ],
    )
    for i in range(1, 4):
        tools.v_random(output=f"soil_{i}", npoints=5)
    register_stds(
        tools,
        "stvds",
        "vsoil",
        _specs(
            ("soil_1", 0, "2001-01-01", "2001-04-01"),
            ("soil_2", 0, "2001-05-01", "2001-07-01"),
            ("soil_3", 0, "2001-08-01", "2001-12-01"),
        ),
    )

    return SimpleNamespace(session=session, read=Reader(session))
