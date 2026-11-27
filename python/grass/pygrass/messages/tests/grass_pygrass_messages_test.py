"""Test when the Messenger warns that it restarted its server

The server is a process of its own. fatal() and stop() end it on purpose, and
the cleanup of a failed run may send messages afterwards; only a server that
died by itself is worth a warning.
"""

import os

import pytest

import grass.script as gs
from grass.pygrass.messages import Messenger

RESTART = "Needed to restart the messenger server"


@pytest.fixture
def session(tmp_path, monkeypatch):
    """A session in os.environ, which the message server reads"""
    project = tmp_path / "test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        for key, value in session.env.items():
            monkeypatch.setenv(key, value)
        yield session


def test_messages_after_fatal_do_not_warn(session, capfd):
    messenger = Messenger()
    with pytest.raises(SystemExit):
        messenger.fatal("the run ends")
    messenger.message("cleanup")
    messenger.stop()
    assert RESTART not in capfd.readouterr().err


def test_messages_after_stop_do_not_warn(session, capfd):
    messenger = Messenger()
    messenger.stop()
    messenger.message("again")
    messenger.stop()
    assert RESTART not in capfd.readouterr().err


def test_server_that_died_by_itself_warns(session, capfd):
    messenger = Messenger()
    messenger.server.terminate()
    messenger.server.join()
    messenger.message("after the death")
    messenger.stop()
    assert RESTART in capfd.readouterr().err
