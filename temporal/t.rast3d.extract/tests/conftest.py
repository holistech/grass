"""Datasets for the tests of t.rast3d.extract that use the shared tools fixture"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region


def quarter(index):
    """The first day of quarter index, counted from 2001-01-01"""
    month = 1 + 3 * index
    return datetime(2001 + (month - 1) // 12, (month - 1) % 12 + 1, 1)


@pytest.fixture(scope="module")
def quarterly(tools):
    """Six maps of three months from 2001-01-01 holding 100 to 600; the name

    The region has one row, two columns and one layer, so the t.info keys of
    the extracted datasets are known: north 1, south 0, east 2, west 0, top 1,
    bottom 0, resolution 1 in all directions.
    """
    small_region(tools, 1, 2, depths=1)
    create_stds(
        tools,
        "str3ds",
        "e3_quarterly",
        [
            MapSpec(f"e3_q{k + 1}", 100 * (k + 1), quarter(k), quarter(k + 1))
            for k in range(6)
        ],
    )
    return "e3_quarterly"
