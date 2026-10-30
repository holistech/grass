"""Tests that run the options of plan(), materialize() and evaluate()

Each option that gives the classic rules is measured against the classic
algebra on real datasets: evaluate() with the option computes an expression,
and the result maps (names, times, values) or the exception class are compared
with grass.temporal.testing.differential to the outcome of the earlier
implementation (grass.temporal.testing.reference) that
grass.temporal.testing.corpus holds. The tests of the planned chain and of the
error texts run the earlier implementation itself. A negative check with the
default options shows that the comparison can see the difference. The expected
values are the results of the earlier implementation, run on 2026-10-16; none
was adjusted to a result.

The datasets of grass.temporal.testing.expressions_data are used (raster
and vector), and the dataset D, whose maps start on the same day.

The tests that need no session are in temporal_algebra_core_plan_options_test.py.
"""

import functools
import re

import pytest

import grass.temporal.algebra as ta
from grass.exceptions import FatalError
from grass.temporal.algebra import MapcalcStyle, Profile
from grass.temporal.algebra.parser import evaluate
from grass.temporal.testing import differential
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds, day
from grass.temporal.testing.reference import run_reference
from grass.tools import Tools

BARE = MapcalcStyle(quote_names=False, written_integers=True, bare_comparisons=True)


@pytest.fixture(scope="module")
def session(temporal_module_session, tmp_path_factory):
    directory = tmp_path_factory.mktemp("data")
    for kind in ("raster", "vector"):
        differential.prepare(kind, temporal_module_session, directory)
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    # d1 is registered first and ends last, so the order of the database
    # differs from the order of (start, end).
    create_stds(
        tools,
        "strds",
        "D",
        [
            MapSpec("d1", 1, day(0), day(4)),
            MapSpec("d2", 2, day(0), day(1)),
            MapSpec("d3", 3, day(0), day(2)),
        ],
    )
    return temporal_module_session


def with_profile(profile):
    """A runner with the signature of run_reference that evaluates with profile"""

    def run(kind, expression, *, basename, overwrite=False, **options):
        return differential.core_runner(
            kind,
            expression,
            basename=basename,
            overwrite=overwrite,
            profile=profile,
            **options,
        )

    return run


COUNTER = iter(range(10**6))


def measured(session, kind, expression, profile, **options):
    """The outcome of the earlier implementation and of the profile, and what
    differs between them (None if nothing)"""
    number = next(COUNTER)
    reference = reference_outcome(kind, expression, **options)
    found = differential.outcome(
        kind, expression, with_profile(profile), basename=f"p{number}", **options
    )
    return differential.compare(kind, expression, reference, found), reference, found


def agrees(session, kind, expression, profile, **options):
    """Assert that the profile gives what the earlier implementation gave;
    return the outcome of the earlier implementation"""
    difference, reference, _ = measured(session, kind, expression, profile, **options)
    assert difference is None, f"{expression}: {difference}"
    return reference


def differs(session, kind, expression, **options):
    """Assert that the core with default options differs from the earlier
    implementation, so that agrees() with an option is a real test of it"""
    difference, _, _ = measured(session, kind, expression, Profile(), **options)
    assert difference is not None, f"{expression}: no difference to see"


def test_the_database_order_of_equal_starts_is_that_of_the_classic_algebra(session):
    """The classic algebra lists d1, d2, d3 (the order of the database), the
    sorted series d2, d3, d1"""
    chain = run_reference(
        "raster", "R = D * 1", basename="q", overwrite=True, run=True, dry_run=True
    )
    classic = [end[:10] for _, _, end in chain["register"]]
    assert classic == ["2001-01-05", "2001-01-02", "2001-01-03"]
    option = evaluate(
        "R = D * 1",
        overwrite=True,
        dry_run=True,
        profile=Profile(database_order=True),
    )
    assert [end[:10] for _, _, end in option["register"]] == classic
    default = evaluate("R = D * 1", overwrite=True, dry_run=True)
    assert [end[:10] for _, _, end in default["register"]] != classic
    assert [slot.origin for slot in ta.source("D", order="start").slots] == [
        "d1@PERMANENT",
        "d2@PERMANENT",
        "d3@PERMANENT",
    ]


def test_source_refuses_an_unknown_order(session):
    with pytest.raises(ValueError, match="Unknown order"):
        ta.source("D", order="end")


def test_the_list_order_is_that_of_the_classic_algebra(session):
    chain = run_reference(
        "raster",
        "R = merge(B, A)",
        basename="q",
        overwrite=True,
        run=True,
        dry_run=True,
    )
    classic = [(name, start[:10]) for name, start, _ in chain["register"]]
    option = evaluate(
        "R = merge(B, A)",
        basename="q",
        overwrite=True,
        dry_run=True,
        profile=Profile(list_order=True),
    )
    assert [(name, start[:10]) for name, start, _ in option["register"]] == classic
    default = evaluate("R = merge(B, A)", basename="q", overwrite=True, dry_run=True)
    assert [(name, start[:10]) for name, start, _ in default["register"]] != classic


