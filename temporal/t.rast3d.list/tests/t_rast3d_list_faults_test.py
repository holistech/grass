"""Test the granule, the standard output and the granularity of t.rast3d.list

A relative granule is a number in the unit of the dataset, also with that
unit; another unit is refused with a message. output=- writes to the standard
output. A dataset of a single time instance has no granularity, and the
message says so.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

COLUMNS = "name,start_time,end_time"


def rows(result):
    """The lines of the listing without the header, split at the bar"""
    return [line.split("|") for line in result.stdout.splitlines()[1:]]


@pytest.fixture(scope="module")
def model(tools):
    """Three 3D maps of 6 hours each in relative time"""
    create_stds(
        tools,
        "str3ds",
        "model",
        [MapSpec(f"step_{k + 1}", k, 6 * k, 6 * k + 6) for k in range(3)],
        temporaltype="relative",
        unit="hours",
    )
    return "model"


@pytest.mark.parametrize("granule", ["12", "12 hours"])
def test_gran_with_number_granule_on_relative_time(tools, model, granule):
    """The granules of 12 hours start at 0 and 12 and take their first map"""
    result = tools.t_rast3d_list(
        input=model, method="gran", granule=granule, columns=COLUMNS
    )
    assert rows(result) == [["step_1", "0", "12"], ["step_3", "12", "24"]]


def test_gran_with_granule_of_another_unit_is_refused(tools, model):
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_list(input=model, method="gran", granule="1 day")
    text = message(error.value)
    assert "Invalid granule <1 day>" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


def test_output_dash_writes_to_stdout(tools, model, tmp_path, monkeypatch):
    """output=- prints the listing and makes no file of the name -"""
    monkeypatch.chdir(tmp_path)
    result = tools.t_rast3d_list(input=model, columns="name", output="-")
    assert result.stdout.split() == ["name", "step_1", "step_2", "step_3"]
    assert list(tmp_path.iterdir()) == []


def test_gran_on_single_instant_names_missing_granularity(tools):
    create_stds(
        tools, "str3ds", "instant", [MapSpec("instant_1", 1, datetime(2026, 3, 1))]
    )
    with pytest.raises(ToolError) as error:
        tools.t_rast3d_list(input="instant", method="gran")
    text = message(error.value)
    assert "Space time dataset <instant@" in text
    assert "has no granularity" in text
    assert "Give a granule or use another method" in text
    assert "None" not in text
