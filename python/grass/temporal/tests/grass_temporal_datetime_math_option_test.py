"""Tests of option_to_datetime(), the date check of tool options

The function needs the message interface of an initialized temporal
framework, so the tests run in a session of the module.
"""

from datetime import datetime

import pytest

from grass.temporal import datetime_math
from grass.temporal.datetime_math import option_to_datetime

pytestmark = pytest.mark.usefixtures("temporal_module_session")


def test_a_date_is_converted():
    assert option_to_datetime("2001-01-03 12:00:00", "start") == datetime(
        2001, 1, 3, 12
    )


def test_unreadable_text_raises_with_the_message_of_the_tools():
    with pytest.raises(
        ValueError, match=r"^Invalid date <garbage> of the option <stop>$"
    ):
        option_to_datetime("garbage", "stop")


def test_unreadable_text_raises_without_a_message_interface(monkeypatch):
    # Without a message interface string_to_datetime() ends in an
    # AttributeError when it reports the text; the message stays the same.
    monkeypatch.setattr(datetime_math, "get_tgis_message_interface", lambda: None)
    with pytest.raises(AttributeError):
        datetime_math.string_to_datetime("garbage")

    with pytest.raises(
        ValueError, match=r"^Invalid date <garbage> of the option <start>$"
    ):
        option_to_datetime("garbage", "start")
