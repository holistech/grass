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
``## EXAMPLES`` names the coordinate system the examples need.

``<!-- example: shell-only -->`` as the first line after a ``###`` heading
makes the example one of a catalog, such as the expressions of an algebra
with their results: it has the ``Command line`` tab only. Elsewhere the
comment is an error, and every other example needs both tabs.

``run_manual`` runs the blocks of one tab, ``check_manual`` also compares the
shown output and the figures. Which options the examples show and whether the
``.html`` agrees is the business of ``manual_coverage``.
"""

from __future__ import annotations

import ast
import difflib
import getpass
import json
import os
import re
import shlex
import signal
import struct
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import grass.script as gs

from . import postgresql
from .versions import downgrade_to_version_2

TABS = {"Command line": "shell", "Python (grass.tools)": "python"}
LANGUAGES = {"shell": "sh", "python": "python"}
INDENT = "    "
FIXED_TIME = "2026-11-01 12:00:00"
FIXED_DATABASE = "/home/user/grassdata"
FIXED_USER = "user"
# Any 32 hex digits; the real name carries a uuid4 that differs every run.
FIXED_REGISTER = "0" * 32

CONTROL_KEYS = ("requires", "not-run", "reason")
SHELL_ONLY = "shell-only"
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
    """One variant ("shell" or "python") of a ``###`` example

    ``shell_only`` marks an example of a catalog, which has no python variant.
    """

    title: str
    variant: str
    blocks: tuple[Block, ...]
    images: tuple[str, ...]
    shell_only: bool = False


@dataclass(frozen=True)
class Manual:
    """A parsed manual

    ``examples`` follows the document: for each ``###`` the shell variant
    first, then the python variant, which a shell-only example does not have.
    ``images`` lists every image of the file,
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
    shell_only: bool = False


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
        # True from a ### heading to the next line that is not blank.
        self.after_heading = False
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
        after_heading = self.after_heading
        self.after_heading = after_heading and not text.strip()
        control = CONTROL.match(text)
        if control and SHELL_ONLY in dict(_words(self.path, number, control[1])):
            self.shell_only(number, text, control[1], after_heading)
        elif PROJECT.match(text):
            if self.section is not None:
                self.fail(number, "example-project belongs directly under ## EXAMPLES")
            self.project = _project(self.path, number, PROJECT.match(text).group(1))
        elif text.startswith("### "):
            self.section = _Section(text[4:].strip(), number)
            self.sections.append(self.section)
            self.variant = self.last = None
            self.after_heading = True
        elif self.section is None:
            return
        elif TAB.match(text):
            self.tab(number, TAB.match(text).group(1))
        elif control:
            self.control(number, text)
        elif text.strip():
            if not text.startswith(INDENT):
                self.variant = None
            elif self.pending is not None:
                self.fail(number, "control comment without a code block")
            self.last = None

    def shell_only(self, number: int, text: str, body: str, after_heading: bool):
        if (
            self.section is None
            or not after_heading
            or text != text.lstrip()
            or body.split() != [SHELL_ONLY]
        ):
            self.fail(
                number,
                f"<!-- example: {SHELL_ONLY} --> stands alone on the first line "
                "after the ### heading",
            )
        self.section.shell_only = True

    def tab(self, number: int, label: str):
        if label not in TABS:
            self.fail(number, f"unknown tab {label!r}, known: {tuple(TABS)}")
        if TABS[label] == "python" and self.section.shell_only:
            self.fail(number, f"a {SHELL_ONLY} example has no tab {label!r}")
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
                if item.shell_only and name == "python":
                    continue
                where = f"{self.tool}, example {item.title!r}: tab {label!r}"
                if name not in item.seen:
                    raise ManualFormatError(self.path, item.line, f"{where} is missing")
                if not item.blocks[name]:
                    raise ManualFormatError(
                        self.path, item.line, f"{where} has no code"
                    )
                yield Example(
                    item.title,
                    name,
                    tuple(item.blocks[name]),
                    tuple(item.images),
                    item.shell_only,
                )


