"""Tests for the absolute granularities that the recordings do not reach

The recordings of the granularity functions run the common granule of every
subset of a short list. This test adds the combinations of more units, the
hierarchy limits of the common granule with start dates and the granularity of
maps. The expected values are the answers of the functions before they were
computed from one table of units, kept in data/granularity_characterization.json.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.temporal_granularity import (
    compute_common_absolute_time_granularity,
    compute_common_absolute_time_granularity_simple,
)
from grass.temporal import temporal_granularity

pytestmark = pytest.mark.usefixtures("temporal_module_session")

DATA = json.loads(
    (Path(__file__).parent / "data" / "granularity_characterization.json").read_text()
)

# The start dates of the common granule: all alike, or different in one field
DATES = {
    "same": [datetime(2001, 1, 1), datetime(2001, 1, 1)],
    "second": [datetime(2001, 1, 1), datetime(2001, 1, 1, 0, 0, 5)],
    "minute": [datetime(2001, 1, 1), datetime(2001, 1, 1, 0, 7)],
    "hour": [datetime(2001, 1, 1), datetime(2001, 1, 1, 3)],
    "day": [datetime(2001, 1, 1), datetime(2001, 1, 4)],
    "month": [datetime(2001, 1, 1), datetime(2001, 3, 1)],
    "year": [datetime(2001, 1, 1), datetime(2003, 1, 1)],
    "none": None,
}


@pytest.mark.parametrize(("grans", "expected"), DATA["simple"])
def test_the_simple_common_granule(grans, expected):
    result = compute_common_absolute_time_granularity_simple(grans)

    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize(("grans", "dates", "expected"), DATA["starts"])
def test_the_common_granule_with_start_dates(grans, dates, expected):
    result = compute_common_absolute_time_granularity(grans, DATES[dates])

    assert result == expected
    assert type(result) is type(expected)


@pytest.mark.parametrize("name", DATA["maps"])
def test_the_granularity_of_maps(name):
    maps = []
    for index, (start, end) in enumerate(DATA["specs"][name]):
        map_ = tgis.RasterDataset(f"a{index}@P")
        map_.set_absolute_time(
            datetime.fromisoformat(start), end and datetime.fromisoformat(end)
        )
        maps.append(map_)

    assert (
        temporal_granularity.compute_absolute_time_granularity(maps)
        == (DATA["maps"][name])
    )
