"""Tests for the parser of t.rast.algebra on the algebra core"""

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError


def expression_of(chain):
    (process,) = chain["processes"][:1]
    return dict(process["inputs"])["expression"]


def test_dry_run_gives_the_process_chain(algebra):
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


def test_dry_run_refuses_an_existing_result_as_the_run(algebra):
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
def test_dry_run_flags_tell_overwrite(algebra, overwrite, flags):
    algebra.remove("R")
    parser = tgis.TemporalRasterAlgebraParser(run=True, debug=False, dry_run=True)
    chain = parser.parse("R = A * 2", "r_flags", overwrite)
    assert [process["flags"] for process in chain["processes"]] == [flags] * 4


def test_run_computes_and_registers(algebra):
    assert algebra.triples("B {:,contains,r} A") == [
        (1, 2, 5),
        (2, 3, 5),
        (3, 4, 6),
        (4, 5, 6),
    ]


def test_without_run_only_the_syntax_is_checked(algebra):
    parser = tgis.TemporalRasterAlgebraParser(run=False, debug=False)
    assert parser.parse("R = no_such_dataset + 1", "r", True) == {
        "processes": [],
        "register": [],
        "remove": [],
        "STDS": {},
    }
    with pytest.raises(SyntaxError):
        parser.parse("R = A +", "r", True)


def test_granularity_mode_runs_the_core(algebra):
    """B has maps of two days; sampled by the day of A, each counts for two
    days, so that A + B has a map for each of the four days"""
    chain = algebra.parse("A + B", dry_run=True, granularity=True)
    assert expression_of(chain) == '"r_0"=("a1@PERMANENT" + "b1@PERMANENT")'
    assert [entry[1:] for entry in chain["register"]] == [
        (f"2001-01-0{day} 00:00:00", f"2001-01-0{day + 1} 00:00:00")
        for day in range(1, 5)
    ]


def test_debug_prints_the_module_calls(algebra, capsys):
    algebra.parse("A * 2", dry_run=True, debug=True)
    assert 'r.mapcalc expression="r_0"=("a1@PERMANENT" * 2)' in capsys.readouterr().out


def test_empty_result_creates_an_empty_dataset(algebra):
    assert algebra.run("if(td(A) > 5, A)") == []
    assert algebra.exists()


def test_pairing_error_reaches_the_caller(algebra):
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


def test_spatial_relations_build_the_topology_also_without_s(algebra, large_region):
    """The name of a spatial relation builds the spatial topology with and
    without -s. spa<i> and spb<i> are spatially equal, so each pair adds up
    to 2 * i."""
    expression = "SA {+,equal|equivalent} SB"
    expected = algebra.run(expression, spatial=True)
    assert [row.min for row in expected] == [2, 4, 6, 8]
    assert algebra.run(expression) == expected
