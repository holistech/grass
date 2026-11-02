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
"""

from pathlib import Path

import pytest

from grass.temporal.testing.manual_coverage import (
    NOT_SHOWN,
    check_html_sync,
    shown_options,
    tool_options,
)
from grass.temporal.testing.manual_examples import (
    ManualFormatError,
    check_manual,
    parse_manual,
    stop_example_processes,
    timeout_for,
)
from grass.temporal.testing.session import project_session

REVIEWED_MANUALS = (
    "t.connect",
    "t.copy",
    "t.create",
    "t.info",
    "t.list",
    "t.merge",
    "t.rast.accdetect",
    "t.rast.accumulate",
    "t.rast.aggregate",
    "t.rast.aggregate.ds",
    "t.rast.colors",
    "t.rast.contour",
    "t.rast.export",
    "t.rast.extract",
    "t.rast.gapfill",
    "t.rast.import",
    "t.rast.list",
    "t.rast.mapcalc",
    "t.rast.neighbors",
    "t.rast.out.vtk",
    "t.rast.series",
    "t.rast.to.rast3",
    "t.rast.to.vect",
    "t.rast.univar",
    "t.rast.what",
    "t.rast3d.algebra",
    "t.rast3d.extract",
    "t.rast3d.list",
    "t.rast3d.mapcalc",
    "t.rast3d.univar",
    "t.register",
    "t.remove",
    "t.rename",
    "t.sample",
    "t.select",
    "t.shift",
    "t.snap",
    "t.support",
    "t.topology",
    "t.unregister",
    "t.upgrade",
    "t.vect.algebra",
    "t.vect.db.select",
    "t.vect.export",
    "t.vect.extract",
    "t.vect.import",
    "t.vect.list",
    "t.vect.observe.strds",
    "t.vect.univar",
    "t.vect.what.strds",
)

# The algebras, whose manuals list their expressions with the result of each.
CATALOG_MANUALS = (
    "t.rast.algebra",
    "t.rast3d.algebra",
    "t.select",
    "t.vect.algebra",
)

TOOLS = Path(__file__).parents[1]
# The introduction is checked like a manual, but it describes no tool, so
# it has no options to show.
INTRODUCTION = TOOLS / "temporalintro.md"


def manual_of(tool):
    return parse_manual(TOOLS / tool / f"{tool}.md")


def example_runs():
    """Each reviewed manual and tab, with the time limit of its blocks"""
    for tool in REVIEWED_MANUALS:
        try:
            manual = manual_of(tool)
        except ManualFormatError:
            # The test of the manual reports the error; until then, the limit
            # of the repository applies.
            manual = None
        for variant in ("shell", "python"):
            marks = (
                ()
                if manual is None
                else pytest.mark.timeout(timeout_for(manual, variant))
            )
            yield pytest.param(tool, variant, marks=marks, id=f"{tool}-{variant}")


@pytest.fixture
def example_processes():
    """Stop the processes of the examples that a test leaves behind

    pytest-timeout ends a test by an exception in the middle of a block; the
    tool that the block started would go on running without this teardown.
    """
    yield
    stop_example_processes()


@pytest.mark.parametrize(("tool", "variant"), example_runs())
def test_examples_run_and_show_their_output(tool, variant, tmp_path, example_processes):
    check_examples(manual_of(tool), variant, tmp_path)


def check_examples(manual, variant, tmp_path):
    """Run the examples of one tab of a manual and compare their output"""
    # A misspelled "## EXAMPLES" leaves a manual without examples, which
    # would otherwise pass unseen.
    assert any(example.variant == variant for example in manual.examples), (
        f"{manual.path} has no examples under ## EXAMPLES"
    )
    project = tmp_path / "grassdata" / "temporal_examples"
    # The examples run in child processes and need only session.env, so this
    # process does not init grass.temporal. With temporal_session, pytest -n
    # auto temporal/tests reported 12 DeprecationWarnings of multiprocessing
    # (fork of a multi-threaded process), with project_session none (measured
    # 2026-11-02).
    with project_session(project, crs=manual.project.get("crs")) as session:
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


@pytest.mark.parametrize(
    "variant",
    [
        pytest.param(
            variant,
            marks=pytest.mark.timeout(timeout_for(parse_manual(INTRODUCTION), variant)),
            id=variant,
        )
        for variant in ("shell", "python")
    ],
)
def test_introduction_examples_run_and_show_their_output(
    variant, tmp_path, example_processes
):
    check_examples(parse_manual(INTRODUCTION), variant, tmp_path)


def test_introduction_markdown_and_html_agree():
    manual = parse_manual(INTRODUCTION)
    assert check_html_sync(manual, INTRODUCTION.with_suffix(".html")) == []


def test_shell_only_examples_are_catalog_manuals():
    users = {
        tool
        for tool in REVIEWED_MANUALS
        if any(example.shell_only for example in manual_of(tool).examples)
    }
    assert users <= set(CATALOG_MANUALS), (
        f"examples without a Python tab outside a catalog: {sorted(users)}"
    )
