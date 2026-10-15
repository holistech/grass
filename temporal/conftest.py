"""Fixtures shared by the tests of the temporal tools

python/grass/temporal/tests is not below this directory, so the fixtures are
defined in its conftest.py as well; the logic lives in grass.temporal.testing.
A conftest.py in a tests directory that defines a fixture of the same name
takes precedence over the one here.
"""

import pytest

from grass.temporal.testing.session import project_session, temporal_session


@pytest.fixture(params=("core", "classic"))
def algebra_setting(request):
    """Name of the algebra a test runs on, "core" or "classic"

    Not autouse, so a directory chooses whether it runs on both algebras. One
    that does writes an autouse fixture which requests this one and sets the
    name in the session the tools use:
    `session.env[ALGEBRA_VARIABLE] = algebra_setting`, with ALGEBRA_VARIABLE
    from grass.temporal.algebra.parser.switch.
    """
    return request.param


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
def xy_module_session(tmp_path_factory):
    """Session in an XY project for a whole module, without touching os.environ

    For tests that run tools only; pass env=session.env or Tools(session=...).
    Use temporal_module_session when the test calls grass.temporal itself.
    """
    with project_session(tmp_path_factory.mktemp("temporal") / "project") as session:
        yield session
