"""Test t.rast.neighbors on a month series from a month end and on equal names

A month step that is cut to the end of a shorter month counts as a month, so
the series from 31 January (28 February, 31 March) has the granularity
"1 month" and the suffix gran names the new maps by the month. Maps that start
and end at the same time of the day other than midnight are named by the day.
Two maps of one time get one name from that suffix; the run is refused before
it writes.
"""

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

    tools.t_rast_neighbors(input=f"{prefix}_in", output=prefix, basename=f"{prefix}_b")

    names = [row.name for row in list_maps(tools, "strds", prefix)]
    assert names == [
        f"{prefix}_b_2026_01",
        f"{prefix}_b_2026_02",
        f"{prefix}_b_2026_03",
    ]


@pytest.mark.parametrize(
    ("nprocs", "overwrite"),
    [(1, False), (2, False), (1, True)],
    ids=["nprocs 1", "nprocs 2", "overwrite"],
)
def test_equal_result_names_are_refused_first(tools, prefix, nprocs, overwrite):
    """Two maps of one time get the name of the suffix gran twice

    The run is refused before the first r.neighbors writes a map, and leaves
    nothing behind, without a traceback.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_{number}", number, datetime(2026, 1, 1), datetime(2026, 2, 1)
            )
            for number in (1, 2)
        ]
        + [MapSpec(f"{prefix}_3", 3, datetime(2026, 2, 1), datetime(2026, 3, 1))],
    )
    before = inventory(tools)

    with pytest.raises(ToolError) as error:
        tools.t_rast_neighbors(
            input=f"{prefix}_in",
            output=f"{prefix}_out",
            basename=f"{prefix}_b",
            nprocs=nprocs,
            overwrite=overwrite,
        )

    text = message(error.value)
    assert (
        f"The maps <{prefix}_1@PERMANENT> and <{prefix}_2@PERMANENT> are given the "
        f"same name <{prefix}_b_2026_01@PERMANENT> by the suffix gran. Use the suffix num"
        in text
    )
    assert "Traceback" not in text
    assert inventory(tools) == before


def test_equal_result_names_with_overwrite_keep_registered_maps(tools, prefix):
    """A refused overwrite run leaves the maps of an earlier run registered

    The earlier run made <prefix>_b_2026_01 and <prefix>_b_2026_02 in the
    dataset <prefix>_res. The overwrite run on the dataset with two maps of
    January is refused, and the entries must not have been removed first.
    """
    create_stds(
        tools,
        "strds",
        f"{prefix}_in",
        [
            MapSpec(
                f"{prefix}_{number}", number, datetime(2026, 1, 1), datetime(2026, 2, 1)
            )
            for number in (1, 2)
        ]
        + [MapSpec(f"{prefix}_3", 3, datetime(2026, 2, 1), datetime(2026, 3, 1))],
    )
    tools.t_rast_extract(
        input=f"{prefix}_in",
        output=f"{prefix}_sub",
        where=f"name != '{prefix}_2'",
    )
    tools.t_rast_neighbors(
        input=f"{prefix}_sub", output=f"{prefix}_res", basename=f"{prefix}_b"
    )
    registered = list_maps(tools, "strds", f"{prefix}_res")
    assert len(registered) == 2
    before = inventory(tools)

    with pytest.raises(ToolError):
        tools.t_rast_neighbors(
            input=f"{prefix}_in",
            output=f"{prefix}_res2",
            basename=f"{prefix}_b",
            overwrite=True,
        )

    assert list_maps(tools, "strds", f"{prefix}_res") == registered
    assert inventory(tools) == before


# Two maps of ten days that start and end at 10:30, with a gap of ten days:
# the time of the day is the same at both ends of each step, so the
# granularity is "10 days" and the suffix gran names a map by the day. Before
# 05.11.2026 the granularity was "14400 minutes" and the names ended with the
# hour and the minute, such as _2026_06_11_10_30.
AT_HALF_PAST_TEN = [
    (datetime(2026, 6, 1, 10, 30), datetime(2026, 6, 11, 10, 30)),
    (datetime(2026, 6, 21, 10, 30), datetime(2026, 7, 1, 10, 30)),
]


def half_past_ten_series(tools, name):
    create_stds(
        tools,
        "strds",
        name,
        [
            MapSpec(f"{name}_{number}", number, start, end)
            for number, (start, end) in enumerate(AT_HALF_PAST_TEN, start=1)
        ],
    )


def test_gran_suffix_of_maps_at_the_same_time_of_day_names_the_day(tools, prefix):
    half_past_ten_series(tools, f"{prefix}_in")
    tools.t_rast_neighbors(
        input=f"{prefix}_in", output=prefix, basename=f"{prefix}_b", method="average"
    )
    assert [row.name for row in list_maps(tools, "strds", prefix)] == [
        f"{prefix}_b_2026_06_01",
        f"{prefix}_b_2026_06_21",
    ]
