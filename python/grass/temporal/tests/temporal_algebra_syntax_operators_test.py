"""Tests for the operators in braces of the temporal algebra syntax"""

import re

import pytest

from grass.temporal.algebra.parser.operators import TemporalOperator, parse_operator


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{+}", TemporalOperator("+")),
        ("{:,during}", TemporalOperator(":", ("during",))),
        ("{!:,during|starts}", TemporalOperator("!:", ("during", "starts"))),
        (
            "{*, equal | during , r}",
            TemporalOperator("*", ("equal", "during"), temporal="r"),
        ),
        ("{+,contains,union}", TemporalOperator("+", ("contains",), temporal="u")),
        ("{#,contains}", TemporalOperator("#", ("contains",))),
        ("{&&,during}", TemporalOperator("&&", ("during",))),
        ("{||,during}", TemporalOperator("||", ("during",), aggregate="|")),
        ("{&&,during,|,i}", TemporalOperator("&&", ("during",), "|", "i")),
        ("{||,during,d}", TemporalOperator("||", ("during",), "|", "d")),
        ("{during}", TemporalOperator(None, ("during",))),
        ("{during,|}", TemporalOperator(None, ("during",), aggregate="|")),
        ("{equal|during,&}", TemporalOperator(None, ("equal", "during"))),
        ("{:,over}", TemporalOperator(":", ("overlaps", "overlapped"))),
        ("{+,equal|equivalent}", TemporalOperator("+", ("equal", "equivalent"))),
        ("{+,equal|covered}", TemporalOperator("+", ("equal", "covered"))),
        ("{+,DURING,Left}", TemporalOperator("+", ("during",))),
        # A comparison takes an aggregation and a temporal reference like &&,
        # and joins the comparisons with and by default, also for >= and <=.
        ("{>=,equal}", TemporalOperator(">=", ("equal",))),
        ("{>,contains,|}", TemporalOperator(">", ("contains",), "|")),
        (
            "{<=,contains|equal,&,r}",
            TemporalOperator("<=", ("contains", "equal"), "&", "r"),
        ),
        ("{==,during,u}", TemporalOperator("==", ("during",), "&", "u")),
        ("{!=,over,|,i}", TemporalOperator("!=", ("overlaps", "overlapped"), "|", "i")),
        ("{<,equals,d}", TemporalOperator("<", ("equal",), "&", "d")),
    ],
)
def test_parse_operator(text, expected):
    assert parse_operator(text) == expected


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{+,foo}", "Unknown relation 'foo'"),
        ("{+,during||equal}", "Unknown relation ''"),
        ("{+,during,x}", "Unknown temporal reference 'x'"),
        ("{+,during,|}", "Unknown temporal reference '|'"),
        ("{during,r}", "Unexpected 'r'"),
        ("{:,during,r,l}", "Unexpected 'l'"),
        ("{&&,during,|,r,l}", "Unexpected 'l'"),
        ("{>=,foo}", "Unknown relation 'foo'"),
        ("{>=,during,x}", "Unknown temporal reference 'x'"),
        ("{>=,during,|,r,l}", "Unexpected 'l'"),
    ],
)
def test_parse_operator_errors(text, message):
    with pytest.raises(SyntaxError, match=re.escape(message)):
        parse_operator(text)
