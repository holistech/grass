# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check that a temporal manual shows every option and agrees with its .html

``tool_options`` asks a tool for its options, ``shown_options`` collects the
ones the examples of its manual use, and ``NOT_SHOWN`` lists the options that
a manual leaves out on purpose. ``check_html_sync`` compares the ``.md`` with
the ``.html`` kept by hand next to it.
"""

from __future__ import annotations

import difflib
import html.parser
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET

from .manual_examples import (
    FENCE,
    Block,
    Manual,
    block_shell_calls,
    python_calls,
)

# The flags that the parser gives every tool. A tool does not have to show
# them; the shell spells them --overwrite, grass.tools takes keywords.
STANDARD_FLAGS = frozenset({"overwrite", "help", "verbose", "quiet", "ui"})
STANDARD_KEYWORDS = STANDARD_FLAGS | {"superquiet"}

# (tool, option) -> why the manual of the tool does not show the option; an
# option is spelled as in tool_options(), a flag as "-x".
NOT_SHOWN: dict[tuple[str, str], str] = {}


def tool_options(tool: str, env) -> set[str]:
    """Return the parameters and flags (as ``-x``) of a tool

    Read from ``<tool> --interface-description`` in the environment env; the
    standard flags of the parser are left out.
    """
    process = subprocess.run(
        [tool, "--interface-description"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if process.returncode:
        msg = f"{tool} --interface-description failed: {process.stderr}"
        raise RuntimeError(msg)
    # The XML comes from the installed tool, not from outside.
    root = ET.fromstring(process.stdout)  # noqa: S314
    options = {parameter.get("name") for parameter in root.iter("parameter")}
    options.update(
        f"-{flag.get('name')}"
        for flag in root.iter("flag")
        if flag.get("name") not in STANDARD_FLAGS
    )
    return options


def _shell_options(manual: Manual, block: Block) -> set[str]:
    shown = set()
    for words in block_shell_calls(manual.path, block, manual.tool):
        for word in words:
            if word.startswith("--"):
                continue
            if "=" in word:
                shown.add(word.split("=", 1)[0])
            elif word.startswith("-"):
                shown.update(f"-{letter}" for letter in word[1:])
    return shown


def _python_options(code: str, tool: str) -> set[str]:
    shown = set()
    for keywords in python_calls(code, tool):
        for name, value in keywords.items():
            if name == "flags":
                # Without a literal (a variable, None) no letter is known.
                if isinstance(value, str):
                    shown.update(f"-{letter}" for letter in value)
            elif name not in STANDARD_KEYWORDS:
                shown.add(name)
    return shown


def shown_options(manual: Manual) -> set[str]:
    """Return the options of the manual's tool that its examples run with

    An option counts as ``name=`` on a command line of the tool in a shell
    block, a flag as ``-x`` or within a group ``-xy``; in a Python block as a
    keyword of ``<object>.<tool with _>(...)``, a flag as a letter of
    ``flags="..."``. Blocks marked not-run do not count, blocks with a
    requirement do, because they run where it holds. A shell-only example
    does not count either: a catalog lists expressions, and an option has to
    be shown in both tabs. The standard flags are left out. Raises
    ManualFormatError for a shell block that shell_calls cannot split into
    words.
    """
    shown = set()
    for example in manual.examples:
        if example.shell_only:
            continue
        for block in example.blocks:
            if "not-run" in block.control:
                continue
            if block.language == "sh":
                shown |= _shell_options(manual, block)
            else:
                shown |= _python_options(block.code, manual.tool)
    return shown


class _Page(html.parser.HTMLParser):
    """The text of each <pre>, the src of each <img> and of each <h2>, <h3>"""

    def __init__(self):
        # convert_charrefs (the default) hands &lt; to handle_data as "<".
        super().__init__()
        self.pre: list[str] = []
        self.images: set[str] = set()
        self.headings: dict[str, set[str]] = {"h2": set(), "h3": set()}
        self._open: str | None = None
        self._text = ""

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.images.update(value for name, value in attrs if name == "src")
        elif tag in {"pre", "h2", "h3"} and self._open is None:
            self._open, self._text = tag, ""

    def handle_endtag(self, tag):
        if tag != self._open:
            return
        if tag == "pre":
            self.pre.append(_without_line_end_blanks(self._text))
        else:
            self.headings[tag].add(" ".join(self._text.split()))
        self._open = None

    def handle_data(self, data):
        if self._open:
            self._text += data


def _without_line_end_blanks(text: str) -> str:
    return "\n".join(line.rstrip(" \t") for line in text.split("\n")).strip("\n")


def _markdown_blocks(path: Path) -> list[tuple[int, str]]:
    """Each fenced block of the file as (line of the fence, content)

    The content loses the indentation of its fence, as a tab of an example
    is indented by four spaces that the .html does not have.
    """
    lines = path.read_text(encoding="utf-8").split("\n")
    found = []
    index = 0
    while index < len(lines):
        fence = FENCE.match(lines[index])
        if not fence:
            index += 1
            continue
        indent = fence.group(1)
        start = index
        body = []
        index += 1
        while index < len(lines) and lines[index].rstrip() != f"{indent}```":
            row = lines[index]
            body.append(row[len(indent) :] if row.startswith(indent) else row.strip())
            index += 1
        found.append((start + 1, "\n".join(body).strip("\n")))
        index += 1
    return found


def _markdown_headings(path: Path) -> list[tuple[str, str]]:
    """Each ``##`` and ``###`` heading as (HTML tag, text with single blanks)"""
    headings = []
    in_fence = False
    for line in path.read_text(encoding="utf-8").split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        marks, _, text = line.partition(" ")
        if not in_fence and marks in {"##", "###"}:
            headings.append((f"h{len(marks)}", " ".join(text.split())))
    return headings


