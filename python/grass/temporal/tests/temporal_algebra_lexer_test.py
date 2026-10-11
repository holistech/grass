"""Tests of TemporalAlgebraLexer and GlobalTemporalVar.

The lexer needs neither a session nor a temporal database, so these tests
run without a project. Expected tokens are written out by hand from the
token rules and the documented syntax of the temporal algebra.
"""

import pytest

from grass.temporal.temporal_algebra import GlobalTemporalVar, TemporalAlgebraLexer


@pytest.fixture(scope="module")
def lexer():
    """A built lexer"""
    lx = TemporalAlgebraLexer()
    lx.build()
    return lx


def tokenize(lexer, text):
    """Return (type, value) pairs for all tokens of text"""
    lexer.lexer.input(text)
    result = []
    while True:
        token = lexer.lexer.token()
        if token is None:
            return result
        result.append((token.type, token.value))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("C = A : B", [("NAME", "C"), ("EQUALS", "="), ("NAME", "A")]),
        ("A : B", [("NAME", "A"), ("T_SELECT", ":"), ("NAME", "B")]),
        ("A !: B", [("NAME", "A"), ("T_NOT_SELECT", "!:"), ("NAME", "B")]),
        ("A # B", [("NAME", "A"), ("HASH", "#"), ("NAME", "B")]),
        ("A == B", [("NAME", "A"), ("CEQUALS", "=="), ("NAME", "B")]),
        ("A != B", [("NAME", "A"), ("UNEQUALS", "!="), ("NAME", "B")]),
        ("A < B", [("NAME", "A"), ("LOWER", "<"), ("NAME", "B")]),
        ("A <= B", [("NAME", "A"), ("LOWER_EQUALS", "<="), ("NAME", "B")]),
        ("A > B", [("NAME", "A"), ("GREATER", ">"), ("NAME", "B")]),
        ("A >= B", [("NAME", "A"), ("GREATER_EQUALS", ">="), ("NAME", "B")]),
        ("A | B", [("NAME", "A"), ("OR", "|"), ("NAME", "B")]),
        ("A & B", [("NAME", "A"), ("AND", "&"), ("NAME", "B")]),
        (
            "A || B",
            [("NAME", "A"), ("OR", "|"), ("OR", "|"), ("NAME", "B")],
        ),
        (
            "f(A, B)",
            [
                ("NAME", "f"),
                ("LPAREN", "("),
                ("NAME", "A"),
                ("COMMA", ","),
                ("NAME", "B"),
                ("RPAREN", ")"),
            ],
        ),
        ("'x'", [("QUOTE", "'"), ("NAME", "x"), ("QUOTE", "'")]),
    ],
)
def test_simple_tokens(lexer, text, expected):
    """Each operator character sequence maps to its own token type"""
    tokens = tokenize(lexer, text)
    # "C = A : B" is only checked for its first three tokens
    assert tokens[: len(expected)] == expected


