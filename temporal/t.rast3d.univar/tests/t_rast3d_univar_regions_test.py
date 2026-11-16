"""Test region_relation of t.rast3d.univar on maps with cubes of their own

The five maps of conftest.py are cubes: ur3_all from (0, 0, 0) to (4, 4, 4)
holding 10, ur3_in from (1, 1, 1) to (3, 3, 3) holding 20, ur3_part from
(2, 2, 2) to (6, 6, 6) holding 30, ur3_out from (10, 10, 10) to (12, 12, 12)
holding 40 and ur3_high above ur3_in, from (1, 1, 10) to (3, 3, 12), holding
50. The statistics are calculated in the current region, which is the cube
from (1, 1, 1) to (3, 3, 3) (eight voxels) unless the test says otherwise.
The tool has no flag for the regions of the maps (-r of t.rast.univar).
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

COLUMNS = ["id", "non_null_cells", "null_cells", "mean"]


def _rows(tools, regions, **options):
    result = tools.t_rast3d_univar(input=regions, **options)
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
    tools.g_region(s=1, n=3, w=1, e=3, b=1, t=3, res=1, res3=1)


def test_the_statistics_are_taken_in_the_current_region(tools, regions):
    rows = _rows(tools, regions)

    # ur3_all and ur3_in cover the eight voxels; ur3_part only the voxel (2, 2,
    # 2) to (3, 3, 3); ur3_out and ur3_high none, the latter because of its
    # height alone
    assert _cells(rows) == [
        ("ur3_all", "8", "0"),
        ("ur3_in", "8", "0"),
        ("ur3_part", "1", "7"),
        ("ur3_out", "0", "8"),
        ("ur3_high", "0", "8"),
    ]


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        # Maps that touch the region: not ur3_out and not ur3_high
        ("overlaps", ["ur3_all", "ur3_in", "ur3_part"]),
        # Maps that contain the region, an equal cube included
        ("contains", ["ur3_all", "ur3_in"]),
        # Maps inside the region: only the equal cube
        ("is_contained", ["ur3_in"]),
    ],
)
def test_region_relation_selects_the_maps(tools, regions, relation, expected):
    rows = _rows(tools, regions, region_relation=relation)

    assert [row["id"].split("@")[0] for row in rows] == expected


def test_region_relation_changes_nothing_in_the_cells_counted(tools, regions):
    rows = _rows(tools, regions, region_relation="overlaps")

    assert _cells(rows) == [
        ("ur3_all", "8", "0"),
        ("ur3_in", "8", "0"),
        ("ur3_part", "1", "7"),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_larger_region_changes_the_relations(tools, regions):
    # The cube from (-1, -1, -1) to (5, 5, 5) has 216 voxels and contains
    # ur3_all and ur3_in; ur3_part reaches out of it and the other two lie
    # far away
    tools.g_region(s=-1, n=5, w=-1, e=5, b=-1, t=5, res=1, res3=1)

    inside = _rows(tools, regions, region_relation="is_contained")
    containing = _rows(tools, regions, region_relation="contains")
    touching = _rows(tools, regions, region_relation="overlaps")

    assert _cells(inside) == [("ur3_all", "64", "152"), ("ur3_in", "8", "208")]
    assert containing == []
    # ur3_part and the region share the cube from (2, 2, 2) to (5, 5, 5):
    # 27 voxels
    assert _cells(touching) == [
        ("ur3_all", "64", "152"),
        ("ur3_in", "8", "208"),
        ("ur3_part", "27", "189"),
    ]


def test_region_relation_and_where_together(tools, regions):
    rows = _rows(
        tools,
        regions,
        region_relation="overlaps",
        where="start_time >= '2001-01-02'",
    )

    assert [row["id"].split("@")[0] for row in rows] == ["ur3_in", "ur3_part"]


def test_a_wrong_region_relation_is_refused_by_the_parser(tools, regions):
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_univar(input=regions, region_relation="touches")

    assert "out of range for parameter <region_relation>" in message(error.value)
