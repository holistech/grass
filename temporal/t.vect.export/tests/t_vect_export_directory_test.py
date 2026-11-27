"""Test where t.vect.export puts the archive and its working files

The option directory is the directory in which the maps are exported before
they are packed; the archive itself goes to the path given by output, which a
relative path takes from the current directory.
"""

import os
import sys

import pytest

from grass.tools import Tools


def test_a_relative_output_is_written_to_the_current_directory(
    tools, absolute, tmp_path, monkeypatch
):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(tmp_path)

    tools.t_vect_export(
        input=absolute, output="out.tar", directory=str(work), compression="no"
    )

    assert (tmp_path / "out.tar").is_file()
    assert not (work / "out.tar").exists()


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GML", "GPKG", "pack"])
def test_the_working_files_are_removed(tools, absolute, tmp_path, fmt):
    work = tmp_path / "work"
    work.mkdir()

    tools.t_vect_export(
        input=absolute,
        output=str(tmp_path / "out"),
        directory=str(work),
        format=fmt,
        compression="no",
    )

    assert list(work.iterdir()) == []


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
def test_overwrite_replaces_the_archive(tools, absolute, tmp_path):
    archive = tmp_path / "out"
    options = {"input": absolute, "output": str(archive), "compression": "no"}
    tools.t_vect_export(**options, where="start_time < '2001-02-01'")
    first = archive.stat().st_size

    tools.t_vect_export(**options, overwrite=True)

    assert archive.stat().st_size > first


def test_without_directory_the_work_is_done_in_the_temporary_directory(
    tools, absolute, tmp_path
):
    # A fixed default such as /tmp does not exist on Windows; the temporary
    # directory of the system is TMPDIR, TEMP or TMP there as here. The work
    # directory inside is removed again, but making and removing it changes
    # the modification time of its parent.
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    os.utime(temporary, (0, 0))
    # Tools has no public access to the environment it runs the tools in
    # (grass.tools of 21.10.2026).
    env = dict(tools._original_env)  # noqa: SLF001
    env["TMPDIR"] = str(temporary)
    tools_with_temporary = Tools(env=env, consistent_return_value=True)

    tools_with_temporary.t_vect_export(
        input=absolute, output=str(tmp_path / "out.tar"), compression="no"
    )

    assert (tmp_path / "out.tar").is_file()
    # On Windows the time of a directory stayed the same when an entry was
    # added or removed (OSGeo4W CI, 26.11.2026), so only the other
    # platforms can show that the work was done here.
    if sys.platform != "win32":
        assert temporary.stat().st_mtime > 0
    assert list(temporary.iterdir()) == []
