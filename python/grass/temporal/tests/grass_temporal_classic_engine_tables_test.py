"""The tables of the classic algebra engine, pinned against a recording

PLY derives the lexer and the LALR tables of the classic algebra from the
order of the rule functions: lexer rules are ordered by the line number of
their function, grammar rules by the line number of their ``p_`` function, and
both orders run across the files of a class hierarchy. Moving or editing the
files of the engine can reorder them silently, and a reordered table changes
which of two ambiguous parses wins, i.e. the results the publications cite.
The recording in ``data/classic_engine_tables.json`` was taken before the
engine was moved into ``grass.temporal.classic``; it holds, per lexer class,
the order and the text of the token rules and, per parser class, a checksum of
the productions and of the action and goto tables.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import hashlib
import json
import types
from pathlib import Path

import pytest

from grass.temporal.temporal_algebra import (
    TemporalAlgebraLexer,
    TemporalAlgebraParser,
)
from grass.temporal.temporal_operator import (
    TemporalOperatorLexer,
    TemporalOperatorParser,
)
from grass.temporal.temporal_raster3d_algebra import (
    TemporalRaster3DAlgebraParser,
)
from grass.temporal.temporal_raster_algebra import (
    TemporalRasterAlgebraParser,
)
from grass.temporal.temporal_raster_base_algebra import (
    TemporalRasterAlgebraLexer,
)
from grass.temporal.temporal_vector_algebra import (
    TemporalVectorAlgebraLexer,
    TemporalVectorAlgebraParser,
)
from grass.temporal.ply import yacc

RECORDING = Path(__file__).parent / "data" / "classic_engine_tables.json"

LEXERS = {
    "TemporalAlgebraLexer": TemporalAlgebraLexer,
    "TemporalRasterAlgebraLexer": TemporalRasterAlgebraLexer,
    "TemporalVectorAlgebraLexer": TemporalVectorAlgebraLexer,
    "TemporalOperatorLexer": TemporalOperatorLexer,
}

PARSERS = {
    "TemporalAlgebraParser": TemporalAlgebraParser,
    "TemporalRasterAlgebraParser": TemporalRasterAlgebraParser,
    "TemporalRaster3DAlgebraParser": TemporalRaster3DAlgebraParser,
    "TemporalVectorAlgebraParser": TemporalVectorAlgebraParser,
}


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def lexer_record(lexer_class):
    """Order of the token rules and a checksum of their regular expressions"""
    lexer = lexer_class()
    lexer.build()
    states = lexer.lexer.lexstatere
    texts = lexer.lexer.lexstateretext
    return {
        state: {
            "order": [
                entry[1]
                for table in states[state]
                for entry in table[1]
                if entry is not None
            ],
            "regex": _digest("\n".join(texts[state])),
        }
        for state in sorted(states)
    }


def parser_record(parser_class):
    """Checksums of the productions and the LALR tables of a grammar"""
    # TemporalOperatorParser is a class-level grammar. The others bind to an
    # instance, which is made without __init__: the grammar does not depend on
    # the state that __init__ sets up, and that needs a database.
    if parser_class is TemporalOperatorParser:
        module = parser_class
    else:
        module = parser_class.__new__(parser_class)
        module.dbif = types.SimpleNamespace(connected=False)
    built = yacc.yacc(module=module, debug=False)
    return {
        "productions": _digest("\n".join(str(p) for p in built.productions)),
        "action": _digest(json.dumps(sorted(built.action.items()), default=str)),
        "goto": _digest(json.dumps(sorted(built.goto.items()), default=str)),
        "states": len(built.action),
    }


def current():
    """The record of the engine as it is now"""
    return {
        "lexers": {name: lexer_record(cls) for name, cls in LEXERS.items()},
        "parsers": {
            name: parser_record(cls)
            for name, cls in {
                **PARSERS,
                "TemporalOperatorParser": TemporalOperatorParser,
            }.items()
        },
    }


RECORDED = (
    json.loads(RECORDING.read_text(encoding="utf-8")) if RECORDING.exists() else {}
)


@pytest.mark.parametrize("name", sorted(LEXERS))
def test_the_token_rules_of_a_lexer_keep_their_order(name):
    assert lexer_record(LEXERS[name]) == RECORDED["lexers"][name]


@pytest.mark.parametrize("name", [*sorted(PARSERS), "TemporalOperatorParser"])
def test_the_tables_of_a_parser_keep_their_checksum(name):
    cls = {**PARSERS, "TemporalOperatorParser": TemporalOperatorParser}[name]
    assert parser_record(cls) == RECORDED["parsers"][name]
