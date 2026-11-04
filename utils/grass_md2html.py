#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Generate the HTML page of a tool manual from its Markdown source

The Markdown file is the source of a manual; the HTML file beside it is the
fragment that utils/mkhtml.py turns into a page (no head or foot, headings as
<h2>/<h3>, code in <div class="code"><pre>). This script writes the fragment,
so that only the Markdown file is edited by hand.

Usage::

    python3 utils/grass_md2html.py FILE.md...          # write FILE.html
    python3 utils/grass_md2html.py --check FILE.md...  # compare, write nothing

With --check, each FILE.md whose FILE.html differs from the generated text is
printed, and the exit code is 1. Markdown outside the supported subset ends
the script with exit code 2 and the file and line in the message.

The script understands the subset of Markdown that the temporal manuals use,
and refuses everything else with UnsupportedMarkdown instead of passing it
through, so that a construct it does not know cannot silently give an HTML
page that says something else. Within the subset, it reads Markdown as
CommonMark does, with the tables of GitHub Flavored Markdown and the tabs of
MkDocs Material. MkDocs reads Markdown with Python-Markdown, which differs
from CommonMark: it counts the content of a list item only from an
indentation of four blanks on, so a code block indented by two or three
blanks under a list item is part of the item for CommonMark and not for
MkDocs. Content of a list item is therefore indented by four blanks per
level, and any other indentation is refused. The subset:

- YAML front matter with ``description`` and ``index`` (introduction pages),
  written as the ``<!-- meta page ... -->`` comments of utils/mkhtml.py; the
  page must start with a level 1 heading that repeats the description, as
  mkhtml.py makes the title of the page from it, and which is left out;
- headings of level 2 to 4 (level 1 only as that title), paragraphs, hard
  line breaks (two blanks);
- bullet and ordered lists, nested by indentation, with paragraphs and code
  blocks in an item;
- tables with a header row and without column alignment;
- fenced code blocks with any language, rendered alike;
- tabs of MkDocs Material (``=== "Command line"``), rendered as a labelled
  paragraph followed by the content of the tab, as the HTML pages have no
  tabs;
- HTML comments on a line of their own, which are dropped (markdownlint
  switches and the control comments of the manual tests);
- inline: code spans, ``*emphasis*``, ``**bold**``, links (``.md`` targets
  become ``.html``), autolinks, images and backslash escapes.

