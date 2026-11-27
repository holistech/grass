"""Test t.shift on a dataset whose maps another dataset registers as well

The other dataset can belong to another mapset: with the mapset check switched
off, a shift must be refused before it moves a map."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from grass.temporal.testing.data import MapSpec, create_stds, create_timed_stds, day
from grass.temporal.testing.readback import inventory, list_maps, message
from grass.temporal.testing.session import mapset_session, project_session
from grass.tools import ToolError, Tools

D = datetime


def _times(tools, name):
    return [(row.start, row.end) for row in list_maps(tools, "strds", name)]


def test_shift_of_extract_without_expression_moves_original(tools, prefix):
    """An extract without expression registers the maps of the original

    The time belongs to the map, so the shift of the extract moves the maps in
    the original dataset too; only an extract with an expression has maps of
    its own.
    """
    original = create_timed_stds(tools, prefix, [(day(0), day(1)), (day(1), day(2))])
    shared = f"{prefix}_shared"
    tools.t_rast_extract(input=original, output=shared)
    before = _times(tools, original)

    tools.t_shift(input=shared, granularity="10 days")

    assert _times(tools, shared) == _times(tools, original)
    assert _times(tools, original) != before
    assert _times(tools, original) == [
        ("2001-01-11 00:00:00", "2001-01-12 00:00:00"),
        ("2001-01-12 00:00:00", "2001-01-13 00:00:00"),
    ]


def test_shift_of_extract_with_expression_leaves_original(tools, prefix):
    original = create_timed_stds(tools, prefix, [(day(0), day(1)), (day(1), day(2))])
    own = f"{prefix}_own"
    tools.t_rast_extract(
        input=original, output=own, expression=original, basename=f"{prefix}_own"
    )
    before = _times(tools, original)

    tools.t_shift(input=own, granularity="10 days")

    assert _times(tools, original) == before
    assert _times(tools, own) != before


@pytest.fixture(scope="module")
def foreign_copy(tmp_path_factory):
    """Tools in the mapset "second" with a dataset of copies of maps of "first"

    The dataset ds of "first" is registered in "second" by an extract without
    expression, so "second" holds the dataset copy whose maps belong to
    "first".
    """
    project = tmp_path_factory.mktemp("foreign_copy") / "project"
    with (
        project_session(project, mapset="second") as second,
        mapset_session(second, "first") as first,
    ):
        work, owner = (
            Tools(session=session, consistent_return_value=True, capture_stderr=True)
            for session in (second, first)
        )
        for tools in (work, owner):
            tools.g_region(n=1, s=0, e=1, w=0, res=1)
        create_stds(
            owner,
            "strds",
            "ds",
            [
                MapSpec("r_1", 1, D(2001, 1, 1), D(2001, 1, 2)),
                MapSpec("r_2", 2, D(2001, 1, 2), D(2001, 1, 3)),
            ],
        )
        work.g_mapsets(operation="add", mapset="first")
        work.t_rast_extract(input="ds@first", output="copy")
        work.g_gisenv(set="TGIS_DISABLE_MAPSET_CHECK=True")
        yield SimpleNamespace(work=work, owner=owner)


def _named_times(tools, name):
    return [(row.name, row.start, row.end) for row in list_maps(tools, "strds", name)]


@pytest.mark.parametrize("granularity", ["10 days", "10 days,1 hour"])
def test_disabled_mapset_check_refuses_before_moving(foreign_copy, granularity):
    """The extent of the dataset of the owner cannot be updated, so no map moves

    With the mapset check off the maps of "first" were written before the
    dataset of "first" was found to be out of reach.
    """
    work, owner = foreign_copy.work, foreign_copy.owner
    before = (_named_times(work, "copy"), _named_times(owner, "ds"), inventory(work))

    with pytest.raises(ToolError) as error:
        work.t_shift(input="copy", granularity=granularity)
    text = message(error.value)

    assert "Unable to update dataset <ds@first>" in text
    assert "Traceback" not in text
    assert (
        _named_times(work, "copy"),
        _named_times(owner, "ds"),
        inventory(work),
    ) == before
