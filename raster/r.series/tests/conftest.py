import os

import pytest

import grass.script as gs
from grass.tools import Tools


@pytest.fixture
def xy_session(tmp_path):
    """Active session in an XY location with a region of one cell (scope: function)"""
    project = tmp_path / "xy_test"
    gs.create_project(project)
    with (
        gs.setup.init(project, env=os.environ.copy()) as session,
        Tools(session=session, consistent_return_value=True) as tools,
    ):
        tools.g_region(s=0, n=1, w=0, e=1, res=1)
        yield tools
