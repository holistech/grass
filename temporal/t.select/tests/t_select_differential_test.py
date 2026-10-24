"""Comparison of the algebra core with the classic algebra for t.select

Both algebras select from the same datasets (conftest.py); the registered
maps (identifier, start day, end day) must agree, except for the differences
listed in the manual between the core and the classic algebra.
"""

import itertools
from datetime import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.algebra.parser import evaluate
from grass.temporal.algebra.parser.switch import ALGEBRA_VARIABLE
from grass.temporal.algebra.profile import CLASSIC
from grass.temporal.testing import expressions
from grass.temporal.testing.corpus import reference_outcome
from grass.tools import Tools

DAY0 = datetime(2001, 1, 1)
counter = itertools.count()

SAME = [
    "A : B",
    "A !: B",
    "A {:, during} B",
    "A {:, contains} B",
    "A {:, over} B",
    "A {:,during,l} D",
    "A {:,during,r} D",
    "A {:,overlaps,i} B",
    "A {:,overlaps,u} B",
    "A {:,overlaps,d} B",
    "A : B !: D",
    "A {:,during} B {:,during} D",
    "A {:,equal} B {:,equal} B",
    "if(start_doy(A) > 20, A)",
    "if(start_doy(A) > 20, A, B)",
    "if(A {#, contains} B > 1, A)",
    "if(td(A) == 10, A) : B",
    "if({equal}, A {#, contains} B > 1, A {:, contains} B)",
    "tsnap(A)",
    'A : tshift(B, "5 days")',
    'buff_t(A, "1 days") {:,contains} B',
    'buff_t(A, "1 days") {:,overlaps} B',
    # b2 [22,27) and b9 [28,29) lie inside the shrunk a3 [21,29)
    'buff_t(A, "-1 days") {:,contains} B',
    'buff_t(A, "-1 days") {:,during} D',
    "A : X@other",
    "X@other {:, precedes} A",
]

# Each changed rule with the item of the manual's difference list, and what
# the core gives: "maps" for the registered maps (possibly none) or the name
# of the error, so that a crash does not pass for a difference. The marker is
# the core's outcome, which the test asserts. The mixed-result case, where
# both algebras register maps and only the copy numbers differ, is checked
# separately below, because this comparison cannot see the numbers.
DIFFERENT = {
    # The core reads the neighbourhood modifier A[1] and copies the shifted
    # map; the classic base grammar reports a syntax error.
    "A[1]": ("maps", "the core reads A[1] and A[-1]"),
    # The core reads the name of a spatial relation, with and without -s; the
    # classic algebra does not know it (see also the test with the flag below).
    "A {:,equal|overlap} B": ("maps", "the core reads spatial relations"),
    # The core reads an expression that is only a dataset, the classic base
    # grammar reports a syntax error.
    "A": ("maps", "the core reads a bare dataset"),
    # A computed result is no selection on the core.
    "A + B": ("ValueError", "t.select selects maps, it computes none"),
    # A negative buffer that leaves a map no time is an error on the core;
    # the classic algebra makes instants (end == start) without a message or
    # keeps the old time (end < start) and prints one ERROR line per map
    # ("End time must be greater than start time ...", exit code 0).
    'buff_t(A, "-5 days") {:,during} D': (
        "ValueError",
        "a negative buffer must leave every map some time",
    ),
    'buff_t(A, "-6 days") {:,during} D': (
        "ValueError",
        "a negative buffer must leave every map some time",
    ),
    # The core refuses a time function as the conclusion of if(); the classic
    # algebra only where its value would be selected. a1, the only map that
    # meets the condition, has no predecessor, so else gives a2 to a4.
    "if(start_doy(A) < 3, start_doy(A, -1), A)": (
        "ValueError",
        "the core refuses a time function as the conclusion of if()",
    ),
}


@pytest.fixture(autouse=True)
def algebra():
    """Each test here runs both algebras itself, so the parametrized fixture
    of conftest.py, which would run every test twice, is replaced"""


