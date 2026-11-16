"""Test the granularity that t.info shows for a month series from a month end

A month step that is cut to the end of a shorter month counts as a month: the
series from 31 January (28 February, 31 March) has the granularity "1 month".
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import map_info, stds_info
from grass.temporal.testing.session import mapset_session, project_session
from grass.temporal.testing.versions import downgrade_to_version_2
from grass.tools import Tools

D = datetime


@pytest.mark.parametrize(
    ("starts", "expected"),
    [
        ([D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)], "1 month"),
        ([D(2026, 1, 15), D(2026, 2, 15), D(2026, 3, 15)], "1 month"),
        ([D(2026, 1, 31), D(2026, 2, 27), D(2026, 3, 31)], "1 day"),
    ],
    ids=["month ends", "15th", "one day short"],
)
def test_month_end_series_has_one_month(tools, prefix, starts, expected):
    create_stds(
        tools,
        "strds",
        prefix,
        [
            MapSpec(f"{prefix}_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(starts), start=1)
        ],
    )
    assert stds_info(tools, "strds", prefix)["granularity"] == f"'{expected}'"


def test_semantic_label_of_map(tools, prefix):
    create_stds(
        tools,
        "strds",
        prefix,
        [
            MapSpec(
                f"{prefix}_1", 1, D(2026, 1, 1), D(2026, 2, 1), semantic_label="S2_B8"
            )
        ],
    )
    assert map_info(tools, "raster", f"{prefix}_1")["semantic_label"] == "S2_B8"
    box = tools.t_info(type="raster", input=f"{prefix}_1").stdout
    assert "Semantic label:............. S2_B8" in box


def test_map_without_semantic_label_shows_none(tools, prefix):
    create_stds(
        tools,
        "strds",
        prefix,
        [MapSpec(f"{prefix}_1", 1, D(2026, 1, 1), D(2026, 2, 1))],
    )
    assert map_info(tools, "raster", f"{prefix}_1")["semantic_label"] == "None"


def test_history_has_no_backslash_before_comment(tools, prefix):
    create_stds(
        tools,
        "strds",
        prefix,
        [MapSpec(f"{prefix}_1", 1, D(2026, 1, 1), D(2026, 2, 1))],
    )
    tools.t_register(
        type="raster",
        input=prefix,
        maps=f"{prefix}_1",
        start="2026-01-01",
        increment="1 months",
        flags="i",
    )
    lines = tools.t_info(flags="h", type="strds", input=prefix).stdout.splitlines()
    assert any(line.startswith("t.register") for line in lines)
    for before, after in pairwise(lines):
        if after.startswith("#"):
            assert not before.endswith("\\"), before
    # A command of several lines is still continued with a backslash.
    assert any(line.endswith(" \\") for line in lines)


def test_map_of_a_mapset_with_an_older_database(tmp_path):
    """The columns that are read are those of the database that is read

    The current mapset has a database of version 3 and the mapset of the map
    one of version 2, which has no column for the semantic label.
    """
    with project_session(tmp_path / "project", mapset="work") as work:
        with mapset_session(work, "other") as other:
            other_tools = Tools(session=other, consistent_return_value=True)
            other_tools.g_region(n=1, s=0, e=1, w=0, res=1)
            create_stds(
                other_tools,
                "strds",
                "series",
                [MapSpec("m", 1, D(2026, 1, 1), D(2026, 2, 1), semantic_label="S2_B8")],
            )
            downgrade_to_version_2(other)
        tools = Tools(session=work, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        tools.t_create(type="strds", output="mine", title="t", description="d")
        tools.g_mapsets(operation="add", mapset="other")

        info = tools.t_info(type="raster", input="m@other", flags="g").keyval

        assert info["name"] == "m"
        assert info["semantic_label"] == "None"