The output is ASCII: other characters become HTML entities. Each line of
text keeps the line break of its Markdown line, so that a change of the
Markdown file changes the same lines of the HTML file. Blanks at the end of a
line are dropped, also in code: the trailing-whitespace hook of pre-commit
would drop them from the HTML file and make it differ from this output.
"""

import argparse
import html
import re
import string
import sys
import unicodedata
from html.entities import codepoint2name
from itertools import starmap
from pathlib import Path

FENCE = re.compile(r"^```([^`\s]*)$")
HEADING = re.compile(r"^(#{1,6})(?: +(.*?))?$")
TAB = re.compile(r'^=== "([^"]+)"$')
LIST_ITEM = re.compile(r"^(?:([-*+])|(\d{1,9})([.)]))( +|$)(.*)$")
COMMENT = re.compile(r"^<!--.*-->$")
TABLE_SEPARATOR = re.compile(r"^\|(?: *-+ *\|)+$")
# A separator row of a table in any form that GitHub Flavored Markdown
# accepts, also without the outer pipes.
TABLE_SEPARATOR_ANY = re.compile(r"^\|? *:?-+:? *(?:\| *:?-+:? *)+\|?$")
THEMATIC_BREAK = re.compile(r"^(?:(?:\* *){3,}|(?:- *){3,}|(?:_ *){3,})$")
SETEXT_UNDERLINE = re.compile(r"^(?:=+|-+) *$")
REFERENCE_DEFINITION = re.compile(r"^\[[^\]]+\]:")
AUTOLINK = re.compile(r"<(https?://[^\s<>]+)>")
ENTITY = re.compile(r"&(?:#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
LINK_TARGET = re.compile(r"\(([^\s()]+)\)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FRONT_MATTER_KEYS = ("description", "index")
ASCII_PUNCTUATION = frozenset(string.punctuation)
# Marks a hard line break in the text of a paragraph until it is rendered.
HARD_BREAK = "\0"


class UnsupportedMarkdown(Exception):
    """Markdown outside the subset that the generator understands"""

    def __init__(self, path: str, line: int, message: str):
        super().__init__(f"{path}:{line}: {message}")
        self.path = path
        self.line = line


def convert(markdown: str, path: str = "<string>") -> str:
    """Return the HTML fragment of a manual written in Markdown

    Raises UnsupportedMarkdown for Markdown outside the subset described in
    the module docstring; *path* only names the file in its message.
    """
    lines = list(enumerate(markdown.split("\n"), start=1))
    meta, lines = _front_matter(lines, path)
    parser = _BlockParser(path, title_allowed=bool(meta))
    blocks = parser.parse(lines)
    if meta:
        blocks = _drop_title(blocks, meta, path)
    chunks = [f"<!-- meta page {key}: {value} -->" for key, value in meta]
    if chunks:
        chunks = ["\n".join(chunks)]
    chunks.extend(_render_blocks(blocks, path, bare_first=True))
    return "\n\n".join(chunks) + "\n"


def _front_matter(lines, path):
    """The keys of the YAML front matter in their order, and the lines after it"""
    if not lines or lines[0][1] != "---":
        return [], lines
    meta = []
    for index, (number, text) in enumerate(lines[1:], start=1):
        if text == "---":
            return meta, lines[index + 1 :]
        key, colon, value = text.partition(":")
        if not colon or key not in FRONT_MATTER_KEYS or not value.strip():
            raise UnsupportedMarkdown(
                path,
                number,
                f"front matter line {text!r}: only 'key: value' with the keys "
                f"{', '.join(FRONT_MATTER_KEYS)}",
            )
        meta.append((key, value.strip()))
    raise UnsupportedMarkdown(path, lines[0][0], "front matter is not closed by ---")


def _drop_title(blocks, meta, path):
    """The blocks without the level 1 heading, which must be the description

    utils/mkhtml.py makes the title of the page from the description; a
    heading with another text would be lost in the HTML page.
    """
    description = dict(meta).get("description")
    first = next((block for block in blocks if block[0] != "comment"), None)
    if (
        first is None
        or first[0] != "heading"
        or first[1] != 1
        or first[2] != description
    ):
        line = first[-1] if first else 1
        raise UnsupportedMarkdown(
            path,
            line,
            "a page with front matter must start with the level 1 heading "
            f"{description!r}, the description",
        )
    return [block for block in blocks if block is not first]


class _BlockParser:
    """Splits lines into blocks; each block is a tuple whose last item is
    the number of its first line

    ("heading", level, text, line), ("paragraph", [(line, text)], line),
    ("code", [text], line), ("tab", label, [block], line),
    ("list", ordered, start, [[block]], line), ("table", [row], line)
    with each row a list of (line, cell text), ("comment", line).
    """

    def __init__(self, path, title_allowed):
        self.path = path
        # Whether the page may start with a level 1 heading, its title.
        self.title_allowed = title_allowed
        # How many containers (page, list item, tab) are open.
        self.depth = 0

    def error(self, line, message):
        return UnsupportedMarkdown(self.path, line, message)

    def parse(self, lines):
        """The blocks of lines whose container indentation is removed"""
        self.depth += 1
        try:
            return self._parse(lines)
        finally:
            self.depth -= 1

    def _parse(self, lines):
        blocks = []
        index = 0
        while index < len(lines):
            number, text = lines[index]
            if not text.strip():
                index += 1
                continue
            if "\t" in text:
                raise self.error(number, "a tab character outside a code block")
            # As in CommonMark, a block may start up to three blanks right of
            # its container; four make an indented code block.
            indent = len(text) - len(text.lstrip(" "))
            if indent > 3:
                raise self.error(
                    number,
                    "a block indented by four or more blanks (an indented code "
                    "block is not supported; use a fence)",
                )
            index = self._block(lines, index, blocks, indent)
        return blocks

    def _block(self, lines, index, blocks, indent):
        number, text = lines[index][0], lines[index][1][indent:]
        if text.startswith("<!--"):
            if not COMMENT.match(text.rstrip()):
                raise self.error(
                    number, "an HTML comment must be a line of its own, closed on it"
                )
            blocks.append(("comment", number))
            return index + 1
        if text.startswith("```"):
            return self._code(lines, index, blocks, indent)
        refused = _refused_block(text.rstrip())
        if refused:
            raise self.error(number, f"{refused} is not supported")
        if text.startswith("#"):
            heading = HEADING.match(text.rstrip())
            if not heading or not heading.group(2):
                raise self.error(number, f"a heading must be '# text': {text!r}")
            level = len(heading.group(1))
            if level > 4:
                raise self.error(number, f"heading level {level}; at most 4")
            if level == 1 and not (
                self.title_allowed
                and self.depth == 1
                and all(block[0] == "comment" for block in blocks)
            ):
                # utils/mkhtml.py gives the page its title; a second one in
                # the text would be wrong.
                raise self.error(
                    number,
                    "a level 1 heading, allowed only as the first block of a page "
                    "with front matter",
                )
            blocks.append(("heading", level, heading.group(2), number))
            return index + 1
        if text.startswith("==="):
            return self._tab(lines, index, blocks, indent)
        if LIST_ITEM.match(text):
            return self._list(lines, index, blocks)
        if text.startswith("|"):
            return self._table(lines, index, blocks)
        return self._paragraph(lines, index, blocks)

    def _code(self, lines, index, blocks, indent):
        number, text = lines[index][0], lines[index][1][indent:]
        if not FENCE.match(text.rstrip()):
            raise self.error(
                number, f"a code fence must be ``` and a language: {text!r}"
            )
        closing = " " * indent + "```"
        body = []
        for row_number, row in lines[index + 1 :]:
            if row.rstrip() == closing:
                blocks.append(("code", body, number))
                return index + len(body) + 2
            if row.lstrip(" ").startswith("```"):
                raise self.error(
                    row_number,
                    "a code fence inside a code block, or a closing fence at "
                    "another indentation than its opening fence",
                )
            # CommonMark removes the indentation of the fence from each line.
            blank = len(row) - len(row.lstrip(" "))
            body.append(row[min(blank, indent) :])
        raise self.error(
            number,
            "code block not closed: no ``` at the indentation of its opening fence",
        )

    def _tab(self, lines, index, blocks, indent):
        number, text = lines[index][0], lines[index][1][indent:]
        tab = TAB.match(text.rstrip())
        if not tab:
            raise self.error(number, f'a tab must be === "label": {text!r}')
        content, end = _indented(lines, index + 1, indent + 4)
        if not any(row.strip() for _, row in content):
            raise self.error(number, "a tab without content indented by 4 blanks")
        blocks.append(("tab", tab.group(1), self.parse(content), number))
        return end

    def _list(self, lines, index, blocks):
        number, text = lines[index]
        first = LIST_ITEM.match(text.lstrip(" "))
        bullet = first.group(1)
        delimiter = first.group(3)
        items = []
        while index < len(lines):
            item_number, item_text = lines[index]
            item = LIST_ITEM.match(item_text.lstrip(" "))
            if (
                not item
                or len(item_text) - len(item_text.lstrip(" ")) > 3
                or item.group(1) != bullet
                or item.group(3) != delimiter
            ):
                break
            if not item.group(5).strip():
                raise self.error(item_number, "an empty list item")
            width = len(item_text) - len(item.group(5))
            if len(item.group(4)) > 4:
                raise self.error(
                    item_number, "more than four blanks after a list marker"
                )
            content, end = _indented(lines, index + 1, width)
            self._refuse_misindented_content(lines, index + 1, item_text)
            self._refuse_lazy_lines(lines, end)
            items.append(self.parse([(item_number, item.group(5)), *content]))
            index = end
            # A blank line between two items keeps them in one list.
            while index < len(lines) and not lines[index][1].strip():
                index += 1
        start = 1 if bullet else int(first.group(2))
        blocks.append(("list", bullet is None, start, items, number))
        return index

    def _refuse_misindented_content(self, lines, index, item_text):
        """Refuse content of a list item that is not indented by a multiple
        of four blanks right of the marker in *item_text*

        The item reaches to the first line that is not blank and not indented
        deeper than the marker, as only such lines can be read as its content
        by one of the two parsers.

        Python-Markdown (MkDocs) counts the content of a list item only from
        four blanks on, CommonMark from the width of the marker; they read
        any other indentation as different blocks. Lines inside a fenced
        code block are code and not checked, only the fence lines are. A line
        that continues the paragraph above it is not checked either: both
        parsers join it to the paragraph whatever its indentation, and the
        manuals wrap the text of an item at the width of its marker. The
        exception is a continuation line that starts with a number other
        than 1 and a dot: CommonMark joins it to the paragraph, Python-Markdown
        starts a new list item, so it is refused.
        """
        base = len(item_text) - len(item_text.lstrip(" "))
        in_fence = False
        # The item text itself is the first line of a paragraph.
        in_paragraph = True
        for number, text in lines[index:]:
            if not text.strip():
                in_paragraph = False
                continue
            relative = len(text) - len(text.lstrip(" ")) - base
            if relative <= 0:
                break
            stripped = text.lstrip(" ")
            is_fence = stripped.startswith("```")
            if in_fence and not is_fence:
                continue
            if is_fence:
                in_fence = not in_fence
            marker = LIST_ITEM.match(stripped)
            if (
                in_paragraph
                and not is_fence
                and marker
                and marker.group(3) == "."
                and marker.group(2) != "1"
            ):
                # CommonMark joins "2. x" to the paragraph above, as only the
                # number 1 interrupts one; Python-Markdown starts a list item.
                raise self.error(
                    number,
                    "a wrapped line must not start with a number and a dot "
                    "(Python-Markdown reads it as a list item); reflow the text",
                )
            # As in _starts_block, only a bullet or the number 1 interrupts a
            # paragraph; "1900) * 12" wrapped to a line start does not.
            continues = (
                in_paragraph
                and not is_fence
                and not (marker and marker.group(2) in {None, "1"})
            )
            in_paragraph = not is_fence
            if relative % 4 and not continues:
                raise self.error(
                    number,
                    f"list content must be indented by 4 spaces per level, "
                    f"not by {relative} right of the list marker",
                )

    def _refuse_lazy_lines(self, lines, end):
        """A line right after a list item that is less indented than its
        content continues the item for CommonMark (a lazy line) and starts a
        paragraph for others; the meaning is not clear, so it is refused"""
        if end < len(lines) and end > 0:
            number, text = lines[end]
            if (
                lines[end - 1][1].strip()
                and text.strip()
                and not LIST_ITEM.match(text.lstrip(" "))
            ):
                raise self.error(
                    number,
                    "a line after a list item that is less indented than the item "
                    "text; indent it, or separate it by a blank line",
                )

    def _table(self, lines, index, blocks):
        number = lines[index][0]
        rows = []
        while index < len(lines) and lines[index][1].lstrip(" ").startswith("|"):
            rows.append((lines[index][0], lines[index][1].lstrip(" ")))
            index += 1
        if len(rows) < 2 or not TABLE_SEPARATOR.match(rows[1][1].rstrip()):
            raise self.error(
                number,
                "a table needs a header row and a separator row of dashes "
                "(column alignment is not supported)",
            )
        if index < len(lines) and lines[index][1].strip():
            # GitHub Flavored Markdown continues the table with this line.
            raise self.error(
                lines[index][0],
                "a line right after a table that does not start with |; "
                "separate it by a blank line",
            )
        cells = list(starmap(self._cells, rows))
        width = len(cells[0])
        for (row_number, _), row in zip(rows, cells, strict=True):
            if len(row) != width:
                raise self.error(
                    row_number, f"{len(row)} cells, the header has {width}"
                )
        blocks.append(("table", [cells[0], *cells[2:]], number))
        return index

    def _cells(self, number, text):
        """The cells of a table row; an escaped pipe is a pipe of the cell,
        also in a code span, as in GitHub Flavored Markdown"""
        text = text.rstrip()
        if not text.endswith("|") or text.endswith("\\|"):
            raise self.error(number, "a table row must end with |")
        cells = []
        current = []
        position = 1
        while position < len(text):
            char = text[position]
            if text.startswith("\\|", position):
                current.append("|")
                position += 2
                continue
            if char == "\\" and position + 1 < len(text):
                current.append(text[position : position + 2])
                position += 2
                continue
            if char == "`":
                end = _code_span_end(text, position)
                if end is None:
                    raise self.error(number, "a code span is not closed in its cell")
                span = text[position:end]
                # GitHub ends the cell at this pipe, Python-Markdown does not.
                if re.search(r"(?<!\\)\|", span):
                    raise self.error(number, "a | in a code span of a cell; write \\|")
                current.append(span.replace("\\|", "|"))
                position = end
                continue
            if char == "|":
                cells.append((number, "".join(current).strip()))
                current = []
            else:
                current.append(char)
            position += 1
        return cells

    def _paragraph(self, lines, index, blocks):
        number = lines[index][0]
        rows = []
        while index < len(lines):
            row_number, text = lines[index]
            stripped = text.strip()
            if not stripped:
                break
            if rows and _starts_block(stripped):
                raise self.error(
                    row_number,
                    "a block starts inside a paragraph; separate it by a blank line",
                )
            rows.append((row_number, text))
            index += 1
        blocks.append(("paragraph", rows, number))
        return index


def _refused_block(text):
    """The name of a block of Markdown that the generator does not support,
    or None"""
    if THEMATIC_BREAK.match(text):
        return "a thematic break"
    if text.startswith("~~~"):
        return "a code fence of ~~~ (use ```)"
    if not text.startswith("|") and TABLE_SEPARATOR_ANY.match(text):
        return "a table without a | at the start of each row"
    if text.startswith(">"):
        return "a block quote"
    if REFERENCE_DEFINITION.match(text):
        return "a link reference definition"
    if text.startswith(("!!!", "???")):
        return "an admonition"
    return None


def _starts_block(stripped):
    """Whether a line inside a paragraph may be read as the start of a block

    Such a line is refused, as CommonMark and Python-Markdown (MkDocs) read
    it differently, or as it would make the paragraph a heading (a setext
    underline) or the header of a table (a separator row). An ordered list
    marker other than 1 starts no block in either, so a wrapped line such as
    "0. The first ..." stays text.
    """
    item = LIST_ITEM.match(stripped)
    return (
        stripped.startswith(("```", "~~~", "<!--", "===", "|", ">"))
        or HEADING.match(stripped) is not None
        or SETEXT_UNDERLINE.match(stripped) is not None
        or TABLE_SEPARATOR_ANY.match(stripped) is not None
        or THEMATIC_BREAK.match(stripped) is not None
        or (item is not None and item.group(2) in {None, "1"})
    )


def _indented(lines, index, width):
    """The lines from *index* on that are blank or indented by *width*,
    without that indentation, and the index after them

    Blank lines at the end belong to what follows.
    """
    content = []
    while index < len(lines):
        number, text = lines[index]
        if text.strip():
            if not text.startswith(" " * width):
                break
            content.append((number, text[width:]))
        else:
            content.append((number, ""))
        index += 1
    while content and not content[-1][1]:
        content.pop()
        index -= 1
    return content, index


def _code_span_end(text, start):
    """The index after the code span that opens at *start*, or None

    A code span closes with a run of as many backticks as opened it.
    """
    run = len(text[start:]) - len(text[start:].lstrip("`"))
    position = start + run
    while True:
        found = text.find("`" * run, position)
        if found < 0:
            return None
        end = found + run
        if end < len(text) and text[end] == "`":
            position = end + len(text[end:]) - len(text[end:].lstrip("`"))
            continue
        return end


def _render_blocks(blocks, path, bare_first):
    """The HTML of each block; a paragraph gets an opening <p> unless it
    follows a heading (or comes first and *bare_first* is set), as in the
    other GRASS manual pages"""
    chunks = []
    previous = None if bare_first else "other"
    for block in blocks:
        kind = block[0]
        if kind == "comment":
            continue
        if kind == "paragraph":
            text = _inline_lines(block[1], path)
            chunks.append(text if previous in {None, "heading"} else f"<p>\n{text}")
        elif kind == "heading":
            level, text, number = block[1:]
            content = _inline(text, path, number)
            chunks.append(f"<h{level}>{content}</h{level}>")
        elif kind == "code":
            chunks.append(_code_html(block[1]))
        elif kind == "tab":
            label, content = block[1], block[2]
            label_html = _inline(label, path, block[3])
            chunks.append(f"<p>{label_html}:</p>")
            chunks.extend(_render_blocks(content, path, bare_first=False))
        elif kind == "list":
            chunks.append(_list_html(block, path))
        elif kind == "table":
            chunks.append(_table_html(block[1], path))
        previous = kind
    return chunks


def _code_html(rows):
    text = "\n".join(_ascii(html.escape(row, quote=False)).rstrip() for row in rows)
    return f'<div class="code"><pre>\n{text}\n</pre></div>'


def _list_html(block, path):
    ordered, start, items = block[1], block[2], block[3]
    tag = "ol" if ordered else "ul"
    opening = f'<{tag} start="{start}">' if ordered and start != 1 else f"<{tag}>"
    rendered = [opening]
    for item in items:
        chunks = _render_blocks(item, path, bare_first=True)
        kinds = [block[0] for block in item if block[0] != "comment"]
        closing = "</li>" if kinds[-1:] in ([], ["paragraph"]) else "\n</li>"
        rendered.append("<li>" + "\n\n".join(chunks) + closing)
    rendered.append(f"</{tag}>")
    return "\n".join(rendered)


def _table_html(rows, path):
    rendered = ["<table>"]
    for index, row in enumerate(rows):
        tag = "th" if index == 0 else "td"
        cells = "".join(
            f"<{tag}>{_inline(text, path, number)}</{tag}>" for number, text in row
        )
        rendered.append(f"<tr>{cells}</tr>")
    rendered.append("</table>")
    return "\n".join(rendered)


def _inline_lines(rows, path):
    """The HTML of the lines of a paragraph, line by line"""
    for number, row in rows:
        if HARD_BREAK in row:
            raise UnsupportedMarkdown(path, number, "a NUL character")
    # Two blanks at the end of a line are a hard line break; at the end of
    # the paragraph they mean nothing, as in CommonMark.
    text = "\n".join(
        row.strip(" ")
        + (HARD_BREAK if row.endswith("  ") and index < len(rows) - 1 else "")
        for index, (_, row) in enumerate(rows)
    )
    return _inline(text, path, rows[0][0])


def _ascii(text):
    """The text with each character beyond ASCII as an HTML entity"""
    return "".join(
        char
        if ord(char) < 128
        else f"&{codepoint2name.get(ord(char), f'#{ord(char)}')};"
        for char in text
    )


def _inline(text, path, number):
    return _ascii(_Inline(text, path, number).render())


class _Inline:
    """Inline Markdown of one paragraph, heading or cell, rendered as HTML

    The emphasis follows the delimiter run rules of CommonMark for ``*``; an
    ``_`` that could open emphasis there is refused, because the manuals do
    not use it and it is easy to write by accident in a name.
    """

    def __init__(self, text, path, number):
        self.text = text
        self.path = path
        self.number = number
        # Each item is ["html", text] or
        # ["delim", char, count, opens, closes, count of the source run].
        self.items = []

    def error(self, position, message):
        line = self.number + self.text.count("\n", 0, position)
        return UnsupportedMarkdown(self.path, line, message)

    def render(self):
        self._scan()
        self._emphasis()
        return "".join(
            item[1] if item[0] == "html" else item[1] * item[2] for item in self.items
        )

    def _out(self, html_text):
        self.items.append(["html", html_text])

    def _scan(self):
        text = self.text
        position = 0
        while position < len(text):
            char = text[position]
            if char == HARD_BREAK:
                self._out("<br>")
                position += 1
            elif char == "`":
                position = self._code_span(position)
            elif char == "\\":
                position = self._escape(position)
            elif char == "*":
                position = self._delimiter(position)
            elif char == "_":
                position = self._underscore(position)
            elif char == "!" and text.startswith("![", position):
                position = self._image(position)
            elif char == "[":
                position = self._link(position)
            elif char == "<":
                position = self._angle(position)
            elif char == "&":
                if ENTITY.match(text, position):
                    raise self.error(
                        position, "an HTML entity in Markdown; write the character"
                    )
                self._out("&amp;")
                position += 1
            else:
                self._out(html.escape(char, quote=False))
                position += 1

    def _code_span(self, position):
        end = _code_span_end(self.text, position)
        if end is None:
            raise self.error(position, "a code span is not closed")
        run = len(self.text[position:]) - len(self.text[position:].lstrip("`"))
        content = self.text[position + run : end - run]
        if content.startswith(" ") and content.endswith(" ") and content.strip(" "):
            content = content[1:-1]
        self._out(f"<code>{html.escape(content, quote=False)}</code>")
        return end

    def _escape(self, position):
        following = self.text[position + 1 : position + 2]
        if following == "\n" or not following:
            raise self.error(
                position, "a backslash at the end of a line; use two blanks for a break"
            )
        if following in ASCII_PUNCTUATION:
            self._out(html.escape(following, quote=False))
            return position + 2
        self._out("\\")
        return position + 1

    def _flanking(self, start, end):
        """Whether the delimiter run from *start* to *end* can open and close"""
        # The start and the end of the text and a line break count as blanks.
        before = self.text[start - 1] if start > 0 else " "
        after = self.text[end] if end < len(self.text) else " "
        before, after = (
            " " if char == HARD_BREAK else char for char in (before, after)
        )
        left = not after.isspace() and (
            not _punctuation(after) or before.isspace() or _punctuation(before)
        )
        right = not before.isspace() and (
            not _punctuation(before) or after.isspace() or _punctuation(after)
        )
        return left, right, before, after

    def _delimiter(self, position):
        end = position
        while end < len(self.text) and self.text[end] == "*":
            end += 1
        left, right, _, _ = self._flanking(position, end)
        self.items.append(["delim", "*", end - position, left, right, end - position])
        return end

    def _underscore(self, position):
        end = position
        while end < len(self.text) and self.text[end] == "_":
            end += 1
        left, right, before, after = self._flanking(position, end)
        opens = left and (not right or _punctuation(before))
        closes = right and (not left or _punctuation(after))
        if opens or closes:
            raise self.error(
                position,
                "an _ that Markdown may read as emphasis; use * for emphasis or "
                "put the name in a code span",
            )
        self._out("_" * (end - position))
        return end

    def _bracket_end(self, position):
        """The index of the ] that closes the [ at *position*, or None"""
        depth = 0
        index = position
        while index < len(self.text):
            char = self.text[index]
            if char == "\\":
                index += 2
                continue
            if char == "`":
                end = _code_span_end(self.text, index)
                index = end if end is not None else index + 1
                continue
            if char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    return index
            index += 1
        return None

    def _target(self, close):
        """The link target after the ] at *close* and the index after it"""
        if not self.text.startswith("(", close + 1):
            return None, None
        target = LINK_TARGET.match(self.text, close + 1)
        if not target:
            raise self.error(
                close,
                "a link target must be (target) without blanks or a title",
            )
        return target.group(1), target.end()

    def _link(self, position):
        close = self._bracket_end(position)
        target, end = self._target(close) if close is not None else (None, None)
        if target is None:
            self._out("[")
            return position + 1
        label = _Inline(
            self.text[position + 1 : close], self.path, self._line(position)
        ).render()
        href = html.escape(_html_target(target))
        self._out(f'<a href="{href}">{label}</a>')
        return end

    def _image(self, position):
        close = self._bracket_end(position + 1)
        target, end = self._target(close) if close is not None else (None, None)
        if target is None:
            raise self.error(position, "an image must be ![text](file)")
        alt = _Inline(self.text[position + 2 : close], self.path, self._line(position))
        alt_text = alt.render()
        if "<" in alt_text:
            raise self.error(position, "the text of an image must be plain text")
        alt_text = alt_text.replace('"', "&quot;")
        self._out(f'<img src="{html.escape(target)}" alt="{alt_text}">')
        return end

    def _angle(self, position):
        autolink = AUTOLINK.match(self.text, position)
        if autolink:
            url = html.escape(autolink.group(1))
            self._out(f'<a href="{url}">{url}</a>')
            return autolink.end()
        following = self.text[position + 1 : position + 2]
        if following.isalpha() or following in {"/", "!", "?"}:
            raise self.error(
                position, "raw HTML in Markdown; put a literal <name> in a code span"
            )
        self._out("&lt;")
        return position + 1

    def _line(self, position):
        return self.number + self.text.count("\n", 0, position)

    def _emphasis(self):
        """Pair the * delimiters into <em> and <b>, as CommonMark does"""
        items = self.items
        index = 0
        while index < len(items):
            closer = items[index]
            if closer[0] != "delim" or not closer[4] or closer[2] == 0:
                index += 1
                continue
            opener_index = self._opener_for(index)
            if opener_index is None:
                if not closer[3]:
                    closer[:] = ["html", "*" * closer[2]]
                index += 1
                continue
            opener = items[opener_index]
            count = 2 if opener[2] >= 2 and closer[2] >= 2 else 1
            tag = "b" if count == 2 else "em"
            opener[2] -= count
            closer[2] -= count
            # Delimiters between the pair can no longer match anything.
            for between in items[opener_index + 1 : index]:
                if between[0] == "delim":
                    between[:] = ["html", "*" * between[2]]
            items.insert(opener_index + 1, ["html", f"<{tag}>"])
            index += 1
            items.insert(index, ["html", f"</{tag}>"])
            index += 1
            if closer[2] == 0:
                index += 1
        for item in items:
            if item[0] == "delim":
                item[:] = ["html", "*" * item[2]]

    def _opener_for(self, index):
        closer = self.items[index]
        for opener_index in range(index - 1, -1, -1):
            opener = self.items[opener_index]
            if opener[0] != "delim" or not opener[3] or opener[2] == 0:
                continue
            # The rule of 3 of CommonMark, on the lengths of the source runs.
            both = opener[4] or closer[3]
            if (
                both
                and (opener[5] + closer[5]) % 3 == 0
                and (opener[5] % 3 or closer[5] % 3)
            ):
                continue
            return opener_index
        return None


def _punctuation(char):
    return char in ASCII_PUNCTUATION or unicodedata.category(char)[0] in {"P", "S"}


def _html_target(target):
    """The target of a link in the HTML page: a manual is an .html file there"""
    if SCHEME.match(target):
        return target
    name, hash_mark, anchor = target.partition("#")
    if name.endswith(".md"):
        name = name[: -len(".md")] + ".html"
    return name + hash_mark + anchor


def main(argv=None):
    """Write or check the HTML file of each Markdown file; the exit code"""
    parser = argparse.ArgumentParser(
        description="Write FILE.html beside each FILE.md, generated from it."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing; print each FILE.html that differs and exit with 1",
    )
    parser.add_argument("files", nargs="+", metavar="FILE.md")
    args = parser.parse_args(argv)
    differing = False
    for name in args.files:
        source = Path(name)
        target = source.with_suffix(".html")
        try:
            generated = convert(source.read_text(encoding="utf-8"), name)
        except UnsupportedMarkdown as error:
            print(error, file=sys.stderr)
            return 2
        if args.check:
            current = target.read_text(encoding="utf-8") if target.exists() else None
            if current != generated:
                print(target)
                differing = True
        else:
            # newline="\n" keeps the file the same on Windows.
            with target.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(generated)
    return 1 if differing else 0


if __name__ == "__main__":
    sys.exit(main())
