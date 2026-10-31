"""materialize() of a reduction that skips null cells past the open files

r.series holds two files per map and thread unless -z makes it read the
maps cell by cell, so a reduction over more maps than the open files of the
process allow must run with -z.
"""

import resource

import pytest

from grass.temporal.algebra.content import MapRef, SeriesReduce
from grass.temporal.algebra.materialize import materialize
from grass.temporal.algebra.series import Extent, Series, Slot
from grass.tools import Tools

MAPS = 20


@pytest.fixture(scope="module")
def session(temporal_module_session):
    grass_session = temporal_module_session
    tools = Tools(session=grass_session, overwrite=True)
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for number in range(1, MAPS + 1):
        tools.r_mapcalc(expression=f"n{number} = {number}")
    return grass_session, tools


@pytest.fixture
def few_open_files():
    """Lower the soft limit of open files of this process to 256

    The children that run the modules inherit it. The limit is set back
    afterwards, so the rest of the session keeps its files.
    """
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, hard))
    yield
    resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def test_a_reduction_past_the_open_files_runs_and_sums(
    session, few_open_files, monkeypatch
):
    """20 maps on 8 threads hold 320 files, more than the 256 allowed; with
    -z r.series runs and gives the sum 1 + 2 + ... + 20"""
    grass_session, tools = session
    monkeypatch.setenv("OMP_NUM_THREADS", "8")
    maps = tuple(MapRef(f"n{number}") for number in range(1, MAPS + 1))
    slot = Slot(Extent(0, 1, "days"), SeriesReduce("sum", maps))
    materialize(Series((slot,)), "skipsum", names=["skipsum_1"], overwrite=True)
    assert float(tools.r_univar(map="skipsum_1", flags="g").keyval["min"]) == 210.0
