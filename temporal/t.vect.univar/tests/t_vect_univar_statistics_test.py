"""Test the statistics of t.vect.univar on point maps with a few values

The maps and values are listed in conftest.py. v.univar prints six significant
digits, so the numbers are compared with a relative tolerance of 1e-5. The
statistics are those of the population (divisor n), apart from the sample
variance and deviation (divisor n - 1). The coefficient of variation is the
population deviation divided by the absolute mean (not in percent), and
skewness and kurtosis use the sample deviation s (vector/v.univar/main.c):

    skewness = (sum((x - mean)^3) / n) / s^3
    kurtosis = (sum((x - mean)^4) / n) / s^4 - 3

The quartiles follow the same rule as t.rast.univar: the values are sorted and
the value at the index trunc(n * p / 100 - 0.5) is taken; the median of an
even number of values is the mean of the two middle ones.
"""

import math

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError

HEADER = [
    "id",
    "start",
    "end",
    "n",
    "nmissing",
    "nnull",
    "min",
    "max",
    "range",
    "mean",
    "mean_abs",
    "population_stddev",
    "population_variance",
    "population_coeff_variation",
    "sample_stddev",
    "sample_variance",
    "kurtosis",
    "skewness",
]
EXTENDED = ["first_quartile", "median", "third_quartile", "percentile_90"]

# up_1: 1, 2, 3, 4. The deviations from the mean 2.5 are -1.5, -0.5, 0.5, 1.5:
# squares 2.25, 0.25, 0.25, 2.25 (sum 5), fourth powers 5.0625, 0.0625, 0.0625,
# 5.0625 (sum 10.25), cubes cancel. Population variance 5 / 4, sample variance
# 5 / 3, kurtosis 10.25 / 4 / (5 / 3)^2 - 3 = 0.9225 - 3 = -2.0775.
UP_1 = {
    "n": 4, "nmissing": 0, "nnull": 0, "min": 1, "max": 4, "range": 3,
    "mean": 2.5, "mean_abs": 2.5, "population_stddev": math.sqrt(1.25),
    "population_variance": 1.25, "population_coeff_variation": math.sqrt(1.25) / 2.5,
    "sample_stddev": math.sqrt(5 / 3), "sample_variance": 5 / 3,
    "kurtosis": -2.0775, "skewness": 0,
}  # fmt: skip
# up_2: 2, 4, 6, 8 and one NULL, twice the values of up_1: the variances are
# four times as large, the coefficient of variation, kurtosis and skewness are
# the same.
UP_2 = {
    "n": 4, "nmissing": 0, "nnull": 1, "min": 2, "max": 8, "range": 6,
    "mean": 5, "mean_abs": 5, "population_stddev": math.sqrt(5),
    "population_variance": 5, "population_coeff_variation": math.sqrt(5) / 5,
    "sample_stddev": math.sqrt(20 / 3), "sample_variance": 20 / 3,
    "kurtosis": -2.0775, "skewness": 0,
}  # fmt: skip
# up_3: 10 and 20. Deviations -5 and 5: population variance 25, sample variance
# 50, kurtosis 625 / 2500 - 3 = -2.75.
UP_3 = {
    "n": 2, "nmissing": 0, "nnull": 0, "min": 10, "max": 20, "range": 10,
    "mean": 15, "mean_abs": 15, "population_stddev": 5,
    "population_variance": 25, "population_coeff_variation": 5 / 15,
    "sample_stddev": math.sqrt(50), "sample_variance": 50,
    "kurtosis": -2.75, "skewness": 0,
}  # fmt: skip
STATS = {"up_1": UP_1, "up_2": UP_2, "up_3": UP_3}
TIMES = {
    "up_1": ("2001-01-01 00:00:00", "2001-02-01 00:00:00"),
    "up_2": ("2001-02-01 00:00:00", "2001-03-01 00:00:00"),
    "up_3": ("2001-03-01 00:00:00", "2001-04-01 00:00:00"),
}


