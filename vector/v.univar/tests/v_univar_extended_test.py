"""Test that v.univar -e takes its order statistics from the features"""

import os
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools

# The table row with category 5 has no feature.
POINTS = "1|1|1|1\n2|2|2|2\n3|3|3|3\n4|4|4|4\n"


@pytest.fixture
def make_points(tmp_path):
    """Create a point map from the given ASCII rows and add an orphan row"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):

        def make(rows, extra_cat=None):
            tools.v_in_ascii(
                input=StringIO(rows),
                output="points",
                separator="pipe",
                columns="x double precision, y double precision, "
                "cat integer, value integer",
                format="point",
                x=1,
                y=2,
                cat=3,
                skip=0,
            )
            tools.db_execute(sql="INSERT INTO points VALUES (100, 100, 5, 100)")
            if extra_cat is not None:
                # The table has one row per category, so a second feature
                # with a category can only be added without a table row.
                tools.v_edit(
                    map="points",
                    tool="add",
                    input=StringIO(f"VERTI:\nP 1 1\n 5 5\n 1 {extra_cat}\n"),
                )
            return tools

        yield make


def test_an_orphan_table_row_is_no_value_of_the_population(make_points):
    tools = make_points(POINTS)
    stats = tools.v_univar(map="points", column="value", flags="ge").keyval

    # The features hold the values 1, 2, 3, 4. Positions (int)(n * q - 0.5):
    # q = 0.25 -> (int)0.5 = 0 -> 1; q = 0.75 -> (int)2.5 = 2 -> 3;
    # q = 0.9 -> (int)3.1 = 3 -> 4. The median of an even count is the mean of
    # the two middle values, (2 + 3) / 2 = 2.5. The orphan row (cat 5, value
    # 100) made the population 1, 2, 3, 4, 100 with the median 3.
    assert stats["n"] == 4
    assert stats["max"] == 4
    assert stats["first_quartile"] == 1
    assert stats["median"] == 2.5
    assert stats["third_quartile"] == 3
    assert stats["percentile_90"] == 4


def test_a_category_shared_by_two_features_counts_twice(make_points):
    tools = make_points(POINTS, extra_cat=4)
    stats = tools.v_univar(map="points", column="value", flags="ge").keyval

    # The features hold the values 1, 2, 3, 4, 4 (the table has one row per
    # category and returned 1, 2, 3, 4). Positions (int)(5 * q - 0.5):
    # q = 0.25 -> (int)0.75 = 0 -> 1; q = 0.75 -> (int)3.25 = 3 -> 4;
    # q = 0.9 -> (int)4.0 = 4 -> 4. The median of an odd count is the middle
    # value at position 5 / 2 = 2, that is 3.
    assert stats["n"] == 5
    assert stats["median"] == 3
    assert stats["first_quartile"] == 1
    assert stats["third_quartile"] == 4
    assert stats["percentile_90"] == 4
