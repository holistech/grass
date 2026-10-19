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
examples and the reason (measured 19.10.2026 with this module). A test fails
when a doctest fails that is not listed, when a listed one fails in another
number of examples, and when a listed one passes: whoever repairs a doctest
removes its entry. The doctests of the frozen modules are listed too; they
are not changed.
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
    "core",
    "datetime_math",
    "gui_support",
    "list_stds",
    "metadata",
    "space_time_datasets",
    "spatial_extent",
    "spatial_topology_dataset_connector",
    "spatio_temporal_relationships",
    "temporal_algebra",
    "temporal_extent",
    "temporal_granularity",
    "temporal_operator",
    "temporal_raster_algebra",
    "temporal_raster_base_algebra",
    "temporal_topology_dataset_connector",
    "temporal_vector_algebra",
]

# The doctests of gs.run_command() expect its output 0, as the function
# returned 0 once; it returns None now.
STALE_RUN_COMMAND = "expects the output 0 of gs.run_command(), which returns None"

# doctest name: (failed examples, reason). The frozen modules are
# abstract_space_time_dataset and temporal_algebra.
KNOWN_FAILURES = {
    "grass.temporal.abstract_space_time_dataset.AbstractSpaceTimeDataset._update_where_statement_by_spatial_extent": (
        1,
        "calls the method by its bare name, which is not in the namespace",
    ),
    "grass.temporal.base.DictSQLSerializer.serialize": (
        4,
        "expects the columns of the SQL statements in another order than the one of today",
    ),
    "grass.temporal.base.SQLDatabaseInterface": (
        8,
        "expects the columns of the SQL statements in another order than the one of today",
    ),
    "grass.temporal.c_libraries_interface.CLibrariesInterface": (
        14,
        f"seven examples {STALE_RUN_COMMAND}; three print dictionaries whose "
        "keys come in another order (and with u'' prefixes of Python 2); four "
        "call fatal_error() and get the FatalError of today in place of the "
        "message they expect",
    ),
    "grass.temporal.core.set_raise_on_error": (
        1,
        "expects the traceback text of fatal() with the exception named "
        "FatalError and a frame in __init__.py; Python prints "
        "grass.exceptions.FatalError and the full path",
    ),
    "grass.temporal.gui_support.tlist_grouped": (
        1,
        "expects the datasets precipitation and temperature of the North "
        "Carolina sample project in PERMANENT, the project here is empty",
    ),
    "grass.temporal.metadata.STRDSMetadata": (
        2,
        "print_info() and print_shell_info() of a metadata object without a "
        "table fail with sqlite3.OperationalError: no such table: None",
    ),
    "grass.temporal.space_time_datasets.Raster3DDataset": (5, STALE_RUN_COMMAND),
    "grass.temporal.space_time_datasets.RasterDataset": (
        6,
        f"five examples {STALE_RUN_COMMAND}; print_info() prints the line "
        "Semantic label that the doctest does not know",
    ),
    "grass.temporal.space_time_datasets.VectorDataset": (5, STALE_RUN_COMMAND),
    "grass.temporal.spatio_temporal_relationships.SpatioTemporalTopologyBuilder": (
        6,
        "lists the relations of a map in the order of the keys of a "
        "dictionary, which is another one today",
    ),
    "grass.temporal.temporal_algebra.TemporalAlgebraParser.set_granularity": (
        1,
        "lists the maps of the result in another order",
    ),
    "grass.temporal.temporal_granularity.get_time_tuple_function": (
        1,
        "passes a single map where the function indexes a list of maps",
    ),
    "grass.temporal.temporal_granularity.gran_to_gran": (
        2,
        "expects '87658.2 hours' and '5259492.0 minutes'; the floating point "
        "results are 87658.20000000001 hours and 5259492.000000001 minutes",
    ),
}


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
