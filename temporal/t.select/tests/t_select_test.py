"""Tests of t.select

The datasets and the temporal relations between their maps are described in
conftest.py. Times are given as day offsets from 2001-01-01. The tool is run
with the same expression syntax as in t.select.md.
"""

import itertools
from datetime import datetime

import pytest

from grass.tools import ToolError, Tools

KINDS = {
    "strds": "t_rast_list",
    "stvds": "t_vect_list",
    "str3ds": "t_rast3d_list",
}

DAY0 = datetime(2001, 1, 1)

# The A maps are 10 days long and follow each other.
A_EXTENTS = {"a1": (0, 10), "a2": (10, 20), "a3": (20, 30), "a4": (30, 40)}

result_counter = itertools.count(1)


def day_offset(text):
    """Day offset from 2001-01-01 of a time stamp string"""
    return (datetime.strptime(text, "%Y-%m-%d %H:%M:%S") - DAY0).days


def run_select(session, expression, kind="strds", flags=""):
    """Run t.select into a new result dataset and return its map rows

    Each row is a tuple (name, start day, end day), sorted by start, end and name.
    """
    result = f"result{next(result_counter)}"
    tools = Tools(session=session, overwrite=True)
    tools.t_select(expression=f"{result} = {expression}", type=kind, flags=flags)
    listing = getattr(tools, KINDS[kind])(
        input=result, columns="name,start_time,end_time", format="json"
    )
    return sorted(
        (row["name"], day_offset(row["start_time"]), day_offset(row["end_time"]))
        for row in listing["data"]
    )


def select_fails(session, expression, kind="strds", match=None):
    """Assert that the t.select call itself ends with an error.

    The result dataset is not listed, so a missing result does not count as
    the error.
    """
    tools = Tools(session=session, overwrite=True)
    with pytest.raises(ToolError, match=match):
        tools.t_select(expression=f"failing = {expression}", type=kind)


def selected_names(session, expression, kind="strds", flags=""):
    """Names of the maps in the result of t.select"""
    return [row[0] for row in run_select(session, expression, kind, flags)]


# Temporal relations


RELATIONS = {
    "equal": ["a2"],
    "precedes": ["a1", "a4"],
    "follows": ["a1", "a3"],
    "starts": ["a1"],
    "started": ["a1"],
    "finishes": ["a2"],
    "finished": ["a4"],
    "during": ["a1", "a2"],
    "contains": ["a1", "a3", "a4"],
    "overlaps": ["a3"],
    "overlapped": ["a4"],
    "over": ["a3", "a4"],
}


@pytest.mark.parametrize(("relation", "expected"), RELATIONS.items())
def test_select_by_relation(series, relation, expected):
    """Each relation selects the A maps that have it to at least one B map.

    "during" includes the starts and finishes cases and "contains" the
    started and finished cases (topology builder definition).
    """
    assert selected_names(series.session, "A {:, %s} B" % relation) == expected


@pytest.mark.parametrize("kind", ["stvds", "str3ds"])
@pytest.mark.parametrize(
    ("relation", "expected"),
    [(r, RELATIONS[r]) for r in ["equal", "precedes", "contains", "over"]],
)
def test_select_by_relation_other_dataset_types(series, kind, relation, expected):
    """Vector and 3D raster time series select the same maps as raster series."""
    assert (
        selected_names(series.session, "A {:, %s} B" % relation, kind=kind) == expected
    )


@pytest.mark.parametrize(
    "relations",
    [
        "equal|precedes",
        "equal | precedes",
        "equal|over",
        "overlaps|overlapped|equal",
    ],
)
def test_select_by_relation_list(series, relations):
    """A list of relations selects the union of the maps of each relation."""
    expected = sorted(
        set(
            itertools.chain.from_iterable(
                RELATIONS[name.strip()] for name in relations.split("|")
            )
        )
    )
    assert selected_names(series.session, "A {:, %s} B" % relations) == expected


def test_select_by_all_relations(series):
    """All eleven relations together select every map that has any relation."""
    relations = "equal|during|precedes|follows|overlaps|overlapped|contains"
    relations += "|starts|started|finishes|finished"
    assert selected_names(series.session, "A {:, %s} B" % relations) == [
        "a1",
        "a2",
        "a3",
        "a4",
    ]


def test_select_by_relation_list_starting_with_over(series):
    """'over|equal' selects the same maps as 'equal|over'."""
    assert selected_names(series.session, "A {:, over|equal} B") == ["a2", "a3", "a4"]


