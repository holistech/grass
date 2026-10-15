"""Tests of TemporalAlgebraParser on registered space time datasets.

The base parser is what t.select uses: selection, temporal relations,
conditions on temporal functions, buffering, shifting and snapping of
time stamped maps. It never touches map data except for copying maps whose
temporal extent was modified.

Most tests run the parser with ``dry_run=True``. The parser then evaluates
the expression completely and reports the maps it would register in
``process_chain_dict["register"]`` as (name, start, end) strings, but
creates no space time dataset. A few tests run for real and inspect the
result dataset.

Test data (value of every raster map in brackets, region 3x3 cells):

====  ====================================================================
STRDS contents
====  ====================================================================
A     a1..a4 (1..4), one month each: 2001-01-01 .. 2001-05-01
B     b2 (20) Feb, b3 (30) Mar, b5 (50) May, one month each, gap in April
C     c1 (100) 2001-01-01 .. 2001-03-01, c2 (200) 2001-03-01 .. 2001-05-01
D     far (5) 2001-02-01 .. 2001-03-01, spatially far away from all others
E     e1 (9) 2001-01-15 .. 2001-02-15
H     h1 (11), h2 (12), h3 (13): one month each with times of day
      06:10:20, 15:20:30 and 23:40:50, starting 2001-01-01, 02-01, 03-01
I     i1 (7) 2001-01-15, i2 (8) 2001-03-10 (time instances)
(none) event (6) 2001-01-06 .. 2001-02-15, time stamped with r.timestamp,
      registered in no dataset
EMPTY no maps
REL   r1 (1), r2 (2), r3 (3): relative time 0-1, 1-2, 2-3 days
====  ====================================================================
"""

from types import SimpleNamespace

import pytest

from grass.temporal.algebra import parser as algebra_parser
from grass.temporal.algebra.backends import ModuleCall
from grass.temporal.temporal_algebra import (
    FatalError,
    TemporalAlgebraLexer,
    TemporalAlgebraParser,
)
from grass.tools import Tools

DAY0 = "00:00:00"


def stamp(date, time=DAY0):
    return f"{date} {time}"


# Expected (start, end) of every registered map, written out by hand
EXTENT = {
    "a1": (stamp("2001-01-01"), stamp("2001-02-01")),
    "a2": (stamp("2001-02-01"), stamp("2001-03-01")),
    "a3": (stamp("2001-03-01"), stamp("2001-04-01")),
    "a4": (stamp("2001-04-01"), stamp("2001-05-01")),
    "b2": (stamp("2001-02-01"), stamp("2001-03-01")),
    "b3": (stamp("2001-03-01"), stamp("2001-04-01")),
    "b5": (stamp("2001-05-01"), stamp("2001-06-01")),
    "c1": (stamp("2001-01-01"), stamp("2001-03-01")),
    "c2": (stamp("2001-03-01"), stamp("2001-05-01")),
    "far": (stamp("2001-02-01"), stamp("2001-03-01")),
    "e1": (stamp("2001-01-15"), stamp("2001-02-15")),
    "h1": (stamp("2001-01-01", "06:10:20"), stamp("2001-02-01", "06:10:20")),
    "h2": (stamp("2001-02-01", "15:20:30"), stamp("2001-03-01", "15:20:30")),
    "h3": (stamp("2001-03-01", "23:40:50"), stamp("2001-04-01", "23:40:50")),
    "i1": (stamp("2001-01-15"), "None"),
    "i2": (stamp("2001-03-10"), "None"),
    "event": (stamp("2001-01-06"), stamp("2001-02-15")),
    "r1": ("0", "1"),
    "r2": ("1", "2"),
    "r3": ("2", "3"),
}


def maps(*names):
    """Expected register entries for the original maps with these names"""
    return [(name, *EXTENT[name]) for name in names]


@pytest.fixture(scope="module")
def session(temporal_exit_session):
    """Session with the datasets described in the module docstring"""
    session = temporal_exit_session
    tools = Tools(session=session)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    values = {
        "a1": 1,
        "a2": 2,
        "a3": 3,
        "a4": 4,
        "b2": 20,
        "b3": 30,
        "b5": 50,
        "c1": 100,
        "c2": 200,
        "e1": 9,
        "h1": 11,
        "h2": 12,
        "h3": 13,
        "i1": 7,
        "i2": 8,
        "r1": 1,
        "r2": 2,
        "r3": 3,
    }
    for name, value in values.items():
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.g_region(n=103, s=100, e=103, w=100, res=1)
    tools.r_mapcalc(expression="far = 5")
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    # a time stamped map which is in no space time dataset
    tools.r_mapcalc(expression="event = 6")
    tools.r_timestamp(map="event", date="6 Jan 2001 / 15 Feb 2001")

    for name in ("A", "B", "C", "D", "E", "H", "I", "EMPTY"):
        tools.t_create(output=name, type="strds", title=name, description=name)
    tools.t_create(
        output="REL",
        type="strds",
        temporaltype="relative",
        title="REL",
        description="REL",
    )
    membership = {
        "A": ("a1", "a2", "a3", "a4"),
        "B": ("b2", "b3", "b5"),
        "C": ("c1", "c2"),
        "D": ("far",),
        "E": ("e1",),
        "H": ("h1", "h2", "h3"),
        "I": ("i1", "i2"),
    }
    for stds, names in membership.items():
        for name in names:
            start, end = EXTENT[name]
            kwargs = {"start": start}
            if end != "None":
                kwargs["end"] = end
            tools.t_register(input=stds, maps=name, **kwargs)
    for name in ("r1", "r2", "r3"):
        start, end = EXTENT[name]
        tools.t_register(input="REL", maps=name, start=start, end=end, unit="days")
    return SimpleNamespace(session=session, tools=tools)


def dry_register(expression, **kwargs):
    """Evaluate expression without creating anything, return register entries"""
    parser = TemporalAlgebraParser(run=True, dry_run=True, **kwargs)
    chain = parser.parse(expression, "strds", overwrite=True)
    return chain["register"]


