"""Test v.univar -e on a table with NULL values"""

import os
from io import StringIO

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def tools(tmp_path):
    """Tools in a session with the points 1 to 4 and the values 1, 2, 3, NULL"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.v_in_ascii(
            input=StringIO("1|1|1\n2|2|2\n3|3|3\n4|4|4\n"),
            output="points",
            separator="pipe",
            columns="x double precision, y double precision, value integer",
            format="point",
            x=1,
            y=2,
            cat=0,
            skip=0,
        )
        tools.db_execute(sql="UPDATE points SET value = NULL WHERE cat = 4")
        yield tools


def test_a_null_row_is_left_out_of_the_extended_statistics(tools):
    stats = tools.v_univar(map="points", column="value", flags="ge").keyval

    # The values are 1, 2 and 3. The NULL row is no value, it was counted as 0
    # before, which made the population 0, 1, 2, 3 with the median 1.5.
    # Positions (int)(3 * q - 0.5) for q = 0.25, 0.75, 0.9 are 0, 1 and 2:
    # first quartile 1, median 2 (odd count, middle value), third quartile 2
    # (position 1), 90th percentile 3 (position 2).
    assert stats["n"] == 3
    assert stats["nnull"] == 1
    assert stats["first_quartile"] == 1
    assert stats["median"] == 2
    assert stats["third_quartile"] == 2
    assert stats["percentile_90"] == 3
