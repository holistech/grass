"""Fixtures for the tests of grass.temporal"""

import pytest

# pytest rewrites the assert statements of test modules and conftest.py only. The
# helpers of grass.temporal.testing compare with a plain assert, which on failure
# shows no values unless the package is registered before its first import.
pytest.register_assert_rewrite("grass.temporal.testing")
# The registration has to precede these imports, so they follow a statement.

# core held it before the database layer; the fallback goes with the algebra core.
try:
    from grass.temporal.state import set_raise_on_error  # noqa: E402
except ImportError:
    from grass.temporal.core import set_raise_on_error  # noqa: E402
from grass.temporal.testing import io_cache  # noqa: E402
from grass.temporal.testing import postgresql  # noqa: E402
from grass.temporal.testing.session import temporal_session  # noqa: E402


@pytest.fixture(scope="module")
def temporal_module_session(tmp_path_factory):
    """Session in an XY project for a whole module, with grass.temporal usable

    The session environment is mirrored into os.environ for the module, see
    grass.temporal.testing.session.temporal_session. Each test module
    gets its own session, also when several directories run together.
    """
    with temporal_session(tmp_path_factory.mktemp("temporal") / "project") as session:
        yield session


@pytest.fixture(scope="module")
def temporal_exit_session(temporal_module_session):
    """Like temporal_module_session, but a fatal error ends the process

    For tests that check the abort of a tool with pytest.raises(SystemExit),
    the way the tools fail. temporal_session
    makes fatal errors raise FatalError instead and restores the mode of
    before when the module ends. The session is shared, so a module that
    requests this fixture must not also rely on raising errors in the tests
    of temporal_module_session: once requested, the exit mode stays on for
    the rest of the module.
    """
    set_raise_on_error(False)
    return temporal_module_session


@pytest.fixture(scope="module")
def io_cache_storage():
    """Answers of the test-only caches, shared by the tests of one module"""
    return io_cache.CacheStorage()


@pytest.fixture(autouse=True)
def cached_io(request, io_cache_storage):
    """Run the test with the caches of grass.temporal.testing.io_cache.cached_io"""
    if request.node.get_closest_marker("real_io"):
        yield
        return
    with io_cache.cached_io(io_cache_storage):
        yield


@pytest.fixture
def postgresql_database():
    """Yield the connection string of a new, empty database on the test server

    Skips without GRASS_TEMPORAL_TEST_POSTGRESQL or when the server does not
    answer. The database is dropped after the test.
    """
    postgresql.server_or_skip()
    with postgresql.fresh_database("t") as dbstring:
        yield dbstring
