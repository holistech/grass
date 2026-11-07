# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check the links, the navigation entry and the build of the changes page

temporal/temporalchanges.md lists what changed in the temporal framework
since GRASS 8.5, and each entry links the section of a manual that describes
the behavior of today. These tests keep the links valid and check that the
Autotools build makes its HTML page. The HTML file and the examples of the page are checked with
the manuals (temporal_manual_html_test.py, temporal_manual_examples_test.py).
"""

import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
ROOT = TOOLS.parent
PAGE = TOOLS / "temporalchanges.md"

LINK = re.compile(r"\]\(([^)\s]+)\)")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")
FENCE = re.compile(r"^[ \t]*(```|~~~)")


def source_pages(root=ROOT):
    """Return the Markdown pages of the source tree by file name

    The MkDocs build copies every page into one directory, so a link names a
    page by its file name alone, as in [r.series](r.series.md). The pages are
    those that git tracks or would track: a walk of the directories would also
    find the copies in build trees and in directories that git ignores, and
    take a copy for the page. Without git, the test that uses this is skipped.
    """
    try:
        run = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("needs a git checkout of the source tree")
    return {Path(name).name: root / name for name in run.stdout.splitlines()}


def slugify(text):
    """Return the anchor of a heading as MkDocs makes it

    The rule of the toc extension of Python-Markdown, which MkDocs uses:
    ASCII only, characters other than letters, digits, blanks, hyphens and
    underscores removed, lower case, blanks and hyphens joined to one hyphen.
    The marks of code, emphasis and links are removed first, as the extension
    takes the text of the rendered heading.
    """
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.replace("`", "").replace("*", "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def anchors(page):
    """Return the anchors of the headings of a page

    A heading inside a code block is no heading. The toc extension gives a
    second heading of the same text the anchor with "_1", a third "_2".
    """
    found = set()
    in_code = False
    for line in page.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        match = None if in_code else HEADING.match(line)
        if match:
            anchor = slugify(match.group(2))
            unique = anchor
            number = 1
            while unique in found:
                unique = f"{anchor}_{number}"
                number += 1
            found.add(unique)
    return found


def broken_links(page, pages):
    """Return the links of a page to a missing page or a missing heading"""
    broken = []
    for target in LINK.findall(page.read_text(encoding="utf-8")):
        if re.match(r"^[a-z]+:", target):
            continue
        name, _, anchor = target.partition("#")
        linked = page if not name else pages.get(name)
        if linked is None or (anchor and anchor not in anchors(linked)):
            broken.append(target)
    return broken


def test_changes_page_links_resolve():
    assert broken_links(PAGE, source_pages()) == []


def test_missing_page_and_heading_are_seen(tmp_path):
    """Counter-check: the check above reports a missing page and heading,
    and it reads the page, not a copy in a directory that git ignores"""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("copies/\n", encoding="utf-8")
    copies = tmp_path / "copies"
    copies.mkdir()
    (copies / "t.x.md").write_text("## Not a heading of the page\n", encoding="utf-8")
    tool = tmp_path / "t.x"
    tool.mkdir()
    (tool / "t.x.md").write_text(
        "## NOTES\n\n### Core and classic algebra\n\n```sh\n# Not a heading\n```\n",
        encoding="utf-8",
    )
    page = tmp_path / "changes.md"
    page.write_text(
        "## Classic algebra\n\n"
        "[a](t.x.md#notes) [b](t.x.md#core-and-classic-algebra) [c](#classic-algebra)\n"
        "[d](t.y.md) [e](t.x.md#not-a-heading) [f](#nowhere)\n"
        "[g](t.x.md#not-a-heading-of-the-page)\n"
        "[h](https://grass.osgeo.org/download/data/)\n",
        encoding="utf-8",
    )
    pages = source_pages(tmp_path)
    assert broken_links(page, pages) == [
        "t.y.md",
        "t.x.md#not-a-heading",
        "#nowhere",
        "t.x.md#not-a-heading-of-the-page",
    ]


def test_anchors_are_those_of_markdown():
    """The anchors of the headings of the page are those Python-Markdown makes"""
    toc = pytest.importorskip("markdown.extensions.toc")
    for line in PAGE.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if match and "`" not in line and "[" not in line:
            assert slugify(match.group(2)) == toc.slugify(match.group(2), "-")


@pytest.mark.skipif(
    not (ROOT / "include" / "Make" / "Platform.make").is_file()
    or shutil.which("make") is None,
    reason="needs a source tree configured for the Autotools build",
)
def test_changes_page_is_built():
    """The Autotools build writes the HTML page, the Markdown page and the
    man page of the changes page

    include/Make/Html.make builds the page of one PGM per directory, and
    temporalintro is the PGM of temporal/. make -n -B prints the commands of
    the target html without running them, for all pages, also those that are
    up to date.
    """
    run = subprocess.run(
        ["make", "-n", "-B", "-C", str(TOOLS), "html"],
        capture_output=True,
        text=True,
        check=True,
    )
    commands = run.stdout
    assert re.search(
        r"mkhtml\.py temporalchanges > \S+/temporalchanges\.html", commands
    )
    assert re.search(
        r"mkmarkdown\.py temporalchanges > \S+/source/temporalchanges\.md", commands
    )
    assert re.search(r"temporalchanges\.md\S* \S+/temporalchanges\.1", commands)
