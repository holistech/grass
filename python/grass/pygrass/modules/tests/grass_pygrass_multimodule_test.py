"""Test failing modules in PyGRASS Module and MultiModule"""

import multiprocessing
import os
import pickle
import signal
import time

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.pygrass.modules import Module, MultiModule, ParallelModuleQueue
from grass.pygrass.modules.interface import module as module_interface

# The tests below patch functions that only the child process of MultiModule
# calls. The patch reaches the child only if it is forked from the test.
needs_fork = pytest.mark.skipif(
    multiprocessing.get_start_method() != "fork",
    reason="the child process sees the patches of the test only with fork",
)


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


def fail_with_os_error(*args, **kwargs):
    msg = "simulated failure in the child process"
    raise OSError(msg)


@needs_fork
@pytest.mark.timeout(60)
def test_an_exception_before_the_module_starts_is_reported(session, monkeypatch):
    """A failure before Popen leaves every return code unset but is an error"""
    monkeypatch.setattr(Module, "run", fail_with_os_error)
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    later = Module("r.mapcalc", expression="later = 1", run_=False, quiet=True)
    multi = MultiModule([first, later], sync=False)
    multi.run()
    with pytest.raises(CalledModuleError, match="exit code 1") as error:
        multi.wait()
    # The OSError leaves the child process, and multiprocessing ends it with
    # exit code 1.
    assert error.value.returncode == 1
    assert error.value.module == "r.mapcalc"


@needs_fork
@pytest.mark.timeout(60)
def test_an_exception_after_the_module_started_is_reported(session, monkeypatch):
    """A failure after Popen leaves a module that cannot be sent back"""
    # Module.run() calls wait() itself for finish_=True, so the exception
    # comes after Popen, while the module still holds its process handle.
    monkeypatch.setattr(Module, "wait", fail_with_os_error)
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    multi = MultiModule([first], sync=False)
    multi.run()
    with pytest.raises(CalledModuleError, match="exit code 1") as error:
        multi.wait()
    assert error.value.returncode == 1


@needs_fork
@pytest.mark.timeout(60)
def test_a_failing_temporary_region_is_reported(session, monkeypatch):
    """A failure in use_temp_region() comes before any module runs"""
    monkeypatch.setattr(module_interface, "use_temp_region", fail_with_os_error)
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    multi = MultiModule([first], sync=False, set_temp_region=True)
    multi.run()
    with pytest.raises(CalledModuleError, match="exit code 1") as error:
        multi.wait()
    assert error.value.returncode == 1
    maps = gs.read_command("g.list", type="raster", env=session.env)
    assert "first" not in maps


@needs_fork
@pytest.mark.timeout(60)
def test_a_killed_child_is_reported(session, monkeypatch):
    """A child process killed by a signal sends nothing back"""
    # The sleep only keeps the child alive until the signal arrives.
    monkeypatch.setattr(
        module_interface, "_run_until_failure", lambda module_list: time.sleep(30)
    )
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    multi = MultiModule([first], sync=False)
    multi.run()
    os.kill(multi.p.pid, signal.SIGKILL)
    with pytest.raises(CalledModuleError) as error:
        multi.wait()
    # multiprocessing gives a process ended by a signal the negative signal
    # number as exit code.
    assert error.value.returncode == -signal.SIGKILL


@pytest.mark.timeout(60)
@pytest.mark.parametrize("set_temp_region", [False, True])
def test_a_slow_healthy_child_is_no_failure(session, monkeypatch, set_temp_region):
    """Waiting longer than one poll interval for the child is no failure"""
    # Each r.mapcalc takes far longer than 10 ms, so wait() polls many times
    # while the child is alive and has not sent the modules back yet.
    monkeypatch.setattr(module_interface, "_POLL_SECONDS", 0.01)
    modules = [
        Module("r.mapcalc", expression=f"slow_{i} = {i}", run_=False, quiet=True)
        for i in range(3)
    ]
    multi = MultiModule(modules, sync=False, set_temp_region=set_temp_region)
    multi.run()
    finished = multi.wait()
    assert [module.returncode for module in finished] == [0, 0, 0]
    maps = gs.read_command("g.list", type="raster", env=session.env).split()
    assert sorted(maps) == ["slow_0", "slow_1", "slow_2"]


@needs_fork
@pytest.mark.timeout(60)
def test_parallel_module_queue_reports_a_failed_child(session, monkeypatch):
    """ParallelModuleQueue.wait() passes the failure of the child on"""
    monkeypatch.setattr(Module, "run", fail_with_os_error)
    first = Module("r.mapcalc", expression="first = 1", run_=False, quiet=True)
    queue = ParallelModuleQueue(nprocs=2)
    queue.put(MultiModule([first], sync=False))
    with pytest.raises(CalledModuleError, match="exit code 1"):
        queue.wait()
