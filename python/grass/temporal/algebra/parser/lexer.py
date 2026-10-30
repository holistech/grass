"""Tokens of the temporal algebra syntax

&& and || are tokens of their own, so that the grammar can give them
different precedence. An operator in braces is one token; its kind decides
its precedence, so each kind has a token type of its own and carries the
parsed TemporalOperator as value.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from grass.temporal.algebra.content import COMPARISONS
from grass.temporal.ply import lex

from .operators import parse_operator

TOKENS = (
    "NAME",
    "INT",
    "FLOAT",
    "STRING",
    "LPAREN",
    "RPAREN",
    "LBRACKET",
    "RBRACKET",
    "COMMA",
    "ASSIGN",
    "PLUS",
    "MINUS",
    "TIMES",
    "DIVIDE",
    "MODULO",
    "HASH",
    "EQ",
    "NE",
    "LT",
    "LE",
    "GT",
    "GE",
    "AND",
    "OR",
    "SELECT",
    "NOT_SELECT",
    "SELECT_OP",
    "HASH_OP",
    "AND_OP",
    "OR_OP",
    "MUL_OP",
    "ADD_OP",
    "RELATION",
    "AMP",
    "PIPE",
    "CARET",
    "TILDE",
    "OVERLAY_OP",
    "CMP_OP",
)

# The first symbol in the braces decides the kind; && and || are listed
# before & and |, because the first match counts.
_OPERATOR_KINDS = (
    ("!:", "SELECT_OP"),
    (":", "SELECT_OP"),
    ("#", "HASH_OP"),
    ("&&", "AND_OP"),
    ("||", "OR_OP"),
    ("&", "OVERLAY_OP"),
    ("|", "OVERLAY_OP"),
    ("^", "OVERLAY_OP"),
    ("~", "OVERLAY_OP"),
    ("*", "MUL_OP"),
    ("/", "MUL_OP"),
    ("%", "MUL_OP"),
    ("+", "ADD_OP"),
    ("-", "ADD_OP"),
    # {>=,equal,l} compares related maps; no comparison symbol starts like
    # one of the symbols above.
    *((symbol, "CMP_OP") for symbol in COMPARISONS),
)


class Lexer:
    """The token rules for PLY

    PLY tries the function rules in the order of definition, then the string
    rules by decreasing length of their pattern, so "==" wins over "=". It
    compiles the patterns with re.VERBOSE: a space or "#" in a pattern must
    be escaped.
    """

    tokens = TOKENS

    t_ignore = " \t\r\n"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_LBRACKET = r"\["
    t_RBRACKET = r"\]"
    t_COMMA = r","
    t_EQ = r"=="
    t_ASSIGN = r"="
    t_NE = r"!="
    t_LE = r"<="
    t_LT = r"<"
    t_GE = r">="
    t_GT = r">"
    t_AND = r"&&"
    t_OR = r"\|\|"
    t_NOT_SELECT = r"!:"
    t_SELECT = r":"
    t_HASH = r"\#"
    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_MODULO = r"%"
    # A single & or | is an overlay of vector maps; PLY tries longer
    # patterns first, so && and || stay the logical operators.
    t_AMP = r"&"
    t_PIPE = r"\|"
    t_CARET = r"\^"
    t_TILDE = r"~"

    # PLY needs the rule name to be a token type; the rule sets the type of
    # the kind it finds.
    @staticmethod
    def t_RELATION(t):
        r"""\{[^{}]*\}"""
        body = t.value[1:].lstrip()
        t.type = next(
            (kind for start, kind in _OPERATOR_KINDS if body.startswith(start)),
            "RELATION",
        )
        try:
            t.value = parse_operator(t.value)
        except SyntaxError as error:
            msg = f"{error} at position {t.lexpos}"
            raise SyntaxError(msg) from None
        return t

    @staticmethod
    def t_STRING(t):
        r"""\"[^\"]*\"|'[^']*'"""
        t.value = t.value[1:-1]
        return t

    @staticmethod
    def t_FLOAT(t):
        r"""\d+\.\d*([eE][-+]?\d+)?|\d+[eE][-+]?\d+"""
        t.value = float(t.value)
        return t

    @staticmethod
    def t_INT(t):
        r"""\d+"""
        t.value = int(t.value)
        return t

    @staticmethod
    def t_NAME(t):
        r"""[a-zA-Z_][a-zA-Z_0-9@]*"""
        return t

    # A "{" or a quote reaches t_error only when it is not closed (a "{"
    # also when another "{" comes first), so the character is not the fault.
    @staticmethod
    def t_error(t):
        """Raise a SyntaxError for a character that no token starts with"""
        char = t.value[0]
        if char == "{":
            msg = f"Unterminated '{{' at position {t.lexpos}"
        elif char in "\"'":
            msg = f"Unterminated text at position {t.lexpos}"
        else:
            msg = f"Unexpected character '{char}' at position {t.lexpos}"
        raise SyntaxError(msg)


def build_lexer():
    """Return a new lexer; a lexer keeps the state of one input"""
    return lex.lex(module=Lexer)


def tokenize(text):
    """Return the type and value of each token of text"""
    lexer = build_lexer()
    lexer.input(text)
    return [(token.type, token.value) for token in lexer]