def names_of(entries):
    return [name for name, _, _ in entries]


def info(session, name):
    """Shell-style t.info output of a dataset as a dict"""
    result = session.tools.t_info(input=name, flags="g")
    return {key: str(value).strip("'") for key, value in result.keyval.items()}


def listed(session, name):
    """(name, start, end, min, max) of every map of a result dataset"""
    result = session.tools.t_rast_list(
        input=name, columns="name,start_time,end_time,min,max", format="json"
    )
    return [
        (row["name"], row["start_time"], row["end_time"], row["min"], row["max"])
        for row in result["data"]
    ]


# --- selection and temporal relations ------------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("R = A : B", ["a2", "a3"]),
        ("R = A : A", ["a1", "a2", "a3", "a4"]),
        ("R = A : EMPTY", []),
        ("R = A !: B", ["a1", "a4"]),
        ("R = A !: A", []),
        ("R = A !: EMPTY", ["a1", "a2", "a3", "a4"]),
        ("R = B : A", ["b2", "b3"]),
        ("R = A : B : C", []),
        ("R = A : A : A", ["a1", "a2", "a3", "a4"]),
        ("R = (A : B)", ["a2", "a3"]),
        ("R = (A : B) !: A", []),
        ("R = A {:,equal} B", ["a2", "a3"]),
        ("R = A {!:,equal} B", ["a1", "a4"]),
        ("R = A {:,equal,l} B", ["a2", "a3"]),
        ("R = A {:,during} C", ["a1", "a2", "a3", "a4"]),
        ("R = C {:,during} A", []),
        ("R = C {:,contains} A", ["c1", "c2"]),
        ("R = A {:,contains} C", []),
        ("R = A {!:,during} C", []),
        ("R = A {:,during|equal} C", ["a1", "a2", "a3", "a4"]),
        ("R = A {:,equal|during} B", ["a2", "a3"]),
        ("R = A {:,starts} C", ["a1", "a3"]),
        ("R = A {:,finishes} C", ["a2", "a4"]),
        ("R = C {:,started} A", ["c1", "c2"]),
        ("R = C {:,finished} A", ["c1", "c2"]),
        ("R = A {:,overlaps} E", ["a1"]),
        ("R = A {:,overlapped} E", ["a2"]),
        ("R = E {:,overlaps} A", ["e1"]),
        ("R = E {:,overlapped} A", ["e1"]),
        ("R = A {:,follows} B", ["a3", "a4"]),
        ("R = A {:,precedes} B", ["a1", "a2", "a4"]),
        ("R = A {:,equal|precedes} B", ["a1", "a2", "a3", "a4"]),
        ("R = A {!:,precedes} B", ["a3"]),
        ("R = I {:,during} A", ["i1", "i2"]),
        ("R = A {:,contains} I", ["a1", "a3"]),
        ("R = I : A", []),
        ("R = I !: A", ["i1", "i2"]),
        ("R = A : strds(B)", ["a2", "a3"]),
        ("R = strds(A) : B", ["a2", "a3"]),
        ("R = strds(A)", ["a1", "a2", "a3", "a4"]),
        ("R = A@PERMANENT : B@PERMANENT", ["a2", "a3"]),
        ("R = tmap(a1)", ["a1"]),
        ("R = tmap(a1) {:,equal} A", ["a1"]),
        ("R = A {:,equal} tmap(a1)", ["a1"]),
        ("R = REL : REL", ["r1", "r2", "r3"]),
        ("R = REL !: REL", []),
    ],
)
def test_selection(session, expression, expected):
    """Selection returns the maps of the left side with the given relation"""
    assert dry_register(expression) == maps(*expected)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("R = merge(A, B)", ["a1", "a2", "a3", "a4", "b2", "b3", "b5"]),
        ("R = merge(B, A)", ["a1", "a2", "a3", "a4", "b2", "b3", "b5"]),
        ("R = merge(EMPTY, A)", ["a1", "a2", "a3", "a4"]),
        ("R = merge(A, EMPTY)", ["a1", "a2", "a3", "a4"]),
        ("R = merge(EMPTY, EMPTY)", []),
        ("R = merge(A : B, A !: B)", ["a1", "a2", "a3", "a4"]),
        ("R = merge(A, A : B)", ["a1", "a2", "a3", "a4"]),
        ("R = merge(A : B, C)", ["a2", "a3", "c1", "c2"]),
        ("R = merge(A, B) : A", ["a1", "a2", "a3", "a4", "b2", "b3"]),
    ],
)
def test_merge(session, expression, expected):
    """merge() joins the map lists of both arguments (the order is not
    significant, the registration into a dataset sorts by time)"""
    entries = dry_register(expression)
    assert sorted(entries) == sorted(maps(*expected))


# --- temporal extent operators --------------------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # a1 [Jan 1, Feb 1] overlaps e1 [Jan 15, Feb 15]
        ("R = A {:,overlaps,l} E", [("a1", *EXTENT["a1"])]),
        (
            "R = A {:,overlaps,u} E",
            [("R_1", stamp("2001-01-01"), stamp("2001-02-15"))],
        ),
        (
            "R = A {:,overlaps,i} E",
            [("R_1", stamp("2001-01-15"), stamp("2001-02-01"))],
        ),
        ("R = A {:,overlaps,r} E", [("R_1", *EXTENT["e1"])]),
        (
            "R = A {:,overlaps,union} E",
            [("R_1", stamp("2001-01-01"), stamp("2001-02-15"))],
        ),
        (
            "R = A {:,overlaps,right} E",
            [("R_1", *EXTENT["e1"])],
        ),
        (
            "R = A {:,overlaps,intersect} E",
            [("R_1", stamp("2001-01-15"), stamp("2001-02-01"))],
        ),
    ],
)
def test_temporal_extent_operator_names_copies(session, expression, expected):
    """Extent operators change the extent of the selected maps.

    The result map is a copy, named by the basename and a counter. t.select
    passes no basename, hence "R_1": see test_extent_operator_copies_have_
    no_none_name for the reason this is wrong.
    """
    assert dry_register(expression) == expected


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("l", ["a1", "a2", "a3", "a4"]),
        ("i", ["a1", "a2", "a3", "a4"]),
    ],
)
def test_extent_operators_keeping_the_extent(session, operator, expected):
    """With left reference or intersection of nested maps nothing is copied"""
    assert dry_register(f"R = A {{:,during,{operator}}} C") == maps(*expected)


