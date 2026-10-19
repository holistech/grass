"""Test t.remove with maps that two datasets share

Both datasets register the same six one-day maps. Removing one dataset must
leave the other one with the maps; with -r the maps leave the temporal
database and so the other dataset, whose metadata should follow, as
t.unregister makes it follow.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def test_f_leaves_the_other_dataset_as_it_was(tools, make_stds):
    maps, (first, second) = make_stds(6, datasets=2)

    tools.t_remove(inputs=first, flags="f")

    assert [row.name for row in list_maps(tools, "strds", second)] == maps
    info = stds_info(tools, "strds", second)
    assert info["number_of_maps"] == 6
    assert info["start_time"] == "'2001-01-01 00:00:00'"
    assert info["end_time"] == "'2001-01-07 00:00:00'"


def test_rf_takes_the_maps_out_of_the_other_dataset(tools, make_stds, registered):
    maps, (first, second) = make_stds(6, datasets=2)

    tools.t_remove(inputs=first, flags="rf")

    assert registered(maps) == [False] * 6
    assert list_maps(tools, "strds", second) == []


def test_today_rf_leaves_the_metadata_of_the_other_dataset_stale(tools, make_stds):
    # Only the maps of the removed dataset are deleted by id: the maps of the
    # other dataset are gone from the listing, but the dataset still counts
    # and spans them.
    maps, (first, second) = make_stds(6, datasets=2)
    tools.t_remove(inputs=first, flags="rf")

    info = stds_info(tools, "strds", second)

    assert info["number_of_maps"] == 6
    assert info["start_time"] == "'2001-01-01 00:00:00'"


@pytest.mark.xfail(
    strict=True,
    reason="t.remove -rf leaves number_of_maps and the time range of another dataset that shared the removed maps unchanged",
)
def test_rf_updates_the_metadata_of_the_other_dataset(tools, make_stds):
    maps, (first, second) = make_stds(6, datasets=2)
    tools.t_remove(inputs=first, flags="rf")

    assert stds_info(tools, "strds", second)["number_of_maps"] == 0
