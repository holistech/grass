"""Test that t.rast.univar closes its output file when the run stops

A file object that is garbage collected unclosed raises a ResourceWarning.
Python only shows it in development mode, so the tool runs with
PYTHONDEVMODE=1 and the warning is turned into an error, which puts it in
stderr whatever happens after.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError, Tools


def test_output_file_closed_on_fatal(tools, values, broken_tools, tmp_path):
    # A stand-in r.univar that fails is the way to stop the run after the
    # output file was opened: the input is checked before the file is opened.
    failing = broken_tools("r.univar")
    env = dict(failing._original_env)  # noqa: SLF001
    env["PYTHONDEVMODE"] = "1"
    env["PYTHONWARNINGS"] = "error::ResourceWarning"
    dev_tools = Tools(env=env, consistent_return_value=True, capture_stderr=True)
    output = tmp_path / "stats.txt"

    with pytest.raises(ToolError) as error:
        dev_tools.t_rast_univar(input=values, output=str(output), overwrite=True)

    # A run that stopped before it opened the file would pass the checks
    # below without testing anything; the file exists once it was opened.
    assert output.exists()
    text = message(error.value)
    assert "ResourceWarning" not in text
    assert "unclosed file" not in text
