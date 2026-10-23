"""Test the selection of maps and the output options of t.rast.neighbors

where, suffix, basename, nprocs, region_relation, -r, selection, the
semantic labels, -n and -e. The datasets are those of conftest.py: "daily"
holds the ramp plus 0, 10, 20 and 30 on four consecutive days, so the centre
of the 3 x 3 average of map k is 5 + 10 k.
"""

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    register_stds,
    small_region,
)
from grass.temporal.testing.readback import (
    cell_values,
    list_maps,
    message,
    stds_info,
)
from grass.tools import ToolError

# Most tests make several maps and datasets, which takes more than a second
# (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _maps(tools, name):
    return [row.name for row in list_maps(tools, "strds", name)]


def _centres(tools, name):
    return [cell_values(tools, row)[4] for row in _maps(tools, name)]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01_01", "2001_01_02", "2001_01_03", "2001_01_04"]),
        (
            "time",
            [
                "2001_01_01T00_00_00",
                "2001_01_02T00_00_00",
                "2001_01_03T00_00_00",
                "2001_01_04T00_00_00",
            ],
        ),
        ("num", ["00001", "00002", "00003", "00004"]),
        ("num%03", ["001", "002", "003", "004"]),
    ],
)
def test_the_suffix_of_the_new_maps(tools, daily, prefix, suffix, names):
    tools.t_rast_neighbors(
        input=daily, output=prefix, basename=f"{prefix}_b", suffix=suffix
    )

    assert _maps(tools, prefix) == [f"{prefix}_b_{name}" for name in names]
    assert _centres(tools, prefix) == [5.0, 15.0, 25.0, 35.0]


def test_where_selects_the_maps(tools, daily, prefix):
    # The maps of the second and third day.
    tools.t_rast_neighbors(
        input=daily,
        output=prefix,
        basename=prefix,
        where="start_time >= '2001-01-02' and start_time < '2001-01-04'",
    )

    assert _maps(tools, prefix) == [f"{prefix}_2001_01_02", f"{prefix}_2001_01_03"]
    assert _centres(tools, prefix) == [15.0, 25.0]


def test_the_output_has_the_times_and_type_of_the_input(tools, daily, prefix):
    tools.t_rast_neighbors(input=daily, output=prefix, basename=prefix)

    rows = list_maps(tools, "strds", prefix)
    assert [(row.start, row.end) for row in rows] == [
        ("2001-01-0%d 00:00:00" % (k + 1), "2001-01-0%d 00:00:00" % (k + 2))
        for k in range(4)
    ]
    info = stds_info(tools, "strds", prefix)
    assert (info["temporal_type"], info["number_of_maps"]) == ("absolute", 4)


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_nprocs_gives_the_same_maps(tools, daily, prefix, nprocs):
    tools.t_rast_neighbors(
        input=daily, output=prefix, basename=prefix, nprocs=nprocs, size=5
    )

    # A window of 5 sees the whole map: its mean is 5 + 10 k everywhere.
    assert [cell_values(tools, name) for name in _maps(tools, prefix)] == [
        [5.0 + 10 * k] * 9 for k in range(4)
    ]


def test_a_selection_limits_the_cells_that_are_computed(tools, spike, prefix):
    # Only the centre is selected: it takes the mean of its window (70 / 9);
    # every other cell keeps its input value.
    small_region(tools, 3, 3)
    tools.r_mapcalc(
        expression=f"{prefix}_sel = if(row() == 2 && col() == 2, 1, null())"
    )

    tools.t_rast_neighbors(
        input=spike, output=prefix, basename=prefix, selection=f"{prefix}_sel"
    )

    (name,) = _maps(tools, prefix)
    assert cell_values(tools, name) == pytest.approx(
        [40.0, 0.0, 0.0, 0.0, 70 / 9, 20.0, 0.0, 0.0, 0.0]
    )


def _labels(tools, name):
    return stds_info(tools, "strds", name)["semantic_labels"]


def test_the_labels_of_the_input_are_copied_by_default(tools, ramp, prefix):
    tools.t_rast_neighbors(input=ramp, output=prefix, basename=prefix)

    assert _labels(tools, prefix) == "LBL_1"


def test_the_method_name_is_appended_to_a_label(tools, ramp, prefix):
    tools.t_rast_neighbors(
        input=ramp,
        output=prefix,
        basename=prefix,
        method="maximum",
        semantic_labels="method",
    )

    assert _labels(tools, prefix) == "LBL_1_maximum"


