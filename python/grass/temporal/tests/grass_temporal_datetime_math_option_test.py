"""Tests of option_to_datetime(), the date check of tool options

The function needs the message interface of an initialized temporal
framework, so the tests run in a session of the module.
"""

from datetime import datetime

import pytest

from grass.temporal.datetime_math import option_to_datetime

pytestmark = pytest.mark.usefixtures("temporal_module_session")


class Connection:
    """A database interface that records whether it was closed"""

    closed = False

    def close(self):
        self.closed = True


def test_a_date_is_converted_and_the_connection_stays_open():
    dbif = Connection()

    assert option_to_datetime("2001-01-03 12:00:00", "start", dbif) == datetime(
        2001, 1, 3, 12
    )
    assert not dbif.closed


def test_unreadable_text_closes_the_connection_and_ends_with_a_message(capfd):
    dbif = Connection()

    with pytest.raises(SystemExit) as error:
        option_to_datetime("garbage", "stop", dbif)

    assert error.value.code == 1
    assert dbif.closed
    assert "Invalid date <garbage> of the option <stop>" in capfd.readouterr().err