def test_select_without_matching_relation_is_empty(series):
    """A relation that no map has leaves the result empty."""
    assert run_select(series.session, "A {:, equal} D") == []


# Default operators


@pytest.mark.parametrize(
    "operator",
    [
        ":",
        "{:}",
        "{:,equal}",
        "{:,equal,l}",
    ],
)
def test_select_default_forms_are_equal(series, operator):
    """The shorthand forms select like {:,equal,l} (t.select manual)."""
    assert run_select(series.session, "A %s B" % operator) == [("a2", 10, 20)]


@pytest.mark.parametrize(
    "operator",
    ["!:", "{!:}", "{!:,equal}", "{!:,equal,l}"],
)
def test_not_select_default_forms_are_complement_of_equal(series, operator):
    """The shorthand forms of the inverse selection are the complement of equal."""
    assert selected_names(series.session, "A %s B" % operator) == ["a1", "a3", "a4"]


@pytest.mark.parametrize("kind", ["stvds", "str3ds"])
def test_select_and_not_select_other_dataset_types(series, kind):
    """Selection and inverse selection split a vector or 3D raster series."""
    assert selected_names(series.session, "A : B", kind=kind) == ["a2"]
    assert selected_names(series.session, "A !: B", kind=kind) == ["a1", "a3", "a4"]


@pytest.mark.parametrize(
    ("relations", "expected"),
    [
        ("precedes|follows", ["a2"]),
        ("during", ["a3", "a4"]),
        ("contains", ["a2"]),
        ("overlaps", ["a1", "a2", "a4"]),
        ("equal|contains", []),
        ("over", ["a1", "a2"]),
    ],
)
def test_not_select_by_relation(series, relations, expected):
    """!: selects the A maps that have none of the given relations."""
    assert selected_names(series.session, "A {!:, %s} B" % relations) == expected


def test_select_and_not_select_are_complements(series):
    """Every A map is in exactly one of the results of : and !: for a relation."""
    selected = selected_names(series.session, "A {:, contains} B")
    inverse = selected_names(series.session, "A {!:, contains} B")
    assert sorted(selected + inverse) == ["a1", "a2", "a3", "a4"]


def test_chained_select_applies_left_to_right(series):
    """A : B : D keeps the A maps equal to B maps and then equal to D maps."""
    assert run_select(series.session, "A : B : D") == []
    assert selected_names(series.session, "A {:,equal} B {:,equal} B") == ["a2"]


# Temporal extent of the result


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("l", [(10, 20), (20, 30), (30, 40)]),
        ("i", [(10, 20), (20, 30), (30, 40)]),
        ("r", [(5, 45)] * 3),
        ("u", [(5, 45)] * 3),
        ("d", [(5, 45)] * 3),
    ],
)
def test_temporal_operator_during(series, operator, expected):
    """a2..a4 are during D (5..45): left and intersection keep the A extent,
    right, union and disjoint union give the D extent."""
    rows = run_select(series.session, "A {:,during,%s} D" % operator)
    assert [(start, end) for _, start, end in rows] == expected


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("l", (20, 30)),
        ("r", (25, 35)),
        ("i", (25, 30)),
        ("u", (20, 35)),
        ("d", (20, 35)),
    ],
)
def test_temporal_operator_overlaps(series, operator, expected):
    """a3 [20,30) overlaps b3 [25,35); the operator picks the result extent."""
    rows = run_select(series.session, "A {:,overlaps,%s} B" % operator)
    assert [(start, end) for _, start, end in rows] == [expected]


@pytest.mark.parametrize(
    ("word", "letter"),
    [
        ("left", "l"),
        ("right", "r"),
        ("intersect", "i"),
        ("union", "u"),
        ("disjoint", "d"),
    ],
)
def test_temporal_operator_words_equal_letters(series, word, letter):
    """The long and the short form of a temporal operator give the same extent."""
    by_word = run_select(series.session, "A {:,overlaps,%s} B" % word)
    by_letter = run_select(series.session, "A {:,overlaps,%s} B" % letter)
    assert [row[1:] for row in by_word] == [row[1:] for row in by_letter]


def test_temporal_operator_keeps_cell_values(series):
    """Maps that get a new extent are copies that keep the cell values."""
    result = f"values{next(result_counter)}"
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"{result} = A {{:,during,r}} D")
    listing = tools.t_rast_list(input=result, columns="min,max", format="json")
    assert [(row["min"], row["max"]) for row in listing["data"]] == [
        (2, 2),
        (3, 3),
        (4, 4),
    ]