def parse_manual(path: Path) -> Manual:
    """Parse the examples of the manual at ``path``

    Raises ManualFormatError for a layout violation: a tab other than the two
    known ones, a code block outside a tab or in the wrong language, a
    ``text`` block that does not follow a code block, an unknown control key,
    an example that lacks a tab or a code block, a shell-only comment that is
    not the first line after its heading or an example with it that has a
    Python tab, or an unclosed fence.
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
      the time of the run; only the time, not the rest of its line;
    - the hex part of the register table name (``raster_map_register_<hex>``,
      likewise ``raster3d_``, ``vector_``) that ``t.info`` prints: it is a
      new uuid4 for every dataset. The type prefix and the rest of the line
      stay comparable.

    The time rules also cover single maps, whose ``t.info`` prints the same
    ``Creation time:`` and ``creation_time=`` lines (base.py). Not covered:
    the creator and time columns of ``t.list``, which have no label to
    anchor a rule.
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


# The examples work on small regions (at most 20 x 20 cells, a rule of the
# manuals), so the limit is not a speed check; it stops a hanging command, such
# as one waiting for input. The Python tab gets the sum for all its blocks.
# pytest-timeout (300 s for the repository) can end a long test first.
BLOCK_SECONDS = 120
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# Tokens that end a shell command, and those whose next word is a file name.
_SHELL_PUNCTUATION = ";&|()<>\n"
_REDIRECT = set("<>")
# Reserved words and the like that bash takes before a command; the word after
# them is the command.
_COMMAND_PREFIXES = frozenset(
    {"!", "{", "do", "elif", "else", "if", "then", "time", "until", "while"}
)
# The characters before which a # starts a comment in bash: blanks and the
# characters that end a word.
_WORD_ENDS = " \t\n;&|()<>"
_HERE_DOCUMENT = re.compile(r"<<(-?)[ \t]*(?:'([^']*)'|\"([^\"]*)\"|([^\s;&|()<>]+))")

# Runs the blocks of a Python tab one after the other in one namespace, so a
# later block uses what an earlier one made (tools = Tools()). The separator
# line between two blocks, on stdout and on stderr, splits the output per block.
# A block that raises ends the process with 1 after its traceback.
_DRIVER = """
import json, os, sys, traceback
from types import SimpleNamespace

job = json.load(sys.stdin)
namespace = {"__name__": "__main__"}
for index, block in enumerate(job["blocks"]):
    if index:
        print(job["separator"], flush=True)
        print(job["separator"], file=sys.stderr, flush=True)
    if block["old_database"]:
        from grass.temporal.testing.versions import downgrade_to_version_2

        downgrade_to_version_2(SimpleNamespace(env=dict(os.environ)))
    try:
        exec(compile(block["code"], block["name"], "exec"), namespace)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
