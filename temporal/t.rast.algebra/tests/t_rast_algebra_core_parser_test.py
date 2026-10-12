"""Tests for the parser of t.rast.algebra on the algebra core

The environment variable GRASS_TEMPORAL_ALGEBRA selects "core" or
"classic"; these tests set it explicitly, so they hold for either default.
"""

import pytest

import grass.temporal as tgis

VARIABLE = "GRASS_TEMPORAL_ALGEBRA"


@pytest.fixture
def core(monkeypatch):
    monkeypatch.setenv(VARIABLE, "core")


@pytest.fixture
def classic(monkeypatch):
    monkeypatch.setenv(VARIABLE, "classic")


def expression_of(chain):
    (process,) = chain["processes"][:1]
    return dict(process["inputs"])["expression"]


def test_dry_run_gives_the_process_chain(algebra, core):
    chain = algebra.parse("A * 2", dry_run=True)
    assert set(chain) == {"processes", "register", "remove", "STDS"}
    assert expression_of(chain) == '"r_0"=("a1@PERMANENT" * 2)'
    assert chain["register"][0] == ("r_0", "2001-01-01 00:00:00", "2001-01-02 00:00:00")
    assert chain["STDS"] == {
        "name": "R",
        "stdstype": "strds",
        "temporal_type": "absolute",
    }
    assert chain["remove"] == []
    assert not algebra.exists()


def test_core_is_the_default(algebra, monkeypatch):
    monkeypatch.delenv(VARIABLE, raising=False)
    chain = algebra.parse("A * 2", dry_run=True)
    assert '"r_0"' in expression_of(chain)


def test_classic_selects_the_earlier_parser(algebra, classic):
    chain = algebra.parse("A * 2", dry_run=True)
    assert '"r_0"' not in expression_of(chain)


def test_keyword_takes_precedence_over_the_variable(algebra, monkeypatch):
    monkeypatch.setenv(VARIABLE, "core")
    chain = algebra.parse("A * 2", dry_run=True, classic=True)
    assert '"r_0"' not in expression_of(chain)
    monkeypatch.setenv(VARIABLE, "classic")
    chain = algebra.parse("A * 2", dry_run=True, classic=False)
    assert '"r_0"' in expression_of(chain)


def test_unknown_parser_is_an_error(algebra, monkeypatch):
    monkeypatch.setenv(VARIABLE, "other")
    with pytest.raises(ValueError, match="core or classic"):
        algebra.parse("A * 2", dry_run=True)


def test_run_computes_and_registers(algebra, core):
    assert algebra.triples("B {:,contains,r} A") == [
        (1, 2, 5),
        (2, 3, 5),
        (3, 4, 6),
        (4, 5, 6),
    ]


def test_without_run_only_the_syntax_is_checked(algebra, core):
    parser = tgis.TemporalRasterAlgebraParser(run=False, debug=False)
    assert parser.parse("R = no_such_dataset + 1", "r", True) == {
        "processes": [],
        "register": [],
        "remove": [],
        "STDS": {},
    }
    with pytest.raises(SyntaxError):
        parser.parse("R = A +", "r", True)


def test_granularity_mode_keeps_the_earlier_parser(algebra, core):
    parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False, dry_run=True)
    assert parser.setup_common_granularity(
        expression="R = A * 2", lexer=tgis.TemporalRasterAlgebraLexer()
    )
    chain = parser.parse("R = A * 2", "r", True)
    assert '"r_0"' not in expression_of(chain)


def test_debug_prints_the_module_calls(algebra, core, capsys):
    algebra.parse("A * 2", dry_run=True, debug=True)
    assert 'r.mapcalc expression="r_0"=("a1@PERMANENT" * 2)' in capsys.readouterr().out


def test_empty_result_creates_an_empty_dataset(algebra, core):
    assert algebra.run("if(td(A) > 5, A)") == []
    assert algebra.exists()


def test_pairing_error_reaches_the_caller(algebra, core):
    """Two maps of one time cannot be paired with the four maps of E"""
    tools = algebra.tools
    tools.r_mapcalc(expression="e2a = 1")
    tools.r_mapcalc(expression="e2b = 2")
    tools.t_create(
        output="E2", type="strds", temporaltype="absolute", title="E2", description="E2"
    )
    tools.t_register(input="E2", maps="e2a,e2b", start="2001-01-01")
    with pytest.raises(ValueError, match="cannot be paired"):
        algebra.run("if(start_day(E2) == 1, E)")


def test_spatial_relations_agree_with_the_earlier_parser(
    algebra, monkeypatch, large_region
):
    expression = "SA {+,equal|equivalent} SB"
    monkeypatch.setenv(VARIABLE, "classic")
    expected = algebra.run(expression, spatial=True)
    monkeypatch.setenv(VARIABLE, "core")
    assert algebra.run(expression, spatial=True) == expected
    with pytest.raises(ValueError, match="need the spatial flag"):
        algebra.run(expression)