def _table(result):
    lines = result.stdout.splitlines()
    header = lines[0].split("|")
    return header, [
        dict(zip(header, line.split("|"), strict=True)) for line in lines[1:]
    ]


def _check(row, expected):
    for key, value in expected.items():
        assert float(row[key]) == pytest.approx(value, rel=1e-5, abs=1e-9), key


def test_the_header_and_the_rows_of_the_maps(tools, points):
    header, rows = _table(tools.t_vect_univar(input=points, column="value"))

    assert header == HEADER
    assert [(row["id"], row["start"], row["end"]) for row in rows] == [
        (f"{name}@PERMANENT", *TIMES[name]) for name in STATS
    ]


@pytest.mark.parametrize("name", list(STATS))
def test_the_statistics_of_a_map(tools, points, name):
    rows = _table(tools.t_vect_univar(input=points, column="value"))[1]

    row = next(row for row in rows if row["id"] == f"{name}@PERMANENT")
    _check(row, STATS[name])


def test_a_null_is_counted_as_null_and_not_as_a_value(tools, points):
    rows = _table(tools.t_vect_univar(input=points, column="value"))[1]

    # up_2 has five points and one NULL value: four values remain.
    assert (rows[1]["n"], rows[1]["nnull"]) == ("4", "1")


def test_the_e_flag_adds_the_quartiles_and_the_percentile(tools, points):
    header, rows = _table(tools.t_vect_univar(input=points, column="value", flags="e"))

    assert header == [*HEADER, *EXTENDED]
    # up_1: sorted 1, 2, 3, 4; n = 4: index trunc(1 - 0.5) = 0 gives 1, the
    # median is (2 + 3) / 2, index trunc(3 - 0.5) = 2 gives 3 and index
    # trunc(3.6 - 0.5) = 3 gives 4. up_3: sorted 10, 20; n = 2: index
    # trunc(0.5 - 0.5) = 0 gives 10, the median is 15, index trunc(1.5 - 0.5)
    # = 1 gives 20, and index trunc(1.8 - 0.5) = 1 gives 20.
    expected = {
        "up_1": [1, 2.5, 3, 4],
        "up_3": [10, 15, 20, 20],
    }
    for name, values in expected.items():
        row = next(row for row in rows if row["id"] == f"{name}@PERMANENT")
        assert [float(row[key]) for key in EXTENDED] == values, name


def test_today_a_null_counts_as_zero_in_the_extended_statistics(tools, points):
    rows = _table(tools.t_vect_univar(input=points, column="value", flags="e"))[1]

    # v.univar sorts the NULL row as the value 0 (0, 2, 4, 6, 8) but takes the
    # indexes of the four values: index 0 gives 0, the median is (2 + 4) / 2,
    # index 2 gives 4 and index 3 gives 6.
    assert [float(rows[1][key]) for key in EXTENDED] == [0, 3, 4, 6]


@pytest.mark.xfail(strict=True, reason="see OFFENE_PUNKTE")
def test_a_null_is_left_out_of_the_extended_statistics(tools, points):
    rows = _table(tools.t_vect_univar(input=points, column="value", flags="e"))[1]

    # The values 2, 4, 6, 8: index 0 gives 2, the median is (4 + 6) / 2 = 5,
    # index 2 gives 6 and index 3 gives 8.
    assert [float(rows[1][key]) for key in EXTENDED] == [2, 5, 6, 8]


def test_the_column_chooses_the_attribute(tools, points):
    rows = _table(tools.t_vect_univar(input=points, column="height"))[1]

    # height = value / 2: the measures of size halve, the variances divide
    # by four, the relative measures stay.
    expected = {
        "min": 0.5, "max": 2, "range": 1.5, "mean": 1.25,
        "population_variance": 0.3125, "sample_variance": 5 / 12,
        "population_coeff_variation": math.sqrt(1.25) / 2.5, "kurtosis": -2.0775,
    }  # fmt: skip
    _check(rows[0], expected)


