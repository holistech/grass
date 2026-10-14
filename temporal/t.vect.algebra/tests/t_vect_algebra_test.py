"""Test t.vect.algebra: selection, overlay, buffer, conditions, flags and errors

The datasets are described in the vector_series fixture in conftest.py. Results
are checked through the metadata that t.vect.list reports for the result
dataset (time stamps and the numbers of points, areas and centroids of each
map). All expected values were derived by hand from the geometry of the input
maps: squares are 10x10 and overlap partially (aa1/ab1 share a 5x10 strip).
"""

import itertools

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.tools import ToolError, Tools

_counter = itertools.count()


def day(n):
    """Time stamp of midnight of January n, 2001"""
    return f"2001-01-{n:02d} 00:00:00"


def run_algebra(session, expression, flags="", overwrite=True, classic=None):
    """Run the algebra in this process and return the name of the result dataset.

    This mirrors what the tool does with its flags. classic=None follows
    GRASS_TEMPORAL_ALGEBRA where both algebras agree; True and False choose
    the algebra where they differ.
    """
    name = f"res{next(_counter)}"
    parser = tgis.TemporalVectorAlgebraParser(
        run=True, debug=False, spatial="s" in flags, classic=classic
    )
    parser.parse(f"{name} = {expression}", name, overwrite)
    return name


def _stamp(value):
    return None if value is None else value.strftime("%Y-%m-%d %H:%M:%S")


def list_maps(session, name):
    """Rows of the result dataset, or None if the dataset does not exist"""
    stds = tgis.dataset_factory("stvds", f"{name}@PERMANENT")
    if not stds.is_in_db():
        return None
    stds.select()
    rows = []
    for vector in stds.get_registered_maps_as_objects(order="start_time") or []:
        start, end = vector.get_absolute_time()
        vector.select()
        meta = vector.metadata
        rows.append(
            {
                "id": vector.get_id(),
                "start_time": _stamp(start),
                "end_time": _stamp(end),
                "points": meta.get_number_of_points(),
                "lines": meta.get_number_of_lines(),
                "centroids": meta.get_number_of_centroids(),
                "areas": meta.get_number_of_areas(),
            }
        )
    return rows


def timeline(session, expression, flags="", classic=None):
    """(start day, end day) of the maps resulting from an expression"""
    name = run_algebra(session, expression, flags, classic=classic)
    rows = list_maps(session, name)
    assert rows is not None
    return [(row["start_time"], row["end_time"]) for row in rows]


def counts(session, expression, key="areas", flags="", classic=None):
    """Per-map value of a metadata column for the maps of the result"""
    name = run_algebra(session, expression, flags, classic=classic)
    rows = list_maps(session, name)
    assert rows is not None
    return [row[key] for row in rows]


def days(*pairs):
    """Expected timeline from pairs of day numbers"""
    return [(day(start), day(end)) for start, end in pairs]


DAILY = days((1, 2), (2, 3), (3, 4))


# Temporal selection


@pytest.mark.parametrize(
    ("expression", "expected_ids"),
    [
        ("aa : ab", ["aa1", "aa2", "aa3"]),
        ("aa {:,equal} ab", ["aa1", "aa2", "aa3"]),
        ("aa {:,equal,l} ab", ["aa1", "aa2", "aa3"]),
        ("aa !: wide", ["aa1", "aa2", "aa3"]),
        ("aa {!:,starts} wide", ["aa2"]),
        ("aa {:,starts} wide", ["aa1", "aa3"]),
        ("aa {:,starts|finishes} wide", ["aa1", "aa2", "aa3"]),
        ("aa {:,during} wide", ["aa1", "aa2", "aa3"]),
        ("wide {:,contains} aa", ["wide1", "wide2"]),
        ("aa : tmap(ev)", ["aa2"]),
        ("aa {!:,equal} tmap(ev)", ["aa1", "aa3"]),
    ],
)
def test_selection_picks_input_maps(vector_series, expression, expected_ids):
    """Selection returns the original input maps without creating new ones"""
    name = run_algebra(vector_series.session, expression)
    rows = list_maps(vector_series.session, name)
    assert [row["id"] for row in rows] == [f"{m}@PERMANENT" for m in expected_ids]


