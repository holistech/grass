# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Run the examples of the reviewed temporal manuals and compare them

A manual is listed in REVIEWED_MANUALS once its examples follow the layout of
grass.temporal.testing.manual_examples. The others still use data that the
tests do not have and stay unchecked until their turn.

CATALOG_MANUALS are the manuals that may keep a catalog of expressions, each
with its result, in examples without a Python tab (``<!-- example:
shell-only -->``). Each tab of a manual runs in one test, whose time limit
grows with its number of blocks (manual_examples.timeout_for).

A manual with ``dataset=`` in its example-project comment runs in the North
Carolina sample dataset (grass.temporal.testing.nc_dataset), which the tests
need: without it, they fail with a message that says where to get it.
"""

import dataclasses
from functools import partial
from pathlib import Path

import pytest

from grass.temporal.testing.manual_coverage import (
    NOT_SHOWN,
    check_html_sync,
    shown_options,
    tool_options,
)
from grass.temporal.testing.manual_examples import (
    MINIMUM_TEST_SECONDS,
    ManualFormatError,
    check_manual,
    example_session,
    parse_manual,
    stop_example_processes,
    timeout_for,
)
from grass.temporal.testing.nc_dataset import (
    USED_DATA,
    differences,
    find_dataset,
    fingerprint,
    snapshot,
)

# The manuals rewritten so far; each tool stage that rewrites manuals replaces
# this file with a longer list, the last one with the final version.
REVIEWED_MANUALS = (
    "t.rast.aggregate",
    "t.rast.aggregate.ds",
    "t.rast.mapcalc",
    "t.rast.univar",
    "t.rast3d.mapcalc",
    "t.rast3d.univar",
    "t.sample",
)

# Blocks whose shown output comes from a tool not yet revised, by manual and
# example, found by a text of their code. The example "Choose the sampling
# method" of t.rast.mapcalc prints map names with t.rast.list method=comma,
# which gives one line only from the revision of t.rast.list on. These blocks
# run, but their output is not compared; a second run compares everything and
# is expected to fail, strictly, so that the revision of t.rast.list has to
# remove the entry.
EXAMPLES_LATER = {"t.rast.mapcalc": {"Choose the sampling method": "comma"}}

# The algebras list their expressions with the result of each; their manuals
# join with the tool stages that rewrite them.
CATALOG_MANUALS = ()

TOOLS = Path(__file__).parents[1]


def manual_of(tool):
    return parse_manual(TOOLS / tool / f"{tool}.md")


def time_limit(read_manual, variant):
    """The time limit of the blocks of one tab as a mark, none for a manual
    that cannot be read

    The test of the manual reports the error; until then, the limit of the
    repository applies. Reading the manual while the tests are collected must
    not fail, or one broken manual would stop the whole file.
    """
    try:
        manual = read_manual()
    except ManualFormatError:
        return ()
    return pytest.mark.timeout(timeout_for(manual, variant))


def example_runs():
    """Each reviewed manual and tab, with the time limit of its blocks"""
    for tool in REVIEWED_MANUALS:
        later = EXAMPLES_LATER.get(tool, {})
        for variant in ("shell", "python"):
            marks = time_limit(partial(manual_of, tool), variant)
            yield pytest.param(
                tool, variant, later, marks=marks, id=f"{tool}-{variant}"
            )
            if later:
                expected = pytest.mark.xfail(
                    strict=True, reason=f"examples {set(later)} show a later revision"
                )
                yield pytest.param(
                    tool,
                    variant,
                    {},
                    marks=(*([marks] if marks else []), expected),
                    id=f"{tool}-{variant}-whole",
                )


@pytest.fixture
def example_processes():
    """Stop the processes of the examples that a test leaves behind

    pytest-timeout ends a test by an exception in the middle of a block; the
    tool that the block started would go on running without this teardown.
    """
    yield
    stop_example_processes()


@pytest.fixture(scope="session")
def dataset_at_start():
    """The North Carolina dataset and its snapshot, checked for the recorded data

    Taken when the first test of this process that needs the dataset asks for
    it, before that test runs examples. A dataset with other data fails here,
    so that its manuals do not show a wall of differing output.
    """
    dataset = find_dataset()
    assert differences(USED_DATA, fingerprint(dataset)) == [], (
        f"{dataset} has other data than the manuals were written with"
    )
    return dataset, snapshot(dataset)


@pytest.mark.parametrize(("tool", "variant", "later"), example_runs())
def test_examples_run_and_show_their_output(
    tool, variant, later, tmp_path, example_processes, request
):
    manual = manual_of(tool)
    if later:
        manual = without_later_output(manual, variant, later)
    check_examples(manual, variant, tmp_path, request)


def without_later_output(manual, variant, later):
    """The manual with the shown output of the blocks named in later removed"""
    examples = []
    unchecked = set()
    for example in manual.examples:
        text = later.get(example.title)
        blocks = []
        for block in example.blocks:
            if text is not None and text in block.code and block.shown_output:
                block = dataclasses.replace(block, shown_output=None)
                if example.variant == variant:
                    unchecked.add(example.title)
            blocks.append(block)
        examples.append(dataclasses.replace(example, blocks=tuple(blocks)))
    assert unchecked == set(later), f"{manual.path}: no such blocks in {later}"
    return dataclasses.replace(manual, examples=tuple(examples))


def test_examples_leave_the_dataset_unchanged(dataset_at_start):
    """Nothing changed the dataset since this process first needed it

    Each run of a manual in the dataset compares the dataset before and after
    and names the manual that changed it (example_session). This test also
    sees a change by anything else that ran in this process before it, and it
    fails, with one message, when the dataset is missing (pytest reports it as
    an error, because the fixture dataset_at_start raises).
    """
    dataset, before = dataset_at_start
    assert differences(before, snapshot(dataset)) == [], (
        f"the dataset {dataset} changed during the tests"
    )


def check_examples(manual, variant, tmp_path, request):
    """Run the examples of one tab of a manual and compare their output"""
    # A misspelled "## EXAMPLES" leaves a manual without examples, which
    # would otherwise pass unseen.
    assert any(example.variant == variant for example in manual.examples), (
        f"{manual.path} has no examples under ## EXAMPLES"
    )
    if "dataset" in manual.project:
        request.getfixturevalue("dataset_at_start")
    # The examples run in child processes and need only session.env, so this
    # process does not init grass.temporal, and example_session does not
    # either. With temporal_session, pytest -n auto temporal/tests reported 12
    # DeprecationWarnings of multiprocessing (fork of a multi-threaded
    # process), with project_session none (measured 2026-11-02).
    with example_session(manual, tmp_path) as session:
        check_manual(manual, variant, session, tmp_path / "work")


@pytest.mark.parametrize("tool", REVIEWED_MANUALS)
def test_every_option_is_shown(tool, xy_module_session):
    manual = manual_of(tool)
    options = tool_options(tool, xy_module_session.env)
    shown = shown_options(manual)
    exempt = {option for name, option in NOT_SHOWN if name == tool}
    missing = options - shown - exempt
    assert not missing, f"{manual.path} shows no example with {sorted(missing)}"
    stale = exempt - (options - shown)
    assert not stale, f"NOT_SHOWN lists shown or unknown options: {sorted(stale)}"


@pytest.mark.parametrize("tool", REVIEWED_MANUALS)
def test_markdown_and_html_agree(tool):
    manual = manual_of(tool)
    assert check_html_sync(manual, manual.path.with_suffix(".html")) == []


def test_minimum_time_limit_is_the_limit_of_the_repository(pytestconfig):
    """A manual gets at least the time limit that every test of the
    repository gets; the two are set in different places"""
    assert int(pytestconfig.getini("timeout")) == MINIMUM_TEST_SECONDS


def test_shell_only_examples_are_catalog_manuals():
    manuals = {tool: manual_of(tool) for tool in REVIEWED_MANUALS}
    users = {
        name
        for name, manual in manuals.items()
        if any(example.shell_only for example in manual.examples)
    }
    assert users <= set(CATALOG_MANUALS), (
        f"examples without a Python tab outside a catalog: {sorted(users)}"
    )
