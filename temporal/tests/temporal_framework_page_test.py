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

The guides listed in PAGES (the page "Writing a temporal tool" and the pages
that join it) hold more than Python snippets. They are read with the rules of
parse_guide(), which knows these forms and refuses every other:

- ``.. code-block:: python`` without a name is a snippet, run like the blocks
  of the overview page, if the page lists its snippets as run (``Page.snippets``);
- a block with a ``:name:`` of the form ``example-<kind>-<what>`` is part of an
  example that the test assembles in a folder: ``example-tool-file`` is the
  Python file of a tool, written under the name of its ``:caption:``, and
  ``example-data-<what>`` is a text file written under its caption;
  ``example-commands-<what>`` is a ``text`` block of commands, one per line,
  that the test runs in order (``python3`` stands for the interpreter of the
  test); ``example-output-<what>`` right behind it is the standard output of
  those commands, which the test compares;
- ``.. literalinclude::`` only with ``:pyobject:`` or with ``:start-after:``
  and ``:end-before:``, never with line numbers, which drift when the file
  changes. The test checks the selection against the real file (see
  literalinclude_selection()).

A page joins the tests by an entry in PAGES. Its named blocks and includes are
then checked, and the overview page must link it in a toctree.

The pages are not built with Sphinx here: the documentation workflow builds
them, and a build needs packages that the tests do not.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
import shlex
import subprocess
import sys
import textwrap
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Page:
    """A page of the developer documentation that the tests keep true

    ``guide`` pages may hold the named blocks and the literalinclude
    directives of parse_guide(); ``snippets`` tells whether their unnamed
    ``code-block:: python`` blocks are run by a test, as those of the overview
    page are. A guide page without that test refuses an unnamed block, so that
    no code on it goes unrun. ``includes`` is the number of literalinclude
    directives the page holds; the test of the includes fails when a page
    holds another number, so that a page cannot lose them unnoticed.
    """

    name: str
    path: Path
    guide: bool = True
    snippets: bool = False
    includes: int = 0


# The pages in the order of the overview's toctree. A new guide adds one entry.
PAGES = (
    Page("overview", PAGE, guide=False, snippets=True),
    Page("tools", PAGE.with_name("temporal_framework_tools.rst"), includes=4),
)

NAMED_BLOCK = re.compile(
    r"^example-(tool-file|data|commands|output)(?:-([a-z0-9-]+))?$"
)
CODE_BLOCK = re.compile(r"^\.\.\s+code-block::\s*(\S*)\s*$")
LITERALINCLUDE = re.compile(r"^\.\.\s+literalinclude::\s*(\S+)\s*$")
DIRECTIVE_OPTION = re.compile(r"^\s+:([a-z-]+):\s*(.*?)\s*$")


@dataclass(frozen=True)
class GuideBlock:
    """A code block of a guide page: its kind, name, caption and body

    kind is "snippet" for an unnamed Python block, else the kind of the name
    (``tool-file``, ``data``, ``commands`` or ``output``); what is the part of
    the name behind the kind, which pairs an output block with its commands.
    """

    kind: str
    what: str
    caption: str
    body: str
    title: str


@dataclass(frozen=True)
class Include:
    """A literalinclude directive: the file as written and its options"""

    filename: str
    options: dict
    title: str


def directive_options(lines, index):
    """The options right behind a directive at lines[index] and the next index"""
    options = {}
    index += 1
    while index < len(lines) and (match := DIRECTIVE_OPTION.match(lines[index])):
        options[match.group(1)] = match.group(2)
        index += 1
    return options, index


def indented_body(lines, index):
    """The indented text from lines[index] on, dedented, and the next index"""
    body = []
    while index < len(lines) and (
        not lines[index].strip() or lines[index].startswith("    ")
    ):
        body.append(lines[index])
        index += 1
    return textwrap.dedent("\n".join(body)).strip("\n") + "\n", index


