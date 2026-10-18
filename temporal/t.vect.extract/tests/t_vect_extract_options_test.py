"""Test the options of t.vect.extract on six quarterly point maps

where, expression, basename, suffix, nprocs and -n. The maps are listed in
conftest.py: map k has four points with value 10 k + i. The comparisons of
the old suites (t.info keys of the extracted datasets) are kept.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info

# Most tests take more than a second (measured 18.10.2026 with a serial
# pytest --durations=0).
pytestmark = pytest.mark.slow


def _info(tools, name):
    return stds_info(tools, "stvds", name)


def _maps(tools, name):
    return [(row.name, row.start) for row in list_maps(tools, "stvds", name)]


def _primitives(tools, name):
    """Number of points of each map of the dataset"""
    return [
        int(tools.v_info(map=row.name, flags="t").keyval["points"])
        for row in list_maps(tools, "stvds", name)
    ]


def test_a_selection_by_time_registers_the_same_maps(tools, quarterly, prefix):
    # start_time > '2001-06-01' keeps the maps that start on 2001-07-01 and
    # later: vq_3 to vq_6, four points each, the last ending on 2002-07-01.
    # Without an expression no map is copied.
    tools.t_vect_extract(
        input=quarterly, output=prefix, where="start_time > '2001-06-01'"
    )

    info = _info(tools, prefix)
    assert info["start_time"] == "'2001-07-01 00:00:00'"
    assert info["end_time"] == "'2002-07-01 00:00:00'"
    assert info["granularity"] == "'3 months'"
    assert info["map_time"] == "interval"
    assert info["number_of_maps"] == 4
    assert info["primitives"] == 16
    assert info["points"] == 16
    assert [name for name, _ in _maps(tools, prefix)] == [
        "vq_3",
        "vq_4",
        "vq_5",
        "vq_6",
    ]


def test_the_expression_selects_the_points(tools, quarterly, prefix):
    # value > 33 leaves the point with 34 in vq_3 and all points of vq_4 to
    # vq_6; vq_1 (11 to 14) and vq_2 (21 to 24) come out empty and are not
    # registered.
    tools.t_vect_extract(
        input=quarterly, output=prefix, expression="value > 33", basename=f"{prefix}_x"
    )

    assert _maps(tools, prefix) == [
        (f"{prefix}_x_2001_07", "2001-07-01 00:00:00"),
        (f"{prefix}_x_2001_10", "2001-10-01 00:00:00"),
        (f"{prefix}_x_2002_01", "2002-01-01 00:00:00"),
        (f"{prefix}_x_2002_04", "2002-04-01 00:00:00"),
    ]
    assert _primitives(tools, prefix) == [1, 4, 4, 4]
    info = _info(tools, prefix)
    assert (info["number_of_maps"], info["primitives"], info["points"]) == (4, 13, 13)


def test_empty_maps_do_not_stay_in_the_mapset(tools, quarterly, prefix):
    tools.t_vect_extract(
        input=quarterly, output=prefix, expression="value > 33", basename=f"{prefix}_x"
    )

    listed = tools.g_list(type="vector", pattern=f"{prefix}_x_*").stdout.split()
    assert sorted(listed) == [
        f"{prefix}_x_2001_07",
        f"{prefix}_x_2001_10",
        f"{prefix}_x_2002_01",
        f"{prefix}_x_2002_04",
    ]


def test_the_n_flag_registers_the_empty_maps(tools, quarterly, prefix):
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        expression="value > 33",
        basename=f"{prefix}_x",
        flags="n",
    )

    assert _primitives(tools, prefix) == [0, 0, 1, 4, 4, 4]
    assert _info(tools, prefix)["number_of_maps"] == 6


def test_selection_and_expression_together(tools, quarterly, prefix):
    # From the maps that start in 2001-05-01 or later (vq_3 to vq_6),
    # value > 33 leaves 1 + 4 + 4 + 4 points.
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        where="start_time >= '2001-05-01'",
        expression="value > 33",
        basename=f"{prefix}_x",
    )

    assert _primitives(tools, prefix) == [1, 4, 4, 4]


def test_the_expression_can_use_a_float_column(tools, quarterly, prefix):
    # height = 1.5 i: height > 3 leaves the points 3 and 4 of every map
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        where="start_time < '2001-04-02'",
        expression="height > 3",
        basename=f"{prefix}_x",
    )

    assert _primitives(tools, prefix) == [2, 2]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["x_2001_01", "x_2001_04", "x_2001_07", "x_2001_10"]),
        (
            "time",
            [
                "x_2001_01_01T00_00_00",
                "x_2001_04_01T00_00_00",
                "x_2001_07_01T00_00_00",
                "x_2001_10_01T00_00_00",
            ],
        ),
        ("num", ["x_00001", "x_00002", "x_00003", "x_00004"]),
        ("num%03", ["x_001", "x_002", "x_003", "x_004"]),
    ],
)
def test_the_suffix_of_the_new_maps(tools, quarterly, prefix, suffix, names):
    # The first four maps are extracted with a condition that all points meet
    # (value > 0): the name is the base name, an underscore and the suffix.
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        where="start_time < '2002-01-01'",
        expression="value > 0",
        basename=f"{prefix}_x",
        suffix=suffix,
    )

    assert [name for name, _ in _maps(tools, prefix)] == [
        f"{prefix}_{name}" for name in names
    ]


def test_one_process_extracts_every_map(tools, quarterly, prefix):
    # value > 33: none of 11 to 24, 34 of the third map, all of the rest.
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        expression="value > 33",
        basename=f"{prefix}_x",
        nprocs=1,
        flags="n",
    )

    assert _primitives(tools, prefix) == [0, 0, 1, 4, 4, 4]


@pytest.mark.parametrize("nprocs", [2, 6, 8])
def test_more_processes_than_maps_run_one_extraction(tools, quarterly, prefix, nprocs):
    # Several v.extract processes copy their tables into one SQLite database
    # at the same time, which the description of nprocs rules out ("Use only
    # if database backend is used which supports concurrent writing"). With
    # 24 maps and nprocs=8, 4 of 30 runs ended with "database is locked" or
    # "database schema has changed" (measured 18.10.2026: t.vect.extract
    # repeated in a temporary project with the default SQLite backend). So
    # the selection holds one map, the fourth (values 41 to 44), and the
    # processes are started and joined without writing at the same time.
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        where="start_time >= '2001-10-01' AND start_time < '2001-12-01'",
        expression="value > 33",
        basename=f"{prefix}_x",
        nprocs=nprocs,
    )

    assert _primitives(tools, prefix) == [4]


def test_overwrite_replaces_the_dataset_and_its_maps(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": f"{prefix}_x"}
    tools.t_vect_extract(expression="value > 33", **options)

    tools.t_vect_extract(
        expression="value > 0",
        where="start_time < '2001-07-01'",
        overwrite=True,
        **options,
    )

    assert _primitives(tools, prefix) == [4, 4]
    assert _info(tools, prefix)["number_of_maps"] == 2


def test_a_basename_without_an_expression_copies_nothing(tools, quarterly, prefix):
    # Old test_selection_no_suffix: the maps are registered, not copied, so no
    # map with the base name appears.
    tools.t_vect_extract(
        input=quarterly,
        output=prefix,
        where="start_time > '2001-06-01'",
        basename=f"{prefix}_x",
    )

    assert tools.g_list(type="vector", pattern=f"{prefix}_x*").stdout == ""
    assert [name for name, _ in _maps(tools, prefix)] == [
        "vq_3",
        "vq_4",
        "vq_5",
        "vq_6",
    ]
