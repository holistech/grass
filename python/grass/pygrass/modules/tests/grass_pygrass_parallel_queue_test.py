"""Test how ParallelModuleQueue fills its slots

The modules of the tests are a small script tool. A slow one waits for a
release file that the test creates, so the order in which the processes end
is fixed by the test and not by timing. The script ends on its own after
RELEASE_DEADLINE seconds, so that a queue that waits for the slow module
too early fails a test instead of hanging it.
"""

import os
import stat
import sys
import time
from subprocess import PIPE

import pytest

import grass.script as gs
from grass.exceptions import CalledModuleError
from grass.pygrass.modules import Module, MultiModule, ParallelModuleQueue

RELEASE_DEADLINE = 60

HELPER = f"""#!{sys.executable}
# %module
# % description: Stands in for a module in the tests of ParallelModuleQueue
# %end
# %option
# % key: release
# % type: string
# % required: no
# % description: Wait until this file exists
# %end
# %option
# % key: done
# % type: string
# % required: no
# % description: Create this file before ending
# %end
# %option
# % key: size
# % type: integer
# % required: no
# % answer: 0
# % description: Number of bytes to write to stdout
# %end
# %flag
# % key: f
# % description: End with an error
# %end

import sys
import time
from pathlib import Path

import grass.script as gs


def main():
    options, flags = gs.parser()
    if options["release"]:
        deadline = time.monotonic() + {RELEASE_DEADLINE}
        while not Path(options["release"]).exists() and time.monotonic() < deadline:
            time.sleep(0.01)
    sys.stdout.write("x" * int(options["size"]))
    sys.stdout.flush()
    if options["done"]:
        Path(options["done"]).touch()
    if flags["f"]:
        gs.fatal("The helper failed as asked")


if __name__ == "__main__":
    main()
"""


@pytest.fixture
def session(tmp_path, monkeypatch):
    """A session in os.environ, where Module reads the interface description"""
    project = tmp_path / "test"
    gs.create_project(project)
    with gs.setup.init(project, env=os.environ.copy()) as session:
        for key, value in session.env.items():
            monkeypatch.setenv(key, value)
        yield session


class Helpers:
    """Creates helper modules and releases and stops their processes"""

    def __init__(self, directory):
        self.directory = directory
        self.release_file = directory / "release"
        self.script = directory / "queue_helper.py"
        self.script.write_text(HELPER)
        self.script.chmod(self.script.stat().st_mode | stat.S_IXUSR)
        self.modules = []

    def module(self, name, *, slow=False, fail=False, **kwargs):
        """A helper module that creates the marker file of name when it ends

        A slow module waits for the release file first.
        """
        if slow:
            kwargs["release"] = str(self.release_file)
        if fail:
            kwargs["flags"] = "f"
        module = Module(
            str(self.script), done=str(self.marker(name)), run_=False, **kwargs
        )
        self.modules.append(module)
        return module

    def marker(self, name):
        return self.directory / f"{name}.done"

    def release(self):
        self.release_file.touch()

    def stop(self):
        """Release the slow modules and end every process that is left"""
        self.release()
        for module in self.modules:
            if module._popen is not None:
                module._popen.kill()
                module._popen.wait()


@pytest.fixture
def helpers(session, tmp_path):
    helpers = Helpers(tmp_path)
    yield helpers
    helpers.stop()


def wait_for_files(paths):
    """Wait until all files exist; fail after RELEASE_DEADLINE seconds"""
    deadline = time.monotonic() + RELEASE_DEADLINE
    while not all(path.exists() for path in paths):
        assert time.monotonic() < deadline, "files did not appear in time"
        time.sleep(0.01)


def done_names(modules):
    """The marker names of the modules, which identify them also after the
    modules came back from the child process of a MultiModule as copies"""
    return [os.path.basename(module.inputs["done"].value) for module in modules]


# The tests create all modules before the first put(): creating a module
# runs it with --interface-description, and that time between two put() calls
# would let a fast module end before the queue first looks at it.


