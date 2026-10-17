"""Tests of TemporalOperatorLexer and TemporalOperatorParser.

The parser turns the operator part of a temporal algebra expression, for
example ``{:, during|contains, r}``, into four attributes: ``relations``,
``temporal``, ``function`` and ``aggregate``. No GRASS database is needed.

Expected values are derived from the grammar comments and from the temporal
algebra manuals (t.select, t.rast.algebra, t.vect.algebra), not from running
the parser.
"""

import itertools

import pytest

from grass.temporal.temporal_operator import (
    TemporalOperatorLexer,
    TemporalOperatorParser,
)

TEMPORAL_WORDS = {
    "l": "l",
    "left": "l",
    "r": "r",
    "right": "r",
    "u": "u",
    "union": "u",
    "d": "d",
    "disjoint": "d",
    "i": "i",
    "intersect": "i",
}

ALL_RELATIONS = [
    "equal",
    "follows",
    "precedes",
    "overlaps",
    "overlapped",
    "during",
    "starts",
    "finishes",
    "contains",
    "started",
    "finished",
    "equivalent",
    "cover",
    "overlap",
    "in",
    "contain",
    "meet",
]


def parse(expression, optype):
    """Parse with a fresh parser and return (relations, temporal, function, aggregate)."""
    parser = TemporalOperatorParser()
    parser.parse(expression, optype=optype)
    return parser.relations, parser.temporal, parser.function, parser.aggregate


def lex(text):
    """Return the (type, value) pairs the lexer produces for text."""
    lexer = TemporalOperatorLexer()
    lexer.build()
    lexer.lexer.input(text)
    return [(token.type, token.value) for token in lexer.lexer]


# Lexer


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{", [("CLPAREN", "{")]),
        ("}", [("CRPAREN", "}")]),
        (",", [("COMMA", ",")]),
        (":", [("T_SELECT", ":")]),
        ("!:", [("T_NOT_SELECT", "!:")]),
        ("#", [("HASH", "#")]),
        ("&", [("AND", "&")]),
        ("^", [("XOR", "^")]),
        ("~", [("NOT", "~")]),
        ("%", [("MOD", "%")]),
        ("/", [("DIV", "/")]),
        ("*", [("MULT", "*")]),
        ("-", [("SUB", "-")]),
        ("equal", [("EQUAL", "equal")]),
        ("over", [("OVER", "over")]),
        ("meet", [("MEET", "meet")]),
        # The published paper writes equals for the relation equal.
        ("equals", [("EQUAL", "equal")]),
        ("==", [("CEQUALS", "==")]),
        ("!=", [("UNEQUALS", "!=")]),
        ("<", [("LOWER", "<")]),
        ("<=", [("LOWER_EQUALS", "<=")]),
        (">", [("GREATER", ">")]),
        (">=", [("GREATER_EQUALS", ">=")]),
    ],
)
def test_lexer_single_tokens(text, expected):
    """Each operator character and relation keyword maps to its token type."""
    assert lex(text) == expected


def test_lexer_or_between_relations():
    """'|' between relation keywords is the OR token."""
    assert lex("equal|during") == [
        ("EQUAL", "equal"),
        ("OR", "|"),
        ("DURING", "during"),
    ]


@pytest.mark.parametrize("word", TEMPORAL_WORDS)
def test_lexer_temporal_words_are_normalized_to_one_letter(word):
    """Long and short temporal reference words yield the same one-letter value."""
    token_type = {
        "l": "LEFTREF",
        "r": "RIGHTREF",
        "u": "UNION",
        "d": "DISJOINT",
        "i": "INTERSECT",
    }[TEMPORAL_WORDS[word]]
    assert lex(word) == [(token_type, TEMPORAL_WORDS[word])]


def test_lexer_ignores_whitespace():
    """Blanks, tabs and newlines between tokens are skipped."""
    assert lex(" {\t:\n,  equal } ") == [
        ("CLPAREN", "{"),
        ("T_SELECT", ":"),
        ("COMMA", ","),
        ("EQUAL", "equal"),
        ("CRPAREN", "}"),
    ]


@pytest.mark.parametrize("text", ["foo", "EQUAL", "lefty", "3", "=", ";", "equal_"])
def test_lexer_rejects_unknown_input(text):
    """Unknown words and characters raise SyntaxError instead of passing silently."""
    with pytest.raises(SyntaxError):
        lex(text)


