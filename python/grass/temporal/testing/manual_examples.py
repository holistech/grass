# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Read the examples of a temporal tool manual and normalise their output

A manual written for testing keeps its examples under ``## EXAMPLES``. Each
``###`` heading there is one example with two tabs of the layout used by
``raster/r.sim/r.sim.water/r.sim.water.md``::

    === "Command line"

        ```sh
        t.create ...
        ```

        ```text
        output as shown to the reader
        ```

    === "Python (grass.tools)"

        ```python
        ...
        ```

A ``text`` block directly after a code block of the same tab is the output
shown for that block. Blocks of any other language are rejected, so that
there is one spelling (``sh``, not ``bash``). An HTML comment
``<!-- example: key=value -->`` directly before a code block steers the test
and stays invisible to the reader; ``<!-- example-project: crs=... -->`` under
``## EXAMPLES`` names the coordinate system the examples need. This module
only reads; running, coverage and the sync with the ``.html`` live elsewhere.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

TABS = {"Command line": "shell", "Python (grass.tools)": "python"}
LANGUAGES = {"shell": "sh", "python": "python"}
INDENT = "    "
FIXED_TIME = "2026-11-01 12:00:00"
FIXED_DATABASE = "/home/user/grassdata"
FIXED_USER = "user"
# Any 32 hex digits; the real name carries a uuid4 that differs every run.
FIXED_REGISTER = "0" * 32

CONTROL_KEYS = ("requires", "not-run", "reason")
SIMPLE_REQUIREMENTS = ("postgresql", "old-database")

FENCE = re.compile(r"^(\s*)```(\S*)\s*$")
CONTROL = re.compile(r"^\s*<!--\s*example:\s*(.*?)\s*-->\s*$")
PROJECT = re.compile(r"^\s*<!--\s*example-project:\s*(.*?)\s*-->\s*$")
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
TAB = re.compile(r'^=== "(.*)"\s*$')


class ManualFormatError(Exception):
    """A manual does not follow the layout, with the file and line"""

    def __init__(self, path: Path, line: int, message: str):
        super().__init__(f"{path}:{line}: {message}")
        self.path = path
        self.line = line
        self.message = message


@dataclass(frozen=True)
class Block:
    """One code block of a tab

    ``code`` and ``shown_output`` are the block content as written, without
    the four spaces of the tab, each line ending with a newline. ``line`` is
    the 1-based line of the opening fence in the file.
    """

    code: str
    language: str
    shown_output: str | None
    control: dict[str, str]
    line: int


@dataclass(frozen=True)
class Example:
    """One variant ("shell" or "python") of a ``###`` example"""

    title: str
    variant: str
    blocks: tuple[Block, ...]
    images: tuple[str, ...]


@dataclass(frozen=True)
class Manual:
    """A parsed manual

    ``examples`` follows the document: for each ``###`` the shell variant
    first, then the python variant. ``images`` lists every image of the file,
    ``project`` the key/values of ``example-project``.
    """

    tool: str
    path: Path
    examples: tuple[Example, ...]
    project: dict[str, str]
    images: tuple[str, ...]


@dataclass(frozen=True)
class NormalizeContext:
    """The values of one run that ``normalize`` replaces"""

    database: str
    user: str


@dataclass
class _Section:
    title: str
    line: int
    blocks: dict[str, list[Block]] = field(
        default_factory=lambda: {"shell": [], "python": []}
    )
    seen: set[str] = field(default_factory=set)
    images: list[str] = field(default_factory=list)


def _words(path: Path, number: int, text: str) -> list[tuple[str, str | None]]:
    try:
        tokens = shlex.split(text)
    except ValueError as error:
        raise ManualFormatError(path, number, f"bad control comment: {error}") from None
    pairs = []
    for token in tokens:
        key, sep, value = token.partition("=")
        pairs.append((key, value if sep else None))
    return pairs


def _control(path: Path, number: int, text: str) -> dict[str, str]:
    control: dict[str, str] = {}
    for key, value in _words(path, number, text):
        if key not in CONTROL_KEYS:
            raise ManualFormatError(
                path, number, f"unknown control key {key!r}, known: {CONTROL_KEYS}"
            )
        if key in control:
            raise ManualFormatError(path, number, f"control key {key!r} given twice")
        if key == "not-run":
            if value is not None:
                raise ManualFormatError(path, number, "not-run takes no value")
            value = ""
        elif not value:
            raise ManualFormatError(path, number, f"control key {key!r} needs a value")
        control[key] = value
    if "requires" in control:
        need = control["requires"]
        driver = need[len("gdal:") :] if need.startswith("gdal:") else ""
        if need not in SIMPLE_REQUIREMENTS and not driver:
            raise ManualFormatError(
                path,
                number,
                f"unknown requirement {need!r}, known: "
                f"{SIMPLE_REQUIREMENTS} and gdal:<driver>",
            )
    if ("not-run" in control) != ("reason" in control):
        raise ManualFormatError(path, number, "not-run and reason belong together")
    return control


