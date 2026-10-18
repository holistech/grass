"""Test t.info for maps and datasets of another mapset

A temporal database belongs to a mapset: a dataset, and the maps registered in
it, are found in the database of the mapset that holds the dataset. A map of
another mapset that is registered in a dataset of the current mapset is a
different case (pinned below).
"""

import pytest

from grass.temporal.testing.data import create_daily_stds, make_map
from grass.temporal.testing.readback import message
from grass.tools import ToolError


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_dataset_of_another_mapset(two_mapsets, prefix):
    work, other = two_mapsets
    create_daily_stds(other, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    info = work.t_info(type="strds", input=f"{prefix}_ds@other", flags="g").keyval

    assert info["id"] == f"{prefix}_ds@other"
    assert info["mapset"] == "other"
    assert info["number_of_maps"] == 2


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_map_in_a_dataset_of_its_own_mapset(two_mapsets, prefix):
    work, other = two_mapsets
    maps = create_daily_stds(other, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    info = work.t_info(type="raster", input=f"{maps[0]}@other", flags="g").keyval

    assert info["id"] == f"{maps[0]}@other"
    assert info["mapset"] == "other"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_name_without_a_mapset_is_taken_from_the_current_one(two_mapsets, prefix):
    work, other = two_mapsets
    maps = create_daily_stds(other, "strds", [f"{prefix}_ds"], 2, map_prefix=prefix)

    with pytest.raises(ToolError) as error:
        work.t_info(type="raster", input=maps[0], flags="g")

    assert f"Dataset <{maps[0]}@work> of type <raster> not found" in message(
        error.value
    )


@pytest.fixture
def foreign_map(two_mapsets, prefix):
    """A map of mapset other that a dataset of mapset work registers"""
    work, other = two_mapsets
    make_map(other, "raster", f"{prefix}_loose", 1)
    # Without a dataset the mapset has no temporal database, which t.info
    # reports with another message.
    other.t_create(output=f"{prefix}_other_ds", title="t", description="d")
    work.t_create(output=f"{prefix}_ds", title="t", description="d")
    work.t_register(
        input=f"{prefix}_ds", maps=f"{prefix}_loose@other", start="2001-01-01"
    )
    return f"{prefix}_loose@other"


def test_the_registration_of_a_foreign_map_is_listed(two_mapsets, prefix, foreign_map):
    work, _ = two_mapsets

    result = work.t_rast_list(input=f"{prefix}_ds", columns="name,mapset")

    assert result.text_split("\n") == ["name|mapset", f"{prefix}_loose|other"]


def test_today_t_info_does_not_find_a_foreign_map_registered_in_the_current_mapset(
    two_mapsets, foreign_map
):
    # t.info looks in the database of the mapset in the name, and the entry is
    # in the database of the mapset that registered the map.
    work, _ = two_mapsets

    with pytest.raises(ToolError) as error:
        work.t_info(type="raster", input=foreign_map, flags="g")

    assert (
        f"Dataset <{foreign_map}> of type <raster> not found in temporal database"
        in (message(error.value))
    )


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_t_info_finds_a_foreign_map_registered_in_the_current_mapset(
    two_mapsets, foreign_map
):
    work, _ = two_mapsets

    info = work.t_info(type="raster", input=foreign_map, flags="g").keyval

    assert info["id"] == foreign_map
