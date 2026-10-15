"""Test t.rast3d.algebra: arithmetic, relations, selection, conditions, neighbors

The datasets are described in the series_3d fixture in conftest.py. Results are
checked through t.rast3d.list (time stamps and minimum and maximum of every
map). All cells of a map carry one value, so minimum and maximum agree and the
expected values were derived by hand.
"""

import itertools

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal.temporal_raster_algebra import ALGEBRA_VARIABLE
from grass.temporal.testing.reference import run_reference
from grass.tools import ToolError, Tools

pytestmark = pytest.mark.real_io

ALGEBRA_ERRORS = (SyntaxError, tgis.FatalError, FatalError)
_counter = itertools.count()


def day(n, time="00:00:00"):
    """Time stamp of January n, 2001"""
    return f"2001-01-{n:02d} {time}"


def run_algebra(session, expression, flags="", nprocs=1, classic=None):
    """Run the algebra in this process and return the name of the result dataset.

    This mirrors what the tool does with its flags. classic=None follows
    GRASS_TEMPORAL_ALGEBRA where both algebras agree; True and False choose
    the algebra where they differ.
    """
    name = f"res{next(_counter)}"
    full = f"{name} = {expression}"
    parser = tgis.TemporalRaster3DAlgebraParser(
        run=True,
        debug=False,
        spatial="s" in flags,
        nprocs=nprocs,
        register_null="n" in flags,
        classic=classic,
    )
    if "g" in flags:
        assert parser.setup_common_granularity(
            expression=full,
            stdstype="str3ds",
            lexer=tgis.TemporalRasterAlgebraLexer(),
        )
    parser.parse(full, name, True)
    return name


def _stamp(value):
    return None if value is None else value.strftime("%Y-%m-%d %H:%M:%S")


def list_maps(session, name):
    """Rows (start, end, min, max, name) of a dataset, or None if it is missing"""
    stds = tgis.dataset_factory("str3ds", f"{name}@PERMANENT")
    if not stds.is_in_db():
        return None
    stds.select()
    rows = []
    for raster in stds.get_registered_maps_as_objects(order="start_time") or []:
        raster.select()
        start, end = raster.get_absolute_time()
        meta = raster.metadata
        rows.append(
            (
                _stamp(start),
                _stamp(end),
                meta.get_min(),
                meta.get_max(),
                raster.get_name(),
            )
        )
    return rows


def result(session, expression, flags="", **options):
    """Rows (start, end, min, max, name) of the result of an expression"""
    name = run_algebra(session, expression, flags, **options)
    return list_maps(session, name)


def values(session, expression, flags="", classic=None):
    """Value of every result map; asserts that min and max are equal"""
    rows = result(session, expression, flags, classic=classic)
    assert all(row[2] == row[3] for row in rows)
    return [row[2] for row in rows]


def daily(*numbers):
    """Expected (start, end) pairs of one day intervals starting on given days"""
    return [(day(n), day(n + 1)) for n in numbers]


def intervals(*pairs):
    """Expected (start, end) pairs given by day numbers"""
    return [(day(start), day(end)) for start, end in pairs]


def times(rows):
    """Start and end of each row"""
    return [row[:2] for row in rows]


# Arithmetic


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A + B", [11, 22, 33, 44]),
        ("A - B", [-9, -18, -27, -36]),
        ("A * B", [10, 40, 90, 160]),
        ("B / A", [10, 10, 10, 10]),
        ("B % A", [0, 0, 0, 0]),
        ("A + B + A", [12, 24, 36, 48]),
        ("A * 2 + B", [12, 24, 36, 48]),
        ("(A + B) * 2", [22, 44, 66, 88]),
        ("A + 1", [2, 3, 4, 5]),
        ("1 + A", [2, 3, 4, 5]),
        ("abs(A - 3)", [2, 1, 0, 1]),
        ("float(A) / 2", [0.5, 1, 1.5, 2]),
        ("int(A / 2)", [0, 1, 1, 2]),
        ("A + map(single)", [1001, 1002, 1003, 1004]),
    ],
)
def test_arithmetic(series_3d, expression, expected):
    """Operators and functions are applied to every pair of equal-time maps.

    A holds 1..4 and B holds 10..40, one value per map.
    """
    assert values(series_3d.session, expression) == expected


