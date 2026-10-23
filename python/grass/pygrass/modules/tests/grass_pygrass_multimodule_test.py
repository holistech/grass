"""Test failing modules in PyGRASS Module and MultiModule"""

import os
import pickle

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.pygrass.modules import Module, MultiModule, ParallelModuleQueue


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


@pytest.mark.timeout(60)
def test_asynchronous_multimodule_prints_no_traceback_of_the_child(session, capfd):
    """The failure is reported by the parent only, not by a traceback of the child"""
    multi = MultiModule([failing_module()], sync=False)
    multi.run()
    with pytest.raises(CalledModuleError, match="no_such_map"):
        multi.wait()
    assert "Traceback" not in capfd.readouterr().err


@pytest.mark.timeout(60)
def test_the_child_stops_at_the_first_failure(session, capfd):
    """Modules after the failed one are not run, as when the exception propagated"""
    later = Module("r.mapcalc", expression="later = 1", run_=False, quiet=True)
    multi = MultiModule([failing_module(), later], sync=False)
    multi.run()
    with pytest.raises(CalledModuleError) as error:
        multi.wait()
    assert error.value.module == "r.mapcalc"
    assert "no_such_map" in str(error.value)
    assert "Traceback" not in capfd.readouterr().err
    maps = gs.read_command("g.list", type="raster", env=session.env)
    assert "later" not in maps


@pytest.mark.timeout(60)
@pytest.mark.parametrize("set_temp_region", [False, True])
def test_parallel_module_queue_reports_failure_without_traceback(
    session, capfd, set_temp_region
):
    """ParallelModuleQueue.wait() raises for the failed module of the queue"""
    queue = ParallelModuleQueue(nprocs=2)
    queue.put(
        MultiModule([failing_module()], sync=False, set_temp_region=set_temp_region)
    )
    with pytest.raises(CalledModuleError, match="no_such_map"):
        queue.wait()
    assert "Traceback" not in capfd.readouterr().err