def guide_block(language, options, body, title, page):
    """Make the GuideBlock of a code block or raise ValueError for a bad one"""
    name = options.get("name")
    if name is None:
        if language != "python":
            msg = (
                f"A '{language}' block of {page.name} needs a ':name:' of the "
                "form 'example-<kind>-<what>'; unnamed code runs only as "
                "'.. code-block:: python'"
            )
            raise ValueError(msg)
        if not page.snippets:
            msg = (
                f"An unnamed Python block under {title!r} on page {page.name} "
                "would not run: the page has no test for its snippets. Name it "
                "'example-tool-file' or list the page with snippets=True."
            )
            raise ValueError(msg)
        return GuideBlock("snippet", "", "", body, title)
    if not page.guide:
        msg = f"Page {page.name} is no guide, so it has no named block {name!r}"
        raise ValueError(msg)
    match = NAMED_BLOCK.match(name)
    if match is None:
        msg = f"The name {name!r} is not 'example-<kind>-<what>' with a known kind"
        raise ValueError(msg)
    kind, what = match.group(1), match.group(2) or ""
    wanted = "python" if kind == "tool-file" else "text"
    if language != wanted:
        msg = f"The block {name!r} must be '.. code-block:: {wanted}', not {language!r}"
        raise ValueError(msg)
    caption = options.get("caption", "")
    if kind in {"tool-file", "data"} and (not caption or Path(caption).name != caption):
        msg = f"The block {name!r} needs the plain file name as its ':caption:'"
        raise ValueError(msg)
    if kind in {"commands", "output"} and not what:
        msg = f"The block {name!r} needs a part behind the kind to pair it"
        raise ValueError(msg)
    return GuideBlock(kind, what, caption, body, title)


def parse_guide(lines, page):
    """The code blocks and includes of a page, as GuideBlock and Include objects

    The forms are those of the module docstring. Any other form of code, any
    unknown or misplaced name and an output block that does not follow the
    commands of its name raise ValueError.
    """
    items = []
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
        block = CODE_BLOCK.match(line)
        include = LITERALINCLUDE.match(line)
        if block:
            options, index = directive_options(lines, index)
            body, index = indented_body(lines, index)
            items.append(guide_block(block.group(1), options, body, title, page))
            check_output_follows_commands(items)
            continue
        if include:
            if not page.guide:
                msg = f"Page {page.name} is no guide, so it has no literalinclude"
                raise ValueError(msg)
            options, index = directive_options(lines, index)
            items.append(Include(include.group(1), options, title))
            continue
        refuse_other_code_forms(line)
        index += 1
    return items


def check_output_follows_commands(items):
    """Raise ValueError if the newest block is an output without its commands"""
    last = items[-1]
    if last.kind != "output":
        return
    before = items[-2] if len(items) > 1 else None
    if not (
        isinstance(before, GuideBlock)
        and before.kind == "commands"
        and before.what == last.what
    ):
        msg = f"The output block {last.what!r} must follow the commands block of that name"
        raise ValueError(msg)


def page_items(page):
    return parse_guide(page.path.read_text().splitlines(), page)


def blocks_of(page):
    return [item for item in page_items(page) if isinstance(item, GuideBlock)]


def includes_of(page):
    return [item for item in page_items(page) if isinstance(item, Include)]


FORBIDDEN_SELECTORS = ("lines", "start-line", "end-line", "start-at", "end-at")


def pyobject_source(path, dotted):
    """The source of a function or class of a Python file, ``Class.method`` too

    Raises ValueError if the file is not Python or has no such object. The
    lookup walks the syntax tree, so it proves that the object exists; it is
    not Sphinx's lookup, which also decides whether decorators are shown, so
    the exact rendered text is not checked here.
    """
    if path.suffix != ".py":
        msg = f"':pyobject:' needs a Python file, {path.name} is not one"
        raise ValueError(msg)
    source = path.read_text()
    scope = ast.parse(source)
    for part in dotted.split("."):
        found = [
            node
            for node in scope.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
            and node.name == part
        ]
        if not found:
            msg = f"{path.name} has no object {dotted!r} (no {part!r})"
            raise ValueError(msg)
        scope = found[0]
    return ast.get_source_segment(source, scope) or ""