def test_arithmetic_time_stamps(series_3d):
    """The result maps keep the time stamps of the left operand"""
    rows = result(series_3d.session, "A + B")
    assert times(rows) == daily(1, 2, 3, 4)


def test_function_square_root(series_3d):
    """sqrt() works on every map; the values are checked with a tolerance"""
    got = values(series_3d.session, "sqrt(B / 10 + 0)")
    assert got == pytest.approx([1.0, 2**0.5, 3**0.5, 2.0], rel=1e-5)


def test_result_dataset_metadata(series_3d):
    """The result is a STR3DS with the maps basename_0 .. basename_3"""
    name = run_algebra(series_3d.session, "A + B")
    rows = list_maps(series_3d.session, name)
    assert [row[4] for row in rows] == [f"{name}_{i}" for i in range(4)]
    stds = tgis.open_old_stds(name, "str3ds")
    assert stds.metadata.get_number_of_maps() == 4
    assert stds.metadata.get_min_min() == 11
    assert stds.metadata.get_max_max() == 44


def test_result_maps_hold_the_values(series_3d):
    """The 3D maps themselves hold the computed value in every cell"""
    name = run_algebra(series_3d.session, "A + B")
    tools = Tools(session=series_3d.session)
    stats = tools.r3_univar(map=f"{name}_3", format="json")
    assert (stats["n"], stats["min"], stats["max"]) == (27, 44, 44)


# Explicit relations and operators


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A {+,equal} B", [11, 22, 33, 44]),
        ("A {+,equal,l} B", [11, 22, 33, 44]),
        ("A {-,equal} B", [-9, -18, -27, -36]),
        ("A {*,equal} B", [10, 40, 90, 160]),
        ("A {/,equal} B", [0.1, 0.1, 0.1, 0.1]),
        ("A {%,equal} B", [1, 2, 3, 4]),
        ("A {+,equal,l} B {*,equal,l} A", [11, 42, 93, 164]),
    ],
)
def test_arithmetic_with_explicit_relation(series_3d, expression, expected):
    """{op,relation,temporal} gives the same values as the short form"""
    assert values(series_3d.session, expression) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        # a1 and a2 are inside w1, a3 and a4 inside w2: their sum is aggregated
        ("W {+,contains} A", [103, 207], intervals((1, 3), (3, 5))),
        (
            "A {+,during} W",
            [101, 102, 203, 204],
            intervals((1, 2), (2, 3), (3, 4), (4, 5)),
        ),
        ("A {+,starts} W", [101, 203], intervals((1, 2), (3, 4))),
        ("A {+,finishes} W", [102, 204], intervals((2, 3), (4, 5))),
        ("W {+,started} A", [101, 203], intervals((1, 3), (3, 5))),
        ("W {+,finished} A", [102, 204], intervals((1, 3), (3, 5))),
    ],
)
def test_relations_with_containment(
    series_3d, expression, expected_values, expected_times
):
    """Relations between one and two day intervals select the right pairs.

    A holds one day maps, W two day maps. a1 starts and a2 finishes w1, a3
    starts and a4 finishes w2. "during" includes starts and finishes, and
    maps related to several maps are aggregated (w1 + a1 + a2 = 103).
    """
    rows = result(series_3d.session, expression)
    assert times(rows) == expected_times
    assert [row[2] for row in rows] == expected_values


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        ("A {+,overlaps} Q", [6], intervals((1, 2))),
        ("A {+,overlapped} Q", [7], intervals((2, 3))),
        ("A {+,overlaps|overlapped} Q", [6, 7], intervals((1, 2), (2, 3))),
        ("A {+,over} Q", [6, 7], intervals((1, 2), (2, 3))),
        ("A {+,overlaps} Q2", [54], intervals((4, 5))),
    ],
)
def test_relations_with_overlap(series_3d, expression, expected_values, expected_times):
    """Overlapping intervals: Q starts at noon, so a1 overlaps q1 and q1 overlaps a2.

    a1 + q1 = 1 + 5 = 6, a2 + q1 = 2 + 5 = 7, a4 + q2 = 4 + 50 = 54.
    """
    rows = result(series_3d.session, expression)
    assert [row[2] for row in rows] == expected_values
    assert times(rows) == expected_times


