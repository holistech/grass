"""Test the end that t.snap gives the last instant of a month series

The instants 31 January, 28 February and 31 March have the granularity
"1 month", so the last one ends a month later, on 30 April. The month is
counted on the series of the first map: an instant on 30 April in a series
from 31 January ends on 31 May, and the snapped dataset keeps the granularity
"1 month".

The instants on the first of January 2024 and the first of March 2025 are
14 months apart, so the last one ends 14 months later.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

D = datetime


def test_last_instant_of_month_end_series_ends_a_month_later(tools):
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec("month_end_1", 1, D(2026, 1, 31)),
            MapSpec("month_end_2", 2, D(2026, 2, 28)),
            MapSpec("month_end_3", 3, D(2026, 3, 31)),
        ],
    )
    tools.t_snap(input="month_ends")
    assert [
        (row.start, row.end) for row in list_maps(tools, "strds", "month_ends")
    ] == [
        ("2026-01-31 00:00:00", "2026-02-28 00:00:00"),
        ("2026-02-28 00:00:00", "2026-03-31 00:00:00"),
        ("2026-03-31 00:00:00", "2026-04-30 00:00:00"),
    ]


@pytest.mark.parametrize(
    ("starts", "last_end"),
    [
        (
            [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)],
            D(2026, 5, 31),
        ),
        ([D(2026, 1, 31), D(2026, 2, 28)], D(2026, 3, 31)),
    ],
    ids=["to 30 April", "to 28 February"],
)
def test_last_instant_ends_on_the_month_series_of_the_first(tools, starts, last_end):
    # One month added to 30 April would end on 30 May, and to 28 February on
    # 28 March; the dataset then had the granularity "1 day" or "28 days".
    name = f"series_{len(starts)}"
    create_stds(
        tools,
        "strds",
        name,
        [MapSpec(f"{name}_{n}", n, start) for n, start in enumerate(starts, 1)],
    )
    tools.t_snap(input=name)
    ends = [*starts[1:], last_end]
    assert [(row.start, row.end) for row in list_maps(tools, "strds", name)] == [
        (f"{start:%Y-%m-%d %H:%M:%S}", f"{end:%Y-%m-%d %H:%M:%S}")
        for start, end in zip(starts, ends, strict=True)
    ]
    assert tools.t_info(input=name, flags="g").keyval["granularity"] == "'1 month'"


def test_last_instant_of_month_firsts_over_a_year_ends_14_months_later(tools, prefix):
    """Before 05.11.2026 the granularity counted 2 months and the last
    instant ended on 1 May 2025"""
    create_stds(
        tools,
        "strds",
        prefix,
        [
            MapSpec(f"{prefix}_1", 1, D(2024, 1, 1)),
            MapSpec(f"{prefix}_2", 2, D(2025, 3, 1)),
        ],
    )
    tools.t_snap(input=prefix)
    assert [(row.start, row.end) for row in list_maps(tools, "strds", prefix)] == [
        ("2024-01-01 00:00:00", "2025-03-01 00:00:00"),
        ("2025-03-01 00:00:00", "2026-05-01 00:00:00"),
    ]


@pytest.fixture(scope="module")
def foreign_copy(tmp_path_factory):
    """Tools in the mapset "second" with a dataset of copies of maps of "first"

    The dataset ds of "first" is registered in "second" by an extract without
    expression, so "second" holds the dataset copy whose maps belong to
    "first".
    """
    project = tmp_path_factory.mktemp("foreign_copy") / "project"
    with (
        project_session(project, mapset="second") as second,
        mapset_session(second, "first") as first,
    ):
        work, owner = (
            Tools(session=session, consistent_return_value=True, capture_stderr=True)
            for session in (second, first)
        )
        for tools in (work, owner):
            tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            owner,
            "strds",
            "ds",
            [
                MapSpec("r_1", 1, D(2001, 1, 1), D(2001, 1, 2)),
                MapSpec("r_2", 2, D(2001, 1, 5), D(2001, 1, 6)),
            ],
        )
        work.g_mapsets(operation="add", mapset="first")
        work.t_rast_extract(input="ds@first", output="copy")
        work.g_gisenv(set="TGIS_DISABLE_MAPSET_CHECK=True")
        yield SimpleNamespace(work=work, owner=owner)


def _named_times(tools, name):
    return [(row.name, row.start, row.end) for row in list_maps(tools, "strds", name)]


def test_disabled_mapset_check_refuses_before_snapping(foreign_copy):
    """The extent of the dataset of the owner cannot be updated, so no map moves

    With the mapset check off the maps of "first" were written before the
    dataset of "first" was found to be out of reach.
    """
    work, owner = foreign_copy.work, foreign_copy.owner
    before = (_named_times(work, "copy"), _named_times(owner, "ds"), inventory(work))

    with pytest.raises(ToolError) as error:
        work.t_snap(input="copy")
    text = message(error.value)

    assert "Unable to update dataset <ds@first>" in text
    assert "Traceback" not in text
    assert (
        _named_times(work, "copy"),
        _named_times(owner, "ds"),
        inventory(work),
    ) == before