"""


@dataclass(frozen=True)
class BlockResult:
    """What running one code block gave

    ``skipped`` is None for a block that ran, otherwise the reason why it did
    not run; a skipped block has empty output and return code 0. A return
    code below 0 is the signal that stopped a block after BLOCK_SECONDS.
    """

    block: Block
    stdout: str
    stderr: str
    returncode: int
    skipped: str | None = None


def _gdal_reason(driver: str) -> str | None:
    try:
        from osgeo import gdal  # noqa: PLC0415
    except ImportError:
        return f"requires=gdal:{driver}: the GDAL Python bindings are missing"
    if gdal.GetDriverByName(driver) is None:
        return f"requires=gdal:{driver}: GDAL has no driver {driver!r}"
    return None


def _skip_reason(block: Block) -> str | None:
    """Why the block does not run here, or None if it runs"""
    control = block.control
    if "not-run" in control:
        return f"not-run: {control['reason']}"
    need = control.get("requires", "")
    if need == "postgresql" and postgresql.server_string() is None:
        return (
            f"requires=postgresql: {postgresql.SERVER_VARIABLE} "
            "names no PostgreSQL server"
        )
    if need.startswith("gdal:"):
        return _gdal_reason(need[len("gdal:") :])
    return None


def _run(arguments, *, env, cwd, seconds, stdin=None) -> tuple[int, str, str]:
    """Run a process in a group of its own; kill the group after seconds

    As session.run_with_timeout, but with stdout kept. The whole group is
    killed, because a tool started below bash or python survives the kill of
    its parent alone.
    """
    process = subprocess.Popen(
        arguments,
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL if stdin is None else subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(stdin, timeout=seconds)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        stderr += f"\nStopped after {seconds} s.\n"
        return -signal.SIGKILL, stdout, stderr
    return process.returncode, stdout, stderr


def _after_failure(block: Block) -> str:
    return f"not run: the block at line {block.line} failed"


def _run_shell(blocks: list[Block], session, workdir: Path) -> list[BlockResult]:
    results = []
    failed = None
    for block in blocks:
        reason = failed or _skip_reason(block)
        if reason:
            results.append(BlockResult(block, "", "", 0, reason))
            continue
        if block.control.get("requires") == "old-database":
            downgrade_to_version_2(session)
        returncode, stdout, stderr = _run(
            ["bash", "-e", "-o", "pipefail", "-c", block.code],
            env=session.env,
            cwd=workdir,
            seconds=BLOCK_SECONDS,
        )
        results.append(BlockResult(block, stdout, stderr, returncode))
        if returncode:
            failed = _after_failure(block)
    return results


def _run_python(
    blocks: list[Block], session, workdir: Path, path: Path
) -> list[BlockResult]:
    reasons = [_skip_reason(block) for block in blocks]
    runnable = [
        block for block, reason in zip(blocks, reasons, strict=True) if reason is None
    ]
    ran = []
    if runnable:
        separator = f"==== end of block {uuid.uuid4().hex} ===="
        job = {
            "separator": separator,
            "blocks": [
                {
                    "code": block.code,
                    "name": f"{path}:{block.line}",
                    "old_database": block.control.get("requires") == "old-database",
                }
                for block in runnable
            ],
        }
        # sys.executable, not a python3 from PATH: the interpreter of the test
        # has the packages the examples import. -u keeps the order of what
        # Python prints and what the tools it starts write to the same pipe.
        returncode, stdout, stderr = _run(
            [sys.executable, "-u", "-c", _DRIVER],
            env=session.env,
            cwd=workdir,
            seconds=BLOCK_SECONDS * len(runnable),
            stdin=json.dumps(job),
        )
        ran = _split_python(runnable, returncode, stdout, stderr, separator)
    results = []
    for block, reason in zip(blocks, reasons, strict=True):
        results.append(BlockResult(block, "", "", 0, reason) if reason else ran.pop(0))
    return results


def _split_python(runnable, returncode, stdout, stderr, separator):
    """Turn the output of the Python process into one result per block"""
    outs = stdout.split(separator + "\n")
    errs = stderr.split(separator + "\n")
    last = len(outs) - 1
    results = []
    for index, block in enumerate(runnable):
        if index < last:
            results.append(BlockResult(block, outs[index], errs[index], 0))
        elif index == last:
            err = errs[index] if index < len(errs) else ""
            results.append(BlockResult(block, outs[index], err, returncode))
        elif returncode:
            failed = _after_failure(runnable[last])
            results.append(BlockResult(block, "", "", 0, failed))
        else:
            # A block that calls sys.exit(0) ends the process early.
            ended = "The Python process ended before this block ran.\n"
            results.append(BlockResult(block, "", ended, 1))
    return results


def _variant_blocks(manual: Manual, variant: str) -> list[tuple[Example, Block]]:
    if variant not in TABS.values():
        msg = f"unknown variant {variant!r}, known: {tuple(TABS.values())}"
        raise ValueError(msg)
    return [
        (example, block)
        for example in manual.examples
        if example.variant == variant
        for block in example.blocks
    ]


def run_manual(
    manual: Manual, variant: str, session, workdir: Path
) -> list[BlockResult]:
    """Run the blocks of one tab ("shell" or "python") of all examples

    The examples run in the order of the document, in the project of the
    session and with workdir (created if needed) as the current directory, so
    a later example can use the maps and files of an earlier one. Each shell
    block runs in ``bash -e -o pipefail``; all Python blocks run in one
    Python process with a shared namespace. A block is skipped when its
    control comment says not-run or names a requirement that does not hold
    here; requires=old-database turns the temporal database into version 2
    before the block. After a failing block, the later ones are skipped.

    Returns one result per block, in the order of the document.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    blocks = [block for _, block in _variant_blocks(manual, variant)]
    if variant == "shell":
        return _run_shell(blocks, session, workdir)
    return _run_python(blocks, session, workdir, manual.path)


def _diff(shown: str, printed: str) -> str:
    lines = difflib.unified_diff(
        shown.splitlines(keepends=True),
        printed.splitlines(keepends=True),
        "shown in the manual",
        "printed by the run",
    )
    # A last line without its newline would run into the next diff line.
    return "".join(
        line if line.endswith("\n") else line + "\n\\ No newline at end\n"
        for line in lines
    )