def marker_line(lines, marker, option, path):
    """The index of the one line of a file that holds the marker"""
    hits = [number for number, line in enumerate(lines) if marker in line]
    if len(hits) != 1:
        msg = (
            f"The marker {marker!r} of ':{option}:' must occur exactly once in "
            f"{path.name}, it occurs {len(hits)} times"
        )
        raise ValueError(msg)
    return hits[0]


def literalinclude_selection(page_path, include):
    """The text that a literalinclude directive selects, checked

    The file is looked up from the folder of the page, as Sphinx does. The
    selection is a ``:pyobject:`` or the lines between ``:start-after:`` and
    ``:end-before:``; each marker must occur once, so that a second occurrence
    added later cannot move the selection unnoticed. Raises ValueError for
    a missing file, an option that selects by line number, a selection of
    the whole file, a missing object or marker, and an empty selection.
    """
    path = (page_path.parent / include.filename).resolve()
    if not path.is_file():
        msg = f"literalinclude file not found: {include.filename}"
        raise ValueError(msg)
    options = include.options
    forbidden = [name for name in FORBIDDEN_SELECTORS if name in options]
    if forbidden:
        msg = (
            f"literalinclude of {include.filename} uses {forbidden}; select with "
            "':pyobject:' or ':start-after:'/':end-before:', which survive edits"
        )
        raise ValueError(msg)
    markers = [name for name in ("start-after", "end-before") if name in options]
    if ("pyobject" in options) == bool(markers):
        msg = (
            f"literalinclude of {include.filename} needs either ':pyobject:' or "
            "markers, and not both"
        )
        raise ValueError(msg)
    if "pyobject" in options:
        selected = pyobject_source(path, options["pyobject"])
    else:
        lines = path.read_text().splitlines()
        first, last = 0, len(lines)
        if "start-after" in options:
            first = marker_line(lines, options["start-after"], "start-after", path) + 1
        if "end-before" in options:
            last = marker_line(lines, options["end-before"], "end-before", path)
        selected = "\n".join(lines[first:last]) if first < last else ""
    if not selected.strip():
        msg = f"literalinclude of {include.filename} selects nothing"
        raise ValueError(msg)
    return selected


@pytest.mark.parametrize("page", PAGES, ids=[page.name for page in PAGES])
def test_literalinclude_selects_existing_code(page):
    """Each literalinclude of a page selects code of an existing file"""
    includes = includes_of(page)
    assert len(includes) == page.includes
    for include in includes:
        assert literalinclude_selection(page.path, include).strip()


def an_include(**options):
    return Include("sample.py", options, "Title")


SAMPLE = """\
# first marker
def top():
    return 1


class Holder:
    def method(self):
        return 2


# second marker
x = 1
# end marker
"""


@pytest.fixture
def sample_page(tmp_path):
    (tmp_path / "sample.py").write_text(SAMPLE)
    (tmp_path / "data.txt").write_text("one\ntwo\none\n")
    return tmp_path / "page.rst"


@pytest.mark.parametrize(
    ("options", "expected"),
    [
        ({"pyobject": "top"}, "def top():"),
        ({"pyobject": "Holder.method"}, "def method(self):"),
        (
            {"start-after": "first marker", "end-before": "second marker"},
            "class Holder:",
        ),
        ({"start-after": "second marker"}, "x = 1"),
        ({"end-before": "first marker"}, None),
    ],
    ids=["function", "method", "between", "to the end", "empty before the start"],
)
def test_literalinclude_selection_of_the_real_forms(sample_page, options, expected):
    if expected is None:
        with pytest.raises(ValueError, match="selects nothing"):
            literalinclude_selection(sample_page, an_include(**options))
    else:
        assert expected in literalinclude_selection(sample_page, an_include(**options))


