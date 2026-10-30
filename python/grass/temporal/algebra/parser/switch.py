"""The choice between the rules of the algebra core and the classic rules

The public parser classes of the raster, 3D raster and vector algebra and
t.select translate an expression onto the core in both cases: with the
profile CORE, or with the classic profile CLASSIC if the classic algebra is
chosen. The classic algebra stays, because published results rely on it.

The reference implementation (grass.temporal.classic) computes no expression
for the tools. The public parser classes use it for the granularity mode and
for the attributes only it has (facade.py), the classic grammar uses its
lexers (classic_grammar.py), and tests compare the classic profile with it
through grass.temporal.testing.reference.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import os

#: The environment variable that chooses the algebra for every expression
#: of a session or script: "core" or "classic". Unset or empty means the core.
ALGEBRA_VARIABLE = "GRASS_TEMPORAL_ALGEBRA"
DEFAULT_ALGEBRA = "core"


def classic_selected(classic):
    """Tell whether the classic algebra computes an expression

    :param classic: True or False decides; None follows the environment
        variable GRASS_TEMPORAL_ALGEBRA, whose default is the core
    :raises ValueError: for a value of the variable other than core and
        classic; an empty value counts as unset, as a shell script that
        writes ``GRASS_TEMPORAL_ALGEBRA= t.rast.algebra ...`` means no
        choice, while a value of blanks is more likely a mistake
    """
    if classic is not None:
        return classic
    choice = os.environ.get(ALGEBRA_VARIABLE) or DEFAULT_ALGEBRA
    if choice not in ("core", "classic"):
        msg = f"{ALGEBRA_VARIABLE} is core or classic, not {choice!r}"
        raise ValueError(msg)
    return choice == "classic"
