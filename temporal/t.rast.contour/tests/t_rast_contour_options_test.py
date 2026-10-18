"""Test the dataset options and flags of t.rast.contour on four quarterly maps

The maps are the column ramp (January), the row ramp (April), the column ramp
(July) and a map without values (October); conftest.py has the geometry. With
the levels 1, 2, 3, 4 the column ramp has the lines at 2, 3, 4 (three) and the
row ramp (2, 4, 6, 8) the lines at 3 and 4 (two), so the dataset holds
3 + 2 + 3 = 8 straight lines with two nodes each; the map without values has
none.
"""

import pytest

from grass.temporal.testing.readback import list_maps, message, stds_info

LEVELS = {"levels": "1,2,3,4"}


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
            "lines",
            "primitives",
            "nodes",
        )
    }


def _names(tools, name):
    return [row.name for row in list_maps(tools, "stvds", name)]


def test_empty_maps_are_dropped(tools, quarterly, prefix):
    tools.t_rast_contour(input=quarterly, output=prefix, basename=prefix, **LEVELS)

    assert _numbers(tools, prefix) == {
        "start_time": "'2001-01-01 00:00:00'",
        "end_time": "'2001-10-01 00:00:00'",
        "granularity": "'3 months'",
        "map_time": "interval",
        "number_of_maps": 3,
        "lines": 8,
        "primitives": 8,
        "nodes": 16,
    }


def test_the_n_flag_registers_the_empty_map(tools, quarterly, prefix):
    tools.t_rast_contour(
        input=quarterly, output=prefix, basename=prefix, flags="n", **LEVELS
    )

    assert _numbers(tools, prefix) == {
        "start_time": "'2001-01-01 00:00:00'",
        "end_time": "'2002-01-01 00:00:00'",
        "granularity": "'3 months'",
        "map_time": "interval",
        "number_of_maps": 4,
        "lines": 8,
        "primitives": 8,
        "nodes": 16,
    }


def test_where_selects_the_maps(tools, quarterly, prefix):
    # The text comparison keeps a map that starts on 2001-04-01, then July and
    # October: the row ramp (2 lines), the column ramp (3 lines) and the empty
    # map, which is dropped.
    tools.t_rast_contour(
        input=quarterly,
        output=prefix,
        basename=prefix,
        where="start_time > '2001-02-01'",
        **LEVELS,
    )

    numbers = _numbers(tools, prefix)
    assert (numbers["start_time"], numbers["end_time"]) == (
        "'2001-04-01 00:00:00'",
        "'2001-10-01 00:00:00'",
    )
    assert (numbers["number_of_maps"], numbers["lines"], numbers["nodes"]) == (2, 5, 10)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("nprocs", [1, 4])
def test_t_flag_makes_no_attribute_table_and_allows_nprocs(
    tools, quarterly, prefix, nprocs
):
    result = tools.t_rast_contour(
        input=quarterly,
        output=prefix,
        basename=prefix,
        flags="t",
        nprocs=nprocs,
        **LEVELS,
    )

    assert "reduced to 1" not in message(result)
    assert _numbers(tools, prefix)["lines"] == 8
    for name in _names(tools, prefix):
        assert tools.v_db_connect(map=name, flags="p").stdout.strip() == ""


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_without_the_t_flag_the_maps_have_a_table(tools, quarterly, prefix):
    tools.t_rast_contour(input=quarterly, output=prefix, basename=prefix, **LEVELS)

    for name in _names(tools, prefix):
        assert f"table <{name}>" in tools.v_db_connect(map=name, flags="p").stdout


def test_nprocs_is_reduced_to_one_with_attribute_tables(tools, quarterly, prefix):
    result = tools.t_rast_contour(
        input=quarterly, output=prefix, basename=prefix, nprocs=4, **LEVELS
    )

    assert (
        "The number of parallel r.contour processes was reduced to 1 because of "
        "the table attribute creation" in message(result)
    )
    assert _numbers(tools, prefix)["lines"] == 8


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01", "2001_04", "2001_07"]),
        ("time", ["2001_01_01T00_00_00", "2001_04_01T00_00_00", "2001_07_01T00_00_00"]),
        ("num", ["00001", "00002", "00003"]),
        ("num%03", ["001", "002", "003"]),
    ],
)
def test_the_suffix_of_the_new_maps(tools, quarterly, prefix, suffix, names):
    tools.t_rast_contour(
        input=quarterly, output=prefix, basename=f"{prefix}_c", suffix=suffix, **LEVELS
    )

    assert _names(tools, prefix) == [f"{prefix}_c_{name}" for name in names]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_dataset(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": prefix}
    tools.t_rast_contour(**options, **LEVELS)

    tools.t_rast_contour(**options, levels="2", overwrite=True)

    # Level 2 is a line of the two column ramps; it is the lowest value of the
    # row ramp, which has none, and the empty maps are dropped.
    assert _numbers(tools, prefix)["lines"] == 2
    assert len(_names(tools, prefix)) == 2
