"""Test t.copy with a dataset of another mapset: the maps stay or are copied

The source dataset <prefix>_src belongs to the mapset "other" and holds three
maps made there, map n with the value n from day n-1 to day n. The tests run
in the mapset "work", which has "other" in its search path. The output must
be in the current mapset.
"""

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError

# Every test makes maps and datasets with tools, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _rows(tools, name, stds_type="strds"):
    """(name, mapset) of the maps of a dataset, from t.rast.list"""
    tool = {"strds": "t_rast_list", "str3ds": "t_rast3d_list", "stvds": "t_vect_list"}
    result = getattr(tools, tool[stds_type])(
        input=name, columns="name,mapset", format="json"
    )
    return [(row["name"], row["mapset"]) for row in result.json["data"]]


@pytest.fixture
def source(two_mapsets, prefix):
    """The dataset <prefix>_src of mapset other and the names of its maps"""
    maps = create_daily_stds(
        two_mapsets.other, "strds", [f"{prefix}_src"], 3, map_prefix=prefix
    )
    return f"{prefix}_src", maps


def test_the_copy_refers_to_the_maps_of_the_other_mapset(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, maps = source

    work.t_copy(input=f"{name}@other", output=f"{prefix}_copy")

    assert _rows(work, f"{prefix}_copy") == [(m, "other") for m in maps]
    # Without -c no map is copied.
    assert set(work.g_list(type="raster", mapset="work").stdout.split()).isdisjoint(
        maps
    )
    assert [row.name for row in list_maps(other, "strds", name)] == maps


def test_c_copies_the_maps_into_the_current_mapset(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, maps = source

    result = work.t_copy(input=f"{name}@other", output=f"{prefix}_copy", flags="c")

    assert "Copying raster maps to the current mapset" in message(result)
    assert _rows(work, f"{prefix}_copy") == [(m, "work") for m in maps]
    assert set(maps) <= set(work.g_list(type="raster", mapset="work").stdout.split())
    # The copies hold the values of the originals, 1 to 3, and their times.
    rows = list_maps(work, "strds", f"{prefix}_copy")
    assert [(r.min, r.max) for r in rows] == [(1, 1), (2, 2), (3, 3)]
    assert [(r.start, r.end) for r in rows] == [
        ("2001-01-01 00:00:00", "2001-01-02 00:00:00"),
        ("2001-01-02 00:00:00", "2001-01-03 00:00:00"),
        ("2001-01-03 00:00:00", "2001-01-04 00:00:00"),
    ]
    # The originals and their dataset are as they were.
    assert set(maps) <= set(other.g_list(type="raster", mapset="other").stdout.split())
    assert [row.name for row in list_maps(other, "strds", name)] == maps


def test_c_refuses_a_map_that_exists_in_the_current_mapset(two_mapsets, prefix, source):
    work, _ = two_mapsets
    name, maps = source
    work.r_mapcalc(expression=f"{maps[1]} = 9")

    with pytest.raises(
        ToolError, match=r"exists\s+already\s+in\s+the\s+current\s+mapset"
    ):
        work.t_copy(input=f"{name}@other", output=f"{prefix}_copy", flags="c")

    assert f"{prefix}_copy" not in work.t_list(type="strds", columns="name").stdout


def test_an_input_without_a_mapset_is_found_in_the_search_path(
    two_mapsets, prefix, source
):
    work, _ = two_mapsets
    name, maps = source

    work.t_copy(input=name, output=f"{prefix}_copy")

    assert _rows(work, f"{prefix}_copy") == [(m, "other") for m in maps]


def test_the_output_may_name_the_current_mapset(two_mapsets, prefix, source):
    work, _ = two_mapsets
    name, maps = source

    work.t_copy(input=name, output=f"{prefix}_copy@work")

    assert len(_rows(work, f"{prefix}_copy")) == 3


def test_the_output_in_another_mapset_is_refused(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, _ = source

    with pytest.raises(ToolError, match=r"must\s+be\s+in\s+the\s+current\s+mapset"):
        work.t_copy(input=name, output=f"{prefix}_copy@other")

    assert f"{prefix}_copy" not in other.t_list(type="strds", columns="name").stdout


def test_the_refusal_names_the_output(two_mapsets, prefix, source):
    work, _ = two_mapsets
    name, _ = source

    with pytest.raises(ToolError) as error:
        work.t_copy(input=f"{name}@other", output=f"{prefix}_copy@other")

    assert f"The output dataset <{prefix}_copy@other>" in " ".join(
        str(error.value).split()
    )


@pytest.mark.parametrize(
    ("stds_type", "map_type"), [("str3ds", "raster_3d"), ("stvds", "vector")]
)
def test_a_failed_c_does_not_copy_any_map(two_mapsets, prefix, stds_type, map_type):
    work, other = two_mapsets
    maps = create_daily_stds(other, stds_type, [f"{prefix}_src"], 2, map_prefix=prefix)
    # The second map exists in the current mapset already, so -c has to refuse;
    # the first map must not have been copied by then.
    work.g_copy(**{map_type: f"{maps[1]}@other,{maps[1]}"})

    with pytest.raises(ToolError) as error:
        work.t_copy(
            type=stds_type,
            input=f"{prefix}_src@other",
            output=f"{prefix}_copy",
            flags="c",
        )

    assert "exists already in the current mapset" in message(error.value)
    assert work.g_list(type=map_type, mapset="work").stdout.split() == [maps[1]]
    assert f"{prefix}_copy" not in work.t_list(type=stds_type, columns="name").stdout


@pytest.mark.parametrize(
    ("stds_type", "map_type"), [("str3ds", "raster_3d"), ("stvds", "vector")]
)
def test_c_copies_3d_and_vector_maps_into_the_current_mapset(
    two_mapsets, prefix, stds_type, map_type
):
    work, other = two_mapsets
    maps = create_daily_stds(other, stds_type, [f"{prefix}_src"], 2, map_prefix=prefix)

    work.t_copy(
        type=stds_type, input=f"{prefix}_src@other", output=f"{prefix}_copy", flags="c"
    )

    assert _rows(work, f"{prefix}_copy", stds_type) == [(m, "work") for m in maps]
    copied = work.g_list(type=map_type, mapset="work", pattern=f"{prefix}_*")
    assert copied.stdout.split() == maps


def test_c_reports_its_progress_every_ten_maps(two_mapsets, prefix):
    work, other = two_mapsets
    maps = create_daily_stds(other, "strds", [f"{prefix}_src"], 10, map_prefix=prefix)

    result = work.t_copy(input=f"{prefix}_src", output=f"{prefix}_copy", flags="c")

    assert "100%" in message(result)
    assert set(maps) <= set(work.g_list(type="raster", mapset="work").stdout.split())


def test_c_keeps_the_semantic_label_of_a_raster_map(two_mapsets, prefix, source):
    work, other = two_mapsets
    name, maps = source
    other.r_semantic_label(map=f"{maps[0]}@other", semantic_label="S2_1")
    # The label is in the temporal metadata only after it has been read.
    other.t_support(input=f"{name}@other", flags="m")

    work.t_copy(input=f"{name}@other", output=f"{prefix}_copy", flags="c")

    labels = work.t_rast_list(
        input=f"{prefix}_copy", columns="name,semantic_label", format="json"
    ).json["data"]
    assert {row["name"]: row["semantic_label"] for row in labels} == {
        maps[0]: "S2_1",
        maps[1]: None,
        maps[2]: None,
    }
    # The copy of the map carries the label itself, not only its entry.
    # r.semantic.label prints the description of the label S2_1.
    printed = work.r_semantic_label(map=f"{maps[0]}@work", operation="print")
    assert "Coastal/Aerosol" in printed.stdout
