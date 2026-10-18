"""Test which flags of t.info need an input, and -d together with -h

-d with and without -g is tested in t_info_backend_test.py. Pinned as it is
today: with -d and -h together and no input the tool skips the report of -d
and falls through to the dataset lookup with an empty name.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def test_without_d_the_input_is_required(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info()

    assert "Required parameter <input> not set" in message(error.value)


def test_today_d_with_h_and_no_input_looks_for_a_dataset_without_a_name(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info(flags="dh")

    assert "Dataset <@PERMANENT> of type <strds> not found" in message(error.value)