@pytest.mark.parametrize("operator", ["r", "u"])
def test_extent_operators_taking_the_reference_extent(session, operator):
    """Right reference and union give maps inside C the extent of C"""
    jan_mar = (stamp("2001-01-01"), stamp("2001-03-01"))
    mar_may = (stamp("2001-03-01"), stamp("2001-05-01"))
    assert dry_register(f"R = A {{:,during,{operator}}} C") == [
        ("R_1", *jan_mar),
        ("R_2", *jan_mar),
        ("R_3", *mar_may),
        ("R_4", *mar_may),
    ]


def test_extent_operator_with_basename(session):
    """The basename of parse() names the copies, numbered from 1"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    chain = parser.parse(
        "R = A {:,overlaps,u} E", "strds", basename="res", overwrite=True
    )
    assert names_of(chain["register"]) == ["res_1"]
    assert len(chain["processes"]) == 1


def test_extent_operator_copies_have_no_none_name(session):
    """Result maps must not be named after the Python value None"""
    entries = dry_register("R = A {:,overlaps,u} E")
    assert not any(name.startswith("None") for name in names_of(entries))


# --- hash operator and td() in conditions --------------------------------


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("R = if(td(A) > 30, A)", ["a1", "a3"]),
        ("R = if(td(A) == 28, A)", ["a2"]),
        ("R = if(td(A) >= 30, A)", ["a1", "a3", "a4"]),
        ("R = if(td(A) < 30, A)", ["a2"]),
        ("R = if(td(A) <= 30, A)", ["a2", "a4"]),
        ("R = if(td(A) != 31, A)", ["a2", "a4"]),
        ("R = if(td(C) > 60, C)", ["c2"]),
        ("R = if(td(C) == 59, C)", ["c1"]),
        ("R = if(td(A : B) == 28, A : B)", ["a2"]),
        ("R = if(A # B == 1, A)", ["a2", "a3"]),
        ("R = if((A # B) == 1, A)", ["a2", "a3"]),
        ("R = if(start_month(A : B) > 2, A)", ["a3"]),
        ("R = if(A # B > 1, A)", []),
        ("R = if(C {#,contains} A == 2, C)", ["c1", "c2"]),
        ("R = if(C {#,contains} A > 2, C)", []),
        ("R = if(C {#,contains} A >= 2, C)", ["c1", "c2"]),
        ("R = if(A {#,during} C == 1, A)", ["a1", "a2", "a3", "a4"]),
        ("R = if(A {#,during|equal} C == 1, A)", ["a1", "a2", "a3", "a4"]),
        ("R = if(C # A == 2, C)", []),
        ("R = if(td(A) == 31 && A # B == 0, A)", []),
    ],
)
def test_td_and_hash_conditions(session, expression, expected):
    """td() is the size of the interval in days, # counts related maps"""
    assert dry_register(expression) == maps(*expected)


def test_td_on_relative_time(session):
    """td() of relative time intervals is end minus start, in time units"""
    assert dry_register("R = if(td(REL) == 1, REL)") == maps("r1", "r2", "r3")


