"""t.sample on the scenario of the manual: monthly rasters and a vector sampler

The inputs prec_1 to prec_6 are the months January to June 2001 (31, 28, 31,
30, 31 and 30 days). The sampler pnts0 has the maps pnts1 [Jan 1, Mar 1) and
pnts2 [May 1, Jul 1) and so three granules: the 59 days of pnts1, the gap
[Mar 1, May 1) of 61 days and the 61 days of pnts2. The sampler pnts_five has
six contiguous granules of five days from January 1. Every expectation is
derived from these times; the tool prints the matrix, so a granule is
compared with the months it relates to.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, register_stds

MONTHS = [datetime(2001, month, 1) for month in range(1, 8)]

# (sampler map, start, end, days, days since the first start) of pnts0
GRANULES = [
    ("pnts1", "2001-01-01", "2001-03-01", "59.0", "0.0"),
    (None, "2001-03-01", "2001-05-01", "61.0", "59.0"),
    ("pnts2", "2001-05-01", "2001-07-01", "61.0", "120.0"),
]


def _vector_stds(tools, name, rows):
    """A stvds of one point per row (map, start, end); the seed is the row number"""
    for seed, (map_name, _, _) in enumerate(rows, 1):
        tools.v_random(output=map_name, npoints=1, seed=seed)
    register_stds(
        tools, "stvds", name, [MapSpec(m, 1, start, end) for m, start, end in rows]
    )


@pytest.fixture(scope="module")
def scenario(tools):
    create_stds(
        tools,
        "strds",
        "precip",
        [MapSpec(f"prec_{i}", i, MONTHS[i - 1], MONTHS[i]) for i in range(1, 7)],
    )
    _vector_stds(
        tools,
        "pnts0",
        [("pnts1", MONTHS[0], MONTHS[2]), ("pnts2", MONTHS[4], MONTHS[6])],
    )
    _vector_stds(
        tools,
        "pnts_five",
        [
            (
                f"five_{i}",
                datetime(2001, 1, 1 + 5 * (i - 1)),
                datetime(2001, 1, 1 + 5 * i),
            )
            for i in range(1, 7)
        ],
    )
    return tools


def _name(name):
    return "None" if name is None else f"{name}@PERMANENT"


def _table(sampler, inputs, rows):
    """The printed matrix; rows are (sampler map, [input maps per column], ...)

    Each input column of a row is a list of map names or None.
    """
    columns = "|".join(f"{name}@PERMANENT" for name in inputs)
    lines = [
        f"{sampler}@PERMANENT|{columns}"
        "|start_time|end_time|interval_length|distance_from_begin"
    ]
    for (granule, start, end, days, since), cells in zip(GRANULES, rows, strict=True):
        shown = "|".join(
            "None" if not cell else ",".join(f"{m}@PERMANENT" for m in cell)
            for cell in cells
        )
        lines.append(
            f"{_name(granule)}|{shown}|{start} 00:00:00|{end} 00:00:00|{days}|{since}"
        )
    return "\n".join(lines)


def _run(tools, **kwargs):
    return tools.t_sample(**kwargs).text


# The input given twice has two equal columns.
TWICE = ["precip", "precip"]
TWICE_OPTION = ",".join(TWICE)
# Per method, the maps of each of the three granules.
#
# start, contain: the months that begin inside a granule. The months are
# whole in it, so contain gives the same maps as start.
# equal, overlap, during: no month equals a granule, none reaches over its
# border, and none is longer than a granule.
# precedes: the month that begins where the granule ends (March 1 for pnts1,
# May 1 for the gap), none after pnts2. follows: the month that ends where
# the granule begins (February for the gap, April for pnts2).
# precedes,follows: both blocks in this order.
IN_GRANULES = [["prec_1", "prec_2"], ["prec_3", "prec_4"], ["prec_5", "prec_6"]]
NOTHING = [None, None, None]
BY_METHOD = {
    "start": IN_GRANULES,
    "contain": IN_GRANULES,
    "equal": NOTHING,
    "overlap": NOTHING,
    "during": NOTHING,
    "precedes": [["prec_3"], ["prec_5"], None],
    "follows": [None, ["prec_2"], ["prec_4"]],
    "precedes,follows": [["prec_3"], ["prec_5", "prec_2"], ["prec_4"]],
}


@pytest.mark.parametrize("method", BY_METHOD)
def test_every_method_on_the_vector_sampler(scenario, method):
    rows = [[cell, cell] for cell in BY_METHOD[method]]
    assert _run(
        scenario,
        input=TWICE_OPTION,
        samtype="stvds",
        sample="pnts0",
        method=method,
        flags="c",
    ) == _table("pnts0", TWICE, rows)


@pytest.mark.parametrize("flags", ["c", "cs"])
def test_the_default_methods_give_the_contained_months(scenario, flags):
    """Of during, overlap, contain and equal only contain relates months here.
    The point of each sampler map lies inside the raster extent, so -s keeps
    them."""
    assert _run(
        scenario, input="precip", samtype="stvds", sample="pnts0", flags=flags
    ) == _table("pnts0", ["precip"], [[cell] for cell in IN_GRANULES])


def test_a_vector_dataset_as_input_and_raster_months_as_sampler(scenario):
    """The months are the granules; each lies during the sampler map that
    contains it, the months of the gap relate to none."""
    expected = "\n".join(
        [
            "precip@PERMANENT|pnts0@PERMANENT|start_time|end_time"
            "|interval_length|distance_from_begin",
            *(
                f"prec_{i}@PERMANENT|{_name(found)}|{start} 00:00:00|{end} 00:00:00"
                f"|{days}|{since}"
                for i, found, start, end, days, since in (
                    (1, "pnts1", "2001-01-01", "2001-02-01", "31.0", "0.0"),
                    (2, "pnts1", "2001-02-01", "2001-03-01", "28.0", "31.0"),
                    (3, None, "2001-03-01", "2001-04-01", "31.0", "59.0"),
                    (4, None, "2001-04-01", "2001-05-01", "30.0", "90.0"),
                    (5, "pnts2", "2001-05-01", "2001-06-01", "31.0", "120.0"),
                    (6, "pnts2", "2001-06-01", "2001-07-01", "30.0", "151.0"),
                )
            ),
        ]
    )
    assert (
        _run(
            scenario,
            input="pnts0",
            intype="stvds",
            samtype="strds",
            sample="precip",
            method="during",
            flags="c",
        )
        == expected
    )


def test_five_day_granules_all_lie_during_the_first_month(scenario):
    """Each of the six granules, from January 1 to January 31, is inside
    prec_1 and nothing else"""
    lines = _run(
        scenario, input="precip", samtype="stvds", sample="pnts_five", flags="c"
    ).splitlines()
    assert lines[0] == (
        "pnts_five@PERMANENT|precip@PERMANENT|start_time|end_time"
        "|interval_length|distance_from_begin"
    )
    assert lines[1:] == [
        f"five_{i}@PERMANENT|prec_1@PERMANENT|2001-01-{1 + 5 * (i - 1):02d} 00:00:00"
        f"|2001-01-{1 + 5 * i:02d} 00:00:00|5.0|{5.0 * (i - 1)}"
        for i in range(1, 7)
    ]


@pytest.mark.parametrize("flags", ["c", "cs"])
def test_a_dataset_sampled_by_itself_relates_each_map_to_itself(scenario, flags):
    """The default list contains equal; the granule lengths are those of the
    months and the distances their running sum (0, 31, 59, 90, 120, 151)"""
    lengths = [31, 28, 31, 30, 31, 30]
    since = [0, 31, 59, 90, 120, 151]
    assert _run(
        scenario, input="precip", samtype="strds", sample="precip", flags=flags
    ).splitlines() == [
        "precip@PERMANENT|precip@PERMANENT|start_time|end_time"
        "|interval_length|distance_from_begin",
        *(
            f"prec_{i}@PERMANENT|prec_{i}@PERMANENT|{MONTHS[i - 1]}|{MONTHS[i]}"
            f"|{lengths[i - 1]}.0|{since[i - 1]}.0"
            for i in range(1, 7)
        ),
    ]
