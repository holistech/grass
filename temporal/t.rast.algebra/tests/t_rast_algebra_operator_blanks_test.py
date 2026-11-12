# SPDX-FileCopyrightText: 2026 Soeren Gebbert
# SPDX-FileCopyrightText: GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later

"""A blank after a comma of an operator in curly brackets is read

Every expected value is derived by hand from the data: A has two daily maps
with the values 1 and 2 (1 and 2 January 2001), N the same days with 10 and
20, and W one map of two days (1 to 3 January) with the value 100. The
operator of the paper can be written {+,equal,l} or, with blanks, {+,equal, l}.
GRASS 8.5 matched the operator with a regular expression that allowed no blank
before the letter of the temporal reference and ended with a syntax error.
"""

import datetime

import pytest

from grass.temporal.testing import io_cache
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.outcomes import constant_values, outcome
from grass.tools import Tools

KIND = "raster"

pytestmark = pytest.mark.slow

DAY1 = datetime.datetime(2001, 1, 1)
DAY2 = datetime.datetime(2001, 1, 2)
DAY3 = datetime.datetime(2001, 1, 3)

# (expression with blanks, the same without, value of each result map)
CASES = [
    # a1 + n1 = 1 + 10 and a2 + n2 = 2 + 20
    ("A {+,equal, l} N", "A {+,equal,l} N", [11, 22]),
    # W contains both maps of A: the hash operator counts 2
    ("W {#,contains, l} A", "W {#,contains,l} A", [2]),
    # Both maps of A lie during W; r gives each pair the time of the right
    # map, so there is a result for a1 (value 1) and one for a2 (value 2)
    ("A {:,during, r} W", "A {:,during,r} W", [1, 2]),
    # a blank before the relation as well: 1 + 10 and 2 + 20
    ("A {+, equal, l} N", "A {+,equal,l} N", [11, 22]),
]


@pytest.fixture(scope="module")
def blanks(temporal_module_session):
    """The datasets A, N and W"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    for name, specs in {
        "A": [MapSpec("a1", 1, DAY1, DAY2), MapSpec("a2", 2, DAY2, DAY3)],
        "N": [MapSpec("n1", 10, DAY1, DAY2), MapSpec("n2", 20, DAY2, DAY3)],
        "W": [MapSpec("w1", 100, DAY1, DAY3)],
    }.items():
        create_stds(tools, "strds", name, specs)
    with io_cache.cached_io(io_cache.CacheStorage()):
        yield


@pytest.fixture(autouse=True)
def cached_io(blanks):
    """Replace the fixture of conftest.py: the caches run through blanks"""


@pytest.mark.parametrize(("spaced", "plain", "expected"), CASES)
def test_blanks_in_an_operator_do_not_change_the_result(
    blanks, spaced, plain, expected
):
    assert constant_values(outcome(KIND, spaced, basename="fa")) == expected
    assert constant_values(outcome(KIND, plain, basename="fb")) == expected
