"""Test that t.rename refuses a PostgreSQL temporal database

Renaming rewrites the names of the register tables with SQL that only the
SQLite backend knows, so the library stops before it writes. The test needs
the PostgreSQL server of GRASS_TEMPORAL_TEST_POSTGRESQL and is skipped without.
"""

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import project_session
from grass.tools import ToolError, Tools


@pytest.mark.postgresql
def test_postgresql_is_refused(tmp_path, postgresql_database):
    with project_session(tmp_path / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.t_connect(driver="pg", database=postgresql_database)
        tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            tools, "strds", "series", [MapSpec("map1", 1, day(0), day(1))], title="T"
        )
        before = inventory(tools)

        with pytest.raises(ToolError) as error:
            tools.t_rename(input="series", output="renamed")

        assert (
            "Renaming of space time datasets is not supported for PostgreSQL"
            in message(error.value)
        )
        # The dataset keeps its name and its map.
        assert inventory(tools) == before
        assert [row.name for row in list_maps(tools, "strds", "series")] == ["map1"]