def _project(path: Path, number: int, text: str) -> dict[str, str]:
    project = {}
    for key, value in _words(path, number, text):
        if key != "crs" or not value:
            raise ManualFormatError(
                path, number, f"example-project knows only crs=<value>, got {key!r}"
            )
        project[key] = value
    return project


class _Parser:
    """The line by line state of one ``parse_manual`` run"""

    def __init__(self, path: Path):
        self.path = path
        self.tool = path.stem
        self.lines = path.read_text(encoding="utf-8").split("\n")
        if self.lines and self.lines[-1] == "":
            self.lines.pop()
        self.sections: list[_Section] = []
        self.project: dict[str, str] = {}
        self.images: list[str] = []
        self.in_examples = False
        self.section: _Section | None = None
        self.variant: str | None = None
        self.pending: dict[str, str] | None = None
        self.last: Block | None = None
        self.index = 0

    def fail(self, number: int, message: str):
        where = self.tool
        if self.section is not None:
            where += f", example {self.section.title!r}"
        raise ManualFormatError(self.path, number, f"{where}: {message}")

    def run(self) -> Manual:
        while self.index < len(self.lines):
            number = self.index + 1
            text = self.lines[self.index]
            fence = FENCE.match(text)
            if fence:
                self.fence(number, *fence.groups())
            else:
                self.index += 1
                self.line(number, text)
        if self.pending is not None:
            self.fail(len(self.lines), "control comment without a code block")
        return Manual(
            self.tool,
            self.path,
            tuple(self.examples()),
            self.project,
            tuple(self.images),
        )

    def fence(self, number: int, indent: str, language: str):
        body = []
        end = self.index + 1
        while end < len(self.lines) and self.lines[end].rstrip() != f"{indent}```":
            body.append(self.lines[end])
            end += 1
        if end >= len(self.lines):
            self.fail(number, "code fence is never closed")
        self.index = end + 1
        section, variant = self.section, self.variant
        if not self.in_examples or section is None:
            return
        if variant is None:
            self.fail(number, "code block outside a tab")
        if indent != INDENT:
            self.fail(number, "fences of a tab are indented by four spaces")
        content = self.dedent(number, body)
        if language == "text":
            self.shown_output(number, content)
            return
        if language != LANGUAGES[variant]:
            self.fail(
                number,
                f"language {language!r} in the {variant} tab, "
                f"expected {LANGUAGES[variant]!r}",
            )
        self.last = Block(content, language, None, self.pending or {}, number)
        self.pending = None
        section.blocks[variant].append(self.last)

    def dedent(self, number: int, body: list[str]) -> str:
        content = ""
        for offset, row in enumerate(body):
            if row.startswith(INDENT):
                row = row[len(INDENT) :]
            elif row.strip():
                self.fail(number + 1 + offset, "line is not indented by the tab")
            else:
                row = ""
            content += row + "\n"
        return content

    def shown_output(self, number: int, content: str):
        last = self.last
        if last is None or last.shown_output is not None:
            self.fail(number, "text block does not follow a code block")
        blocks = self.section.blocks[self.variant]
        blocks[-1] = Block(last.code, last.language, content, last.control, last.line)
        self.last = self.pending = None

    def line(self, number: int, text: str):
        found = IMAGE.findall(text)
        self.images.extend(found)
        if self.pending is not None and (text.startswith("#") or TAB.match(text)):
            self.fail(number, "control comment without a code block")
        if text.startswith("## "):
            self.in_examples = text.strip() == "## EXAMPLES"
            self.section = self.variant = self.last = self.pending = None
            return
        if not self.in_examples:
            return
        if self.section is not None:
            self.section.images.extend(found)
        if PROJECT.match(text):
            if self.section is not None:
                self.fail(number, "example-project belongs directly under ## EXAMPLES")
            self.project = _project(self.path, number, PROJECT.match(text).group(1))
        elif text.startswith("### "):
            self.section = _Section(text[4:].strip(), number)
            self.sections.append(self.section)
            self.variant = self.last = None
        elif self.section is None:
            return
        elif TAB.match(text):
            self.tab(number, TAB.match(text).group(1))
        elif CONTROL.match(text):
            self.control(number, text)
        elif text.strip():
            if not text.startswith(INDENT):
                self.variant = None
            elif self.pending is not None:
                self.fail(number, "control comment without a code block")
            self.last = None

    def tab(self, number: int, label: str):
        if label not in TABS:
            self.fail(number, f"unknown tab {label!r}, known: {tuple(TABS)}")
        self.variant = TABS[label]
        if self.variant in self.section.seen:
            self.fail(number, f"tab {label!r} given twice")
        self.section.seen.add(self.variant)
        self.last = self.pending = None

    def control(self, number: int, text: str):
        if self.variant is None or not text.startswith(INDENT):
            self.fail(number, "control comment must stand inside a tab")
        if self.pending is not None:
            self.fail(number, "two control comments before one code block")
        self.pending = _control(self.path, number, CONTROL.match(text).group(1))
        self.last = None

    def examples(self):
        for item in self.sections:
            for label, name in TABS.items():
                where = f"{self.tool}, example {item.title!r}: tab {label!r}"
                if name not in item.seen:
                    raise ManualFormatError(self.path, item.line, f"{where} is missing")
                if not item.blocks[name]:
                    raise ManualFormatError(
                        self.path, item.line, f"{where} has no code"
                    )
                yield Example(
                    item.title, name, tuple(item.blocks[name]), tuple(item.images)
                )