def test_temporal_operator_result_map_names(series):
    """The copies made for a changed extent are named after the result dataset."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="copies = A {:,during,r} D")
    listing = tools.t_rast_list(input="copies", columns="name", format="json")
    assert [row["name"] for row in listing["data"]] == [
        "copies_1",
        "copies_2",
        "copies_3",
    ]


def test_unchanged_extent_keeps_map_names(series):
    """If the extent does not change, the result maps are the input maps."""
    assert run_select(series.session, "A {:,during,l} D") == [
        (name, *A_EXTENTS[name]) for name in ["a2", "a3", "a4"]
    ]


# Conditions with temporal functions


@pytest.mark.parametrize(
    ("condition", "dataset", "expected"),
    [
        ("td(A) == 10", "A", ["a1", "a2", "a3", "a4"]),
        ("td(A) == 11", "A", []),
        ("td(B) > 9", "B", ["b1", "b3", "b6", "b7", "b8"]),
        ("td(B) == 5", "B", ["b2", "b5"]),
        ("td(B) < 5", "B", ["b4", "b9"]),
        ("td(B) != 10", "B", ["b2", "b4", "b5", "b8", "b9"]),
        ('start_date(B) >= "2001-01-26"', "B", ["b3", "b5", "b6", "b9"]),
        ('start_date(A) < "2001-01-15"', "A", ["a1", "a2"]),
        ('end_date(A) == "2001-01-21"', "A", ["a2"]),
        ('start_datetime(A) > "2001-01-11 00:00:00"', "A", ["a3", "a4"]),
        ('end_datetime(A) <= "2001-01-21 00:00:00"', "A", ["a1", "a2"]),
        ('start_time(A) == "00:00:00"', "A", ["a1", "a2", "a3", "a4"]),
        ('start_time(A) > "00:00:00"', "A", []),
        ("start_doy(A) > 20", "A", ["a3", "a4"]),
        ("end_doy(A) == 21", "A", ["a2"]),
        ("start_year(B) == 2000", "B", ["b7"]),
        ("end_year(B) == 2000", "B", []),
        ("start_month(B) == 2", "B", ["b5", "b6"]),
        ("end_month(B) == 2", "B", ["b3", "b5", "b6"]),
        ("start_day(A) == 11", "A", ["a2"]),
        ("end_day(A) < 15", "A", ["a1", "a4"]),
        ("start_week(A) == 2", "A", ["a2"]),
        ("start_dow(A) == 1", "A", ["a1"]),
        ("start_hour(A) == 0", "A", ["a1", "a2", "a3", "a4"]),
        ("start_minute(A) == 1", "A", []),
        ("start_second(A) == 0", "A", ["a1", "a2", "a3", "a4"]),
        ("end_hour(A) == 0", "A", ["a1", "a2", "a3", "a4"]),
        ("end_minute(A) == 0", "A", ["a1", "a2", "a3", "a4"]),
        ("end_second(A) == 0", "A", ["a1", "a2", "a3", "a4"]),
        ("end_dow(A) == 4", "A", ["a1"]),
        ("end_week(A) == 5", "A", ["a3"]),
    ],
)
def test_if_with_temporal_function(series, condition, dataset, expected):
    """The then-part keeps the maps for which the condition is true."""
    assert (
        selected_names(series.session, "if(%s, %s)" % (condition, dataset)) == expected
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("start_doy(A) > 5 && start_doy(A) < 25", ["a2", "a3"]),
        ("start_doy(A) < 5 || start_doy(A) > 25", ["a1", "a4"]),
        ("start_doy(A) > 5 && td(A) == 11", []),
        ("start_doy(A) > 15 || td(A) == 10", ["a1", "a2", "a3", "a4"]),
    ],
)
def test_if_with_combined_conditions(series, condition, expected):
    """&& and || combine conditions of the same dataset."""
    assert selected_names(series.session, "if(%s, A)" % condition) == expected


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("A {#, contains} B > 1", ["a3"]),
        ("A {#, contains} B == 1", ["a1", "a4"]),
        ("A {#, contains} B >= 1", ["a1", "a3", "a4"]),
        ("A {#, contains} B < 1", []),
        ("A {#} B == 1", ["a2"]),
        ("A {#, equal} B == 1", ["a2"]),
        ("A {#, overlaps} B == 1", ["a3"]),
        ("A {#, equal|precedes} B == 1", ["a1", "a2", "a4"]),
        ("A {#, precedes} B >= 2", []),
        ("A {#, follows} B == 2", ["a3"]),
    ],
)
def test_if_with_hash_operator(series, condition, expected):
    """# counts the B maps that have the relation to each A map.

    b2 and b9 are in a3, b4 in a1, b5 in a4 (contains); a1 precedes b1 and a4
    precedes b6; a3 follows b1 and b8, a1 follows b7. A maps without any
    related B map have no count, so "< 1" selects nothing (t.select.md: the
    result is a list for the A maps that contain B maps).
    """
    assert selected_names(series.session, "if(%s, A)" % condition) == expected


@pytest.mark.parametrize("kind", ["stvds", "str3ds"])
def test_if_with_hash_operator_other_dataset_types(series, kind):
    """The hash operator counts maps of vector and 3D raster series."""
    assert selected_names(
        series.session, "if(A {#, contains} B > 1, A)", kind=kind
    ) == ["a3"]


@pytest.mark.parametrize("kind", ["stvds", "str3ds"])
def test_if_with_temporal_function_other_dataset_types(series, kind):
    """Conditions on temporal functions work for vector and 3D raster series."""
    assert selected_names(series.session, "if(start_doy(A) > 20, A)", kind=kind) == [
        "a3",
        "a4",
    ]


def test_if_hash_in_condition_and_selection_in_then(series):
    """The example of the manual: select A maps containing more than one B map."""
    assert selected_names(
        series.session, "if({equal}, A {#, contains} B > 1, A {:, contains} B)"
    ) == ["a3"]


def test_if_with_else(series):
    """The else-part supplies the B maps equal to the A maps that failed the test.

    The condition fails for a1 and a2; of the B maps only b1 equals one of
    them (a2).
    """
    assert selected_names(series.session, "if(start_doy(A) > 20, A, B)") == [
        "a3",
        "a4",
        "b1",
    ]


def test_if_with_inverse_selection_in_then(series):
    """The inverse selection is a conclusion like any other: a2, a3 and a4
    pass the condition, and a2 equals b1, so only a3 and a4 remain. Plain
    A as the conclusion would keep a2."""
    assert selected_names(series.session, "if(start_doy(A) > 5, A !: B)") == [
        "a3",
        "a4",
    ]
    assert selected_names(series.session, "if(start_doy(A) > 5, A)") == [
        "a2",
        "a3",
        "a4",
    ]


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("if({contains}, start_doy(A) > 0, B)", ["b2", "b4", "b5", "b9"]),
        ("if({contains}, start_doy(A) > 20, B)", ["b2", "b5", "b9"]),
    ],
)
def test_if_with_explicit_relation_reads_condition_relation_conclusion(
    series, expression, expected
):
    """if({R}, condition, conclusion) reads "condition R conclusion": the
    conclusion maps are the B maps within an A map that passes the test."""
    assert selected_names(series.session, expression) == expected


def test_if_then_other_dataset_has_no_equal_map(series):
    """The then-part dataset needs maps with the same extent as the condition."""
    assert run_select(series.session, "if(start_doy(A) > 20, B)") == []


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("if(td(A) == 10, A) : B", ["a2"]),
        ('if(start_date(A) < "2001-01-25", A) {:, precedes} B', ["a1"]),
        ("if(td(A) == 10 && start_doy(A) > 20, A {:, finished} B)", ["a4"]),
    ],
)
def test_if_combined_with_selection(series, expression, expected):
    """Conditional results can be selected from and selections can be conditional."""
    assert selected_names(series.session, expression) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("tsnap(A)", ["a1", "a2", "a3", "a4"]),
        ('A : tshift(B, "5 days")', ["a4"]),
        ('buff_t(A, "1 days") : B', []),
    ],
)
def test_temporal_functions_in_expression(series, expression, expected):
    """tsnap, tshift and buff_t take part in selections."""
    assert selected_names(series.session, expression) == expected


# Dataset selection


def test_select_from_dataset_in_other_mapset(series):
    """A dataset of another mapset is addressed as name@mapset."""
    assert run_select(series.session, "A : X@other") == [("a2", 10, 20), ("a4", 30, 40)]


def test_select_from_dataset_in_other_mapset_needs_mapset_name(series):
    """A dataset name without mapset refers to the current mapset only."""
    select_fails(series.session, "A : X", match="not found")


def test_select_from_other_mapset_on_the_left(series):
    """Maps of another mapset can be the selected maps."""
    assert run_select(series.session, "X@other {:, precedes} A") == [("x1", 10, 20)]


def test_selected_map_of_other_mapset_is_referenced(series):
    """The result registers the map of the other mapset like t.register does,
    it is not copied into the current mapset."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="referenced = X@other {:, precedes} A")
    listing = tools.t_rast_list(input="referenced", columns="id", format="json")
    assert [row["id"] for row in listing["data"]] == ["x1@other"]
    current = tools.g_list(type="raster", mapset="PERMANENT", format="json")
    assert "x1" not in [item["name"] for item in current]


