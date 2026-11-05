"""Test the time suffix gran and an expression that names another dataset

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month. The suffix gran
follows the granularity of the input dataset also for time instants, which have
no end: the clock time of the instants decides that granularity.
"""

from datetime import datetime
from itertools import pairwise

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.readback import inventory, list_maps, message, stds_info
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

    tools.t_rast_extract(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        expression=f"{prefix}_in * 2",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]


@pytest.mark.parametrize(
    ("hour", "granularity", "suffixes"),
    [
        # Ten days at midnight: the unit of the granularity is the day.
        (0, "'10 days'", ["2026_06_11", "2026_06_21"]),
        # Ten days at 10:30: compute_datetime_delta counts the hours and the
        # minutes of such a step, so the granularity is "14400 minutes" and
        # the names, which follow the unit of the granularity, carry the
        # time of the day.
        (10, "'14400 minutes'", ["2026_06_11_10_30", "2026_06_21_10_30"]),
    ],
)
def test_suffix_gran_for_instants_with_time(tools, prefix, hour, granularity, suffixes):
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_i{number}",
                number,
                datetime(2026, 6, day, hour, 30 * bool(hour)),
            )
            for number, day in enumerate((11, 21), start=1)
        ],
    )
    assert stds_info(tools, "strds", f"{prefix}_in")["granularity"] == granularity

    tools.t_rast_extract(
        input=f"{prefix}_in",
        output=prefix,
        basename=f"{prefix}_b",
        expression=f"{prefix}_in * 2",
    )

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [f"{prefix}_b_{suffix}" for suffix in suffixes]


def test_other_dataset_in_expression_is_refused(tools, prefix):
    """Only the name of the input dataset stands for a map in the expression"""
    for name, value in (("in", 1), ("other", 5)):
        create_stds(
            tools,
            "strds",
            f"{prefix}_{name}",
            [
                MapSpec(
                    f"{prefix}_{name}_map",
                    value,
                    datetime(2026, 1, 1),
                    datetime(2026, 2, 1),
                )
            ],
        )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_extract(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_b",
            expression=f"{prefix}_in + {prefix}_other",
        )

    text = message(error.value)
    assert f"Invalid map <{prefix}_other>" in text
    assert "Error in computation process" in text
    assert inventory(tools) == before