# --- conditions on temporal functions --------------------------------------


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("start_doy(A) > 59", ["a3", "a4"]),
        ("start_doy(A) == 1", ["a1"]),
        ("end_doy(A) == 60", ["a2"]),
        ("start_dow(A) == 4", ["a2", "a3"]),
        ("start_dow(A) == 7", ["a4"]),
        ("end_dow(A) == 4", ["a1", "a2"]),
        ("start_year(A) == 2001", ["a1", "a2", "a3", "a4"]),
        ("end_year(A) == 2001", ["a1", "a2", "a3", "a4"]),
        ("start_year(A) < 2001", []),
        ("start_month(A) > 2", ["a3", "a4"]),
        ("end_month(A) == 5", ["a4"]),
        ("start_week(A) > 5", ["a3", "a4"]),
        ("end_week(A) <= 9", ["a1", "a2"]),
        ("start_day(A) == 1", ["a1", "a2", "a3", "a4"]),
        ("end_day(A) != 1", []),
        ("start_hour(A) == 0", ["a1", "a2", "a3", "a4"]),
        ("start_hour(H) > 10", ["h2", "h3"]),
        ("start_hour(H) == 6", ["h1"]),
        ("end_hour(H) >= 15", ["h2", "h3"]),
        ("start_minute(H) == 20", ["h2"]),
        ("end_minute(H) > 10", ["h2", "h3"]),
        ("start_second(H) >= 30", ["h2", "h3"]),
        ("end_second(H) < 30", ["h1"]),
        ("start_day(I) == 15", ["i1"]),
        ("start_month(I) > 1", ["i2"]),
        ("start_doy(I) > 10", ["i1", "i2"]),
        ("start_week(I) == 10", ["i2"]),
        ("start_year(I) == 2001", ["i1", "i2"]),
    ],
)
def test_number_functions(session, condition, expected):
    """Start and end functions return the field of the time stamp"""
    stds = condition.split("(")[1].split(")")[0]
    assert dry_register(f"R = if({condition}, {stds})") == maps(*expected)


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ('start_time(H) == "15:20:30"', ["h2"]),
        ('start_time(H) < "12:00:00"', ["h1"]),
        ('start_time(H) >= "15:20:30"', ["h2", "h3"]),
        ('start_time(H) != "15:20:30"', ["h1", "h3"]),
        ('start_time(H) > "09:59:59"', ["h2", "h3"]),
        ('end_time(H) > "20:00:00"', ["h3"]),
        ('end_time(H) <= "06:10:20"', ["h1"]),
        ('start_time(A) == "00:00:00"', ["a1", "a2", "a3", "a4"]),
        ('start_date(H) == "2001-02-01"', ["h2"]),
        ('start_date(H) != "2001-02-01"', ["h1", "h3"]),
        ('start_date(A) > "2001-02-01"', ["a3", "a4"]),
        ('start_date(A) >= "2001-02-01"', ["a2", "a3", "a4"]),
        ('start_date(A) < "2001-03-01"', ["a1", "a2"]),
        ('end_date(H) == "2001-03-01"', ["h2"]),
        ('end_date(A) <= "2001-02-01"', ["a1"]),
        ('start_date(I) > "2001-02-01"', ["i2"]),
        ('start_datetime(H) == "2001-02-01 15:20:30"', ["h2"]),
        ('start_datetime(H) > "2001-02-01 15:20:30"', ["h3"]),
        ('start_datetime(H) >= "2001-02-01 15:20:30"', ["h2", "h3"]),
        ('start_datetime(H) < "2001-02-01 09:00:00"', ["h1"]),
        ('start_datetime(H) < "2001-02-01 19:00:00"', ["h1", "h2"]),
        ('start_datetime(H) < "2001-02-01 23:00:00"', ["h1", "h2"]),
        ('start_datetime(H) > "2001-02-01 10:00:00"', ["h2", "h3"]),
        ('start_datetime(H) != "2001-02-01 15:20:30"', ["h1", "h3"]),
        ('end_datetime(H) == "2001-03-01 15:20:30"', ["h2"]),
        ('end_datetime(H) >= "2001-03-01 15:20:30"', ["h2", "h3"]),
        ('end_datetime(A) < "2001-03-01 00:00:01"', ["a1", "a2"]),
        ('start_datetime(A) == "2001-03-01 00:00:00"', ["a3"]),
        ('start_datetime(I) < "2001-02-01 20:00:00"', ["i1"]),
    ],
)
def test_time_literal_functions(session, condition, expected):
    """Time, date and datetime functions compare with the matching literal"""
    stds = condition.split("(")[1].split(")")[0]
    assert dry_register(f"R = if({condition}, {stds})") == maps(*expected)


@pytest.mark.parametrize(
    "condition",
    [
        "end_doy(I) > 0",
        "end_month(I) == 1",
        'end_date(I) == "2001-01-15"',
        'end_time(I) == "00:00:00"',
        'end_datetime(I) == "2001-01-15 00:00:00"',
        "start_month(REL) > 0",
        "end_second(REL) == 0",
        'start_date(REL) > "2001-01-01"',
        'start_datetime(REL) > "2001-01-01 10:00:00"',
        'start_time(REL) == "00:00:00"',
    ],
)
def test_unavailable_function_aborts(session, condition):
    """End functions of time instances and any function of relative time are
    a fatal error, not a silently empty result"""
    stds = condition.split("(")[1].split(")")[0]
    with pytest.raises(SystemExit):
        dry_register(f"R = if({condition}, {stds})")


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("start_month(A) > 2 && end_month(A) < 5", ["a3"]),
        ("start_month(A) > 2 || end_month(A) < 3", ["a1", "a3", "a4"]),
        ("start_month(A) > 2 && end_month(A) < 5 && td(A) > 30", ["a3"]),
        ("start_month(A) > 2 && td(A) == 31 || start_month(A) == 2", ["a2", "a3"]),
        ("td(A) == 31 && start_month(A) > 3", []),
        ("start_month(A) == 1 || start_month(A) == 4", ["a1", "a4"]),
        ("start_month(A) < 2 {||,equal} start_month(A) > 2", ["a1", "a3", "a4"]),
        ("start_month(A) > 2 {&&,equal} end_month(A) < 5", ["a3"]),
        ("start_month(A) > 2 {&&,equal,l} td(A) > 30", ["a3"]),
        (
            'start_date(A) > "2001-01-01" && start_time(A) == "00:00:00"',
            ["a2", "a3", "a4"],
        ),
    ],
)
def test_combined_conditions(session, condition, expected):
    """Conditions combine with && and || (equal precedence, left to right)"""
    assert dry_register(f"R = if({condition}, A)") == maps(*expected)


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("T || F && F", False),
        ("F || T && T", True),
        ("T && F || T", True),
        ("F && T || F", False),
    ],
)
def test_logical_operators_have_equal_precedence(session, condition, expected):
    """&& and || bind equally and associate to the left (documented in the
    manual), so ``T || F && F`` is ``(T || F) && F``"""
    values = {"T": "start_month(A) == 1", "F": "start_month(A) == 2"}
    expression = " ".join(values.get(token, token) for token in condition.split())
    got = dry_register(f"R = if({expression}, tmap(a1))")
    assert (got == maps("a1")) is expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("if(start_month(A) > 2, A)", ["a3", "a4"]),
        ("if(start_month(A) > 2, A, A)", ["a1", "a2", "a3", "a4"]),
        ("if(start_month(A) > 2, A : B, A)", ["a1", "a2", "a3"]),
        ("if(start_month(A) > 2, if(start_month(A) < 4, A))", ["a3"]),
        ("if(start_month(A) > 2, A : B)", ["a3"]),
        ("if(start_month(A) > 2, A !: B)", ["a4"]),
        ("if(start_month(A) > 2, strds(A))", ["a3", "a4"]),
        ("if({equal}, start_month(B) == 3, A)", ["a3"]),
        ("if({equal}, start_month(B) == 3, A, A)", ["a2", "a3"]),
        ("if({contains}, start_month(C) == 1, A)", ["a1", "a2"]),
        ("if({contains}, start_month(C) == 1, A, A)", ["a1", "a2", "a3", "a4"]),
        ("if({contains}, start_month(C) == 3, A)", ["a3", "a4"]),
        ("if({during}, start_month(A) < 3, C)", ["c1"]),
        ("if({follows}, td(A) > 30, B)", ["b2"]),
        ("if({follows}, start_month(A) == 2, B)", []),
    ],
)
def test_if_then_else(session, expression, expected):
    """Conditions select maps of the then branch, else gets the others.

    The relation in braces connects condition and branches, equal by default.
    It reads from the condition to the branch: C contains A, A is during C.
    With {follows} the condition maps follow the branch maps (B precedes A),
    so these cases name the relation of the condition to the branch.
    """
    assert dry_register(f"R = {expression}") == maps(*expected)


