"""Test the flags -m and -u of t.support: the dataset follows its maps

The dataset has three maps (see the make_dataset fixture): map n lasts one
day from 2001-01-0n to 2001-01-0(n+1), holds the value 10 n (a vector map the
point (n, n)), on a region of one cell from 0,0 to 1,1.

-m reads the maps from the mapset again, unregisters those that are gone and
updates every other dataset that holds a map it read or removed (since
18.10.2026, before only for removed maps);
-u updates the dataset from the entries of the registered maps in the
temporal database; the flag itself is ignored by the tool, but every call
does it (pinned below).
"""

import sqlite3

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, make_map
from grass.temporal.testing.readback import list_maps, message, stds_info

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

BIG = {"n": 2, "s": 0, "e": 2, "w": 0, "res": 2, "b": 0, "t": 1, "res3": 1}


@pytest.mark.parametrize(
    ("stds_type", "map_type"), [("strds", "raster"), ("str3ds", "raster_3d")]
)
def test_m_reads_the_new_values_of_the_maps(tools, make_dataset, stds_type, map_type):
    name, maps = make_dataset(stds_type)
    before = stds_info(tools, stds_type, name)
    assert (before["min_min"], before["max_max"]) == (10, 30)
    # The old test replaced the values 100..400 by 10..40; here 10..30 by 1..3.
    for number, map_name in enumerate(maps, 1):
        make_map(tools, map_type, map_name, number, overwrite=True)

    tools.t_support(type=stds_type, input=name, flags="m")

    info = stds_info(tools, stds_type, name)
    assert (info["min_min"], info["min_max"]) == (1, 3)
    assert (info["max_min"], info["max_max"]) == (1, 3)
    assert info["number_of_maps"] == 3


def test_without_m_the_dataset_keeps_the_old_values(tools, make_dataset):
    name, maps = make_dataset()
    make_map(tools, "raster", maps[0], 1, overwrite=True)

    tools.t_support(input=name, title="Only the title")

    assert stds_info(tools, "strds", name)["min_min"] == 10


def test_m_reads_the_extent_and_resolution_of_the_maps(tools, make_dataset):
    name, maps = make_dataset()
    # The first map is made again on a region of one cell of 2 by 2.
    make_map(tools, "raster", maps[0], 1, region=BIG, overwrite=True)

    tools.t_support(input=name, flags="m")

    info = stds_info(tools, "strds", name)
    assert (info["north"], info["south"], info["east"], info["west"]) == (2, 0, 2, 0)
    # Two maps of cells of 1 and one of 2.
    assert (info["nsres_min"], info["nsres_max"]) == (1, 2)
    assert (info["ewres_min"], info["ewres_max"]) == (1, 2)


def test_m_reads_the_extent_of_a_vector_map(tools, make_dataset):
    name, maps = make_dataset("stvds")
    before = stds_info(tools, "stvds", name)
    # The points are at (1,1), (2,2) and (3,3); the first moves to (7,7).
    assert (before["north"], before["south"]) == (3, 1)
    make_map(tools, "vector", maps[0], 7, overwrite=True)

    tools.t_support(type="stvds", input=name, flags="m")

    info = stds_info(tools, "stvds", name)
    assert (info["north"], info["south"], info["east"], info["west"]) == (7, 2, 7, 2)


def test_m_unregisters_a_map_that_is_gone(tools, make_dataset):
    name, maps = make_dataset()
    tools.g_remove(type="raster", name=maps[2], flags="f")

    tools.t_support(input=name, flags="m")

    # The values 10 and 20 of the maps that are left; map 2 ends on day 2.
    info = stds_info(tools, "strds", name)
    assert info["number_of_maps"] == 2
    assert (info["min_min"], info["max_max"]) == (10, 20)
    assert info["end_time"] == "'2001-01-03 00:00:00'"
    assert [row.name for row in list_maps(tools, "strds", name)] == maps[:2]


def test_m_updates_every_dataset_that_held_the_missing_map(tools, prefix):
    # The former shell test: two datasets register the same six maps, three
    # of them are removed, both datasets must lose them.
    specs = [MapSpec(f"{prefix}_{n}", n, day(n - 1), day(n)) for n in range(1, 7)]
    create_stds(tools, "strds", f"{prefix}_a", specs)
    tools.t_create(output=f"{prefix}_b", title="b", description="b")
    tools.t_register(
        input=f"{prefix}_b",
        maps=",".join(spec.name for spec in specs),
        start="2001-01-01",
        increment="1 days",
        flags="i",
        overwrite=True,
    )
    tools.g_remove(type="raster", name=",".join(s.name for s in specs[:3]), flags="f")

    tools.t_support(input=f"{prefix}_a", flags="m")

    for dataset in (f"{prefix}_a", f"{prefix}_b"):
        info = stds_info(tools, "strds", dataset)
        assert info["number_of_maps"] == 3
        assert info["start_time"] == "'2001-01-04 00:00:00'"
        assert info["end_time"] == "'2001-01-07 00:00:00'"
    assert not set(tools.t_list(type="raster", columns="name").stdout.split()) & {
        spec.name for spec in specs[:3]
    }


def test_m_sets_the_semantic_type_to_mean(tools, make_dataset):
    # The same default as for the options: see t_support_metadata_test.py.
    name, _ = make_dataset()
    tools.t_support(input=name, semantictype="sum")

    tools.t_support(input=name, flags="m")

    assert stds_info(tools, "strds", name)["semantic_type"] == "mean"


