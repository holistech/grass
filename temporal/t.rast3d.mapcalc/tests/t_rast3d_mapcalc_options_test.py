"""Test the options of t.rast3d.mapcalc: methods, suffix, nprocs and refusals

The characterization tests of this directory cover two inputs, -n, -s and a few
functions. This file adds the example of the shell test (three datasets), every
sampling method on a series of granules with one partner each, the default
list of methods, the names of the new maps, relative time and the refusals.
Maps are 3D rasters of one voxel row of two cells.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.temporal.testing.readback import message, stds_info
from grass.tools import ToolError


def _day(text):
    return datetime.strptime(text, "%Y-%m-%d")


def _call(tools, **options):
    return tools.t_rast3d_mapcalc(**{"overwrite": True, **options})


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_mapcalc(**options)
    return message(error.value)


def _maps(tools, name):
    """(name, start, min) of the maps of the 3D dataset name"""
    lines = tools.t_rast3d_list(
        input=name, columns="name,start_time,min", flags="s"
    ).stdout.splitlines()
    return [tuple(line.split("|")) for line in lines]


@pytest.fixture(scope="module")
def series(tools):
    """Datasets M1 and M2 (the same three quarterly maps under two names)

    m1_k holds 100 k, and M2 holds the maps m2_k with the same times and
    values. The region is one row of two cells and one layer.
    """
    small_region(tools, 1, 2, depths=1)
    quarters = [
        (_day("2001-01-01"), _day("2001-04-01")),
        (_day("2001-04-01"), _day("2001-07-01")),
        (_day("2001-07-01"), _day("2001-10-01")),
    ]
    for name in ("m1", "m2"):
        create_stds(
            tools,
            "str3ds",
            name.upper(),
            [
                MapSpec(f"{name}_{number}", 100 * number, start, end)
                for number, (start, end) in enumerate(quarters, 1)
            ],
        )


@pytest.mark.slow
def test_the_shell_example_with_three_inputs(tools, series):
    # The first run adds the datasets: 200, 400, 600. The second run lists the
    # result as a third input; its granules are those of M1 and M2, so the
    # expression (M1 + M2) / M2 gives 2 in all three granules.
    _call(
        tools,
        flags="n",
        inputs="M1,M2",
        output="MC1",
        expression=" M1 + M2",
        basename="mc1",
        method="equal",
        nprocs=6,
    )
    _call(
        tools,
        flags="s",
        inputs="M1,M2,MC1",
        output="MC2",
        expression=" (M1 + M2) / M2",
        basename="mc2",
        method="equal",
        nprocs=6,
    )

    assert [value for _, _, value in _maps(tools, "MC1")] == ["200.0", "400.0", "600.0"]
    assert [value for _, _, value in _maps(tools, "MC2")] == ["2.0", "2.0", "2.0"]
    assert stds_info(tools, "str3ds", "MC2")["number_of_maps"] == 3


def test_the_new_maps_are_numbered_from_one(tools, series):
    _call(tools, inputs="M1", output="MN", expression="M1 * 2", basename="mn")

    assert [(name, start) for name, start, _ in _maps(tools, "MN")] == [
        ("mn_1", "2001-01-01 00:00:00"),
        ("mn_2", "2001-04-01 00:00:00"),
        ("mn_3", "2001-07-01 00:00:00"),
    ]


def test_the_result_has_the_type_and_the_times_of_the_first_input(tools, series):
    _call(tools, inputs="M1", output="MT", expression="M1 + 1", basename="mt")

    info = stds_info(tools, "str3ds", "MT")
    assert info["temporal_type"] == "absolute"
    assert (info["start_time"], info["end_time"]) == (
        "'2001-01-01 00:00:00'",
        "'2001-10-01 00:00:00'",
    )
    assert info["granularity"] == "'3 months'"


@pytest.mark.parametrize("nprocs", [1, 2, 3, 0])
def test_nprocs_gives_the_same_maps(tools, series, nprocs):
    _call(
        tools,
        inputs="M1,M2",
        output="MP",
        expression="M1 - M2 + 5",
        basename="mp",
        method="equal",
        nprocs=nprocs,
    )

    assert [value for _, _, value in _maps(tools, "MP")] == ["5.0", "5.0", "5.0"]


def _granules():
    return {
        1: ("2001-01-01", "2001-02-01"),
        2: ("2001-03-01", "2001-04-01"),
        3: ("2001-05-01", "2001-06-01"),
        4: ("2001-07-01", "2001-08-01"),
        5: ("2001-09-01", "2001-10-01"),
        6: ("2001-11-01", "2001-12-01"),
        7: ("2002-01-01", "2002-03-01"),
        8: ("2002-04-01", "2002-05-01"),
    }


@pytest.fixture(scope="module")
def methods(tools):
    """Sampler G3 with the eight granules of _granules() and input X3 with
    eight maps, map N (value N) related to granule N:

    1. equals granule 1
    2. 2001-03-10 to 2001-03-20, inside granule 2
    3. 2001-04-20 to 2001-06-10, covers granule 3
    4. 2001-07-20 to 2001-08-20, starts in granule 4 and ends after it
    5. 2001-10-01 to 2001-10-15, begins where granule 5 ends
    6. 2001-10-15 to 2001-11-01, ends where granule 6 begins
    7. 2002-01-01 to 2002-02-01, inside granule 7, sharing its start
    8. 2002-04-01 to 2002-07-01, covers granule 8, sharing its start

    Each map is related to its own granule only. The same geometry as in the
    tests of t.rast.mapcalc; the sampling does not depend on the map type.
    """
    small_region(tools, 1, 2, depths=1)
    create_stds(
        tools,
        "str3ds",
        "G3",
        [
            MapSpec(f"g3_{number}", 1000 * number, _day(start), _day(end))
            for number, (start, end) in _granules().items()
        ],
    )
    partners = [
        ("2001-01-01", "2001-02-01"),
        ("2001-03-10", "2001-03-20"),
        ("2001-04-20", "2001-06-10"),
        ("2001-07-20", "2001-08-20"),
        ("2001-10-01", "2001-10-15"),
        ("2001-10-15", "2001-11-01"),
        ("2002-01-01", "2002-02-01"),
        ("2002-04-01", "2002-07-01"),
    ]
    create_stds(
        tools,
        "str3ds",
        "X3",
        [
            MapSpec(f"x3_{number}", number, _day(start), _day(end))
            for number, (start, end) in enumerate(partners, 1)
        ],
    )


@pytest.mark.parametrize(
    ("method", "granules"),
    [
        ("equal", [1]),
        ("during", [3, 8]),
        ("contain", [2, 7]),
        ("overlap", [4]),
        ("follows", [6]),
        ("precedes", [5]),
        # The method start takes the relations overlapped, starts, started,
        # finishes and contains (_METHOD_RELATIONS in related_maps.py), not
        # equal and not overlaps: so granule 1 (equal) and granule 4
        # (overlaps) have no partner. The maps 2 and 7 lie in their granule
        # (contains), map 8 starts with it and runs on.
        ("start", [2, 7, 8]),
        # The default of the tool: during, overlap, contain and equal
        (None, [1, 2, 3, 4, 7, 8]),
    ],
)
def test_the_sampling_methods_take_the_related_map(tools, methods, method, granules):
    options = {} if method is None else {"method": method}
    _call(tools, inputs="G3,X3", output="MM", expression="X3", basename="mm", **options)

    # The new maps are named by the granule number and hold the value of the
    # partner, which equals the number
    assert [
        (name.rsplit("_", 1)[1], start, value)
        for name, start, value in _maps(tools, "MM")
    ] == [
        (str(number), f"{_granules()[number][0]} 00:00:00", f"{number}.0")
        for number in granules
    ]


def test_several_methods_are_joined(tools, methods):
    _call(
        tools,
        inputs="G3,X3",
        output="MJ",
        expression="X3",
        basename="mj",
        method="follows,precedes",
    )

    assert [value for _, _, value in _maps(tools, "MJ")] == ["5.0", "6.0"]


@pytest.fixture(scope="module")
def relative(tools):
    small_region(tools, 1, 2, depths=1)
    create_stds(
        tools,
        "str3ds",
        "R3",
        [MapSpec(f"r3_{k}", 10 * (k + 1), 5 * k, 5 * (k + 1)) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )


@pytest.mark.slow
def test_relative_time_keeps_the_times_and_the_unit(tools, relative):
    _call(tools, inputs="R3", output="MR", expression="R3 * 2", basename="mr")

    info = stds_info(tools, "str3ds", "MR")
    assert (info["temporal_type"], info["unit"]) == ("relative", "days")
    assert (info["start_time"], info["end_time"]) == ("'0'", "'15'")
    assert [value for _, _, value in _maps(tools, "MR")] == ["20.0", "40.0", "60.0"]


@pytest.mark.parametrize("missing", ["inputs", "output", "expression", "basename"])
def test_required_options_are_named(tools, series, missing):
    options = {
        "inputs": "M1",
        "output": "ME",
        "expression": "M1 + 1",
        "basename": "me",
    }
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_sampling_method_is_refused(tools, series):
    text = _refused(
        tools,
        inputs="M1",
        output="ME",
        expression="M1 + 1",
        basename="me",
        method="bogus",
    )

    assert "Value <bogus> out of range for parameter <method>" in text


def test_a_missing_input_dataset_is_named(tools, series):
    assert "Space time dataset <nothere> of type <str3ds> not found" in _refused(
        tools, inputs="nothere", output="ME", expression="nothere + 1", basename="me"
    )


def test_an_invalid_expression_stops_the_computation(tools, series):
    text = _refused(tools, inputs="M1", output="ME", expression="M1 +", basename="me")

    assert "Error while mapcalc computation" in text


@pytest.mark.slow
def test_an_existing_output_needs_overwrite(tools, series):
    _call(tools, inputs="M1", output="MK", expression="M1 + 1", basename="mk")

    text = _refused(tools, inputs="M1", output="MK", expression="M1 + 2", basename="mk")

    assert "Space time raster3d dataset <MK> is already in the database" in text
    assert [value for _, _, value in _maps(tools, "MK")] == ["101.0", "201.0", "301.0"]


def test_nprocs_must_be_an_integer(tools, series):
    text = _refused(
        tools, inputs="M1", output="ME", expression="M1", basename="me", nprocs="x"
    )

    assert "Invalid value <x> for parameter <nprocs>" in text


def test_a_decimal_nprocs_today_ends_with_a_traceback(tools, series):
    text = _refused(
        tools, inputs="M1", output="ME", expression="M1", basename="me", nprocs="2.5"
    )

    assert "ValueError: invalid literal for int() with base 10: '2.5'" in text


@pytest.mark.xfail(strict=True, reason="a decimal nprocs ends with a traceback")
def test_a_decimal_nprocs_is_reported_as_a_message(tools, series):
    text = _refused(
        tools, inputs="M1", output="ME", expression="M1", basename="me", nprocs="2.5"
    )

    assert "Traceback" not in text


@pytest.mark.parametrize(
    ("flags", "announced", "not_announced"),
    [
        ("", "Starting temporal sampling...", "spatio-temporal"),
        ("s", "Starting spatio-temporal sampling...", "Starting temporal sampling"),
    ],
)
def test_the_flag_s_is_announced(tools, series, flags, announced, not_announced):
    result = _call(
        tools,
        inputs="M1",
        output="MF",
        expression="M1 + 1",
        basename="mf",
        flags=flags,
    )

    text = message(result)
    assert announced in text
    assert not_announced not in text


def test_basename_maps_that_exist_end_with_an_error_status(tools, series):
    _call(tools, inputs="M1", output="MB3", expression="M1 + 1", basename="mc")

    with pytest.raises(ToolError) as error:
        tools.t_rast3d_mapcalc(
            inputs="M1", output="MB4", expression="M1 + 5", basename="mc"
        )

    assert (
        "Map <mc_1@PERMANENT> is already in temporal database, "
        "use overwrite flag to overwrite"
    ) in message(error.value)
    # The tool stops before it computes or makes anything.
    assert "MB4" not in tools.t_list(type="str3ds", columns="name").stdout
