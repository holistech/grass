"""Tests of the selection of t.select on registered space time datasets.

The core with ``selection=True`` is what t.select runs: selection, temporal relations,
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
from grass.exceptions import FatalError
from grass.tools import Tools

DAY0 = "00:00:00"


class SelectionRunner:
    """The selection of t.select: the core with the maps registered unchanged

    t.select calls evaluate() with ``selection=True``; this class gives the
    tests the same call in the form of a parser object.
    """

    def __init__(self, run=False, dry_run=False, debug=False, spatial=False):
        self.options = {
            "run": run,
            "dry_run": dry_run,
            "debug": debug,
            "spatial": spatial,
        }

    def parse(self, expression, stdstype="strds", overwrite=False):
        return algebra_parser.evaluate(
            expression,
            kind="raster",
            selection=True,
            overwrite=overwrite,
            **self.options,
        )


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
    parser = SelectionRunner(run=True, dry_run=True, **kwargs)
    chain = parser.parse(expression, "strds", overwrite=True)
    # The core names a map by its full id; the tests list the bare names.
    return [
        (name.partition("@")[0], start, end) for name, start, end in chain["register"]
    ]


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
    """Conditions combine with && and ||. The cases give the same result
    whichever of the two binds stronger."""
    assert dry_register(f"R = if({condition}, A)") == maps(*expected)


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


# --- granularity ----------------------------------------------------------


# --- real runs ------------------------------------------------------------


def test_run_result_dataset_metadata(session):
    """The result dataset has the temporal type, extent and map count"""
    SelectionRunner(run=True).parse("sel2 = A !: B", "strds", overwrite=True)
    result = info(session, "sel2")
    assert result["temporal_type"] == "absolute"
    assert result["number_of_maps"] == "2"
    assert result["start_time"] == "2001-01-01 00:00:00"
    assert result["end_time"] == "2001-05-01 00:00:00"


def test_run_empty_result(session):
    """An empty selection creates an empty dataset and warns"""
    chain = SelectionRunner(run=True).parse("sel4 = A : EMPTY", "strds", overwrite=True)
    # a dataset without maps stores no map count at all
    assert info(session, "sel4")["number_of_maps"] in {"0", "None"}
    assert info(session, "sel4")["temporal_type"] == "absolute"
    assert chain["register"] == []


def test_run_overwrite_replaces_result(session):
    """With overwrite the result dataset is replaced"""
    SelectionRunner(run=True).parse("sel5 = A : B", "strds", overwrite=True)
    SelectionRunner(run=True).parse("sel5 = A !: B", "strds", overwrite=True)
    assert [row[0] for row in listed(session, "sel5")] == ["a1", "a4"]


def test_run_time_instances(session):
    """Maps without end time are registered as instances"""
    SelectionRunner(run=True).parse("sel7 = I {:,during} A", "strds", overwrite=True)
    assert listed(session, "sel7") == [
        ("i1", stamp("2001-01-15"), None, 7.0, 7.0),
        ("i2", stamp("2001-03-10"), None, 8.0, 8.0),
    ]


def test_run_relative_time(session):
    """Selecting from a relative dataset yields a relative result dataset"""
    SelectionRunner(run=True).parse("sel8 = REL : REL", "strds", overwrite=True)
    result = info(session, "sel8")
    assert result["temporal_type"] == "relative"
    assert result["number_of_maps"] == "3"


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
    parser = SelectionRunner(run=False)
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
    SelectionRunner(run=False).parse(expression, "strds")


def test_run_false_keeps_database_untouched(session):
    """run=False does not even open the operands"""
    chain = SelectionRunner(run=False).parse("R = nonexisting : A", "strds")
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
        "R = A {bogus} B",
        "R = A {:,during,x} B",
        "R = A $ B",
        "A : B",
        "= A : B",
        "R = tmap()",
        'R = buff_t(A "1 days")',
        "R = merge(A)",
        "R = A.b : B",
        "R == A : B",
        "R = start_doy(A, 1.5)",
    ],
)
def test_syntax_errors(session, expression):
    """Invalid syntax raises SyntaxError"""
    with pytest.raises(SyntaxError):
        SelectionRunner(run=True, dry_run=True).parse(expression, "strds")


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
        SelectionRunner(run=True, dry_run=True).parse(expression, "strds")


@pytest.mark.parametrize(
    "expression",
    ["R = A {:,bogus} B", "R = A {:,equal|bogus} B", "R = A {!:,nothing} B"],
)
def test_unknown_relation_is_an_error(session, expression):
    """An unknown temporal relation must be reported, not ignored"""
    with pytest.raises(SyntaxError):
        SelectionRunner(run=True, dry_run=True).parse(expression, "strds")


# --- documented equivalences ------------------------------------------------


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


def test_module_dict_shows_the_input_maps_of_an_r_series_call():
    call = ModuleCall("r.series", {"output": "x", "method": "sum"}, inputs=("a", "b"))
    described = algebra_parser._as_process_dict(call, False)
    assert ("input", "a,b") in described["inputs"]
    assert ("method", "sum") in described["inputs"]
    assert described["outputs"] == [("output", "x")]
