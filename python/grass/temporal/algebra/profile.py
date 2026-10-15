"""The variant of the algebra that evaluate() computes

A profile collects what differs between the core algebra and another
variant of the algebra that is built on the core: the grammar that reads an
expression and the translator class that turns the syntax tree into
operations. The profile is an object that is handed down to the places that
use it, not a global setting, so that two variants can run in one process.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Profile:
    """The rules of one variant of the algebra

    The defaults are the rules of the core.

    :param grammar: an object with parse(text) that returns the syntax tree
        (grass.temporal.algebra.parser.ast.Statement) of "name = expression";
        None reads the syntax of the core
    :param translator: the Translator class (or a subclass of it) that
        translates the tree; evaluate() calls it with the keywords of
        Translator and profile=; None takes Translator
    """

    grammar: Any = None
    translator: Any = None


CORE = Profile()