@pytest.mark.parametrize(
    "expression",
    ["aa {!:,during} wide", "aa {:,contains} wide"],
)
@pytest.mark.parametrize(("classic", "expected"), [(False, []), (True, None)])
def test_selection_without_maps(vector_series, expression, classic, expected):
    """An empty result creates an empty dataset; the classic algebra creates
    no dataset (None)"""
    name = run_algebra(vector_series.session, expression, classic=classic)
    assert list_maps(vector_series.session, name) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("aa {:,during,r} wide", days((1, 3), (1, 3), (3, 5))),
        ("aa {:,starts,r} wide", days((1, 3), (3, 5))),
        ("wide {:,contains,l} aa", days((1, 3), (3, 5))),
        ("wide {:,contains,u} aa", days((1, 3), (3, 5))),
        ("aa {:,during,i} wide", days((1, 2), (2, 3), (3, 4))),
        ("aa {:,during,l} wide", DAILY),
    ],
)
def test_selection_temporal_operator(vector_series, expression, expected):
    """The temporal operator sets the time stamps of the selected maps"""
    assert timeline(vector_series.session, expression) == expected


def test_selection_with_temporal_operator_does_not_change_inputs(vector_series):
    """Time stamps of input maps stay untouched when results get new extents"""
    before = list_maps(vector_series.session, "aa")
    timeline(vector_series.session, "aa {:,during,r} wide")
    assert list_maps(vector_series.session, "aa") == before


def test_selection_with_new_extent_copies_maps(vector_series):
    """Maps whose extent changes are copied to basename_N, so the input stays"""
    name = run_algebra(vector_series.session, "aa {:,starts,r} wide")
    ids = [row["id"] for row in list_maps(vector_series.session, name)]
    assert ids == [f"{name}_0@PERMANENT", f"{name}_1@PERMANENT"]
    existing = gs.list_strings(
        "vector", pattern=f"{name}_*", env=vector_series.session.env
    )
    assert sorted(existing) == [f"{name}_0@PERMANENT", f"{name}_1@PERMANENT"]


def test_selection_by_single_map(vector_series):
    """tmap() makes a single time stamped map usable as selection reference"""
    assert timeline(vector_series.session, "aa : tmap(ev)") == days((2, 3))


def test_nested_selection(vector_series):
    """Selections can be chained: the result of the first one is the input"""
    assert timeline(vector_series.session, "aa : ab !: tmap(ev)") == days(
        (1, 2), (3, 4)
    )


# Temporal functions on the dataset itself


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('tshift(aa, "1 day")', days((2, 3), (3, 4), (4, 5))),
        ("tsnap(aa)", DAILY),
        ('tshift(aa, "1 day") : aa', days((2, 3), (3, 4))),
    ],
)
def test_temporal_shift_and_snap(vector_series, expression, expected):
    """tshift moves all maps by the granule; tsnap keeps gapless intervals"""
    assert timeline(vector_series.session, expression) == expected


@pytest.mark.parametrize("classic", [False, True])
def test_time_function_that_changes_nothing_registers_the_inputs(
    vector_series, classic
):
    """tsnap() of gapless maps leaves every time stamp as it is, so the result
    dataset registers the maps aa1..aa3 themselves and makes no copies (measured
    2026-10-14 on both algebras), while a shift gives a new extent and so
    copies named after the result"""
    session = vector_series.session
    snapped = run_algebra(session, "tsnap(aa)", classic=classic)
    assert [row["id"] for row in list_maps(session, snapped)] == [
        "aa1@PERMANENT",
        "aa2@PERMANENT",
        "aa3@PERMANENT",
    ]
    shifted = run_algebra(session, 'tshift(aa, "1 day")', classic=classic)
    assert [row["id"] for row in list_maps(session, shifted)] == [
        f"{shifted}_{number}@PERMANENT" for number in range(3)
    ]


# Spatial overlay operators