def selected(session, expression, algebra):
    """The registered maps of a tool run as (identifier without the result
    name, start day, end day), through the subprocess the session chooses"""
    name = f"diff_{algebra}_{next(counter)}"
    env = dict(session.env, **{ALGEBRA_VARIABLE: algebra})
    tools = Tools(session=session, overwrite=True, env=env)
    tools.t_select(expression=f"{name} = {expression}")
    listing = tools.t_rast_list(
        input=name, columns="id,start_time,end_time", format="json"
    )
    rows = []
    for row in listing["data"]:
        start = (datetime.strptime(row["start_time"], "%Y-%m-%d %H:%M:%S") - DAY0).days
        end = (datetime.strptime(row["end_time"], "%Y-%m-%d %H:%M:%S") - DAY0).days
        rows.append((row["id"].replace(name, "C", 1), start, end))
    return sorted(rows)


@pytest.mark.parametrize("expression", SAME)
def test_same_result(series, expression):
    core = selected(series.session, expression, "core")
    classic = selected(series.session, expression, "classic")
    assert core == classic
    # Two empty results are equal, so they would compare nothing.
    assert core, "the expression selects no map and compares nothing"


def outcome(expression, algebra, spatial=False):
    """The word "maps" for a result dataset, None for none, or the error name

    The parsers run in this process, so that the error class is visible; the
    core and the classic profile take evaluate(..., selection=True), each into
    its own result dataset.
    """
    name = f"diff_{algebra}_{next(counter)}"
    try:
        evaluate(
            f"{name} = {expression}",
            kind="raster",
            basename=name,
            overwrite=True,
            run=True,
            spatial=spatial,
            selection=True,
            **({"profile": CLASSIC} if algebra == "classic" else {}),
        )
    except (SyntaxError, ValueError, TypeError, tgis.FatalError) as error:
        return type(error).__name__
    dataset = tgis.dataset_factory("strds", f"{name}@{tgis.get_current_mapset()}")
    if not dataset.is_in_db():
        return None
    return "maps"


@pytest.mark.parametrize("expression", sorted(DIFFERENT))
def test_listed_differences_still_differ(series, expression):
    """A listed difference that no longer differs must leave the list"""
    core = outcome(expression, "core")
    classic = outcome(expression, "classic")
    assert core != classic, DIFFERENT[expression][1]
    assert core == DIFFERENT[expression][0]


def test_spatial_relation_is_read_by_the_core_only(series):
    """The core reads the spatial relation and selects maps, with and without
    -s; the classic algebra reports a syntax error for the name, with or
    without -s"""
    expression = "A {:,equal|overlap} B"
    assert outcome(expression, "core") == "maps"
    assert outcome(expression, "core", spatial=True) == "maps"
    assert outcome(expression, "classic", spatial=True) == "SyntaxError"


def test_right_reference_gives_one_map_per_pair(series):
    """a3 contains b2 and b9: the core registers a map for each pair, the
    classic algebra only the last pair of each map of A (measured
    2026-10-14 on this fixture: 4 maps against 3, the map of b2 missing)"""
    expression = "A {:,contains,r} B"
    core = selected(series.session, expression, "core")
    classic = selected(series.session, expression, "classic")
    assert [(start, end) for _, start, end in core] == [
        (0, 4),
        (22, 27),
        (28, 29),
        (35, 40),
    ]
    assert [(start, end) for _, start, end in classic] == [(0, 4), (28, 29), (35, 40)]


def test_mixed_result_copies_are_numbered_differently(series):
    """A result that mixes maps registered unchanged with retimed copies:
    both algebras register the same unchanged maps with the same times, but
    the classic algebra numbers the copies among all result maps, so the copy
    suffixes differ while the maps and their times stay the same"""
    expression = "merge(A {:,during,l} D, A {:,during,r} D)"
    core = selected(series.session, expression, "core")
    classic = selected(series.session, expression, "classic")
    assert sorted((start, end) for _, start, end in core) == sorted(
        (start, end) for _, start, end in classic
    )
    kept_core = [i for i, _, _ in core if not i.startswith("C_")]
    kept_classic = [i for i, _, _ in classic if not i.startswith("C_")]
    assert kept_core == kept_classic == ["a2@PERMANENT", "a3@PERMANENT", "a4@PERMANENT"]
    assert [i for i, _, _ in core if i.startswith("C_")] == [
        "C_1@PERMANENT",
        "C_2@PERMANENT",
        "C_3@PERMANENT",
    ]
    assert [i for i, _, _ in classic if i.startswith("C_")] == [
        "C_4@PERMANENT",
        "C_5@PERMANENT",
        "C_6@PERMANENT",
    ]


