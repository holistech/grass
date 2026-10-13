"""Tests for the lexer of the temporal algebra syntax"""

import pytest

from grass.temporal.algebra.parser.lexer import tokenize
from grass.temporal.algebra.parser.operators import TemporalOperator


def types(text):
    return [kind for kind, _value in tokenize(text)]


def test_statement():
    assert types("R = A + B") == ["NAME", "ASSIGN", "NAME", "PLUS", "NAME"]


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("&&", "AND"),
        ("||", "OR"),
        ("==", "EQ"),
        ("!=", "NE"),
        ("<", "LT"),
        ("<=", "LE"),
        (">", "GT"),
        (">=", "GE"),
        (":", "SELECT"),
        ("!:", "NOT_SELECT"),
        ("#", "HASH"),
        ("%", "MODULO"),
        ("/", "DIVIDE"),
        ("*", "TIMES"),
        ("-", "MINUS"),
        ("[", "LBRACKET"),
        ("]", "RBRACKET"),
        ("=", "ASSIGN"),
    ],
)
def test_symbols(text, kind):
    assert types(text) == [kind]


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("{:,during}", "SELECT_OP"),
        ("{!:,during}", "SELECT_OP"),
        ("{#,during}", "HASH_OP"),
        ("{&&,during}", "AND_OP"),
        ("{||,during}", "OR_OP"),
        ("{*,during}", "MUL_OP"),
        ("{/,during}", "MUL_OP"),
        ("{%,during}", "MUL_OP"),
        ("{+,during}", "ADD_OP"),
        ("{-,during}", "ADD_OP"),
        ("{during}", "RELATION"),
        ("{during,|}", "RELATION"),
        ("{ +,during}", "ADD_OP"),
    ],
)
def test_operator_kinds(text, kind):
    ((found, value),) = tokenize(text)
    assert found == kind
    assert isinstance(value, TemporalOperator)


def test_operator_value():
    assert tokenize("{+,during,r}") == [
        ("ADD_OP", TemporalOperator("+", ("during",), temporal="r"))
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12", [("INT", 12)]),
        ("1.5", [("FLOAT", 1.5)]),
        ("2.", [("FLOAT", 2.0)]),
        ("1.0e-05", [("FLOAT", 1e-05)]),
        ("2e3", [("FLOAT", 2000.0)]),
        ("-3", [("MINUS", "-"), ("INT", 3)]),
        ('"1 month"', [("STRING", "1 month")]),
        ("'2001-01-01'", [("STRING", "2001-01-01")]),
        ("A@PERMANENT", [("NAME", "A@PERMANENT")]),
        ("start_doy", [("NAME", "start_doy")]),
        ("A-1", [("NAME", "A"), ("MINUS", "-"), ("INT", 1)]),
    ],
)
def test_values(text, expected):
    assert tokenize(text) == expected


def test_whitespace_and_newlines_are_ignored():
    assert types(" R\t=\nA ") == ["NAME", "ASSIGN", "NAME"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("A $ B", r"Unexpected character '\$' at position 2"),
        ("A {+,foo} B", r"Unknown relation 'foo'.* at position 2"),
        ("K = A {+,during B", r"Unterminated '\{' at position 6"),
        ('R = tshift(A, "1 day)', r"Unterminated text at position 14"),
        ("R = tshift(A, '1 day)", r"Unterminated text at position 14"),
    ],
)
def test_errors(text, message):
    with pytest.raises(SyntaxError, match=message):
        tokenize(text)


@pytest.mark.parametrize(
    ("text", "kind"),
    [("&", "AMP"), ("|", "PIPE"), ("^", "CARET"), ("~", "TILDE")],
)
def test_overlay_symbols(text, kind):
    assert [token for token, _ in tokenize(f"A {text} B")] == ["NAME", kind, "NAME"]


@pytest.mark.parametrize(
    ("text", "kind", "symbol"),
    [
        ("{&,during,l}", "OVERLAY_OP", "&"),
        ("{|,equal}", "OVERLAY_OP", "|"),
        ("{^,equal,r}", "OVERLAY_OP", "^"),
        ("{~,equal}", "OVERLAY_OP", "~"),
        ("{&&,equal}", "AND_OP", "&&"),
        ("{||,equal}", "OR_OP", "||"),
        ("{+,equal}", "ADD_OP", "+"),
    ],
)
def test_overlay_operators_in_braces(text, kind, symbol):
    [(token, operator)] = tokenize(text)
    assert (token, operator.symbol) == (kind, symbol)


def test_double_symbols_stay_logical():
    assert [token for token, _ in tokenize("A && B || C")] == [
        "NAME",
        "AND",
        "NAME",
        "OR",
        "NAME",
    ]