def test_select_with_relation_to_dataset_in_other_mapset(series):
    """Relations to maps in another mapset use their time stamps."""
    assert selected_names(series.session, "A {:, precedes|follows} X@other") == [
        "a1",
        "a3",
    ]


def test_select_single_map_with_time_stamp(series):
    """tmap() makes a single map with a time stamp usable as right side."""
    tools = Tools(session=series.session, overwrite=True)
    tools.r_mapcalc(expression="event = 1")
    tools.r_timestamp(map="event", date="06 Jan 2001/15 Feb 2001")
    assert selected_names(series.session, "A {:, during} tmap(event)") == [
        "a2",
        "a3",
        "a4",
    ]


# Spatial topology


def test_select_without_spatial_flag_ignores_location(series):
    """Without -s only the time decides: both S maps match an A map."""
    assert selected_names(series.session, "A : S") == ["a2", "a3"]


def test_select_with_spatial_flag_checks_location(series):
    """With -s the map s1 outside the region of the A maps is not related."""
    assert selected_names(series.session, "A : S", flags="s") == ["a3"]


# Result dataset, dry run and overwrite


def test_empty_result_dataset_exists(series):
    """An empty selection still creates the result dataset with no maps."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="nothing = A {:, equal} D")
    assert "nothing@PERMANENT" in tools.t_list(type="strds").text.split()


def test_result_dataset_has_type_and_time_type_of_input(series):
    """The result is a STDS of the requested type with absolute time."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="typed = A : B", type="stvds")
    info = tools.t_info(input="typed", type="stvds", flags="g")
    assert info.keyval["temporal_type"] == "absolute"
    assert info.keyval["number_of_maps"] == 1


