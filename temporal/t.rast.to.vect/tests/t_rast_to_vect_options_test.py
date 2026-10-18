"""Test the dataset options and flags of t.rast.to.vect on five quarterly maps

The maps hold the constant values 100 to 400 on the nine cells and, in the
fifth, no value (conftest.py). Every constant map gives nine points, or one
area with one boundary, one centroid and one node; the map without values
gives nothing and is dropped unless the flag -n asks for it.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message, stds_info


def _numbers(tools, name):
    info = stds_info(tools, "stvds", name)
    return {
        key: info[key]
        for key in (
            "start_time",
            "end_time",
            "granularity",
            "map_time",
            "number_of_maps",
            "points",
            "primitives",
        )
    }


def _names(tools, name):
    return [row.name for row in list_maps(tools, "stvds", name)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_points_of_the_maps_with_values(tools, quarterly, prefix):
    tools.t_rast_to_vect(input=quarterly, output=prefix, basename=prefix, type="point")

    assert _numbers(tools, prefix) == {
        "start_time": "'2001-01-01 00:00:00'",
        "end_time": "'2002-01-01 00:00:00'",
        "granularity": "'3 months'",
        "map_time": "interval",
        "number_of_maps": 4,
        "points": 36,
        "primitives": 36,
    }


def test_the_n_flag_registers_the_empty_map(tools, quarterly, prefix):
    tools.t_rast_to_vect(
        input=quarterly, output=prefix, basename=prefix, type="point", flags="n"
    )

    assert _numbers(tools, prefix) == {
        "start_time": "'2001-01-01 00:00:00'",
        "end_time": "'2002-04-01 00:00:00'",
        "granularity": "'3 months'",
        "map_time": "interval",
        "number_of_maps": 5,
        "points": 36,
        "primitives": 36,
    }


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("flags", [None, "s", "n"])
def test_areas_are_one_per_map(tools, quarterly, prefix, flags):
    tools.t_rast_to_vect(
        input=quarterly, output=prefix, basename=prefix, type="area", flags=flags
    )

    info = stds_info(tools, "stvds", prefix)
    assert {
        key: info[key]
        for key in (
            "number_of_maps",
            "boundaries",
            "centroids",
            "primitives",
            "nodes",
            "areas",
            "islands",
        )
    } == {
        "number_of_maps": 5 if flags == "n" else 4,
        "boundaries": 4,
        "centroids": 4,
        "primitives": 8,
        "nodes": 4,
        "areas": 4,
        "islands": 4,
    }


def test_where_selects_the_maps(tools, quarterly, prefix):
    # The text comparison keeps a map that starts on 2001-04-01, then July,
    # October and the dropped empty map: three maps with values are left.
    tools.t_rast_to_vect(
        input=quarterly,
        output=prefix,
        basename=prefix,
        type="point",
        where="start_time > '2001-02-01'",
    )

    numbers = _numbers(tools, prefix)
    assert (numbers["start_time"], numbers["end_time"]) == (
        "'2001-04-01 00:00:00'",
        "'2002-01-01 00:00:00'",
    )
    assert (numbers["number_of_maps"], numbers["points"]) == (3, 27)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_several_empty_maps_are_dropped(tools, prefix):
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_a", "null()", day(0), day(1)),
            MapSpec(f"{prefix}_b", "7", day(1), day(2)),
            MapSpec(f"{prefix}_c", "null()", day(2), day(3)),
            MapSpec(f"{prefix}_d", "null()", day(3), day(4)),
        ],
    )

    tools.t_rast_to_vect(
        input=f"{prefix}_in", output=prefix, basename=prefix, type="point"
    )

    assert _names(tools, prefix) == [f"{prefix}_2001_01_02"]
    assert tools.g_list(type="vector", pattern=f"{prefix}_*").stdout.split() == [
        f"{prefix}_2001_01_02"
    ]


def test_an_empty_selection_makes_no_dataset(tools, quarterly, prefix):
    result = tools.t_rast_to_vect(
        input=quarterly,
        output=prefix,
        basename=prefix,
        type="point",
        where="start_time > '2010-01-01'",
        flags="n",
    )

    assert f"Space time raster dataset <{quarterly}@PERMANENT> is empty" in message(
        result
    )
    assert tools.t_list(type="stvds", format="json").stdout.count(prefix) == 0


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("nprocs", [1, 4])
def test_t_flag_makes_no_attribute_table_and_allows_nprocs(
    tools, quarterly, prefix, nprocs
):
    result = tools.t_rast_to_vect(
        input=quarterly,
        output=prefix,
        basename=prefix,
        type="point",
        flags="t",
        nprocs=nprocs,
    )

    assert "reduced to 1" not in message(result)
    assert _numbers(tools, prefix)["points"] == 36
    for name in _names(tools, prefix):
        assert tools.v_db_connect(map=name, flags="p").stdout.strip() == ""


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_nprocs_is_reduced_to_one_with_attribute_tables(tools, quarterly, prefix):
    result = tools.t_rast_to_vect(
        input=quarterly, output=prefix, basename=prefix, type="point", nprocs=4
    )

    assert "The number of parallel r.to.vect processes was reduced to 1" in " ".join(
        message(result).split()
    )
    assert _numbers(tools, prefix)["points"] == 36


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01", "2001_04", "2001_07", "2001_10"]),
        (
            "time",
            [
                "2001_01_01T00_00_00",
                "2001_04_01T00_00_00",
                "2001_07_01T00_00_00",
                "2001_10_01T00_00_00",
            ],
        ),
        ("num", ["00001", "00002", "00003", "00004"]),
        ("num%03", ["001", "002", "003", "004"]),
    ],
)
def test_the_suffix_of_the_new_maps(tools, quarterly, prefix, suffix, names):
    tools.t_rast_to_vect(
        input=quarterly,
        output=prefix,
        basename=f"{prefix}_v",
        type="point",
        suffix=suffix,
        flags="t",
    )

    assert _names(tools, prefix) == [f"{prefix}_v_{name}" for name in names]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_dataset(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": prefix}
    tools.t_rast_to_vect(**options, type="point")

    tools.t_rast_to_vect(**options, type="area", overwrite=True)

    info = stds_info(tools, "stvds", prefix)
    assert (info["number_of_maps"], info["areas"], info["points"]) == (4, 4, 0)


def test_today_the_b_flag_registers_the_empty_map_without_n(tools, quarterly, prefix):
    # Without topology the number of primitives of a map is not known (None,
    # not 0), so the map without values is not seen as empty.
    tools.t_rast_to_vect(
        input=quarterly, output=prefix, basename=prefix, type="point", flags="b"
    )

    info = stds_info(tools, "stvds", prefix)
    assert (info["number_of_maps"], info["points"]) == (5, "None")


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_the_b_flag_drops_the_empty_map_without_n(tools, quarterly, prefix):
    tools.t_rast_to_vect(
        input=quarterly, output=prefix, basename=prefix, type="point", flags="b"
    )

    assert stds_info(tools, "stvds", prefix)["number_of_maps"] == 4
