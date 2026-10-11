"""Fixtures for the tests of grass.temporal"""

import datetime

import pytest

from grass.temporal.algebra.content import Const, MapRef
from grass.temporal.algebra.series import Extent, Series, Slot


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
    """

    def make(name, *spans, values=None, unit=None, space=None):
        slots = []
        for number, span in enumerate(spans, start=1):
            extent = _extent(span, unit)
            if values is None:
                ident = f"{name}{number}@PERMANENT"
                slots.append(Slot(extent, MapRef(ident), space, ident))
            else:
                slots.append(Slot(extent, Const(values[number - 1]), space))
        return Series(tuple(slots), sort="field" if values is None else "scalar")

    return make