def test_the_method_name_is_the_label_of_a_map_without_one(tools, daily, prefix):
    # No input label, so the label of every output map is the method name.
    tools.t_rast_neighbors(
        input=daily,
        output=prefix,
        basename=prefix,
        method="minimum",
        semantic_labels="method",
    )

    assert _labels(tools, prefix) == "minimum"


def test_maps_without_a_label_get_none_by_default(tools, daily, prefix):
    tools.t_rast_neighbors(input=daily, output=prefix, basename=prefix)

    assert _labels(tools, prefix) == "None"


@pytest.fixture(scope="module")
def regions(tools):
    """Five maps of one day each with regions of their own; returns the dataset

    The current region is 0 to 3 in both directions. The maps are
    inside (1 to 2), equal (0 to 3), larger (-1 to 5), far away (10 to 13)
    and overlapping (2 to 5), in the order of the days 0 to 4. Each holds
    row() + col() of its own region.
    """
    specs = [
        ("nbr_in", (2, 1, 2, 1)),
        ("nbr_eq", (3, 0, 3, 0)),
        ("nbr_big", (5, -1, 5, -1)),
        ("nbr_far", (13, 10, 13, 10)),
        ("nbr_over", (5, 2, 5, 2)),
    ]
    for name, (north, south, east, west) in specs:
        tools.g_region(n=north, s=south, e=east, w=west, res=1)
        tools.r_mapcalc(expression=f"{name} = double(row() + col())")
    small_region(tools, 3, 3)
    register_stds(
        tools,
        "strds",
        "nbr_regions",
        [MapSpec(name, None, day(k), day(k + 1)) for k, (name, _) in enumerate(specs)],
    )
    return "nbr_regions"


@pytest.mark.parametrize(
    ("relation", "days"),
    [
        # The maps that touch the region: inside, equal, larger, overlapping.
        ("overlaps", [0, 1, 2, 4]),
        # The maps that contain the region: the equal and the larger one.
        ("contains", [1, 2]),
        # The maps inside the region: the small one and the equal one.
        ("is_contained", [0, 1]),
    ],
)
def test_region_relation_selects_the_maps_by_their_extent(
    tools, regions, prefix, relation, days
):
    tools.t_rast_neighbors(
        input=regions, output=prefix, basename=prefix, region_relation=relation
    )

    assert _maps(tools, prefix) == [f"{prefix}_2001_01_0{day + 1}" for day in days]


def test_no_relation_takes_every_map_but_drops_the_empty_result(tools, regions, prefix):
    # The far map has no cell in the region, so its result is null everywhere
    # and is not registered; with -n it is.
    tools.t_rast_neighbors(input=regions, output=prefix, basename=prefix)
    assert _maps(tools, prefix) == [f"{prefix}_2001_01_0{n}" for n in (1, 2, 3, 5)]

    tools.t_rast_neighbors(
        input=regions, output=f"{prefix}_n", basename=f"{prefix}_n", flags="n"
    )
    assert len(_maps(tools, f"{prefix}_n")) == 5


def _size(tools, name):
    info = tools.r_info(map=name, flags="g").keyval
    return info["rows"], info["cols"]


def test_the_outputs_have_the_current_region_by_default(tools, regions, prefix):
    tools.t_rast_neighbors(
        input=regions, output=prefix, basename=prefix, region_relation="overlaps"
    )

    assert [_size(tools, name) for name in _maps(tools, prefix)] == [(3, 3)] * 4


def test_the_r_flag_takes_the_region_of_each_map(tools, regions, prefix):
    # The maps cover 1, 3, 6 and 3 rows and columns (the inside map, the equal
    # one, the larger one from -1 to 5, and the overlapping one from 2 to 5).
    tools.t_rast_neighbors(
        input=regions,
        output=prefix,
        basename=prefix,
        region_relation="overlaps",
        nprocs=2,
        flags="r",
    )

    assert [_size(tools, name) for name in _maps(tools, prefix)] == [
        (1, 1),
        (3, 3),
        (6, 6),
        (3, 3),
    ]
    # The run leaves the current region alone.
    region = tools.g_region(flags="g").keyval
    assert (region["rows"], region["cols"]) == (3, 3)


@pytest.fixture(scope="module")
def with_a_null_map(tools):
    """Two maps: one without a value in any cell, then the ramp"""
    small_region(tools, 3, 3)
    create_stds(
        tools,
        "strds",
        "nbr_nulls",
        [
            MapSpec("nbr_empty", "double(null())", day(0), day(1)),
            MapSpec("nbr_full", "double((row() - 1) * 3 + col())", day(1), day(2)),
        ],
    )
    return "nbr_nulls"