@pytest.mark.parametrize(
    ("text", "token_type"),
    [
        ("{:}", "T_SELECT_OPERATOR"),
        ("{!:}", "T_SELECT_OPERATOR"),
        ("{:,equal}", "T_SELECT_OPERATOR"),
        ("{!:,equal}", "T_SELECT_OPERATOR"),
        ("{:,during|equal}", "T_SELECT_OPERATOR"),
        ("{:, equal}", "T_SELECT_OPERATOR"),
        ("{:,during,u}", "T_SELECT_OPERATOR"),
        ("{!:,during|equal,intersect}", "T_SELECT_OPERATOR"),
        ("{#}", "T_HASH_OPERATOR"),
        ("{#,equal}", "T_HASH_OPERATOR"),
        ("{#,equal|during}", "T_HASH_OPERATOR"),
        ("{#,contains,r}", "T_HASH_OPERATOR"),
        ("{||,equal}", "T_COMP_OPERATOR"),
        ("{&&,equal|during}", "T_COMP_OPERATOR"),
        ("{||,equal,l}", "T_COMP_OPERATOR"),
        ("{&&,equal|during,union}", "T_COMP_OPERATOR"),
        ("{:, during, r}", "T_SELECT_OPERATOR"),
        ("{#, equal,  l}", "T_HASH_OPERATOR"),
        ("{||, equal, u}", "T_COMP_OPERATOR"),
        ("{&&, equal|contains, |, l}", "T_COMP_OPERATOR"),
        ("{&&,contains, |, r}", "T_COMP_OPERATOR"),
        ("{&&,equal,|,l}", "T_COMP_OPERATOR"),
        ("{equal}", "T_REL_OPERATOR"),
        ("{equal|during}", "T_REL_OPERATOR"),
        ("{ equal | during }", "T_REL_OPERATOR"),
    ],
)
def test_operator_tokens(lexer, text, token_type):
    """A brace expression is one token whose type depends on its first symbol"""
    assert tokenize(lexer, f"A {text} B") == [
        ("NAME", "A"),
        (token_type, text),
        ("NAME", "B"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "{+,during}",  # arithmetic operators belong to the raster lexer
        "{:,equal,x}",  # unknown temporal operator letter
        "{}",
        "{:,equal",  # not closed
    ],
)
def test_operator_tokens_rejected(lexer, text):
    """Brace expressions which match no operator rule are a syntax error"""
    with pytest.raises(SyntaxError):
        tokenize(lexer, text)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0", [("INT", 0)]),
        ("42", [("INT", 42)]),
        ("-3", [("INT", -3)]),
        ("1.5", [("FLOAT", 1.5)]),
        ("-1.5", [("FLOAT", -1.5)]),
        ("2.", [("FLOAT", 2.0)]),
        ("1.5e3", [("FLOAT", 1500.0)]),
        ("-1.5e-3", [("FLOAT", -0.0015)]),
        # The minus sign is part of the number, the grammar has no subtraction
        ("3-2", [("INT", 3), ("INT", -2)]),
        ("A -1", [("NAME", "A"), ("INT", -1)]),
        ("1abc", [("INT", 1), ("NAME", "abc")]),
    ],
)
def test_numbers(lexer, text, expected):
    """INT and FLOAT carry converted values; a minus sign belongs to the number"""
    assert tokenize(lexer, text) == expected


@pytest.mark.parametrize("text", [".5", "$", "a.b", "A + B", "A / B", "A ~ B"])
def test_illegal_characters(lexer, text):
    """Characters without a rule raise SyntaxError"""
    with pytest.raises(SyntaxError):
        tokenize(lexer, text)


@pytest.mark.parametrize(
    "name",
    ["A", "map1", "_x", "a_b_1", "name@PERMANENT", "A1@mapset_2", "IF", "Start_Doy"],
)
def test_names(lexer, name):
    """Identifiers with digits, underscores and a mapset suffix are NAME tokens"""
    assert tokenize(lexer, name) == [("NAME", name)]


FUNCTIONS = (
    ["if", "buff_t", "tsnap", "tshift", "tmap", "merge", "strds", "str3ds", "stvds"]
    + ["start_time", "start_date", "start_datetime"]
    + ["end_time", "end_date", "end_datetime"]
    + ["td"]
    + [
        f"{side}_{part}"
        for side in ("start", "end")
        for part in (
            "doy",
            "dow",
            "year",
            "month",
            "week",
            "day",
            "hour",
            "minute",
            "second",
        )
    ]
)


@pytest.mark.parametrize("name", FUNCTIONS)
def test_function_names(lexer, name):
    """Each reserved word has the token type of its upper-case spelling"""
    assert tokenize(lexer, name) == [(name.upper(), name)]


def test_function_count():
    """No reserved word is added or lost unnoticed: 9 + 6 + 19 plus 26 others"""
    assert len(FUNCTIONS) == 9 + 3 + 3 + 1 + 18
    assert len(TemporalAlgebraLexer.tokens) == 26 + len(FUNCTIONS)


def test_reserved_word_needs_exact_match(lexer):
    """A name starting with a reserved word, or a longer one, stays a NAME"""
    assert tokenize(lexer, "iffy") == [("NAME", "iffy")]
    assert tokenize(lexer, "start_doy2") == [("NAME", "start_doy2")]
    assert tokenize(lexer, "tmap_x") == [("NAME", "tmap_x")]


