"""Test the end of the processed time of t.rast.accdetect

Without stop the run ends with the input dataset. A time instant at the end
is processed, a last interval is processed as ever. The expected values are
derived in the comments.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import cell_values, list_maps

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _detect(tools, output, **options):
    options = {"range": "10,50", **options}
    tools.t_rast_accdetect(occurrence=output, basename=output, **options)
    return [
        (row.start, row.end, cell_values(tools, row.name))
        for row in list_maps(tools, "strds", output)
    ]


def test_an_instant_at_the_end_is_processed_without_stop(tools, prefix):
    # A map of the value 20 from the 1st to the 2nd of January 2001 and an
    # instant on the 3rd of the value 30, both inside the range 10 to 50. One
    # cycle of three days from the 1st holds both. The occurrence is the
    # number of days from the start of the cycle to the start of the map: 0
    # for the first map and 2 for the instant. The run with stop behind the
    # instant gives the same.
    small_region(tools, 1, 1)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m0", 20, day(0), day(1)),
            MapSpec(f"{prefix}_m1", 30, day(2)),
        ],
    )
    options = {"input": f"{prefix}_in", "start": "2001-01-01", "cycle": "3 days"}

    without = _detect(tools, f"{prefix}_a", **options)
    with_stop = _detect(tools, f"{prefix}_b", stop="2001-01-04", **options)

    assert [cells for _, _, cells in without] == [[0], [2]]
    assert without == with_stop


def test_a_relative_instant_at_the_end_is_processed_without_stop(tools, prefix):
    # An interval 0 to 1 of the value 20 and an instant at 2 of the value 30,
    # one cycle of 3: the occurrence is 0 for the interval and 2 for the
    # instant, as with stop=4.
    small_region(tools, 1, 1)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m0", 20, 0, 1), MapSpec(f"{prefix}_m1", 30, 2)],
        temporaltype="relative",
        unit="days",
    )
    options = {"input": f"{prefix}_in", "start": "0", "cycle": "3"}

    without = _detect(tools, f"{prefix}_a", **options)
    with_stop = _detect(tools, f"{prefix}_b", stop="4", **options)

    assert [cells for _, _, cells in without] == [[0], [2]]
    assert without == with_stop


def test_a_last_interval_gives_the_same_maps_as_before(tools, prefix):
    # Daily maps with 20, 30 and 5 and a cycle of three days: the 20 and the
    # 30 lie in the range 10 to 50, the 5 does not, so the occurrence is 0
    # and 1 and the third day has no map. The dataset ends with the interval,
    # which no instant moves, so stop is the 4th of January, with or without
    # the option.
    small_region(tools, 1, 1)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m{k}", v, day(k), day(k + 1))
            for k, v in enumerate((20, 30, 5))
        ],
    )
    options = {"input": f"{prefix}_in", "start": "2001-01-01", "cycle": "3 days"}

    without = _detect(tools, f"{prefix}_a", **options)
    with_stop = _detect(tools, f"{prefix}_b", stop="2001-01-04", **options)

    assert [cells for _, _, cells in without] == [[0], [1]]
    assert without == with_stop
