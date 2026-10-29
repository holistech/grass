# SPDX-License-Identifier: GPL-2.0-or-later

"""The interface of every temporal tool loads no temporal library code

``--help`` and ``--interface-description`` have to answer without importing
``grass.temporal``: the library pulls in ``sqlite3``, ``numpy`` and the C
libraries, which costs start-up time on every call of ``g.parser`` and of the
GUI that builds its dialogs from the interface description. A tool that
imports the library at module level or before ``gs.parser()`` runs fails here.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from grass.temporal.testing.session import project_session

TOOLS_DIR = Path(__file__).resolve().parents[4] / "temporal"
TOOLS = sorted(path.stem for path in TOOLS_DIR.glob("t.*/t.*.py"))


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    with project_session(tmp_path_factory.mktemp("imports") / "project") as session:
        yield session


def test_tool_list_is_complete():
    assert len(TOOLS) == 50


@pytest.mark.parametrize("tool", TOOLS)
def test_help_does_not_load_the_temporal_library(session, tool):
    # The installed copy is what users run; the tests of the tools load it too.
    script = Path(session.env["GISBASE"]) / "scripts" / tool
    result = subprocess.run(
        [sys.executable, "-X", "importtime", str(script), "--interface-description"],
        env=session.env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "<?xml" in result.stdout
    loaded = [
        line.rsplit("|", 1)[1].strip()
        for line in result.stderr.splitlines()
        if line.startswith("import time:") and "|" in line
    ]
    assert not [name for name in loaded if name.startswith("grass.temporal")]
