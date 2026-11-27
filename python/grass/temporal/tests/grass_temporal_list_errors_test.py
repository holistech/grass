"""Test that the listing of maps ends with a fatal error of the messenger

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal.testing.data import MapSpec, create_stds, small_region
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "lsr",
        [MapSpec("lsr1", 1, datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    tools.t_create(type="strds", output="lse", title="t", description="t")
    return tools


def _list(name, *, where=None, method="cols", output_format="plain", gran=None):
    tgis.list_maps_of_stds(
        "raster",
        name,
        None,
        None,
        where,
        "|",
        method,
        gran=gran,
        output_format=output_format,
    )


def test_an_invalid_where_condition(tools):
    with pytest.raises(FatalError, match="Invalid where condition <nonsense \\[>"):
        _list("lsr", where="nonsense [")


def test_an_empty_selection_in_a_plain_listing(tools):
    with pytest.raises(FatalError, match="Nothing found in the database"):
        _list("lse")


def test_an_empty_selection_in_a_listing_by_granule(tools):
    with pytest.raises(FatalError, match="Nothing found in the database"):
        _list("lse", method="gran", gran="1 month")


def test_a_dataset_that_does_not_exist(tools):
    with pytest.raises(FatalError, match="Space time dataset <nosuch"):
        _list("nosuch")
