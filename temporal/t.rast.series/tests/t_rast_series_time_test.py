"""Test the time stamp that t.rast.series gives to its output maps

The output map gets the start of the first and the end of the last of the
selected maps in the order of order= (the end of the last map, or its start if
it is a time instant); with -t it gets no time and is not registered. The data
are the series of conftest.py: map k lasts from day k to day k + 1 of 2001-01.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import map_info


def _times(tools, name):
    """(start, end) of a registered map as text, end None for a time point"""
    info = map_info(tools, "raster", name)
    if info is None:
        return None
    start, end = (str(info[key]).strip("'") for key in ("start_time", "end_time"))
    return start, None if end == "None" else end


def _run(tools, name, input, **options):
    tools.t_rast_series(input=input, method="sum", output=name, **options)
    return _times(tools, name)


def test_the_output_spans_all_maps(tools, stats, prefix):
    assert _run(tools, f"{prefix}_o", stats) == (
        "2001-01-01 00:00:00",
        "2001-01-06 00:00:00",
    )


def test_the_output_spans_the_selected_maps(tools, stats, prefix):
    # The maps that start on January 2 and 3 are selected; the last one ends
    # on January 4.
    assert _run(
        tools,
        f"{prefix}_o",
        stats,
        where="start_time >= '2001-01-02' and start_time < '2001-01-04'",
    ) == ("2001-01-02 00:00:00", "2001-01-04 00:00:00")


def test_the_t_flag_gives_no_time_and_no_registration(tools, stats, prefix):
    assert _run(tools, f"{prefix}_o", stats, flags="t") is None


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_every_output_gets_the_time(tools, stats, prefix):
    tools.t_rast_series(
        input=stats, method="minimum,maximum", output=f"{prefix}_a,{prefix}_b"
    )

    assert _times(tools, f"{prefix}_a") == _times(tools, f"{prefix}_b")
    assert _times(tools, f"{prefix}_a")[1] == "2001-01-06 00:00:00"


@pytest.fixture(scope="module")
def points(tools):
    """Three time instants, on days 0, 2 and 5"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_points",
        [
            MapSpec(f"ser_p{k}", k + 1, day(offset))
            for k, offset in enumerate((0, 2, 5))
        ],
    )
    return "ser_points"


def test_instants_span_from_the_first_to_the_last(tools, points, prefix):
    assert _run(tools, f"{prefix}_o", points) == (
        "2001-01-01 00:00:00",
        "2001-01-06 00:00:00",
    )


def test_one_instant_stays_an_instant(tools, points, prefix):
    assert _run(
        tools, f"{prefix}_o", points, where="start_time = '2001-01-03 00:00:00'"
    ) == ("2001-01-03 00:00:00", None)


@pytest.fixture(scope="module")
def relative(tools):
    """Four time instants of relative time: 0, 14, 28 and 42 days"""
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        "ser_relative",
        [MapSpec(f"ser_r{k}", 100 * (k + 1), 14 * k) for k in range(4)],
        temporaltype="relative",
        unit="days",
    )
    return "ser_relative"


def test_relative_time_spans_the_selected_maps(tools, relative, prefix):
    tools.t_rast_series(
        input=relative, method="minimum", output=f"{prefix}_o", where="start_time >= 28"
    )

    info = map_info(tools, "raster", f"{prefix}_o")
    assert (info["temporal_type"], info["start_time"], info["end_time"]) == (
        "relative",
        "'28'",
        "'42'",
    )
    # t.info -g prints the numbers of relative time as quoted text.
    assert info["unit"] == "days"
    assert info["min"] == 300.0


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_order_by_a_value_changes_the_time_stamp_today(tools, stats, prefix):
    # By maximum the first map is ser_e (January 2 to 3) and the last ser_c
    # (January 5 to 6), so the output spans January 2 to 6 although the
    # first map of the dataset starts on January 1. By name the first map is
    # ser_a (January 3 to 4) and the last ser_e (January 2 to 3): start and
    # end are both January 3, so the output is an instant.
    assert _run(tools, f"{prefix}_o", stats, order="max") == (
        "2001-01-02 00:00:00",
        "2001-01-06 00:00:00",
    )
    assert _run(tools, f"{prefix}_p", stats, order="name") == (
        "2001-01-03 00:00:00",
        None,
    )


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.series takes the start of the first and the end of the last map in the order of order=, so the time stamp of the result shrinks",
)
@pytest.mark.parametrize("order", ["max", "name"])
def test_order_does_not_shrink_the_time_stamp(tools, stats, prefix, order):
    assert _run(tools, f"{prefix}_o", stats, order=order) == (
        "2001-01-01 00:00:00",
        "2001-01-06 00:00:00",
    )