def test_where_selects_the_features_of_every_map(tools, points):
    rows = _table(tools.t_vect_univar(input=points, column="value", where="value > 2"))[
        1
    ]

    # up_1: 3 and 4 remain, the two others count as missing; mean 3.5,
    # variance 0.25.
    _check(rows[0], {"n": 2, "nmissing": 2, "min": 3, "max": 4, "mean": 3.5})
    _check(rows[0], {"population_variance": 0.25})
    # up_3 (10, 20) keeps both values.
    _check(rows[2], {"n": 2, "nmissing": 0})


def test_a_where_without_a_feature_gives_a_row_without_statistics(tools, points):
    rows = _table(
        tools.t_vect_univar(input=points, column="value", where="value > 100")
    )[1]

    # All features are missing for the map; min, max and the rest stay empty.
    assert rows[2]["n"] == "0"
    assert rows[2]["nmissing"] == "2"
    assert rows[2]["min"] == ""
    assert rows[2]["skewness"] == ""


@pytest.mark.parametrize(
    ("twhere", "names"),
    [
        ("start_time >= '2001-02-01'", ["up_2", "up_3"]),
        # The times are stored with the clock, so '2001-03-01' alone would
        # sort before the end of up_2.
        ("end_time <= '2001-03-01 00:00:00'", ["up_1", "up_2"]),
        ("start_time = '2001-02-01 00:00:00'", ["up_2"]),
    ],
)
def test_twhere_selects_the_maps(tools, points, twhere, names):
    rows = _table(tools.t_vect_univar(input=points, column="value", twhere=twhere))[1]

    assert [row["id"] for row in rows] == [f"{name}@PERMANENT" for name in names]


def test_the_separator_replaces_the_bar(tools, points):
    lines = tools.t_vect_univar(
        input=points, column="value", separator=";", where="value > 2"
    ).stdout.splitlines()

    assert lines[0] == ";".join(HEADER)
    assert lines[1].startswith(
        "up_1@PERMANENT;2001-01-01 00:00:00;2001-02-01 00:00:00;2;2;0;3;4;1;3.5"
    )


def test_the_separator_can_be_a_name(tools, points):
    line = tools.t_vect_univar(
        input=points, column="value", separator="tab"
    ).stdout.splitlines()[0]

    assert line == "\t".join(HEADER)


def test_the_u_flag_leaves_out_the_header(tools, points):
    lines = tools.t_vect_univar(
        input=points, column="value", flags="u"
    ).stdout.splitlines()

    assert [line.split("|")[0] for line in lines] == [
        "up_1@PERMANENT",
        "up_2@PERMANENT",
        "up_3@PERMANENT",
    ]


def test_output_writes_the_same_text_to_a_file(tools, points, tmp_path):
    path = tmp_path / "univar.txt"
    expected = tools.t_vect_univar(input=points, column="value").stdout

    result = tools.t_vect_univar(input=points, column="value", output=str(path))

    assert result.stdout == ""
    assert path.read_text() == expected


def test_a_dash_as_output_means_the_standard_output(tools, points):
    result = tools.t_vect_univar(input=points, column="value", output="-")

    assert result.stdout.splitlines()[0] == "|".join(HEADER)


def test_an_existing_output_file_is_refused_without_overwrite(tools, points, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("keep")

    with pytest.raises(ToolError) as error:
        tools.t_vect_univar(input=points, column="value", output=str(path))

    assert "exists. To overwrite, use the --overwrite flag" in message(error.value)
    assert path.read_text() == "keep"


def test_overwrite_replaces_the_output_file(tools, points, tmp_path):
    path = tmp_path / "univar.txt"
    path.write_text("old")

    tools.t_vect_univar(input=points, column="value", output=str(path), overwrite=True)

    assert path.read_text().startswith("id|start|end")