# --- buffering, shifting and snapping --------------------------------------


def test_buff_t_absolute(session):
    """buff_t adds the increment before the start and after the end"""
    entries = dry_register('R = buff_t(A, "1 days")')
    assert [(start, end) for _, start, end in entries] == [
        (stamp("2000-12-31"), stamp("2001-02-02")),
        (stamp("2001-01-31"), stamp("2001-03-02")),
        (stamp("2001-02-28"), stamp("2001-04-02")),
        (stamp("2001-03-31"), stamp("2001-05-02")),
    ]


@pytest.mark.parametrize(
    ("increment", "first"),
    [
        ('"1 months"', (stamp("2000-12-01"), stamp("2001-03-01"))),
        ('"1 years"', (stamp("2000-01-01"), stamp("2002-02-01"))),
        (
            '"6 hours"',
            (stamp("2000-12-31", "18:00:00"), stamp("2001-02-01", "06:00:00")),
        ),
    ],
)
def test_buff_t_units(session, increment, first):
    """buff_t understands months, years and hours"""
    entries = dry_register(f"R = buff_t(A, {increment})")
    assert entries[0][1:] == first


def test_buff_t_of_expression(session):
    """buff_t works on the result of an expression"""
    entries = dry_register('R = buff_t(A : B, "1 days")')
    assert [(start, end) for _, start, end in entries] == [
        (stamp("2001-01-31"), stamp("2001-03-02")),
        (stamp("2001-02-28"), stamp("2001-04-02")),
    ]


def test_buff_t_relative(session):
    """buff_t with a number buffers relative time (documented as buff_t(A, 5))"""
    entries = dry_register("R = buff_t(REL, 1)")
    assert [(start, end) for _, start, end in entries] == [
        ("-1", "2"),
        ("0", "3"),
        ("1", "4"),
    ]


def test_tshift_absolute(session):
    """tshift moves start and end by the increment"""
    entries = dry_register('R = tshift(A, "1 months")')
    assert [(start, end) for _, start, end in entries] == [
        (stamp("2001-02-01"), stamp("2001-03-01")),
        (stamp("2001-03-01"), stamp("2001-04-01")),
        (stamp("2001-04-01"), stamp("2001-05-01")),
        (stamp("2001-05-01"), stamp("2001-06-01")),
    ]


def test_tshift_relative(session):
    """tshift with a number moves relative time"""
    entries = dry_register("R = tshift(REL, 1)")
    assert [(start, end) for _, start, end in entries] == [
        ("1", "2"),
        ("2", "3"),
        ("3", "4"),
    ]


def test_tshift_of_expression(session):
    """tshift works on the result of a selection"""
    entries = dry_register('R = tshift(A : B, "1 days")')
    assert [(start, end) for _, start, end in entries] == [
        (stamp("2001-02-02"), stamp("2001-03-02")),
        (stamp("2001-03-02"), stamp("2001-04-02")),
    ]


def test_tsnap_closes_gaps(session):
    """tsnap extends a map to the start of the next one: b3 ends 2001-05-01"""
    entries = dry_register("R = tsnap(B)")
    assert [(start, end) for _, start, end in entries] == [
        EXTENT["b2"],
        (stamp("2001-03-01"), stamp("2001-05-01")),
        EXTENT["b5"],
    ]


def test_tsnap_of_expression(session):
    """tsnap works on the result of a selection, here B : B"""
    entries = dry_register("R = tsnap(B : B)")
    assert [(start, end) for _, start, end in entries][1] == (
        stamp("2001-03-01"),
        stamp("2001-05-01"),
    )


def test_tsnap_keeps_gapless_series(session):
    """A series without gaps is not changed"""
    assert dry_register("R = tsnap(A)") == maps("a1", "a2", "a3", "a4")


def test_tsnap_of_time_instances(session):
    """Instances are snapped to the next one: i1 becomes [2001-01-15, 2001-03-10]"""
    entries = dry_register("R = tsnap(I)")
    assert entries[0][1:] == (stamp("2001-01-15"), stamp("2001-03-10"))


# --- start_doy(A, -1) and friends ------------------------------------------


@pytest.mark.parametrize(
    ("function", "offset", "expected"),
    [
        # neighbour of a2 is a1 (doy 1) etc.; maps without neighbour are dropped
        ("start_doy", -1, [("a2", "1"), ("a3", "32"), ("a4", "60")]),
        ("start_doy", 1, [("a1", "32"), ("a2", "60"), ("a3", "91")]),
        ("start_doy", 0, [("a1", "1"), ("a2", "32"), ("a3", "60"), ("a4", "91")]),
        ("start_doy", 2, [("a1", "60"), ("a2", "91")]),
        ("start_doy", 4, []),
        ("start_doy", -4, []),
        ("end_day", 1, [("a1", "1"), ("a2", "1"), ("a3", "1")]),
        ("start_month", 1, [("a1", "2"), ("a2", "3"), ("a3", "4")]),
        ("end_month", -1, [("a2", "2"), ("a3", "3"), ("a4", "4")]),
    ],
)
def test_time_constant_of_neighbour(session, function, offset, expected):
    """function(A, n) gives each map the value of its n-th neighbour in time.

    The result keeps the temporal extent of the map and carries the value
    as the command string for the map calculator.
    """
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    parser.count = 0
    parser.stdstype = "strds"
    rule = [None, function, "(", "A", ",", offset, ")"]
    parser.p_expr_time_const(rule)
    got = [(m.get_temporal_extent_as_tuple()[0], m.cmd_list) for m in rule[0]]
    start = {name: EXTENT[name][0] for name in ("a1", "a2", "a3", "a4")}
    assert [(str(s), value) for s, value in got] == [
        (start[name], value) for name, value in expected
    ]