def test_dry_run_creates_no_result(series):
    """-d computes the plan but creates no dataset."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="dryresult = A : B", flags="d")
    with pytest.raises(ToolError):
        tools.t_info(input="dryresult")


def test_existing_result_is_not_overwritten_by_default(series):
    """Without overwrite, an existing result dataset is an error."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="kept = A : B")
    with pytest.raises(ToolError):
        Tools(session=series.session).t_select(expression="kept = A !: B")
    assert [
        row["name"]
        for row in tools.t_rast_list(input="kept", columns="name", format="json")[
            "data"
        ]
    ] == ["a2"]


def test_existing_result_is_replaced_with_overwrite(series):
    """With overwrite the result dataset is rebuilt."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression="replaced = A : B")
    tools.t_select(expression="replaced = A !: B")
    names = [
        row["name"]
        for row in tools.t_rast_list(input="replaced", columns="name", format="json")[
            "data"
        ]
    ]
    assert names == ["a1", "a3", "a4"]


def test_existing_result_without_overwrite_prints_one_error(series):
    """The refusal is printed once on both algebras. With the messenger in
    raise mode the classic algebra printed it twice, the library message and
    again the tool's own (measured 2026-10-14)."""
    Tools(session=series.session, overwrite=True).t_select(expression="once = A : B")
    refusing = Tools(
        session=series.session,
        capture_stderr=True,
        consistent_return_value=True,
        errors="ignore",
    )
    result = refusing.t_select(expression="once = A !: B")
    assert result.returncode != 0
    errors = [line for line in result.stderr.splitlines() if line.startswith("ERROR")]
    assert len(errors) == 1
    assert "once" in errors[0]


# Errors


@pytest.mark.parametrize("expression", ["A :", "A : Z", "A {:, equal, x} B"])
def test_errors_are_reported_without_traceback(series, expression):
    """Users get a GRASS error message, not a Python traceback."""
    tools = Tools(session=series.session, overwrite=True)
    with pytest.raises(ToolError) as error:
        tools.t_select(expression=f"failing = {expression}")
    assert "Traceback" not in error.value.stderr
    assert "ERROR" in error.value.stderr