@pytest.mark.parametrize(
    ("expression", "expected_value", "expected_time"),
    [
        ("A {+,precedes} tmap(single)", 1001, (day(1), day(2))),
        ("A {+,follows} tmap(single)", 1003, (day(3), day(4))),
        ("tmap(single) {+,follows} A", 1001, (day(2), day(3))),
        ("tmap(single) {+,precedes} A", 1003, (day(2), day(3))),
    ],
)
def test_relations_precedes_and_follows(
    series_3d, expression, expected_value, expected_time
):
    """precedes and follows relate maps that touch: a1 ends where single starts.

    single has the time stamp Jan 2 to Jan 3 and the value 1000.
    """
    rows = result(series_3d.session, expression)
    assert [row[:4] for row in rows] == [
        (*expected_time, expected_value, expected_value)
    ]


@pytest.mark.parametrize(
    ("temporal", "expected"),
    [
        ("l", intervals((1, 2), (2, 3), (3, 4), (4, 5))),
        ("left", intervals((1, 2), (2, 3), (3, 4), (4, 5))),
        ("r", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("right", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("i", intervals((1, 2), (2, 3), (3, 4), (4, 5))),
        ("intersect", intervals((1, 2), (2, 3), (3, 4), (4, 5))),
        ("u", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("union", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("d", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("disjoint", intervals((1, 3), (1, 3), (3, 5), (3, 5))),
    ],
)
def test_temporal_extent_operators(series_3d, temporal, expected):
    """The temporal operator sets the time stamps of A {+,during,x} W.

    Every a_i lies within one w_j, so left and intersection keep the one day
    interval of A, right and union take the two day interval of W.
    """
    rows = result(series_3d.session, f"A {{+,during,{temporal}}} W")
    assert times(rows) == expected
    assert [row[2] for row in rows] == [101, 102, 203, 204]


def test_default_extent_is_left_reference(series_3d):
    """Without a temporal operator the time stamps of the left side are used"""
    rows = result(series_3d.session, "A {+,during} W")
    assert times(rows) == intervals((1, 2), (2, 3), (3, 4), (4, 5))


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A {+} B", [11, 22, 33, 44]),
        ("A {+,equal} B {+,equal} A", [12, 24, 36, 48]),
    ],
)
def test_operator_without_relation_list(series_3d, expression, expected):
    """Braces without relation mean the equal relation"""
    assert values(series_3d.session, expression) == expected


# Selection and hash


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        ("A : B", [1, 2, 3, 4], daily(1, 2, 3, 4)),
        ("A : tmap(single)", [2], daily(2)),
        ("A {!:,starts} W", [2, 4], daily(2, 4)),
        ("A {:,during} W", [1, 2, 3, 4], daily(1, 2, 3, 4)),
        ("A {:,starts} W", [1, 3], daily(1, 3)),
        ("A {:,during,r} W", [1, 2, 3, 4], intervals((1, 3), (1, 3), (3, 5), (3, 5))),
        ("W {:,contains} A", [100, 200], intervals((1, 3), (3, 5))),
        ("A : B : tmap(single)", [2], daily(2)),
        ("A !: tmap(single)", [1, 3, 4], daily(1, 3, 4)),
    ],
)
def test_selection(series_3d, expression, expected_values, expected_times):
    """Selection keeps the maps of the left side that are related to the right"""
    rows = result(series_3d.session, expression)
    assert [row[2] for row in rows] == expected_values
    assert times(rows) == expected_times


@pytest.mark.parametrize(
    ("expression", "expected"),
    [("A {:} B", [1, 2, 3, 4]), ("A {!:} tmap(single)", [1, 3, 4])],
)
def test_selection_without_relation_list(series_3d, expression, expected):
    """{:} and {!:} are shortcuts for the equal relation"""
    rows = result(series_3d.session, expression) or []
    assert [row[2] for row in rows] == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("A {#,during} W", [1, 1, 1, 1]),
        ("W {#,contains} A", [2, 2]),
        ("W {#,contains} B", [2, 2]),
        ("A {#,equal} B", [1, 1, 1, 1]),
    ],
)
def test_hash_operator(series_3d, expression, expected):
    """The hash operator counts related maps: each w contains two maps of A"""
    assert values(series_3d.session, expression) == expected


