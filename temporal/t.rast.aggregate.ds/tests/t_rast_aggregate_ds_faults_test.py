"""Test the suffix gran, the end of a sampler interval, the names and the options of t.rast.aggregate.ds

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month. The granularity is that of the
sampler, here the month series.

A sampler interval includes its start and excludes its end, so a time
instant on the end belongs to the next interval. A result map may not get
the name of an input map. The descriptions of nprocs and type say what the
options do.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.tools import ToolError

ENDS = [
    datetime(2026, 1, 31),
    datetime(2026, 2, 28),
    datetime(2026, 3, 31),
    datetime(2026, 4, 30),
]


def month_end_series(tools, name):
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
    )


def test_gran_suffix_of_month_end_series_names_the_month(tools, prefix):
    month_end_series(tools, f"{prefix}_in")

    create_stds(
        tools,
        "strds",
        f"{prefix}_days",
        [
            MapSpec(f"{prefix}_d{k}", k, datetime(2026, 2, k), datetime(2026, 2, k + 1))
            for k in (1, 2)
        ]
        + [MapSpec(f"{prefix}_d3", 3, datetime(2026, 3, 5), datetime(2026, 3, 6))]
        + [MapSpec(f"{prefix}_d4", 4, datetime(2026, 4, 5), datetime(2026, 4, 6))],
    )
    tools.t_rast_aggregate_ds(
        input=f"{prefix}_days",
        output=prefix,
        basename=f"{prefix}_b",
        sample=f"{prefix}_in",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]


def june_sampler(tools, name):
    """Two intervals, 10 to 20 June and 20 to 30 June 2026"""
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_1", 1, datetime(2026, 6, 10), datetime(2026, 6, 20)),
            MapSpec(f"{name}_2", 2, datetime(2026, 6, 20), datetime(2026, 6, 30)),
        ],
    )


def test_instant_at_end_of_sampler_belongs_to_next(tools, prefix):
    """The instant of 20 June is not in 10 to 20 June but in 20 to 30 June"""
    june_sampler(tools, f"{prefix}_s")
    create_stds(
        tools,
        "strds",
        f"{prefix}_p",
        [
            MapSpec(f"{prefix}_p10", 10, datetime(2026, 6, 10)),
            MapSpec(f"{prefix}_p20", 20, datetime(2026, 6, 20)),
        ],
    )
    tools.t_rast_aggregate_ds(
        input=f"{prefix}_p",
        sample=f"{prefix}_s",
        output=f"{prefix}_out",
        basename=f"{prefix}_out",
        method="sum",
        sampling="contains",
    )
    rows = list_maps(tools, "strds", f"{prefix}_out")
    assert [(row.start, row.end, row.min) for row in rows] == [
        ("2026-06-10 00:00:00", "2026-06-20 00:00:00", 10.0),
        ("2026-06-20 00:00:00", "2026-06-30 00:00:00", 20.0),
    ]


@pytest.mark.parametrize("overwrite", [False, True])
def test_output_name_equal_to_input_map_is_refused(tools, prefix, overwrite):
    """basename and suffix num give the name of the input map, which stays"""
    june_sampler(tools, f"{prefix}_s")
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [MapSpec(f"{prefix}_b_00001", 7, datetime(2026, 6, 11), datetime(2026, 6, 12))],
    )
    before = inventory(tools)
    with pytest.raises(ToolError) as error:
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_s",
            output=f"{prefix}_out",
            basename=f"{prefix}_b",
            suffix="num",
            method="sum",
            overwrite=overwrite,
        )
    assert f"The result map <{prefix}_b_00001> has the name of an input map" in message(
        error.value
    )
    assert inventory(tools) == before
    assert [row.min for row in list_maps(tools, "strds", f"{prefix}_in")] == [7.0]


def option_descriptions(tools):
    root = ET.fromstring(
        tools.call_cmd(["t.rast.aggregate.ds", "--interface-description"]).stdout
    )
    return {
        key: root.findtext(f"parameter[@name='{key}']/description").strip()
        for key in ("nprocs", "type")
    }


def test_option_descriptions_match_behaviour(tools, prefix):
    """nprocs runs r.series processes, not r.mapcalc; type is that of sample

    A vector sampler of the type given in type gives its intervals to the
    aggregation, and nprocs 1 and 2 give the same maps.
    """
    texts = option_descriptions(tools)
    assert texts["nprocs"] == "Number of r.series processes to run in parallel"
    assert texts["type"] == "Type of the space time dataset given in sample"
    for k in (1, 2):
        tools.v_random(output=f"{prefix}_v{k}", npoints=1, seed=k)
    tools.t_create(
        type="stvds", output=f"{prefix}_vs", title="sampler", description="sampler"
    )
    tools.t_register(
        type="vector",
        input=f"{prefix}_vs",
        maps=f"{prefix}_v1,{prefix}_v2",
        start="2026-06-10",
        increment="10 days",
        flags="i",
    )
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_d{day}",
                day,
                datetime(2026, 6, day),
                datetime(2026, 6, day + 1),
            )
            for day in (11, 12, 21)
        ],
    )
    results = []
    for nprocs in (1, 2):
        tools.t_rast_aggregate_ds(
            input=f"{prefix}_in",
            sample=f"{prefix}_vs",
            type="stvds",
            output=f"{prefix}_out{nprocs}",
            basename=f"{prefix}_out{nprocs}",
            method="sum",
            nprocs=nprocs,
        )
        rows = list_maps(tools, "strds", f"{prefix}_out{nprocs}")
        results.append([(row.start, row.end, row.min) for row in rows])
    assert (
        results[0]
        == results[1]
        == [
            ("2026-06-10 00:00:00", "2026-06-20 00:00:00", 23.0),
            ("2026-06-20 00:00:00", "2026-06-30 00:00:00", 21.0),
        ]
    )
