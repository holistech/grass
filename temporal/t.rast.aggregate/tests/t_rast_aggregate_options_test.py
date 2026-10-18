"""Test the options of t.rast.aggregate that the other modules leave out

nprocs, one sampling relation at a time, the input that is empty or has
instants of relative time, and the refusals of wrong values. The expected
values are derived from the data in the comments.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day, register_stds
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError


def _rows(tools, name):
    return [
        (row.name, row.start, row.end, row.min)
        for row in list_maps(tools, "strds", name)
    ]


@pytest.fixture(scope="module")
def four_hourly(tools):
    """120 maps that follow each other: map k holds k, from 4 (k-1) to 4 k hours"""
    count = 120
    tools.r_mapcalc(
        file=StringIO("".join(f"ah{k} = {k}\n" for k in range(1, count + 1)))
    )
    register_stds(
        tools,
        "strds",
        "four_hourly",
        [
            MapSpec(f"ah{k}", k, day(0, hours=4 * (k - 1)), day(0, hours=4 * k))
            for k in range(1, count + 1)
        ],
    )
    return "four_hourly"


def _suffixes(rows, output):
    return [row[0].removeprefix(f"{output}_") for row in rows]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_nprocs_gives_the_same_maps_as_one_process(tools, four_hourly):
    # A granule of 12 hours holds three maps, 3j+1 to 3j+3, so it sums to
    # 9j+6 for j = 0 to 39 (6 to 357). A granule of a day holds six maps,
    # 6j+1 to 6j+6, and sums to 36j+21 for j = 0 to 19 (21 to 705).
    results = {}
    for nprocs in (1, 2, 4, 9):
        output = f"par_{nprocs}"
        tools.t_rast_aggregate(
            input=four_hourly,
            output=output,
            basename=output,
            granularity="12 hours",
            method="sum",
            nprocs=nprocs,
            file_limit=2,
        )
        results[nprocs] = _rows(tools, output)

    one = results[1]
    assert [row[3] for row in one] == [9.0 * j + 6 for j in range(40)]
    assert one[0][1:3] == (
        day(0).strftime("%Y-%m-%d %H:%M:%S"),
        day(0, hours=12).strftime("%Y-%m-%d %H:%M:%S"),
    )
    for nprocs in (2, 4, 9):
        assert _suffixes(results[nprocs], f"par_{nprocs}") == _suffixes(one, "par_1")
        assert [row[1:] for row in results[nprocs]] == [row[1:] for row in one]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("nprocs", [1, 2, 3, 4])
def test_one_day_sum_with_nprocs(tools, four_hourly, nprocs):
    output = f"day_{nprocs}"

    tools.t_rast_aggregate(
        input=four_hourly,
        output=output,
        basename=output,
        granularity="1 day",
        method="sum",
        nprocs=nprocs,
    )

    assert [row[3] for row in _rows(tools, output)] == [
        36.0 * j + 21 for j in range(20)
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_today_nprocs_below_one_runs_one_process(tools, four_hourly):
    # No value is refused: 0 and -1 aggregate like 1.
    for nprocs in (0, -1):
        output = f"par_n{abs(nprocs)}"
        tools.t_rast_aggregate(
            input=four_hourly,
            output=output,
            basename=output,
            granularity="1 day",
            method="sum",
            nprocs=nprocs,
        )

        assert [row[3] for row in _rows(tools, output)] == [
            36.0 * j + 21 for j in range(20)
        ]


@pytest.mark.parametrize(
    "sampling",
    [
        "equal",
        "contains",
        "during",
        "overlaps",
        "overlapped",
        "started",
        "starts",
        "finished",
        "finishes",
        "overlaps,overlapped",
        "equal,contains",
    ],
)
def test_one_sampling_relation_at_a_time(tools, sampling_relations, sampling):
    # The data and the sums are described in temporal/conftest.py.
    output = "rel_" + sampling.replace(",", "_")

    tools.t_rast_aggregate(
        input=sampling_relations.dataset,
        output=output,
        basename=output,
        granularity="10 days",
        method="sum",
        sampling=sampling,
    )

    second = [row for row in _rows(tools, output) if row[1] == sampling_relations.start]
    assert [row[3] for row in second] == [float(sampling_relations.sums[sampling])]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_relative_instants_get_a_final_granule(tools):
    # Instants at 0, 1 and 2 with a granularity of 1: the granules [0,1),
    # [1,2) and [2,3), the last one for the final instant.
    create_stds(
        tools,
        "strds",
        "inst_rel",
        [MapSpec(f"ir{k}", k + 1, k, None) for k in range(3)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_aggregate(
        input="inst_rel",
        output="inst_rel_out",
        basename="inst_rel_out",
        granularity=1,
        method="sum",
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, "inst_rel_out")] == [
        (0, 1, 1.0),
        (1, 2, 2.0),
        (2, 3, 3.0),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_relative_instant_at_the_end_adds_no_granule_after_it(tools):
    # The long map [0,30) holds 7, the instant on 3 holds 2. A granularity of
    # 10 gives the single granule [0,10) that holds the instant; a granule
    # [10,20) would lie during the long map, which sampling "during" would
    # relate and produce a second map.
    create_stds(
        tools,
        "strds",
        "tail_rel",
        [MapSpec("tr_long", 7, 0, 30), MapSpec("tr_inst", 2, 3, None)],
        temporaltype="relative",
        unit="days",
    )

    tools.t_rast_aggregate(
        input="tail_rel",
        output="tail_rel_out",
        basename="tail_rel_out",
        granularity=10,
        method="sum",
        sampling="during",
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, "tail_rel_out")] == [
        (0, 10, 7.0)
    ]


def test_an_input_that_where_empties_is_refused(tools, four_hourly):
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=four_hourly,
            output="where_empty",
            basename="where_empty",
            granularity="1 day",
            method="sum",
            where="start_time > '2010-01-01'",
        )

    assert f"Space time raster dataset <{four_hourly}> is empty" in message(error.value)


def test_an_unknown_input_is_refused(tools):
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input="no_such_dataset",
            output="unknown_out",
            basename="unknown_out",
            granularity="1 day",
            method="sum",
        )

    assert "Space time dataset <no_such_dataset> of type <strds> not found" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("granularity", "text"),
    [
        ("1 fortnight", "Wrong granularity format: 1 fortnight"),
        ("1.5 days", "Cannot read '1.5 days' as a time step"),
    ],
)
def test_a_wrong_absolute_granularity_is_refused(tools, four_hourly, granularity, text):
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=four_hourly,
            output="bad_gran",
            basename="bad_gran",
            granularity=granularity,
            method="sum",
        )

    assert text in message(error.value)


@pytest.mark.parametrize("granularity", ["abc", "2"])
def test_today_a_granularity_without_a_unit_ends_with_a_traceback(
    tools, four_hourly, granularity
):
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=four_hourly,
            output="bad_gran",
            basename="bad_gran",
            granularity=granularity,
            method="sum",
        )

    assert "IndexError: list index out of range" in message(error.value)


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
@pytest.mark.parametrize("granularity", ["abc", "2"])
def test_a_granularity_without_a_unit_is_refused_with_a_message(
    tools, four_hourly, granularity
):
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=four_hourly,
            output="bad_gran",
            basename="bad_gran",
            granularity=granularity,
            method="sum",
        )

    assert "Traceback" not in message(error.value)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("granularity", "text"),
    [
        ("1 day", "invalid literal for int() with base 10: '1 day'"),
        ("1.5", "invalid literal for int() with base 10: '1.5'"),
        ("0", "The granularity 0 must be positive"),
        ("-1", "The granularity -1 must be positive"),
    ],
)
def test_a_wrong_relative_granularity_is_refused(tools, granularity, text):
    create_stds(
        tools,
        "strds",
        "rel_for_errors",
        [MapSpec("rfe1", 1, 0, 1)],
        temporaltype="relative",
        unit="days",
        overwrite=True,
    )

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input="rel_for_errors",
            output="bad_rel",
            basename="bad_rel",
            granularity=granularity,
            method="sum",
        )

    assert text in message(error.value)


@pytest.mark.parametrize(
    ("option", "value"),
    [("method", "bogus"), ("sampling", "nonsense")],
)
def test_a_value_out_of_range_is_refused(tools, four_hourly, option, value):
    options = {"method": "sum", option: value}

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(
            input=four_hourly,
            output="bad_option",
            basename="bad_option",
            granularity="1 day",
            **options,
        )

    assert f"Value <{value}> out of range for parameter <{option}>" in message(
        error.value
    )


@pytest.mark.parametrize("missing", ["input", "output", "basename", "granularity"])
def test_the_required_options(tools, four_hourly, missing):
    options = {
        "input": four_hourly,
        "output": "req_out",
        "basename": "req_out",
        "granularity": "1 day",
        "method": "sum",
    }
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate(**options)

    assert f"Required parameter <{missing}> not set" in message(error.value)


@pytest.fixture(scope="module")
def half_days(tools):
    """Two maps of 12 hours on the first two days: one map per daily granule"""
    create_stds(
        tools,
        "strds",
        "half_days",
        [MapSpec(f"hd{k}", k + 1, day(k, hours=6), day(k, hours=18)) for k in range(2)],
    )
    return "half_days"


@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        # No number of digits: five.
        ("num", ["00001", "00002"]),
        # The value is not tested, and any text but gran and time counts as
        # num (measured 18.10.2026 with t.rast.aggregate in a temporary
        # project).
        ("anything", ["00001", "00002"]),
    ],
)
def test_the_numeric_suffix_has_five_digits_unless_told_otherwise(
    tools, half_days, suffix, names
):
    output = f"suf_{suffix}"

    tools.t_rast_aggregate(
        input=half_days,
        output=output,
        basename=output,
        granularity="1 day",
        method="sum",
        suffix=suffix,
    )

    assert _suffixes(_rows(tools, output), output) == names
