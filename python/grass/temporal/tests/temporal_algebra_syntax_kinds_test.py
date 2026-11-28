"""Translation of the algebra syntax for 3D raster and vector maps

The datasets are built in memory; the expected series are those of the
core calls named in the translation table of the algebra.
"""

import pytest

from grass.temporal.algebra import operations
from grass.temporal.algebra.content import Call, Const, MapRef
from grass.temporal.algebra.parser.grammar import parse
from grass.temporal.algebra.parser.translate import Translator
from grass.temporal.algebra.relations import equal
from grass.temporal.algebra.series import Space

BOX = Space(north=10, south=0, east=10, west=0)
SHIFTED = Space(north=15, south=5, east=15, west=5)


@pytest.fixture
def translate(make_series):
    def run(text, kind="vector", spatial=False):
        datasets = {
            "A": make_series("a", (1, 2), (2, 3), space=BOX, kind=kind),
            "B": make_series("b", (1, 2), (2, 3), space=SHIFTED, kind=kind),
            "C": make_series("c", (1, 2), (2, 3), space=BOX, kind=kind),
            "W": make_series("w", (1, 4), space=BOX, kind=kind),
        }
        translator = Translator(
            kind=kind, spatial=spatial, resolve=datasets.__getitem__
        )
        return translator.statement(parse(f"R = {text}"))[1]

    return run


def contents(series):
    return [slot.content for slot in series]


def test_and_is_an_overlay_within_the_intersection(translate):
    result = translate("A & B")
    assert contents(result)[0] == Call(
        "and", (MapRef("a1@PERMANENT"), MapRef("b1@PERMANENT"))
    )
    assert result.slots[0].space == Space(10, 5, 10, 5)


@pytest.mark.parametrize(
    ("text", "function"),
    [("A | B", "or"), ("A ^ B", "xor"), ("A ~ B", "not"), ("A + B", "disor")],
)
def test_other_overlays_lie_within_the_union(translate, text, function):
    result = translate(text)
    assert contents(result)[0].function == function
    assert result.slots[0].space == Space(15, 0, 15, 0)


def test_overlays_fold_from_left_to_right(translate):
    a1, b1, c1 = (MapRef(f"{name}1@PERMANENT") for name in "abc")
    assert contents(translate("A & B | C"))[0] == Call(
        "or", (Call("and", (a1, b1)), c1)
    )


def test_overlay_with_relation_and_right_reference(translate, make_series):
    result = translate("A {|,equal,r} B")
    expected = operations.pairs(
        make_series("a", (1, 2), (2, 3), space=BOX, kind="vector"),
        equal,
        make_series("b", (1, 2), (2, 3), space=SHIFTED, kind="vector"),
        extent="right",
        space="union",
        content=lambda mine, theirs: Call("or", (mine, theirs)),
    )
    assert result.slots == expected.slots


def test_buffer_functions(translate):
    result = translate("buff_l(A, 2)")
    assert contents(result)[0] == Call("buff_l", (MapRef("a1@PERMANENT"), Const(2.0)))
    assert result.slots[0].space == Space(12, -2, 12, -2, top=2, bottom=-2)


def test_temporal_conditions_on_vector_maps(translate):
    result = translate("if(start_day(A) == 2, A)")
    assert [slot.origin for slot in result] == ["a2@PERMANENT"]


def test_temporal_neighbour_of_vector_maps(translate):
    result = translate("A[-1]")
    assert contents(result) == [MapRef("a1@PERMANENT")]
    assert result.slots[0].extent == translate("A").slots[1].extent
    # The map a1 with the time stamp of a2 is a new map, not the registered
    # a1, so the slot has no origin.
    assert result.slots[0].origin is None


def test_3d_cell_offsets(translate):
    result = translate("A[1,0,-1]", kind="raster3d")
    assert contents(result)[0] == MapRef("a1@PERMANENT", (1, 0, -1))
    shifted = translate("A[1,0,-1,1]", kind="raster3d")
    assert len(shifted) == 1


@pytest.mark.parametrize(
    ("text", "kind", "message"),
    [
        ("A & B", "raster", "vector"),
        ("A ~ B", "raster3d", "vector"),
        ("A - B", "vector", "vector"),
        ("A * 2", "vector", "vector"),
        ("A > 1", "vector", "vector"),
        ("sin(A)", "vector", "vector"),
        ("A && B", "vector", "vector"),
        ("if(A, B)", "vector", "temporal"),
        ("buff_a(A, 1)", "raster", "vector"),
        ("buff_a(A, B)", "vector", "distance"),
        ("A[1,0]", "vector", "offset"),
        ("A[1,0]", "raster3d", "offset"),
        ("A[1,0,0,0,0]", "raster3d", "offset"),
    ],
)
def test_operators_that_a_map_type_does_not_have(translate, text, kind, message):
    with pytest.raises(SyntaxError, match=message):
        translate(text, kind=kind)


@pytest.mark.parametrize(
    "text",
    [
        "A {#,equal} B",
        # No map of A lies within a map of B, so that the count has no slot;
        # the error must not depend on whether the relation finds a pair.
        "A {#,during} B",
        "A {#,during} W",
        "td(A)",
        "start_day(A) + 1",
    ],
)
def test_a_vector_expression_of_numbers_is_rejected(translate, text):
    with pytest.raises(SyntaxError, match="gives numbers, not vector maps"):
        translate(text)


@pytest.mark.parametrize(
    "text",
    [
        "if(td(A) > 0, 1)",
        "if(td(A) > 0, A, 1)",
        "if(td(A) > 0, A, null())",
        "if(td(A) > 0, A, td(A))",
        "if(td(A) > 0, td(A))",
    ],
)
def test_a_vector_if_chooses_between_vector_maps(translate, text):
    with pytest.raises(SyntaxError, match="chooses between vector maps"):
        translate(text)


def test_plus_stays_arithmetic_for_raster_maps(translate):
    result = translate("A + B", kind="raster")
    assert contents(result)[0] == Call(
        "+", (MapRef("a1@PERMANENT"), MapRef("b1@PERMANENT"))
    )