def test_free_slot_is_refilled(helpers):
    """A slot freed by a fast module runs the next module while a slow one runs"""
    queue = ParallelModuleQueue(nprocs=2)
    names = ["fast_1", "fast_2", "fast_3"]
    modules = [helpers.module("slow", slow=True)] + [
        helpers.module(name) for name in names
    ]
    for module in modules:
        queue.put(module)
    wait_for_files([helpers.marker(name) for name in names])
    # The slow module is still waiting for the release file.
    assert not helpers.marker("slow").exists()
    helpers.release()
    queue.wait()
    assert helpers.marker("slow").exists()


def test_finished_modules_in_put_order(helpers):
    """The finished modules come in the order of put(), not of their end

    fast_1 ends and is collected by the third put(), before slow ends. No
    put() waits for slow, which ends only after the release.
    """
    queue = ParallelModuleQueue(nprocs=2)
    modules = [
        helpers.module("slow", slow=True),
        helpers.module("fast_1"),
        helpers.module("fast_2"),
    ]
    for module in modules:
        queue.put(module)
    assert not helpers.marker("slow").exists()
    helpers.release()
    queue.wait()
    assert done_names(queue.get_finished_modules()) == [
        "slow.done",
        "fast_1.done",
        "fast_2.done",
    ]


def test_nprocs_one_is_synchronous(helpers):
    """With one process put() returns after the module ended"""
    queue = ParallelModuleQueue(nprocs=1)
    names = ["first", "second", "third"]
    modules = [helpers.module(name) for name in names]
    for name, module in zip(names, modules, strict=True):
        queue.put(module)
        assert module.returncode == 0
        assert helpers.marker(name).exists()
        assert queue.get_num_run_procs() == 0


def test_error_reported(helpers):
    """A failure collected by put() is raised by wait() after all processes

    The third put() collects failing_1, the only module that can end before
    the release. wait() raises it as the first failure, in the order of put(),
    with a note on failing_2.
    """
    queue = ParallelModuleQueue(nprocs=2)
    failing_1 = helpers.module("failing_1", fail=True)
    slow = helpers.module("slow", slow=True)
    failing_2 = helpers.module("failing_2", fail=True)
    for module in (failing_1, slow, failing_2):
        queue.put(module)
    assert failing_1.returncode == 1
    assert not helpers.marker("slow").exists()
    helpers.release()
    with pytest.raises(CalledModuleError) as excinfo:
        queue.wait()
    assert str(helpers.marker("failing_1")) in str(excinfo.value)
    assert excinfo.value.__notes__ == ["1 other module(s) of the queue failed as well"]
    assert slow.returncode == 0
    assert failing_2.returncode == 1
    assert done_names(queue.get_finished_modules()) == ["slow.done"]
    assert queue.get_num_run_procs() == 0


def test_multimodule_takes_one_slot(helpers):
    """A MultiModule takes one slot, and its modules come back together"""
    queue = ParallelModuleQueue(nprocs=2)
    multi = MultiModule(
        [helpers.module("multi_1"), helpers.module("multi_2")], sync=False
    )
    slow = helpers.module("slow", slow=True)
    fast = helpers.module("fast")
    queue.put(multi)
    assert queue.get_num_run_procs() == 1
    queue.put(slow)
    assert queue.get_num_run_procs() == 2
    # The slow module holds its slot, so this put() takes the slot of the
    # MultiModule.
    queue.put(fast)
    assert queue.get_num_run_procs() == 2
    assert not helpers.marker("slow").exists()
    helpers.release()
    queue.wait()
    assert done_names(queue.get_finished_modules()) == [
        "multi_1.done",
        "multi_2.done",
        "slow.done",
        "fast.done",
    ]


@pytest.mark.timeout(120)
def test_piped_output_does_not_block_the_queue(helpers):
    """Modules that fill the pipe of their output still free their slots

    Each module writes more than a pipe buffer holds (64 KiB on Linux), so it
    cannot end before the queue reads its output.
    """
    size = 1024 * 1024
    queue = ParallelModuleQueue(nprocs=2)
    piped = [helpers.module(f"piped_{i}", size=size, stdout_=PIPE) for i in range(3)]
    for module in piped:
        queue.put(module)
    queue.wait()
    assert [len(module.outputs["stdout"].value) for module in piped] == [size] * 3
