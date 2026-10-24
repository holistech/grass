"""Test the options of t.rast.gapfill on the monthly maps of the old suite

The maps hold 100 (January), 400 (April) and 1200 (December 2001) in the
first cell and 0, 30 and 94 in the second (conftest.py). The tool
interpolates linearly between the map before and the map after a gap: the n
missing maps of a gap sit at the positions i / (n + 1) of the way from the
predecessor to the successor, so the value is v0 + i (v1 - v0) / (n + 1) in
each cell.

First gap, two maps (February, March): first cell 100 + 300 i / 3 = 200, 300;
second cell 0 + 30 i / 3 = 10, 20. Second gap, seven maps (May to November):
first cell 400 + 800 i / 8 = 500 ... 1100; second cell 30 + 64 i / 8 =
38, 46 ... 86.

The names of the new maps: the number of entries of the dataset with its gaps
(five here: January, the first gap, April, the second gap, December) plus the
count of the gap gives the first part of a numeric suffix, so the first gap
is 6 and the second 7 (the suffix num%01 gives test_6_1, test_6_2, test_7_1 ...).
"""

import pytest

from grass.temporal.testing.readback import cell_values, list_maps, message, stds_info
from grass.tools import ToolError

# Nearly every test builds maps and datasets and runs the interpolation, which takes
# more than a second (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow

FIRST_GAP = [(200, 10), (300, 20)]
SECOND_GAP = [(500 + 100 * i, 38 + 8 * i) for i in range(7)]


def _approx(pairs):
    """Expected cell values; the position 2 / 3 is not exact in a double"""
    return [[pytest.approx(float(v), rel=1e-12) for v in pair] for pair in pairs]


def _filled(tools, name):
    """(name, start, end, cell values) of every map of the dataset"""
    return [
        (row.name, row.start, row.end, cell_values(tools, row.name))
        for row in list_maps(tools, "strds", name)
    ]


def _expected(prefix, month_start, names):
    """The rows of the full dataset: the old maps and the interpolated ones

    names is the list of the 9 interpolated names, in time order.
    """
    rows = [(f"{prefix}_in_m1", 1, [100.0, 0.0])]
    rows += [(names[i], 2 + i, [float(v) for v in FIRST_GAP[i]]) for i in range(2)]
    rows += [(f"{prefix}_in_m4", 4, [400.0, 30.0])]
    rows += [(names[2 + i], 5 + i, [float(v) for v in SECOND_GAP[i]]) for i in range(7)]
    rows += [(f"{prefix}_in_m12", 12, [1200.0, 94.0])]
    return [
        (
            name,
            month_start(number).strftime("%Y-%m-%d %H:%M:%S"),
            month_start(number + 1).strftime("%Y-%m-%d %H:%M:%S"),
            [pytest.approx(value, rel=1e-12) for value in values],
        )
        for name, number, values in rows
    ]


def _info(tools, name):
    info = stds_info(tools, "strds", name)
    return {
        key: info[key]
        for key in (
            "start_time",
            "end_time",
            "granularity",
            "map_time",
            "number_of_maps",
            "min_min",
            "min_max",
            "max_min",
            "max_max",
        )
    }


def _all_names(prefix, suffixes):
    return [f"{prefix}_{suffix}" for suffix in suffixes]


FULL = {
    "start_time": "'2001-01-01 00:00:00'",
    "end_time": "'2002-01-01 00:00:00'",
    "granularity": "'1 month'",
    "map_time": "interval",
    "number_of_maps": 12,
    "min_min": 0.0,
    "min_max": 94.0,
    "max_min": 100.0,
    "max_max": 1200.0,
}
NUMERIC = [f"6_{i}" for i in (1, 2)] + [f"7_{i}" for i in range(1, 8)]
GRAN = [f"2001_{m:02d}" for m in (2, 3, 5, 6, 7, 8, 9, 10, 11)]
TIME = [f"2001_{m:02d}_01T00_00_00" for m in (2, 3, 5, 6, 7, 8, 9, 10, 11)]


@pytest.mark.parametrize(
    ("options", "suffixes"),
    [
        ({"suffix": "num%01", "nprocs": 2}, NUMERIC),
        ({"nprocs": 2}, GRAN),
        ({"suffix": "gran"}, GRAN),
        ({"suffix": "time", "nprocs": 2}, TIME),
    ],
    ids=["num%01-2procs", "default-gran", "gran", "time"],
)
def test_every_gap_is_filled(
    tools, gappy, old_suite, month_start, prefix, options, suffixes
):
    name = gappy(old_suite)

    tools.t_rast_gapfill(input=name, basename=prefix, **options)

    assert _filled(tools, name) == _expected(
        prefix, month_start, _all_names(prefix, suffixes)
    )
    assert _info(tools, name) == FULL


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_nprocs_gives_the_same_maps(
    tools, gappy, old_suite, month_start, prefix, nprocs
):
    name = gappy(old_suite)

    tools.t_rast_gapfill(input=name, basename=prefix, nprocs=nprocs)

    assert _filled(tools, name) == _expected(
        prefix, month_start, _all_names(prefix, GRAN)
    )


