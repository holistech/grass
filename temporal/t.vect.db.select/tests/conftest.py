"""Datasets for the tests of t.vect.db.select

Every map has points at x = k and y = 1, 2, 3 (cat 1 to 3 in the order of
the points); the tables have the columns x, y and cat in front of the
attributes.

- dbs_int has three monthly maps di_1 to di_3 (March to May 2001) with the
  columns observation (100 k for map k, in all three rows) and label (a, b, c),
- dbs_inst has three instants dn_1 to dn_3 (2004-01-01, 2004-04-01 and
  2004-07-01) with the column observation (100 k),
- dbs_chg has dc_1 (January 2001; two points at (1, 1) and (2, 2); columns a =
  1, 2 and b = x, y) and dc_2 (February 2001; one point at (1, 1); a = 5 and c =
  2.5), whose tables differ,
- dbs_nest has dx_1 (January to July 2001) and dx_2 (February to March 2001),
  one point each, whose start order differs from the end order,
- dbs_lay has the map dl with two layers (a = 1, 2 in layer 1 and 101, 102 in
  layer 2) registered as dl:2 in January 2001, and the map du with the same
  tables registered without a layer in February 2001.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, register_stds, vector_points


@pytest.fixture(scope="module")
def intervals(tools):
    """The dataset dbs_int described above; returns its name"""
    for k in (1, 2, 3):
        vector_points(
            tools,
            f"di_{k}",
            [(k, 1), (k, 2), (k, 3)],
            attributes={"observation": [100 * k] * 3, "label": ["a", "b", "c"]},
        )
    register_stds(
        tools,
        "stvds",
        "dbs_int",
        [
            MapSpec(f"di_{k}", None, datetime(2001, k + 2, 1), datetime(2001, k + 3, 1))
            for k in (1, 2, 3)
        ],
    )
    return "dbs_int"


@pytest.fixture(scope="module")
def instants(tools):
    """The dataset dbs_inst described above; returns its name"""
    for k in (1, 2, 3):
        vector_points(
            tools,
            f"dn_{k}",
            [(k, 1), (k, 2), (k, 3)],
            attributes={"observation": [100 * k] * 3},
        )
    register_stds(
        tools,
        "stvds",
        "dbs_inst",
        [MapSpec(f"dn_{k}", None, datetime(2004, 3 * k - 2, 1)) for k in (1, 2, 3)],
    )
    return "dbs_inst"


@pytest.fixture(scope="module")
def changing(tools):
    """The dataset dbs_chg described above; returns its name"""
    vector_points(
        tools, "dc_1", [(1, 1), (2, 2)], attributes={"a": [1, 2], "b": ["x", "y"]}
    )
    vector_points(tools, "dc_2", [(1, 1)], attributes={"a": [5], "c": [2.5]})
    register_stds(
        tools,
        "stvds",
        "dbs_chg",
        [
            MapSpec("dc_1", None, datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("dc_2", None, datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    return "dbs_chg"


@pytest.fixture(scope="module")
def layers(tools):
    """The dataset dbs_lay described above; returns its name"""
    for name in ("dl", "du"):
        vector_points(
            tools, name, [(1, 1), (2, 2)], attributes={"a": [1, 2]}, layers=(1, 2)
        )
        tools.db_execute(sql=f"UPDATE {name}_2 SET a = a + 100")
    register_stds(
        tools,
        "stvds",
        "dbs_lay",
        [
            MapSpec("dl:2", None, datetime(2001, 1, 1), datetime(2001, 2, 1)),
            MapSpec("du", None, datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    return "dbs_lay"


@pytest.fixture(scope="module")
def nested(tools):
    """The dataset dbs_nest described above; returns its name"""
    for k in (1, 2):
        vector_points(tools, f"dx_{k}", [(k, 1)], attributes={"a": [k]})
    register_stds(
        tools,
        "stvds",
        "dbs_nest",
        [
            MapSpec("dx_1", None, datetime(2001, 1, 1), datetime(2001, 7, 1)),
            MapSpec("dx_2", None, datetime(2001, 2, 1), datetime(2001, 3, 1)),
        ],
    )
    return "dbs_nest"
