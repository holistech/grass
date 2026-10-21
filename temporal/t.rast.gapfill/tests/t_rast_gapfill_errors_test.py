"""Test the refusals of t.rast.gapfill and the cases that other time types bring

Relative time, time instants, existing results and overwrite.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError

# Nearly every test builds maps and datasets and runs the interpolation, which takes
# more than a second (measured 18.10.2026 with a serial pytest --durations=0).
pytestmark = pytest.mark.slow


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_gapfill(**options)
    return message(error.value)


def _rows(tools, name):
    return [(row.name, row.start, row.min) for row in list_maps(tools, "strds", name)]


@pytest.mark.parametrize("missing", ["input", "basename"])
def test_a_required_option_is_checked_by_the_parser(tools, gappy, prefix, missing):
    options = {"input": gappy({1: (1, 1), 3: (3, 3)}), "basename": prefix}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="gap_missing", basename=prefix)

    assert "Space time dataset <gap_missing> of type <strds> not found" in text


def test_an_unknown_suffix_counts_like_num(tools, gappy, prefix):
    # Nothing checks the suffix: any other text gives the numeric form with
    # five digits (the name has two numbers, see the module docstring of
    # t_rast_gapfill_options_test.py).
    name = gappy({1: (100, 0), 3: (300, 90)})

    tools.t_rast_gapfill(input=name, basename=prefix, suffix="bogus")

    # Three entries (map, gap, map) plus the gap count 1 give 4.
    assert [row[0] for row in _rows(tools, name)][1] == f"{prefix}_00004_00001"


def test_the_message_for_an_existing_map_names_the_map(tools, gappy, prefix):
    first = gappy({1: (100, 0), 3: (300, 90)})
    tools.t_rast_gapfill(input=first, basename=prefix)
    second = gappy({1: (100, 0), 3: (300, 90)}, name=f"{prefix}_other")

    text = _refused(tools, input=second, basename=prefix)

    assert f"<{prefix}_2001_02@PERMANENT>" in text


def test_a_refused_run_leaves_the_dataset_as_it_was(tools, gappy, prefix):
    first = gappy({1: (100, 0), 3: (300, 90)})
    tools.t_rast_gapfill(input=first, basename=prefix)
    second = gappy({1: (100, 0), 3: (300, 90)}, name=f"{prefix}_other")

    _refused(tools, input=second, basename=prefix)

    assert stds_info(tools, "strds", second)["number_of_maps"] == 2


def test_overwrite_replaces_a_map_of_another_dataset(tools, gappy, prefix):
    # The maps of the second dataset hold 0 and 10 where the first held 100
    # and 300, so the gap map is 5 instead of 200.
    first = gappy({1: (100, 0), 3: (300, 90)})
    tools.t_rast_gapfill(input=first, basename=prefix)
    second = gappy({1: (0, 0), 3: (10, 10)}, name=f"{prefix}_other")

    tools.t_rast_gapfill(input=second, basename=prefix, overwrite=True)

    assert _rows(tools, second)[1] == (f"{prefix}_2001_02", "2001-02-01 00:00:00", 5.0)
    assert [row[0] for row in _rows(tools, first)] == [
        f"{prefix}_in_m1",
        f"{prefix}_in_m3",
    ]


def test_the_first_dataset_counts_its_maps_after_an_overwrite(tools, gappy, prefix):
    first = gappy({1: (100, 0), 3: (300, 90)})
    tools.t_rast_gapfill(input=first, basename=prefix)
    second = gappy({1: (0, 0), 3: (10, 10)}, name=f"{prefix}_other")
    tools.t_rast_gapfill(input=second, basename=prefix, overwrite=True)

    assert stds_info(tools, "strds", first)["number_of_maps"] == 2


@pytest.fixture
def relative(tools, prefix):
    """Four maps in relative days: 0 to 1 (100), 1 to 2 (200), gap, 4 to 5 (500)"""

    def make(name=None, values=(100, 200, 500)):
        small_region(tools, 1, 2)
        name = name or f"{prefix}_rel"
        create_stds(
            tools,
            "strds",
            name,
            [
                MapSpec(f"{name}_a", values[0], 0, 1),
                MapSpec(f"{name}_b", values[1], 1, 2),
                MapSpec(f"{name}_c", values[2], 4, 5),
            ],
            temporaltype="relative",
            unit="days",
        )
        return name

    return make


def test_relative_time_has_a_numeric_name_of_two_numbers(tools, relative, prefix):
    # The gap from 2 to 4 holds two maps (days 2 and 3) at the positions 1/3
    # and 2/3 between 200 and 500: 300 and 400. The name is the base, the
    # entries of the dataset with its gap (four: three maps and the gap) plus
    # the count of the gap, 5, and the count of the new map.
    name = relative()

    tools.t_rast_gapfill(input=name, basename=prefix)

    assert [(row[0], row[1], row[2]) for row in _rows(tools, name)] == [
        (f"{name}_a", 0, 100.0),
        (f"{name}_b", 1, 200.0),
        (f"{prefix}_00005_00001", 2, pytest.approx(300.0)),
        (f"{prefix}_00005_00002", 3, pytest.approx(400.0)),
        (f"{name}_c", 4, 500.0),
    ]
    info = stds_info(tools, "strds", name)
    assert info["temporal_type"] == "relative"
    assert info["number_of_maps"] == 5


def test_relative_time_with_a_numeric_width(tools, relative, prefix):
    name = relative()

    tools.t_rast_gapfill(input=name, basename=prefix, suffix="num%03")

    assert [row[0] for row in _rows(tools, name)][2:4] == [
        f"{prefix}_005_001",
        f"{prefix}_005_002",
    ]


def test_time_instants_cannot_be_filled(tools, prefix):
    # Points at the days 0, 3 and 4 have no intervals between them that a
    # gap could fill; the tool finds a gap but no neighbours.
    small_region(tools, 1, 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_points",
        [
            MapSpec(f"{prefix}_p0", 100, day(0)),
            MapSpec(f"{prefix}_p1", 400, day(3)),
            MapSpec(f"{prefix}_p2", 500, day(4)),
        ],
    )

    text = _refused(tools, input=f"{prefix}_points", basename=prefix)

    assert "Unable to determine successor and predecessor of a gap." in text
    assert stds_info(tools, "strds", f"{prefix}_points")["number_of_maps"] == 3


def test_overwrite_replaces_a_map_in_relative_time(tools, relative, prefix):
    # The second dataset holds 0 (days 1 to 2) and 30 (days 4 to 5) around
    # the gap, so its new maps are 10 and 20 where the first dataset had 300
    # and 400. The maps have the same names, so the first dataset loses them.
    first = relative()
    tools.t_rast_gapfill(input=first, basename=prefix)
    second = relative(f"{prefix}_other", values=(0, 0, 30))

    tools.t_rast_gapfill(input=second, basename=prefix, overwrite=True)

    assert [(row[0], row[2]) for row in _rows(tools, second)][2:4] == [
        (f"{prefix}_00005_00001", pytest.approx(10.0)),
        (f"{prefix}_00005_00002", pytest.approx(20.0)),
    ]
    assert [row[0] for row in _rows(tools, first)] == [
        f"{first}_a",
        f"{first}_b",
        f"{first}_c",
    ]


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, gappy, prefix):
    text = _refused(
        tools,
        input=gappy({1: (100, 0), 3: (300, 90)}),
        basename=prefix,
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert not tools.g_list(type="raster", pattern=f"{prefix}_2*").stdout.strip()


def test_a_failing_r_series_interp_is_reported_by_the_tool(tools, gappy, prefix):
    # The predecessor of the gap is still registered but gone from the
    # mapset, so r.series.interp fails on its input.
    name = gappy({1: (100, 0), 3: (300, 90)})
    tools.g_remove(type="raster", name=f"{name}_m1", flags="f")

    text = _refused(tools, input=name, basename=prefix)

    assert "Error running r.series.interp" in text
    assert "Traceback" not in text
    assert [row[0] for row in _rows(tools, name)] == [f"{name}_m1", f"{name}_m3"]
    # The map of the gap would be <prefix>_2001_02 (suffix gran).
    assert not tools.g_list(type="raster", pattern=f"{prefix}_2*").stdout.strip()