def test_where_limits_the_search_for_gaps_to_the_end(tools, gappy, old_suite, prefix):
    # start_time >= '2001-03-01' keeps April and December: only the second
    # gap lies between them and is filled. The suffix counts three entries
    # (April, the gap, December), so the gap is number 4.
    name = gappy(old_suite)

    tools.t_rast_gapfill(
        input=name,
        where="start_time >= '2001-03-01'",
        basename=prefix,
        suffix="num%01",
    )

    rows = _filled(tools, name)
    assert [row[0] for row in rows] == [
        f"{prefix}_in_m1",
        f"{prefix}_in_m4",
        *[f"{prefix}_4_{i}" for i in range(1, 8)],
        f"{prefix}_in_m12",
    ]
    assert [row[3] for row in rows[2:9]] == _approx(SECOND_GAP)
    assert _info(tools, name)["number_of_maps"] == 10


def test_where_limits_the_search_for_gaps_to_the_start(tools, gappy, old_suite, prefix):
    # start_time <= '2001-05-01' keeps January and April: the first gap only.
    name = gappy(old_suite)

    tools.t_rast_gapfill(
        input=name,
        where="start_time <= '2001-05-01'",
        basename=prefix,
        suffix="num%01",
    )

    rows = _filled(tools, name)
    assert [row[0] for row in rows] == [
        f"{prefix}_in_m1",
        f"{prefix}_4_1",
        f"{prefix}_4_2",
        f"{prefix}_in_m4",
        f"{prefix}_in_m12",
    ]
    assert [row[3] for row in rows[1:3]] == _approx(FIRST_GAP)
    assert _info(tools, name)["number_of_maps"] == 5


def test_a_where_without_a_gap_changes_nothing(tools, gappy, old_suite, prefix):
    name = gappy(old_suite)

    result = tools.t_rast_gapfill(
        input=name,
        where="start_time >= '2001-10-01'",
        basename=prefix,
        suffix="num%01",
    )

    assert "No gaps found" in message(result)
    assert [row.name for row in list_maps(tools, "strds", name)] == [
        f"{prefix}_in_m1",
        f"{prefix}_in_m4",
        f"{prefix}_in_m12",
    ]
    assert _info(tools, name)["number_of_maps"] == 3


def test_a_dataset_without_a_gap_is_left_alone(tools, gappy, prefix):
    name = gappy({1: (100, 0), 2: (200, 5), 3: (300, 10)})

    result = tools.t_rast_gapfill(input=name, basename=prefix)

    assert "No gaps found" in message(result)
    assert _info(tools, name)["number_of_maps"] == 3


def test_one_missing_map_is_the_mean_of_its_neighbours(tools, gappy, prefix):
    # (100 + 300) / 2 = 200 and (0 + 90) / 2 = 45 at the position 1 / 2.
    name = gappy({1: (100, 0), 3: (300, 90)})

    tools.t_rast_gapfill(input=name, basename=prefix)

    rows = _filled(tools, name)
    assert rows[1] == (
        f"{prefix}_2001_02",
        "2001-02-01 00:00:00",
        "2001-03-01 00:00:00",
        [200.0, 45.0],
    )
    assert len(rows) == 3


def test_the_removed_t_flag_is_refused(tools, gappy, prefix):
    # The flag had no effect and was removed on 18.10.2026.
    name = gappy({1: (100, 0), 3: (300, 90)})

    with pytest.raises(ToolError) as error:
        tools.t_rast_gapfill(input=name, basename=prefix, flags="t")

    assert "Sorry, <t> is not a valid flag" in message(error.value)
    assert tools.g_list(type="raster", pattern=f"{prefix}_2*").stdout == ""


def test_a_gap_with_two_successors_uses_one_of_them(tools, gappy, prefix):
    # The maps of March and the map of March to April share a start, so the
    # gap has two successors (300 / 90 and 500 / 70). The tool warns and uses
    # "the first found"; which one that is, is not defined, so the result is
    # either (100 + 300) / 2 = 200 or (100 + 500) / 2 = 300 in the first cell.
    name = gappy({1: (100, 0), 3: (300, 90)})
    tools.r_mapcalc(expression=f"{prefix}_wide = if(col() == 1, 500, 70)")
    tools.t_register(
        type="raster",
        input=name,
        maps=f"{prefix}_wide",
        start="2001-03-01",
        end="2001-05-01",
    )

    result = tools.t_rast_gapfill(input=name, basename=prefix)

    assert (
        "More than one successor of the gap found. Using the first found."
        in message(result)
    )
    assert _filled(tools, name)[1][3][0] in {200.0, 300.0}


def test_a_gap_with_two_predecessors_uses_the_one_that_starts_first(
    tools, gappy, prefix
):
    # A map from December 2000 to the end of January ends where the map of
    # January ends, so the gap has two predecessors (100 / 0 and 500 / 70).
    # The tool warns and uses "the first found". The topology builder adds
    # the neighbours of the gap in the order of the maps by start time, and
    # the two predecessors start on different days, so the first found is
    # the map from December: (500 + 300) / 2 = 400 and (70 + 90) / 2 = 80.
    # (Two successors with the same start, as above, have no defined order.)
    name = gappy({1: (100, 0), 3: (300, 90)})
    tools.r_mapcalc(expression=f"{prefix}_wide = if(col() == 1, 500, 70)")
    tools.t_register(
        type="raster",
        input=name,
        maps=f"{prefix}_wide",
        start="2000-12-01",
        end="2001-02-01",
    )

    result = tools.t_rast_gapfill(input=name, basename=prefix)

    assert "More than one predecessor of the gap found. Using the first found." in (
        message(result)
    )
    assert _filled(tools, name)[2][3] == [400.0, 80.0]
