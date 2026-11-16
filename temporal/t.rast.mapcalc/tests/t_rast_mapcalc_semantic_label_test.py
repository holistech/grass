"""Test t.rast.mapcalc with semantic labels in the names of the inputs.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.tools import Tools


@pytest.fixture(scope="module")
def label_session(xy_module_session):
    """STRDS "test" with one S2_8 and one S2_4 map in each of two months."""
    tools = Tools(session=xy_module_session, overwrite=True)
    tools.g_region(s=0, n=80, w=0, e=120, res=10)
    jan, feb = datetime(2001, 1, 1), datetime(2001, 2, 1)
    create_stds(
        tools,
        "strds",
        "test",
        [
            MapSpec("b8_1", 8, jan, semantic_label="S2_8"),
            MapSpec("b4_1", 4, jan, semantic_label="S2_4"),
            MapSpec("b8_2", 16, feb, semantic_label="S2_8"),
            MapSpec("b4_2", 2, feb, semantic_label="S2_4"),
        ],
        title="A test",
    )
    return xy_module_session


def test_inputs_with_semantic_labels(label_session):
    """The inputs of the manual example (test.S2_8 and test.S2_4) are found."""
    tools = Tools(session=label_session, overwrite=True)
    tools.t_rast_mapcalc(
        inputs="test.S2_8,test.S2_4",
        output="ratio",
        basename="ratio",
        expression="float(test.S2_8) / test.S2_4",
    )
    names = tools.t_rast_list(input="ratio", columns="name", flags="u").text.split()
    assert len(names) == 2
    values = sorted(
        float(tools.r_univar(map=name, flags="g").keyval["mean"]) for name in names
    )
    assert values == [2.0, 8.0]
