"""Tests for the session helpers of grass.temporal.testing.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

import os

import pytest

import grass.script as gs
import grass.temporal as tgis
from grass.exceptions import FatalError
from grass.pygrass.messages import get_msgr
from grass.temporal.testing.session import (
    add_mapset,
    project_session,
    temporal_session,
)

pytestmark = pytest.mark.real_io


def test_project_session_leaves_os_environ_alone(tmp_path):
    before = dict(os.environ)
    with project_session(tmp_path / "p") as session:
        assert session.env["GISRC"]
        assert dict(os.environ) == before
    assert dict(os.environ) == before


def test_temporal_session_mirrors_and_restores_os_environ(tmp_path):
    before = dict(os.environ)
    with temporal_session(tmp_path / "p") as session:
        assert os.environ["GISRC"] == session.env["GISRC"]
    assert dict(os.environ) == before


def test_temporal_session_restores_os_environ_after_exception(tmp_path):
    before = dict(os.environ)
    with pytest.raises(ZeroDivisionError), temporal_session(tmp_path / "p"):
        raise ZeroDivisionError
    assert dict(os.environ) == before


def test_temporal_session_raises_and_restores_module_flag(tmp_path):
    # A known value, so that the restore is not compared with the value
    # that the block sets anyway.
    before = tgis.get_raise_on_error()
    tgis.set_raise_on_error(False)
    try:
        with temporal_session(tmp_path / "p"):
            assert tgis.get_raise_on_error() is True
        assert tgis.get_raise_on_error() is False
    finally:
        tgis.set_raise_on_error(before)


@pytest.mark.parametrize("before_block", [False, True])
def test_messenger_mode_is_set_and_restored(tmp_path, before_block):
    """Both orders: the messenger exists with either mode before the block.

    init() does not change the mode of an existing messenger, so the helper
    has to set it and put the old mode back. After the block the mode is
    probed with msgr.fatal(), because open_old_stds() cannot run there: with
    no session it fails with OSError (t.connect not found; probed 2026-10-15).
    """
    msgr = get_msgr()
    found = msgr.raise_on_error
    msgr.set_raise_on_error(before_block)
    try:
        with temporal_session(tmp_path / "p"):
            assert msgr.raise_on_error is True
            with pytest.raises(FatalError):
                tgis.open_old_stds("missing", "strds")
        assert msgr.raise_on_error is before_block
        if not before_block:
            with pytest.raises(SystemExit):
                msgr.fatal("probe")
    finally:
        msgr.set_raise_on_error(found)


def test_messenger_created_by_the_block_is_left_in_exit_mode(tmp_path):
    """A messenger that init() creates in the block is back in exit mode after.

    This pins the restore rule for a process without a messenger: later tests
    expect sys.exit on fatal errors. The cache of get_msgr() and
    tgis.core.message_interface are emptied for the test, because there is no
    other way to start from "no messenger", and both are put back afterwards.
    """
    cache = get_msgr.__defaults__[0]
    original = cache[0]
    original_interface = tgis.core.message_interface
    cache[0] = None
    tgis.core.message_interface = None
    try:
        with temporal_session(tmp_path / "p"):
            assert get_msgr().raise_on_error is True
        created = get_msgr()
        assert created is not original
        assert created.raise_on_error is False
        created.server.terminate()
    finally:
        cache[0] = original
        tgis.core.message_interface = original_interface


def test_mapset_is_created_and_entered(tmp_path):
    with project_session(tmp_path / "p", mapset="other") as session:
        assert gs.read_command("g.gisenv", get="MAPSET", env=session.env).strip() == (
            "other"
        )


def test_add_mapset_keeps_current_mapset(tmp_path):
    with project_session(tmp_path / "p") as session:
        add_mapset(session, "user1")
        mapsets = gs.read_command("g.mapsets", flags="l", env=session.env)
        assert "user1" in mapsets.split()
        current = gs.read_command("g.gisenv", get="MAPSET", env=session.env)
        assert current.strip() == "PERMANENT"
