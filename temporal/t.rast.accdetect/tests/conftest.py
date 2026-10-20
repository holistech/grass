"""Fixtures of the t.rast.accdetect tests

The input is a dataset of six daily maps from 2001-01-01 on a region of two
cells. The first cell holds 5, 20, 30, 40, 5, 5, the second 20, 30, 5, 20, 30,
5. With the range 10 to 50 (the bounds are not part of the range) the first
cell is in the range on the days 1, 2 and 3 (counted from 0) and the second
on the days 0, 1, 3 and 4.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import cell_values, list_maps
from grass.temporal.testing.session import project_session
from grass.tools import Tools

FIRST = [5, 20, 30, 40, 5, 5]
SECOND = [20, 30, 5, 20, 30, 5]


def make_cells(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "det_cells",
        [
            MapSpec(f"det_c{k}", f"if(col() == 1, {a}, {b})", day(k), day(k + 1))
            for k, (a, b) in enumerate(zip(FIRST, SECOND, strict=True))
        ],
    )
    return "det_cells"


@pytest.fixture(scope="module")
def cells(tools):
    return make_cells(tools)


def _by_day(tools, dataset):
    """The cells of every map of the dataset, by the day of its start (0 is 2001-01-01)

    A day on which the dataset holds no map is not in the result.
    """
    return {
        (datetime.fromisoformat(row.start) - day(0)).days: cell_values(tools, row.name)
        for row in list_maps(tools, "strds", dataset)
    }


@pytest.fixture
def by_day(tools):
    """Function that reads a dataset as {day: cells}"""
    return lambda dataset: _by_day(tools, dataset)


@pytest.fixture
def detect(tools, cells, by_day):
    """Function that runs t.rast.accdetect on the cells and reads the occurrence

    detect(name, **options) writes the occurrence dataset and the maps <name>
    (an option such as range=None leaves a default out) and gives the cells
    by day. The defaults are the cycle of six days from 2001-01-01 and the
    range 10 to 50.
    """

    def run(name, **options):
        options = {
            "input": cells,
            "start": "2001-01-01",
            "cycle": "6 days",
            "range": "10,50",
            **options,
        }
        options = {key: value for key, value in options.items() if value is not None}
        tools.t_rast_accdetect(occurrence=name, basename=name, **options)
        return by_day(name)

    return run


@pytest.fixture(scope="module", params=["UTC", "Asia/Kathmandu"])
def zone_tools(request, tmp_path_factory):
    """Tools in a project of its own whose subprocesses run with TZ set"""
    with project_session(tmp_path_factory.mktemp("zone") / "project") as session:
        session.env["TZ"] = request.param
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        make_cells(tools)
        create_stds(
            tools,
            "strds",
            "det_min_step",
            [
                MapSpec("det_ms0", 15, day(0), day(3)),
                MapSpec("det_ms1", 35, day(3), day(6)),
            ],
        )
        yield tools


@pytest.fixture
def zone_by_day(zone_tools):
    """Function that reads a dataset of the project of zone_tools as {day: cells}"""
    return lambda dataset: _by_day(zone_tools, dataset)
