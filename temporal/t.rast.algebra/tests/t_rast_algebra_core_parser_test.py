"""Tests for the parser of t.rast.algebra on the algebra core

The environment variable GRASS_TEMPORAL_ALGEBRA selects "core" or
"classic"; these tests set it explicitly, so they hold for either default.
"""

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal.algebra.parser.switch import classic_selected

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


def test_dry_run_refuses_an_existing_result_as_the_run(algebra, core):
    """Without overwrite a dry run stops where the run would stop: at the
    existing dataset, and at an existing map of a new dataset"""
    algebra.parse("A * 2", basename="r_dry")
    parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False, dry_run=True)
    with pytest.raises(FatalError, match=r"<R@\w+> exists\. Use the overwrite"):
        parser.parse("R = A * 2", "r_dry", False)
    algebra.remove("R")
    with pytest.raises(FatalError, match=r"<r_dry_0@\w+> exists\. Use the overwrite"):
        parser.parse("R = A * 2", "r_dry", False)
    assert parser.parse("R = A * 2", "r_dry_new", False)["register"]


@pytest.mark.parametrize(("overwrite", "flags"), [(True, ["overwrite"]), (False, [])])
def test_dry_run_flags_tell_overwrite(algebra, core, overwrite, flags):
    algebra.remove("R")
    parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False, dry_run=True)
    chain = parser.parse("R = A * 2", "r_flags", overwrite)
    assert [process["flags"] for process in chain["processes"]] == [flags] * 4


@pytest.mark.fixed_algebra
def test_core_is_the_default(algebra, monkeypatch):
    monkeypatch.delenv(VARIABLE, raising=False)
    chain = algebra.parse("A * 2", dry_run=True)
    assert '"r_0"' in expression_of(chain)


@pytest.mark.fixed_algebra
def test_an_empty_variable_selects_the_core(algebra, monkeypatch):
    """A script that writes GRASS_TEMPORAL_ALGEBRA= means no choice"""
    monkeypatch.setenv(VARIABLE, "")
    assert not classic_selected(None)
    chain = algebra.parse("A * 2", dry_run=True)
    assert '"r_0"' in expression_of(chain)


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("value", [" ", "\t", "bogus"])
def test_a_value_that_only_looks_empty_is_refused(algebra, monkeypatch, value):
    """Whitespace is more likely a mistake than an empty choice"""
    monkeypatch.setenv(VARIABLE, value)
    with pytest.raises(ValueError, match="core or classic"):
        classic_selected(None)
    with pytest.raises(ValueError, match="core or classic"):
        algebra.parse("A * 2", dry_run=True)


@pytest.mark.fixed_algebra
def test_classic_selects_the_classic_profile(algebra, classic):
    """The profile writes the r.mapcalc text of the classic algebra: the names
    unquoted"""
    chain = algebra.parse("A * 2", dry_run=True)
    assert expression_of(chain) == "r_0=(a1@PERMANENT * 2)"


@pytest.mark.fixed_algebra
def test_keyword_takes_precedence_over_the_variable(algebra, monkeypatch):
    monkeypatch.setenv(VARIABLE, "core")
    chain = algebra.parse("A * 2", dry_run=True, classic=True)
    assert expression_of(chain) == "r_0=(a1@PERMANENT * 2)"
    monkeypatch.setenv(VARIABLE, "classic")
    chain = algebra.parse("A * 2", dry_run=True, classic=False)
    assert '"r_0"' in expression_of(chain)


@pytest.mark.fixed_algebra
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


def test_granularity_mode_runs_the_core(algebra, core):
    """B has maps of two days; sampled by the day of A, each counts for two
    days, so that A + B has a map for each of the four days"""
    chain = algebra.parse("A + B", dry_run=True, granularity=True)
    assert expression_of(chain) == '"r_0"=("a1@PERMANENT" + "b1@PERMANENT")'
    assert [entry[1:] for entry in chain["register"]] == [
        (f"2001-01-0{day} 00:00:00", f"2001-01-0{day + 1} 00:00:00")
        for day in range(1, 5)
    ]


@pytest.mark.fixed_algebra
def test_granularity_mode_runs_the_classic_algebra_when_chosen(algebra, classic):
    chain = algebra.parse("A + B", dry_run=True, granularity=True)
    # The classic algebra neither quotes map names nor numbers its results
    # this way.
    assert '"r_0"' not in expression_of(chain)
    assert len(chain["register"]) == 4


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


@pytest.mark.fixed_algebra
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