# Conditions


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        ('if(start_date(A) > "2001-01-02", A)', [3, 4], daily(3, 4)),
        ("if(td(A) == 1, A + B)", [11, 22, 33, 44], daily(1, 2, 3, 4)),
        ("if(start_doy(A) == 2, A)", [2], daily(2)),
        ("if(start_dow(A) < 3, A)", [1, 2], daily(1, 2)),
        ("if(end_day(A) == 3, A)", [2], daily(2)),
        (
            "if(start_year(A) == 2001 && start_hour(A) == 0, A)",
            [1, 2, 3, 4],
            daily(1, 2, 3, 4),
        ),
        ('if(start_datetime(A) < "2001-01-03 00:00:00", A)', [1, 2], daily(1, 2)),
        ('if(start_time(A) == "00:00:00", A)', [1, 2, 3, 4], daily(1, 2, 3, 4)),
        ("if(start_month(A) == 2, A)", None, None),
    ],
)
def test_temporal_conditions(series_3d, expression, expected_values, expected_times):
    """Conditions on temporal functions select whole maps.

    None means that no map is selected.
    """
    rows = result(series_3d.session, expression)
    if expected_values is None:
        assert not rows
    else:
        assert [row[2] for row in rows] == expected_values
        assert times(rows) == expected_times


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("if(A > 1, A, B)", [10, 2, 3, 4]),
        ("if(A > 1 || B < 40, A)", [1, 2, 3, 4]),
        ("if(isnull(A), 1, 0)", [0, 0, 0, 0]),
        ("if(A > 1, A, B) {+,equal} B", [20, 22, 33, 44]),
    ],
)
def test_cell_conditions(series_3d, expression, expected):
    """Conditions on cell values are evaluated per cell by r3.mapcalc"""
    assert values(series_3d.session, expression) == expected


@pytest.mark.parametrize(
    ("expression", "classic", "expected"),
    [
        ("if(A > 1, A)", False, [2, 3, 4]),
        ("if(A > 1, A)", True, [0, 2, 3, 4]),
        ("if(A > 1 && B < 40, A)", False, [2, 3]),
        ("if(A > 1 && B < 40, A)", True, [0, 2, 3, 0]),
        ("if(A > 100, A)", False, []),
        ("if(A > 100, A)", True, [0, 0, 0, 0]),
        ("if(A > 1, A) + B", False, [22, 33, 44]),
        ("if(A > 1, A) + B", True, [10, 22, 33, 44]),
    ],
)
@pytest.mark.fixed_algebra
def test_cell_conditions_without_else(series_3d, expression, classic, expected):
    """if() without else gives null where the condition is false, and a map
    that is null everywhere is left out; the classic algebra gives 0 there,
    as the two-argument if() of r3.mapcalc does"""
    assert values(series_3d.session, expression, classic=classic) == expected


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        ("if({equal}, W {#,contains} A > 1, W)", [100, 200], intervals((1, 3), (3, 5))),
        ("if({equal}, W {#,contains} A > 2, W)", None, None),
        (
            "if({equal}, W {#,contains} A > 1, W {+,contains,l} A, A)",
            [103, 207],
            intervals((1, 3), (3, 5)),
        ),
        ("if({equal}, td(A) == 1, A)", [1, 2, 3, 4], daily(1, 2, 3, 4)),
        (
            "if({equal|contains}, W {#,contains} A == 2, W)",
            [100, 200],
            intervals((1, 3), (3, 5)),
        ),
    ],
)
def test_conditions_with_relation_and_hash(
    series_3d, expression, expected_values, expected_times
):
    """The hash operator and an explicit relation work inside if()

    Each W map contains two A maps, so ">2" selects nothing.
    """
    rows = result(series_3d.session, expression)
    if expected_values is None:
        assert not rows
    else:
        assert [row[2] for row in rows] == expected_values
        assert times(rows) == expected_times


