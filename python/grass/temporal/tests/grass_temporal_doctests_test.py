"""The doctests of grass.temporal, run in a temporal session

The earlier gunittest file test_temporal_doctests.py ran none of them under
Python 3 (its main block did nothing there), so nobody saw that some do not
pass. This module runs the doctests of every module that has some, one test
per module, each in a session of its own because the doctests make datasets
and maps and expect an empty project.

Two things differ from running a module with doctest.testmod():

* The doctests were written for a namespace that has everything of
  grass.temporal (``init()``, ``get_current_mapset()``, ``Raster3DDataset``)
  and ``datetime``, so the names are added to the globals of each doctest.
* The doctest runner ends a run by setting ``builtins._`` to None, which
  removes the gettext function ``_`` that grass.temporal calls for its
  messages; clear_globs=False keeps it. Its display hook is replaced by one
  that does not assign ``_`` either.

KNOWN_FAILURES lists the doctests that do not pass, with the number of failed
examples and the reason. A test fails when a doctest fails that is not listed,
when a listed one fails in another number of examples, and when a listed one
passes: whoever repairs a doctest removes its entry. It is empty since
21.10.2026, when the docstrings were repaired (the two frozen modules only in
the text of two docstrings).
"""

import builtins
import doctest
import importlib
import io
import sys
from pathlib import Path

import pytest

import grass.temporal as tgis
from grass.temporal.testing.session import temporal_session

pytestmark = pytest.mark.real_io

MODULES = [
    "abstract_map_dataset",
    "abstract_space_time_dataset",
    "algebra.content",
    "base",
    "c_libraries_interface",
    "datetime_math",
    "db",
    "granule_sampling",
    "gui_support",
    "list_stds",
    "metadata",
    "rows",
    "space_time_datasets",
    "spatial_extent",
    "state",
    "stds_time_edit",
    "temporal_algebra",
    "temporal_extent",
    "temporal_granularity",
    "temporal_operator",
    "temporal_raster_algebra",
    "temporal_raster_base_algebra",
    "topology",
    "temporal_vector_algebra",
]

# doctest name: (failed examples, reason). Empty: every doctest of the library
# passes; whoever breaks one fixes the docstring or the code.
KNOWN_FAILURES = {}


def doctest_globs():
    names = {
        name: getattr(tgis, name) for name in dir(tgis) if not name.startswith("_")
    }
    names["datetime"] = importlib.import_module("datetime").datetime
    return names


def show_without_assigning(value):
    """Print a value like sys.displayhook, but leave ``builtins._`` alone"""
    if value is not None:
        sys.stdout.write(repr(value) + "\n")


def run_doctests(module):
    """Run every doctest of a module, return {name: (failed, output)}"""
    results = {}
    finder = doctest.DocTestFinder()
    for test in finder.find(module, module.__name__, extraglobs=doctest_globs()):
        if not test.examples:
            continue
        output = io.StringIO()
        runner = doctest.DocTestRunner()
        runner.run(test, out=output.write, clear_globs=False)
        failed = runner.summarize(verbose=False).failed
        if failed:
            results[test.name] = (failed, output.getvalue())
    return results


@pytest.mark.parametrize("name", MODULES)
def test_the_doctests_of_a_module(name, tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "__displayhook__", show_without_assigning)
    module = importlib.import_module(f"grass.temporal.{name}")
    translate = builtins._
    with temporal_session(tmp_path / "project"):
        results = run_doctests(module)

    assert builtins._ is translate
    failed = {key: value[0] for key, value in results.items()}
    known = {
        key: value[0]
        for key, value in KNOWN_FAILURES.items()
        if key.startswith(f"grass.temporal.{name}.") or key == f"grass.temporal.{name}"
    }
    assert failed == known, "\n".join(value[1] for value in results.values())


def test_every_module_with_doctests_is_run():
    root = Path(tgis.__file__).parent
    found = {
        str(path.relative_to(root).with_suffix("")).replace("/", ".")
        for path in root.rglob("*.py")
        if ">>>" in path.read_text()
        and "ply" not in path.parts
        and "testing" not in path.parts
        and "tests" not in path.parts
    }
    assert found == set(MODULES)
