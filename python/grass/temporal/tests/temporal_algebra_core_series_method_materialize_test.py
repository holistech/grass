"""materialize() of a SeriesAggregate: g.copy for one map, r.series for more

A one map granule is copied with g.copy, so the CELL type and the color
table survive; two maps run r.series. Measured expectations match the
characterization tests of t.rast.aggregate.
"""

import os

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.algebra.content import MapRef, SeriesAggregate
from grass.temporal.algebra.materialize import materialize
from grass.temporal.algebra.series import Extent, Series, Slot
from grass.tools import Tools


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    project = tmp_path_factory.mktemp("aggregate_materialize") / "project"
    gs.create_project(project)
    with (
        pytest.MonkeyPatch.context() as monkeypatch,
        gs.setup.init(project, env=os.environ.copy()) as grass_session,
    ):
        for key, value in grass_session.env.items():
            if os.environ.get(key) != value:
                monkeypatch.setenv(key, value)
        tgis.init(True)
        tools = Tools(session=grass_session, overwrite=True)
        tools.g_region(n=3, s=0, e=3, w=0, res=1)
        tools.r_mapcalc(expression="a = 1")
        tools.r_mapcalc(expression="b = 3")
        tools.r_colors(map="a", color="grey")
        yield grass_session, tools


def _slot(start, end, content):
    return Slot(Extent(start, end, "days"), content)


def test_single_map_is_copied_verbatim(session):
    grass_session, tools = session
    series = Series((_slot(0, 1, SeriesAggregate("average", (MapRef("a"),), 1000)),))
    materialize(series, "copied", basename="c", names=["c_1"], overwrite=True)
    assert tools.r_info(map="c_1", flags="g").keyval["datatype"] == "CELL"
    assert float(tools.r_univar(map="c_1", flags="g").keyval["min"]) == 1.0
    assert tools.r_colors_out(map="c_1").text.strip().splitlines()[0] == "1 127:127:127"


def test_two_maps_run_r_series(session):
    grass_session, tools = session
    node = SeriesAggregate("average", (MapRef("a"), MapRef("b")), 1000)
    materialize(Series((_slot(0, 1, node),)), "mean", names=["m_1"], overwrite=True)
    assert tools.r_info(map="m_1", flags="g").keyval["datatype"] == "DCELL"
    assert float(tools.r_univar(map="m_1", flags="g").keyval["min"]) == 2.0


def test_file_limit_adds_the_z_flag(session):
    """Past the file limit r.series reads the inputs cell by cell (-z); the
    values are the same, so the result still averages a and b"""
    grass_session, tools = session
    node = SeriesAggregate("average", (MapRef("a"), MapRef("b")), 1)
    materialize(Series((_slot(0, 1, node),)), "zmean", names=["z_1"], overwrite=True)
    assert float(tools.r_univar(map="z_1", flags="g").keyval["min"]) == 2.0
