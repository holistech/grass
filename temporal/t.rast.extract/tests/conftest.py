"""Datasets for the tests of t.rast.extract that use the shared tools fixture"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, quarter, small_region


@pytest.fixture(scope="module")
def quarterly(tools):
    """Six maps of three months from 2001-01-01 holding 100 to 600; the name

    The region has one row and two cells, so the t.info keys of the extracted
    datasets are known: north 1, south 0, east 2, west 0, resolution 1.
    """
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ext_quarterly",
        [
            MapSpec(f"ext_q{k + 1}", 100 * (k + 1), quarter(k), quarter(k + 1))
            for k in range(6)
        ],
    )
    return "ext_quarterly"
