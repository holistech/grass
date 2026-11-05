"""Test the indicator of t.rast.accdetect for a stretch of a single map

The indicator marks the first map of a stretch with the start value and the
last with the end value. A stretch of one map has only that one map, and it
gets the start value, never the end value; so does a map that is alone in its
cycle.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, small_region
from grass.temporal.testing.readback import cell_values, inventory, list_maps, message
from grass.temporal.testing.session import project_session, run_with_timeout
from grass.tools import ToolError, Tools

N = None
# Six daily maps from 2001-01-01 on a region of one row and four cells; 60 is
# outside the range 10 to 50. The cells, by column, are in the range on the
# days: 1 (inside the cycle), 0 (the first map of the cycle), 5 (the last
# map of the cycle), and 0 and 1 (a stretch of two maps).
IN_RANGE = ([1], [0], [5], [0, 1])


def column_values(days):
    return [20 if number in days else 60 for number in range(6)]


@pytest.fixture
def stretches(tools, prefix):
    small_region(tools, 1, 4)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_c{number}",
                "if(col() == 1, {}, if(col() == 2, {}, if(col() == 3, {}, {})))".format(
                    *(column_values(days)[number] for days in IN_RANGE)
                ),
                day(number),
                day(number + 1),
            )
            for number in range(6)
        ],
    )
    return f"{prefix}_in"


def indicator_by_day(tools, name):
    """The cells of every map by the day of its start; empty maps are removed"""
    return {
        (datetime.fromisoformat(row.start) - day(0)).days: cell_values(tools, row.name)
        for row in list_maps(tools, "strds", name)
    }


def test_single_map_stretch_indicator(tools, prefix, stretches):
    tools.t_rast_accdetect(
        input=stretches,
        occurrence=f"{prefix}_occ",
        indicator=f"{prefix}_ind",
        basename=prefix,
        start="2001-01-01",
        cycle="6 days",
        range="10,50",
    )

    # A stretch of one map is marked 1, wherever it lies in the cycle; the
    # stretch of two maps in the fourth cell is 1 and 3.
    assert indicator_by_day(tools, f"{prefix}_ind") == {
        0: [N, 1, N, 1],
        1: [1, N, N, 3],
        5: [N, N, 1, N],
    }


def test_map_alone_in_its_cycle_gets_start_value(tools, prefix, stretches):
    tools.t_rast_accdetect(
        input=stretches,
        occurrence=f"{prefix}_occ",
        indicator=f"{prefix}_ind",
        basename=prefix,
        start="2001-01-01",
        cycle="1 day",
        range="10,50",
    )

    # Every cycle holds one map, so the stretch of two maps is cut into two
    # stretches of one, each 1.
    assert indicator_by_day(tools, f"{prefix}_ind") == {
        0: [N, 1, N, 1],
        1: [1, N, N, 1],
        5: [N, N, 1, N],
    }


@pytest.fixture
def three_days(tools, prefix):
    """Three daily maps of the value 20 from 2001-01-01, the input dataset"""
    small_region(tools, 1, 1)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_c{number}", 20, day(number), day(number + 1))
            for number in range(3)
        ],
    )
    return f"{prefix}_in"


@pytest.mark.parametrize("overwrite", [False, True], ids=["refused", "overwrite"])
@pytest.mark.parametrize("output", ["occurrence", "indicator"])
def test_unregistered_raster_with_a_later_name_is_refused_first(
    tools, prefix, three_days, output, overwrite
):
    """A raster that no dataset holds blocks the third map, not the first

    Without overwrite the run is refused before the first map is computed,
    so no map of the earlier granules is left behind and the raster keeps its
    value. With overwrite it is replaced and the run goes through.
    """
    taken = (
        f"{prefix}_b_2001_01_03"
        if output == "occurrence"
        else (f"{prefix}_b_indicator_2001_01_03")
    )
    tools.r_mapcalc(expression=f"{taken} = 9")
    before = inventory(tools)
    arguments = {
        "input": three_days,
        "start": "2001-01-01",
        "cycle": "3 days",
        "basename": f"{prefix}_b",
        "occurrence": f"{prefix}_occ",
        "indicator": f"{prefix}_ind",
        "range": "10,50",
    }

    if overwrite:
        tools.t_rast_accdetect(overwrite=True, **arguments)
        assert len(list_maps(tools, "strds", f"{prefix}_occ")) == 3
        assert cell_values(tools, taken) != [9.0]
        return

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(**arguments)

    assert f"Raster map <{taken}@PERMANENT> exists" in message(error.value)
    assert inventory(tools) == before
    assert cell_values(tools, taken) == [9.0]


def test_suffix_gran_collision_is_refused_before_writing(tools, prefix):
    """Two maps of one time get one name from gran; the run writes nothing

    The names follow the granularity of the input dataset, which the tool has
    no option to change, so equal times are the way to a collision.
    """
    small_region(tools, 1, 1)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_c{number}", 20, day(0), day(1)) for number in (1, 2)]
        + [MapSpec(f"{prefix}_c3", 20, day(1), day(2))],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=f"{prefix}_in",
            start="2001-01-01",
            cycle="3 days",
            basename=f"{prefix}_b",
            occurrence=f"{prefix}_occ",
            range="10,50",
        )

    assert (
        f"The maps <{prefix}_c1@PERMANENT> and <{prefix}_c2@PERMANENT> are given "
        f"the same name <{prefix}_b_2001_01_01@PERMANENT> by the suffix gran"
        in message(error.value)
    )
    assert inventory(tools) == before


def test_registered_map_with_a_later_name_is_refused_first(tools, prefix, three_days):
    """A map of another dataset blocks the third map, not the first"""
    taken = f"{prefix}_b_2001_01_03"
    create_stds(tools, "strds", f"{prefix}_kept", [MapSpec(taken, 7, day(10), day(11))])
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=three_days,
            start="2001-01-01",
            cycle="3 days",
            basename=f"{prefix}_b",
            occurrence=f"{prefix}_occ",
            range="10,50",
        )

    assert f"Map <{taken}@PERMANENT> is already registered" in message(error.value)
    assert inventory(tools) == before
    assert cell_values(tools, taken) == [7.0]


@pytest.mark.parametrize("option", ["occurrence", "indicator"])
def test_result_dataset_of_another_mapset_is_refused_first(two_mapsets, prefix, option):
    """A dataset can be created only in the current mapset

    The refusal comes before the first map is computed. The maps are named in
    the current mapset, so none of them could be registered in the dataset of
    the other mapset.
    """
    work, other = two_mapsets
    small_region(work, 1, 1)
    # The other mapset needs a temporal database, or the refusal would be
    # that of a mapset without one.
    create_stds(
        other, "strds", f"{prefix}_there", [MapSpec(f"{prefix}_t", 1, day(0), day(1))]
    )
    create_stds(
        work,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(f"{prefix}_c{number}", 20, day(number), day(number + 1))
            for number in range(3)
        ],
    )
    before = inventory(work)
    arguments = {
        "input": f"{prefix}_in",
        "start": "2001-01-01",
        "cycle": "3 days",
        "basename": f"{prefix}_b",
        "occurrence": f"{prefix}_occ",
        "indicator": f"{prefix}_ind",
        "range": "10,50",
    }
    arguments[option] = f"{prefix}_{option}@other"

    with pytest.raises(ToolError) as error:
        work.t_rast_accdetect(**arguments)

    assert "Space time datasets can only be created in the current mapset" in (
        message(error.value)
    )
    assert inventory(work) == before


@pytest.mark.parametrize("suffix", ["gran", "time", "num"])
def test_overlapping_cycles_with_the_same_name_are_refused_before_writing(
    tools, prefix, three_days, suffix
):
    """A negative offset puts a map into two cycles; the run is refused

    The tool keeps one result per input map. With the suffix num the names
    would differ, but the first result of a map in two cycles would stay
    behind in no dataset, so every suffix is refused.
    """
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_accdetect(
            input=three_days,
            start="2001-01-01",
            cycle="2 days",
            offset="-1 day",
            basename=f"{prefix}_b",
            occurrence=f"{prefix}_occ",
            range="10,50",
            suffix=suffix,
        )

    text = message(error.value)
    assert f"<{prefix}_c1@PERMANENT> lies in overlapping cycles" in text
    assert "Traceback" not in text
    assert inventory(tools) == before


def test_a_negative_offset_of_another_unit_than_the_cycle_is_refused(tmp_path):
    """The cycles of a month and an offset of -29 days stop moving forward

    Each cycle starts two days after the one before until the month is cut at
    the end of February; then the start repeats. The run is refused before it
    writes a map instead of running on forever.
    """
    with project_session(tmp_path / "project") as session:
        tools = Tools(session=session, consistent_return_value=True)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools,
            "strds",
            "mix_in",
            [
                MapSpec("mix_1", 20, datetime(2026, 1, 1), datetime(2026, 1, 31)),
                MapSpec("mix_2", 20, datetime(2026, 1, 31), datetime(2026, 3, 5)),
            ],
        )
        before = inventory(tools)

        result = run_with_timeout(
            session,
            [
                "t.rast.accdetect",
                "input=mix_in",
                "basename=mix_out",
                "start=2026-01-01",
                "cycle=1 month",
                "offset=-29 days",
                "range=10,50",
                "occurrence=mix_occ",
                "suffix=num",
            ],
            30,
        )

        assert result is not None, "the tool did not end"
        code, messages = result
        assert code != 0
        assert (
            "The offset must not move the next cycle back to or before the "
            "start of this one" in " ".join(messages.split())
        )
        assert "Traceback" not in messages
        assert inventory(tools) == before