def test_else_branch_for_false_condition(series_3d):
    """if(cond, then, else) returns the else maps where the condition is false.

    W {#,contains} A > 2 is false for both W maps (each contains two maps
    of A), so the result consists of the four maps of A, which lie in W.
    """
    expression = "if({equal|contains}, W {#,contains} A > 2, W {+,contains,l} A, A)"
    assert values(series_3d.session, expression) == [1, 2, 3, 4]


def test_condition_relation_reads_condition_to_conclusion(series_3d):
    """if({contains}, c(W), A): the maps of A within a map of W

    The selection A {:,during} W is the reference: it keeps the maps of A that
    lie in a map of W (checked 2026-10-11 to give all four maps of A).
    """
    assert values(series_3d.session, "A {:,during} W") == [1, 2, 3, 4]
    assert values(series_3d.session, "if({contains}, td(W) > 0, A)") == [1, 2, 3, 4]
    assert values(series_3d.session, "if({during}, td(W) > 0, A)") == []


# Neighborhood


@pytest.mark.parametrize(
    ("expression", "expected_values", "expected_times"),
    [
        ("A[-1] + A[1]", [4, 6], daily(2, 3)),
        ("A[0,0,0,-1] + A[0,0,0,1]", [4, 6], daily(2, 3)),
        ("A[1]", [2, 3, 4], daily(1, 2, 3)),
        ("A[-1]", [1, 2, 3], daily(2, 3, 4)),
        ("A[0,0,0,1] + A", [3, 5, 7], daily(1, 2, 3)),
        ("A[0,0,0,2] + A[0,0,0,-2]", None, None),
        ("A[2] - A", [2, 2], daily(1, 2)),
    ],
)
def test_temporal_neighbors(series_3d, expression, expected_values, expected_times):
    """A[t] is the t-th successor map; the first and last maps have no neighbor.

    A[-1] + A[1] exists only for the second and third map: 1 + 3 and 2 + 4.
    None means that no map has both neighbors.
    """
    rows = result(series_3d.session, expression)
    if expected_values is None:
        assert not rows
    else:
        assert [row[2] for row in rows] == expected_values
        assert times(rows) == expected_times


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # D holds the depth (1, 2, 3); the neighbor one level up is depth + 1
        ("D[0,0,1] - D", 1),
        ("D[0,0,-1] - D", -1),
        ("D[0,0,0] - D", 0),
        ("D[0,0,0,0] - D", 0),
    ],
)
def test_spatial_neighbors(series_3d, expression, expected):
    """Cell offsets work in all maps of the dataset; cells at the border are null."""
    rows = result(series_3d.session, expression)
    assert len(rows) == 3
    assert {(row[2], row[3]) for row in rows} == {(expected, expected)}


def test_combined_spatial_and_temporal_neighbor(series_3d):
    """D[x,y,z,t] combines a cell offset with a temporal offset.

    The depth is the same in all maps, so the successor one level up is 1 more
    than the depth: [0,0,1,1] - D gives 1 for the first two maps.
    """
    rows = result(series_3d.session, "D[0,0,1,1] - D")
    assert [(row[2], row[3]) for row in rows] == [(1, 1), (1, 1)]
    assert times(rows) == daily(1, 2)


# Temporal functions on datasets


def test_temporal_buffer(series_3d):
    """buff_t widens each interval by the granule on both sides"""
    rows = result(series_3d.session, 'buff_t(A, "1 day")')
    assert times(rows) == [
        ("2000-12-31 00:00:00", day(3)),
        (day(1), day(4)),
        (day(2), day(5)),
        (day(3), day(6)),
    ]
    assert [row[2] for row in rows] == [1, 2, 3, 4]


