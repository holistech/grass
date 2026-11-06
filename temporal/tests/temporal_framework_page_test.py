# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check the overview page of the temporal framework against the code

The page python/grass/docs/src/temporal_framework.rst describes every module
of grass.temporal and shows Python examples. These tests keep it true:

- each code block of the page runs in a throwaway XY project and ends without
  a traceback;
- each code block calls only what the public contract of grass.temporal lists
  (grass.temporal.testing.contract_trace), so a change of the contract that
  breaks an example fails here;
- every module and package of the library has a :mod: role on the page, so a
  new module cannot stay undescribed.

The page is not built with Sphinx here: the documentation workflow builds it,
and a build needs packages that the tests do not.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import grass.script as gs
from grass.temporal.testing.contract_trace import called_names, missing_from_contract
from grass.temporal.testing.manual_examples import example_environment
from grass.temporal.testing.session import project_session

REPOSITORY = Path(__file__).resolve().parents[2]
PAGE = REPOSITORY / "python/grass/docs/src/temporal_framework.rst"
LIBRARY = REPOSITORY / "python/grass/temporal"
# Passed explicitly: the default of missing_from_contract() searches from the
# working directory, which may lie in another checkout.
CONTRACT = REPOSITORY / "python/grass/temporal/tests/data/public_contract.json"

# ply is an embedded copy of the PLY parser generator that the page names but
# does not document; the tests of the library are not part of its interface.
# A name with a leading underscore is private and not in the reference.
LEFT_OUT = {"ply", "tests"}

# The name of a heading underline of reStructuredText: one repeated character.
UNDERLINE = re.compile(r"^([=\-^\"~])\1{3,}\s*$")

# The datasets that the examples of the page read, as the page says: the
# example that creates a dataset must find none, the others find these.
DATASETS = ("test", "A", "B")
MAPS_PER_DATASET = 3
CREATES_ITS_DATASET = "Creation of a space time dataset"


def code_blocks():
    """The code blocks of the page as (title, source) pairs, in page order"""
    return parse_code_blocks(PAGE.read_text().splitlines())


# The directives that show or run code, a line ending in two colons (alone or
# behind a paragraph), which starts a literal block, and a doctest block, which
# needs no directive.
CODE_DIRECTIVE = re.compile(
    r"^\.\.\s+(code-block|code|sourcecode|literalinclude|doctest|testcode)::"
)


def refuse_other_code_forms(line):
    """Raise ValueError for code in any form but ``.. code-block:: python``

    The tests run only what parse_code_blocks() recognises. Another form,
    even one of the same language, would never run, and the page could claim
    anything in it.
    """
    if line.strip() == ".. code-block:: python":
        return
    stripped = line.strip()
    literal_block = stripped.endswith("::") and not stripped.startswith("..")
    if CODE_DIRECTIVE.match(stripped) or literal_block or stripped.startswith(">>>"):
        msg = (
            f"Unrecognised form of code on the page: {line.strip()!r}. "
            "Write Python examples as '.. code-block:: python', the only form "
            "the tests run."
        )
        raise ValueError(msg)


def parse_code_blocks(lines):
    """The code blocks of reStructuredText lines as (title, source) pairs

    The title is the heading above the block. A block is a ``code-block``
    directive with the language python; its body is the indented text after
    the directive, without the blank lines at the end.
    """
    blocks = []
    title = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if (
            index + 1 < len(lines)
            and line.strip()
            and UNDERLINE.match(lines[index + 1])
        ):
            title = line.strip()
            index += 2
            continue
        refuse_other_code_forms(line)
        if line.strip() == ".. code-block:: python":
            index += 1
            body = []
            while index < len(lines) and (
                not lines[index].strip() or lines[index].startswith("    ")
            ):
                body.append(lines[index])
                index += 1
            source = textwrap.dedent("\n".join(body)).strip("\n") + "\n"
            blocks.append((title, source))
            continue
        index += 1
    return blocks


def block_params():
    """The blocks as pytest parameters, with the heading as id

    A heading with several blocks gets a counter behind it.
    """
    seen: dict[str, int] = {}
    params = []
    for title, source in code_blocks():
        seen[title] = seen.get(title, 0) + 1
        name = title if seen[title] == 1 else f"{title} {seen[title]}"
        params.append(pytest.param((title, source), id=name))
    return params