@pytest.mark.parametrize(
    ("expression", "expected_areas"),
    [
        # aa1/ab1 and aa2/ab2 overlap by 5x10; aa3 and ab3 are far apart
        ("aa & ab", [1, 1]),
        ("aa | ab", [3, 3]),
        ("aa ^ ab", [2, 2]),
        ("aa ~ ab", [1, 1]),
        ("aa {&,equal} ab", [1, 1]),
        ("aa {|,equal} ab", [3, 3]),
        ("aa {^,equal} ab", [2, 2]),
        ("aa {~,equal} ab", [1, 1]),
        ("aa {&,equal,l} ab", [1, 1]),
        ("aa {&,equal,r} ab", [1, 1]),
        ("aa {&,equal,i} ab", [1, 1]),
        ("aa {|,equal,u} ab", [3, 3]),
    ],
)
def test_overlay_operators_areas(vector_series, expression, expected_areas):
    """Overlay operators give the areas of v.overlay with and, or, xor and not.

    Expected for the overlapping pairs aa1/ab1 and aa2/ab2: intersection 1
    area; union 3 areas (left, middle, right strip); xor 2 areas; not 1 area.
    The third pair is far apart and covered by the NEW-1 test below.
    """
    result = counts(vector_series.session, expression)
    assert result[:2] == expected_areas


@pytest.mark.parametrize(
    ("expression", "expected_areas"),
    [
        ("aa | ab", [3, 3, 2]),
        ("aa ^ ab", [2, 2, 2]),
        ("aa ~ ab", [1, 1, 1]),
    ],
)
def test_overlay_non_and_keeps_disjoint_pairs(
    vector_series, expression, expected_areas
):
    """Union, xor and not keep a pair whose maps do not touch each other"""
    assert counts(vector_series.session, expression) == expected_areas


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("aa & ab", days((1, 2), (2, 3))),
        ("aa {&,equal,l} ab", days((1, 2), (2, 3))),
        ("aa {&,during} wide", days((1, 2), (3, 4))),
        ("aa {&,during,l} wide", days((1, 2), (3, 4))),
        ("aa {&,during,r} wide", days((1, 3), (3, 5))),
        ("aa {&,during,i} wide", days((1, 2), (3, 4))),
        ("aa {&,during,u} wide", days((1, 3), (3, 5))),
    ],
)
def test_overlay_time_stamps(vector_series, expression, expected):
    """Result maps get the time stamps given by the temporal operator.

    aa1 and aa3 overlap wide1 and wide2; aa2 does not touch wide1.
    """
    assert timeline(vector_series.session, expression) == expected


def test_overlay_patch(vector_series):
    """The + operator patches (v.patch) the maps, keeping all centroids"""
    result = counts(vector_series.session, "aa + ab", key="centroids")
    assert result[:2] == [2, 2]


def test_overlay_patch_points_with_disjoint_extents(vector_series):
    """Patching disjoint point maps keeps every pair"""
    assert counts(vector_series.session, "pa + pb", key="points") == [3, 4, 5]


@pytest.mark.parametrize(
    "expression",
    ["aa {+,equal} ab", "aa {+,equal,l} ab", "aa {+,starts} wide"],
)
def test_overlay_patch_with_relation(vector_series, expression):
    """The patch operator accepts relation and temporal operator in braces"""
    assert len(timeline(vector_series.session, expression)) >= 2


@pytest.mark.parametrize(
    ("expression", "expected_areas"),
    [
        ("ac | aa", [2, 3, 3]),
        ("ac ^ aa", [1, 3, 3]),
        ("ac ~ aa", [1, 2, 2]),
    ],
)
def test_overlay_maps_with_several_areas(vector_series, expression, expected_areas):
    """Maps with two separate squares: ac has squares at x=0 and x=50.

    The same square in ac1 and aa1 cancels out for xor and not.
    """
    assert counts(vector_series.session, expression)[: len(expected_areas)] == (
        expected_areas
    )


@pytest.mark.parametrize(("classic", "expected_areas"), [(False, [1]), (True, [1, 0])])
def test_overlay_without_common_area(vector_series, classic, expected_areas):
    """ac1 & ab1: the square of ac1 at x=0 overlaps ab1, so one area remains.
    ac2 & ab2 do not overlap, so the overlay has no areas.

    A vector map without primitives is not registered; the classic algebra
    registers it.
    """
    assert counts(vector_series.session, "ac & ab", classic=classic) == expected_areas


@pytest.mark.parametrize(("classic", "expected_areas"), [(False, [1]), (True, [0, 1])])
def test_overlay_implicit_aggregation(vector_series, classic, expected_areas):
    """wide1 contains aa1 and aa2, so both are overlaid with it: c1 = w1 & a1 & a2.

    The strip of aa1 inside wide1 does not meet aa2, hence the map has no area
    and is not registered; the classic algebra registers it. wide2 & aa3
    leaves one area.
    """
    assert (
        counts(vector_series.session, "wide {&,contains} aa", classic=classic)
        == expected_areas
    )


