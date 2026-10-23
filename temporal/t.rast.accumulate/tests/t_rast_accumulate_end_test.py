"""Test the end of the processed time of t.rast.accumulate

Without stop the run ends with the dataset; a time instant at the end is
processed, a last interval is processed as ever. The expected values are
derived in the comments.
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


def test_an_instant_at_the_end_is_processed_without_stop(tools, prefix):
    # A map of the value 5 from the 1st to the 2nd of January 2001 and an
    # instant on the 3rd of the value 7. The cycle and the granularity are
    # one day. The cycle of the 1st holds the first map, the cycle of the 2nd
    # no map, the cycle of the 3rd the instant, so the sums are 5 (gdd from
    # 0) and 7. The run with stop behind the instant gives the same.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m0", 5, day(0), day(1)),
            MapSpec(f"{prefix}_m1", 7, day(2)),
        ],
    )
    options = {"input": f"{prefix}_in", "start": "2001-01-01", "cycle": "1 day"}

    without, _ = _accumulate(tools, f"{prefix}_a", **options)
    with_stop, _ = _accumulate(tools, f"{prefix}_b", stop="2001-01-04", **options)

    assert [value for _, _, value in without] == [5, 7]
    assert without == with_stop


def test_a_relative_instant_at_the_end_is_processed_without_stop(tools, prefix):
    # An interval 0 to 1 of the value 5 and an instant at 2 of the value 7,
    # cycle and granularity 1: the cycles [0,1) and [2,3) hold a map, so the
    # sums are 5 and 7, as with stop=3.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_m0", 5, 0, 1), MapSpec(f"{prefix}_m1", 7, 2)],
        temporaltype="relative",
        unit="days",
    )
    options = {
        "input": f"{prefix}_in",
        "start": "0",
        "cycle": "1",
        "granularity": "1",
    }

    without, _ = _accumulate(tools, f"{prefix}_a", **options)
    with_stop, _ = _accumulate(tools, f"{prefix}_b", stop="3", **options)

    assert [value for _, _, value in without] == [5, 7]
    assert without == with_stop


def test_a_last_interval_gives_the_same_maps_as_before(tools, prefix):
    # Three daily maps with 5, 10 and 20 and cycles of two days from the 1st:
    # the first cycle holds 5 and 10 (sums 5 and 15), the second the map of
    # 20 (sum 20). The dataset ends with the interval, which no instant
    # moves, so stop is the 4th of January, with or without the option.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_m{k}", v, day(k), day(k + 1))
            for k, v in enumerate((5, 10, 20))
        ],
    )
    options = {"input": f"{prefix}_in", "start": "2001-01-01", "cycle": "2 days"}

    without, _ = _accumulate(tools, f"{prefix}_a", **options)
    with_stop, _ = _accumulate(tools, f"{prefix}_b", stop="2001-01-04", **options)

    assert [value for _, _, value in without] == [5, 15, 20]
    assert without == with_stop
