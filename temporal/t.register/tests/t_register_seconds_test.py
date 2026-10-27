"""Test that t.register stores time stamps in whole seconds

The temporal database has the resolution of one second. A start time with a
fraction of a second is cut to the second, not rounded, and read back as such.
An interval whose start and end fall into the same second is a time instance.
"""

import pytest

from grass.temporal.testing.readback import list_maps, stds_info


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        ("2001-01-01 10:00:00.5", "2001-01-01 10:00:00"),
        ("2001-01-01 10:00:00.999999", "2001-01-01 10:00:00"),
        ("2001-01-01 10:00:00.000001", "2001-01-01 10:00:00"),
    ],
)
def test_a_fraction_of_a_second_is_cut(
    tools, prefix, make_maps, dataset, start, expected
):
    name = dataset()
    (raster,) = make_maps(1)

    tools.t_register(type="raster", input=name, maps=raster, start=start)

    assert [row.start for row in list_maps(tools, "strds", name)] == [expected]


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (
            "2001-01-01 10:00:00.2",
            "2001-01-01 10:00:00.7",
            ("2001-01-01 10:00:00", None),
        ),
        (
            "2001-01-01 10:00:00",
            "2001-01-01 10:00:00.5",
            ("2001-01-01 10:00:00", None),
        ),
        (
            "2001-01-01 10:00:00.7",
            "2001-01-01 10:00:01.2",
            ("2001-01-01 10:00:00", "2001-01-01 10:00:01"),
        ),
    ],
)
def test_an_interval_inside_one_second_becomes_a_time_instance(
    tools, prefix, make_maps, dataset, tmp_path, start, end, expected
):
    # Cut to whole seconds, start and end of the first two intervals are
    # equal, and equal times give a time instance, as when they are equal in
    # the input. An interval across a second boundary stays an interval.
    name = dataset()
    (raster,) = make_maps(1)
    map_file = tmp_path / "maps.txt"
    map_file.write_text(f"{raster}|{start}|{end}\n")

    tools.t_register(type="raster", input=name, file=map_file)

    assert [(row.start, row.end) for row in list_maps(tools, "strds", name)] == [
        expected
    ]
    assert stds_info(tools, "strds", name)["number_of_maps"] == 1
