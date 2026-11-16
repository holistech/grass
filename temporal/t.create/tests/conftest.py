"""Fixtures for the t.create tests

SPDX-License-Identifier: GPL-2.0-or-later
"""

import pytest

from grass.temporal.testing.session import add_mapset, project_session
from grass.tools import Tools

MAPSET = "work"


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in a project whose current mapset is "work", next to "other"

    A mapset other than PERMANENT lets the tests tell the current mapset from
    the one every project has. Messages of a successful run are kept in
    result.stderr, because the warnings of t.create are part of its behaviour.
    """
    with project_session(
        tmp_path_factory.mktemp("t_create") / "project", mapset=MAPSET
    ) as session:
        add_mapset(session, "other")
        yield Tools(session=session, consistent_return_value=True, capture_stderr=True)
