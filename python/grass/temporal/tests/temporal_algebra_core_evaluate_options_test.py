"""Tests for the options of evaluate() that give the classic rules

The profile hands the options of plan() and materialize() on, reads the
datasets in the order of the database, refuses a second temporal type and
reports a ValueError of the core as the exception class of the classic
algebra. The datasets are series in memory, so translate.source (the read of
the temporal database) is replaced. The real read is checked by
test_the_database_order_of_equal_starts_is_that_of_the_classic_algebra
(database_order), test_a_second_temporal_type_is_a_fatal_error
(one_temporal_type) and test_an_empty_result_takes_the_temporal_type_of_the_first_dataset
in temporal_algebra_core_plan_options_io_test.py. The options of plan() themselves are tested in
temporal_algebra_core_plan_options_test.py, those that need a session in
temporal_algebra_core_plan_options_io_test.py.

The expected values come from the classic algebra. Where a value is claimed for
it, the comment says what was run: on 2026-10-16 the reference implementation
(grass.temporal.classic, run by grass.temporal.testing.reference.run_reference)
computed the expression on the datasets of
grass.temporal.testing.expressions_data with dry_run=True and the process chain
was read, and the exceptions were taken from the same runs without dry_run.
"""

import pytest

from grass.exceptions import FatalError
from grass.temporal.algebra import CORE, MapcalcStyle, Profile
from grass.temporal.algebra import parser as parser_module
from grass.temporal.algebra.parser import evaluate, translate
from grass.temporal.algebra.series import Series
from grass.temporal.algebra.time_functions import TimeFunctionError, TimeStepError

BARE = MapcalcStyle(quote_names=False, written_integers=True, bare_comparisons=True)

# evaluate() with datasets in memory

DATASETS = {}


@pytest.fixture
def datasets(monkeypatch, make_series):
    DATASETS.clear()
    DATASETS.update(
        {
            "A": make_series("a", (1, 2), (2, 3), (3, 4)),
            "B": make_series("b", (1, 3), (3, 5)),
            "E": Series(),
            "RT": make_series("rt", (0, 1), (1, 2), unit="days"),
            "RT2": make_series("ru", (10, 11), unit="days"),
            "V": make_series("v", (1, 2), (2, 3), kind="vector"),
            "W": make_series("w", (5, 6), kind="vector"),
        }
    )
    reads = []

    def read(name, **keywords):
        reads.append((name, keywords))
        return DATASETS[name.split("@")[0]]

    monkeypatch.setattr(translate, "source", read)
    monkeypatch.setattr(parser_module, "get_current_mapset", lambda: "PERMANENT")
    return reads


def dry(expression, profile=CORE, **options):
    return evaluate(
        expression, overwrite=True, dry_run=True, profile=profile, **options
    )


def test_evaluate_passes_the_style_to_plan(datasets):
    profile = Profile(mapcalc=BARE)
    chain = dry("R = A > 1", profile)
    assert chain["processes"][0]["inputs"] == [
        ("expression", "R_0=a1@PERMANENT > 1"),
        ("nprocs", 1),
    ]
    assert dry("R = A > 1")["processes"][0]["inputs"][0][1].startswith('"R_0"=(')


def test_evaluate_passes_the_list_order_to_plan(datasets):
    chain = dry("R = merge(B, A)", Profile(list_order=True))
    assert [start for _, start, _ in chain["register"]][:3] == [
        "2001-01-01 00:00:00",
        "2001-01-03 00:00:00",
        "2001-01-01 00:00:00",
    ]
    default = dry("R = merge(B, A)")
    assert [start for _, start, _ in default["register"]][:3] == [
        "2001-01-01 00:00:00",
        "2001-01-01 00:00:00",
        "2001-01-02 00:00:00",
    ]


def test_evaluate_passes_the_union_region_to_a_spatial_run(datasets):
    def params(chain):
        return dict(chain["processes"][0]["inputs"])

    profile = Profile(union_region_when_spatial=True)
    assert params(dry("R = A + 1", profile, spatial=True))["region"] == "union"
    assert "region" not in params(dry("R = A + 1", profile))
    assert "region" not in params(dry("R = A + 1", spatial=True))


def test_evaluate_passes_the_copy_numbering_to_a_selection(datasets):
    # On 2026-10-16 the classic t.select (run_reference, kind "select",
    # dry_run) gave for merge(A, tshift(A, "1 day")) on four daily maps the
    # registered maps a1..a4 followed by the copies pp_5..pp_8, numbered by
    # their position in the list; A here has three maps.
    expression = "R = merge(A, tshift(A, '1 day'))"
    profile = Profile(copies_by_position=True, list_order=True)
    chain = dry(expression, profile, selection=True)
    assert [name for name, _, _ in chain["register"]] == [
        "a1@PERMANENT",
        "a2@PERMANENT",
        "a3@PERMANENT",
        "R_4",
        "R_5",
        "R_6",
    ]
    default = dry(expression, selection=True)
    assert [call["inputs"][0][1][1] for call in default["processes"]] == [
        "R_1",
        "R_2",
        "R_3",
    ]


def test_evaluate_reads_the_datasets_sorted_by_start_only_if_asked(datasets):
    dry("R = A + 1")
    assert datasets[-1][1].get("order") is None
    dry("R = A + 1", Profile(database_order=True))
    assert datasets[-1][1]["order"] == "start"
    dry("R = A + 1", Profile(database_order=False))
    assert datasets[-1][1].get("order") is None