def test_overlay_aggregation_is_not_symmetric(vector_series):
    """aa {&,during} wide gives one map per aa map, not one per wide map"""
    assert len(timeline(vector_series.session, "aa {&,during} wide")) == 2


def test_overlay_of_overlay(vector_series):
    """Overlay results can be used as operand of further overlays"""
    assert counts(vector_series.session, "(aa & ab) | aa") == [2, 2]


def test_overlay_three_operands(vector_series):
    """aa & ab & ac: only the strip in the square at x=0 is left on day 1"""
    assert counts(vector_series.session, "aa & ab & ac")[0] == 1


@pytest.mark.parametrize("expression", ["aa & ab", "aa | ab", "aa {&,during} wide"])
def test_overlay_result_maps_exist(vector_series, expression):
    """Every map registered in the result dataset exists in the mapset"""
    name = run_algebra(vector_series.session, expression)
    rows = list_maps(vector_series.session, name)
    existing = gs.list_strings(
        "vector", pattern=f"{name}_*", env=vector_series.session.env
    )
    assert [row["id"] for row in rows] == sorted(existing)
    assert existing


# Buffers


@pytest.mark.parametrize(
    ("expression", "key", "expected"),
    [
        ("buff_p(pa, 1)", "areas", [1, 2, 3]),
        ("buff_p(pa, 1)", "points", [0, 0, 0]),
        ("buff_p(pa, 1)", "centroids", [1, 2, 3]),
        # points are 10 apart: radius 6 makes the circles overlap and merge
        ("buff_p(pa, 6)", "areas", [1, 1, 1]),
        ("buff_l(la, 2)", "areas", [1, 1, 1]),
        ("buff_l(la, 2)", "lines", [0, 0, 0]),
        ("buff_a(aa, 2)", "areas", [1, 1, 1]),
        ("buff_a(buff_p(pa, 1), 1)", "areas", [1, 2, 3]),
    ],
)
def test_buffers(vector_series, expression, key, expected):
    """Buffers create areas around points, lines and areas of every map"""
    assert counts(vector_series.session, expression, key) == expected


@pytest.mark.parametrize(
    "expression", ["buff_p(pa, 1)", "buff_l(la, 2)", "buff_a(aa, 2)"]
)
def test_buffer_keeps_time_stamps(vector_series, expression):
    """Buffering does not change the temporal extent"""
    assert timeline(vector_series.session, expression) == DAILY


def test_buffer_maps_are_created_with_basename(vector_series):
    """Buffer results are real maps named basename_0, basename_1, ..."""
    name = run_algebra(vector_series.session, "buff_p(pa, 1)")
    existing = gs.list_strings(
        "vector", pattern=f"{name}_*", env=vector_series.session.env
    )
    assert sorted(existing) == [f"{name}_{i}@PERMANENT" for i in range(3)]


def test_buffer_result_maps_hold_the_buffer(vector_series):
    """The map itself, not only its metadata, contains the buffer areas"""
    name = run_algebra(vector_series.session, "buff_p(pa, 1)")
    tools = Tools(session=vector_series.session)
    info = tools.v_info(map=f"{name}_2", flags="t", format="json")
    assert (info["areas"], info["centroids"], info["points"]) == (3, 3, 0)


def test_buffer_combined_with_overlay(vector_series):
    """Buffer results work as operands of overlay operators"""
    assert len(timeline(vector_series.session, "buff_l(la, 2) & aa")) == 3


@pytest.mark.parametrize(
    ("classic", "expected_areas"), [(False, [1, 1]), (True, [1, 1, 0])]
)
def test_buffers_combined_without_common_area(vector_series, classic, expected_areas):
    """The buffers of pa3 and aa3 do not meet: the point of pa3 nearest to
    aa3 (x 40 to 50, y 0 to 10) is (20, 30), 28.3 from the corner (40, 10),
    which is more than the sum 26 of both distances.

    A vector map without primitives is not registered; the classic algebra
    registers it.
    """
    expression = "buff_p(pa, 6) & buff_a(aa, 20)"
    assert counts(vector_series.session, expression, classic=classic) == expected_areas


def test_buffer_line_and_area_overlay_area_count(vector_series):
    """The buffer of la_i (y=5, length 10) lies inside aa_i: one common area"""
    assert counts(vector_series.session, "buff_l(la, 2) & aa") == [1, 1, 1]