@pytest.mark.parametrize(
    ("expression", "expected_times"),
    [
        ('tshift(A, "1 day")', intervals((2, 3), (3, 4), (4, 5), (5, 6))),
        ('tshift(A, "2 days")', intervals((3, 4), (4, 5), (5, 6), (6, 7))),
        ("tsnap(A)", intervals((1, 2), (2, 3), (3, 4), (4, 5))),
    ],
)
def test_shift_and_snap(series_3d, expression, expected_times):
    """tshift moves every interval by the granule; tsnap keeps gapless intervals"""
    rows = result(series_3d.session, expression)
    assert times(rows) == expected_times
    assert [row[2] for row in rows] == [1, 2, 3, 4]


def test_shifted_dataset_in_arithmetic(series_3d):
    """tshift(A, 1 day) + A adds each map to its predecessor"""
    rows = result(series_3d.session, 'tshift(A, "1 day") + A')
    assert [row[2] for row in rows] == [3, 5, 7]
    assert times(rows) == daily(2, 3, 4)


# Flags


@pytest.mark.parametrize(
    ("expression", "expected_values"),
    [
        ("A + B", [11, 22, 33, 44]),
        ("W + A", [101, 102, 203, 204]),
        ("A[-1] + A[1]", [4, 6]),
        ("A[0,0,0,-1] + A[0,0,0,1]", [4, 6]),
        ("if(A > 1, A, B)", [10, 2, 3, 4]),
    ],
)
def test_granularity_flag(series_3d, expression, expected_values):
    """With -g the maps are sampled by the granule of the datasets (one day).

    W + A is only defined with -g: the maps of W are split into daily samples.
    """
    assert values(series_3d.session, expression, flags="g") == expected_values


def test_without_granularity_flag_unequal_intervals_give_nothing(series_3d):
    """Without -g, W + A needs equal time stamps and yields an empty dataset"""
    assert result(series_3d.session, "W + A") == []


def test_granularity_flag_time_stamps(series_3d):
    """With -g the results are daily maps"""
    rows = result(series_3d.session, "W + A", flags="g")
    assert times(rows) == daily(1, 2, 3, 4)


def test_spatial_flag_with_equal_regions(series_3d):
    """With -s datasets with the same extent are processed as without it"""
    assert values(series_3d.session, "A + B", flags="s") == [11, 22, 33, 44]


def test_spatial_flag_excludes_spatially_unrelated_maps(series_3d):
    """With -s, maps whose 3D extents are disjoint are not related"""
    assert not result(series_3d.session, "A : E", flags="s")


def test_selection_without_spatial_flag_ignores_location(series_3d):
    """Without -s only the time decides: e1 and e2 are selected for a1 and a2"""
    rows = result(series_3d.session, "A : E")
    assert [row[2] for row in rows] == [1, 2]


def test_register_null_flag(series_3d):
    """With -n completely null result maps are registered with empty statistics"""
    rows = result(series_3d.session, "if(A > 1, A, null())", flags="n")
    assert [(row[2], row[3]) for row in rows] == [(None, None), (2, 2), (3, 3), (4, 4)]


def test_null_maps_are_not_registered_without_n(series_3d):
    """Without -n a result map that is null everywhere is dropped"""
    rows = result(series_3d.session, "if(A > 1, A, null())")
    assert [(row[2], row[3]) for row in rows] == [(2, 2), (3, 3), (4, 4)]


def test_division_by_zero_gives_no_maps(series_3d):
    """A / 0 is null everywhere, so there is nothing to register"""
    assert not result(series_3d.session, "A / 0")


def test_nprocs_option(series_3d):
    """Parallel processing gives the same result as the default"""
    rows = result(series_3d.session, "A + B", nprocs=2)
    assert [row[2] for row in rows] == [11, 22, 33, 44]


@pytest.mark.fixed_algebra
def test_classic_flag_selects_the_classic_algebra(series_3d):
    """if() without else gives null in the core and 0 in the classic algebra,
    so the core leaves out the maps of value 1 and 2"""
    # The flag must win over the variable, which therefore selects the core.
    env = {**series_3d.session.env, "GRASS_TEMPORAL_ALGEBRA": "core"}
    tools = Tools(env=env, overwrite=True)
    tools.t_rast3d_algebra(expression="flag_core = if(A > 2, A)", basename="flag_core")
    tools.t_rast3d_algebra(
        expression="flag_classic = if(A > 2, A)", basename="flag_classic", flags="c"
    )
    assert [row[2] for row in list_maps(series_3d.session, "flag_core")] == [3, 4]
    assert [row[2] for row in list_maps(series_3d.session, "flag_classic")] == [
        0,
        0,
        3,
        4,
    ]