def test_results_are_computed_in_list_order_like_the_classic_algebra(session):
    """The maps of merge(B, A) are numbered B first, then A"""
    expression = "merge(B, A)"
    agrees(session, "raster", expression, Profile(list_order=True))
    differs(session, "raster", expression)


def test_an_empty_result_gets_the_given_temporal_type(session):
    import grass.temporal as tgis

    series = ta.Series((), "raster")
    ta.materialize(series, "EmptyRelative", temporal_type="relative", overwrite=True)
    dataset = tgis.open_old_stds("EmptyRelative", "strds")
    assert dataset.get_temporal_type() == "relative"
    ta.materialize(series, "EmptyAbsolute", overwrite=True)
    dataset = tgis.open_old_stds("EmptyAbsolute", "strds")
    assert dataset.get_temporal_type() == "absolute"


def test_a_selection_numbers_its_copies_like_the_classic_algebra(session):
    expression = "R = merge(A, tshift(A, '1 day'))"
    chain = run_reference(
        "select", expression, basename="q", overwrite=True, run=True, dry_run=True
    )
    classic = [name for name, _, _ in chain["register"]]
    profile = Profile(copies_by_position=True, list_order=True)
    names = [
        name.partition("@")[0]
        for name, _, _ in evaluate(
            expression,
            basename="q",
            selection=True,
            overwrite=True,
            dry_run=True,
            profile=profile,
        )["register"]
    ]
    assert names == classic
    assert classic[-1].startswith("q_")
    default = [
        name.partition("@")[0]
        for name, _, _ in evaluate(
            expression, basename="q", selection=True, overwrite=True, dry_run=True
        )["register"]
    ]
    assert default != classic


@pytest.mark.parametrize(
    "expression",
    [
        "A > 2",
        "if(A > 2 && N < 4, A, N)",
        "if(A > 3 || N < 2, A, N)",
        "A == N",
        "(A > 1) + (N <= 3)",
        "A * 7 - 2",
    ],
)
def test_the_plain_mapcalc_text_computes_the_same_maps_as_the_quoted_one(
    session, expression
):
    """No quotes, integers as written and bare comparisons give the maps of
    the default text. The comparisons are written in the syntax of the core:
    the grammar of the classic algebra takes them in conditions only."""
    plain = differential.outcome(
        "raster", expression, with_profile(Profile(mapcalc=BARE)), basename="a"
    )
    quoted = differential.outcome(
        "raster", expression, with_profile(Profile()), basename="b"
    )
    assert plain["maps"], "an empty result proves nothing"
    assert differential.compare("raster", expression, plain, quoted) is None


def test_the_plain_mapcalc_text_computes_the_maps_of_the_classic_algebra(session):
    agrees(session, "raster", "A * 7 - 2", Profile(mapcalc=BARE))


def test_integers_as_written_wrap_around_like_in_the_classic_algebra(session):
    """r.mapcalc wraps 3000000000 around to -1294967296; the core writes a
    float and keeps the value, the earlier implementation wraps (measured
    2026-10-16, A + 3000000000: -1294970000 against 3000000000)"""
    expression = "A + 3000000000"
    reference = agrees(
        session,
        "raster",
        expression,
        Profile(mapcalc=MapcalcStyle(written_integers=True)),
    )
    assert reference["maps"][0][3] == pytest.approx(-1294967296, rel=1e-5)
    differs(session, "raster", expression)


def test_the_plain_mapcalc_text_is_planned(session):
    chain = evaluate(
        "R = A > 2", overwrite=True, dry_run=True, profile=Profile(mapcalc=BARE)
    )
    assert dict(chain["processes"][0]["inputs"])["expression"] == "R_0=a1@PERMANENT > 2"


def test_the_union_region_of_a_spatial_run_computes_the_same_maps(session):
    expression = "A + N"
    agrees(
        session,
        "raster",
        expression,
        Profile(union_region_when_spatial=True),
        spatial=True,
    )


def test_the_union_region_is_planned_for_a_spatial_run(session):
    profile = Profile(union_region_when_spatial=True)
    chain = evaluate(
        "R = A + 1", overwrite=True, dry_run=True, spatial=True, profile=profile
    )
    assert dict(chain["processes"][0]["inputs"])["region"] == "union"
    # On 2026-10-16 the earlier implementation planned region=union for the
    # same expression in the same mode.
    classic = run_reference(
        "raster",
        "R = A + 1",
        basename="q",
        overwrite=True,
        run=True,
        dry_run=True,
        spatial=True,
    )
    assert dict(classic["processes"][0]["inputs"])["region"] == "union"
    default = evaluate("R = A + 1", overwrite=True, dry_run=True, spatial=True)
    assert "region" not in dict(default["processes"][0]["inputs"])


def test_an_empty_result_takes_the_temporal_type_of_the_first_dataset(session):
    expression = "RT {:, during} RT"
    profile = Profile(empty_result_type_from_input=True)
    reference = agrees(session, "raster", expression, profile)
    assert reference["ttype"] == "relative"
    assert reference["maps"] == []
    differs(session, "raster", expression)


