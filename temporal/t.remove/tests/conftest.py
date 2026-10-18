# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fixtures for the t.remove tests

tools, prefix and make_stds come from temporal/conftest.py.
"""

import pytest

from grass.temporal.testing.readback import map_info


@pytest.fixture
def has_dataset(tools):
    """Function that tells whether a space time dataset of that name exists"""

    def check(name, stds_type="strds"):
        return name in tools.t_list(type=stds_type, columns="name").stdout.split()

    return check


@pytest.fixture
def registered(tools):
    """Function that tells for each map whether the temporal database holds it"""

    def check(maps, map_type="raster"):
        return [map_info(tools, map_type, name) is not None for name in maps]

    return check


@pytest.fixture
def existing(tools):
    """Function that tells for each map whether it exists in the mapset"""

    def check(maps, map_type="raster"):
        listed = set(tools.g_list(type=map_type).stdout.split())
        return [name in listed for name in maps]

    return check