# Conditions


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ('if(start_date(aa) > "2001-01-01", aa)', days((2, 3), (3, 4))),
        (
            'if(start_date(aa) > "2001-01-01", aa, ab)',
            days((1, 2), (2, 3), (3, 4)),
        ),
        ("if(start_month(aa) == 1 && start_day(aa) < 3, aa)", days((1, 2), (2, 3))),
        ("if(td(aa) == 1, aa)", DAILY),
        ("if({equal}, wide {#,contains} aa > 1, wide)", days((1, 3))),
        ('if(start_date(aa) < "2001-01-03", aa & ab)', days((1, 2), (2, 3))),
    ],
)
def test_conditions(vector_series, expression, expected):
    """if() selects maps by temporal functions, hash counts and combinations.

    The hash example counts the aa maps inside each wide map: wide1 holds
    aa1 and aa2, wide2 holds aa3, so only wide1 has more than one.
    """
    assert timeline(vector_series.session, expression) == expected


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        ("contains", DAILY),
        ("during", []),
    ],
)
def test_condition_relation_reads_condition_to_conclusion(
    vector_series, relation, expected
):
    """A wide map contains the aa maps that lie within it; the aa maps
    contain no wide map. The condition maps are the wide maps, so the
    conclusion maps are the aa maps within them."""
    expression = f"if({{{relation}}}, td(wide) > 0, aa)"
    name = run_algebra(vector_series.session, expression)
    rows = list_maps(vector_series.session, name)
    assert [(row["start_time"], row["end_time"]) for row in rows or []] == expected


def test_merge_of_vector_datasets(vector_series):
    """merge() is the union of the maps of both operands: aa and ab have
    different maps at the same days, so all six stay"""
    name = run_algebra(vector_series.session, "merge(aa, ab)")
    rows = list_maps(vector_series.session, name)
    assert [(row["start_time"], row["end_time"]) for row in rows] == sorted(
        DAILY + DAILY
    )
    assert [row["areas"] for row in rows] == [1] * 6


def test_merge_of_overlay_results(vector_series):
    """Overlay results carry their commands into merge(): the two overlays of
    aa & ab (aa3 and ab3 do not overlap) join the three maps of aa"""
    assert timeline(vector_series.session, "merge(aa & ab, aa)") == sorted(
        days((1, 2), (2, 3)) + DAILY
    )


def test_condition_with_overlay_result_maps(vector_series):
    """The overlay in the then-branch of a condition produces areas"""
    result = counts(vector_series.session, 'if(start_date(aa) < "2001-01-03", aa & ab)')
    assert result == [1, 1]


def test_hash_operator_is_not_a_map_expression(vector_series):
    """A bare hash expression is an error: it yields numbers, not maps"""
    with pytest.raises(SyntaxError):
        run_algebra(vector_series.session, "aa {#,during} wide")


# Spatial flag


def test_spatial_topology_flag_drops_spatially_unrelated_maps(vector_series):
    """With -s, maps of aa3 and ab3 (far apart) are not related"""
    assert len(timeline(vector_series.session, "aa : ab")) == 3
    assert timeline(vector_series.session, "aa : ab", flags="s") == days((1, 2), (2, 3))


def test_spatial_topology_flag_keeps_overlapping_maps(vector_series):
    """With -s, overlay of related maps gives the same result as without"""
    assert counts(vector_series.session, "aa & ab", flags="s") == [1, 1]


