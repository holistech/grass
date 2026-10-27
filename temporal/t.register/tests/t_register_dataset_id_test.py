"""Test t.register into datasets whose identifier holds a placeholder word

The extent and the metadata of a dataset are updated with SQL templates whose
placeholders are words such as STDS and SPACETIME_ID. The identifier of the
dataset, name@mapset, goes into these templates and must reach the database
unchanged, also when its name or its mapset contains one of these words.
"""

import pytest

from grass.temporal.testing.data import make_map
from grass.temporal.testing.readback import list_maps, stds_info
from grass.temporal.testing.session import project_session
from grass.tools import Tools

EXPECTED_TIMES = [
    ("2001-01-01 00:00:00", "2001-01-02 00:00:00"),
    ("2001-01-02 00:00:00", "2001-01-03 00:00:00"),
]


def register_two_maps(tools, name, maps):
    tools.t_create(output=name, title="t", description="d")
    tools.t_register(
        input=name,
        maps=",".join(maps),
        start="2001-01-01",
        increment="1 days",
        flags="i",
    )


@pytest.mark.parametrize(
    "word", ["STDS", "GRASS_MAP", "SPACETIME_ID", "SPACETIME_REGISTER_TABLE"]
)
def test_a_placeholder_word_in_the_name_of_the_dataset(tools, prefix, make_maps, word):
    name = f"{word}_{prefix}"
    maps = make_maps(2)

    register_two_maps(tools, name, maps)

    info = stds_info(tools, "strds", name)
    assert info["number_of_maps"] == 2
    assert (info["start_time"], info["end_time"]) == (
        "'2001-01-01 00:00:00'",
        "'2001-01-03 00:00:00'",
    )
    rows = list_maps(tools, "strds", name)
    assert [(row.name, row.start, row.end) for row in rows] == [
        (map_name, *times) for map_name, times in zip(maps, EXPECTED_TIMES, strict=True)
    ]


def test_a_placeholder_word_in_the_name_of_the_mapset(tmp_path):
    with project_session(tmp_path / "project", mapset="STDS_work") as session:
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        maps = ["a", "b"]
        for number, map_name in enumerate(maps, start=1):
            make_map(tools, "raster", map_name, number)

        register_two_maps(tools, "series", maps)

        assert stds_info(tools, "strds", "series")["number_of_maps"] == 2
        rows = list_maps(tools, "strds", "series")
        assert [(row.start, row.end) for row in rows] == EXPECTED_TIMES
