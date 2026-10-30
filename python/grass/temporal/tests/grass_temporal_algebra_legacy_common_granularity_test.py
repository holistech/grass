"""The tests of the earlier gunittest file unittests_temporal_algebra_grs.py

They call the common granularity of the earlier select algebra directly:
setup_common_granularity() on the expression, then parse(). The new algebra
has no such step; the select expressions run in all three runners in
grass_temporal_algebra_legacy_select_test.py. The datasets are those of
algebra_cases.algebra_granularity: A a1..a6 = 1..6 on the months January to
June 2001, B b1 = 7 and b2 = 8 for three months each, C c1 = 9 for the year,
D d1..d3 = 10..12 for 31 days from the first of January, March and May.
"""

import datetime

import pytest

import grass.temporal as tgis
from grass.temporal.classic.temporal_algebra import TemporalAlgebraParser
from grass.temporal.testing import algebra_cases
from grass.tools import Tools

pytestmark = pytest.mark.fixed_algebra


@pytest.fixture(scope="module")
def data(temporal_module_session):
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    algebra_cases.algebra_granularity(tools)
    return temporal_module_session


def common_granularity(expression):
    parser = TemporalAlgebraParser(run=True, debug=True)
    assert parser.setup_common_granularity(expression=expression) is True
    return parser


# (expression, maps, minimum, maximum, months of the start and the end of the
# result in 2001)
CASES = [
    pytest.param("R = A : B", 6, 1, 6, (1, 7), id="two datasets"),
    pytest.param("R = A : C", 6, 1, 6, (1, 7), id="year to month sampling"),
    pytest.param("R = A : D", 3, 1, 5, (1, 6), id="gaps"),
    pytest.param("R = C : D", 3, 9, 9, (1, 6), id="year to month with gaps"),
    pytest.param("R = A : C : D", 3, 1, 5, (1, 6), id="three datasets and gaps"),
    pytest.param(
        "R = if(start_month(A) > 2, A : C : D)",
        2,
        3,
        5,
        (3, 6),
        id="conditional with gaps",
    ),
]


@pytest.mark.parametrize(("expression", "count", "low", "high", "months"), CASES)
def test_common_granularity(data, expression, count, low, high, months):
    parser = common_granularity(expression)
    assert parser.granularity == "1 month"
    parser.parse(expression=expression, basename="r", overwrite=True)

    result = tgis.open_old_stds("R", type="strds")
    assert result.metadata.get_number_of_maps() == count
    assert result.metadata.get_min_min() == low
    assert result.metadata.get_max_max() == high
    start, end = result.get_absolute_time()
    assert start == datetime.datetime(2001, months[0], 1)
    assert end == datetime.datetime(2001, months[1], 1)
    assert result.check_temporal_topology() is True
    assert result.get_granularity() == "1 month"


def test_the_datasets_are_sampled_to_the_common_granularity(data):
    # B has two maps of three months; at the granularity of one month it
    # contributes a map for each of the six months.
    parser = common_granularity("R = A : B")
    parser.count = 0
    parser.stdstype = "strds"
    parser.maptype = "raster"
    parser.mapclass = tgis.RasterDataset
    assert len(parser.check_stds("A")) == 6
    assert len(parser.check_stds("B")) == 6
