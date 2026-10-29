"""Test the refusals of t.rast.contour and the cases of an empty input"""

import os
import shlex
import shutil

import pytest

from grass.temporal.testing.readback import list_maps, message, stds_info
from grass.tools import ToolError, Tools


def _refused(tools, **options):
    with pytest.raises(ToolError) as error:
        tools.t_rast_contour(**options)
    return message(error.value)


@pytest.mark.parametrize("missing", ["input", "output", "basename"])
def test_a_required_option_is_checked_by_the_parser(tools, quarterly, prefix, missing):
    options = {"input": quarterly, "output": prefix, "basename": prefix, "step": 1}
    del options[missing]

    assert f"Required parameter <{missing}> not set" in _refused(tools, **options)


def test_an_unknown_input_is_refused(tools, prefix):
    text = _refused(tools, input="ctr_missing", output=prefix, basename=prefix, step=1)

    assert "Space time dataset <ctr_missing> of type <strds> not found" in text


def test_levels_or_step_are_needed_and_the_refusal_is_a_message(
    tools, quarterly, prefix
):
    text = _refused(tools, input=quarterly, output=prefix, basename=prefix)

    assert "Either <levels> or <step> option must be specified" in text
    assert "Traceback" not in text
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


def test_a_step_of_zero_is_refused(tools, ramps, prefix):
    text = _refused(tools, input=ramps, output=prefix, basename=prefix, step=0)

    assert "This step value is not allowed" in text
    assert "Traceback" not in text
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


def test_a_level_that_is_no_number_is_refused_by_the_parser(tools, ramps, prefix):
    text = _refused(tools, input=ramps, output=prefix, basename=prefix, levels="a")

    assert "Invalid value <a> for parameter <levels>" in text


def test_a_step_leaves_a_map_without_values_empty(tools, quarterly, prefix):
    # The three maps with values and, with -n, the empty one.
    tools.t_rast_contour(
        input=quarterly, output=prefix, basename=prefix, step=1, flags="n"
    )

    assert stds_info(tools, "stvds", prefix)["number_of_maps"] == 4


def test_a_selection_without_a_map_warns(tools, quarterly, prefix):
    result = tools.t_rast_contour(
        input=quarterly,
        output=prefix,
        basename=prefix,
        levels="2",
        where="start_time > '2010-01-01'",
    )

    assert f"Space time raster dataset <{quarterly}@PERMANENT> is empty" in message(
        result
    )
    assert tools.t_list(type="stvds", columns="name").stdout.count(prefix) == 0


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_existing_output_is_refused_without_overwrite(tools, quarterly, prefix):
    options = {"input": quarterly, "output": prefix, "basename": prefix, "levels": "2"}
    tools.t_rast_contour(**options)

    text = _refused(tools, **options)

    assert f"Space time vector dataset <{prefix}> is already in the database" in text


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_several_empty_maps_are_all_dropped(tools, ramps, prefix):
    # Three maps without values in front of the two ramps: the names of the
    # empty maps are joined for the removal, and none of them stays.
    from datetime import datetime

    from grass.temporal.testing.data import MapSpec, create_stds, small_region

    small_region(tools, 4, 4)
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_n{k}",
                "double(null())",
                datetime(2001, 1, k + 1),
                datetime(2001, 1, k + 2),
            )
            for k in range(3)
        ],
    )

    tools.t_rast_contour(
        input=f"{prefix}_in", output=prefix, basename=prefix, levels="2"
    )

    assert tools.g_list(type="vector", pattern=f"{prefix}_*").stdout.split() == []


def test_a_where_with_a_syntax_error_is_reported_as_a_message(tools, quarterly, prefix):
    text = _refused(
        tools,
        input=quarterly,
        output=prefix,
        basename=prefix,
        step=1,
        where="nonsense =",
    )

    assert "Traceback" not in text
    assert "Invalid where condition <nonsense =>" in text
    assert "syntax error" in text
    assert prefix not in tools.t_list(type="strds,str3ds,stvds", columns="name").stdout


def test_a_failing_r_contour_is_reported(broken_tools, ramps, prefix):
    with pytest.raises(ToolError) as error:
        broken_tools("r.contour").t_rast_contour(
            input=ramps, output=prefix, basename=prefix, step=1
        )

    assert "Error running r.contour" in message(error.value)


def test_a_failing_r_contour_is_reported_when_the_processes_are_waited_for(
    broken_tools, ramps, prefix
):
    # With three processes the two maps are queued without a wait; the failure
    # shows when the tool waits for the end of both.
    with pytest.raises(ToolError) as error:
        broken_tools("r.contour").t_rast_contour(
            input=ramps, output=prefix, basename=prefix, step=1, nprocs=3, flags="t"
        )

    assert "Error running r.contour" in message(error.value)


def test_a_map_that_r_contour_did_not_make_is_not_registered(
    tools, broken_tools, ramps, prefix
):
    # A run that ends with 0 and makes nothing leaves no vector map to register.
    broken_tools("r.contour", status=0).t_rast_contour(
        input=ramps, output=prefix, basename=prefix, step=1
    )

    assert stds_info(tools, "stvds", prefix)["number_of_maps"] == 0


def test_a_contour_map_that_cannot_be_loaded_is_passed_over(
    tools, ramps, tmp_path, prefix
):
    # r.contour makes the maps, then the stand-in overwrites the coor file of
    # the vector map of the second day. The temporal framework reads the map
    # through the C library, which ends the read with a fatal error that
    # load() raises as FatalError (measured 29.10.2026 with a coor file that
    # holds the text "garbage": FatalError "read_history vector").
    real = shlex.quote(shutil.which("r.contour", path=tools._original_env["PATH"]))  # noqa: SLF001
    stand_in = tmp_path / "r.contour"
    stand_in.write_text(
        f"""#!/bin/sh
case "$1" in --interface-description) exec {real} "$@" ;; esac
{real} "$@" || exit $?
for arg in "$@"; do
    case "$arg" in output=*) out=${{arg#output=}} ;; esac
done
out=${{out%@*}}
case "$out" in
    *_00002) eval "$(g.gisenv -n)"
        printf garbage > "$GISDBASE/$LOCATION_NAME/$MAPSET/vector/$out/coor" ;;
esac
"""
    )
    stand_in.chmod(0o755)
    env = dict(tools._original_env)  # noqa: SLF001
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    broken = Tools(env=env, consistent_return_value=True, capture_stderr=True)

    broken.t_rast_contour(
        input=ramps, output=prefix, basename=prefix, step=1, suffix="num"
    )

    assert [row.name for row in list_maps(tools, "stvds", prefix)] == [
        f"{prefix}_00001"
    ]


def test_the_progress_is_reported_every_ten_maps(tools, prefix):
    from grass.temporal.testing.data import create_daily_stds, small_region

    small_region(tools, 4, 4)
    create_daily_stds(tools, "strds", [f"{prefix}_in"], 10, map_prefix=prefix)

    result = tools.t_rast_contour(
        input=f"{prefix}_in", output=prefix, basename=prefix, step=1
    )

    # Once when the tenth process is queued, once when the tenth map is
    # registered and once at the end.
    assert result.stderr.count("100%") == 3
