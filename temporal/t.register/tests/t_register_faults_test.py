"""Test file=-, the warnings and the layer check of t.register

The file "-" is the standard input. A warning about a time is given only when
the time is ignored; a layer of a vector map is checked with or without a
database link; the message about a time zone reads right in both directions.
"""

import subprocess
from io import StringIO

import pytest

from grass.temporal.testing.data import register_file
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

IGNORED = "will be ignored because of time stamps"


def test_file_dash_reads_stdin(tools, make_maps, dataset):
    maps = make_maps(2)
    name = dataset()
    text = f"{maps[0]}|2001-01-01|2001-01-02\n{maps[1]}|2001-01-02|2001-01-03\n"

    tools.t_register(input=name, file=StringIO(text))

    assert [row.name for row in list_maps(tools, "strds", name)] == maps


def test_file_dash_in_the_shell(tools, make_maps, dataset):
    maps = make_maps(2)
    name = dataset()
    text = f"{maps[0]}|2001-01-01|2001-01-02\n{maps[1]}|2001-01-02|2001-01-03\n"

    result = subprocess.run(
        ["t.register", f"input={name}", "file=-"],
        input=text,
        text=True,
        capture_output=True,
        # The session environment of the tools, which has the project.
        env=tools._original_env,  # noqa: SLF001
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert [row.name for row in list_maps(tools, "strds", name)] == maps


def test_file_dash_with_nothing_on_stdin_is_an_empty_file(tools, dataset, tmp_path):
    name = dataset()
    empty = tmp_path / "empty.txt"
    empty.write_text("")

    from_file = tools.t_register(input=name, file=empty)
    from_stdin = tools.t_register(input=name, file=StringIO(""))

    assert from_stdin.returncode == from_file.returncode == 0
    assert list_maps(tools, "strds", name) == []


def test_mixed_file_warns_only_when_all_lines_have_time(
    tools, make_maps, dataset, tmp_path
):
    maps = make_maps(3)
    name = dataset()
    mixed = register_file(
        tmp_path / "mixed.txt",
        [(maps[0], "2001-01-01"), (maps[1],), (maps[2], "2001-01-05", "2001-01-06")],
    )

    result = tools.t_register(
        input=name, file=mixed, start="2001-03-01", increment="1 days"
    )

    assert IGNORED not in message(result)
    rows = {row.name: row.start for row in list_maps(tools, "strds", name)}
    # The row without a time is moved by the increment, as the warning of
    # the old text denied.
    assert rows[maps[1]] == "2001-03-02 00:00:00"


def test_file_with_a_time_on_every_line_warns(tools, make_maps, dataset, tmp_path):
    maps = make_maps(2)
    name = dataset()
    full = register_file(
        tmp_path / "full.txt",
        [(maps[0], "2001-01-01"), (maps[1], "2001-01-05", "2001-01-06")],
    )

    result = tools.t_register(
        input=name, file=full, start="2001-03-01", increment="1 days"
    )

    assert IGNORED in message(result)


def test_registered_map_without_start_gives_no_warning(tools, make_maps, dataset):
    maps = make_maps(2)
    first = dataset(suffix="1")
    second = dataset(suffix="2")
    tools.t_register(
        input=first, maps=",".join(maps), start="2001-01-01", increment="1 days"
    )

    result = tools.t_register(input=second, maps=",".join(maps))

    assert "already registered" not in message(result)
    assert [row.name for row in list_maps(tools, "strds", second)] == maps


def test_registered_map_with_start_still_warns(tools, make_maps, dataset):
    maps = make_maps(1)
    first = dataset(suffix="1")
    second = dataset(suffix="2")
    tools.t_register(input=first, maps=maps[0], start="2001-01-01")

    result = tools.t_register(input=second, maps=maps[0], start="2001-02-01")

    assert "already registered" in message(result)
    assert [row.start for row in list_maps(tools, "strds", second)] == [
        "2001-01-01 00:00:00"
    ]


@pytest.fixture
def unlinked_vector(tools, prefix):
    """A vector map without a table, with categories in layer 1 only"""
    name = f"{prefix}_v"
    tools.v_in_ascii(
        input=StringIO("1|1|1\n"),
        output=name,
        format="point",
        flags="t",
        x=1,
        y=2,
        cat=3,
    )
    return name


def test_vector_layer_without_link_is_checked(tools, dataset, unlinked_vector):
    name = dataset(stds_type="stvds")
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_register(
            type="vector", input=name, maps=f"{unlinked_vector}:9", start="2001-01-01"
        )

    assert "has no layer 9" in message(error.value)
    assert inventory(tools) == before
    assert list_maps(tools, "stvds", name) == []


def test_vector_layer_without_link_that_has_categories_is_registered(
    tools, dataset, unlinked_vector
):
    name = dataset(stds_type="stvds")

    tools.t_register(
        type="vector", input=name, maps=f"{unlinked_vector}:1", start="2001-01-01"
    )

    assert [row.name for row in list_maps(tools, "stvds", name)] == [unlinked_vector]


@pytest.mark.parametrize(
    ("first", "second", "second_part", "dataset_part"),
    [
        (
            "2001-01-01 10:00:00 +02:00",
            "2001-01-02 10:00:00",
            "has no time zone",
            "has one",
        ),
        (
            "2001-01-01 10:00:00",
            "2001-01-02 10:00:00 +02:00",
            "has a time zone",
            "has none",
        ),
    ],
)
def test_time_zone_message(
    tools, make_maps, dataset, first, second, second_part, dataset_part
):
    maps = make_maps(2)
    name = dataset()
    tools.t_register(input=name, maps=maps[0], start=first)

    with pytest.raises(ToolError) as error:
        tools.t_register(input=name, maps=maps[1], start=second)

    text = message(error.value)
    assert f"Its time {second_part}, the time of the maps" in text
    assert text.rstrip().endswith(f"{dataset_part}.")