@pytest.mark.parametrize(
    ("include", "message"),
    [
        (Include("missing.py", {"pyobject": "top"}, "T"), "file not found"),
        (an_include(pyobject="invented"), "no object 'invented'"),
        (an_include(pyobject="Holder.invented"), "no object 'Holder.invented'"),
        (Include("data.txt", {"pyobject": "top"}, "T"), "needs a Python file"),
        (an_include(lines="1-3"), "uses .*lines"),
        (an_include(**{"start-line": "1"}), "start-line"),
        (an_include(**{"start-at": "def top"}), "start-at"),
        (an_include(), "needs either"),
        (an_include(pyobject="top", **{"start-after": "first marker"}), "not both"),
        (an_include(**{"start-after": "absent marker"}), "occurs 0 times"),
        (an_include(**{"start-after": "marker"}), "occurs 3 times"),
        (an_include(**{"end-before": "absent marker"}), "occurs 0 times"),
        (an_include(**{"start-after": "end marker"}), "selects nothing"),
        (
            an_include(
                **{"start-after": "second marker", "end-before": "first marker"}
            ),
            "selects nothing",
        ),
    ],
)
def test_literalinclude_check_refuses_a_bad_selection(sample_page, include, message):
    with pytest.raises(ValueError, match=message):
        literalinclude_selection(sample_page, include)


def test_literalinclude_check_refuses_a_marker_that_occurs_twice(sample_page):
    sample_page.with_name("data.py").write_text("one\ntwo\none\n")
    include = Include("data.py", {"start-after": "one"}, "T")

    with pytest.raises(ValueError, match="occurs 2 times"):
        literalinclude_selection(sample_page, include)


GUIDE = Page("sample", Path("sample.rst"))
ARCHIVE = [
    "Title",
    "-----",
    "",
    ".. code-block:: text",
    "    :name: example-commands-all",
    "",
    "    t.list",
    "",
    ".. code-block:: text",
    "    :name: example-output-all",
    "",
    "    x",
    "",
]


def test_guide_blocks_and_their_options_are_parsed():
    lines = [
        "Title",
        "-----",
        "",
        ".. code-block:: python",
        "    :caption: tool.py",
        "    :name: example-tool-file",
        "",
        "    print(1)",
        "",
        ".. literalinclude:: ../x.py",
        "    :pyobject: top",
        "",
        *ARCHIVE[3:],
    ]

    items = parse_guide(lines, GUIDE)

    assert [type(item).__name__ for item in items] == [
        "GuideBlock",
        "Include",
        "GuideBlock",
        "GuideBlock",
    ]
    assert items[0] == GuideBlock("tool-file", "", "tool.py", "print(1)\n", "Title")
    assert items[1].options == {"pyobject": "top"}
    assert [(item.kind, item.what, item.body) for item in items[2:]] == [
        ("commands", "all", "t.list\n"),
        ("output", "all", "x\n"),
    ]


@pytest.mark.parametrize(
    ("page", "lines", "message"),
    [
        (GUIDE, [".. code-block:: text", "", "    t.list"], "needs a ':name:'"),
        (GUIDE, [".. code-block:: sh", "", "    t.list"], "needs a ':name:'"),
        (GUIDE, [".. code-block:: python", "", "    print(1)"], "would not run"),
        (
            GUIDE,
            [".. code-block:: text", "    :name: example-tool-file", "", "    x"],
            "must be '.. code-block:: python'",
        ),
        (
            GUIDE,
            [".. code-block:: python", "    :name: example-commands-a", "", "    x"],
            "must be '.. code-block:: text'",
        ),
        (
            GUIDE,
            [".. code-block:: text", "    :name: example-data-a", "", "    x"],
            "plain file name",
        ),
        (
            GUIDE,
            [
                ".. code-block:: text",
                "    :name: example-data-a",
                "    :caption: ../a.txt",
                "",
                "    x",
            ],
            "plain file name",
        ),
        (
            GUIDE,
            [".. code-block:: text", "    :name: example-other-a", "", "    x"],
            "known kind",
        ),
        (
            GUIDE,
            [".. code-block:: text", "    :name: example-commands", "", "    x"],
            "needs a part",
        ),
        (
            GUIDE,
            [".. code-block:: text", "    :name: example-output-a", "", "    x"],
            "must follow the commands",
        ),
        (
            GUIDE,
            [
                *ARCHIVE[3:8],
                ".. code-block:: text",
                "    :name: example-output-other",
                "",
                "    x",
            ],
            "must follow the commands block of that name",
        ),
        (GUIDE, [".. code:: python", "", "    print(1)"], "Unrecognised form"),
        (GUIDE, ["Run this::", "", "    print(1)"], "Unrecognised form"),
        (
            Page("flat", Path("flat.rst"), guide=False, snippets=True),
            [".. code-block:: text", "    :name: example-commands-a", "", "    t.list"],
            "no guide",
        ),
        (
            Page("flat", Path("flat.rst"), guide=False, snippets=True),
            [".. literalinclude:: x.py", "    :pyobject: top"],
            "no guide",
        ),
    ],
)
def test_guide_forms_that_would_not_be_checked_are_refused(page, lines, message):
    with pytest.raises(ValueError, match=message):
        parse_guide(lines, page)