# --- granularity ----------------------------------------------------------


def test_common_granularity_of_two_datasets(session):
    """The common granularity of A (1 month) and C (2 months) is 1 month"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    assert parser.setup_common_granularity("R = A : C") is True
    assert parser.granularity == "1 month"
    assert parser.use_granularity is True


def test_common_granularity_of_one_dataset(session):
    """The granularity of a single dataset is its own"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    assert parser.setup_common_granularity("R = C : C") is True
    assert parser.granularity == "2 months"


def test_selection_in_granularity_mode(session):
    """With a common granularity every map is split into granules"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    assert parser.setup_common_granularity("R = A : C")
    chain = parser.parse("R = C : A", "strds", overwrite=True)
    starts = [start for _, start, _ in chain["register"]]
    assert starts == [
        stamp("2001-01-01"),
        stamp("2001-02-01"),
        stamp("2001-03-01"),
        stamp("2001-04-01"),
    ]


def test_granularity_rejects_mixed_temporal_types(session):
    """Absolute and relative datasets cannot share a granularity"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    assert parser.setup_common_granularity("R = A : REL") is False


@pytest.mark.parametrize("expression", ["R = A {:,equal} C", "R = A {:} C"])
def test_granularity_rejects_relation_operators(session, expression):
    """Spatio-temporal operators are meaningless in granularity mode"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    assert parser.setup_common_granularity(expression) is False


# --- real runs ------------------------------------------------------------


def test_run_registers_result_dataset(session):
    """A real run creates the result dataset with the selected maps"""
    parser = TemporalAlgebraParser(run=True)
    chain = parser.parse("sel1 = A : B", "strds", overwrite=True)
    assert listed(session, "sel1") == [
        ("a2", *EXTENT["a2"], 2.0, 2.0),
        ("a3", *EXTENT["a3"], 3.0, 3.0),
    ]
    assert chain["STDS"] == {
        "name": "sel1",
        "stdstype": "strds",
        "temporal_type": "absolute",
    }
    assert chain["register"] == maps("a2", "a3")
    assert chain["processes"] == []
    assert chain["remove"] == []


def test_run_result_dataset_metadata(session):
    """The result dataset has the temporal type, extent and map count"""
    TemporalAlgebraParser(run=True).parse("sel2 = A !: B", "strds", overwrite=True)
    result = info(session, "sel2")
    assert result["temporal_type"] == "absolute"
    assert result["number_of_maps"] == "2"
    assert result["start_time"] == "2001-01-01 00:00:00"
    assert result["end_time"] == "2001-05-01 00:00:00"


def test_run_with_extent_change_copies_maps(session):
    """Maps whose extent changes are copied under the basename"""
    parser = TemporalAlgebraParser(run=True)
    chain = parser.parse(
        "sel3 = A {:,during,r} C", "strds", basename="cp", overwrite=True
    )
    jan_mar = (stamp("2001-01-01"), stamp("2001-03-01"))
    mar_may = (stamp("2001-03-01"), stamp("2001-05-01"))
    assert listed(session, "sel3") == [
        ("cp_1", *jan_mar, 1.0, 1.0),
        ("cp_2", *jan_mar, 2.0, 2.0),
        ("cp_3", *mar_may, 3.0, 3.0),
        ("cp_4", *mar_may, 4.0, 4.0),
    ]
    assert len(chain["processes"]) == 4
    # the originals still have their own extent
    assert listed(session, "A")[0][1:3] == EXTENT["a1"]


def test_run_empty_result(session):
    """An empty selection creates an empty dataset and warns"""
    chain = TemporalAlgebraParser(run=True).parse(
        "sel4 = A : EMPTY", "strds", overwrite=True
    )
    # a dataset without maps stores no map count at all
    assert info(session, "sel4")["number_of_maps"] in {"0", "None"}
    assert info(session, "sel4")["temporal_type"] == "absolute"
    assert chain["register"] == []


def test_run_overwrite_replaces_result(session):
    """With overwrite the result dataset is replaced"""
    TemporalAlgebraParser(run=True).parse("sel5 = A : B", "strds", overwrite=True)
    TemporalAlgebraParser(run=True).parse("sel5 = A !: B", "strds", overwrite=True)
    assert [row[0] for row in listed(session, "sel5")] == ["a1", "a4"]


def test_run_without_overwrite_refuses_existing_dataset(session):
    """Without overwrite an existing result dataset is not replaced"""
    TemporalAlgebraParser(run=True).parse("sel6 = A : B", "strds", overwrite=True)
    with pytest.raises(SystemExit):
        TemporalAlgebraParser(run=True).parse("sel6 = A !: B", "strds")
    assert [row[0] for row in listed(session, "sel6")] == ["a2", "a3"]


def test_run_time_instances(session):
    """Maps without end time are registered as instances"""
    TemporalAlgebraParser(run=True).parse(
        "sel7 = I {:,during} A", "strds", overwrite=True
    )
    assert listed(session, "sel7") == [
        ("i1", stamp("2001-01-15"), None, 7.0, 7.0),
        ("i2", stamp("2001-03-10"), None, 8.0, 8.0),
    ]


def test_run_relative_time(session):
    """Selecting from a relative dataset yields a relative result dataset"""
    TemporalAlgebraParser(run=True).parse("sel8 = REL : REL", "strds", overwrite=True)
    result = info(session, "sel8")
    assert result["temporal_type"] == "relative"
    assert result["number_of_maps"] == "3"


def test_dry_run_creates_nothing(session):
    """dry_run evaluates but registers no dataset and runs no module"""
    parser = TemporalAlgebraParser(run=True, dry_run=True)
    chain = parser.parse("drynot = A : B", "strds", overwrite=True)
    assert names_of(chain["register"]) == ["a2", "a3"]
    result = session.tools.t_list(type="strds", format="json")
    assert "drynot" not in str(result)


def test_tmap_reads_time_stamp_of_unregistered_map(session):
    """tmap() takes the time stamp from the GRASS database for a map which is
    not in the temporal database. As the temporal database does not know the
    time, the map is registered as a copy."""
    assert dry_register("R = tmap(event)") == [("R_1", *EXTENT["event"])]


def test_tmap_with_relation(session):
    """event [Jan 6, Feb 15] starts before a2 [Feb 1, Mar 1] and ends inside"""
    assert dry_register("R = tmap(event) {:,overlaps} A") == [("R_1", *EXTENT["event"])]
    assert dry_register("R = A {:,overlapped} tmap(event)") == maps("a2")


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        # a1 and a4 precede one map of B, a2 is equal to b2 and precedes b3
        ("A {#,equal|precedes} B == 2", ["a2"]),
        ("A {#,equal|precedes} B == 1", ["a1", "a3", "a4"]),
        ("A {#,precedes|equal} B == 2", ["a2"]),
        ("A {#,equal|follows} B == 2", ["a3"]),
        ("A {#,precedes|follows} B == 1", ["a1", "a2", "a3"]),
        ("A {#,precedes|follows} B == 2", ["a4"]),
    ],
)
def test_hash_counts_the_maps_of_all_relations(session, condition, expected):
    """The hash operator counts the maps related by any of the relations"""
    assert dry_register(f"R = if({condition}, A)") == maps(*expected)


@pytest.mark.parametrize("condition", ["td(I) > 1", "td(I) == 0", "end_doy(I) > 1"])
def test_time_instance_has_no_time_difference(session, condition):
    """td() needs an interval: for a time instance it is a fatal error naming
    the map, not an UnboundLocalError"""
    with pytest.raises(SystemExit):
        dry_register(f"R = if({condition}, I)")


def test_copy_name_defaults_to_the_result_name(session):
    """Copies of maps with a changed extent are named after the result
    dataset, since t.select has no basename"""
    assert names_of(dry_register("res = A {:,overlaps,u} E")) == ["res_1"]


# --- run=False ------------------------------------------------------------


@pytest.mark.parametrize(
    "expression",
    [
        "R = A : B",
        "R = A !: B",
        "R = A {:,during,r} C",
        "R = A {!:,equal} B",
        "R = strds(A)",
        "R = merge(A, B)",
        'R = buff_t(A, "1 days")',
        "R = buff_t(A, 3)",
        'R = tshift(A, "1 days")',
        "R = tsnap(A)",
        "R = if(start_month(A) > 2, A)",
        "R = if(start_month(A) > 2, A, B)",
        "R = if({equal}, start_month(A) > 2, A)",
        "R = if({equal}, start_month(A) > 2, A, B)",
        "R = if(td(A) > 1, A)",
        "R = if(A # B == 1, A)",
        "R = start_doy(A, -1)",
        "R = A : B : C",
        "R = tmap(a1)",
    ],
)
def test_run_false_parses_without_error(session, expression):
    """With run=False the expression is only parsed: nothing is evaluated,
    created or registered"""
    parser = TemporalAlgebraParser(run=False)
    chain = parser.parse(expression, "strds", overwrite=True)
    assert chain == {"processes": [], "register": [], "remove": [], "STDS": {}}


@pytest.mark.parametrize(
    "expression",
    [
        "R = tmap(a1) : A",
        'R = buff_t(merge(A, B), "1 days")',
        "R = tsnap(merge(A, B))",
    ],
)
def test_run_false_parses_nested_tmap_and_merge(session, expression):
    """run=False must accept every valid expression, also nested merge/tmap"""
    TemporalAlgebraParser(run=False).parse(expression, "strds")


def test_run_false_keeps_database_untouched(session):
    """run=False does not even open the operands"""
    chain = TemporalAlgebraParser(run=False).parse("R = nonexisting : A", "strds")
    assert chain["register"] == []


# --- errors ---------------------------------------------------------------


@pytest.mark.parametrize(
    "expression",
    [
        "R = A :",
        "R = ",
        "R = A B",
        "R = ( A : B",
        "R = A : B )",
        "R = if(start_month(A) > 2)",
        "R = A # B",
        "R = A {#} B",
        "R = C {#,contains} A",
        'R = if(start_month(A) > "x", A)',
        "R = if(start_month(A), A)",
        "R = if(A, A)",
        "R = A {bogus} B",
        "R = A {:,during,x} B",
        "R = A $ B",
        "R = A + B",
        "R = A - B",
        "R = 1",
        "R = A",
        "A : B",
        "= A : B",
        "R = tmap()",
        'R = buff_t(A, "x")',
        'R = buff_t(A "1 days")',
        "R = merge(A)",
        "R = A.b : B",
        "R == A : B",
        'R = if(start_datetime(A) > "2001-01-01", A)',
        'R = if(start_date(A) > "2001-01-01 10:00:00", A)',
        'R = if(start_time(A) > "10:00", A)',
        "R = if(start_time(A) > 10, A)",
        'R = if(start_month(A) > "2001-01-01", A)',
        "R = start_doy(A, 1.5)",
        "R = td(A)",
    ],
)
def test_syntax_errors(session, expression):
    """Invalid syntax raises SyntaxError, from the lexer or the parser"""
    with pytest.raises(SyntaxError):
        TemporalAlgebraParser(run=True, dry_run=True).parse(expression, "strds")


def test_syntax_error_message(session):
    """The message names the token and the whole expression"""
    with pytest.raises(SyntaxError, match=r"token NAME near 'B' expression 'R = A B'"):
        TemporalAlgebraParser(run=True, dry_run=True).parse("R = A B", "strds")


@pytest.mark.parametrize(
    "expression",
    [
        "R = nothere : A",
        "R = A : nothere",
        "R = A : nothere@PERMANENT",
        "R = A : other@PERMANENT",
        "R = merge(A, nothere)",
        "R = if(start_month(nothere) > 1, A)",
        "R = tmap(nothere)",
        "R = tmap(A)",
        "R = str3ds(A)",
        "R = stvds(A)",
        "R = tsnap(nothere)",
    ],
)
def test_unknown_dataset(session, expression):
    """An unknown dataset or map raises FatalError naming it"""
    with pytest.raises(FatalError, match="not found"):
        TemporalAlgebraParser(run=True, dry_run=True).parse(expression, "strds")


@pytest.mark.parametrize(
    "expression",
    [
        "R = A : REL",
        "R = REL : A",
        "R = merge(A, REL)",
        "R = A {:,during} REL",
        "R = if(td(A) > 1, REL)",
    ],
)
def test_mixed_temporal_types_abort(session, expression):
    """Absolute and relative datasets in one expression are a fatal error"""
    with pytest.raises(SystemExit):
        TemporalAlgebraParser(run=True, dry_run=True).parse(expression, "strds")


@pytest.mark.parametrize(
    "expression",
    ["R = A {:,bogus} B", "R = A {:,equal|bogus} B", "R = A {!:,nothing} B"],
)
def test_unknown_relation_is_an_error(session, expression):
    """An unknown temporal relation must be reported, not ignored"""
    with pytest.raises(SyntaxError):
        TemporalAlgebraParser(run=True, dry_run=True).parse(expression, "strds")


# --- documented equivalences ------------------------------------------------


@pytest.mark.parametrize("operator", ["{:,equal}", "{:,equal,l}"])
def test_select_operator_equals_plain_select(session, operator):
    """`A {:,equal} B` and `A {:,equal,l} B` select the same maps as `A : B`"""
    assert dry_register(f"R = A {operator} B") == maps("a2", "a3")


@pytest.mark.parametrize("operator", ["{:}", "{!:}"])
def test_default_select_operator_equals_plain_select(session, operator):
    """`A {:} B` selects like `A : B` and `A {!:} B` like `A !: B`"""
    plain = ":" if operator == "{:}" else "!:"
    assert dry_register(f"R = A {operator} B") == dry_register(f"R = A {plain} B")


def test_spatial_flag_filters_plain_select(session):
    """D's map is far from all maps of A, so `A : D` selects nothing with -s"""
    assert dry_register("R = A : D", spatial=True) == []


