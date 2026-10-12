"""Test failing modules in PyGRASS Module and MultiModule"""

import os
import pickle

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.pygrass.modules import Module, MultiModule


@pytest.fixture
def session(tmp_path, monkeypatch):
    """A session in os.environ, where Module reads the interface description"""
    project = tmp_path / "test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        for key, value in session.env.items():
            monkeypatch.setenv(key, value)
        gs.run_command("g.region", rows=2, cols=2, env=session.env)
        yield session


def failing_module():
    return Module(
        "r.mapcalc", expression="result = no_such_map", run_=False, quiet=True
    )


def test_failed_module_is_picklable(session):
    """A module that failed can be sent to another process"""
    module = failing_module()
    module.run_ = True
    with pytest.raises(CalledModuleError):
        module.run()
    pickle.dumps(module)


@pytest.mark.timeout(60)
def test_asynchronous_multimodule_reports_failure(session):
    """wait() raises for a failed module instead of waiting forever"""
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    multi = MultiModule([first, failing_module()], sync=False)
    multi.run()
    with pytest.raises(CalledModuleError, match="no_such_map"):
        multi.wait()