def test_lexer_or_at_start_of_input_is_or():
    """A '|' is the OR token wherever it stands, also at the start of the input."""
    assert lex("|") == [("OR", "|")]


# Parser: relation operators {during}, {during|equal}


@pytest.mark.parametrize("relation", ALL_RELATIONS)
def test_relation_operator_single_relation(relation):
    """Every supported relation parses as a one-element relation operator."""
    assert parse("{%s}" % relation, "relation") == ([relation], None, None, None)


@pytest.mark.parametrize(
    ("expression", "relations"),
    [
        ("{equal|during}", ["equal", "during"]),
        ("{equal| during}", ["equal", "during"]),
        ("{ equal | during | starts }", ["equal", "during", "starts"]),
        (
            "{equal|equivalent|cover|in|meet|contain|overlap}",
            ["equal", "equivalent", "cover", "in", "meet", "contain", "overlap"],
        ),
        ("{during|during}", ["during", "during"]),
    ],
)
def test_relation_operator_lists(expression, relations):
    """Relations joined with '|' are kept in the written order."""
    assert parse(expression, "relation") == (relations, None, None, None)


def test_relation_operator_equals_is_another_name_of_equal():
    """'equals' is read as 'equal' and named twice stays twice."""
    assert parse("{equals}", "relation")[0] == ["equal"]
    assert parse("{during|equals}", "relation")[0] == ["during", "equal"]
    assert parse("{equals|equal}", "relation")[0] == ["equal", "equal"]


@pytest.mark.parametrize("word", ["EQUALS", "Equals", "equalss"])
def test_relation_name_equals_is_matched_exactly(word):
    """Only the lower case word is an alias, like every relation name."""
    with pytest.raises(SyntaxError, match=word):
        parse("{%s}" % word, "relation")


def test_relation_operator_over_expands_to_both_overlaps():
    """'over' stands for overlaps and overlapped (t.select manual)."""
    assert parse("{over}", "relation")[0] == ["overlaps", "overlapped"]


def test_relation_operator_over_last_in_list():
    """'over' at the end of a list is flattened into the relation list."""
    assert parse("{during|over}", "relation")[0] == [
        "during",
        "overlaps",
        "overlapped",
    ]


def test_relation_operator_over_first_in_list():
    """'over' at the start of a list is flattened like it is at the end."""
    assert parse("{over|during}", "relation")[0] == [
        "overlaps",
        "overlapped",
        "during",
    ]


# Parser: select operators {:}, {!:, during, r}


@pytest.mark.parametrize("function", [":", "!:"])
def test_select_operator_default_is_equal(function):
    """A bare select operator selects temporally equal maps (t.select.md)."""
    assert parse("{%s}" % function, "select") == (
        ["equal"],
        "l",
        function,
        None,
    )


@pytest.mark.parametrize("function", [":", "!:"])
@pytest.mark.parametrize(
    ("relation_text", "relations"),
    [
        ("during", ["during"]),
        ("contains", ["contains"]),
        ("during|contains", ["during", "contains"]),
        ("equal | contains | starts", ["equal", "contains", "starts"]),
    ],
)
def test_select_operator_with_relations(function, relation_text, relations):
    """Without a temporal operator, the result extent is the left one."""
    assert parse("{%s, %s}" % (function, relation_text), "select") == (
        relations,
        "l",
        function,
        None,
    )


@pytest.mark.parametrize("function", [":", "!:"])
@pytest.mark.parametrize(("word", "letter"), TEMPORAL_WORDS.items())
def test_select_operator_with_temporal_operator(function, word, letter):
    """All five temporal extent operators are accepted in long and short form."""
    assert parse("{%s,during,%s}" % (function, word), "select") == (
        ["during"],
        letter,
        function,
        None,
    )


def test_select_operator_with_relation_list_and_temporal_operator():
    """The full select form combines a relation list and a temporal operator."""
    assert parse("{!:, equal | contains, d}", "select") == (
        ["equal", "contains"],
        "d",
        "!:",
        None,
    )


# Parser: hash operators {#}, {#, contains, r}


def test_hash_operator_default_is_equal():
    """A bare hash operator counts temporally equal maps."""
    assert parse("{#}", "hash") == (["equal"], "l", "#", None)


