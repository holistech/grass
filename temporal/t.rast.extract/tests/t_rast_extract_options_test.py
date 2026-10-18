"""Test the options of t.rast.extract on six quarterly maps

where, expression, basename, suffix, nprocs and -n. The maps hold 100 to 600
and cover the quarters from 2001-01-01 to 2002-07-01 (conftest.py). The
comparisons of the old suite are kept with all their keys.
"""

import pytest

from grass.temporal.testing.readback import list_maps, message, stds_info

# The keys the old suite compared, for datasets of this region.
REGION = {
    "north": 1.0,
    "south": 0.0,
    "east": 2.0,
    "west": 0.0,
    "top": 0.0,
    "bottom": 0.0,
    "nsres_min": 1.0,
    "nsres_max": 1.0,
    "ewres_min": 1.0,
    "ewres_max": 1.0,
    "granularity": "'3 months'",
    "map_time": "interval",
    "aggregation_type": "None",
}
LARGE = "if(ext_quarterly > 400, ext_quarterly, null())"


def _check(tools, name, expected):
    info = stds_info(tools, "strds", name)
    for key, value in {**REGION, **expected}.items():
        assert info[key] == value, f"{key}: expected {value!r}, got {info[key]!r}"


def _maps(tools, name):
    return [(row.name, row.start, row.min) for row in list_maps(tools, "strds", name)]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_selection_keeps_the_maps(tools, quarterly, prefix):
    # start_time > '2001-06-01' selects the maps that start on 2001-07-01,
    # 2001-10-01, 2002-01-01 and 2002-04-01: 300, 400, 500, 600, the last
    # ending on 2002-07-01. Without an expression the maps are not copied.
    tools.t_rast_extract(
        input=quarterly, output=prefix, where="start_time > '2001-06-01'"
    )

    _check(
        tools,
        prefix,
        {
            "start_time": "'2001-07-01 00:00:00'",
            "end_time": "'2002-07-01 00:00:00'",
            "number_of_maps": 4,
            "min_min": 300.0,
            "min_max": 600.0,
            "max_min": 300.0,
            "max_max": 600.0,
        },
    )
    assert [name for name, _, _ in _maps(tools, prefix)] == [
        "ext_q3",
        "ext_q4",
        "ext_q5",
        "ext_q6",
    ]


def test_the_extracted_dataset_keeps_type_and_description(tools, quarterly, prefix):
    tools.t_rast_extract(input=quarterly, output=prefix)

    info = stds_info(tools, "strds", prefix)
    assert info["temporal_type"] == "absolute"
    assert info["semantic_type"] == "mean"
    assert info["number_of_maps"] == 6


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_selection_and_expression(tools, quarterly, prefix):
    # Of the four selected maps (300 to 600) the expression keeps the values
    # above 400: 500 and 600 on 2002-01-01 and 2002-04-01. The maps that
    # come out empty are not registered and removed from the mapset.
    tools.t_rast_extract(
        input=quarterly,
        output=prefix,
        where="start_time > '2001-06-01'",
        expression=LARGE,
        basename=f"{prefix}_x",
        nprocs=2,
    )

    _check(
        tools,
        prefix,
        {
            "start_time": "'2002-01-01 00:00:00'",
            "end_time": "'2002-07-01 00:00:00'",
            "number_of_maps": 2,
            "min_min": 500.0,
            "min_max": 600.0,
            "max_min": 500.0,
            "max_max": 600.0,
        },
    )
    assert _maps(tools, prefix) == [
        (f"{prefix}_x_2002_01", "2002-01-01 00:00:00", 500.0),
        (f"{prefix}_x_2002_04", "2002-04-01 00:00:00", 600.0),
    ]
    listed = tools.g_list(type="raster", pattern=f"{prefix}_x_*").stdout.split()
    assert sorted(listed) == [f"{prefix}_x_2002_01", f"{prefix}_x_2002_04"]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_n_flag_registers_the_empty_maps(tools, quarterly, prefix):
    # All six maps are registered; the first four are empty (no minimum), so
    # the value range of the dataset is that of the last two.
    tools.t_rast_extract(
        input=quarterly,
        output=prefix,
        expression=LARGE,
        basename=f"{prefix}_x",
        nprocs=2,
        flags="n",
    )

    _check(
        tools,
        prefix,
        {
            "start_time": "'2001-01-01 00:00:00'",
            "end_time": "'2002-07-01 00:00:00'",
            "number_of_maps": 6,
            "min_min": 500.0,
            "min_max": 600.0,
            "max_min": 500.0,
            "max_max": 600.0,
        },
    )
    assert [row.min for row in list_maps(tools, "strds", prefix)] == [
        None,
        None,
        None,
        None,
        500.0,
        600.0,
    ]


