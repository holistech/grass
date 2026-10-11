"""Fixtures for t.rast.algebra tests"""

import os
from types import SimpleNamespace

import pytest

import grass.script as gs
from grass.tools import Tools


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