@pytest.mark.parametrize(
    ("expression", "relations", "temporal"),
    [
        ("{#, contains}", ["contains"], "l"),
        ("{#, during | equal | starts}", ["during", "equal", "starts"], "l"),
        ("{#, during, r}", ["during"], "r"),
        ("{#, equal | contains, intersect}", ["equal", "contains"], "i"),
        ("{#,contains,union}", ["contains"], "u"),
    ],
)
def test_hash_operator_forms(expression, relations, temporal):
    """Relation and temporal operator parts of the hash operator are parsed."""
    assert parse(expression, "hash") == (relations, temporal, "#", None)


# Parser: raster (arithmetic) operators


@pytest.mark.parametrize("function", ["+", "-", "*", "/", "%"])
def test_raster_operator_default_is_equal(function):
    """A bare arithmetic operator combines temporally equal maps."""
    assert parse("{%s}" % function, "raster") == (["equal"], "l", function, None)


@pytest.mark.parametrize("function", ["+", "-", "*", "/", "%"])
@pytest.mark.parametrize(
    ("suffix", "relations", "temporal"),
    [
        (", during", ["during"], "l"),
        (", equal | contains", ["equal", "contains"], "l"),
        (", during, r", ["during"], "r"),
        (", equal | contains, intersect", ["equal", "contains"], "i"),
        (", contains, disjoint", ["contains"], "d"),
        (", equal, left", ["equal"], "l"),
    ],
)
def test_raster_operator_forms(function, suffix, relations, temporal):
    """Every arithmetic operator accepts relations and a temporal operator."""
    assert parse("{%s%s}" % (function, suffix), "raster") == (
        relations,
        temporal,
        function,
        None,
    )


def test_raster_operator_over_relation():
    """'over' also expands inside the arithmetic operator form."""
    assert parse("{*, over}", "raster") == (
        ["overlaps", "overlapped"],
        "l",
        "*",
        None,
    )


# Parser: overlay operators


@pytest.mark.parametrize("function", ["&", "|", "^", "~", "+"])
def test_overlay_operator_default_is_equal(function):
    """A bare overlay operator combines temporally equal maps."""
    assert parse("{%s}" % function, "overlay") == (["equal"], "l", function, None)


@pytest.mark.parametrize("function", ["&", "|", "^", "~", "+"])
@pytest.mark.parametrize(
    ("suffix", "relations", "temporal"),
    [
        (", starts", ["starts"], "l"),
        (", equal | during", ["equal", "during"], "l"),
        (", equal, left", ["equal"], "l"),
        (", over, right", ["overlaps", "overlapped"], "r"),
        (", equal | contains, union", ["equal", "contains"], "u"),
    ],
)
def test_overlay_operator_forms(function, suffix, relations, temporal):
    """Every overlay operator accepts relations and a temporal operator."""
    assert parse("{%s%s}" % (function, suffix), "overlay") == (
        relations,
        temporal,
        function,
        None,
    )


def test_overlay_operator_plus():
    """The overlay operator '+' (disjoint union of vector maps) parses."""
    assert parse("{+}", "overlay") == (["equal"], "l", "+", None)


# Parser: boolean (comparison) operators


@pytest.mark.parametrize(("function", "default_aggregate"), [("&&", "&"), ("||", "|")])
def test_boolean_operator_default_aggregate_follows_function(
    function, default_aggregate
):
    """'&&' aggregates related maps with '&', '||' with '|' (t.select manual)."""
    assert parse("{%s, equal}" % function, "boolean") == (
        ["equal"],
        "l",
        function,
        default_aggregate,
    )


@pytest.mark.parametrize("function", ["&&", "||"])
@pytest.mark.parametrize("aggregate", ["&", "|"])
def test_boolean_operator_explicit_aggregate(function, aggregate):
    """An explicit aggregation operator overrides the default."""
    assert parse("{%s, equal | during, %s}" % (function, aggregate), "boolean") == (
        ["equal", "during"],
        "l",
        function,
        aggregate,
    )


@pytest.mark.parametrize("function", ["&&", "||"])
@pytest.mark.parametrize(("word", "letter"), TEMPORAL_WORDS.items())
def test_boolean_operator_with_temporal_operator(function, word, letter):
    """A temporal operator without aggregate keeps the default aggregate."""
    default_aggregate = function[0]
    assert parse("{%s, during, %s}" % (function, word), "boolean") == (
        ["during"],
        letter,
        function,
        default_aggregate,
    )


