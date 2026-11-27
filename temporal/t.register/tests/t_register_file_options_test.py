"""Test t.register file= with absolute time: names, times, increment and separator

The file formats are those of the manual. Relative time and the ambiguity of
the third column are in t_register_file_test.py.
"""

import pytest

from grass.temporal.testing.data import day, register_file
from grass.temporal.testing.readback import list_maps, stds_info
from grass.tools import ToolError

# Almost every test of the module runs longer than one second (measured
# 18.10.2026 with pytest --durations).
pytestmark = pytest.mark.slow


def _times(tools, name):
    return [(row.start, row.end) for row in list_maps(tools, "strds", name)]


def test_names_with_start_and_increment(tools, make_maps, dataset, tmp_path):
    # One month after each other, as time points: Jan 1, Feb 1, Mar 1.
    maps = make_maps(3)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", maps)

    tools.t_register(
        type="raster", input=name, file=file, start="2001-01-01", increment="1 months"
    )

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", None),
        ("2001-02-01 00:00:00", None),
        ("2001-03-01 00:00:00", None),
    ]
    assert stds_info(tools, "strds", name)["granularity"] == "'1 month'"


def test_names_with_start_only_share_the_start(tools, make_maps, dataset, tmp_path):
    maps = make_maps(3)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", maps)

    tools.t_register(type="raster", input=name, file=file, start="2001-01-01")

    assert set(_times(tools, name)) == {("2001-01-01 00:00:00", None)}


def test_names_with_start_increment_and_interval(tools, make_maps, dataset, tmp_path):
    maps = make_maps(3)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", maps)

    tools.t_register(
        type="raster",
        input=name,
        file=file,
        start="2001-01-01",
        increment="1 months",
        flags="i",
    )

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
        ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
    ]


def test_start_in_the_file(tools, make_maps, dataset, tmp_path):
    maps = make_maps(3)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt",
        [(maps[0], day(0)), (maps[1], day(31)), (maps[2], day(59))],
    )

    tools.t_register(type="raster", input=name, file=file)

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", None),
        ("2001-02-01 00:00:00", None),
        ("2001-03-01 00:00:00", None),
    ]
    assert stds_info(tools, "strds", name)["granularity"] == "'1 month'"


def test_start_and_end_in_the_file(tools, make_maps, dataset, tmp_path):
    maps = make_maps(2)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt",
        [(maps[0], "2001-01-01", "2001-04-01"), (maps[1], "2001-04-01", "2001-07-01")],
    )

    tools.t_register(type="raster", input=name, file=file)

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-04-01 00:00:00"),
        ("2001-04-01 00:00:00", "2001-07-01 00:00:00"),
    ]
    assert stds_info(tools, "strds", name)["granularity"] == "'3 months'"


def test_increment_without_start_option_is_refused_with_times_in_the_file(
    tools, make_maps, dataset, tmp_path
):
    # The check for the missing start option comes before the file is read.
    maps = make_maps(1)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", [(maps[0], "2001-01-01")])

    with pytest.raises(
        ToolError, match=r"increment\s+option\s+requires\s+the\s+start\s+option"
    ):
        tools.t_register(type="raster", input=name, file=file, increment="1 months")

    assert list_maps(tools, "strds", name) == []


def test_interval_flag_without_start_option_is_refused_with_times_in_the_file(
    tools, make_maps, dataset, tmp_path
):
    maps = make_maps(1)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", [(maps[0], "2001-01-01", "2001-04-01")])

    with pytest.raises(
        ToolError, match=r"interval\s+flag\s+requires\s+the\s+start\s+option"
    ):
        tools.t_register(type="raster", input=name, file=file, flags="i")