@pytest.mark.parametrize(
    "expression",
    [
        "R = if(A {#} D == 1, A)",
        "R = if({equal}, start_doy(D) > 0, A)",
        "R = if(td(D) > 1, A)",
    ],
)
def test_spatial_flag_applies_to_hash_and_conditions(session, expression):
    """The manual describes -s as evaluating the spatial topology of the
    expression, so it also restricts the maps counted or compared by hash and
    if conditions: D is far from A, so nothing is related and nothing selected"""
    assert dry_register(expression) == maps("a2")
    assert dry_register(expression, spatial=True) == []


def test_plain_select_ignores_space_without_flag(session):
    """Without -s only time counts: a2 is selected although D is far away"""
    assert dry_register("R = A : D") == maps("a2")


@pytest.mark.parametrize(
    "expression",
    ["R = A {:,foo} B : C", "R = (A {:,foo} B) : C", "R = A : (B {:,foo} C)"],
)
def test_first_reported_error_wins(session, expression):
    """A faulty operator is reported itself, not as a follow-up error of the
    rule which received nothing from it"""
    with pytest.raises(SyntaxError, match="foo"):
        dry_register(expression)


@pytest.mark.parametrize("run", [True, False])
def test_debug_output_shows_the_parsed_rules(session, capsys, run):
    """debug=True prints the rules while parsing, with and without run"""
    parser = TemporalAlgebraParser(run=run, dry_run=True, debug=True)
    parser.parse("R = A : B", "strds", overwrite=True)
    output = capsys.readouterr().out
    assert "A" in output
    assert "B" in output