# Names, overwrite and empty results


def test_basename(series_3d):
    """Result maps are named <basename>_<n>"""
    tools = Tools(session=series_3d.session, overwrite=True)
    tools.t_rast3d_algebra(expression="named = A + B", basename="pre")
    rows = list_maps(series_3d.session, "named")
    assert [row[4] for row in rows] == [f"pre_{i}" for i in range(4)]
    existing = gs.list_strings("raster_3d", pattern="pre_*", env=series_3d.session.env)
    assert sorted(existing) == [f"pre_{i}@PERMANENT" for i in range(4)]


def test_existing_result_without_overwrite_fails(series_3d):
    """Existing result maps are not replaced without overwrite"""
    tools = Tools(session=series_3d.session, overwrite=True)
    tools.t_rast3d_algebra(expression="keep = A + B", basename="keep")
    tools = Tools(session=series_3d.session, overwrite=False)
    with pytest.raises(ToolError):
        tools.t_rast3d_algebra(expression="keep = A * B", basename="keep")
    assert list_maps(series_3d.session, "keep")[0][2] == 11


def test_overwrite_replaces_result(series_3d):
    """With overwrite the result is replaced"""
    tools = Tools(session=series_3d.session, overwrite=True)
    tools.t_rast3d_algebra(expression="rep = A + B", basename="rep")
    tools.t_rast3d_algebra(expression="rep = A * B", basename="rep")
    assert [row[2] for row in list_maps(series_3d.session, "rep")] == [10, 40, 90, 160]


def test_empty_result_gives_empty_dataset(series_3d):
    """Pairs without common time stamps give a dataset without maps.

    This pins the current behavior (M8): the tool succeeds silently.
    """
    assert result(series_3d.session, "A + Q") == []


def test_inputs_are_not_modified(series_3d):
    """Input datasets keep their maps and time stamps"""
    rows = list_maps(series_3d.session, "A")
    assert [row[:4] for row in rows] == [
        (day(n), day(n + 1), n, n) for n in (1, 2, 3, 4)
    ]
    rows = list_maps(series_3d.session, "W")
    assert times(rows) == intervals((1, 3), (3, 5))


# Errors


@pytest.mark.parametrize("expression", ["A {:,equals} B"])
def test_unknown_relation_is_an_error(series_3d, expression):
    """A misspelled relation of a selection is reported as syntax error"""
    with pytest.raises(SyntaxError):
        run_algebra(series_3d.session, expression)


@pytest.mark.parametrize("expression", ["A {+,nonsense} B", "A {+,during|nonsense} W"])
def test_unknown_relation_of_arithmetic_operator_is_an_error(series_3d, expression):
    """A misspelled relation of an arithmetic operator is reported"""
    with pytest.raises(SyntaxError):
        run_algebra(series_3d.session, expression)


@pytest.mark.parametrize(
    "expression",
    [
        "res = A +",
        "res = A + + B",
        "res = + B",
        "res = A {+,equal,x} B",
        "res = A {+,equal| precedes| follows,l B",
        "res = (A + B",
        "res = A + B)",
        "res = nosuchdataset + A",
        "res = A + single",
        "res = A[x]",
        "res = if(A > 1)",
        "res = if(start_date(A) >, A)",
        "res = buff_t(A)",
        "res = tshift(A)",
        "res = R = A + B",
        "A + B",
        "res = ",
    ],
)
def test_invalid_expressions_fail(series_3d, expression):
    """Syntax errors and unknown names are reported as exceptions"""
    parser = tgis.TemporalRaster3DAlgebraParser(run=True, debug=False)
    with pytest.raises(ALGEBRA_ERRORS):
        parser.parse(expression, "bad", True)