def test_empty_results_are_dropped_by_default(tools, with_a_null_map, prefix):
    tools.t_rast_neighbors(input=with_a_null_map, output=prefix, basename=prefix)

    assert _maps(tools, prefix) == [f"{prefix}_2001_01_02"]
    assert tools.g_list(type="raster", pattern=f"{prefix}_*").stdout.split() == [
        f"{prefix}_2001_01_02"
    ]


def test_the_n_flag_registers_empty_results(tools, with_a_null_map, prefix):
    tools.t_rast_neighbors(
        input=with_a_null_map, output=prefix, basename=prefix, flags="n"
    )

    rows = list_maps(tools, "strds", prefix)
    assert [(row.name, row.min) for row in rows] == [
        (f"{prefix}_2001_01_01", None),
        (f"{prefix}_2001_01_02", 3.0),
    ]


def test_extend_adds_maps_to_an_existing_dataset(tools, daily, prefix):
    # With overwrite and -e the existing dataset keeps its maps and gets the
    # new ones; the map of the second day is made again.
    options = {"input": daily, "output": prefix, "basename": prefix}
    tools.t_rast_neighbors(where="start_time < '2001-01-03'", **options)

    tools.t_rast_neighbors(
        where="start_time >= '2001-01-02' and start_time < '2001-01-04'",
        flags="e",
        overwrite=True,
        **options,
    )

    assert _maps(tools, prefix) == [f"{prefix}_2001_01_0{n}" for n in (1, 2, 3)]
    assert _centres(tools, prefix) == [5.0, 15.0, 25.0]


def test_without_extend_overwrite_replaces_the_dataset(tools, daily, prefix):
    options = {"input": daily, "output": prefix, "basename": prefix}
    tools.t_rast_neighbors(where="start_time < '2001-01-03'", **options)

    result = tools.t_rast_neighbors(
        where="start_time >= '2001-01-04'", overwrite=True, **options
    )

    assert "Overwriting space time raster dataset" in message(result)
    assert _maps(tools, prefix) == [f"{prefix}_2001_01_04"]


def test_extend_adds_maps_to_an_existing_dataset_without_overwrite(
    tools, daily, prefix
):
    options = {"input": daily, "output": prefix, "basename": prefix}
    tools.t_rast_neighbors(where="start_time < '2001-01-03'", **options)
    assert len(_maps(tools, prefix)) == 2

    tools.t_rast_neighbors(where="start_time >= '2001-01-03'", flags="e", **options)

    # Two maps before and the two of the third and fourth day.
    assert _maps(tools, prefix) == [f"{prefix}_2001_01_0{n}" for n in (1, 2, 3, 4)]
    assert _centres(tools, prefix) == [5.0, 15.0, 25.0, 35.0]


def test_extend_makes_a_new_dataset_when_there_is_none(tools, daily, prefix):
    tools.t_rast_neighbors(
        input=daily,
        output=prefix,
        basename=prefix,
        where="start_time < '2001-01-03'",
        flags="e",
    )

    assert _maps(tools, prefix) == [f"{prefix}_2001_01_0{n}" for n in (1, 2)]


def test_extend_refuses_an_existing_map_without_overwrite_and_writes_nothing(
    tools, daily, prefix
):
    # The dataset holds the map of the third day. The second run selects the
    # first three days, so the maps of the first and second day are new and
    # the third, the last one of the run, exists.
    options = {"input": daily, "output": prefix, "basename": prefix}
    tools.t_rast_neighbors(
        where="start_time >= '2001-01-03' and start_time < '2001-01-04'", **options
    )
    before = _maps(tools, prefix)
    rasters = tools.g_list(type="raster", pattern=f"{prefix}_*").stdout.split()
    assert before == [f"{prefix}_2001_01_03"]

    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(where="start_time < '2001-01-04'", flags="e", **options)

    assert f"Map <{prefix}_2001_01_03@PERMANENT> is already in temporal database" in (
        message(error.value)
    )
    assert _maps(tools, prefix) == before
    assert tools.g_list(type="raster", pattern=f"{prefix}_*").stdout.split() == rasters


def test_an_existing_dataset_is_refused_without_extend_and_overwrite(
    tools, daily, prefix
):
    options = {"input": daily, "output": prefix, "basename": prefix}
    tools.t_rast_neighbors(where="start_time < '2001-01-03'", **options)

    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(where="start_time >= '2001-01-03'", **options)

    assert (
        f"Space time raster dataset <{prefix}> is already in the database"
        in message(error.value)
    )
    assert len(_maps(tools, prefix)) == 2