@pytest.mark.parametrize(
    "expression",
    [
        "A :",
        "A B",
        "A {:} ",
        "A = B",
        "A {:, equal, x} B",
        "A {#, contains} B",
        "if(start_doy(A) > 20)",
        "if(A, B)",
        "A : : B",
        "A {:, equal B",
        "A {:, equal} {:} B",
        "(A : B",
        "A : B)",
    ],
)
def test_syntax_error_fails(series, expression):
    """Malformed expressions end with an error."""
    select_fails(series.session, expression)


def test_missing_assignment_fails(series):
    """The expression needs 'result = ' on the left side."""
    tools = Tools(session=series.session, overwrite=True)
    with pytest.raises(ToolError):
        tools.t_select(expression="A : B")


def test_unknown_dataset_fails(series):
    """A dataset that does not exist is reported."""
    with pytest.raises(ToolError, match="not found"):
        run_select(series.session, "A : Z")


def test_dataset_of_other_type_fails(series):
    """Raster datasets cannot be used with type=stvds when no vector dataset has
    that name."""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_create(type="strds", output="rasteronly", title="r", description="r")
    with pytest.raises(ToolError, match="not found"):
        tools.t_select(expression="r = rasteronly : rasteronly", type="stvds")


@pytest.mark.parametrize(
    "operator",
    [
        "{:, equal, x}",
        "{=, equal}",
        "{:, equal, l, r}",
        "{:, foo}",
        "{:, equal | }",
        "{:, equivalent}",
    ],
)
def test_invalid_temporal_operator_fails(series, operator):
    """Unknown relations, temporal operators and malformed operators are errors."""
    select_fails(series.session, "A %s B" % operator)


def test_blank_before_temporal_operator(series):
    """Blanks around the temporal operator are allowed."""
    rows = run_select(series.session, "A {:, during, r} D")
    assert [(start, end) for _, start, end in rows] == [(5, 45)] * 3


def test_classic_flag_overrides_the_variable(series):
    """-c runs the classic algebra even when the variable asks for the core"""
    tools = Tools(session=series.session, overwrite=True)
    env = dict(series.session.env, GRASS_TEMPORAL_ALGEBRA="core")
    # A fresh name per run: the copies of the first run stay in the mapset.
    result = f"flagged{next(result_counter)}"
    tools.t_select(expression=f"{result} = A {{:,during,r}} D", flags="c", env=env)
    names = [
        row["name"]
        for row in tools.t_rast_list(input=result, columns="name", format="json")[
            "data"
        ]
    ]
    assert sorted(names) == [f"{result}_1", f"{result}_2", f"{result}_3"]
    # The result above is the same on both algebras. The neighbourhood
    # modifier A[1] is only read by the core, so its rejection shows that the
    # flag, not the variable, chose the algebra.
    tools.t_select(expression=f"{result}_n = A[1]", env=env)
    with pytest.raises(ToolError):
        tools.t_select(expression=f"{result}_c = A[1]", flags="c", env=env)


@pytest.mark.parametrize("function", ["strds", "str3ds", "stvds"])
def test_dataset_type_function_hints_at_the_classic_flag(series, algebra, function):
    """Only the classic algebra mixes dataset types; the message of the core
    says so for the three functions that do it, and for no other"""
    if algebra != "core":
        pytest.skip("the classic algebra reads the function")
    tools = Tools(session=series.session, overwrite=True)
    with pytest.raises(ToolError) as error:
        tools.t_select(expression=f"hinted = {function}(A) : B")
    assert f"Unknown function {function}()" in error.value.stderr
    assert "Use the flag -c" in error.value.stderr


def test_other_unknown_function_has_no_classic_hint(series, algebra):
    if algebra != "core":
        pytest.skip("the classic algebra reports another error")
    tools = Tools(session=series.session, overwrite=True)
    with pytest.raises(ToolError) as error:
        tools.t_select(expression="hinted = nosuch(A) : B")
    assert "Unknown function nosuch()" in error.value.stderr
    assert "-c" not in error.value.stderr


def test_dataset_type_function_works_with_the_classic_flag(series, algebra):
    """The hint is right: -c selects with strds(A)"""
    if algebra != "core":
        pytest.skip("the flag is the point of the test")
    assert run_select(series.session, "strds(A) : B", flags="c") == run_select(
        series.session, "A : B", flags="c"
    )