def test_debug_output_does_not_change_the_result(session, capsys):
    """The registered maps are the same with and without debug"""
    quiet = dry_register("R = A : B")
    parser = TemporalAlgebraParser(run=True, dry_run=True, debug=True)
    loud = parser.parse("R = A : B", "strds", overwrite=True)["register"]
    capsys.readouterr()
    assert loud == quiet


@pytest.mark.parametrize("function", ["buff_t", "tshift"])
def test_increment_without_unit_is_refused_for_absolute_time(session, function):
    """A bare number is no increment for absolute time: a clear SyntaxError
    instead of an exception of the datetime code"""
    with pytest.raises(SyntaxError, match=f"{function}.*unit"):
        dry_register(f"R = {function}(A, 1)")


@pytest.mark.parametrize(
    "expression", ["R = strds(A) : B", "R = A : str3ds(B)", "R = stvds(A)"]
)
def test_dataset_type_functions_are_refused_by_the_reject_helper(session, expression):
    """The shared check refuses the functions which select the dataset type"""
    parser = TemporalAlgebraParser(run=False)
    with pytest.raises(SyntaxError, match="Syntax error near"):
        parser._reject_dataset_type_tokens(TemporalAlgebraLexer(), expression)


def test_module_dict_shows_the_input_maps_of_an_r_series_call():
    call = ModuleCall("r.series", {"output": "x", "method": "sum"}, inputs=("a", "b"))
    described = algebra_parser._module(call, False)
    assert ("input", "a,b") in described["inputs"]
    assert ("method", "sum") in described["inputs"]
    assert described["outputs"] == [("output", "x")]
