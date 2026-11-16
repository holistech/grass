"""The boundary time values of t.rast.mapcalc, without a GRASS session

The start_time()/end_time() offsets are pure computations on the algebra core,
so they are checked here directly. The expected offsets follow the geometry of
three three-month granules from 2001-01-01, as in the tool's fixture. The
mapping of sampling methods to relations is tested with the module that holds
it, grass_temporal_related_maps_test.py.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import datetime

import pytest

from grass.temporal.algebra.series import Extent
from grass.temporal.mapcalc import _time_token_value


class _RaisingMessenger:
    """A messenger whose fatal() raises, to check the relative-time guard"""

    def fatal(self, message):
        raise RuntimeError(message)


FIRST = Extent(datetime.datetime(2001, 1, 1), datetime.datetime(2001, 4, 1))
SECOND = Extent(datetime.datetime(2001, 4, 1), datetime.datetime(2001, 7, 1))


def test_start_time_is_the_offset_from_the_first_start():
    assert _time_token_value("start_time", FIRST, FIRST, True, None) == "0.0"
    assert _time_token_value("start_time", FIRST, SECOND, True, None) == "90.0"


def test_end_time_is_the_offset_from_the_first_start():
    assert _time_token_value("end_time", FIRST, SECOND, True, None) == "181.0"


def test_end_time_of_an_instant_is_null():
    instant = Extent(datetime.datetime(2001, 1, 1))
    assert _time_token_value("end_time", FIRST, instant, True, None) == "null()"


def test_calendar_value_comes_from_timevar():
    assert _time_token_value("start_month", FIRST, SECOND, True, None) == "4"


def test_calendar_function_on_relative_time_is_fatal():
    first = Extent(0, 2, "days")
    extent = Extent(2, 4, "days")
    with pytest.raises(RuntimeError):
        _time_token_value("start_doy", first, extent, False, _RaisingMessenger())