@pytest.mark.parametrize("expression", [*SAME, *sorted(DIFFERENT)])
def test_profile_equals_reference(series, expression):
    """-c selects what the earlier implementation of the classic algebra
    selected, also where the core differs"""
    # The result of the earlier implementation comes from the recorded corpus,
    # which stores the form of expressions.outcome(), so the profile is read in
    # that form as well. That form names each map without its mapset; it
    # also compares the values, to 6 significant digits, which the form of
    # outcome() above leaves out.
    reference = reference_outcome("select", expression, stdstype="strds")
    profile = selection_outcome("classic", "fb", expression)
    assert expressions.compare("select", expression, reference, profile) is None
    if expression in SAME:
        # Two errors or two empty results are equal and would compare nothing.
        assert profile.get("maps")
        assert profile["maps"][0][1] is not None


TIME_FUNCTION_SELECTED = "if(start_doy(A)<3,start_doy(A, 1), A)"

# Results that hold a value of a time function, also one moved in time
TIME_FUNCTION_RESULTS = [
    TIME_FUNCTION_SELECTED,
    "start_doy(A, 1)",
    'tshift(start_doy(A, 1), "1 day")',
]


def selection_outcome(
    runner, basename, expression=TIME_FUNCTION_SELECTED, stdstype="strds"
):
    return expressions.outcome(
        "select",
        expression,
        expressions.RUNNERS[runner],
        basename=basename,
        stdstype=stdstype,
    )


def test_the_reference_fails_on_a_time_function_as_the_selected_maps(series):
    """The earlier implementation never computes the value of start_doy(A, 1)
    and fails when it copies that map into the result"""
    reference = selection_outcome("reference", "tfref")
    assert reference["error"] == "Other:CalledModuleError"
    assert "g.copy raster=tmp_map_name_" in reference["msg"]


@pytest.mark.parametrize("stdstype", ["strds", "stvds", "str3ds"])
@pytest.mark.parametrize("expression", TIME_FUNCTION_RESULTS)
def test_the_error_pair_of_a_time_function_as_the_selected_maps_is_accepted(
    series, expression, stdstype
):
    """The profile refuses what the reference fails to copy, and the pair is
    accepted for exactly this class, whatever the map type"""
    reference = reference_outcome("select", expression, stdstype=stdstype)
    profile = selection_outcome("classic", "tfpro", expression, stdstype)
    assert reference["error"] == "Other:CalledModuleError"
    assert profile["error"] == "Other:ValueError"
    assert expressions.accepted_error_pair(
        "select", expression, reference, profile
    ) == ("Other:CalledModuleError/Other:ValueError")
    assert expressions.compare_runs("select", expression, reference, profile) is None


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # A failed copy of a map that is not a temporary one
        (
            {"error": "Other:CalledModuleError", "msg": "g.copy raster=a@x,b"},
            {
                "error": "Other:ValueError",
                "msg": "A time function such as start_doy()"
                " cannot be the result of a selection: more",
            },
        ),
        # Another ValueError of the profile
        (
            {"error": "Other:CalledModuleError", "msg": "g.copy raster=tmp_map_name_1"},
            {"error": "Other:ValueError", "msg": "t.select selects maps"},
        ),
        # Another failing module of the reference
        (
            {"error": "Other:CalledModuleError", "msg": "r.mapcalc expression=a"},
            {
                "error": "Other:ValueError",
                "msg": "A time function such as start_doy()"
                " cannot be the result of a selection: more",
            },
        ),
    ],
)
def test_other_pairs_with_a_value_error_are_differences(first, second):
    """Only the class of the time function is accepted"""
    assert expressions.accepted_error_pair("select", "A", first, second) is None
