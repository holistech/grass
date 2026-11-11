"""Tests that the core gives the process chains recorded before its rework

The datasets are series in memory, so that no temporal database is read.
"""

import json
import pathlib

import pytest

from grass.temporal.algebra.parser import evaluate, translate

GOLDEN = pathlib.Path(__file__).with_name("temporal_algebra_golden_chains.json")

EXPRESSIONS = (
    "R = A",
    "R = A + B",
    "R = A * 2",
    "R = A {+, during} B",
    "R = A {+, equal, u} B",
    "R = B {:, contains} A",
    "R = A : B",
    "R = B !: A",
    "R = A # B",
    "R = if(A > 1, A, C)",
    "R = if({equal}, start_day(A) > 1, C)",
    "R = if(start_doy(A) == 1, A)",
    "R = A[1] - A",
    "R = sin(A) + abs(B)",
    "R = merge(A, B)",
    "R = tshift(A, '1 day')",
    "R = tsnap(A)",
    "R = buff_t(A, '1 day')",
    "R = A - td(A)",
    "R = null() + A",
)


@pytest.fixture
def in_memory_datasets(monkeypatch, make_series):
    datasets = {
        "A": make_series("a", (1, 2), (2, 3), (3, 4)),
        "B": make_series("b", (1, 2), (2, 3), (3, 4), (1, 4)),
        "C": make_series("c", (1, 2), (2, 3), (3, 4)),
    }
    monkeypatch.setattr(translate, "source", lambda name, **_: datasets[name])
    return datasets


def chain(expression):
    return evaluate(expression, overwrite=True, dry_run=True)


def as_json(chain_):
    return json.loads(json.dumps(chain_, default=list))


@pytest.mark.parametrize("expression", EXPRESSIONS)
def test_the_core_gives_the_chain_of_the_code_before_profiles(
    in_memory_datasets, expression
):
    """The chains in the JSON file were produced on 2026-10-16 by the code of
    commit 07b3e76f9b (before profiles), checked out in a temporary git
    worktree: the algebra package of that commit over a copy of the installed
    tree, run on the same in-memory datasets with evaluate(overwrite=True,
    dry_run=True) and dumped as JSON.
    """
    golden = json.loads(GOLDEN.read_text())[expression]
    assert golden["register"]
    assert as_json(chain(expression)) == golden
