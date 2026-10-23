"""Test the flags of t.remove: what -r, -f and -d remove, and what a plain call says

Six one-day maps, registered in a dataset (and in a second one for some
tests). Without -f nothing is removed and the call lists what -f would
remove. -f removes the dataset, -r also the maps from the temporal database,
-d also the maps of the dataset from the mapset; -r and -d need -f to act.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _message(result):
    """The messages of a call as one line: the tool wraps long ones"""
    return " ".join(result.stderr.split())


def test_without_flags_nothing_is_removed(tools, make_stds, has_dataset, registered):
    maps, (name,) = make_stds(3)

    result = tools.t_remove(inputs=name)

    message = _message(result)
    assert f"STRDS: {name}@PERMANENT" in message
    assert "Nothing removed. You must use the force flag (-f)" in message
    assert has_dataset(name)
    assert registered(maps) == [True] * 3


def test_r_without_f_lists_the_maps_it_would_unregister(
    tools, make_stds, has_dataset, registered
):
    maps, (name,) = make_stds(3)

    result = tools.t_remove(inputs=name, flags="r")

    message = _message(result)
    assert "will be unregistered from temporal database:" in message
    for map_name in maps:
        assert f"- {map_name}" in message
    assert "Nothing removed" in message
    assert has_dataset(name)
    assert registered(maps) == [True] * 3


def test_d_without_f_lists_the_maps_it_would_delete(
    tools, make_stds, has_dataset, registered, existing
):
    maps, (name,) = make_stds(3)

    result = tools.t_remove(inputs=name, flags="d")

    message = _message(result)
    assert "unregistered from temporal database and removed from spatial database:" in (
        message
    )
    for map_name in maps:
        assert f"- {map_name}" in message
    assert has_dataset(name)
    assert registered(maps) == [True] * 3
    assert existing(maps) == [True] * 3


def test_f_removes_the_dataset_and_keeps_the_maps(
    tools, make_stds, has_dataset, registered, existing
):
    maps, (name, other) = make_stds(3, datasets=2)

    result = tools.t_remove(inputs=name, flags="f")

    assert result.stderr == ""
    assert not has_dataset(name)
    assert has_dataset(other)
    assert registered(maps) == [True] * 3
    assert existing(maps) == [True] * 3
    # The other dataset still holds all three maps.
    assert (
        tools.t_info(type="strds", input=other, flags="g").keyval["number_of_maps"] == 3
    )


def test_rf_unregisters_the_maps_and_keeps_them_in_the_mapset(
    tools, make_stds, has_dataset, registered, existing
):
    maps, (name,) = make_stds(3)

    tools.t_remove(inputs=name, flags="rf")

    assert not has_dataset(name)
    assert registered(maps) == [False] * 3
    assert existing(maps) == [True] * 3


def test_df_deletes_the_maps_of_the_dataset_only(
    tools, make_stds, has_dataset, registered, existing, prefix
):
    maps, (name,) = make_stds(3)
    tools.r_mapcalc(expression=f"{prefix}_bystander = 7")

    tools.t_remove(inputs=name, flags="df")

    assert not has_dataset(name)
    assert registered(maps) == [False] * 3
    assert existing(maps) == [False] * 3
    assert existing([f"{prefix}_bystander"]) == [True]


def test_r_and_d_together_delete_the_maps(
    tools, make_stds, has_dataset, registered, existing
):
    maps, (name,) = make_stds(2)

    tools.t_remove(inputs=name, flags="rdf")

    assert not has_dataset(name)
    assert registered(maps) == [False] * 2
    assert existing(maps) == [False] * 2


def test_the_old_sequence_removing_twice_fails_the_second_time(
    tools, make_stds, has_dataset, registered
):
    # The former shell test registered six maps in steps of one second, removed
    # the dataset with -rf and called -r again, expecting the error.
    maps, (name,) = make_stds(6)
    tools.t_remove(inputs=name, flags="rf")

    with pytest.raises(
        ToolError, match=r"Space\s+time\s+dataset\s+<.*>\s+of\s+type\s+<strds>"
    ):
        tools.t_remove(inputs=name, flags="r")

    assert not has_dataset(name)
    assert registered(maps) == [False] * 6


def test_f_without_inputs_is_refused(tools, make_stds, has_dataset):
    _, (first, second) = make_stds(1, datasets=2)

    with pytest.raises(ToolError) as error:
        tools.t_remove(flags="f")

    assert "inputs= or file= must be specified" in " ".join(
        message(error.value).split()
    )
    assert has_dataset(first)
    assert has_dataset(second)
