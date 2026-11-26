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


def installed_script(gisbase, tool):
    """Return the path of the installed script of tool below gisbase

    The installation names it after the tool, on Windows with .py appended.
    """
    scripts = Path(gisbase) / "scripts"
    for path in (scripts / tool, scripts / f"{tool}.py"):
        if path.exists():
            return path
    msg = f"No installed script of {tool} in {scripts}"
    raise FileNotFoundError(msg)


@pytest.mark.parametrize("tool", TOOLS)
def test_help_does_not_load_the_temporal_library(session, tool):
    # The installed copy is what users run; the tests of the tools load it too.
    script = installed_script(session.env["GISBASE"], tool)
    result = subprocess.run(
        [sys.executable, "-X", "importtime", str(script), "--interface-description"],
        env=session.env,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stderr.splitlines()
    imports = [line for line in lines if line.startswith("import time:")]
    # -X importtime fills stderr with its table; the message of a failure is in
    # the other lines.
    others = "\n".join(line for line in lines if not line.startswith("import time:"))
    assert result.returncode == 0, others[-2000:]
    assert "<?xml" in result.stdout
    loaded = [line.rsplit("|", 1)[1].strip() for line in imports if "|" in line]
    assert not [name for name in loaded if name.startswith("grass.temporal")]


def test_installed_script_is_found_with_and_without_py(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "t.a").write_text("")
    (scripts / "t.b.py").write_text("")
    assert installed_script(tmp_path, "t.a") == scripts / "t.a"
    assert installed_script(tmp_path, "t.b") == scripts / "t.b.py"
    with pytest.raises(FileNotFoundError, match=r"t\.c"):
        installed_script(tmp_path, "t.c")
