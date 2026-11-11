"""Tests for evaluate(): its options and the errors of the core

The datasets are series in memory, so translate.source (the read of the
temporal database) is replaced. The options of plan() themselves are tested in
temporal_algebra_core_plan_options_test.py, those that need a session in
temporal_algebra_core_plan_options_io_test.py.
"""

import pytest

from grass.temporal.algebra.parser import evaluate, translate
from grass.temporal.algebra.series import Series

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
    return reads


def dry(expression, **options):
    return evaluate(expression, overwrite=True, dry_run=True, **options)


def test_a_spatial_run_without_spatial_relation_has_no_region(datasets):
    chain = dry("R = A + 1", spatial=True)
    assert "region" not in dict(chain["processes"][0]["inputs"])


def test_datasets_of_two_temporal_types_are_not_merged(datasets):
    with pytest.raises(ValueError, match="different temporal types"):
        dry("R = merge(A, RT)")


def test_datasets_without_maps_have_no_temporal_type(datasets):
    chain = dry("R = merge(E, A)")
    assert len(chain["register"]) == 3
    chain = dry("R = merge(RT, E)")
    assert chain["STDS"]["temporal_type"] == "relative"


def test_an_empty_result_has_absolute_time(datasets):
    chain = dry("R = RT {:, during} RT2")
    assert chain["register"] == []
    assert chain["STDS"]["temporal_type"] == "absolute"


def test_a_vector_result_without_maps_has_a_dataset_by_default(datasets):
    chain = dry("R = V {&, contains} W", kind="vector")
    assert chain["register"] == []
    assert chain["STDS"]["stdstype"] == "stvds"


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        ("R = tshift(A, 5)", "Absolute time needs a time unit"),
        ("R = buff_t(A, 5)", "Absolute time needs a time unit"),
        ("R = tshift(RT, '1 month')", "Relative time is changed by a number"),
        ("R = buff_t(RT, '1 day')", "Relative time is changed by a number"),
    ],
)
def test_a_refused_increment_is_a_value_error(datasets, expression, message):
    with pytest.raises(ValueError, match=message):
        dry(expression)


@pytest.mark.parametrize(
    "expression",
    [
        "R = if(start_month(RT) == 1, RT)",
        "R = A + start_month(RT, 1)",
    ],
)
def test_a_missing_time_function_is_a_value_error(datasets, expression):
    with pytest.raises(ValueError, match="Temporal function start_month"):
        dry(expression)