@pytest.mark.parametrize(
    "expression", ["merge(A, RT)", "RT + A", "tshift(A, '1 day') + RT"]
)
def test_a_second_temporal_type_is_a_fatal_error(session, expression):
    reference = agrees(session, "raster", expression, Profile(one_temporal_type=True))
    assert reference["error"] == "FatalError"
    differs(session, "raster", expression)


@pytest.mark.parametrize(
    "expression",
    [
        "tshift(A, 5)",
        "buff_t(A, 5)",
        "buff_t(RT, '1 day')",
        "tshift(RT, '1 month')",
        "end_month(I, 0)",
        "start_month(RT, 0)",
        "A + start_month(RT, 1)",
        "if(end_month(I) == 1, I)",
    ],
)
def test_errors_have_the_class_of_the_classic_algebra(session, expression):
    reference = agrees(session, "raster", expression, Profile(classic_errors=True))
    assert reference["error"] in {"SyntaxError", "FatalError"}
    differs(session, "raster", expression)


def test_the_messages_of_the_classic_errors_are_the_classic_ones(session):
    """The words of a mapped FatalError are those of the classic algebra"""
    text = {}
    for name, runner in (
        ("classic", differential.reference_runner),
        ("profile", with_profile(Profile(classic_errors=True))),
    ):
        with pytest.raises(FatalError) as caught:
            runner(
                "raster", "R = end_month(I, 0)", basename="m", overwrite=True, run=True
            )
        text[name] = re.sub(r"<[^>]*>", "<>", str(caught.value))
    assert text["classic"] == text["profile"]
    assert "requires absolute time" in text["profile"]


def test_empty_vector_maps_are_registered_like_the_classic_algebra(session):
    expression = "aa & ac"
    reference = agrees(
        session, "vector", expression, Profile(keep_empty_vector_maps=True)
    )
    assert len(reference["maps"]) == 3
    differs(session, "vector", expression)


def test_a_vector_result_without_maps_has_no_dataset_like_the_classic_algebra(session):
    expression = "aa {&, contains} ab"
    reference = agrees(
        session, "vector", expression, Profile(vector_dataset_if_empty=False)
    )
    assert reference == {"stds": False}
    differs(session, "vector", expression)


@pytest.mark.parametrize("expression", ["buff_p(ac, 2) & ne", "buff_p(aa, 1) ^ ac"])
def test_dropped_vector_overlays_leave_no_dataset_like_the_classic_algebra(
    session, expression
):
    """Every overlay is dropped for an intermediate map without areas"""
    profile = Profile(vector_dataset_if_empty=False, keep_empty_vector_maps=True)
    reference = agrees(session, "vector", expression, profile)
    assert reference == {"stds": False}
    differs(session, "vector", expression)


def stds_exists(name, stds_type="strds"):
    import grass.temporal as tgis

    return tgis.dataset_factory(stds_type, f"{name}@PERMANENT").is_in_db()


def error_text(run):
    with pytest.raises(FatalError) as caught:
        run()
    return str(caught.value)


def test_existing_results_are_reported_like_the_classic_algebra(session):
    """Maps are looked at before the dataset, with the words of the classic
    algebra; the dry run does not look at the dataset"""
    tools = Tools(session=session, overwrite=True, quiet=True)
    series = ta.source("A") * 2
    classic = functools.partial(
        run_reference, "raster", "X = A * 2", basename="x", overwrite=False, run=True
    )
    classic()
    option = functools.partial(
        ta.materialize, series, "X", basename="x", classic_absence_check=True
    )

    # Maps and dataset exist
    expected = error_text(classic)
    assert expected.startswith("Error maps with basename x_0@PERMANENT exist.")
    assert error_text(option) == expected
    assert "Space time dataset <X@PERMANENT> exists" in error_text(
        functools.partial(ta.materialize, series, "X", basename="x")
    )

    # Only the dataset exists
    tools.g_remove(type="raster", name="x_0,x_1,x_2,x_3", flags="f")
    assert stds_exists("X")
    expected = error_text(
        functools.partial(
            run_reference,
            "raster",
            "X = A * 2",
            basename="y",
            overwrite=False,
            run=True,
        )
    )
    assert expected == (
        "Space time raster dataset <X> is already in the database. "
        "Use the overwrite flag."
    )
    option = functools.partial(
        ta.materialize, series, "X", basename="z", classic_absence_check=True
    )
    assert error_text(option) == expected

    # A dry run of both passes
    run_reference(
        "raster",
        "X = A * 2",
        basename="w",
        overwrite=False,
        run=True,
        dry_run=True,
    )
    evaluate(
        "X = A * 2",
        basename="w",
        dry_run=True,
        profile=Profile(classic_absence_check=True),
    )
    with pytest.raises(FatalError, match="exists"):
        evaluate("X = A * 2", basename="w", dry_run=True)