def test_increment_is_ignored_when_the_file_has_times(
    tools, make_maps, dataset, tmp_path
):
    maps = make_maps(2)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt", [(maps[0], "2001-01-01"), (maps[1], "2001-01-05")]
    )

    result = tools.t_register(
        type="raster",
        input=name,
        file=file,
        start="2000-01-01",
        increment="1 months",
    )

    assert "increment option will be ignored" in " ".join(result.stderr.split())
    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", None),
        ("2001-01-05 00:00:00", None),
    ]


def test_interval_flag_is_ignored_when_the_file_has_times(
    tools, make_maps, dataset, tmp_path
):
    maps = make_maps(1)
    name = dataset()
    file = register_file(tmp_path / "maps.txt", [(maps[0], "2001-01-01")])

    result = tools.t_register(
        type="raster", input=name, file=file, start="2000-01-01", flags="i"
    )

    assert "interval flag will be ignored" in " ".join(result.stderr.split())
    assert _times(tools, name) == [("2001-01-01 00:00:00", None)]


def test_fully_qualified_name_and_semantic_label_in_the_file(
    tools, make_maps, dataset, tmp_path
):
    # Four columns: name@mapset, start, end and the semantic label.
    maps = make_maps(2)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt",
        [
            (f"{maps[0]}@PERMANENT", "2001-01-01", "2001-04-01", "S2_1"),
            (f"{maps[1]}@PERMANENT", "2001-04-01", "2001-07-01", "S2_1"),
        ],
    )

    tools.t_register(type="raster", input=name, file=file)

    info = stds_info(tools, "strds", name)
    assert (info["number_of_semantic_labels"], info["semantic_labels"]) == (1, "S2_1")
    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-04-01 00:00:00"),
        ("2001-04-01 00:00:00", "2001-07-01 00:00:00"),
    ]


@pytest.mark.parametrize(
    ("option", "character"),
    [("comma", ","), ("tab", "\t"), (";", ";"), ("pipe", "|")],
)
def test_separator(tools, make_maps, dataset, tmp_path, option, character):
    maps = make_maps(2)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt",
        [(maps[0], "2001-01-01", "2001-02-01"), (maps[1], "2001-02-01", "2001-03-01")],
        separator=character,
    )

    tools.t_register(type="raster", input=name, file=file, separator=option)

    assert _times(tools, name) == [
        ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
        ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
    ]


def test_wrong_separator_does_not_find_the_times(tools, make_maps, dataset, tmp_path):
    # With the default pipe the whole line is one name: the map is not found.
    maps = make_maps(1)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt", [(maps[0], "2001-01-01")], separator=","
    )

    with pytest.raises(ToolError, match=r"not\s+found"):
        tools.t_register(type="raster", input=name, file=file)


def test_maps_after_an_empty_line_are_registered(tools, make_maps, dataset, tmp_path):
    maps = make_maps(2)
    name = dataset()
    file = tmp_path / "maps.txt"
    file.write_text(f"{maps[0]}|2001-01-01\n\n{maps[1]}|2001-01-02\n")

    tools.t_register(type="raster", input=name, file=file)

    assert [row.name for row in list_maps(tools, "strds", name)] == maps


def test_a_refused_map_leaves_no_semantic_label_on_the_maps_before_it(
    tools, make_maps, dataset, tmp_path
):
    # The second row has no time zone in a dataset whose first map has one, so
    # the call is refused; the label of the first row must not be written.
    maps = make_maps(2)
    name = dataset()
    file = register_file(
        tmp_path / "maps.txt",
        [
            (
                maps[0],
                "2001-01-01 10:00:00 +02:00",
                "2001-01-02 10:00:00 +02:00",
                "S2_1",
            ),
            (maps[1], "2001-01-02 10:00:00", "2001-01-03 10:00:00", "S2_2"),
        ],
    )

    with pytest.raises(ToolError, match="time zone"):
        tools.t_register(type="raster", input=name, file=file)

    info = tools.r_info(map=maps[0], flags="e").keyval
    assert info["semantic_label"].strip('"') == "none"
    assert list_maps(tools, "strds", name) == []
