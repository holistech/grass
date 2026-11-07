"""Trace the calls of an example script and compare them with the public contract

The scripts run in a child process in the session of the module, whose
environment is mirrored into os.environ.
"""

import os
import textwrap

import pytest

from grass.temporal.testing.contract_trace import called_names, missing_from_contract

pytestmark = pytest.mark.usefixtures("temporal_module_session")

SCRIPT = """\
import grass.temporal as tgis

tgis.init()
stds = tgis.SpaceTimeRasterDataset("trace@PERMANENT")
stds.get_temporal_type()
stds.metadata.set_title("x")
"""

TRACED = {
    "grass.temporal.state.init",
    # Inherited: the method is defined on a base class of the dataset.
    "grass.temporal.abstract_dataset.AbstractDataset.get_temporal_type",
    # A setter that rows.py generates for a column of the metadata.
    "grass.temporal.metadata.STRDSMetadata.set_title",
}


def trace(tmp_path, source=SCRIPT):
    script = tmp_path / "example.py"
    script.write_text(textwrap.dedent(source))
    return called_names(script, env=dict(os.environ), cwd=tmp_path)


def test_called_names_records_public_calls(tmp_path):
    names = trace(tmp_path)

    assert names == TRACED


def test_called_names_leaves_out_private_names_and_the_calls_of_the_library(tmp_path):
    # __init__ is private, and init() calls many helpers of its own.
    names = trace(tmp_path)

    assert not [n for n in names if any(p.startswith("_") for p in n.split("."))]
    assert not [n for n in names if n.endswith((".connection", ".start_server"))]


def test_called_names_raises_with_the_stderr_of_a_failing_script(tmp_path):
    with pytest.raises(RuntimeError, match="ZeroDivisionError"):
        trace(tmp_path, "1 / 0\n")


def test_missing_from_contract_reports_unknown_names():
    invented_function = "grass.temporal.state.invented_function"
    invented_method = "grass.temporal.abstract_dataset.AbstractDataset.invented_method"
    # Not wrong, but nothing outside has used it yet: the metadata accessor
    # get_title is not in the contract (title and set_title are).
    unlisted = "grass.temporal.metadata.STRDSMetadata.get_title"

    assert missing_from_contract(TRACED) == []
    assert missing_from_contract(
        TRACED | {invented_function, invented_method, unlisted}
    ) == sorted([invented_function, invented_method, unlisted])


def test_a_copy_of_a_top_name_in_another_module_is_not_covered():
    # The classic algebra keeps its own copy of this function. The contract
    # pins the exported one, not every function of that name.
    exported = "grass.temporal.temporal_granularity.compute_absolute_time_granularity"
    copy = "grass.temporal.classic.granularity.compute_absolute_time_granularity"

    assert missing_from_contract({exported}) == []
    assert missing_from_contract({copy}) == [copy]


def test_methods_of_a_class_that_also_has_contract_attributes_stay_covered():
    # RasterDataset has entries under "methods" and under "attributes"; one
    # category must not replace the other.
    method = "grass.temporal.datasets.MapDataset.load"
    contract = {
        "top_names": {},
        "module_paths": {},
        "methods": {"RasterDataset": {"load": "docs"}},
        "attributes": {"RasterDataset": {"base": "docs"}},
        "members": {},
    }

    assert missing_from_contract({method}, contract=contract) == []


TIMED_MAPS = """\
from datetime import datetime

import grass.temporal as tgis
from grass.temporal.abstract_dataset import AbstractDatasetComparisonKeyStartTime
from grass.temporal.stds_time_edit import snap_map_list

maps = []
for name, day in (("b", 2), ("a", 1)):
    item = tgis.RasterDataset(f"{name}@m")
    item.set_absolute_time(datetime(2026, 1, day), datetime(2026, 1, day + 1))
    maps.append(item)
"""

KEY = "grass.temporal.abstract_dataset.AbstractDatasetComparisonKeyStartTime.__lt__"


def test_operator_of_a_public_class_is_recorded(tmp_path):
    # sorted() compares in the script's own call, through the key class.
    names = trace(
        tmp_path,
        TIMED_MAPS + "sorted(maps, key=AbstractDatasetComparisonKeyStartTime)\n",
    )

    assert KEY in names


def test_a_series_operator_is_covered_by_the_contract():
    division = "grass.temporal.algebra.series.Series.__truediv__"

    assert missing_from_contract({division}) == []


def test_private_base_method_is_reported_under_the_public_class(tmp_path):
    names = trace(
        tmp_path,
        """\
        import grass.temporal as tgis

        vector = tgis.VectorDataset("v@m")
        other = tgis.VectorDataset("w@m")
        for item in (vector, other):
            item.set_spatial_extent_from_values(10, 0, 10, 0, 10, 0)
        vector.spatial_intersection(other)
        """,
    )

    assert (
        "grass.temporal.space_time_datasets.VectorDataset.spatial_intersection" in names
    )


def test_private_base_method_without_public_self_is_left_out(tmp_path):
    # A private class instance, a function without self and a self from
    # outside grass.temporal give no name.
    names = trace(
        tmp_path,
        """\
        from grass.temporal.space_time_datasets import _PlanarExtentMethods

        class Outside:
            def spatial_intersection(self, other):
                return None

        Outside().spatial_intersection(None)
        try:
            _PlanarExtentMethods().spatial_intersection(None)
        except AttributeError:
            pass
        try:
            _PlanarExtentMethods.spatial_intersection(Outside(), None)
        except AttributeError:
            pass
        """,
    )

    assert not [n for n in names if n.endswith("spatial_intersection")]


def test_operator_called_inside_the_library_is_not_recorded(tmp_path):
    # snap_map_list sorts the maps with the key class itself.
    names = trace(tmp_path, TIMED_MAPS + "snap_map_list(maps)\n")

    assert "grass.temporal.stds_time_edit.snap_map_list" in names
    assert KEY not in names


def test_constructor_and_repr_stay_unrecorded(tmp_path):
    names = trace(
        tmp_path,
        TIMED_MAPS + "repr(maps[0])\nlen(maps)\nlist(iter(maps))\n",
    )

    assert not [
        n for n in names if n.endswith(("__init__", "__repr__", "__len__", "__iter__"))
    ]
