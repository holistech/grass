"""Pin what t.topology prints for no maps, so that library changes cannot alter it"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds

# Recorded on 2026-11-06 on the unchanged library (commit 5afc992456) by running
# the tool on an empty dataset and on a dataset whose where selects nothing, and
# printing stdout and stderr. The summary after the basic information is
# compared exactly; the basic information holds the id, the creator and the
# times of the run.
EMPTY_SUMMARY = """\
 +-------------------- Temporal topology -------------------------------------+
 | Is subset of dataset: ...... {subset}
 | Temporal topology is: ...... valid
 | Number of points: .......... 0
 | Number of intervals: ....... 0
 | Invalid time stamps: ....... 0
 | Number of gaps: ............ 0
 | Granularity: ............... None
 +-------------------- Topological relations ---------------------------------+
+----------------------------------------------------------------------------+
"""

NOTHING = "start_time > '2100-01-01'"


@pytest.fixture
def datasets(tools, prefix):
    """An empty dataset and one with a map, named by the prefix"""
    tools.t_create(output=f"{prefix}_empty", title="t", description="d")
    create_stds(
        tools,
        "strds",
        f"{prefix}_full",
        [MapSpec(f"{prefix}_1", 1, datetime(2026, 1, 1), datetime(2026, 1, 2))],
    )
    return f"{prefix}_empty", f"{prefix}_full"


def test_empty_selection_prints_as_before(tools, datasets):
    empty, full = datasets
    for name, options, subset in (
        (empty, {}, "False"),
        (full, {"where": NOTHING}, "True"),
    ):
        result = tools.t_topology(input=name, **options)
        text = result.stdout
        assert text.endswith(EMPTY_SUMMARY.format(subset=subset)), text
        assert result.stderr == ""
        # -m lists the maps one by one and prints nothing without maps.
        listed = tools.t_topology(input=name, flags="m", **options)
        assert (listed.stdout, listed.stderr) == ("", "")