def module_names():
    """Every module and package of the library the page has to name

    The package grass.temporal itself is the page's toctree, not a module of
    its own.
    """
    names = set()
    for path in LIBRARY.rglob("*.py"):
        parts = path.relative_to(LIBRARY).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if not parts or LEFT_OUT & set(parts):
            continue
        if any(part.startswith("_") for part in parts):
            continue
        names.add(".".join(("grass.temporal", *parts)))
    return names


def create_datasets(env):
    """Create the datasets of DATASETS with registered maps in the session"""
    for name in DATASETS:
        maps = []
        for number in range(MAPS_PER_DATASET):
            map_name = f"{name}_map_{number}"
            gs.run_command("r.mapcalc", expression=f"{map_name} = {number}", env=env)
            maps.append(map_name)
        gs.run_command(
            "t.create",
            output=name,
            type="strds",
            temporaltype="absolute",
            title=f"Dataset {name}",
            description=f"The datasets of the page, {name}",
            env=env,
        )
        gs.run_command(
            "t.register",
            input=name,
            maps=",".join(maps),
            start="2020-01-01",
            increment="1 days",
            env=env,
        )


@pytest.fixture
def page_session(tmp_path):
    """A session in a new XY project and the folder for the script to run in"""
    with project_session(tmp_path / "project") as session:
        work = tmp_path / "work"
        work.mkdir()
        yield session, work


def prepared_script(title, source, session, work):
    """Write the block to a file and make the datasets it needs

    Returns the path of the script and the environment to run it in.
    """
    env = example_environment(session.env)
    if title != CREATES_ITS_DATASET:
        create_datasets(env)
    script = work / "block.py"
    script.write_text(source)
    return script, env


def test_page_has_code_blocks():
    assert len(code_blocks()) >= 4


@pytest.mark.parametrize(
    "form",
    [
        ".. code:: python",
        ".. sourcecode:: python",
        ".. code-block:: python3",
        ".. code-block:: pycon",
        ".. code-block::",
        "Run this::",
        "::",
        ".. literalinclude:: example.py",
        ".. doctest::",
        ".. testcode::",
        ">>> print(1)",
    ],
)
def test_other_forms_of_code_are_not_skipped_silently(form):
    """A code directive that is not ``code-block:: python`` fails loudly"""
    lines = ["Title", "-----", "", form, "", "    print(1)", ""]
    with pytest.raises(ValueError, match="code"):
        parse_code_blocks(lines)


def test_the_python_code_block_is_parsed():
    lines = ["Title", "-----", "", ".. code-block:: python", "", "    print(1)", ""]
    assert parse_code_blocks(lines) == [("Title", "print(1)\n")]


def test_block_ids_are_unique():
    ids = [param.id for param in block_params()]
    assert len(set(ids)) == len(ids)


@pytest.mark.timeout(300)
@pytest.mark.parametrize("block", block_params())
def test_code_blocks_of_the_page_run(block, page_session):
    """Each code block runs to its end without a traceback"""
    session, work = page_session
    script, env = prepared_script(block[0], block[1], session, work)
    result = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        cwd=work,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.timeout(300)
@pytest.mark.parametrize("block", block_params())
def test_code_blocks_of_the_page_use_only_the_contract(block, page_session):
    """Each code block calls only functions that the public contract lists"""
    session, work = page_session
    script, env = prepared_script(block[0], block[1], session, work)
    names = called_names(script, env=env, cwd=work)
    assert names, "the block calls nothing of grass.temporal"
    assert missing_from_contract(names, contract=json.loads(CONTRACT.read_text())) == []


def test_page_names_every_module():
    """Every module and package of the library appears as :mod: on the page"""
    text = PAGE.read_text()
    named = set(re.findall(r":mod:`~?([A-Za-z0-9_.]+)`", text))
    assert sorted(module_names() - named) == []


def test_page_names_no_module_that_does_not_exist():
    """Every :mod: role of the page names a module of the library"""
    text = PAGE.read_text()
    named = set(re.findall(r":mod:`~?([A-Za-z0-9_.]+)`", text))
    assert sorted(named - module_names()) == []
