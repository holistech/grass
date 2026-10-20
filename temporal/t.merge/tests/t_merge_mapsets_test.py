"""Test t.merge with a dataset of another mapset: it can be merged, not into

A dataset <prefix>_src of the mapset "other" holds three maps made there, map n
with the value n from day n-1 to day n. The tests run in the mapset "work",
which has "other" in its search path.
"""

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.readback import list_maps
from grass.tools import ToolError

# Only the test that makes its data in the body runs longer than one second;
# the others get theirs from a fixture (measured 18.10.2026 with a serial
# pytest --durations=0).


@pytest.fixture
def foreign(two_mapsets, prefix):
    """The dataset <prefix>_src of mapset other and the names of its maps"""
    maps = create_daily_stds(
        two_mapsets.other, "strds", [f"{prefix}_src"], 3, map_prefix=f"{prefix}_o"
    )
    return f"{prefix}_src", maps


def test_the_maps_of_a_dataset_of_another_mapset_are_merged(
    two_mapsets, prefix, foreign
):
    work, _ = two_mapsets
    name, maps = foreign

    work.t_merge(inputs=f"{name}@other", output=f"{prefix}_out")

    assert [r.name for r in list_maps(work, "strds", f"{prefix}_out")] == maps


def test_a_refused_merge_does_not_create_the_output(two_mapsets, prefix, foreign):
    work, _ = two_mapsets
    name, _ = foreign

    with pytest.raises(ToolError):
        work.t_merge(inputs=f"{name}@other,{prefix}_missing", output=f"{prefix}_out")

    assert f"{prefix}_out" not in work.t_list(type="strds", columns="name").stdout


def test_today_an_input_without_a_mapset_is_taken_from_the_current_mapset(
    two_mapsets, prefix, foreign
):
    # t.copy finds such a dataset in the search path; t.merge adds the current
    # mapset to every name that has none.
    work, _ = two_mapsets
    name, _ = foreign

    with pytest.raises(
        ToolError, match=r"Space\s+time\s+dataset\s+<.*>\s+of\s+type\s+<strds>"
    ):
        work.t_merge(inputs=name, output=f"{prefix}_out")


@pytest.mark.slow
def test_an_output_in_another_mapset_is_refused(two_mapsets, prefix):
    work, other = two_mapsets
    create_daily_stds(work, "strds", [f"{prefix}_loc"], 2, map_prefix=prefix)

    with pytest.raises(ToolError, match=r"must\s+be\s+located\s+in\s+this\s+mapset"):
        work.t_merge(inputs=f"{prefix}_loc", output=f"{prefix}_out@other")

    assert f"{prefix}_out" not in other.t_list(type="strds", columns="name").stdout
