# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""Run the examples of the reviewed temporal manuals and compare them

A manual is listed in REVIEWED_MANUALS once its examples follow the layout of
grass.temporal.testing.manual_examples. The others still use data that the
tests do not have and stay unchecked until their turn.
"""

from pathlib import Path

import pytest

from grass.temporal.testing.manual_coverage import (
    NOT_SHOWN,
    check_html_sync,
    shown_options,
    tool_options,
)
from grass.temporal.testing.manual_examples import check_manual, parse_manual
from grass.temporal.testing.session import project_session

REVIEWED_MANUALS = (
    "t.connect",
    "t.copy",
    "t.create",
    "t.info",
    "t.list",
    "t.merge",
    "t.rast.aggregate",
    "t.rast.aggregate.ds",
    "t.rast.contour",
    "t.rast.list",
    "t.rast.univar",
    "t.register",
    "t.remove",
    "t.rename",
    "t.sample",
    "t.shift",
    "t.snap",
    "t.support",
    "t.topology",
    "t.unregister",
    "t.upgrade",
)

TOOLS = Path(__file__).parents[1]


def manual_of(tool):
    return parse_manual(TOOLS / tool / f"{tool}.md")


@pytest.mark.parametrize("variant", ["shell", "python"])
@pytest.mark.parametrize("tool", REVIEWED_MANUALS)
def test_examples_run_and_show_their_output(tool, variant, tmp_path):
    manual = manual_of(tool)
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
