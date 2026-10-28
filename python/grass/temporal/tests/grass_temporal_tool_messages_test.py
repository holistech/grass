# SPDX-License-Identifier: GPL-2.0-or-later

"""Pin the translatable message texts of the temporal tools

A translator works on the text inside ``_()``, and a changed text loses the
translation. ``data/tool_message_texts.json`` lists every text that stands as
the first argument of a call ``_("...")`` in the tool scripts
``temporal/t.*/t.*.py`` or in the top level library modules. The record
started as the texts of the tool scripts; some of them moved into library
modules together with the steps the tools share, and are still pinned there.
A change that has to alter a text
changes the record in the same commit and says so in the commit message.

The texts come from parsing the source tree this file lives in, not an
installed copy. To record the current texts again, run this file as a script. It keeps the
recorded texts that are still present, so texts that moved into the library
survive::

    python3 grass_temporal_tool_messages_test.py
"""

import ast
import json
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]
TOOLS = LIBRARY.parents[2] / "temporal"
RECORD = LIBRARY / "tests" / "data" / "tool_message_texts.json"


def _texts(paths):
    """Return the texts of all ``_("...")`` calls in the given source files"""
    found = set()
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "_"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.add(node.args[0].value)
    return found


def _tool_scripts():
    return sorted(TOOLS.glob("t.*/t.*.py"))


def _present_texts():
    """Texts of the tool scripts and of the top level library modules"""
    return _texts(_tool_scripts() + sorted(LIBRARY.glob("*.py")))


def test_every_recorded_tool_message_is_still_there():
    recorded = json.loads(RECORD.read_text(encoding="utf-8"))
    missing = sorted(set(recorded) - _present_texts())
    assert not missing, "message texts lost:\n" + "\n".join(missing)


if __name__ == "__main__":
    old = (
        set(json.loads(RECORD.read_text(encoding="utf-8")))
        if RECORD.exists()
        else set()
    )
    RECORD.write_text(
        json.dumps(
            sorted(_texts(_tool_scripts()) | (old & _present_texts())),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
