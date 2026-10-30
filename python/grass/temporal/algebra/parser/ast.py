"""Nodes of the syntax tree of the temporal algebra

The grammar only builds these nodes; it never looks at data. Their meaning
comes from the translator.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .operators import TemporalOperator


@dataclass(frozen=True)
class Number:
    """A numeric constant"""

    value: int | float


@dataclass(frozen=True)
class Text:
    """A quoted text, such as a date or the increment '1 month'"""

    value: str


@dataclass(frozen=True)
class Name:
    """The name of a space time dataset, with or without mapset"""

    ident: str


@dataclass(frozen=True)
class Negative:
    """The arithmetic negation of an operand"""

    operand: object


@dataclass(frozen=True)
class Binary:
    """A binary operation; operator is set for an operator in braces"""

    symbol: str
    left: object
    right: object
    operator: TemporalOperator | None = None


@dataclass(frozen=True)
class Function:
    """A call such as sin(A) or if({during}, A > 1, B)

    relation is the operator in braces before the arguments of if().
    """

    name: str
    arguments: tuple
    relation: TemporalOperator | None = None


@dataclass(frozen=True)
class Index:
    """A dataset with offsets: A[1] in time, A[1,0] in space, A[1,0,1] both"""

    name: str
    offsets: tuple[int, ...]


@dataclass(frozen=True)
class Statement:
    """An assignment of an expression to the name of the result"""

    target: str
    expression: object
