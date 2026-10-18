"""Test the system information of t.info: -d with and without -g, and -h

Pinned as it is today: with -d and -h together and no input the tool falls
through to the dataset lookup with an empty name.
"""

import pytest

from grass.temporal.testing.readback import message
from grass.tools import ToolError


def test_d_prints_the_backend_in_plain_text(tools):
    result = tools.t_info(flags="d")

    lines = result.stdout.splitlines()
    assert lines[0].strip().startswith("+")
    assert any("Temporal DBMI backend" in line for line in lines)
    assert any("DBMI Python interface:...... sqlite3" in line for line in lines)
    assert any("Temporal database string:" in line for line in lines)
    assert any("SQL template path:" in line for line in lines)
    assert any("tgis_db_version" in line for line in lines)


def test_d_with_g_prints_keys_and_values(tools):
    result = tools.t_info(flags="dg")

    keys = [line.split("=", 1)[0] for line in result.stdout.splitlines()]
    assert keys[:3] == ["dbmi_python_interface", "dbmi_string", "sql_template_path"]
    assert "tgis_db_version" in keys
    assert result.keyval["dbmi_python_interface"].strip("'") == "sqlite3"


def test_d_needs_no_input(tools):
    assert tools.t_info(flags="d").returncode == 0


def test_without_d_the_input_is_required(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info()

    assert "Required parameter <input> not set" in message(error.value)


def test_today_d_with_h_and_no_input_looks_for_a_dataset_without_a_name(tools):
    with pytest.raises(ToolError) as error:
        tools.t_info(flags="dh")

    assert "Dataset <@PERMANENT> of type <strds> not found" in message(error.value)
