"""Test the granule, the standard output and the gaps of t.rast.list

A relative granule is a number in the unit of the dataset, also with that
unit; another unit is refused with a message. output=- writes to the standard
output. A dataset of a single time instance has no granularity, and the
message says so. A month series from 31 January has the granularity
"1 month". A gap is time that no map covers. The granules reach the end of
the dataset.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, message
from grass.temporal.testing.session import project_session
from grass.temporal.testing.versions import downgrade_to_version_2
from grass.tools import ToolError, Tools

D = datetime
COLUMNS = "name,start_time,end_time"


def rows(result):
    """The lines of the listing without the header, split at the bar"""
    return [line.split("|") for line in result.stdout.splitlines()[1:]]


@pytest.fixture(scope="module")
def model(tools):
    """Three maps of 6 hours each in relative time"""
    create_stds(
        tools,
        "strds",
        "model",
        [MapSpec(f"step_{k + 1}", k, 6 * k, 6 * k + 6) for k in range(3)],
        temporaltype="relative",
        unit="hours",
    )
    return "model"


@pytest.mark.parametrize("granule", ["12", "12 hours", "12 hour"])
def test_gran_with_number_granule_on_relative_time(tools, model, granule):
    """The granules of 12 hours start at 0 and 12 and take their first map"""
    result = tools.t_rast_list(
        input=model, method="gran", granule=granule, columns=COLUMNS
    )
    assert rows(result) == [["step_1", "0", "12"], ["step_3", "12", "24"]]


@pytest.mark.parametrize("granule", ["1 day", "12 foo", "0"])
def test_gran_with_granule_of_another_unit_is_refused(tools, model, granule):
    """Another unit and a number below 1 end with a message, no traceback"""
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(input=model, method="gran", granule=granule)
    text = message(error.value)
    assert f"Invalid granule <{granule}>" in text
    assert "<hours>" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


def test_output_dash_writes_to_stdout(tools, model, tmp_path, monkeypatch):
    """output=- prints the listing and makes no file of the name -"""
    monkeypatch.chdir(tmp_path)
    result = tools.t_rast_list(input=model, columns="name", output="-")
    assert result.stdout.split() == ["name", "step_1", "step_2", "step_3"]
    assert list(tmp_path.iterdir()) == []


def test_gran_on_single_instant_names_missing_granularity(tools):
    create_stds(tools, "strds", "instant", [MapSpec("instant_1", 1, D(2026, 3, 1))])
    with pytest.raises(ToolError) as error:
        tools.t_rast_list(input="instant", method="gran")
    text = message(error.value)
    assert "Space time dataset <instant@" in text
    assert "has no granularity" in text
    assert "Give a granule or use another method" in text
    assert "None" not in text


def test_gran_of_month_end_series_lists_months(tools):
    """A series from 31 January has the granularity 1 month: one granule per
    map, cut to the end of the shorter month"""
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    result = tools.t_rast_list(input="month_ends", method="gran", columns=COLUMNS)
    assert rows(result) == [
        ["month_end_1", "2026-01-31 00:00:00", "2026-02-28 00:00:00"],
        ["month_end_2", "2026-02-28 00:00:00", "2026-03-31 00:00:00"],
        ["month_end_3", "2026-03-31 00:00:00", "2026-04-30 00:00:00"],
    ]


def test_gap_inside_longer_map_is_not_a_gap(tools):
    """m_1 1 to 11 January covers the time between m_2 and m_3"""
    create_stds(
        tools,
        "strds",
        "cover",
        [
            MapSpec("cover_1", 1, D(2026, 1, 1), D(2026, 1, 11)),
            MapSpec("cover_2", 2, D(2026, 1, 3), D(2026, 1, 5)),
            MapSpec("cover_3", 3, D(2026, 1, 8), D(2026, 1, 13)),
            MapSpec("cover_4", 4, D(2026, 1, 15), D(2026, 1, 16)),
        ],
    )
    result = tools.t_rast_list(input="cover", method="deltagaps", columns=COLUMNS)
    assert rows(result) == [
        ["cover_1", "2026-01-01 00:00:00", "2026-01-11 00:00:00"],
        ["cover_2", "2026-01-03 00:00:00", "2026-01-05 00:00:00"],
        ["cover_3", "2026-01-08 00:00:00", "2026-01-13 00:00:00"],
        ["None", "2026-01-13 00:00:00", "2026-01-15 00:00:00"],
        ["cover_4", "2026-01-15 00:00:00", "2026-01-16 00:00:00"],
    ]


def test_gran_ends_at_end_of_dataset(tools):
    """nest_a 1 to 3 July, nest_b 1 to 2 July: two granules of a day"""
    create_stds(
        tools,
        "strds",
        "nest",
        [
            MapSpec("nest_a", 1, D(2026, 7, 1), D(2026, 7, 3)),
            MapSpec("nest_b", 2, D(2026, 7, 1), D(2026, 7, 2)),
        ],
    )
    result = tools.t_rast_list(
        input="nest", method="gran", columns="start_time,end_time"
    )
    assert rows(result) == [
        ["2026-07-01 00:00:00", "2026-07-02 00:00:00"],
        ["2026-07-02 00:00:00", "2026-07-03 00:00:00"],
    ]


def test_gran_of_a_selection_counts_from_the_start_of_the_dataset(tools):
    """A selection from 28 February of the series from 31 January has the
    granules 28 February to 31 March and 31 March to 30 April"""
    ends = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]
    create_stds(
        tools,
        "strds",
        "month_selection",
        [
            MapSpec(f"month_selection_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ends), start=1)
        ],
    )
    result = tools.t_rast_list(
        input="month_selection",
        method="gran",
        columns=COLUMNS,
        where="start_time >= '2026-02-28'",
    )
    assert rows(result) == [
        ["month_selection_2", "2026-02-28 00:00:00", "2026-03-31 00:00:00"],
        ["month_selection_3", "2026-03-31 00:00:00", "2026-04-30 00:00:00"],
    ]


def test_old_database_points_to_upgrade(tmp_path):
    """A column that only the current database has is named with t.upgrade"""
    with project_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools, "strds", "series", [MapSpec("map1", 1, D(2026, 1, 1), D(2026, 2, 1))]
        )
        downgrade_to_version_2(session)
        with pytest.raises(ToolError) as error:
            tools.t_rast_list(input="series", columns="name,semantic_label")
        text = message(error.value)
        # The warning about the version names t.upgrade already; the error
        # that ends the run has to name it, too.
        error_text = text.rsplit("ERROR:", 1)[1]
        assert "semantic labels" in error_text
        assert "t.upgrade" in error_text
        # Columns that version 2 has are still listed.
        result = tools.t_rast_list(input="series", columns="name")
        assert result.stdout.split()[1:] == ["map1"]
