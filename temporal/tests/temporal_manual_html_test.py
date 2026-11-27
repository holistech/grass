# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check that the HTML manuals of the temporal tools are generated

The Markdown file of a manual is its source; utils/grass_md2html.py writes
the HTML file from it. An HTML file edited by hand, or a Markdown file
changed without generating the HTML file again, fails here.
"""

import difflib
import importlib.util
import re
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
GENERATOR = TOOLS.parent / "utils" / "grass_md2html.py"

# utils/ is no package that the tests could import from; the generator is a
# script, so it is loaded from its file.
_spec = importlib.util.spec_from_file_location("grass_md2html", GENERATOR)
md2html = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md2html)

# The manual of each tool, the introduction to the temporal framework and
# the page of its changes in GRASS 8.6.
MANUALS = sorted(
    path for path in TOOLS.glob("*/*.md") if path.stem == path.parent.name
) + [TOOLS / "temporalintro.md", TOOLS / "temporalchanges.md"]


@pytest.mark.parametrize("manual", MANUALS, ids=lambda path: path.stem)
def test_html_is_generated_from_markdown(manual):
    page = manual.with_suffix(".html")
    generated = md2html.convert(manual.read_text(encoding="utf-8"), str(manual))
    current = page.read_text(encoding="utf-8")
    difference = "".join(
        difflib.unified_diff(
            current.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            str(page),
            "generated",
            n=1,
        )
    )
    assert not difference, (
        f"{page} is not the HTML of {manual.name}; run "
        f"python3 utils/grass_md2html.py {manual.relative_to(TOOLS.parent)}\n"
        f"{difference}"
    )


def missing_images(manual, tools=TOOLS):
    """Return the images that manual references and that no directory holds

    A tool manual finds its images next to itself. The introduction has no
    directory of its own, so its images may lie in any tool directory, where
    the build installs them from.
    """
    names = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", manual.read_text(encoding="utf-8"))
    if manual.parent == tools:
        directories = [path for path in tools.iterdir() if path.is_dir()]
    else:
        directories = [manual.parent]
    return [
        name
        for name in names
        if not any((directory / name).is_file() for directory in directories)
    ]


@pytest.mark.parametrize("manual", MANUALS, ids=lambda path: path.stem)
def test_images_of_the_manual_exist(manual):
    assert missing_images(manual) == [], (
        f"{manual.name} references images that are not files next to it"
    )


def test_missing_image_is_seen(tmp_path):
    """Counter-check: the check above reports a name that is not there"""
    tool = tmp_path / "t.x"
    tool.mkdir()
    (tool / "t.x.md").write_text("![a](there.png)\n![b](gone.png)\n", encoding="utf-8")
    (tool / "there.png").write_bytes(b"")
    intro = tmp_path / "temporalintro.md"
    intro.write_text("![c](there.png)\n![d](gone.png)\n", encoding="utf-8")
    assert missing_images(tool / "t.x.md", tmp_path) == ["gone.png"]
    assert missing_images(intro, tmp_path) == ["gone.png"]
