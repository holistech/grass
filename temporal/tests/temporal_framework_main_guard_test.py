# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Keep the examples of the temporal framework documentation spawn-safe

On macOS and Windows a child process starts with the method "spawn": it imports
the main module again. An example that calls ``tgis.init()`` or a tool at module
level then runs that code once more in every child that the library starts, and
fails (a GitHub macOS runner showed this on 26.11.2026 with 33 failed tests of
the design document and the guides). A user who copies such an example meets the
same error. The rule for every example is therefore: the module level holds
imports, definitions and constants; whatever runs lives in a function that
``if __name__ == "__main__":`` calls.

The examples are the files of the design document, the Python blocks of the
overview page and the Python files of the guides. The blocks are read with the
readers of the page tests, so a new form of block is seen here as there.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLES = REPOSITORY / "python/grass/docs/src/temporal_framework_design/examples"

# Calls that may stand at module level because they build a plain value and
# neither start a process nor read the session: the constant STEP of an example
# is a timedelta. Any other call, above all those of grass.temporal,
# grass.script and grass.tools, belongs in a function.
VALUE_CONSTRUCTORS = {"timedelta"}


def load_page_test():
    """The module of the page tests, whose readers this test reuses

    pytest imports the tests with ``--import-mode=importlib``, so a sibling
    module is not importable by name.
    """
    path = Path(__file__).with_name("temporal_framework_page_test.py")
    spec = importlib.util.spec_from_file_location("temporal_framework_page_test", path)
    module = importlib.util.module_from_spec(spec)
    # dataclasses looks its module up by name while the module executes.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PAGE_TEST = load_page_test()


def is_main_guard(node):
    """Whether node is ``if __name__ == "__main__":``"""
    if not isinstance(node, ast.If):
        return False
    test = node.test
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and [getattr(c, "value", None) for c in test.comparators] == ["__main__"]
    )


def callee_name(call):
    """The last name of what a call calls: ``a.b.c()`` gives ``c``"""
    function = call.func
    if isinstance(function, ast.Attribute):
        return function.attr
    if isinstance(function, ast.Name):
        return function.id
    return ast.dump(function)


def module_level_calls(source):
    """The calls of a source that run when the file is imported, as text

    Function and class bodies and the body of the main guard do not count.
    Decorators, default values and base classes do run at import, so they are
    searched too.
    """
    found = []
    for node in ast.parse(source).body:
        if is_main_guard(node):
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            runs = [*node.decorator_list]
            if isinstance(node, ast.ClassDef):
                runs += node.bases
            else:
                runs += [*node.args.defaults, *node.args.kw_defaults]
            parts = [part for part in runs if part is not None]
        else:
            parts = [node]
        for part in parts:
            found += [
                ast.unparse(call)
                for call in ast.walk(part)
                if isinstance(call, ast.Call)
                and callee_name(call) not in VALUE_CONSTRUCTORS
            ]
    return found


def documented_sources():
    """Every documented example as (id, source)"""
    sources = [
        (f"examples/{path.name}", path.read_text())
        for path in sorted(EXAMPLES.glob("*.py"))
    ]
    for title, source in PAGE_TEST.code_blocks():
        sources.append((f"overview: {title}", source))
    for page in PAGE_TEST.PAGES[1:]:
        for block in PAGE_TEST.blocks_of(page):
            if block.kind in {"snippet", "tool-file"}:
                name = block.caption or block.title
                sources.append((f"{page.name}: {name}", block.body))
    return sources


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("import os\nX = 1\n", []),
        ("def f():\n    g()\n", []),
        ("def f():\n    g()\n\n\nif __name__ == '__main__':\n    f()\n", []),
        ("STEP = timedelta(minutes=5)\n", []),
        ("tgis.init()\n", ["tgis.init()"]),
        ("tools = Tools()\n", ["Tools()"]),
        ("def f(x=h()):\n    pass\n", ["h()"]),
        ("@deco()\ndef f():\n    pass\n", ["deco()"]),
        ("if True:\n    run()\n", ["run()"]),
    ],
)
def test_the_reader_sees_calls_that_run_at_import(source, expected):
    """The checker flags calls at import and ignores those behind the guard"""
    assert module_level_calls(source) == expected


def test_there_are_examples_to_check():
    sources = documented_sources()
    assert len([s for s in sources if s[0].startswith("examples/")]) == 8
    assert len(sources) >= 8 + 5


@pytest.mark.parametrize(
    ("name", "source"),
    [pytest.param(name, source, id=name) for name, source in documented_sources()],
)
def test_examples_run_nothing_at_import(name, source):
    """A child process that imports the example again runs none of its work"""
    assert module_level_calls(source) == [], f"{name} runs code at module level"
