"""Test the options and flags of the t.rast.algebra tool

The tool is run as a subprocess here, in contrast to the expression tests
that call the library. The datasets are described in the algebra fixture in
conftest.py.
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.tools import ToolError, Tools


@pytest.fixture
def tool(algebra):
    """Tools object that returns a result also for tools without output"""
    return Tools(session=algebra.session, consistent_return_value=True)


@pytest.fixture
def core_tool(algebra):
    """As tool, with the core as the algebra of the tool

    Without -c the tool follows GRASS_TEMPORAL_ALGEBRA. Tests whose result
    differs between the algebras set it to core and take -c for the classic
    algebra, which the flag selects whatever the variable says.
    """
    env = {**algebra.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    return Tools(env=env, consistent_return_value=True)


def list_maps(tool, dataset, columns="name,start_time,end_time,min,max"):
    """Return the rows of t.rast.list as dictionaries"""
    return tool.t_rast_list(input=dataset, columns=columns, format="json").json["data"]


def values(tool, dataset):
    """Return the minimum value of the maps of a dataset in temporal order"""
    return [row["min"] for row in list_maps(tool, dataset)]


def test_result_dataset_description(algebra, tool):
    """The result is a STRDS of the temporal type of its inputs, covering the
    result maps, with the granularity of the maps"""
    tool.t_rast_algebra(expression="OPT_BASIC = A * 2", basename="opt_basic")
    info = tool.t_info(input="OPT_BASIC", flags="g").keyval
    assert info["temporal_type"] == "absolute"
    assert info["number_of_maps"] == 4
    assert info["start_time"].strip("'") == "2001-01-01 00:00:00"
    assert info["end_time"].strip("'") == "2001-01-05 00:00:00"
    assert info["granularity"].strip("'") == "1 day"
    assert (info["min_min"], info["max_max"]) == (2, 8)
    assert values(tool, "OPT_BASIC") == [2, 4, 6, 8]


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        (None, ["opt_x_0", "opt_x_1", "opt_x_2", "opt_x_3"]),
        ("num", ["opt_x_0", "opt_x_1", "opt_x_2", "opt_x_3"]),
        (
            "gran",
            [
                "opt_x_2001_01_01",
                "opt_x_2001_01_02",
                "opt_x_2001_01_03",
                "opt_x_2001_01_04",
            ],
        ),
        (
            "time",
            [
                "opt_x_2001_01_01T00_00_00",
                "opt_x_2001_01_02T00_00_00",
                "opt_x_2001_01_03T00_00_00",
                "opt_x_2001_01_04T00_00_00",
            ],
        ),
    ],
)
def test_basename_and_suffix(algebra, tool, suffix, names):
    """The maps are named basename plus a number, the granule or the time"""
    options = {} if suffix is None else {"suffix": suffix}
    tool.t_rast_algebra(
        expression="OPT_NAMES = A * 2", basename="opt_x", overwrite=True, **options
    )
    assert [row["name"] for row in list_maps(tool, "OPT_NAMES")] == names


def test_result_dataset_is_registered_under_basename(algebra, tool):
    """The result maps are real raster maps that carry the computed values"""
    tool.t_rast_algebra(expression="OPT_RAS = A + 1", basename="opt_ras")
    stats = tool.r_univar(map="opt_ras_2", flags="g").keyval
    assert (stats["min"], stats["max"], stats["n"]) == (4, 4, 9)


@pytest.mark.parametrize(
    ("flags", "message"), [("", "Use the overwrite"), ("c", "Use --o flag")]
)
def test_overwrite_is_required(algebra, core_tool, flags, message):
    """A second run fails without --overwrite and leaves the result unchanged"""
    name, basename = f"OPT_OW{flags}", f"opt_ow{flags}"
    core_tool.t_rast_algebra(
        expression=f"{name} = A * 2", basename=basename, flags=flags
    )
    with pytest.raises(ToolError, match=message):
        core_tool.t_rast_algebra(
            expression=f"{name} = A * 3", basename=basename, flags=flags
        )
    assert values(core_tool, name) == [2, 4, 6, 8]
    core_tool.t_rast_algebra(
        expression=f"{name} = A * 3", basename=basename, flags=flags, overwrite=True
    )
    assert values(core_tool, name) == [3, 6, 9, 12]


@pytest.mark.parametrize(
    ("flags", "message"),
    [("", r"exists\. Use the overwrite"), ("c", "already in the database")],
)
def test_existing_dataset_with_new_basename_is_not_overwritten(
    algebra, core_tool, flags, message
):
    """The result dataset exists: refuse even if the map names are new"""
    name, basename = f"OPT_OW2{flags}", f"opt_ow2{flags}"
    core_tool.t_rast_algebra(
        expression=f"{name} = A * 2", basename=basename, flags=flags
    )
    with pytest.raises(ToolError, match=message):
        core_tool.t_rast_algebra(
            expression=f"{name} = A * 3", basename=f"{basename}_other", flags=flags
        )
    assert values(core_tool, name) == [2, 4, 6, 8]


@pytest.mark.parametrize(
    ("flags", "first", "last"),
    [
        # The core quotes the names and parenthesizes every operation.
        ("d", '"opt_dry_0"=("a1@PERMANENT" * 2)', '"opt_dry_3"=("a4@PERMANENT" * 2)'),
        ("dc", "opt_dry_0=(a1@PERMANENT * 2)", "opt_dry_3=(a4@PERMANENT * 2)"),
    ],
)
def test_dry_run_creates_nothing(algebra, core_tool, flags, first, last):
    """-d prints the planned r.mapcalc calls and creates neither maps nor dataset"""
    result = core_tool.t_rast_algebra(
        expression="OPT_DRY = A * 2", basename="opt_dry", flags=flags
    )
    assert "r.mapcalc" in result.stdout
    assert first in result.stdout
    assert last in result.stdout
    assert "OPT_DRY" in result.stdout
    with pytest.raises(ToolError):
        core_tool.t_info(input="OPT_DRY")
    assert not core_tool.g_list(type="raster", pattern="opt_dry_*").stdout.strip()


@pytest.mark.parametrize(
    ("flags", "message"), [("", "Use the overwrite"), ("c", "Use --o flag")]
)
def test_dry_run_requires_overwrite_as_the_real_run(algebra, core_tool, flags, message):
    """-d fails without --overwrite where the run would fail"""
    name, basename = f"OPT_DRY_OW{flags}", f"opt_dry_ow{flags}"
    core_tool.t_rast_algebra(
        expression=f"{name} = A * 2", basename=basename, flags=flags
    )
    with pytest.raises(ToolError, match=message):
        core_tool.t_rast_algebra(
            expression=f"{name} = A * 3", basename=basename, flags=f"d{flags}"
        )
    result = core_tool.t_rast_algebra(
        expression=f"{name} = A * 3",
        basename=basename,
        flags=f"d{flags}",
        overwrite=True,
    )
    assert "r.mapcalc" in result.stdout


def test_classic_flag_selects_the_classic_algebra(algebra, core_tool):
    """A selection with r gives one map per related pair in the core and one
    map per left map in the classic algebra"""
    core_tool.t_rast_algebra(
        expression="OPT_CORE = B {:,contains,r} A", basename="opt_core"
    )
    core_tool.t_rast_algebra(
        expression="OPT_CLASSIC = B {:,contains,r} A",
        basename="opt_classic",
        flags="c",
    )
    assert len(list_maps(core_tool, "OPT_CORE")) == 4
    assert len(list_maps(core_tool, "OPT_CLASSIC")) == 2


@pytest.mark.parametrize("nprocs", [1, 2, 4])
def test_nprocs_gives_same_result(algebra, tool, nprocs):
    """Parallel r.mapcalc processes give the same maps as a single process"""
    tool.t_rast_algebra(
        expression="OPT_NPROCS = A * 2 + N",
        basename="opt_nprocs",
        nprocs=nprocs,
        overwrite=True,
    )
    assert list_maps(tool, "OPT_NPROCS") == [
        {
            "name": f"opt_nprocs_{number}",
            "start_time": f"2001-01-0{number + 1} 00:00:00",
            "end_time": f"2001-01-0{number + 2} 00:00:00",
            "min": 3 * (number + 1) + 10,
            "max": 3 * (number + 1) + 10,
        }
        for number in range(4)
    ]


def test_register_null_maps(algebra, tool):
    """Maps without any valid cell are registered only with -n"""
    expression = "OPT_NULL = if(A > 2, A, null())"
    tool.t_rast_algebra(expression=expression, basename="opt_null")
    assert values(tool, "OPT_NULL") == [3, 4]
    tool.t_rast_algebra(
        expression=expression, basename="opt_null", flags="n", overwrite=True
    )
    assert values(tool, "OPT_NULL") == [None, None, 3, 4]


def test_granularity_algebra_samples_datasets(algebra, tool):
    """-g samples the datasets with their common granularity: the two-day maps
    of B are repeated for each day, so that A + B has one result per day"""
    tool.t_rast_algebra(expression="OPT_GRAN = A + B", basename="opt_gran", flags="g")
    assert values(tool, "OPT_GRAN") == [6, 7, 9, 10]
    maps = list_maps(tool, "OPT_GRAN")
    assert maps[0]["start_time"] == "2001-01-01 00:00:00"
    assert maps[0]["end_time"] == "2001-01-02 00:00:00"
    assert maps[3]["end_time"] == "2001-01-05 00:00:00"


def test_without_granularity_unrelated_datasets_give_nothing(algebra, tool):
    """The same expression without -g relates only equal maps: none here"""
    tool.t_rast_algebra(expression="OPT_NOGRAN = A + B", basename="opt_nogran")
    assert list_maps(tool, "OPT_NOGRAN") == []


def test_granularity_algebra_rejects_topological_operators(algebra, tool):
    """Spatio-temporal operators with a relation do not exist in -g mode"""
    with pytest.raises(ToolError, match="topological operators are not supported"):
        tool.t_rast_algebra(
            expression="OPT_GRAN3 = A {+,during} B", basename="opt_gran3", flags="g"
        )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A * 2", [2, 4, 6, 8]),
        ("if(A > 2, A, 0)", [0, 0, 3, 4]),
    ],
)
def test_granularity_flag_does_not_change_regular_results(
    algebra, tool, expression, expected
):
    """For datasets that are already regular, -g gives the usual maps"""
    tool.t_rast_algebra(
        expression=f"OPT_GRAN2 = {expression}",
        basename="opt_gran2",
        flags="g",
        overwrite=True,
    )
    assert values(tool, "OPT_GRAN2") == expected


@pytest.mark.parametrize(
    ("relations", "flags", "expected"),
    [
        # spa<i> and spb<i> have the same extent
        ("equal|equivalent", "s", [2, 4, 6, 8]),
        # spa2 [20,50] contains spb3 [25,40]
        ("equal|contain", "s", [5]),
        # spa3 overlaps spb1 and spa4 overlaps spb2; the sums of spa1 and
        # spa2 with several maps are empty
        ("equal|overlap", "s", [4, 6]),
        ("equal|overlap", "sn", [None, None, 4, 6]),
    ],
)
def test_spatial_topology(algebra, tool, large_region, relations, flags, expected):
    """-s combines only maps with the given spatial relation. The maps have
    equal time stamps, so that the spatial relation decides"""
    tool.t_rast_algebra(
        expression=f"OPT_SPATIAL = SA {{+,{relations},l}} SB",
        basename="opt_spatial",
        flags=flags,
        overwrite=True,
    )
    assert sorted(values(tool, "OPT_SPATIAL"), key=lambda value: value or 0) == expected


@pytest.mark.parametrize(
    ("spatial", "expected"),
    [
        (False, [4, 4, 4, 4]),
        # spa1: spb1, spb2, spb3; spa2: all four; spa3: spb1, spb2, spb3
        # (spb4 touches it only at the corner 40,40); spa4: spb2, spb4
        # (spb3 touches it only at the corner). SpatialExtent.meet_2d() is False
        # and disjoint_2d() True for both corner pairs, so the topology builder
        # is right (checked 2026-10-11). Equal time stamps: sorted by value.
        (True, [2, 3, 3, 4]),
    ],
)
def test_spatial_option_counts_only_spatially_related_maps(
    algebra, large_region, spatial, expected
):
    """With spatial=True the temporal relation alone is not enough: the maps
    must also be related in space, even if no spatial relation is given.

    The expected counts are 2, 3, 3, 4 and not 3, 3, 4, 4: maps that touch
    only at a corner are not related, see the comment at the parameters."""
    assert algebra.values("SA # SB", spatial=spatial) == expected


@pytest.mark.parametrize(
    "expression",
    [
        "OPT_ERR == A + A",
        "OPT_ERR = A +",
        "OPT_ERR = A {+,during} ",
        "OPT_ERR = (A + A",
        "OPT_ERR = A {+,during,x} A",
        "OPT_ERR = A $ A",
        "A + A",
    ],
)
def test_syntax_error_fails(algebra, tool, expression):
    """A malformed expression ends the tool with an error and creates nothing"""
    with pytest.raises(ToolError):
        tool.t_rast_algebra(expression=expression, basename="opt_err")
    with pytest.raises(ToolError):
        tool.t_info(input="OPT_ERR")


def test_unknown_dataset_is_named_in_the_error(algebra, tool):
    """The error message names the missing dataset"""
    with pytest.raises(ToolError, match="NoSTRDS"):
        tool.t_rast_algebra(expression="OPT_ERR = NoSTRDS + NoSTRDS", basename="x")


def test_strds_function_is_not_available_in_raster_algebra(algebra, tool):
    """strds() is reserved for the other temporal algebras"""
    with pytest.raises(ToolError):
        tool.t_rast_algebra(expression="OPT_ERR = strds(A) + strds(B)", basename="x")


def test_missing_basename_fails(algebra, tool):
    """basename is required"""
    with pytest.raises(ToolError, match="basename"):
        tool.t_rast_algebra(expression="OPT_ERR = A + A")


def test_missing_expression_fails(algebra, tool):
    """expression is required"""
    with pytest.raises(ToolError, match="expression"):
        tool.t_rast_algebra(basename="x")


@pytest.mark.parametrize("expression", ["OPT_ERR = 1 + 1", "OPT_ERR = A +"])
def test_syntax_error_is_reported_without_traceback(algebra, tool, expression):
    """Users get a GRASS error message, not a Python traceback"""
    with pytest.raises(ToolError) as error:
        tool.t_rast_algebra(expression=expression, basename="x")
    assert "Traceback" not in error.value.stderr


def test_overwrite_error_is_reported_without_traceback(algebra, tool):
    """The request to use --overwrite is a plain message"""
    tool.t_rast_algebra(expression="OPT_OW3 = A * 2", basename="opt_ow3")
    with pytest.raises(ToolError) as error:
        tool.t_rast_algebra(expression="OPT_OW3 = A * 2", basename="opt_ow3")
    assert "Traceback" not in error.value.stderr


def test_empty_result_gives_a_warning(algebra, tool):
    """A result without any map is reported (warning or error)"""
    try:
        result = tool.t_rast_algebra(expression="OPT_EMPTY = A + B", basename="x")
    except ToolError:
        return
    assert "WARNING" in result.stderr


@pytest.mark.parametrize(
    "expression",
    ["A + A", "A {+,equal,l} A", "(A + A) * 2", "if(A > 1, A)", "A[1]", "A : B"],
)
def test_parse_without_run_creates_nothing(algebra, expression):
    """With run=False the expression is only checked, no dataset is created"""
    algebra.remove("R")
    parser = tgis.TemporalRasterAlgebraParser(run=False, debug=False)
    parser.parse(f"R = {expression}", "r", True)
    assert not algebra.exists("R")


def test_result_map_without_command_and_without_raster_is_fatal(algebra):
    """A result map that has no mapcalc command and no raster is an error

    Before, the message was only printed and the dataset was registered with a
    missing map (review H5). The state cannot be produced by an expression, so
    the step is called directly.
    """
    parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False)
    missing = tgis.RasterDataset("no_such_map@PERMANENT")
    with pytest.raises(algebra.errors, match="no_such_map"):
        parser._mapcalc_expression(missing)


@pytest.mark.parametrize(
    ("basename", "first", "second", "count", "start"),
    [
        ("typeswitch_rel", "A + N", "RT * 2", 3, 0),
        ("typeswitch_abs", "RT * 2", "A + N", 4, datetime.datetime(2001, 1, 1)),
    ],
)
def test_overwrite_result_maps_of_other_temporal_type(
    algebra, basename, first, second, count, start
):
    """Result maps registered with the other temporal type are replaced

    Each case has its own basename. With a shared one the second case would
    find the maps of the first and could pass on them.
    """
    algebra.run(first, basename=basename)
    rows = algebra.run(second, basename=basename)
    assert len(rows) == count
    starts = []
    for number in range(count):
        stored = tgis.RasterDataset(f"{basename}_{number}@PERMANENT")
        stored.select()
        assert stored.is_time_absolute() is isinstance(start, datetime.datetime)
        starts.append(stored.temporal_extent.get_start_time())
    assert min(starts) == start


def run_with_debug(algebra, expression, run, classic):
    """Parse "R = <expression>" with debug=True and the given run"""
    algebra.remove("R")
    parser = tgis.TemporalRasterAlgebraParser(
        run=run, debug=True, dry_run=True, classic=classic
    )
    parser.parse(f"R = {expression}", "r", True)


def test_debug_output_of_a_run(algebra, capsys):
    """debug=True prints each planned module call as a command line"""
    run_with_debug(algebra, "(A + A) * 2", run=True, classic=False)
    output = capsys.readouterr().out
    assert (
        'r.mapcalc expression="r_0"=(("a1@PERMANENT" + "a1@PERMANENT") * 2)' in output
    )


def test_debug_output_without_run(algebra, capsys):
    """With run=False only the syntax is checked, so nothing is planned and
    debug=True prints nothing"""
    run_with_debug(algebra, "(A + A) * 2", run=False, classic=False)
    assert not capsys.readouterr().out


def test_debug_output_of_the_classic_algebra(algebra, capsys):
    """The classic algebra prints the mapcalc commands and the resulting
    statement, and without run the statement with the placeholder name"""
    run_with_debug(algebra, "(A + A) * 2", run=True, classic=True)
    output = capsys.readouterr().out
    assert "((a1@PERMANENT + a1@PERMANENT) * 2)" in output
    assert "R = [" in output
    run_with_debug(algebra, "(A + A) * 2", run=False, classic=True)
    assert "R = A**" in capsys.readouterr().out
