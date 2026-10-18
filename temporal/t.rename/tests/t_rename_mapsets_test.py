"""Test t.rename with a second mapset: only a dataset of the current one can move

The tests run in the mapset "work" and see the mapset "other" through the
search path. A dataset belongs to the mapset whose temporal database holds it.
"""

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.readback import list_maps
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _names(tools, name):
    return [row.name for row in list_maps(tools, "strds", name)]


def test_a_new_name_in_another_mapset_is_refused(two_mapsets, prefix):
    work = two_mapsets.work
    maps = create_daily_stds(work, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    # The old test used a mapset name that is not the current one as well.
    with pytest.raises(ToolError, match=r"differs\s+from\s+the\s+current\s+mapset"):
        work.t_rename(input=f"{prefix}_ds", output=f"{prefix}_new@other")

    assert _names(work, f"{prefix}_ds") == maps


def test_a_dataset_of_another_mapset_cannot_be_renamed(two_mapsets, prefix):
    work, other = two_mapsets
    maps = create_daily_stds(other, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    with pytest.raises(ToolError, match=r"does\s+not\s+match\s+the\s+current\s+mapset"):
        work.t_rename(input=f"{prefix}_ds@other", output=f"{prefix}_new")

    assert _names(other, f"{prefix}_ds") == maps
    assert f"{prefix}_new" not in work.t_list(type="strds", columns="name").stdout


def test_the_dataset_of_the_current_mapset_is_renamed_when_both_have_the_name(
    two_mapsets, prefix
):
    work, other = two_mapsets
    name = f"{prefix}_ds"
    create_daily_stds(work, "strds", [name], 2, map_prefix=f"{prefix}_w")
    foreign = create_daily_stds(other, "strds", [name], 3, map_prefix=f"{prefix}_o")

    work.t_rename(input=name, output=f"{prefix}_new")

    assert len(_names(work, f"{prefix}_new")) == 2
    # The dataset of the other mapset keeps its name and its three maps.
    assert _names(other, name) == foreign


def test_a_name_that_only_the_other_mapset_uses_is_free(two_mapsets, prefix):
    work, other = two_mapsets
    create_daily_stds(other, "strds", [f"{prefix}_taken"], 1, map_prefix=f"{prefix}_o")
    maps = create_daily_stds(work, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    work.t_rename(input=f"{prefix}_ds", output=f"{prefix}_taken")

    assert _names(work, f"{prefix}_taken") == maps
    assert len(_names(other, f"{prefix}_taken")) == 1
