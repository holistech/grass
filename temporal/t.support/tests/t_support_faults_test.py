"""Test that t.support writes the granularity anew that a release stored

Releases before GRASS 8.6 stored the granularity "1 day" for a month series
that starts on the last day of a month; the granularity is now "1 month". A
dataset keeps the stored value until an update reads its maps again: t.support
with -u, with -m or with a changed title, description, semantic type or
aggregation type.
"""

from datetime import datetime
from itertools import pairwise

import pytest

import grass.temporal as tgis
from grass.temporal.testing.data import MapSpec, create_stds
from grass.tools import Tools

D = datetime
ENDS = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]


@pytest.fixture(scope="module")
def tools(temporal_module_session):
    tools = Tools(session=temporal_module_session, quiet=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    return tools


def granularity(tools, name):
    return tools.t_info(input=name, flags="g").keyval["granularity"]


@pytest.mark.parametrize(
    "options",
    [
        {"flags": "u"},
        {"flags": "m"},
        {"title": "Changed"},
        {"description": "Changed"},
        {"semantictype": "sum"},
        {"aggr_type": "maximum"},
    ],
    ids=["u", "m", "title", "description", "semantictype", "aggr_type"],
)
def test_stored_granularity_updates_on_support(tools, prefix, options):
    create_stds(
        tools,
        "strds",
        prefix,
        [
            MapSpec(f"{prefix}_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(ENDS), start=1)
        ],
    )
    # The value an older release stored, written as it would have written it
    dataset = tgis.open_old_stds(prefix, "strds")
    dataset.set_granularity("1 day")
    dataset.update()
    assert granularity(tools, prefix) == "'1 day'"

    tools.t_support(input=prefix, **options)

    assert granularity(tools, prefix) == "'1 month'"
