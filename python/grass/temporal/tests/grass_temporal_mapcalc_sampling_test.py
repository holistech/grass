"""The method-to-relation mapping and the boundary time values of
t.rast.mapcalc, without a GRASS session

The relation mapping and the start_time()/end_time() offsets are pure
computations on the algebra core, so they are checked here directly. The
expected offsets follow the geometry of three three-month granules from
2001-01-01, as in the tool's fixture.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import datetime

import pytest

from grass.temporal.algebra.relations import (
    contains,
    during,
    equal,
    overlapped,
    overlaps,
)
from grass.temporal.algebra.series import Extent
from grass.temporal.mapcalc import _method_relation, _time_token_value


class _RaisingMessenger:
    """A messenger whose fatal() raises, to check the relative-time guard"""

    def fatal(self, message):
        raise RuntimeError(message)


def test_method_names_map_to_relations_without_inverse():
    assert _method_relation(["equal"]) == equal
    assert _method_relation(["during"]) == during
    assert _method_relation(["contain"]) == contains
    assert _method_relation(["overlap"]) == overlaps | overlapped
    assert _method_relation(["equal", "during"]) == equal | during


def test_start_method_omits_equal():
    """The 'start' union leaves equal out, so the method never matches a map of
    equal time, as sample_by_dataset() does not (its EQUALS key is never filed)"""
    rel = _method_relation(["start"])
    assert rel.temporal == {"overlapped", "starts", "started", "finishes", "contains"}
    assert "equal" not in rel.temporal


def test_unknown_method_is_an_error():
    with pytest.raises(ValueError, match="nonsense"):
        _method_relation(["nonsense"])


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
