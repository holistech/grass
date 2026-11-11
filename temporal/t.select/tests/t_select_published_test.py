"""The selection of the paper that mixes dataset types

Gebbert, Leppelt and Pebesma (2019) select the maps of a 3D raster time
series that are during the maps of a vector time series. The paper prints the
function names in capitals, STR3DS(A) and STVDS(B); the algebra reads the
functions. Capitals are accepted for these three names, and only before an
opening parenthesis. The datasets are those of conftest.py: A of type str3ds
and B of type stvds, whose maps stand in the relations listed there.
"""

import pytest

import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.temporal.algebra.parser import evaluate
from grass.tools import Tools

PRINTED = "STR3DS(A) {:,during,l} STVDS(B)"
LOWER_CASE = "str3ds(A) {:,during,l} stvds(B)"

# By hand from the table in conftest.py: during includes starts and finishes,
# so a1 (starts b8) and a2 (finishes b8) are selected, unchanged and with
# their values 1 and 2; a3 contains b2 and b9 and a4 contains b5, they are
# not during any map. The same maps were recorded from the reference
# implementation on 2026-11-11.
SELECTED = [
    ("a1", "2001-01-01 00:00:00", "2001-01-11 00:00:00", 1),
    ("a2", "2001-01-11 00:00:00", "2001-01-21 00:00:00", 2),
]


def select(expression, basename):
    """Select R = expression into a str3ds on the algebra core

    Calls the core as t.select does without -c, with -n. Returns the maps of
    R as (name, start, end, value); every map of the data is constant, so its
    minimum is its value.
    """
    result = tgis.SpaceTimeRaster3DDataset("R@PERMANENT")
    if result.is_in_db():
        result.delete()
    evaluate(
        f"R = {expression}",
        kind="raster3d",
        basename=basename,
        overwrite=True,
        selection=True,
        register_null=True,
    )
    rows = []
    dataset = tgis.open_old_stds("R", "str3ds")
    for item in dataset.get_registered_maps_as_objects(order="start_time") or []:
        item.select()
        start, end = item.get_temporal_extent_as_tuple()
        low, high = item.metadata.get_min(), item.metadata.get_max()
        assert low == high, item.get_id()
        rows.append((item.get_name(), str(start), str(end), low))
    return rows


def test_the_lower_case_selection_gives_a1_and_a2(series):
    """The selection of the paper in lower case gives a1 and a2"""
    assert select(LOWER_CASE, "fa") == SELECTED


def test_the_function_names_in_capitals_select_like_lower_case(series):
    """The printed form selects the same maps as the lower case"""
    assert select(PRINTED, "fa") == SELECTED


@pytest.mark.parametrize(
    "expression",
    [
        "Str3ds(A) {:,during,l} stvds(B)",
        "STR3ds(A) {:,during,l} stvds(B)",
        "str3ds(A) {:,during,l} STVDs(B)",
    ],
)
def test_other_capital_spellings_are_refused(series, expression):
    with pytest.raises(SyntaxError):
        select(expression, "fa")


def test_a_dataset_named_like_a_capital_function_stays_a_name(series):
    """Without a parenthesis after it, STVDS is a dataset name

    No dataset of that name exists here, so the selection stops where the
    dataset is looked up. The core reads the lower case stvds in the same
    place as a dataset name as well (checked 2026-11-11); the reference
    implementation refused it as a syntax error.
    """
    with pytest.raises(FatalError, match="<STVDS@PERMANENT> not found"):
        select("A {:,during,l} STVDS", "fa")
    with pytest.raises(FatalError, match="<stvds@PERMANENT> not found"):
        select("A {:,during,l} stvds", "fb")


def test_the_tool_selects_with_the_classic_flag(series):
    """-c takes precedence over the variable of the fixture algebra"""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds", flags="c")
    listing = tools.t_rast3d_list(input="published", columns="name", format="json")
    assert listing["data"]


def test_the_tool_selects_with_the_functions_in_both_algebras(series, algebra):
    """Observed 2026-10-17: the core read no dataset type function before;
    both algebras select the maps a1 and a2 now"""
    tools = Tools(session=series.session, overwrite=True)
    tools.t_select(expression=f"published = {LOWER_CASE}", type="str3ds")
    listing = tools.t_rast3d_list(input="published", columns="name", format="json")
    assert len(listing["data"]) == 2