def test_classic_flag_selects_the_classic_algebra(vector_series):
    """An empty result creates an empty dataset in the core and none in the
    classic algebra"""
    # The flag must win over the variable, which therefore selects the core.
    env = {**vector_series.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tools = Tools(env=env, overwrite=True)
    # No daily map of aa contains one of the two-day maps of wide.
    expression = "{name} = aa {{:,contains}} wide"
    tools.t_vect_algebra(
        expression=expression.format(name="flag_core"), basename="flag_core"
    )
    tools.t_vect_algebra(
        expression=expression.format(name="flag_classic"),
        basename="flag_classic",
        flags="c",
    )
    assert list_maps(vector_series.session, "flag_core") == []
    assert list_maps(vector_series.session, "flag_classic") is None


# Names, overwrite and empty results


def test_basename_is_used_for_new_maps(vector_series):
    """New maps are named <basename>_<number> in order of time"""
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.t_vect_algebra(expression="named = buff_p(pa, 1)", basename="mybase")
    rows = list_maps(vector_series.session, "named")
    assert [row["id"] for row in rows] == [f"mybase_{i}@PERMANENT" for i in range(3)]


def test_existing_result_maps_without_overwrite_give_clean_error(vector_series):
    """Existing result maps are refused with a hint on the overwrite flag."""
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.t_vect_algebra(expression="again = buff_p(pa, 1)", basename="again")
    tools = Tools(session=vector_series.session, overwrite=False)
    with pytest.raises(ToolError) as error:
        tools.t_vect_algebra(expression="again2 = buff_p(pa, 1)", basename="again")
    assert "NameError" not in str(error.value)
    assert "again_0" in str(error.value)


def test_new_extent_without_overwrite(vector_series):
    """A selection with new extent works without --o if no result exists.

    The result maps do not exist, so nothing has to be overwritten.
    """
    tools = Tools(session=vector_series.session, overwrite=False)
    tools.t_vect_algebra(expression="fresh = aa {:,starts,r} wide", basename="fresh")
    assert len(list_maps(vector_series.session, "fresh")) == 2


def test_existing_result_dataset_without_overwrite(vector_series):
    """An existing result dataset is refused with a clean message"""
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.t_vect_algebra(expression="keep = buff_p(pa, 1)", basename="keep")
    tools = Tools(session=vector_series.session, overwrite=False)
    with pytest.raises(ToolError) as error:
        tools.t_vect_algebra(expression="keep = buff_p(pa, 1)", basename="other")
    assert "NameError" not in str(error.value)
    assert "overwrite" in str(error.value).lower()


def test_overwrite_replaces_result(vector_series):
    """With overwrite the same expression and basename can be run twice"""
    tools = Tools(session=vector_series.session, overwrite=True)
    for _ in range(2):
        tools.t_vect_algebra(expression="twice = buff_p(pa, 1)", basename="twice")
    assert len(list_maps(vector_series.session, "twice")) == 3


@pytest.mark.parametrize(("classic", "expected"), [(False, []), (True, None)])
def test_empty_selection_creates_an_empty_dataset(vector_series, classic, expected):
    """A selection without hits creates an empty result dataset, as in
    t.rast.algebra; the classic algebra leaves no dataset behind (None).
    Neither raises an error.
    """
    name = run_algebra(vector_series.session, "aa {:,during} tmap(ev)", classic=classic)
    assert list_maps(vector_series.session, name) == expected


def test_overlay_of_maps_without_areas_reports_error(vector_series):
    """Overlay of point maps must fail with a message, not vanish silently"""
    with pytest.raises(FatalError, match="has no areas"):
        run_algebra(vector_series.session, "pc & pc")


# Errors


@pytest.mark.parametrize(
    "expression",
    ["aa {&,nonsense} ab", "aa {:,nonsense} ab", "aa {:,equals} ab"],
)
def test_unknown_relation_is_an_error(vector_series, expression):
    """A misspelled temporal relation ends the tool with an error"""
    with pytest.raises(SyntaxError):
        run_algebra(vector_series.session, expression)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("aa {:} ab", DAILY), ("aa {!:} tmap(ev)", days((1, 2), (3, 4)))],
)
def test_selection_without_relation_list(vector_series, expression, expected):
    """{:} and {!:} are shortcuts for the equal relation"""
    assert timeline(vector_series.session, expression) == expected


@pytest.mark.parametrize("expression", ["res = aa &", "res = aa : ", "res = (aa : ab"])
def test_truncated_expressions_raise_syntax_error(vector_series, expression):
    """An expression that ends in the middle of a construct is a syntax error"""
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False)
    with pytest.raises(SyntaxError):
        parser.parse(expression, "bad", True)


@pytest.mark.parametrize(
    "expression",
    [
        "res = & ab",
        "res = aa {&,equal,x} ab",
        "res = buff_p(aa)",
        "res = buff_p(aa, one)",
        "res = nosuchdataset : ab",
        "aa : ab",
        "res = if(start_date(aa) >, aa)",
    ],
)
def test_invalid_expressions_fail(vector_series, expression):
    """Syntax errors and unknown datasets are reported as exceptions"""
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False)
    # The core reads "one" in buff_p(aa, one) as a dataset and does not find
    # it, where the classic grammar reports a syntax error.
    with pytest.raises((SyntaxError, FatalError)):
        parser.parse(expression, "bad", True)
    assert list_maps(vector_series.session, "res") is None


