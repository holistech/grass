"""Fixtures for the characterization tests of t.rast.aggregate.ds"""

import os
from types import SimpleNamespace

import pytest

import grass.script as gs
import grass.temporal as tgis
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
        text = self.tools.t_rast_list(
            input=dataset, columns="name", flags="u"
        ).text.strip()
        return text.splitlines() if text else []

    def rows(self, dataset):
        text = self.tools.t_rast_list(
            input=dataset,
            columns="name,start_time,end_time,min,max",
            separator="pipe",
            flags="u",
        ).text.strip()
        return [line.split("|") for line in text.splitlines()]


def _register_raster(dataset, temporaltype, rows):
    tgis.open_new_stds(
        dataset, "strds", temporaltype, dataset, dataset, "mean", overwrite=True
    )
    for name, start, end in rows:
        tgis.register_maps_in_space_time_dataset(
            "raster", dataset, name, start=start, end=end
        )


@pytest.fixture(scope="module")
def aggregate_ds_data(tmp_path_factory):
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

    The computational region is 3x3 cells of size 1.
    """
    project = tmp_path_factory.mktemp("t_rast_aggregate_ds") / "project"
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
        for name, value in [("m1", 1), ("m2", 2), ("nz1", "null()"), ("nz2", "null()")]:
            tools.r_mapcalc(expression=f"{name} = {value}")
        for i in range(1, 4):
            tools.r_mapcalc(expression=f"s{i} = {i}")
        _register_raster(
            "input",
            "absolute",
            [
                ("m1", "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("m2", "2001-01-02 06:00:00", "2001-01-02 18:00:00"),
                ("nz1", "2001-01-03 06:00:00", "2001-01-03 12:00:00"),
                ("nz2", "2001-01-03 13:00:00", "2001-01-03 18:00:00"),
            ],
        )
        for name, value in [("g1", 1), ("g3", 3), ("ct", 9), ("ov1", 1), ("os1", 1)]:
            tools.r_mapcalc(expression=f"{name} = {value}")
        _register_raster(
            "gapin",
            "absolute",
            [
                ("g1", "2001-01-01 06:00:00", "2001-01-01 18:00:00"),
                ("g3", "2001-01-03 06:00:00", "2001-01-03 18:00:00"),
            ],
        )
        _register_raster(
            "ordin",
            "absolute",
            [
                ("ov1", "2001-01-02 00:00:00", "2001-01-15 00:00:00"),
                ("ct", "2001-01-05 00:00:00", "2001-01-06 00:00:00"),
            ],
        )
        _register_raster(
            "osamp",
            "absolute",
            [("os1", "2001-01-01 00:00:00", "2001-01-11 00:00:00")],
        )
        _register_raster(
            "samp",
            "absolute",
            [
                ("s1", "2001-01-01 00:00:00", "2001-01-02 00:00:00"),
                ("s2", "2001-01-02 00:00:00", "2001-01-03 00:00:00"),
                ("s3", "2001-01-03 00:00:00", "2001-01-04 00:00:00"),
            ],
        )

        # Deterministic part of the legacy shell test: a monthly precip strds
        # and an stvds sampler of three fixed intervals. The vector content is
        # irrelevant; only the time stamps are used.
        for i, value in enumerate([100, 150, 250, 250, 150, 100], start=1):
            tools.r_mapcalc(expression=f"prec_{i} = {value}")
        tools.t_create(
            type="strds",
            temporaltype="absolute",
            output="precip",
            title="precip",
            description="precip",
        )
        tools.t_register(
            flags="i",
            type="raster",
            input="precip",
            maps="prec_1,prec_2,prec_3,prec_4,prec_5,prec_6",
            start="2001-03-01 00:00:00",
            increment="1 months",
        )
        for i in range(1, 4):
            tools.v_random(output=f"soil_{i}", npoints=5)
        tools.t_create(
            type="stvds",
            temporaltype="absolute",
            output="vsoil",
            title="vsoil",
            description="vsoil",
        )
        register = tmp_path_factory.mktemp("reg") / "soil.txt"
        register.write_text(
            "soil_1|2001-01-01|2001-04-01\n"
            "soil_2|2001-05-01|2001-07-01\n"
            "soil_3|2001-08-01|2001-12-01\n"
        )
        tools.t_register(type="vector", input="vsoil", file=str(register))

        yield SimpleNamespace(session=session, read=Reader(session))
