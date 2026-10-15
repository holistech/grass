"""Tests for grass.temporal.testing.reference

The helper must run the earlier implementation of the algebra whatever
GRASS_TEMPORAL_ALGEBRA says, so the tests set the variable to each value and
compare with the algebra core, which they call directly.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

from grass.temporal.algebra.parser import evaluate
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.temporal_raster_algebra import TemporalRasterAlgebraParser
from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps
from grass.temporal.testing.reference import reference_parser, run_reference
from grass.tools import Tools

# The classic algebra keeps a null map for each map of A where the condition
# is false, the core drops them. The expression is one of the listed
# differences in t_rast_algebra_differential_test.py.
DIFFERENT_EXPRESSION = "R = if(A > 2, A)"
CLASSIC_MAXIMA = [0.0, 0.0, 3.0, 4.0]
CORE_MAXIMA = [3.0, 4.0]


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True)
    create_stds(
        tools,
        "strds",
        "A",
        [
            MapSpec(f"a{number}", number, day(number - 1), day(number))
            for number in range(1, 5)
        ],
    )
    create_stds(
        tools,
        "stvds",
        "V",
        [
            MapSpec(f"v{number}", number, day(number - 1), day(number))
            for number in (1, 2)
        ],
    )
    return tools


@pytest.fixture(params=[None, "core", "classic"], ids=["unset", "core", "classic"])
def algebra_variable(request, monkeypatch):
    if request.param is None:
        monkeypatch.delenv(ALGEBRA_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(ALGEBRA_VARIABLE, request.param)
    return request.param


def maxima(tools, name):
    return [row.max for row in list_maps(tools, "strds", name)]


@pytest.mark.needs_solo_run
def test_reference_is_classic_and_core_is_not(tools, algebra_variable):
    environment = dict(os.environ)
    run_reference(
        "raster",
        DIFFERENT_EXPRESSION,
        basename="ref",
        run=True,
        debug=False,
        overwrite=True,
    )
    assert maxima(tools, "R") == CLASSIC_MAXIMA
    evaluate(
        DIFFERENT_EXPRESSION,
        basename="core",
        overwrite=True,
        run=True,
        debug=False,
    )
    assert maxima(tools, "R") == CORE_MAXIMA
    assert dict(os.environ) == environment


@pytest.mark.needs_solo_run
def test_reference_parser_binds_the_earlier_parse(tools, algebra_variable):
    """The instance carries its own parse, not the one of the routing class"""
    parser = reference_parser("raster", run=True, debug=False)
    assert "parse" in vars(parser)


@pytest.mark.needs_solo_run
def test_reference_parser_survives_a_rerouted_class(tools, monkeypatch):
    def rerouted(*args, **kwargs):
        msg = "the routing parse() was called"
        raise AssertionError(msg)

    monkeypatch.setattr(TemporalRasterAlgebraParser, "parse", rerouted)
    parser = reference_parser("raster", run=False, debug=False)
    parser.parse("R = A + 1", basename="x", overwrite=True)


@pytest.mark.needs_solo_run
def test_parse_only_accepts_and_rejects(tools, algebra_variable):
    chain = run_reference(
        "raster", "R = A + 1", basename="x", run=False, debug=False, overwrite=True
    )
    assert "register" in chain
    # A dataset alone is no expression of the classic grammar.
    with pytest.raises(SyntaxError):
        run_reference("raster", "R = A", basename="x", run=False, debug=False)


@pytest.mark.needs_solo_run
@pytest.mark.parametrize(
    ("kind", "expression", "options"),
    [
        ("raster3d", "R = A + 1", {}),
        ("vector", "R = V & V", {}),
        ("select", "R = A : A", {"stdstype": "strds"}),
    ],
)
def test_every_kind_parses(tools, algebra_variable, kind, expression, options):
    chain = run_reference(
        kind,
        expression,
        basename="x",
        overwrite=True,
        run=False,
        debug=False,
        **options,
    )
    assert set(chain) >= {"processes", "register"}


def test_select_returns_the_chain_of_the_registered_maps(tools, algebra_variable):
    chain = run_reference(
        "select", "S = A : A", basename="S", overwrite=True, stdstype="strds"
    )
    assert [name for name, _start, _end in chain["register"]] == [
        "a1",
        "a2",
        "a3",
        "a4",
    ]
    assert chain["STDS"]["name"] == "S"


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError, match="raster3d"):
        reference_parser("raster2d")