def test_every_token_type_is_produced(lexer):
    """Each entry of the token list is reachable from some input"""
    samples = (
        '"2001-01-01 10:00:00" "2001-01-01" "12:30:00" 1 1.5 ( ) , == = != < <= '
        "> >= # | & {:} {#} {&&,equal} {equal} : !: A ' "
    ) + " ".join(FUNCTIONS)
    produced = {token_type for token_type, _ in tokenize(lexer, samples)}
    assert produced == set(TemporalAlgebraLexer.tokens)


@pytest.mark.parametrize("hour", ["00", "09", "10", "19", "20", "23"])
@pytest.mark.parametrize(
    ("template", "token_type"),
    [
        ('"2001-02-15 {hour}:05:09"', "DATETIME"),
        ('"2001-02-15T{hour}:05:09"', "DATETIME"),
        ('"{hour}:05:09"', "TIME"),
    ],
)
def test_time_literals_hours(lexer, hour, template, token_type):
    """Hours 00 to 23 form one token, in particular the range 10 to 19"""
    text = template.format(hour=hour)
    assert tokenize(lexer, text) == [(token_type, text)]


@pytest.mark.parametrize(
    ("minute", "second"), [("00", "00"), ("09", "10"), ("59", "59"), ("30", "45")]
)
def test_time_literals_minutes_seconds(lexer, minute, second):
    """Minutes and seconds up to 59 are accepted"""
    text = f'"2001-02-15 12:{minute}:{second}"'
    assert tokenize(lexer, text) == [("DATETIME", text)]


@pytest.mark.parametrize(
    "text", ['"2001-01-01"', '"2001-12-31"', '"1999-10-09"', '"2001-02-28"']
)
def test_date_literals(lexer, text):
    """A quoted ISO date is a single DATE token including the quotes"""
    assert tokenize(lexer, text) == [("DATE", text)]


@pytest.mark.parametrize(
    "text",
    [
        '"2001-13-01"',  # month 13
        '"2001-00-10"',  # month 0
        '"2001-01-32"',  # day 32
        '"2001-01-00"',  # day 0
        '"25:00:00"',  # hour 25
        '"2001-01-01 10:00"',  # seconds missing
    ],
)
def test_invalid_time_literals_are_no_literal(lexer, text):
    """Out-of-range fields do not form DATE, TIME or DATETIME tokens"""
    types = {token_type for token_type, _ in tokenize(lexer, text)}
    assert not types & {"DATE", "TIME", "DATETIME"}


@pytest.mark.parametrize(
    "text",
    [
        '"2001-01-01 10:60:00"',  # minute 60
        '"2001-01-01 10:00:60"',  # second 60: string_to_datetime rejects it
        '"2001-02-15 24:00:00"',  # hour 24
        '"24:00:00"',
    ],
)
def test_fields_beyond_the_valid_range_are_no_literal(lexer, text):
    """Hour 24 and the 60th minute or second do not exist for datetime"""
    types = {token_type for token_type, _ in tokenize(lexer, text)}
    assert not types & {"TIME", "DATETIME"}


@pytest.mark.parametrize("text", ["[...]", "[]"])
def test_list_brackets_are_not_part_of_the_language(lexer, text):
    """Square brackets have no meaning in the algebra and must be rejected"""
    with pytest.raises(SyntaxError):
        tokenize(lexer, text)


def test_line_numbers_are_counted(lexer):
    """A newline advances the line number reported for later tokens"""
    lexer.lexer.lineno = 1
    lexer.lexer.input("A\n\nB")
    assert [token.lineno for token in iter(lexer.lexer.token, None)] == [1, 3]


def test_whitespace_is_ignored(lexer):
    """Blanks, tabs and newlines separate tokens without producing any"""
    assert tokenize(lexer, "A\t:\n  B") == [
        ("NAME", "A"),
        ("T_SELECT", ":"),
        ("NAME", "B"),
    ]