def parse_manual(path: Path) -> Manual:
    """Parse the examples of the manual at ``path``

    Raises ManualFormatError for a layout violation: a tab other than the two
    known ones, a code block outside a tab or in the wrong language, a
    ``text`` block that does not follow a code block, an unknown control key,
    an example that lacks a tab or a code block, or an unclosed fence.
    """
    return _Parser(Path(path)).run()


# The label, the dots or blanks that align the value, then the time. Only the
# time is replaced, so other values on the line stay comparable.
_TIME = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
_TIME_FIELDS = (
    # t.info: " | Creation time: ......... TIME"
    re.compile(rf"((?:Creation|Modification) time:[ .]*){_TIME}"),
    # t.info -g: creation_time='TIME'
    re.compile(rf"((?:creation|modification)_time=')({_TIME})(')"),
    # t.info "Command history": the " | # TIME" line of every command
    re.compile(rf"^( \| # ){_TIME}", re.MULTILINE),
)

_REGISTER = re.compile(r"(\b\w+_map_register_)[0-9a-f]{32}\b")


def normalize(text: str, context: NormalizeContext) -> str:
    """Replace what changes from run to run by the fixed values of a manual

    Replaced, each with its reason:

    - the GRASS database path ``context.database``: a pytest tmp_path differs
      every run, the manual shows ``/home/user/grassdata``;
    - the user name ``context.user`` in the creator fields of ``t.info``
      (``Creator: ...``) and ``t.info -g`` (``creator=``) only: the name of
      whoever runs the test, and a blind replace would hit any text that
      contains it, a user called ``a`` for instance;
    - the creation and modification time of a space time dataset as ``t.info``
      and ``t.info -g`` print them, and the time stamps of its command history:
      the time of the run. Only the time is replaced, not the rest of its line.

    - the hex part of the register table name (``raster_map_register_<hex>``,
      likewise ``raster3d_``, ``vector_``) that ``t.info`` prints: it is a
      new uuid4 for every dataset. The type prefix and the rest of the line
      stay comparable.

    The time rules also cover single maps, whose ``t.info`` prints the same
    ``Creation time:`` and ``creation_time=`` lines (base.py). Not covered
    because none of the pilot tools prints them: the creator and time columns
    of ``t.list`` (unlabelled).
    """
    if context.database:
        text = text.replace(context.database, FIXED_DATABASE)
    user = re.escape(context.user)
    text = re.sub(rf"(Creator:[ .]*){user}(?=\s|$)", rf"\g<1>{FIXED_USER}", text)
    text = re.sub(rf"(?m)^(creator=){user}$", rf"\g<1>{FIXED_USER}", text)
    text = _TIME_FIELDS[0].sub(rf"\g<1>{FIXED_TIME}", text)
    text = _TIME_FIELDS[1].sub(rf"\g<1>{FIXED_TIME}\g<3>", text)
    text = _TIME_FIELDS[2].sub(rf"\g<1>{FIXED_TIME}", text)
    return _REGISTER.sub(rf"\g<1>{FIXED_REGISTER}", text)
