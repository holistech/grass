# SPDX-FileCopyrightText: 2026 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fixture for t.register tests"""

import pytest

from grass.temporal.testing.data import make_map
from grass.temporal.testing.session import project_session
from grass.tools import Tools


@pytest.fixture
def session_with_rasters(tmp_path):
    """Start a session in a new project and create small test rasters."""
    with project_session(tmp_path / "test") as session:
        tools = Tools(session=session)
        tools.g_region(s=0, n=1, w=0, e=1, res=1)
        for name in ("a", "b", "c"):
            make_map(tools, "raster", name, 1)
        yield session
