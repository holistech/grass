# SPDX-License-Identifier: GPL-2.0-or-later

"""Pin the message ids that translations of the library are keyed on

A translator works on the text inside ``_()``, and a changed text loses the
translation. The golden file lists every message id that the library and the
tools under ``temporal/`` had before the clean-up and still have: whole
sentences, one per map type and per form with or without a layer, rather than
one sentence with an English word inserted. Seven ids are not in the list on
purpose: those of code that was deleted (the aggregation by topology, the
volume computation, the export of 3D rasters), the one that was renamed to the
``str.format`` convention (``Aggregating {} raster maps``) and the one whose
text carried the indentation of the source. The ids were extracted on 26.10.2026 from the tree before the clean-up
(commit b8f890df1c) by parsing every ``_("...")`` literal.
"""

import ast
import json
from pathlib import Path

LIBRARY = Path(__file__).resolve().parents[1]
TOOLS = LIBRARY.parents[2] / "temporal"
GOLDEN = json.loads(LIBRARY.joinpath("tests/data/message_ids.json").read_text())


def _message_ids():
    paths = [
        path
        for path in LIBRARY.rglob("*.py")
        if "tests" not in path.parts and "testing" not in path.parts
    ]
    paths += TOOLS.glob("*/*.py")
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


def test_the_message_ids_of_the_translations_still_exist():
    missing = sorted(set(GOLDEN) - _message_ids())
    assert not missing, "message ids lost:\n" + "\n".join(missing)
