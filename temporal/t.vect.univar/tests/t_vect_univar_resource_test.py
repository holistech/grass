"""Test that t.vect.univar closes its output file when the run stops

A file object that is garbage collected unclosed raises a ResourceWarning.
Python only shows it in development mode, so the tool runs with
PYTHONDEVMODE=1 and the warning is turned into an error, which puts it in
stderr whatever happens after.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError, Tools


def test_output_file_closed_on_fatal(tools, points, tmp_path):
    env = dict(tools._original_env)  # noqa: SLF001
    env["PYTHONDEVMODE"] = "1"
    env["PYTHONWARNINGS"] = "error::ResourceWarning"
    dev_tools = Tools(env=env, consistent_return_value=True, capture_stderr=True)

    # The output file is opened before the dataset is looked up, so an unknown
    # input stops the run with the file open.
    with pytest.raises(ToolError) as error:
        dev_tools.t_vect_univar(
            input="uv_missing", column="value", output=str(tmp_path / "stats.txt")
        )

    text = message(error.value)
    assert "not found" in text
    assert "ResourceWarning" not in text
    assert "unclosed file" not in text
