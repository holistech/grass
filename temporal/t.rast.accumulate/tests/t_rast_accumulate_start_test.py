"""Test the start of the processed time of t.rast.accumulate

A start that does not lie on the granularity is moved to it (a month to its
first day) and the run says so. The expected values are derived in the
comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _accumulate(tools, output, **options):
    options = {"limits": "0,100", **options}
    result = tools.t_rast_accumulate(output=output, basename=output, **options)
    rows = [(row.start, row.end, row.min) for row in list_maps(tools, "strds", output)]
    return rows, message(result)


@pytest.fixture
def january(tools, prefix):
    """Seven daily maps from 2001-01-01 with the value 15 each"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_jan",
        [MapSpec(f"{prefix}_j{k}", 15, day(k), day(k + 1)) for k in range(7)],
    )
    return f"{prefix}_jan"


def test_a_start_moved_to_the_granularity_warns(tools, prefix, january):
    # 2001-01-31 lies in the month that starts on 2001-01-01. The granule
    # of January holds the seven maps of the value 15, so the mean, the gdd
    # increment above 0 and the sum are 15, and the map is the first of its
    # cycle of two months. The values are those of the run from 2001-01-01.
    options = {"input": january, "granularity": "1 months", "cycle": "2 months"}

    rows, text = _accumulate(tools, f"{prefix}_a", start="2001-01-31", **options)
    expected, _ = _accumulate(tools, f"{prefix}_b", start="2001-01-01", **options)

    assert rows[0][2] == 15
    assert [(start, value) for start, _, value in rows] == [
        (start, value) for start, _, value in expected
    ]
    assert "2001-01-31" in text
    assert "2001-01-01" in text
    assert "1 months" in text


def test_a_start_on_the_granularity_does_not_warn(tools, prefix, january):
    rows, text = _accumulate(
        tools,
        f"{prefix}_a",
        input=january,
        start="2001-01-01",
        granularity="1 months",
        cycle="2 months",
    )

    assert rows[0][2] == 15
    assert "WARNING" not in text
