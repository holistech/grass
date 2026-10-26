# SPDX-License-Identifier: GPL-2.0-or-later

"""Characterize the functions that were split into steps

Four functions were too complex to read and were split: the adjustment of a
time to a granularity, the delta between two times, the where statement for
temporal relations and the serialization of vector statistics. The golden file
holds what the functions returned before the split, for the inputs below, so
that the split changed no result. The golden values were recorded from the code
before the split on 26.10.2026.
"""

import builtins
import json
from datetime import datetime
from pathlib import Path

import pytest

from grass.temporal.datetime_math import (
    adjust_datetime_to_granularity,
    compute_datetime_delta,
)
from grass.temporal.stds_map_register import _map_time_of
from grass.temporal.topology import create_temporal_relation_sql_where_statement
from grass.temporal.univar_statistics import _vector_columns, _vector_fields

GOLDEN = json.loads(
    Path(__file__).with_name("data").joinpath("complexity_splits.json").read_text()
)

RELATIONS = (
    "use_start",
    "use_during",
    "use_overlap",
    "use_contain",
    "use_equal",
    "use_follows",
    "use_precedes",
)


@pytest.mark.parametrize(("moment", "granularity", "expected"), GOLDEN["adjust"])
def test_a_time_is_adjusted_to_a_granularity_as_before(moment, granularity, expected):
    moment = datetime.fromisoformat(moment)
    if expected.startswith("ERR:") if isinstance(expected, str) else False:
        with pytest.raises(getattr(builtins, expected[4:])):
            adjust_datetime_to_granularity(moment, granularity)
        return
    result = adjust_datetime_to_granularity(moment, granularity)
    assert (result.isoformat() if hasattr(result, "isoformat") else result) == expected


@pytest.mark.parametrize(("start", "end", "expected"), GOLDEN["delta"])
def test_the_delta_between_two_times_is_as_before(start, end, expected):
    result = compute_datetime_delta(
        datetime.fromisoformat(start), datetime.fromisoformat(end)
    )
    assert dict(result) == expected


@pytest.mark.parametrize(("pair", "flags", "expected"), GOLDEN["where"])
def test_the_where_statement_of_the_relations_is_as_before(pair, flags, expected):
    start, end = (
        datetime.fromisoformat(value) if isinstance(value, str) else value
        for value in pair
    )
    result = create_temporal_relation_sql_where_statement(
        start, end, **dict(zip(RELATIONS, flags, strict=True))
    )
    assert result == expected


@pytest.mark.parametrize("vector_type", ["point", "centroid", "line", "area"])
@pytest.mark.parametrize("extended", [False, True])
@pytest.mark.parametrize("complete", [False, True])
def test_a_line_of_vector_statistics_has_the_columns_of_its_header(
    vector_type, extended, complete
):
    stats = {"n": 5, "nmissing": 1, "nnull": 0}
    if complete:
        stats.update(
            dict.fromkeys(
                ("min", "max", "range", "mean", "mean_abs", "first_quartile"), 1
            )
        )
        stats.update(
            dict.fromkeys(
                (
                    "population_stddev",
                    "population_variance",
                    "population_coeff_variation",
                    "sample_stddev",
                    "sample_variance",
                    "kurtosis",
                    "skewness",
                    "median",
                    "third_quartile",
                    "percentile_90",
                ),
                2,
            )
        )
    columns = _vector_columns(vector_type, extended)
    fields = _vector_fields("v@PERMANENT", "s", "e", stats, vector_type, extended)
    assert len(fields) == len(columns)
    # The header is the one the tool always printed
    assert columns[:9] == [
        "id",
        "start",
        "end",
        "n",
        "nmissing",
        "nnull",
        "min",
        "max",
        "range",
    ]
    assert len(columns) == 9 + (9 if vector_type in {"point", "centroid"} else 0) + (
        4 if extended and vector_type in {"point", "centroid"} else 0
    )
    if extended and vector_type in {"point", "centroid"}:
        assert columns[-4:] == [
            "first_quartile",
            "median",
            "third_quartile",
            "percentile_90",
        ]
        assert columns[-5] == "skewness"
    assert fields[:6] == ["v@PERMANENT", "s", "e", "5", "1", "0"]
    # Without the statistics the fields stay empty
    assert (fields[6] != "") == complete


def test_the_statistics_without_a_range_leave_its_three_fields_empty():
    stats = {"n": 1, "nmissing": 0, "nnull": 0}
    assert _vector_fields("v", 1, 2, stats, "line", False)[6:] == ["", "", ""]


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ({"interval": 3, "point": 0, "invalid": 0}, "interval"),
        ({"interval": 0, "point": 2, "invalid": 0}, "point"),
        ({"interval": 3, "point": 2, "invalid": 0}, "mixed"),
        ({"interval": 3, "point": 2, "invalid": 1}, "invalid"),
        ({"interval": 3, "point": 0, "invalid": 1}, "invalid"),
        ({"interval": 0, "point": 0, "invalid": 0}, "invalid"),
    ],
)
def test_the_temporal_type_of_the_maps_follows_their_counts(counts, expected):
    assert _map_time_of(counts) == expected
