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
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1]
GENERATOR = TOOLS.parent / "utils" / "grass_md2html.py"

# utils/ is no package that the tests could import from; the generator is a
# script, so it is loaded from its file.
_spec = importlib.util.spec_from_file_location("grass_md2html", GENERATOR)
md2html = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(md2html)

# The manual of each tool and the introduction to the temporal framework.
MANUALS = sorted(
    path for path in TOOLS.glob("*/*.md") if path.stem == path.parent.name
) + [TOOLS / "temporalintro.md"]


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
