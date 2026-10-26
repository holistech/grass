"""Test that the univariate statistics end with a fatal error, and how

The tools exit with the message. In a process that asked the framework to
raise, the same refusals are a FatalError of the messenger.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal.testing.data import (
    MapSpec,
    create_stds,
    small_region,
    vector_points,
)
from grass.tools import Tools

pytestmark = pytest.mark.usefixtures("temporal_module_session")


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    small_region(tools, 2, 3)
    create_stds(
        tools,
        "strds",
        "uvr",
        [MapSpec("uvr1", 1, datetime(2001, 1, 1), datetime(2001, 2, 1))],
    )
    vector_points(tools, "uvv1", [(1, 1)])
    tools.t_create(type="stvds", output="uvv", title="t", description="t")
    tools.t_register(type="vector", input="uvv", maps="uvv1", start="2001-01-01")
    tools.t_create(type="stvds", output="uve", title="t", description="t")
    return tools


def test_an_invalid_where_condition_of_a_raster_dataset(tools):
    with pytest.raises(FatalError, match="Invalid where condition <nonsense \\[>"):
        tgis.print_gridded_dataset_univar_statistics(
            "strds", "uvr", None, "nonsense [", False
        )


def test_an_invalid_twhere_condition_of_a_vector_dataset(tools):
    with pytest.raises(FatalError, match="Invalid twhere condition <nonsense \\[>"):
        tgis.print_vector_dataset_univar_statistics(
            "uvv", None, "nonsense [", 1, "point", "value", None, False
        )


def test_a_vector_dataset_that_does_not_exist(tools):
    with pytest.raises(FatalError, match="Space time vector dataset <nosuch@"):
        tgis.print_vector_dataset_univar_statistics(
            "nosuch", None, None, 1, "point", "value", None, False
        )


def test_a_vector_dataset_without_maps(tools):
    with pytest.raises(FatalError, match=r"Space time vector dataset <uve@.*is empty"):
        tgis.print_vector_dataset_univar_statistics(
            "uve", None, None, 1, "point", "value", None, False
        )


def test_a_column_that_does_not_exist(tools, tmp_path):
    output = tmp_path / "out.txt"

    with pytest.raises(FatalError, match=r"Error running v\.univar on <uvv1@"):
        tgis.print_vector_dataset_univar_statistics(
            "uvv", str(output), None, 1, "point", "nocolumn", None, False
        )

    # The file that was opened for the output is closed and holds the header.
    assert output.read_text().startswith("id|start|end|n|")
