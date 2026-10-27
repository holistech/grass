"""Tests for grass.temporal.testing.reference

The helper must run the earlier implementation of the algebra whatever
GRASS_TEMPORAL_ALGEBRA says, so the tests set the variable to each value and
compare with the algebra core, which they call directly.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.temporal as tgis
from grass.temporal import TemporalRasterAlgebraParser
from grass.temporal.algebra.parser import evaluate
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.readback import list_maps
from grass.temporal.testing.reference import (
    reference_parser,
    run_reference,
    sample_by_dataset,
)
from grass.tools import Tools

# B (10 on days 0 to 2, 20 on days 2 to 4) contains a1 and a2, and b2 contains
# a3 and a4. A selection with the right reference gives one map per related
# pair in the core: 10, 10, 20, 20. The classic algebra keeps only the last
# pair of each map of B: 10, 20. The expression is one of the listed
# differences in t_rast_algebra_differential_test.py.
DIFFERENT_EXPRESSION = "R = B {:,contains,r} A"
CLASSIC_MAXIMA = [10.0, 20.0]
CORE_MAXIMA = [10.0, 10.0, 20.0, 20.0]


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
        "strds",
        "B",
        [MapSpec("b1", 10, day(0), day(2)), MapSpec("b2", 20, day(2), day(4))],
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


# The tests that take this fixture change os.environ and run grass.temporal in
# this process, so they carry needs_solo_run (doc/development/testing.md).
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
def test_classic_parser_class_computes_on_the_profile(tools, algebra_variable):
    """The parser class with classic=True gives the classic maxima although
    it no longer runs the earlier implementation: the expression is a listed
    difference of the core"""
    parser = TemporalRasterAlgebraParser(run=True, debug=False, classic=True)
    parser.parse(DIFFERENT_EXPRESSION, "prof", True)
    assert maxima(tools, "R") == CLASSIC_MAXIMA
    assert "parse" not in vars(parser)


@pytest.mark.needs_solo_run
@pytest.mark.parametrize(
    ("kind", "class_name", "expression"),
    [
        ("raster", "TemporalRasterAlgebraParser", "R = A + 1"),
        ("raster3d", "TemporalRaster3DAlgebraParser", "R = A + 1"),
        ("vector", "TemporalVectorAlgebraParser", "R = V & V"),
    ],
)
def test_reference_parser_is_the_engine_and_not_the_public_class(
    tools, monkeypatch, algebra_variable, kind, class_name, expression
):
    """The public class chooses between the core and the classic profile in
    parse(). The reference is an object of the classic engine, which does not
    inherit from it, so what the public class does is not on its way. (t.select
    has no such class: its reference is the engine itself, and
    test_every_kind_parses runs it under each setting of the variable.)"""
    public_class = getattr(tgis, class_name)

    def rerouted(*args, **kwargs):
        msg = "the routing parse() was called"
        raise AssertionError(msg)

    # Negative control: the patched class does fail when it is the one called.
    monkeypatch.setattr(public_class, "parse", rerouted)
    with pytest.raises(AssertionError, match="routing parse"):
        public_class(run=False, debug=False).parse(expression, "x", True)
    parser = reference_parser(kind, run=False, debug=False)
    assert not isinstance(parser, public_class)
    assert type(parser).__module__.startswith("grass.temporal.classic.")
    parser.parse(expression, basename="x", overwrite=True)


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


@pytest.mark.needs_solo_run
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


@pytest.mark.parametrize("temporaltype", ["absolute", "relative"])
def test_the_reference_sampling_puts_no_gap_next_to_a_map_without_time(
    tools, temporaltype
):
    prefix = f"nogap_{temporaltype}"
    spans = [(0, 1), (2, 3), (4, 5)]
    times = spans
    options = {"temporaltype": temporaltype}
    if temporaltype == "absolute":
        times = [(day(start), day(end)) for start, end in spans]
    else:
        options["unit"] = "days"
    for name, maps in (
        (f"{prefix}_sampled", [MapSpec(f"{prefix}_s", 1, *times[0])]),
        (
            f"{prefix}_sampler",
            [
                MapSpec(f"{prefix}_{number}", number, start, end)
                for number, (start, end) in enumerate(times, 1)
            ],
        ),
    ):
        create_stds(tools, "strds", name, maps, via="library", **options)

    mapset = tgis.get_current_mapset()
    middle = tgis.RasterDataset(f"{prefix}_2@{mapset}")
    middle.select()
    extent = (
        middle.absolute_time if temporaltype == "absolute" else middle.relative_time
    )
    # The setter and update() do not check the order of start and end, so the
    # row is stored reversed and the reader turns it into a map without time.
    extent.set_end_time(day(1) if temporaltype == "absolute" else 1)
    extent.update()

    stds = tgis.open_old_stds(f"{prefix}_sampled", "strds")
    sampler = tgis.open_old_stds(f"{prefix}_sampler", "strds")
    granules = sample_by_dataset(stds, sampler, ["start"])

    assert [item["granule"].get_id() for item in granules] == [
        f"{prefix}_{number}@{mapset}" for number in (1, 2, 3)
    ]