@pytest.mark.parametrize("function", ["&&", "||"])
@pytest.mark.parametrize("aggregate", ["&", "|"])
@pytest.mark.parametrize("relation_text", ["during", "equal | during | contains"])
def test_boolean_operator_with_aggregate_and_temporal_operator(
    function, aggregate, relation_text
):
    """The full boolean form sets all four attributes."""
    relations = [part.strip() for part in relation_text.split("|")]
    assert parse(
        "{%s, %s, %s, r}" % (function, relation_text, aggregate), "boolean"
    ) == (relations, "r", function, aggregate)


def test_boolean_operator_single_ampersand_function_is_rejected():
    """'&' alone is an overlay operator, not a boolean comparison operator."""
    with pytest.raises(SyntaxError):
        parse("{&, equal}", "boolean")


# Parser: errors


@pytest.mark.parametrize(
    ("expression", "optype"),
    [
        ("{+, starting}", "raster"),
        ("{nope, start, |, l}", "relation"),
        ("{:, foo}", "select"),
        ("{:, during, foo}", "select"),
        ("{:, 3}", "select"),
        ("{=}", "raster"),
        ("{EQUAL}", "relation"),
        ("{equal;}", "relation"),
        ("{++, start, |, l}", "relation"),
        ("{&&&, equal}", "boolean"),
        ("{&|, equal}", "boolean"),
        ("{&&, equal | during | contains | starts, &&&&&}", "boolean"),
        ("{&&, equal, |, bad}", "boolean"),
        ("{:,}", "select"),
        ("{:, during|}", "select"),
        ("{:, during, l, r}", "select"),
        ("{:, during, equal}", "select"),
        ("{:} x", "select"),
        ("{:, |during}", "select"),
        ("{#, during, l, r}", "hash"),
        ("{+, equal, |}", "raster"),
        ("{&&, equal, l, |}", "boolean"),
        ("{&&}", "boolean"),
        ("{||, during, &, r, x}", "boolean"),
    ],
)
def test_invalid_expressions_raise_syntax_error(expression, optype):
    """Malformed operator expressions raise SyntaxError."""
    with pytest.raises(SyntaxError):
        parse(expression, optype)


@pytest.mark.parametrize(
    ("operator", "optype"),
    [
        ("{nonsense}", "relation"),
        ("{equal|nonsense}", "relation"),
        ("{:, nonsense}", "select"),
        ("{#, contain|nonsense}", "hash"),
        ("{+, nonsense}", "raster"),
        ("{*, during|nonsense, r}", "raster"),
        ("{&, nonsense}", "overlay"),
        ("{+, equal | nonsense}", "overlay"),
        ("{&&, nonsense}", "boolean"),
    ],
)
def test_unknown_relation_name_raises_syntax_error(operator, optype):
    """A relation name which is none of the known relations is reported by name"""
    with pytest.raises(SyntaxError, match=r"near 'nonsense'"):
        parse(operator, optype)


def test_unknown_optype_raises_syntax_error():
    """An optype outside the supported list is rejected and named."""
    with pytest.raises(SyntaxError, match="Unknown optype rter"):
        parse("{:}", "rter")


@pytest.mark.parametrize("expression", ["", "{", "{:, during", "{:,", "{equal"])
def test_truncated_expression_raises_syntax_error(expression):
    """Incomplete input raises SyntaxError like any other malformed input."""
    with pytest.raises(SyntaxError):
        parse(expression, "select")


# Parser: operator type has to match the expression


OPTYPE_EXAMPLES = {
    "relation": "{during}",
    "select": "{:, during}",
    "hash": "{#, during}",
    "raster": "{*, during}",
    "overlay": "{|, during}",
    "boolean": "{&&, during}",
}


@pytest.mark.parametrize(
    ("optype", "other"),
    [(optype, other) for optype, other in itertools.permutations(OPTYPE_EXAMPLES, 2)],
)
def test_operator_of_other_type_is_rejected(optype, other):
    """An operator that does not belong to the requested optype raises SyntaxError."""
    with pytest.raises(SyntaxError):
        parse(OPTYPE_EXAMPLES[other], optype)


