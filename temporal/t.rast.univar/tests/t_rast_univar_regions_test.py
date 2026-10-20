"""Test -r and region_relation of t.rast.univar on maps with regions of their own

The four maps of conftest.py are squares: ur_all from (0, 0) to (4, 4) holding
10, ur_in from (1, 1) to (3, 3) holding 20, ur_part from (2, 2) to (6, 6)
holding 30 and ur_out from (10, 10) to (12, 12) holding 40. The statistics are
calculated in the current region, which is the square from (1, 1) to (3, 3)
(four cells) unless the test says otherwise.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

COLUMNS = ["id", "non_null_cells", "null_cells", "mean"]


def _rows(tools, regions, **options):
    result = tools.t_rast_univar(input=regions, **options)
    lines = result.stdout.splitlines()
    if not lines:
        return []
    header = lines[0].split("|")
    return [
        {key: row[key] for key in COLUMNS}
        for row in (
            dict(zip(header, line.split("|"), strict=True)) for line in lines[1:]
        )
    ]


def _cells(rows):
    return [
        (row["id"].split("@")[0], row["non_null_cells"], row["null_cells"])
        for row in rows
    ]


@pytest.fixture(autouse=True)
def _region(tools, regions):
    tools.g_region(s=1, n=3, w=1, e=3, res=1)


def test_the_statistics_are_taken_in_the_current_region(tools, regions):
    rows = _rows(tools, regions)

    # ur_all and ur_in cover the four cells; ur_part only the cell (2, 2) to
    # (3, 3); ur_out none, so its four cells are null
    assert _cells(rows) == [
        ("ur_all", "4", "0"),
        ("ur_in", "4", "0"),
        ("ur_part", "1", "3"),
        ("ur_out", "0", "4"),
    ]


def test_today_a_map_without_a_valid_cell_gets_meaningless_statistics(tools, regions):
    result = tools.t_rast_univar(input=regions, where="start_time >= '2001-01-04'")

    fields = result.stdout.splitlines()[1].split("|")
    # min is nan and max the smallest double instead of nan too. r.univar
    # alone prints the same for a map outside the region; the tool passes
    # its numbers on, the defect is r.univar's.
    assert fields[6] == "nan"
    assert fields[7] == "-1.79769313486232e+308"


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.univar prints the smallest double instead of nan as maximum for a map without a valid cell",
)
def test_a_map_without_a_valid_cell_has_no_value_for_min_and_max(tools, regions):
    result = tools.t_rast_univar(input=regions, where="start_time >= '2001-01-04'")

    fields = result.stdout.splitlines()[1].split("|")
    assert fields[6] == fields[7] == "nan"


def test_the_r_flag_uses_the_region_of_each_map(tools, regions):
    rows = _rows(tools, regions, flags="r")

    assert _cells(rows) == [
        ("ur_all", "16", "0"),
        ("ur_in", "4", "0"),
        ("ur_part", "16", "0"),
        ("ur_out", "4", "0"),
    ]
    assert [row["mean"] for row in rows] == ["10", "20", "30", "40"]


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        # Maps that touch the region: not ur_out
        ("overlaps", ["ur_all", "ur_in", "ur_part"]),
        # Maps that contain the region, an equal square included
        ("contains", ["ur_all", "ur_in"]),
        # Maps inside the region: only the equal square
        ("is_contained", ["ur_in"]),
    ],
)
def test_region_relation_selects_the_maps(tools, regions, relation, expected):
    rows = _rows(tools, regions, region_relation=relation)

    assert [row["id"].split("@")[0] for row in rows] == expected


def test_region_relation_changes_nothing_in_the_cells_counted(tools, regions):
    rows = _rows(tools, regions, region_relation="overlaps")

    assert _cells(rows) == [
        ("ur_all", "4", "0"),
        ("ur_in", "4", "0"),
        ("ur_part", "1", "3"),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_larger_region_changes_the_relations(tools, regions):
    # The square from (-1, -1) to (5, 5) has 36 cells and contains ur_all and
    # ur_in; ur_part reaches out of it and ur_out lies far away
    tools.g_region(s=-1, n=5, w=-1, e=5, res=1)

    inside = _rows(tools, regions, region_relation="is_contained")
    containing = _rows(tools, regions, region_relation="contains")
    touching = _rows(tools, regions, region_relation="overlaps")

    assert _cells(inside) == [("ur_all", "16", "20"), ("ur_in", "4", "32")]
    assert containing == []
    # ur_part and the region share the square from (2, 2) to (5, 5): 9 cells
    assert _cells(touching) == [
        ("ur_all", "16", "20"),
        ("ur_in", "4", "32"),
        ("ur_part", "9", "27"),
    ]


def test_r_flag_and_region_relation_together(tools, regions):
    rows = _rows(tools, regions, flags="r", region_relation="overlaps")

    assert _cells(rows) == [
        ("ur_all", "16", "0"),
        ("ur_in", "4", "0"),
        ("ur_part", "16", "0"),
    ]


def test_a_wrong_region_relation_is_refused_by_the_parser(tools, regions):
    with pytest.raises(ToolError) as error:
        tools.t_rast_univar(input=regions, region_relation="touches")

    assert "out of range for parameter <region_relation>" in message(error.value)
