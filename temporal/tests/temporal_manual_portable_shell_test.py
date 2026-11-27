# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check that the shell examples of the manuals run with GNU and BSD tools

The example tests compare the shown output character for character, and the
macOS runner of the CI has BSD tools. A command whose output differs between
the two (26.11.2026: the macOS run failed eight manuals) must not stand in an
example, or be made portable the way the replacement of each pattern says.
"""

import re
from pathlib import Path

import pytest

from grass.temporal.testing.manual_examples import ManualFormatError, parse_manual

TOOLS = Path(__file__).parents[1]
MANUALS = sorted(TOOLS.glob("*/*.md")) + [TOOLS / "temporalintro.md"]

# Each pattern matches one form that differs between GNU and BSD tools. A
# pattern with a lookahead matches the form only without its portable fix.
NON_PORTABLE = {
    # BSD wc pads the count with blanks, GNU wc does not; `| tr -d ' '` gives
    # the bare number with both.
    "wc without tr": re.compile(r"\bwc\s+-[lcw]\b(?!\s*\|\s*tr -d ' ')"),
    # BSD seq -s keeps the separator after the last number with -f formats,
    # so the list is written out or built with printf and sed.
    "seq -s": re.compile(r"\bseq\s+(?:-\w+\s+)*-s"),
    # BSD od ends its line differently from GNU od; deleting blanks and
    # newlines leaves the same hex digits.
    "od without tr": re.compile(r"\bod\b[^\n|]*+(?!\s*\|\s*tr -d ' \\n')"),
    # GNU date reads a date with -d, BSD date wants -j -f.
    "date -d": re.compile(r"\bdate\s+(?:-\w*d\b|--date)"),
    # BSD sed -i needs a suffix argument, GNU sed takes none.
    "sed -i": re.compile(r"\bsed\s+(?:-\w*i\b|--in-place)"),
    # BSD readlink has no -f before macOS 12.3.
    "readlink -f": re.compile(r"\breadlink\s+-f\b"),
    # BSD head has no -c.
    "head -c": re.compile(r"\bhead\s+-c\b"),
}


def paste_without_dash(code):
    """Return the paste commands with -s that do not read standard input as -

    BSD paste reads standard input only when told so by `-`; GNU paste also
    does without.
    """
    found = []
    for match in re.finditer(r"\bpaste\b([^|)\n]*)", code):
        words = match.group(1).split()
        if any(re.match(r"-[a-z]*s", word) for word in words) and "-" not in words:
            found.append(match.group(0).strip())
    return found


def problems(code):
    """Return the non-portable forms in the shell code, each with its name"""
    found = []
    for name, pattern in NON_PORTABLE.items():
        found.extend(f"{name}: {m.group(0)!r}" for m in pattern.finditer(code))
    found.extend(f"paste without -: {text!r}" for text in paste_without_dash(code))
    return found


def shell_blocks(manual):
    try:
        examples = parse_manual(manual).examples
        return [
            (block.line, block.code)
            for example in examples
            for block in example.blocks
            if block.language == "sh"
        ]
    except ManualFormatError:
        # A manual that does not follow the example layout has no checked
        # examples; the example tests report the layout.
        return []


def test_shell_blocks_avoid_gnu_only_forms():
    found = [
        f"{manual.name}:{line}: {problem}"
        for manual in MANUALS
        for line, code in shell_blocks(manual)
        for problem in problems(code)
    ]
    assert not found, "\n".join(found)


@pytest.mark.parametrize(
    "code",
    [
        "g.list type=raster | wc -l\n",
        "echo $(tar -tf a.tar | wc -c) bytes\n",
        "x | paste -sd,\n",
        "x | paste -s -d,\n",
        "maps=$(seq -s, -f 'f_%g' 1 10)\n",
        "od -An -tx1 -N2 a.tar | tr -d ' '\n",
        "date -d yesterday\n",
        "sed -i s/a/b/ file\n",
        "readlink -f link\n",
        "head -c 10 file\n",
    ],
)
def test_guard_flags_the_forms_it_claims(code):
    assert problems(code)


@pytest.mark.parametrize(
    "code",
    [
        "g.list type=raster | wc -l | tr -d ' '\n",
        "echo $(tar -tf a.tar | wc -l | tr -d ' ') files\n",
        "x | paste -sd, -\n",
        "x | paste -s -d, -\n",
        "paste a b\n",
        "od -An -tx1 -N2 a.tar | tr -d ' \\n'; echo\n",
        "head -n 3 file\n",
        "sed -n 1,4p file\n",
        "date +%Y\n",
    ],
)
def test_guard_leaves_portable_forms(code):
    assert problems(code) == []