def test_unnamed_python_blocks_are_snippets_on_a_page_that_runs_them():
    lines = [".. code-block:: python", "", "    print(1)"]
    page = Page("runs", Path("runs.rst"), snippets=True)

    assert [(b.kind, b.body) for b in parse_guide(lines, page)] == [
        ("snippet", "print(1)\n")
    ]


@pytest.mark.parametrize("page", PAGES, ids=[page.name for page in PAGES])
def test_every_page_parses_under_its_own_rules(page):
    assert page_items(page) is not None


def toctree_entries(text):
    """The documents that the toctrees of reStructuredText text list"""
    entries = []
    inside = False
    for line in text.splitlines():
        if line.startswith(".. toctree::"):
            inside = True
        elif inside and line.strip() and not line.startswith(" "):
            inside = False
        elif inside and line.strip() and not line.strip().startswith(":"):
            entries.append(line.strip())
    return entries


def test_overview_links_every_guide_in_a_toctree():
    listed = toctree_entries(PAGE.read_text())
    guides = [page.path.stem for page in PAGES if page.guide]

    assert [name for name in guides if name not in listed] == []


def test_toctree_entries_are_read_without_options():
    text = ".. toctree::\n   :maxdepth: 1\n\n   one\n   two\n\nText\n"

    assert toctree_entries(text) == ["one", "two"]


def tool_blocks():
    return blocks_of(PAGES[1])


def page_commands(block):
    """The commands of a commands block, each as the list of its words"""
    return [shlex.split(line) for line in block.body.splitlines() if line.strip()]


def write_example_files(blocks, work):
    """Write the tool file and the data files of the blocks, return the tool's name"""
    tool = None
    for block in blocks:
        if block.kind in {"tool-file", "data"}:
            (work / block.caption).write_text(block.body)
        if block.kind == "tool-file":
            tool = block.caption
    return tool


