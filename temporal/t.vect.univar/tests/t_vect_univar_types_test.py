"""Test the options type and layer of t.vect.univar

Lines and areas print only the columns up to range (the header of every type
other than point and centroid ends there). The maps are described in
conftest.py.
"""

import math

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

SHORT = "id|start|end|n|nmissing|nnull|min|max|range"


def _lines(tools, **options):
    return tools.t_vect_univar(**options).stdout.splitlines()


def test_type_line_uses_the_categories_of_the_lines(tools, lines):
    assert _lines(tools, input=lines, column="value", type="line") == [
        SHORT,
        "ul_1@PERMANENT|2001-01-01 00:00:00|2001-02-01 00:00:00|2|0|0|10|20|10",
    ]


def test_type_area_uses_the_categories_of_the_centroids(tools, areas):
    assert _lines(tools, input=areas, column="value", type="area") == [
        SHORT,
        "ua_1@PERMANENT|2001-01-01 00:00:00|2001-02-01 00:00:00|2|0|0|100|200|100",
    ]


def test_type_centroid_prints_all_statistics(tools, areas):
    lines = _lines(tools, input=areas, column="value", type="centroid", flags="e")
    header = lines[0].split("|")
    row = dict(zip(header, lines[1].split("|"), strict=True))

    # Values 100 and 200: mean 150, deviations -50 and 50, population variance
    # 2500, sample variance 5000, kurtosis 50^4 / 5000^2 - 3 = 0.25 - 3 = -2.75;
    # the quartiles follow the index rule of t.vect.univar for two values.
    assert header[-4:] == [
        "first_quartile",
        "median",
        "third_quartile",
        "percentile_90",
    ]
    assert float(row["mean"]) == 150
    assert float(row["population_variance"]) == pytest.approx(2500)
    assert float(row["sample_stddev"]) == pytest.approx(math.sqrt(5000), rel=1e-5)
    assert float(row["kurtosis"]) == pytest.approx(-2.75)
    assert [float(row[key]) for key in header[-4:]] == [100, 150, 200, 200]


def test_the_e_flag_adds_nothing_for_a_line(tools, lines):
    assert _lines(tools, input=lines, column="value", type="line", flags="e")[0] == (
        SHORT
    )


def test_type_boundary_finds_no_category(tools, areas):
    # The boundaries have no category: a row of zeros without statistics.
    assert _lines(tools, input=areas, column="value", type="boundary", flags="u") == [
        "ua_1@PERMANENT|2001-01-01 00:00:00|2001-02-01 00:00:00|0|0|0|||"
    ]


def test_the_default_type_is_point(tools, lines):
    # The lines are not points: no value is found.
    row = _lines(tools, input=lines, column="value", flags="u")[0]

    assert row.split("|")[3:6] == ["0", "0", "0"]


def test_the_type_of_the_maps_decides_what_is_found(tools, points):
    row = _lines(tools, input=points, column="value", type="line", flags="u")[0]

    assert row.split("|")[3] == "0"


def test_the_layer_option_applies_to_a_map_without_a_registered_layer(tools, layers):
    rows = _lines(tools, input=layers, column="value", layer=2, flags="u")

    # lm:2 keeps its registered layer 2 (101 to 103); lu takes layer 2 (the
    # same values).
    assert [(row.split("|")[0], row.split("|")[6:9]) for row in rows] == [
        ("lm@PERMANENT", ["101", "103", "2"]),
        ("lu@PERMANENT", ["101", "103", "2"]),
    ]


def test_the_default_layer_is_one_for_a_map_without_a_registered_layer(tools, layers):
    rows = _lines(tools, input=layers, column="value", flags="u")

    # lm:2 keeps layer 2; lu is read from layer 1 (1 to 3).
    assert [(row.split("|")[0], row.split("|")[6:9]) for row in rows] == [
        ("lm@PERMANENT", ["101", "103", "2"]),
        ("lu@PERMANENT", ["1", "3", "2"]),
    ]


def test_a_registered_layer_wins_over_the_option(tools, layers):
    row = _lines(tools, input=layers, column="value", layer=1, flags="u")[0]

    assert row.split("|")[6:8] == ["101", "103"]


def test_the_layer_must_exist(tools, layers):
    with pytest.raises(ToolError) as error:
        tools.t_vect_univar(input=layers, column="value", layer=3)

    assert "CalledModuleError" in message(error.value)