def _bash_words(code: str) -> str:
    """Return the code without comments and without here document bodies

    As bash reads them: a # starts a comment only where a word starts and
    outside quotes, so an apostrophe in a comment is no quote; the body of a
    here document starts on the line after its << and ends at the line that
    is the delimiter alone (after leading tabs for <<-). The operator and
    the delimiter stay, as a redirection. A quote left open stays open, for
    shlex to reject.
    """
    out = []
    pending: list[tuple[str, bool]] = []
    quote = None
    word_start = True
    index = 0
    while index < len(code):
        char = code[index]
        if quote:
            if char == "\\" and quote == '"':
                out.append(code[index : index + 2])
                index += 2
                continue
            quote = None if char == quote else quote
        elif char == "\\":
            # A continued line joins two lines of one word or command; the
            # start of a word is that of the first line.
            out.append(code[index : index + 2])
            if code[index + 1 : index + 2] != "\n":
                word_start = False
            index += 2
            continue
        elif char in "'\"":
            quote = char
        elif char == "#" and word_start:
            end = code.find("\n", index)
            index = len(code) if end < 0 else end
            continue
        elif code.startswith("<<<", index):
            out.append("<<<")
            index += 3
            word_start = True
            continue
        elif match := _HERE_DOCUMENT.match(code, index):
            delimiter = next(word for word in match.groups()[1:] if word is not None)
            pending.append((delimiter, bool(match.group(1))))
            out.append(match.group(0))
            index = match.end()
            word_start = False
            continue
        elif char == "\n" and pending:
            out.append(char)
            index = _after_here_documents(code, index + 1, pending)
            pending = []
            word_start = True
            continue
        out.append(char)
        word_start = quote is None and char in _WORD_ENDS
        index += 1
    return "".join(out)


def _after_here_documents(code: str, index: int, pending) -> int:
    """The index after the bodies of the here documents that start at index"""
    for delimiter, strip_tabs in pending:
        while index < len(code):
            end = code.find("\n", index)
            end = len(code) if end < 0 else end
            line = code[index:end]
            index = end + 1
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
    return index


def shell_calls(code: str, name: str) -> list[list[str]]:
    """Return the words after ``name`` of each shell command that runs ``name``

    Understands what the examples use: lines continued with a backslash,
    quotes, comments, here documents (their body is left out), commands
    joined by ``|``, ``;``, ``&&`` and ``||``, redirections (their file name
    is left out), variable assignments in front of a command and the words
    after which bash expects a command (``do``, ``then``, ``else``,
    ``elif``, ``if``, ``while``, ``until``, ``!``, ``{``, ``time``).

    Not understood: a command substitution within double quotes or with
    backquotes, functions, aliases, ``eval`` and a tool name in a variable;
    a command in one of them may be missed. A command after ``$(`` counts.
    A shift ``<<`` in arithmetic is taken for a here document. ANSI-C quotes
    with an escaped quote (``$'it\\'s'``) and other quoting that shlex cannot
    split raise ValueError.
    """
    lexer = shlex.shlex(
        _bash_words(code).replace("\\\n", ""),
        posix=True,
        punctuation_chars=_SHELL_PUNCTUATION,
    )
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    # _bash_words has dropped the comments; shlex would also start one inside
    # a word, which bash does not.
    lexer.commenters = ""
    commands: list[list[str]] = [[]]
    skip_word = False
    for token in lexer:
        if token and set(token) <= set(_SHELL_PUNCTUATION):
            if set(token) & _REDIRECT:
                skip_word = True
            else:
                commands.append([])
            continue
        if skip_word:
            skip_word = False
            continue
        commands[-1].append(token)
    calls = []
    for words in commands:
        while words and (
            words[0] in _COMMAND_PREFIXES
            or ("=" in words[0] and not words[0].startswith("-"))
        ):
            words = words[1:]
        if words and words[0] == name:
            calls.append(words[1:])
    return calls


def block_shell_calls(path: Path, block: Block, name: str) -> list[list[str]]:
    """Return shell_calls of a block of the manual at path

    Raises ManualFormatError with the file and the line of the block where
    shell_calls cannot split the code into words.
    """
    try:
        return shell_calls(block.code, name)
    except ValueError as error:
        raise ManualFormatError(
            path, block.line, f"cannot split the shell block into words: {error}"
        ) from None


