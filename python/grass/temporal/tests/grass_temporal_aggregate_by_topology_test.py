# SPDX-License-Identifier: GPL-2.0-or-later

"""aggregate_by_topology selects the maps of a granule by their relation to it

The granules are not in the temporal database: they are map objects with a
temporal extent, and the maps to aggregate are raster maps with a value
each, so r.series runs for real and the averages show which maps it got.
"""

from datetime import datetime

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.temporal.testing.data import make_map
from grass.temporal.testing.session import temporal_session
from grass.tools import Tools

pytestmark = pytest.mark.real_io


@pytest.fixture
def session_with_days(tmp_path):
    """Four daily raster maps d1 to d4 with the values 10, 20, 30 and 40"""
    with temporal_session(tmp_path / "project") as session:
        tgis.init(raise_fatal_error=True)
        tools = Tools(session=session, overwrite=True)
        tools.g_region(n=10, s=0, e=10, w=0, res=1)
        for day in range(1, 5):
            make_map(tools, "raster", f"d{day}", day * 10)
        yield session


def day_map(day):
    """The map object of the map dN, valid on day N of January 2001"""
    mapset = tgis.get_current_mapset()
    map_ = tgis.RasterDataset(f"d{day}@{mapset}")
    map_.set_absolute_time(datetime(2001, 1, day), datetime(2001, 1, day + 1))
    return map_


def span(name, start, end):
    """A map object named name that is valid from start to end (January 2001)"""
    map_ = tgis.RasterDataset(f"{name}@{tgis.get_current_mapset()}")
    map_.set_absolute_time(datetime(2001, 1, start), datetime(2001, 1, end))
    return map_


GRANULE = (2, 6)
# Name, first and last day of one map each against the granule from the second
# to the sixth of January, and the relation of the granule to the map.
CASES = [
    ("d1", 2, 6, "equal"),
    ("d2", 3, 5, "contains"),
    ("d3", 1, 8, "during"),
    ("d4", 2, 4, "started"),
    ("d1", 2, 8, "starts"),
    ("d2", 4, 6, "finished"),
    ("d3", 1, 6, "finishes"),
    ("d4", 4, 8, "overlaps"),
    ("d1", 1, 4, "overlapped"),
]


@pytest.mark.parametrize(("name", "start", "end", "relation"), CASES)
def test_each_relation_selects_its_map(session_with_days, name, start, end, relation):
    # The values of d1 to d4 are 10 to 40, so the mean names the map.
    granule = span("g", *GRANULE)
    others = [span(f"d{n}", 7, 8) for n in range(1, 5) if f"d{n}" != name]
    result = tgis.aggregate_by_topology(
        [granule],
        "1 day",
        [span(name, start, end), *others],
        [relation],
        "agg",
        "gran",
        method="average",
        nprocs=1,
    )

    assert len(result) == 1
    stats = gs.parse_command(
        "r.univar", map=result[0].get_name(), flags="g", env=session_with_days.env
    )
    assert float(stats["mean"]) == float(name[1]) * 10
