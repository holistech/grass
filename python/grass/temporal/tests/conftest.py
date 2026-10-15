"""Fixtures for the tests of grass.temporal"""

import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.content import Const, MapRef
from grass.temporal.algebra.series import Extent, Series, Slot
from grass.temporal.testing.session import project_session, temporal_session


def _extent(span, unit):
    start, end = span if isinstance(span, tuple) else (span, None)
    if unit is not None:
        return Extent(start, end, unit)
    return Extent(
        datetime.datetime(2001, 1, start),
        None if end is None else datetime.datetime(2001, 1, end),
    )


@pytest.fixture
def make_series():
    """Return a function that builds a series in memory

    make_series("a", (1, 2), (2, 3)) has the maps a1@PERMANENT and
    a2@PERMANENT with the intervals [1, 2] and [2, 3] of January 2001; a
    number alone is an instant. With values the series is scalar and holds
    these values instead of maps. With a unit the numbers are relative time.
    kind is the map type of the series.
    """

    def make(name, *spans, values=None, unit=None, space=None, kind="raster"):
        slots = []
        for number, span in enumerate(spans, start=1):
            extent = _extent(span, unit)
            if values is None:
                ident = f"{name}{number}@PERMANENT"
                slots.append(Slot(extent, MapRef(ident), space, ident))
            else:
                slots.append(Slot(extent, Const(values[number - 1]), space))
        return Series(
            tuple(slots), kind=kind, sort="field" if values is None else "scalar"
        )

    return make


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
def temporal_exit_session(temporal_module_session):
    """Like temporal_module_session, but a fatal error ends the process

    For tests that check the abort of the classic algebra with
    pytest.raises(SystemExit), the way the tools fail. temporal_session
    makes fatal errors raise FatalError instead and restores the mode of
    before when the module ends.
    """
    tgis.set_raise_on_error(False)
    return temporal_module_session


@pytest.fixture(scope="module")
def xy_module_session(tmp_path_factory):
    """Session in an XY project for a whole module, without touching os.environ

    For tests that run tools only; pass env=session.env or Tools(session=...).
    Use temporal_module_session when the test calls grass.temporal itself.
    """
    with project_session(tmp_path_factory.mktemp("temporal") / "project") as session:
        yield session