def test_buff_t_argument_tokens(lexer):
    """A quoted increment is split into QUOTE, INT, NAME, QUOTE"""
    assert tokenize(lexer, 'buff_t(A, "10 months")') == [
        ("BUFF_T", "buff_t"),
        ("LPAREN", "("),
        ("NAME", "A"),
        ("COMMA", ","),
        ("QUOTE", '"'),
        ("INT", 10),
        ("NAME", "months"),
        ("QUOTE", '"'),
        ("RPAREN", ")"),
    ]


def test_condition_tokens(lexer):
    """A condition with a datetime literal is tokenized completely"""
    assert tokenize(lexer, 'if(start_datetime(A) >= "2001-02-15 15:00:00", A)') == [
        ("IF", "if"),
        ("LPAREN", "("),
        ("START_DATETIME", "start_datetime"),
        ("LPAREN", "("),
        ("NAME", "A"),
        ("RPAREN", ")"),
        ("GREATER_EQUALS", ">="),
        ("DATETIME", '"2001-02-15 15:00:00"'),
        ("COMMA", ","),
        ("NAME", "A"),
        ("RPAREN", ")"),
    ]


def test_lexer_instances_are_independent():
    """Two built lexers tokenize independently of each other"""
    first = TemporalAlgebraLexer()
    second = TemporalAlgebraLexer()
    first.build()
    second.build()
    first.lexer.input("A : B")
    second.lexer.input("C # D")
    assert first.lexer.token().value == "A"
    assert second.lexer.token().value == "C"
    assert first.lexer.token().type == "T_SELECT"
    assert second.lexer.token().type == "HASH"


def test_lexer_error_message_names_position(lexer):
    """The SyntaxError of an illegal character tells where it occurred"""
    with pytest.raises(SyntaxError, match=r"position 4 near '\$"):
        tokenize(lexer, "A : $B")


class TestGlobalTemporalVar:
    """GlobalTemporalVar stores one part of a condition and reports its kind"""

    def test_empty(self):
        """A new variable has no kind and an empty value list"""
        var = GlobalTemporalVar()
        assert var.get_type() is None
        assert var.get_type_value() == []
        assert var.topology == []

    def test_global(self):
        """Function, comparison operator and value together make a 'global'"""
        var = GlobalTemporalVar()
        var.tfunc = "START_DOY"
        var.compop = "=="
        var.value = 3
        assert var.get_type() == "global"
        assert var.get_type_value() == ["START_DOY", "==", 3]
        assert str(var) == "START_DOY==3"

    @pytest.mark.parametrize("missing", ["tfunc", "compop", "value"])
    def test_global_incomplete(self, missing):
        """Without one of the three parts it is not a 'global'"""
        var = GlobalTemporalVar()
        var.tfunc = "START_DOY"
        var.compop = "=="
        var.value = 3
        setattr(var, missing, None)
        assert var.get_type() is None

    def test_global_value_zero(self):
        """The value 0 is a value, not a missing one"""
        var = GlobalTemporalVar()
        var.tfunc = "START_HOUR"
        var.compop = ">"
        var.value = 0
        assert var.get_type() == "global"

    @pytest.mark.parametrize("value", [True, False])
    def test_boolean(self, value):
        """A boolean, including False, is a 'boolean'"""
        var = GlobalTemporalVar()
        var.boolean = value
        assert var.get_type() == "boolean"
        assert var.get_type_value() == value

    def test_operator(self):
        """Relation operator plus topology make an 'operator'"""
        var = GlobalTemporalVar()
        var.relationop = "&&"
        var.topology = ["EQUAL"]
        assert var.get_type() == "operator"
        assert var.get_type_value() == [["EQUAL"], "&&"]

    def test_operator_needs_topology(self):
        """An operator without topology is not an 'operator'"""
        var = GlobalTemporalVar()
        var.relationop = "&&"
        assert var.get_type() is None

    def test_timediff(self):
        """A time difference, also 0, is a 'timediff'"""
        var = GlobalTemporalVar()
        var.td = 0
        assert var.get_type() == "timediff"
        assert var.get_type_value() == [0]

    def test_str_of_empty(self):
        """__str__ concatenates the three parts of a condition"""
        assert str(GlobalTemporalVar()) == "NoneNoneNone"
