"""Operators in braces of the temporal algebra, such as {+,during|starts,r}

An operator names a function symbol, the relations, how the conditions of
several related maps are joined, and which time stamp the result takes.
The text between the braces is regular, so it is read here and not by the
grammar; the grammar only decides where an operator may stand.
"""

from __future__ import annotations

from dataclasses import dataclass

from grass.temporal.algebra.relations import SPATIAL_RELATIONS, TEMPORAL_RELATIONS

COMPARISONS = ("==", "!=", ">", ">=", "<", "<=")
SYMBOLS = (
    "!:", ":", "#", "&&", "||", "+", "-", "*", "/", "%", "&", "|", "^", "~",
    *COMPARISONS,
)  # fmt: skip

# The manual names both overlap relations "over". The published paper writes
# "equals" for the relation that is called "equal"; the earlier
# implementation reads it the same way. It is a second name so that the
# printed expressions run. TEMPORAL_RELATIONS keeps the canonical names only.
_SHORTHANDS = {"over": ("overlaps", "overlapped"), "equals": ("equal",)}
_TEMPORAL_REFERENCES = {
    "l": "l",
    "left": "l",
    "r": "r",
    "right": "r",
    "u": "u",
    "union": "u",
    "i": "i",
    "intersect": "i",
    "d": "d",
    "disjoint": "d",
}
_AGGREGATES = ("&", "|")


@dataclass(frozen=True)
class TemporalOperator:
    """An operator in braces

    symbol is one of SYMBOLS, among them the overlays &, |, ^ and ~ of
    vector maps, or None for a bare relation such as ``{during,|}``, the
    first argument of if(). aggregate joins the conditions of several
    related maps, "&" (all) or "|" (any); temporal is the time stamp of the
    result: "l" left, "r" right, "u" union, "i" intersection or "d" disjoint
    union.
    """

    symbol: str | None
    relations: tuple[str, ...] = ("equal",)
    aggregate: str = "&"
    temporal: str = "l"


def parse_operator(text):
    """Read an operator from its text including the braces

    A bare relation takes an aggregation, && and || and the comparisons take
    an aggregation and a temporal reference, the other symbols a temporal
    reference.

    :raises SyntaxError: for an unknown relation or temporal reference, or a
        part the operator does not take
    """
    parts = [part.strip() for part in text.strip()[1:-1].split(",")]
    symbol = parts[0] if parts[0] in SYMBOLS else None
    rest = parts[1:] if symbol is not None else parts
    relations = _relations(rest.pop(0), text) if rest else ("equal",)
    aggregate = "|" if symbol == "||" else "&"
    joining = (None, "&&", "||", *COMPARISONS)
    temporal = "l"
    if rest and symbol in joining and rest[0] in _AGGREGATES:
        aggregate = rest.pop(0)
    if rest and symbol is not None:
        word = rest.pop(0).lower()
        if word not in _TEMPORAL_REFERENCES:
            msg = f"Unknown temporal reference '{word}' in the operator {text}"
            raise SyntaxError(msg)
        temporal = _TEMPORAL_REFERENCES[word]
    if rest:
        msg = f"Unexpected '{rest[0]}' in the operator {text}"
        raise SyntaxError(msg)
    return TemporalOperator(symbol, relations, aggregate, temporal)


def relation_names(name):
    """Return the canonical relation names that a written name stands for

    ``over`` is both overlap relations and ``equals`` is ``equal``; any other
    name stands for itself, known or not.
    """
    return _SHORTHANDS.get(name, (name,))


def _relations(part, text):
    names = []
    for word in part.lower().split("|"):
        name = word.strip()
        for each in relation_names(name):
            if each not in TEMPORAL_RELATIONS and each not in SPATIAL_RELATIONS:
                msg = f"Unknown relation '{name}' in the operator {text}"
                raise SyntaxError(msg)
            if each not in names:
                names.append(each)
    return tuple(names)