def test_a_temporal_type_per_expression_is_not_demanded_by_default(datasets):
    with pytest.raises(ValueError, match="different temporal types"):
        dry("R = merge(A, RT)")


def test_a_second_temporal_type_is_refused_if_asked(datasets):
    profile = Profile(one_temporal_type=True)
    with pytest.raises(
        FatalError,
        match=(
            r"^Wrong temporal type of space time dataset <RT@PERMANENT> "
            r"<absolute> time is required$"
        ),
    ):
        dry("R = merge(A, RT)", profile)
    with pytest.raises(FatalError, match=r"<A@PERMANENT> <relative>"):
        dry("R = merge(RT, A@PERMANENT)", profile)


def test_datasets_without_maps_have_no_temporal_type(datasets):
    profile = Profile(one_temporal_type=True)
    chain = dry("R = merge(E, A)", profile)
    assert len(chain["register"]) == 3
    chain = dry("R = merge(RT, E)", profile)
    assert chain["STDS"]["temporal_type"] == "relative"


def test_an_empty_result_takes_the_type_of_the_first_dataset_if_asked(datasets):
    expression = "R = RT {:, during} RT2"
    assert dry(expression)["STDS"]["temporal_type"] == "absolute"
    chain = dry(expression, Profile(empty_result_type_from_input=True))
    assert chain["register"] == []
    assert chain["STDS"]["temporal_type"] == "relative"


def test_a_dataset_without_maps_gives_no_type_to_an_empty_result(datasets):
    profile = Profile(empty_result_type_from_input=True)
    chain = dry("R = E {:, during} RT", profile)
    assert chain["register"] == []
    assert chain["STDS"]["temporal_type"] == "relative"


def test_a_vector_result_without_maps_has_a_dataset_by_default(datasets):
    chain = dry("R = V {&, contains} W", kind="vector")
    assert chain["register"] == []
    assert chain["STDS"]["stdstype"] == "stvds"


def test_a_vector_result_without_maps_can_have_no_dataset(datasets):
    profile = Profile(vector_dataset_if_empty=False)
    chain = dry("R = V {&, contains} W", profile, kind="vector")
    assert chain["register"] == []
    assert chain["STDS"] == {}
    chain = dry("R = V & V", profile, kind="vector")
    assert chain["STDS"]["name"] == "R"


def test_other_empty_results_keep_their_dataset(datasets):
    profile = Profile(vector_dataset_if_empty=False)
    chain = dry("R = RT {:, during} RT2", profile)
    assert chain["register"] == []
    assert chain["STDS"]["name"] == "R"


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("R = tshift(A, 5)", "Absolute time needs a time unit"),
        ("R = buff_t(A, 5)", "Absolute time needs a time unit"),
        ("R = tshift(RT, '1 month')", "Relative time is changed by a number"),
        ("R = buff_t(RT, '1 day')", "Relative time is changed by a number"),
    ],
)
def test_a_refused_increment_is_a_syntax_error_of_the_classic_algebra(
    datasets, expression, message
):
    # The classic algebra raises SyntaxError for each of these (run on
    # 2026-10-16 with run_reference on the datasets A and RT), the core a
    # ValueError.
    with pytest.raises(ValueError, match=message):
        dry(expression)
    with pytest.raises(SyntaxError, match=message):
        dry(expression, Profile(classic_errors=True))


@pytest.mark.parametrize(
    "expression",
    [
        "R = if(start_month(RT) == 1, RT)",
        "R = A + start_month(RT, 1)",
    ],
)
def test_a_missing_time_function_is_a_fatal_error_of_the_classic_algebra(
    datasets, expression
):
    # The classic algebra raises FatalError "... requires absolute time ..."
    # for the condition and the neighbour form alike (2026-10-16, run_reference).
    with pytest.raises(ValueError, match="Temporal function start_month"):
        dry(expression)
    with pytest.raises(FatalError, match=r"start_month\(\) is not available for map"):
        dry(expression, Profile(classic_errors=True))


def test_the_fatal_error_names_the_map_and_the_requirement(datasets):
    with pytest.raises(
        FatalError,
        match=(
            r"^Temporal function start_month\(\) is not available for map "
            r"<rt1@PERMANENT>\. It requires absolute time, end time functions "
            r"also an end time\.$"
        ),
    ):
        dry("R = if(start_month(RT) == 1, RT)", Profile(classic_errors=True))


def test_other_value_errors_stay_value_errors(datasets):
    with pytest.raises(ValueError, match="different temporal types"):
        dry("R = merge(A, RT)", Profile(classic_errors=True))


def test_the_mapping_goes_by_class_not_by_wording():
    from grass.temporal.algebra.parser import _classic_error

    text = "Cannot read '1 fortnight' as a time step, use e.g. \"1 day\""
    assert _classic_error(ValueError(text)) is None
    assert isinstance(_classic_error(TimeStepError(text)), SyntaxError)
    mapped = _classic_error(TimeFunctionError("any words", "end_doy", "a1@PERMANENT"))
    assert isinstance(mapped, FatalError)
    assert "end_doy() is not available for map <a1@PERMANENT>" in str(mapped)
