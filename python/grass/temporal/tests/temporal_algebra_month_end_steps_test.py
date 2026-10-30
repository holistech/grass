"""tshift() and buff_t() by months and years from the end of a month

A month or year step that ends behind the last day of a shorter month ends
on that day. Before, the library raised a ValueError ("day is out of range
for month") and the expression stopped in every algebra. The reference
implementation (grass.temporal.classic), the classic profile (-c) and the
core give the same maps, for each kind of dataset and for the selection of
t.select.
"""

from datetime import datetime

import pytest

from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.differential import RUNNERS, outcome
from grass.tools import Tools

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

# Kind of the algebra, type of its datasets, prefix of the dataset names.
KINDS = {
    "raster": ("strds", "R"),
    "raster3d": ("str3ds", "D"),
    "vector": ("stvds", "V"),
    "select": ("strds", "R"),
}


@pytest.fixture(scope="module")
def datasets(temporal_module_session):
    """M with a map from 31.01.2001 to 31.03.2001, L with one from the leap
    day 29.02.2004 to 31.03.2004, D with one from 01.12.2003 to 01.01.2004,
    for each dataset type"""
    tools = Tools(session=temporal_module_session)
    tools.g_region(n=1, s=0, e=1, w=0, res=1, b=0, t=1, res3=1)
    for stds_type, prefix in dict.fromkeys(KINDS.values()):
        create_stds(
            tools,
            stds_type,
            f"{prefix}M",
            [MapSpec(f"{prefix}m1", 1, datetime(2001, 1, 31), datetime(2001, 3, 31))],
        )
        create_stds(
            tools,
            stds_type,
            f"{prefix}D",
            [MapSpec(f"{prefix}d1", 1, datetime(2003, 12, 1), datetime(2004, 1, 1))],
        )
        create_stds(
            tools,
            stds_type,
            f"{prefix}L",
            [MapSpec(f"{prefix}l1", 1, datetime(2004, 2, 29), datetime(2004, 3, 31))],
        )


@pytest.mark.parametrize("runner", ["reference", "classic", "core"])
@pytest.mark.parametrize("kind", list(KINDS))
@pytest.mark.parametrize(
    ("expression", "start", "end"),
    [
        # 31.01. + 1 month = 28.02. (2001 is no leap year); 31.03. + 1 month
        # = 30.04.
        ('tshift({}M, "1 months")', "2001-02-28T00:00:00", "2001-04-30T00:00:00"),
        # 31.01. - 1 month = 31.12.2000; 31.03. + 1 month = 30.04.
        ('buff_t({}M, "1 months")', "2000-12-31T00:00:00", "2001-04-30T00:00:00"),
        # 29.02.2004 + 1 year = 28.02.2005; 31.03.2004 + 1 year = 31.03.2005.
        ('tshift({}L, "1 years")', "2005-02-28T00:00:00", "2005-03-31T00:00:00"),
        # 01.12.2003 - 24 months = 01.12.2001; 01.01.2004 + 24 months =
        # 01.01.2006. A step back by 24 months from December raised "bad month
        # number 0".
        ('buff_t({}D, "24 months")', "2001-12-01T00:00:00", "2006-01-01T00:00:00"),
        # 01.12.2003 - 24 months = 01.12.2001; 01.01.2004 - 24 months =
        # 01.01.2002.
        ('tshift({}D, "-24 months")', "2001-12-01T00:00:00", "2002-01-01T00:00:00"),
    ],
)
def test_month_and_year_steps_end_on_the_last_day_of_a_shorter_month(
    datasets, runner, kind, expression, start, end
):
    stds_type, prefix = KINDS[kind]
    options = {"stdstype": stds_type} if kind == "select" else {}
    result = outcome(
        kind,
        expression.format(prefix),
        RUNNERS[runner],
        basename=f"me{runner}",
        **options,
    )
    assert "error" not in result, result
    assert [row[1:3] for row in result["maps"]] == [[start, end]]