def test_granularity_syntax_error_fails(series_3d):
    """A syntax error is also detected in granularity mode"""
    tools = Tools(session=series_3d.session, overwrite=True)
    with pytest.raises(ToolError):
        tools.t_rast3d_algebra(
            expression="res = A {+,equal| precedes| follows,l} B +",
            basename="bad",
            flags="g",
        )


def test_basename_is_required(series_3d):
    """The tool refuses to run without basename"""
    tools = Tools(session=series_3d.session, overwrite=True)
    with pytest.raises(ToolError):
        tools.t_rast3d_algebra(expression="res = A + B")


def test_failed_run_leaves_no_result(series_3d):
    """After a syntax error no result dataset exists"""
    tools = Tools(session=series_3d.session, overwrite=True)
    with pytest.raises(ToolError):
        tools.t_rast3d_algebra(expression="failed = A +", basename="failed")
    assert list_maps(series_3d.session, "failed") is None


def test_raster_dataset_is_refused(series_3d):
    """A space time raster dataset cannot be used in the 3D algebra"""
    tools = Tools(session=series_3d.session, overwrite=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="flat = 1")
    tools.t_create(
        output="flat", type="strds", temporaltype="absolute", title="f", description="f"
    )
    tools.t_register(input="flat", maps="flat", start=day(1), end=day(2))
    with pytest.raises(ToolError):
        tools.t_rast3d_algebra(expression="res = flat + A", basename="bad")


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("implementation", ["core", "reference"])
@pytest.mark.parametrize(
    "expression",
    ["B - td(A * 2)", "B - td(A + B)"],
)
def test_duration_of_an_expression_in_arithmetic(
    series_3d, monkeypatch, implementation, expression
):
    """td() of a computed expression is the duration of its maps (one day) on
    the right of an operator, as td() of a dataset is"""
    if implementation == "core":
        monkeypatch.delenv(ALGEBRA_VARIABLE, raising=False)
        name = run_algebra(series_3d.session, expression)
    else:
        name = f"res{next(_counter)}"
        run_reference(
            "raster3d",
            f"{name} = {expression}",
            basename=name,
            overwrite=True,
            run=True,
        )
    rows = list_maps(series_3d.session, name)
    assert [row[2] for row in rows] == [9, 19, 29, 39]


def run_on(series_3d, monkeypatch, expression, implementation):
    """Return the maps of "res = <expression>" computed by the core or by the
    earlier implementation, whatever GRASS_TEMPORAL_ALGEBRA says"""
    if implementation == "core":
        monkeypatch.delenv(ALGEBRA_VARIABLE, raising=False)
        name = run_algebra(series_3d.session, expression)
    else:
        name = f"res{next(_counter)}"
        run_reference(
            "raster3d",
            f"{name} = {expression}",
            basename=name,
            overwrite=True,
            run=True,
        )
    return list_maps(series_3d.session, name)


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("implementation", ["core", "reference"])
@pytest.mark.parametrize(
    "expression",
    [
        # A and Q have no map that is equal in time.
        "tsnap(A {:,equal} Q)",
        'tshift(A {:,equal} Q, "1 day")',
        "A + tsnap(A {:,equal} Q)",
    ],
)
def test_tsnap_and_tshift_of_no_maps_give_an_empty_result(
    series_3d, monkeypatch, implementation, expression
):
    """Without maps to snap or shift the result is an empty dataset, like any
    other empty result"""
    assert run_on(series_3d, monkeypatch, expression, implementation) == []


@pytest.mark.fixed_algebra
@pytest.mark.parametrize("expression", ['tshift(A, "1 DAY")', 'tshift(A, "1 d")'])
def test_tshift_with_a_refused_increment_is_a_syntax_error(series_3d, expression):
    """An increment that the library refuses is an error, not an absent result.

    Checked on the earlier implementation only: the core raises a ValueError
    with its own message for the same expressions.
    """
    name = f"res{next(_counter)}"
    with pytest.raises(SyntaxError, match="tshift"):
        run_reference(
            "raster3d",
            f"{name} = {expression}",
            basename=name,
            overwrite=True,
            run=True,
        )
    assert list_maps(series_3d.session, name) is None
