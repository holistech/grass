"""Fixtures shared by the tests of the temporal tools

python/grass/temporal/tests is not below this directory, so the session
fixtures are defined in its conftest.py as well; the logic lives in
grass.temporal.testing.
A conftest.py in a tests directory that defines a fixture of the same name
takes precedence over the one here.
"""

import re
import zlib

import pytest

from grass.temporal.testing.data import create_daily_stds
from grass.temporal.testing.session import project_session, temporal_session
from grass.tools import Tools


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


@pytest.fixture(scope="module")
def tools(tmp_path_factory):
    """Tools in an XY project of its own for a whole module

    The 2D and the 3D region are one cell, so a constant map is cheap.
    Messages of a successful run are kept in result.stderr, because the
    warnings and the reports of the tools are part of their behaviour. A
    directory whose tests need another project defines its own tools.
    """
    with project_session(tmp_path_factory.mktemp("tools") / "project") as session:
        tools = Tools(
            session=session, consistent_return_value=True, capture_stderr=True
        )
        tools.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
        yield tools


@pytest.fixture
def prefix(request):
    """A name prefix that is unique for the test within its module

    The tests of a module share the project of tools, so each names its maps
    and datasets with this prefix: the test name, shortened, and a checksum of
    the full name, which tells the parameters of a test apart.
    """
    node = re.sub(r"\W+", "_", request.node.name).strip("_").lower()
    return f"{node[:24]}_{zlib.crc32(request.node.name.encode()) % 100000}"


@pytest.fixture
def make_stds(tools, prefix):
    """Function that creates maps and datasets that hold all of them

    make(count) creates the maps <prefix>_1 to <prefix>_<count> of the kind
    that stds_type holds, where map n holds the value n and lasts one day
    from day n-1 to day n, and the datasets <prefix>_ds0, <prefix>_ds1, ...
    that each register all of them. Returns the map names and the dataset
    names.
    """

    def make(count, *, stds_type="strds", datasets=1):
        names = [f"{prefix}_ds{index}" for index in range(datasets)]
        maps = create_daily_stds(tools, stds_type, names, count, map_prefix=prefix)
        return maps, names

    return make