def test_the_expression_names_the_dataset_for_every_map(tools, quarterly, prefix):
    # The dataset name in the expression stands for the map of each step, so
    # 2 * name doubles every value.
    tools.t_rast_extract(
        input=quarterly,
        output=prefix,
        expression="2 * ext_quarterly",
        basename=f"{prefix}_x",
    )

    assert [value for _, _, value in _maps(tools, prefix)] == [
        200.0,
        400.0,
        600.0,
        800.0,
        1000.0,
        1200.0,
    ]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["x_2001_01", "x_2001_04", "x_2001_07", "x_2001_10", "x_2002_01"]),
        (
            "time",
            [
                "x_2001_01_01T00_00_00",
                "x_2001_04_01T00_00_00",
                "x_2001_07_01T00_00_00",
                "x_2001_10_01T00_00_00",
                "x_2002_01_01T00_00_00",
            ],
        ),
        ("num", ["x_00001", "x_00002", "x_00003", "x_00004", "x_00005"]),
        ("num%03", ["x_001", "x_002", "x_003", "x_004", "x_005"]),
    ],
)
def test_the_suffix_of_the_new_maps(tools, quarterly, prefix, suffix, names):
    # The first five maps (100 to 500) are extracted; the name is the base
    # name, an underscore and the suffix: the granularity gives the year and
    # month of a three months interval, time the full time stamp, num a
    # counter of five digits unless the width is given.
    tools.t_rast_extract(
        input=quarterly,
        output=prefix,
        where="start_time < '2002-04-01'",
        expression="ext_quarterly",
        basename=f"{prefix}_x",
        suffix=suffix,
    )

    assert [name for name, _, _ in _maps(tools, prefix)] == [
        f"{prefix}_{name}" for name in names
    ]


@pytest.mark.parametrize("nprocs", [1, 2, 6, 8])
def test_nprocs_gives_the_same_maps(tools, quarterly, prefix, nprocs):
    tools.t_rast_extract(
        input=quarterly,
        output=prefix,
        expression=LARGE,
        basename=f"{prefix}_x",
        nprocs=nprocs,
        flags="n",
    )

    assert [row.min for row in list_maps(tools, "strds", prefix)] == [
        None,
        None,
        None,
        None,
        500.0,
        600.0,
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_dataset_and_its_maps(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": f"{prefix}_x"}
    tools.t_rast_extract(expression="ext_quarterly", **options)

    tools.t_rast_extract(
        expression="-ext_quarterly",
        where="start_time < '2001-07-01'",
        overwrite=True,
        **options,
    )

    assert [value for _, _, value in _maps(tools, prefix)] == [-100.0, -200.0]
    assert stds_info(tools, "strds", prefix)["number_of_maps"] == 2


def test_a_selection_that_finds_no_map_warns_and_makes_no_dataset(
    tools, quarterly, prefix
):
    result = tools.t_rast_extract(
        input=quarterly, output=prefix, where="start_time > '2030-01-01'"
    )

    assert (
        f"Nothing found in the database for space time dataset <{quarterly}> "
        "(type: raster): Dataset is empty or where clause is too constrained or "
        "incorrect"
    ) in message(result)
    assert tools.t_list(type="strds", columns="name").stdout.count(prefix) == 0


def test_an_empty_dataset_warns_without_the_hint_on_where(tools, quarterly, prefix):
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output=f"{prefix}_empty",
        title="empty",
        description="empty",
    )

    result = tools.t_rast_extract(input=f"{prefix}_empty", output=prefix)

    assert (
        f"Nothing found in the database for space time dataset <{prefix}_empty> "
        "(type: raster): Dataset is empty"
    ) in message(result)
    assert "where clause" not in message(result)