def run_example(blocks, session_env, work, *, trace=False):
    """Run the commands of the blocks as the page shows them

    Returns the output of each commands block as (what, stdout) and the names of
    grass.temporal that the tool called when trace is true; the calls of the
    tool are then traced instead of run plainly, so their output is empty.
    """
    tool = write_example_files(blocks, work)
    outputs = []
    names = set()
    for block in blocks:
        if block.kind != "commands":
            continue
        text = ""
        for command in page_commands(block):
            if trace and command[:2] == ["python3", tool]:
                names |= called_names(
                    work / tool, env=session_env, cwd=work, argv=tuple(command[2:])
                )
                continue
            argv = [
                sys.executable if command[0] == "python3" else command[0],
                *command[1:],
            ]
            result = subprocess.run(
                argv,
                env=session_env,
                cwd=work,
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode == 0, f"{shlex.join(command)}\n{result.stderr}"
            text += result.stdout
        outputs.append((block.what, text))
    return outputs, names


def shown_outputs(blocks):
    """The output blocks of the page by the part of their name"""
    return {block.what: block.body for block in blocks if block.kind == "output"}


def test_the_tool_guide_shows_a_tool_with_calls_and_outputs():
    blocks = tool_blocks()
    kinds = [block.kind for block in blocks]
    tool = [block for block in blocks if block.kind == "tool-file"]

    assert len(tool) == 1
    assert "def main():" in tool[0].body
    assert "tool-file" in kinds
    assert len(shown_outputs(blocks)) >= 3
    calls = [
        command
        for block in blocks
        if block.kind == "commands"
        for command in page_commands(block)
        if command[:2] == ["python3", tool[0].caption]
    ]
    assert len(calls) >= 3


@pytest.mark.timeout(300)
def test_example_tool_runs_as_the_page_shows(page_session):
    """The tool of the page and its calls run and print what the page shows"""
    session, work = page_session
    blocks = tool_blocks()
    env = example_environment(session.env)

    outputs, _names = run_example(blocks, env, work)

    shown = shown_outputs(blocks)
    for what, text in outputs:
        if what in shown:
            assert text.rstrip("\n") == shown[what].rstrip("\n"), what
    assert {what for what, _text in outputs if what in shown} == set(shown)


@pytest.mark.timeout(300)
def test_example_tool_uses_only_the_contract(page_session):
    """The tool calls only functions that the public contract lists"""
    session, work = page_session
    env = example_environment(session.env)

    _outputs, names = run_example(tool_blocks(), env, work, trace=True)

    assert names, "the tool calls nothing of grass.temporal"
    assert missing_from_contract(names, contract=json.loads(CONTRACT.read_text())) == []


@pytest.mark.timeout(300)
def test_example_tool_loads_no_temporal_code_for_its_interface(page_session):
    """--interface-description answers before main() imports grass.temporal"""
    session, work = page_session
    tool = write_example_files(tool_blocks(), work)

    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "importtime",
            str(work / tool),
            "--interface-description",
        ],
        env=example_environment(session.env),
        cwd=work,
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
    assert loaded, "the import time of the interpreter is not shown"
    assert not [name for name in loaded if name.startswith("grass.temporal")]


def roles_of(page, kinds=("func", "class", "mod", "meth", "attr")):
    """The grass.temporal names that the roles of the page refer to

    Only the roles of ``kinds`` are read; a role of another kind (``:data:``,
    ``:exc:``, ``:ref:``) is not checked.
    """
    pattern = rf":(?:{'|'.join(kinds)}):`~?(grass\.temporal[A-Za-z0-9_.]*)(?:\(\))?`"
    return sorted(set(re.findall(pattern, page.path.read_text())))


def resolve(dotted):
    """The object that a dotted name refers to: a module, then attributes"""
    parts = dotted.split(".")
    for end in range(len(parts), 0, -1):
        try:
            found = importlib.import_module(".".join(parts[:end]))
        except ModuleNotFoundError:
            continue
        for attribute in parts[end:]:
            found = getattr(found, attribute)
        return found
    raise ModuleNotFoundError(dotted)


@pytest.mark.parametrize("page", PAGES[1:], ids=[page.name for page in PAGES[1:]])
def test_the_names_that_a_guide_refers_to_exist(page):
    """Every role of the page names a module, function or class that exists"""
    names = roles_of(page)

    assert names
    assert [name for name in names if not _exists(name)] == []


def _exists(dotted):
    try:
        resolve(dotted)
    except (ModuleNotFoundError, AttributeError):
        return False
    return True


def test_resolve_finds_modules_functions_and_methods_and_not_invented_names():
    assert _exists("grass.temporal.tool_steps")
    assert _exists("grass.temporal.tool_steps.names_from_file")
    assert _exists("grass.temporal.db.SQLDatabaseInterfaceConnection")
    assert not _exists("grass.temporal.tool_steps.invented_step")
    assert not _exists("grass.temporal.invented_module.names_from_file")


def test_the_tool_guide_names_every_shared_step():
    """Each public function of tool_steps has a role on the tool guide"""
    from grass.temporal import tool_steps

    defined = {
        f"grass.temporal.tool_steps.{name}"
        for name, function in vars(tool_steps).items()
        if callable(function)
        and getattr(function, "__module__", "") == tool_steps.__name__
        and not name.startswith("_")
    }

    assert defined
    assert sorted(defined - set(roles_of(PAGES[1]))) == []
