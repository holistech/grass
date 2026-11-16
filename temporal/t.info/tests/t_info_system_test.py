"""Test which flags of t.info need an input, and -d together with -h

-d with and without -g is tested in t_info_backend_test.py. With -d and -h
together the history of a dataset is asked for, so an input is required.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError, Tools


def test_without_d_the_input_is_required(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info()

    assert "Required parameter <input> not set" in message(error.value)


def test_d_with_h_and_no_input_asks_for_the_input(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info(flags="dh")

    assert "Please specify input=" in message(error.value)


def test_d_with_h_and_an_input_prints_the_history(tools, temporal_data):
    tools = Tools(session=temporal_data.session)

    text = tools.t_info(type="strds", input="precip_abs1", flags="dh").text

    # The history, not the report of -d.
    assert "# Command history:" in text
    assert "Temporal DBMI backend information" not in text