def _two_datasets(tools, prefix):
    """Datasets A and B register the same maps 1 to 3 with the values 1, 2, 3"""
    specs = [MapSpec(f"{prefix}_{n}", n, day(n - 1), day(n)) for n in (1, 2, 3)]
    create_stds(tools, "strds", f"{prefix}_a", specs)
    tools.t_create(output=f"{prefix}_b", title="b", description="b")
    tools.t_register(
        input=f"{prefix}_b",
        maps=",".join(spec.name for spec in specs),
        start="2001-01-01",
        increment="1 days",
        flags="i",
        overwrite=True,
    )
    return specs


def test_m_updates_every_dataset_that_holds_a_changed_map(tools, prefix):
    # Changed on 18.10.2026: map 1 is made again with the value 7; -m on A
    # reads it, and B, which holds the map too, follows. The entries hold 7,
    # 2 and 3, so B reports the smallest minimum 2 and the largest maximum 7.
    specs = _two_datasets(tools, prefix)
    make_map(tools, "raster", specs[0].name, 7, overwrite=True)

    tools.t_support(input=f"{prefix}_a", flags="m")

    for dataset in (f"{prefix}_a", f"{prefix}_b"):
        info = stds_info(tools, "strds", dataset)
        assert (info["min_min"], info["max_max"]) == (2, 7), dataset


def _stale_dataset(tools, prefix):
    """A dataset whose metadata lags behind the entries of its maps

    Datasets A and B register the same maps 1 to 3 with the values 1, 2 and 3.
    Map 1 is made again with the value 7 and read by t.support -m A, which
    updates B as well. The state "metadata lags behind" no longer arises that
    way, so the metadata of B is set back to the values 1 to 3 in the
    temporal database: B reports 1 and 3 while the entries hold 7, 2 and 3.
    """
    specs = _two_datasets(tools, prefix)
    make_map(tools, "raster", specs[0].name, 7, overwrite=True)
    tools.t_support(input=f"{prefix}_a", flags="m")
    base = tools.g_gisenv(get="GISDBASE").stdout.strip()
    project = tools.g_gisenv(get="LOCATION_NAME").stdout.strip()
    mapset = tools.g_gisenv(get="MAPSET").stdout.strip()
    with sqlite3.connect(f"{base}/{project}/{mapset}/tgis/sqlite.db") as database:
        database.execute(
            "UPDATE strds_metadata SET min_min = 1, max_max = 3 WHERE id = ?",
            (f"{prefix}_b@{mapset}",),
        )
    assert stds_info(tools, "strds", f"{prefix}_a")["max_max"] == 7
    stale = stds_info(tools, "strds", f"{prefix}_b")
    assert (stale["min_min"], stale["max_max"]) == (1, 3)
    return f"{prefix}_b"


# The entries hold the values 7, 2 and 3: the smallest minimum is 2, the
# largest maximum 7.
REPAIRED = (2, 7)


def test_m_repairs_a_dataset_with_stale_metadata(tools, prefix):
    name = _stale_dataset(tools, prefix)

    tools.t_support(input=name, flags="m")

    info = stds_info(tools, "strds", name)
    assert (info["min_min"], info["max_max"]) == REPAIRED
    assert info["number_of_maps"] == 3


def test_u_repairs_a_dataset_with_stale_metadata(tools, prefix):
    name = _stale_dataset(tools, prefix)

    tools.t_support(input=name, flags="u")

    info = stds_info(tools, "strds", name)
    assert (info["min_min"], info["max_max"]) == REPAIRED
    assert info["number_of_maps"] == 3


def test_today_a_call_without_u_repairs_it_as_well(tools, prefix):
    # The flag is read into a variable that the next line overwrites, so it
    # makes no difference. The update comes from the default of semantictype,
    # which makes every call write the dataset (see t_support_metadata_test.py).
    name = _stale_dataset(tools, prefix)

    tools.t_support(input=name)

    info = stds_info(tools, "strds", name)
    assert (info["min_min"], info["max_max"]) == REPAIRED


def test_today_u_sets_the_semantic_type_to_mean(tools, make_dataset):
    name, _ = make_dataset()
    tools.t_support(input=name, semantictype="sum")

    tools.t_support(input=name, flags="u")

    assert stds_info(tools, "strds", name)["semantic_type"] == "mean"


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_u_keeps_the_semantic_type(tools, make_dataset):
    name, _ = make_dataset()
    tools.t_support(input=name, semantictype="sum")

    tools.t_support(input=name, flags="u")

    assert stds_info(tools, "strds", name)["semantic_type"] == "sum"


def test_u_does_not_read_the_maps_again(tools, make_dataset):
    # -u works on the entries of the temporal database, not on the maps.
    name, maps = make_dataset()
    make_map(tools, "raster", maps[0], 1, overwrite=True)

    tools.t_support(input=name, flags="u")

    assert stds_info(tools, "strds", name)["min_min"] == 10


def test_m_reports_its_progress_every_ten_maps(tools, make_stds):
    maps, (name,) = make_stds(10)

    result = tools.t_support(input=name, flags="m")

    assert "100%" in message(result)
    assert stds_info(tools, "strds", name)["number_of_maps"] == 10