def _block_findings(manual: Manual, html_path: Path, pre: list[str]) -> list[str]:
    """Where the fenced blocks of the .md and the <pre> of the .html differ

    A block and a <pre> at the same place of a changed stretch form one
    finding with both texts; what is left of the longer side is reported
    alone.
    """
    blocks = list(_markdown_blocks(manual.path))
    matcher = difflib.SequenceMatcher(
        a=[_without_line_end_blanks(text) for _, text in blocks], b=pre, autojunk=False
    )
    findings = []
    for tag, first, last, html_first, html_last in matcher.get_opcodes():
        if tag == "equal":
            continue
        changed = blocks[first:last]
        numbers = range(html_first, html_last)
        for (line, text), number in zip(changed, numbers, strict=False):
            findings.append(
                f"{manual.path}:{line}: block differs from <pre> {number + 1} of "
                f"{html_path}:\n{text}\n--- the <pre>:\n{pre[number]}"
            )
        findings.extend(
            f"{manual.path}:{line}: block not in a <pre> of {html_path}:\n{text}"
            for line, text in changed[len(numbers) :]
        )
        findings.extend(
            f"{html_path}: <pre> {number + 1} is no block of {manual.path}:\n"
            f"{pre[number]}"
            for number in numbers[len(changed) :]
        )
    return findings


def check_html_sync(manual: Manual, html_path: Path) -> list[str]:
    """Return where the .md and the .html differ, one entry per finding

    The fenced blocks of the ``.md`` (code and shown output, inside the
    examples and elsewhere) and the ``<pre>`` of the ``.html`` have to be the
    same texts in the same order, after the entities are resolved (``&lt;`` is
    ``<``) and the newlines at both ends are dropped. The order matters: an
    output that both tabs show alike is in the ``.html`` twice, and a change
    of one copy would otherwise go unseen. A block of the ``.md`` that has no
    ``<pre>`` at its place and a ``<pre>`` that has no block are reported each
    with its text. Blanks at the end of a line do not count on either
    side: the trailing-whitespace hook of pre-commit strips them from .html
    files but not from .md files, which it leaves out, and a reader cannot see
    them. The comparison of a shown output with the run stays exact (see
    manual_examples.check_manual). Every image of the ``.md`` has to be the
    ``src`` of an ``<img>``; every ``##`` heading has to be an ``<h2>``, every
    ``###`` heading an ``<h3>``. An empty list means the two agree in these
    respects; the prose between them is not compared.
    """
    page = _Page()
    page.feed(Path(html_path).read_text(encoding="utf-8"))
    page.close()
    missing = _block_findings(manual, html_path, page.pre)
    missing.extend(
        f"{manual.path}: image {image} not in an <img src> of {html_path}"
        for image in manual.images
        if image not in page.images
    )
    missing.extend(
        f"{manual.path}: heading {heading!r} not an <{tag}> of {html_path}"
        for tag, heading in _markdown_headings(manual.path)
        if heading not in page.headings[tag]
    )
    return missing
