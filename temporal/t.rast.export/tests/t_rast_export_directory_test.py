"""Test where t.rast.export puts the archive and its working files

The option directory is the directory in which the maps are exported before
they are packed; the archive itself goes to the path given by output, which a
relative path takes from the current directory.
"""

import pytest


def test_a_relative_output_is_written_to_the_current_directory(
    tools, absolute, tmp_path, monkeypatch
):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(tmp_path)

    tools.t_rast_export(
        input=absolute, output="out.tar", directory=str(work), compression="no"
    )

    assert (tmp_path / "out.tar").is_file()
    assert not (work / "out.tar").exists()


# More than a second (measured 18.10.2026 with a serial pytest --durations=0).
@pytest.mark.slow
@pytest.mark.parametrize("fmt", ["GTiff", "AAIGrid", "pack"])
def test_the_working_files_are_removed(tools, absolute, tmp_path, fmt):
    work = tmp_path / "work"
    work.mkdir()

    tools.t_rast_export(
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
    tools.t_rast_export(**options, where="start_time < '2001-02-01'")
    first = archive.stat().st_size

    tools.t_rast_export(**options, overwrite=True)

    assert archive.stat().st_size > first
