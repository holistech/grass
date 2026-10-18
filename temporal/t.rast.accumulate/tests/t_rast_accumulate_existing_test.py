"""Test t.rast.accumulate with existing results and with granules that cut the maps

The granule of an accumulation step takes the maps of the dataset by their
temporal relation to it: equal, contained, overlapped by or overlapping the
granule, or containing it, in that order of preference.
"""

import itertools

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Most tests make maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

OPTIONS = {"start": "2001-01-01", "limits": "0,40", "method": "gdd"}


def _text(offset, hours=0):
    return day(offset, hours=hours).strftime("%Y-%m-%d %H:%M:%S")


def _run(tools, name, **options):
    options = {**OPTIONS, **options}
    return tools.t_rast_accumulate(output=name, basename=name, **options)


def _series(tools, name):
    return [(row.start, row.min) for row in list_maps(tools, "strds", name)]


@pytest.fixture(scope="module")
def ones(tools):
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ex_ones",
        [MapSpec(f"ex_one{k}", 1, day(k), day(k + 1)) for k in range(12)],
    )


def test_twelve_steps_add_up(tools, ones):
    # One map of 1 per day for twelve days in a cycle of twelve: 1, 2, ... 12.
    _run(tools, "ex_twelve", input="ex_ones", cycle="12 days")

    assert _series(tools, "ex_twelve") == [(_text(k), k + 1) for k in range(12)]


def test_overwrite_replaces_the_output_dataset(tools, ones):
    _run(tools, "ex_over", input="ex_ones", cycle="3 days")
    assert [value for _, value in _series(tools, "ex_over")][:3] == [1, 2, 3]

    # The method mean adds the means: the same sums, but 2 instead of 1 per
    # step with the shift 1 (new = old + 1).
    _run(tools, "ex_over", input="ex_ones", cycle="3 days", shift=1, overwrite=True)

    values = [value for _, value in _series(tools, "ex_over")]
    assert values[:3] == [2, 4, 6]
    assert stds_info(tools, "strds", "ex_over")["number_of_maps"] == 12


_taken = itertools.count()


@pytest.fixture
def taken(tools, ones):
    """A basename whose first result map exists in a dataset of its own

    Each test gets its own name: the maps live in the mapset of the module and
    an overwrite run would otherwise leave a map to the next test.
    """
    base = f"ex_taken{next(_taken)}"
    create_stds(
        tools,
        "strds",
        f"{base}_ds",
        [MapSpec(f"{base}_2001_01_01", 7, day(40), day(41))],
    )
    return base


def test_a_result_map_that_is_registered_elsewhere_is_not_replaced(tools, taken):
    with pytest.raises(ToolError) as error:
        _run(tools, taken, input="ex_ones", cycle="3 days")

    assert (
        f"Map <{taken}_2001_01_01@PERMANENT> is already registered in the "
        "temporal database, use overwrite flag to overwrite" in message(error.value)
    )
    # The other dataset keeps its map.
    assert stds_info(tools, "strds", f"{taken}_ds")["number_of_maps"] == 1


def test_overwrite_replaces_a_result_map_that_is_registered_elsewhere(tools, taken):
    _run(tools, taken, input="ex_ones", cycle="3 days", overwrite=True)

    assert _series(tools, taken)[0] == (_text(0), 1)
    # The map is registered anew in the result dataset and dropped from the
    # other one's list.
    assert list_maps(tools, "strds", f"{taken}_ds") == []


@pytest.mark.xfail(
    strict=True,
    reason="The counter of the other dataset keeps the replaced map (1, not 0).",
)
def test_the_other_dataset_counts_its_maps_after_an_overwrite(tools, taken):
    _run(tools, taken, input="ex_ones", cycle="3 days", overwrite=True)

    assert stds_info(tools, "strds", f"{taken}_ds")["number_of_maps"] == 0


def test_a_granule_overlapping_a_map_takes_it(tools):
    # One map from 12:00 on the first day to 12:00 on the second, value 10.
    # The granule of the first day overlaps its start, the granule of the
    # second day its end, so both take the map: 10, then 10 + 10.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ex_straddle",
        [MapSpec("ex_st0", 10, day(0, hours=12), day(1, hours=12))],
    )

    _run(tools, "ex_overlap", input="ex_straddle", cycle="2 days")

    assert _series(tools, "ex_overlap") == [(_text(0), 10), (_text(1), 20)]


def test_a_granule_during_a_map_takes_it(tools):
    # One map of three days with the value 10: each daily granule lies inside
    # it and takes it, so the sums are 10, 20, 30.
    small_region(tools, 1, 2)
    create_stds(tools, "strds", "ex_long", [MapSpec("ex_long0", 10, day(0), day(3))])

    _run(tools, "ex_during", input="ex_long", cycle="3 days")

    assert _series(tools, "ex_during") == [
        (_text(0), 10),
        (_text(1), 20),
        (_text(2), 30),
    ]