def python_calls(code: str, name: str) -> list[dict[str, object]]:
    """Return the keywords of each call ``<object>.<name with _>(...)``

    ``tools.t_create(output="a")`` is a call of ``t.create``. A keyword whose
    value is not a literal maps to None; ``**kwargs`` is left out.
    """
    attribute = name.replace(".", "_")
    calls = []
    for node in ast.walk(ast.parse(code)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == attribute
        ):
            continue
        keywords: dict[str, object] = {}
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            try:
                keywords[keyword.arg] = ast.literal_eval(keyword.value)
            except ValueError:
                keywords[keyword.arg] = None
        calls.append(keywords)
    return calls


def _image_size(
    path: Path, results: list[BlockResult], image: str
) -> tuple[int, int] | None:
    """The width and height that the d.mon call writing image asks for"""
    for result in results:
        block = result.block
        if block.language == "sh":
            calls = [
                dict(word.split("=", 1) for word in words if "=" in word)
                for words in block_shell_calls(path, block, "d.mon")
            ]
        else:
            calls = python_calls(block.code, "d.mon")
        for call in calls:
            if call.get("output") == image:
                try:
                    return int(call["width"]), int(call["height"])
                except (KeyError, TypeError, ValueError):
                    msg = (
                        f"the d.mon call that writes {image} gives no width and height"
                    )
                    raise AssertionError(msg) from None
    return None


def _check_image(
    manual: Manual, where: str, results: list[BlockResult], image: str, workdir: Path
):
    size = _image_size(manual.path, results, image)
    if size is None:
        msg = f"{where}: no d.mon call of a block that ran writes {image}"
        raise AssertionError(msg)
    path = workdir / image
    if not path.is_file():
        msg = f"{where}: the image {image} does not exist after the run"
        raise AssertionError(msg)
    head = path.read_bytes()[:24]
    if not head.startswith(PNG_SIGNATURE) or head[12:16] != b"IHDR":
        msg = f"{where}: the image {image} is not a PNG"
        raise AssertionError(msg)
    width, height = struct.unpack(">II", head[16:24])
    if (width, height) != size:
        msg = (
            f"{where}: the image {image} is {width} x {height} pixels, "
            f"the d.mon call asks for {size[0]} x {size[1]}"
        )
        raise AssertionError(msg)


def check_manual(manual: Manual, variant: str, session, workdir: Path) -> None:
    """Run one tab of the examples and compare what they show with the run

    Raises AssertionError with the manual, the example and the line of the
    block when a block fails (with its stderr), when its stdout differs from
    the shown output after ``normalize`` (with a unified diff), or when an
    image of an example is missing, is no PNG or has another size than its
    d.mon call asks for, and ManualFormatError when shell_calls cannot split
    a shell block that ran into words. Each tab has to make the images of
    its examples itself, in workdir. The size comes from the width and height of the
    ``d.mon`` call (``output=``, ``width=``, ``height=``, or the keywords of
    ``tools.d_mon(...)``), so the manual states it where the reader sees it.
    """
    workdir = Path(workdir)
    results = run_manual(manual, variant, session, workdir)
    context = NormalizeContext(
        database=gs.gisenv(env=session.env)["GISDBASE"], user=getpass.getuser()
    )
    examples = _variant_blocks(manual, variant)
    for (example, block), result in zip(examples, results, strict=True):
        if result.skipped:
            continue
        where = (
            f"{manual.path}: example {example.title!r}, {variant} tab, "
            f"block at line {block.line}"
        )
        if result.returncode:
            msg = (
                f"{where} ended with return code {result.returncode}:\n{result.stderr}"
            )
            raise AssertionError(msg)
        if block.shown_output is None:
            continue
        shown = normalize(block.shown_output, context)
        printed = normalize(result.stdout, context)
        if shown != printed:
            diff = _diff(shown, printed)
            msg = f"{where}: the output differs from the shown one\n{diff}"
            raise AssertionError(msg)
    for example in manual.examples:
        if example.variant != variant:
            continue
        ran = [
            result
            for (owner, _), result in zip(examples, results, strict=True)
            if owner is example and not result.skipped
        ]
        where = f"{manual.path}: example {example.title!r}, {variant} tab"
        for image in example.images:
            _check_image(manual, where, ran, image, workdir)