@pytest.mark.parametrize(
    "expression",
    [
        "{&&, during}",
        "{&&, during, |}",
        "{&&, during, l}",
        "{&&, during, |, l}",
    ],
)
def test_boolean_operator_with_select_optype_is_rejected(expression):
    """All four boolean grammar rules refuse to run with a different optype."""
    with pytest.raises(SyntaxError):
        parse(expression, "select")


def test_boolean_operator_error_names_boolean():
    """The error of a wrong optype names the type of the operator."""
    with pytest.raises(SyntaxError, match="it is a boolean operator"):
        parse("{&&, during, |, l}", "select")


# Parser: object state


def test_new_parser_starts_empty():
    """A fresh parser has no parsed attributes."""
    parser = TemporalOperatorParser()
    assert (parser.relations, parser.temporal, parser.function, parser.aggregate) == (
        None,
        None,
        None,
        None,
    )


def test_parser_can_be_reused_for_same_optype():
    """A second parse replaces the attributes of the first."""
    parser = TemporalOperatorParser()
    parser.parse("{:, during, r}", optype="select")
    parser.parse("{!:, equal}", optype="select")
    assert (parser.relations, parser.temporal, parser.function) == (
        ["equal"],
        "l",
        "!:",
    )


def test_reused_parser_resets_aggregate():
    """Parsing a non-boolean operator after a boolean one leaves no aggregate."""
    parser = TemporalOperatorParser()
    parser.parse("{&&, equal, |}", optype="boolean")
    parser.parse("{:}", optype="select")
    assert parser.aggregate is None


def test_parser_stores_optype_and_expression():
    """parse() records the optype and the expression it worked on."""
    parser = TemporalOperatorParser()
    parser.parse("{#}", optype="hash")
    assert (parser.optype, parser.expression) == ("hash", "{#}")


def test_default_optype_is_relation():
    """Without optype argument, a relation operator is expected."""
    parser = TemporalOperatorParser()
    parser.parse("{contains | starts}")
    assert parser.relations == ["contains", "starts"]


def test_failed_parse_leaves_no_stale_attributes():
    """After an error the attributes of the previous parse are gone."""
    parser = TemporalOperatorParser()
    parser.parse("{:, during, r}", optype="select")
    with pytest.raises(SyntaxError):
        parser.parse("{:, during, r}", optype="raster")
    assert (parser.relations, parser.temporal, parser.function) == (None, None, None)


# Parser: comparison operators {>=, during, |, r}


@pytest.mark.parametrize("symbol", ["==", "!=", "<", "<=", ">", ">="])
def test_compare_operator_default_is_equal_and_and(symbol):
    """A bare comparison relates equal maps and joins the comparisons with and"""
    assert parse("{%s, equal}" % symbol, "compare") == (["equal"], "l", symbol, "&")


@pytest.mark.parametrize(
    ("expression", "relations", "temporal", "aggregate"),
    [
        ("{>=, contains}", ["contains"], "l", "&"),
        ("{>=, contains, |}", ["contains"], "l", "|"),
        ("{<, during | equals, |, r}", ["during", "equal"], "r", "|"),
        ("{<=, equal, union}", ["equal"], "u", "&"),
        ("{==, over, &, i}", ["overlaps", "overlapped"], "i", "&"),
        ("{!=, meet, d}", ["meet"], "d", "&"),
    ],
)
def test_compare_operator_forms(expression, relations, temporal, aggregate):
    """The options are those of the boolean operators"""
    symbol = expression[1:].split(",")[0]
    assert parse(expression, "compare") == (relations, temporal, symbol, aggregate)


@pytest.mark.parametrize(
    ("expression", "optype"),
    [
        ("{>=, equal}", "boolean"),
        ("{>=, equal}", "raster"),
        ("{&&, equal}", "compare"),
        ("{+, equal}", "compare"),
        ("{:, equal}", "compare"),
    ],
)
def test_compare_operator_belongs_to_its_optype_only(expression, optype):
    with pytest.raises(SyntaxError, match="Wrong optype"):
        parse(expression, optype)


@pytest.mark.parametrize(
    "expression", ["{>=}", "{>=,}", "{>=, nonsense}", "{=, equal}"]
)
def test_compare_operator_errors(expression):
    with pytest.raises(SyntaxError):
        parse(expression, "compare")
