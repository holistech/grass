"""Test the options of t.rast.aggregate.ds that the characterization leaves out

The sampler gives the granules, so a test names them as [start, end) in days
from 2001-01-01. The expected values are derived from the data in the
comments.
"""

from io import StringIO

import pytest

from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    day,
    intervals,
    register_stds,
)
from grass.temporal.testing.readback import list_maps, message
from grass.tools import ToolError

TIME = "%Y-%m-%d %H:%M:%S"


def _rows(tools, name):
    return [
        (row.name, row.start, row.end, row.min)
        for row in list_maps(tools, "strds", name)
    ]


def _half_days(tools, name, count):
    """count maps of 12 hours on the days 0, 1, ...; map k holds k + 1"""
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{k}", k + 1, day(k, hours=6), day(k, hours=18))
            for k in range(count)
        ],
    )


def _daily_sampler(tools, name, stds_type="strds", count=4, step=2):
    """count intervals of step days that follow each other, from day 0"""
    create_stds(
        tools,
        stds_type,
        name,
        [
            MapSpec(f"{name}_{k}", k, day(step * k), day(step * (k + 1)))
            for k in range(count)
        ],
    )


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
    # The data and the sums are described in temporal/conftest.py. The sampler
    # intervals are the granules [0,10), [10,20) and [20,30).
    output = "dsrel_" + sampling.replace(",", "_")

    tools.t_rast_aggregate_ds(
        input=sampling_relations.dataset,
        sample=sampling_relations.sampler,
        type="strds",
        output=output,
        basename=output,
        method="sum",
        sampling=sampling,
    )

    second = [row for row in _rows(tools, output) if row[1] == sampling_relations.start]
    assert [row[3] for row in second] == [float(sampling_relations.sums[sampling])]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_str3ds_sampler(tools, prefix):
    # Four maps of 12 hours on the days 0 to 3 with 1 to 4; the sampler has
    # the intervals [0,2) and [2,4), so the sums are 1 + 2 and 3 + 4.
    _half_days(tools, f"{prefix}_in", 4)
    _daily_sampler(tools, f"{prefix}_smp", "str3ds", count=2)

    tools.t_rast_aggregate_ds(
        input=f"{prefix}_in",
        sample=f"{prefix}_smp",
        type="str3ds",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="sum",
    )

    assert [(row[1], row[2], row[3]) for row in _rows(tools, f"{prefix}_out")] == [
        (day(0).strftime(TIME), day(2).strftime(TIME), 3.0),
        (day(2).strftime(TIME), day(4).strftime(TIME), 7.0),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize(
    ("suffix", "names"),
    [
        ("gran", ["2001_01_01", "2001_01_03"]),
        ("time", ["2001_01_01T00_00_00", "2001_01_03T00_00_00"]),
        ("num", ["00001", "00002"]),
        ("num%03", ["001", "002"]),
    ],
)
def test_suffix(tools, prefix, suffix, names):
    # The granules of the sampler [0,2) and [2,4) hold the maps 1 and 2 and 3
    # and 4. The default granularity of the names is the one of the sampler,
    # 2 days, which the names show as the day.
    _half_days(tools, f"{prefix}_in", 4)
    _daily_sampler(tools, f"{prefix}_smp", count=2)

    tools.t_rast_aggregate_ds(
        input=f"{prefix}_in",
        sample=f"{prefix}_smp",
        type="strds",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="sum",
        suffix=suffix,
    )

    assert [row[0] for row in _rows(tools, f"{prefix}_out")] == [
        f"{prefix}_out_{name}" for name in names
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_where_restricts_the_input_and_the_sampler(tools, prefix):
    # Five maps with 1 to 5 on the days 0 to 4 and the sampler intervals
    # [0,1), [1,2), [2,3), [3,4), [4,5). The condition keeps the maps and the
    # intervals that start on day 2 or later: 3, 4 and 5 on the last three.
    _half_days(tools, f"{prefix}_in", 5)
    _daily_sampler(tools, f"{prefix}_smp", count=5, step=1)

    tools.t_rast_aggregate_ds(
        input=f"{prefix}_in",
        sample=f"{prefix}_smp",
        type="strds",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="sum",
        where=f"start_time >= '{day(2).strftime(TIME)}'",
    )

    assert [(row[1], row[3]) for row in _rows(tools, f"{prefix}_out")] == [
        (day(2).strftime(TIME), 3.0),
        (day(3).strftime(TIME), 4.0),
        (day(4).strftime(TIME), 5.0),
    ]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overlapping_sampler_intervals_collect_the_same_map_twice(tools, prefix):
    # Sampler [0,2), [1,3), [2,4) over the maps 1 to 4 on days 0 to 3: the
    # granules hold the maps of days 0 and 1 (3), of days 1 and 2 (5) and of
    # days 2 and 3 (7).
    _half_days(tools, f"{prefix}_in", 4)
    create_stds(
        tools,
        "strds",
        f"{prefix}_smp",
        [MapSpec(f"{prefix}_smp_{k}", k, day(k), day(k + 2)) for k in range(3)],
    )

    tools.t_rast_aggregate_ds(
        input=f"{prefix}_in",
        sample=f"{prefix}_smp",
        type="strds",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="sum",
    )

    assert [row[3] for row in _rows(tools, f"{prefix}_out")] == [3.0, 5.0, 7.0]


@pytest.fixture(scope="module")
def eight_halves(tools):
    """24 maps that follow each other, map k holds k from 4 (k-1) to 4 k hours"""
    tools.r_mapcalc(file=StringIO("".join(f"dsh{k} = {k}\n" for k in range(1, 25))))
    register_stds(
        tools,
        "strds",
        "ds_four_hourly",
        [
            MapSpec(f"dsh{k}", k, day(0, hours=4 * (k - 1)), day(0, hours=4 * k))
            for k in range(1, 25)
        ],
    )
    # Eight intervals of 12 hours, from the start of the first map.
    create_stds(
        tools,
        "strds",
        "ds_half_days",
        [
            MapSpec(f"dsd{k}", k, day(0, hours=12 * k), day(0, hours=12 * (k + 1)))
            for k in range(8)
        ],
    )
    return "ds_four_hourly", "ds_half_days"


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_nprocs_gives_the_same_maps_as_one_process(tools, eight_halves):
    # An interval of 12 hours holds three maps, 3j+1 to 3j+3: 9j+6 for j = 0
    # to 7.
    dataset, sampler = eight_halves
    results = {}
    for nprocs in (1, 2, 4):
        output = f"dspar_{nprocs}"
        tools.t_rast_aggregate_ds(
            input=dataset,
            sample=sampler,
            type="strds",
            output=output,
            basename=output,
            method="sum",
            nprocs=nprocs,
        )
        results[nprocs] = _rows(tools, output)

    assert [row[3] for row in results[1]] == [9.0 * j + 6 for j in range(8)]
    for nprocs in (2, 4):
        assert [row[0].removeprefix(f"dspar_{nprocs}_") for row in results[nprocs]] == [
            row[0].removeprefix("dspar_1_") for row in results[1]
        ]
        assert [row[1:] for row in results[nprocs]] == [row[1:] for row in results[1]]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("flags", ["", "n"])
def test_precipitation_by_a_vector_sampler(tools, flags):
    # The deterministic part of the old shell test: six monthly maps from
    # March with 100, 150, 250, 250, 150, 100, and three vector intervals.
    # [Jan, Apr) holds March (100), [May, Jul) holds May and June (250 + 250),
    # [Aug, Dec) holds August (100); no granule is null, so -n changes nothing.
    values = [100, 150, 250, 250, 150, 100]
    name = f"dsprecip_{flags or 'plain'}"
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{i}", value, start, end)
            for i, (value, (start, end)) in enumerate(
                zip(values, intervals(6, start=2), strict=True), start=1
            )
        ],
    )
    create_stds(
        tools,
        "stvds",
        f"{name}_soil",
        [
            MapSpec(f"{name}_soil_{i}", 0, day(start), day(end))
            for i, (start, end) in enumerate([(0, 90), (120, 181), (212, 334)], 1)
        ],
    )

    tools.t_rast_aggregate_ds(
        input=name,
        sample=f"{name}_soil",
        type="stvds",
        output=f"{name}_out",
        basename=f"{name}_out",
        method="sum",
        flags=flags,
    )

    assert [row[3] for row in _rows(tools, f"{name}_out")] == [100.0, 500.0, 100.0]


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_types_of_time_must_match(tools, prefix):
    _half_days(tools, f"{prefix}_in", 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_rel",
        [MapSpec(f"{prefix}_rel_0", 1, 0, 2)],
        temporaltype="relative",
        unit="days",
    )

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_rel",
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
        )

    assert "Input and aggregation dataset must have the same temporal type" in message(
        error.value
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_sampler_needs_intervals(tools, prefix):
    _half_days(tools, f"{prefix}_in", 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_pts",
        [MapSpec(f"{prefix}_pts_{k}", k, day(k), None) for k in range(2)],
    )

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_pts",
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
        )

    assert (
        "All registered maps of the aggregation dataset must have time intervals"
        in message(error.value)
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_an_input_that_where_empties_is_refused(tools, prefix):
    _half_days(tools, f"{prefix}_in", 2)
    _daily_sampler(tools, f"{prefix}_smp", count=1)

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_smp",
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
            where="start_time > '2010-01-01'",
        )

    assert f"Space time raster dataset <{prefix}_in> is empty" in message(error.value)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_a_sampler_that_where_empties_is_refused(tools, prefix):
    # The names of the input maps are <prefix>_in_0 and so on, those of the
    # sampler <prefix>_smp_0, so the condition keeps only input maps.
    _half_days(tools, f"{prefix}_in", 2)
    _daily_sampler(tools, f"{prefix}_smp", count=1)

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_smp",
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
            where=f"name LIKE '{prefix}_in%'",
        )

    assert f"Space time dataset <{prefix}_smp> is empty" in message(error.value)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_sampler_intervals_that_are_equal_are_refused(tools, prefix):
    # Two intervals give two maps of one name.
    _half_days(tools, f"{prefix}_in", 2)
    create_stds(
        tools,
        "strds",
        f"{prefix}_smp",
        [MapSpec(f"{prefix}_smp_{k}", k, day(0), day(2)) for k in range(2)],
    )

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_smp",
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
        )

    assert "Several maps would get the same name" in message(error.value)


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("which", ["input", "sample"])
def test_an_unknown_dataset_is_refused(tools, prefix, which):
    _half_days(tools, f"{prefix}_in", 2)
    _daily_sampler(tools, f"{prefix}_smp", count=1)
    options = {"input": f"{prefix}_in", "sample": f"{prefix}_smp"}
    options[which] = "no_such_dataset"

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            type="strds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
            **options,
        )

    assert "Space time dataset <no_such_dataset> of type <strds> not found" in message(
        error.value
    )


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_the_type_selects_the_sampler(tools, prefix):
    _half_days(tools, f"{prefix}_in", 2)
    _daily_sampler(tools, f"{prefix}_smp", count=1)

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_smp",
            type="stvds",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            method="sum",
        )

    assert f"Space time dataset <{prefix}_smp> of type <stvds> not found" in message(
        error.value
    )


@pytest.mark.parametrize(
    ("option", "value"),
    [("method", "bogus"), ("sampling", "nonsense"), ("type", "raster")],
)
def test_a_value_out_of_range_is_refused(tools, prefix, option, value):
    options = {"method": "sum", "type": "strds", option: value}

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input="a",
            sample="b",
            output=f"{prefix}_out",
            basename=f"{prefix}_out",
            **options,
        )

    assert f"Value <{value}> out of range for parameter <{option}>" in message(
        error.value
    )


@pytest.mark.parametrize("missing", ["input", "sample", "output", "basename"])
def test_the_required_options(tools, prefix, missing):
    options = {
        "input": "a",
        "sample": "b",
        "output": f"{prefix}_out",
        "basename": f"{prefix}_out",
    }
    del options[missing]

    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(method="sum", **options)

    assert f"Required parameter <{missing}> not set" in message(error.value)
