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


def test_rf_updates_the_metadata_of_the_other_dataset(tools, make_stds):
    maps, (first, second) = make_stds(6, datasets=2)
    tools.t_remove(inputs=first, flags="rf")

    info = stds_info(tools, "strds", second)
    assert info["number_of_maps"] == 0
    assert info["start_time"] == "'None'"
    assert info["end_time"] == "'None'"


def test_rf_updates_a_dataset_that_shares_maps_of_another_mapset(two_mapsets, prefix):
    # The maps belong to "other" and are registered there as well, so that
    # t.remove can read them; the two datasets of "work" share them.
    work, other = two_mapsets
    maps = [f"{prefix}_{i}" for i in range(3)]
    for name in maps:
        other.r_mapcalc(expression=f"{name} = 1")
    other.t_create(output=f"{prefix}_own", title="t", description="t")
    other.t_register(
        input=f"{prefix}_own", maps=maps, start="2001-01-01", increment="1 days"
    )
    for dataset in ("first", "second"):
        work.t_create(output=f"{prefix}_{dataset}", title="t", description="t")
        work.t_register(
            input=f"{prefix}_{dataset}",
            maps=[f"{name}@other" for name in maps],
            start="2001-01-01",
            increment="1 days",
        )

    work.t_remove(inputs=f"{prefix}_first", flags="rf")

    info = stds_info(work, "strds", f"{prefix}_second")
    assert info["number_of_maps"] == 0
    assert info["start_time"] == "'None'"
