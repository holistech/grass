"""Test the granule, the standard output and the granules of t.vect.list

The option granule takes the same values as in t.rast.list: a granule of
absolute time such as "2 days", and in relative time a number in the unit of
the dataset, also with that unit; another unit is refused with a message.
output=- writes to the standard output. A dataset of a single time instance
has no granularity, and the message says so. The granules reach the end of
the dataset.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, message
from grass.tools import ToolError

D = datetime
COLUMNS = "name,start_time,end_time"


def rows(result):
    """The lines of the listing without the header, split at the bar"""
    return [line.split("|") for line in result.stdout.splitlines()[1:]]


@pytest.fixture(scope="module")
def model(tools):
    """Three vector maps of 6 hours each in relative time"""
    create_stds(
        tools,
        "stvds",
        "model",
        [MapSpec(f"step_{k + 1}", k + 1, 6 * k, 6 * k + 6) for k in range(3)],
        temporaltype="relative",
        unit="hours",
    )
    return "model"


@pytest.fixture(scope="module")
def days(tools):
    """Four vector maps of one day each"""
    create_stds(
        tools,
        "stvds",
        "days",
        [MapSpec(f"day_{k}", k, D(2026, 7, k), D(2026, 7, k + 1)) for k in range(1, 5)],
    )
    return "days"


def test_granule_option(tools, days):
    """granule="2 days" gives two granules, each named by its first map"""
    result = tools.t_vect_list(
        input=days, method="gran", granule="2 days", columns=COLUMNS
    )
    assert rows(result) == [
        ["day_1", "2026-07-01 00:00:00", "2026-07-03 00:00:00"],
        ["day_3", "2026-07-03 00:00:00", "2026-07-05 00:00:00"],
    ]


def test_granule_of_the_wrong_kind_is_refused(tools, days):
    """A number is no granule of absolute time"""
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input=days, method="gran", granule="2")
    assert 'Wrong granularity: "2"' in message(error.value)


@pytest.mark.parametrize("granule", ["12", "12 hours"])
def test_gran_with_number_granule_on_relative_time(tools, model, granule):
    """The granules of 12 hours start at 0 and 12 and take their first map"""
    result = tools.t_vect_list(
        input=model, method="gran", granule=granule, columns=COLUMNS
    )
    assert rows(result) == [["step_1", "0", "12"], ["step_3", "12", "24"]]


def test_gran_with_granule_of_another_unit_is_refused(tools, model):
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input=model, method="gran", granule="1 day")
    text = message(error.value)
    assert "Invalid granule <1 day>" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


def test_output_dash_writes_to_stdout(tools, model, tmp_path, monkeypatch):
    """output=- prints the listing and makes no file of the name -"""
    monkeypatch.chdir(tmp_path)
    result = tools.t_vect_list(input=model, columns="name", output="-")
    assert result.stdout.split() == ["name", "step_1", "step_2", "step_3"]
    assert list(tmp_path.iterdir()) == []


def test_gran_on_single_instant_names_missing_granularity(tools):
    create_stds(tools, "stvds", "instant", [MapSpec("instant_1", 1, D(2026, 3, 1))])
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input="instant", method="gran")
    text = message(error.value)
    assert "Space time dataset <instant@" in text
    assert "has no granularity" in text
    assert "Give a granule or use another method" in text
    assert "None" not in text


@pytest.mark.parametrize("order", ["a first", "b first"])
def test_gran_ends_at_end_of_dataset(tools, order):
    """nest_a 1 to 3 July and nest_b 1 to 2 July have the same start; the
    granules of a day reach 3 July, whichever map comes last"""
    maps = [
        MapSpec("nest_a", 1, D(2026, 7, 1), D(2026, 7, 3)),
        MapSpec("nest_b", 2, D(2026, 7, 1), D(2026, 7, 2)),
    ]
    if order == "b first":
        maps.reverse()
    name = "nest_" + order.split()[0]
    create_stds(tools, "stvds", name, maps, overwrite=True)
    assert tools.t_info(type="stvds", input=name, flags="g").keyval["end_time"] == (
        "'2026-07-03 00:00:00'"
    )
    result = tools.t_vect_list(input=name, method="gran", columns="start_time,end_time")
    assert rows(result) == [
        ["2026-07-01 00:00:00", "2026-07-02 00:00:00"],
        ["2026-07-02 00:00:00", "2026-07-03 00:00:00"],
    ]


@pytest.mark.timeout(10)
@pytest.mark.parametrize("granule", ["0 days", "0 months", "-1 days"])
def test_zero_granule_is_refused(tools, granule):
    """A granule of 0 or less ends with a message and does not run on

    Granule "0 days" never moved on, so the listing ran without end; the
    timeout makes such a run fail the test instead of hanging it.
    """
    create_stds(
        tools,
        "stvds",
        "stepped",
        [MapSpec(f"d_{k}", k, D(2026, 7, k), D(2026, 7, k + 1)) for k in range(1, 4)],
        overwrite=True,
    )
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input="stepped", method="gran", granule=granule)
    text = message(error.value)
    assert f"Invalid granule <{granule}>: the number must be positive" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


@pytest.mark.timeout(10)
def test_zero_relative_granule_is_refused(tools, model):
    """The relative granule 0 is refused as well"""
    with pytest.raises(ToolError) as error:
        tools.t_vect_list(input=model, method="gran", granule="0")
    assert "Invalid granule <0>" in message(error.value)