def test_raster_dataset_names_are_refused(vector_series):
    """Space time raster datasets do not belong in vector algebra"""
    tools = Tools(session=vector_series.session, overwrite=True)
    tools.g_region(n=100, s=0, e=100, w=0, res=10)
    tools.r_mapcalc(expression="rmap = 1")
    tools.t_create(
        output="rast", type="strds", temporaltype="absolute", title="r", description="r"
    )
    tools.t_register(input="rast", maps="rmap", start="2001-01-01", end="2001-01-02")
    with pytest.raises(ToolError):
        tools.t_vect_algebra(expression="res = rast : aa", basename="bad")


def test_inputs_unchanged_after_all_operations(vector_series):
    """Input datasets keep their maps and time stamps after the whole suite"""
    for name, ids in [("aa", 3), ("ab", 3), ("wide", 2), ("pa", 3), ("la", 3)]:
        assert len(list_maps(vector_series.session, name)) == ids
    assert [row["start_time"] for row in list_maps(vector_series.session, "aa")] == [
        day(1),
        day(2),
        day(3),
    ]


def test_result_of_relative_time_input_is_relative(vector_series):
    """The result dataset takes over the temporal type of its input maps"""
    name = run_algebra(vector_series.session, "buff_p(rel, 1)")
    stds = tgis.open_old_stds(name, "stvds")
    assert stds.get_temporal_type() == "relative"
    assert [row["areas"] for row in list_maps(vector_series.session, name)] == [1, 2]


def test_parse_returns_registered_maps(vector_series):
    """parse() returns the process chain with the maps registered in the result"""
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False)
    chain = parser.parse("chain = buff_p(pa, 1)", "chain", True)
    assert [entry[0] for entry in chain["register"]] == [
        "chain_0",
        "chain_1",
        "chain_2",
    ]


@pytest.mark.parametrize(
    "expression",
    [
        "aa {&, equal, l} ab",
        "aa {&,equal, l} ab",
        "aa {&, equal,l} ab",
        "aa {&, equal} ab",
    ],
)
def test_blanks_in_overlay_operator(vector_series, expression):
    """Blanks after the commas of an overlay operator are allowed"""
    assert counts(vector_series.session, expression) == [1, 1]


def test_debug_output(vector_series, capsys):
    """debug=True prints each module call as a command line"""
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=True, classic=False)
    parser.parse("dbg = aa & ab", "dbg", True)
    assert (
        "v.overlay ainput=aa1@PERMANENT binput=ab1@PERMANENT operator=and"
        in capsys.readouterr().out
    )
    parser.parse('dbg = tshift(aa, "1 day")', "dbg", True)
    assert "g.copy vector=aa1@PERMANENT,dbg_0" in capsys.readouterr().out


def test_debug_output_without_run(vector_series, capsys):
    """With run=False only the syntax is checked, so nothing is planned and
    debug=True prints nothing"""
    parser = tgis.TemporalVectorAlgebraParser(run=False, debug=True, classic=False)
    parser.parse("dbg = aa & ab", "dbg", True)
    assert not capsys.readouterr().out


@pytest.mark.parametrize("run", [True, False])
def test_debug_output_of_the_classic_algebra(vector_series, capsys, run):
    """With debug=True the classic algebra prints the parsed rules, with or
    without running"""
    parser = tgis.TemporalVectorAlgebraParser(run=run, debug=True, classic=True)
    parser.parse("dbg = aa & ab", "dbg", True)
    assert "aa&ab" in capsys.readouterr().out


def test_deprecated_overlay_cmd_value_alias(vector_series, monkeypatch):
    """overlay_cmd_value forwards to operator_cmd_value with the new arguments"""
    parser = tgis.TemporalVectorAlgebraParser(run=True, debug=False, classic=True)
    calls = []
    monkeypatch.setattr(
        parser, "operator_cmd_value", lambda *args: calls.append(args) or ["cmd"]
    )
    assert parser.overlay_cmd_value("map", {}, "&", ["DURING"]) == ["cmd"]
    assert calls == [("map", "&", ["DURING"])]
