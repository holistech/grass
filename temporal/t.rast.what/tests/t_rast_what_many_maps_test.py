"""Test t.rast.what with more maps than one r.what call can take

The tool hands r.what at most 400 maps per process and loop (a limit of
r.what). With one process, 401 maps leave one map for a single extra call
(up to 100 remaining maps) and 520 maps leave 120 for the path of more than 100.
The maps hold their number: the 3D raster has depth() as value and r3.to.rast
makes a map of every layer, which is quicker than 520 calls of r.mapcalc.
"""

from datetime import datetime, timedelta

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

# Registering 520 maps takes about ten seconds (measured 18.10.2026).
pytestmark = pytest.mark.slow

COUNT = 520


@pytest.fixture(scope="module")
def many(tools, tmp_path_factory):
    """520 daily maps holding 1 to 520; returns the name of the dataset"""
    tools.g_region(n=1, s=0, e=1, w=0, b=0, t=COUNT, res=1, res3=1)
    tools.r3_mapcalc(expression="wm3 = depth()")
    tools.r3_to_rast(input="wm3", output="wm")
    names = sorted(tools.g_list(type="raster", pattern="wm_*").stdout.split())
    start = datetime(2001, 1, 1)
    register = tmp_path_factory.mktemp("wm_register") / "register.txt"
    register.write_text(
        "".join(
            f"{name}|{(start + timedelta(days=index)):%Y-%m-%d}"
            f"|{(start + timedelta(days=index + 1)):%Y-%m-%d}\n"
            for index, name in enumerate(names)
        ),
        encoding="utf-8",
    )
    tools.t_create(
        type="strds",
        temporaltype="absolute",
        output="wm_ds",
        title="t",
        description="d",
    )
    tools.t_register(type="raster", input="wm_ds", file=str(register))
    return "wm_ds"


def _values(result):
    return [int(line.split("|")[-1]) for line in result.stdout.splitlines()]


def test_520_maps_with_one_process_use_the_path_for_more_than_100_remaining(
    tools, many
):
    result = tools.t_rast_what(strds=many, coordinates="0.5,0.5")

    assert _values(result) == list(range(1, COUNT + 1))


def test_400_maps_with_one_process_need_no_extra_call(tools, many):
    # The 400th map starts on 2002-02-04
    result = tools.t_rast_what(
        strds=many, coordinates="0.5,0.5", where="start_time < '2002-02-05'"
    )

    assert _values(result) == list(range(1, 401))


def test_today_the_extra_call_for_the_remaining_maps_loses_the_last_map(tools, many):
    # The 401st map starts on 2002-02-05, day 400 after 2001-01-01. Its call
    # writes to the file name of the first loop and is not listed for the
    # output, so only 400 values come back.
    result = tools.t_rast_what(
        strds=many, coordinates="0.5,0.5", where="start_time < '2002-02-06'"
    )

    assert _values(result) == list(range(1, 401))


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.what loses the last map when exactly one map remains after the loop of 100, its call writes to the file name of the first loop",
)
def test_all_maps_come_back_when_one_map_remains(tools, many):
    result = tools.t_rast_what(
        strds=many, coordinates="0.5,0.5", where="start_time < '2002-02-06'"
    )

    assert _values(result) == list(range(1, 402))


def test_today_more_than_100_remaining_maps_leave_a_file_in_the_current_directory(
    tools, many, tmp_path
):
    tools.t_rast_what(strds=many, coordinates="0.5,0.5")

    assert (tmp_path / "out_remain_0").is_file()


def test_today_a_second_run_with_more_than_100_remaining_maps_is_refused(tools, many):
    tools.t_rast_what(strds=many, coordinates="0.5,0.5")

    with pytest.raises(ToolError) as error:
        tools.t_rast_what(strds=many, coordinates="0.5,0.5")

    assert "<out_remain_0> exists. To overwrite, use the --overwrite flag" in message(
        error.value
    )


@pytest.mark.xfail(
    strict=True,
    reason="t.rast.what leaves the file out_remain_0 behind after more than 100 remaining maps",
)
def test_more_than_100_remaining_maps_leave_no_file_behind(tools, many, tmp_path):
    tools.t_rast_what(strds=many, coordinates="0.5,0.5")

    assert not (tmp_path / "out_remain_0").exists()


def test_three_processes_take_all_maps_in_one_loop(tools, many):
    result = tools.t_rast_what(strds=many, coordinates="0.5,0.5", nprocs=3)

    assert sorted(_values(result)) == list(range(1, COUNT + 1))
