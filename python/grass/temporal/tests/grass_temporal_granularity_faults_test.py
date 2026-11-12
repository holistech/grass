"""The granularity of month steps, the gaps of overlapping maps and granule sampling

A month step that is cut to the end of a shorter month, as a series from
31 January takes it (31 January, 28 February, 31 March), counts as one month
in the granularity, if both of its ends lie whole months after the earliest
start of the maps. A gap is time that no map covers: a map that ends inside a
longer one leaves no gap behind it. The granules of a dataset reach to the
latest end of its maps, not to the end of the map that starts last.

The classic algebra keeps the old rules in copies of its own, see
grass_temporal_classic_frozen_library_test.py. Both count a step between two
firsts of a month over more than a year in full and the hours, minutes and
seconds of a step only where the two times of the day differ in them.

The common granule of datasets whose start times differ in a finer unit than
the granule is one unit of the finest unit in which they differ.
"""

import datetime
from itertools import pairwise

import pytest

import grass.temporal as tgis
from grass.pygrass.messages import FatalError
from grass.temporal.algebra.content import MapRef
from grass.temporal.algebra.series import Extent, Series, Slot, Space
from grass.temporal.related_maps import with_gaps
from grass.temporal.testing.data import MapSpec, create_stds
from grass.tools import Tools

D = datetime.datetime


def absolute_maps(*extents):
    """Raster map objects with the absolute times (start, end)"""
    maps = []
    for number, (start, end) in enumerate(extents):
        map_ = tgis.RasterDataset(f"m{number}@PERMANENT")
        assert map_.set_absolute_time(start, end)
        maps.append(map_)
    return maps


def series_of(starts, *, instants=False):
    """Adjacent intervals between the starts, or instants at the starts"""
    if instants:
        return absolute_maps(*((start, None) for start in starts))
    return absolute_maps(*pairwise(starts))


MONTH_ENDS = [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)]


@pytest.fixture(scope="module")
def session(temporal_module_session):
    return temporal_module_session


@pytest.fixture(scope="module")
def tools(session):
    tools = Tools(session=session, overwrite=True, quiet=True)
    tools.g_region(n=1, s=0, e=1, w=0, res=1)
    return tools


@pytest.mark.parametrize("instants", [False, True], ids=["intervals", "instants"])
@pytest.mark.parametrize(
    ("starts", "expected"),
    [
        # 31 January, 28 February, 31 March, 30 April: each step is one month
        # step from 31 January, cut to the end of the shorter month.
        (MONTH_ENDS, "1 month"),
        # From 30 January: 28 February, 30 March, 30 April
        ([D(2026, 1, 30), D(2026, 2, 28), D(2026, 3, 30), D(2026, 4, 30)], "1 month"),
        # A leap year: 29 February
        ([D(2024, 1, 31), D(2024, 2, 29), D(2024, 3, 31)], "1 month"),
        # The same day of each month needs no cut
        ([D(2026, 1, 15), D(2026, 2, 15), D(2026, 3, 15)], "1 month"),
        # Two months from the end of a month
        ([D(2026, 1, 31), D(2026, 3, 31), D(2026, 5, 31)], "2 months"),
        # A year from 31 January is twelve months; from January to January a
        # step counts in years, as from the first of January.
        ([D(2025, 1, 31), D(2026, 1, 31), D(2027, 1, 31)], "1 year"),
        # 28 February is no month after 31 January when the year has a 29
        # February: the steps are 28 and 32 days.
        ([D(2024, 1, 31), D(2024, 2, 28), D(2024, 3, 31)], "4 days"),
        # 27 February lies one day short of a month step
        ([D(2026, 1, 31), D(2026, 2, 27), D(2026, 3, 31)], "1 day"),
        # 28 March is no month step from 31 January, which would end on
        # 31 March: the two steps are 28 days each.
        ([D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 28)], "28 days"),
        # The same with 28 April: steps of 28, 28 and 31 days
        (
            [D(2026, 1, 31), D(2026, 2, 28), D(2026, 3, 28), D(2026, 4, 28)],
            "1 day",
        ),
        # From 28 February the month steps end on the 28th: 31 March and
        # 30 April are not on them, the steps are 31 and 30 days.
        ([D(2026, 2, 28), D(2026, 3, 31), D(2026, 4, 30)], "1 day"),
        # A yearly series from 29 February is cut to 28 February in the other
        # years. It counts in months, as a yearly series from 1 February does.
        ([D(2024, 2, 29), D(2025, 2, 28), D(2026, 2, 28)], "12 months"),
        # A step over more than a year counts all its months: 31 January 2024
        # to 31 March 2025 is 14 months.
        ([D(2024, 1, 31), D(2025, 3, 31)], "14 months"),
        # Steps of 13 months from the end of a month
        ([D(2025, 1, 31), D(2026, 2, 28), D(2027, 3, 31)], "13 months"),
        # The first of each month, as before
        ([D(2026, 1, 1), D(2026, 2, 1), D(2026, 3, 1)], "1 month"),
        # Days that cross the end of a month stay days
        ([D(2026, 1, 30), D(2026, 1, 31), D(2026, 2, 1), D(2026, 2, 2)], "1 day"),
    ],
    ids=[
        "month ends",
        "30th",
        "leap year",
        "15th",
        "two months",
        "year",
        "leap day missed",
        "one day short",
        "chained cut",
        "chained cut, four",
        "from 28 February",
        "yearly from 29 February",
        "over a year",
        "13 months",
        "first",
        "days",
    ],
)
def test_month_end_series_has_one_month(session, starts, expected, instants):
    """A step between two time stamps of the month grid of the earliest start,
    with the cut to the month end, is a month"""
    maps = series_of(starts, instants=instants)
    assert tgis.compute_absolute_time_granularity(maps) == expected


def test_month_steps_with_a_time_of_day_are_months(session):
    """A month series at 06:00 has the granularity "1 month": the time of the
    day is the same at both ends of each step, so the hours do not count.
    Before 05.11.2026 they did, and the granularity was "24 hours"."""
    starts = [moment.replace(hour=6) for moment in MONTH_ENDS]
    assert tgis.compute_absolute_time_granularity(series_of(starts)) == "1 month"


@pytest.mark.parametrize("instants", [False, True], ids=["intervals", "instants"])
def test_granularity_of_month_firsts_over_a_year(session, instants):
    """A step from 1 January 2024 to 1 March 2025 is 14 months, not 2"""
    starts = [D(2024, 1, 1), D(2025, 3, 1)]
    assert (
        tgis.compute_absolute_time_granularity(series_of(starts, instants=instants))
        == "14 months"
    )


def test_granularity_of_instants_at_the_same_time_of_day(session):
    """Instants at 10:30, ten days apart, are 10 days apart, not 14400
    minutes"""
    starts = [D(2026, 6, 1, 10, 30), D(2026, 6, 11, 10, 30)]
    assert (
        tgis.compute_absolute_time_granularity(series_of(starts, instants=True))
        == "10 days"
    )


def test_granularity_of_instants_at_another_time_of_day(session):
    """Instants at 10:30 and 11:30 ten days later are 241 hours apart: the
    hours differ and count, the minutes are equal and do not"""
    starts = [D(2026, 6, 1, 10, 30), D(2026, 6, 11, 11, 30)]
    assert (
        tgis.compute_absolute_time_granularity(series_of(starts, instants=True))
        == "241 hours"
    )


def test_registered_month_end_series_stores_one_month(tools, session):
    """t.register stores the granularity "1 month" of a series from 31 January"""
    create_stds(
        tools,
        "strds",
        "month_ends",
        [
            MapSpec(f"month_end_{number}", number, start, end)
            for number, (start, end) in enumerate(pairwise(MONTH_ENDS), start=1)
        ],
    )
    dataset = tgis.open_old_stds("month_ends", "strds")
    assert dataset.get_granularity() == "1 month"


# m_1 1 to 11 January, m_2 3 to 5 January, m_3 8 to 13 January: m_1 covers
# 5 to 8 January, so there is no gap. m_4 15 to 16 January leaves a gap from
# 13 January, the latest end before it.
COVER = [
    (D(2026, 1, 1), D(2026, 1, 11)),
    (D(2026, 1, 3), D(2026, 1, 5)),
    (D(2026, 1, 8), D(2026, 1, 13)),
    (D(2026, 1, 15), D(2026, 1, 16)),
]


@pytest.fixture(scope="module")
def cover(tools):
    create_stds(
        tools,
        "strds",
        "cover",
        [
            MapSpec(f"cover_{number}", number, start, end)
            for number, (start, end) in enumerate(COVER, start=1)
        ],
    )
    return tgis.open_old_stds("cover", "strds")


def test_gap_inside_longer_map_is_not_a_gap(cover):
    """The list with gaps has one gap, from 13 to 15 January"""
    maps = cover.get_registered_maps_as_objects_with_gaps()
    listed = [(map_.get_id(), *map_.get_temporal_extent_as_tuple()) for map_ in maps]
    assert listed == [
        ("cover_1@PERMANENT", *COVER[0]),
        ("cover_2@PERMANENT", *COVER[1]),
        ("cover_3@PERMANENT", *COVER[2]),
        (None, D(2026, 1, 13), D(2026, 1, 15)),
        ("cover_4@PERMANENT", *COVER[3]),
    ]


def test_gap_inside_longer_map_is_not_counted(cover):
    """count_gaps() counts the one gap from 13 to 15 January"""
    assert cover.count_gaps() == 1
    assert tgis.topology.count_gaps(absolute_maps(*COVER)) == 1


def test_gap_after_an_instant_inside_a_longer_map(session):
    """An instant inside an interval does not end the covered time: the gap
    begins at the end of the interval"""
    maps = absolute_maps(
        (D(2026, 1, 1), D(2026, 1, 5)),
        (D(2026, 1, 3), None),
        (D(2026, 1, 7), D(2026, 1, 8)),
    )
    assert tgis.topology.count_gaps(maps) == 1


def slot(name, start, end):
    return Slot(
        Extent(start, end, "days"), MapRef(f"{name}@PERMANENT"), Space(1, 0, 1, 0), name
    )


def test_gap_inside_longer_granule_is_not_a_gap_slot():
    """with_gaps() gives the granules of t.sample a gap only where no granule
    lies: from 13 to 15, not from 5 to 8"""
    granules = Series(
        (slot("a", 1, 11), slot("b", 3, 5), slot("c", 8, 13), slot("d", 15, 16)),
        "raster",
    )
    result = with_gaps(granules).slots
    assert [found.origin for found in result] == ["a", "b", "c", None, "d"]
    assert (result[3].extent.start, result[3].extent.end) == (13, 15)


@pytest.fixture(scope="module")
def nest(tools):
    """nest_a 1 to 3 July and nest_b 1 to 2 July: the same start, the shorter
    map last in the order of the start time"""
    create_stds(
        tools,
        "strds",
        "nest",
        [
            MapSpec("nest_a", 1, D(2026, 7, 1), D(2026, 7, 3)),
            MapSpec("nest_b", 2, D(2026, 7, 1), D(2026, 7, 2)),
        ],
    )
    return tgis.open_old_stds("nest", "strds")


def test_granules_reach_the_end_of_the_dataset(nest):
    """The granules of "1 day" reach 3 July, the end of nest_a"""
    granules = nest.get_registered_maps_as_objects_by_granularity()
    assert [granule[0].get_temporal_extent_as_tuple() for granule in granules] == [
        (D(2026, 7, 1), D(2026, 7, 2)),
        (D(2026, 7, 2), D(2026, 7, 3)),
    ]


@pytest.fixture(scope="module")
def model(tools):
    """Three maps of 6 hours each, in relative time"""
    create_stds(
        tools,
        "strds",
        "model",
        [MapSpec(f"model_{k}", k, 6 * k, 6 * k + 6) for k in range(3)],
        temporaltype="relative",
        unit="hours",
    )
    return tgis.open_old_stds("model", "strds")


@pytest.mark.parametrize("granule", [12, "12", "12 hours", "12 hour"])
def test_relative_granule_in_the_unit_of_the_dataset(model, granule):
    """A number, or a number with the unit of the dataset, is a granule"""
    granules = model.get_registered_maps_as_objects_by_granularity(gran=granule)
    assert [granule[0].get_temporal_extent_as_tuple() for granule in granules] == [
        (0, 12),
        (12, 24),
    ]


@pytest.mark.parametrize("granule", ["1 day", "12 foo", "x", "0", "-6", "1.5"])
def test_relative_granule_of_another_unit_is_refused(model, granule):
    """Another unit, a text and a number below 1 end with a message"""
    with pytest.raises(FatalError, match="granule"):
        model.get_registered_maps_as_objects_by_granularity(gran=granule)


@pytest.fixture(scope="module")
def instant(tools):
    create_stds(tools, "strds", "instant", [MapSpec("instant_1", 1, D(2026, 3, 1))])
    return tgis.open_old_stds("instant", "strds")


def test_single_instant_names_missing_granularity(instant):
    """A dataset of one instant has no granularity; the message says so. It
    gives no hint on a granule: t.rast.to.rast3 and t.rast.out.vtk reach it
    and have no granule option, the list tools give the hint themselves."""
    with pytest.raises(FatalError, match="has no granularity") as error:
        instant.get_registered_maps_as_objects_by_granularity()
    assert "granule" not in str(error.value)


@pytest.mark.parametrize(
    ("anchor", "expected"),
    [
        # From the anchor 31 January the granule after 28 February ends on
        # 31 March.
        (D(2026, 1, 31), [(D(2026, 2, 28), D(2026, 3, 31))]),
        # Without anchor the granules count from 28 February.
        (None, [(D(2026, 2, 28), D(2026, 3, 28)), (D(2026, 3, 28), D(2026, 4, 28))]),
        # 15 January lies no whole month before 28 February: from 28 February.
        (
            D(2026, 1, 15),
            [(D(2026, 2, 28), D(2026, 3, 28)), (D(2026, 3, 28), D(2026, 4, 28))],
        ),
    ],
    ids=["month end", "none", "off the grid"],
)
def test_month_granules_count_from_the_anchor(session, anchor, expected):
    maps = absolute_maps((D(2026, 2, 28), D(2026, 3, 31)))
    granules = tgis.AbstractSpaceTimeDataset.resample_maplist_by_granularity(
        maps, D(2026, 2, 28), D(2026, 3, 31), "1 month", anchor=anchor
    )
    assert [granule[0].get_temporal_extent_as_tuple() for granule in granules] == (
        expected
    )


@pytest.fixture(scope="module")
def relative_instant(tools):
    create_stds(
        tools,
        "strds",
        "relative_instant",
        [MapSpec("relative_instant_1", 1, 5)],
        temporaltype="relative",
        unit="days",
    )
    return tgis.open_old_stds("relative_instant", "strds")


def test_single_relative_instant_names_missing_granularity(relative_instant):
    """In relative time the dataset of one instant stores the granularity 0"""
    with pytest.raises(FatalError, match="has no granularity"):
        relative_instant.get_registered_maps_as_objects_by_granularity()


def test_relative_granule_given_as_number_is_taken_as_it_is(relative_instant):
    """A number is not read like the text of a tool option: the granularity 0
    of a relative dataset of one instant gives no granule, as before, which
    the classic algebra relied on in its granularity mode (it then failed with
    a TypeError, measured 05.11.2026 on the reference before and after this
    rule)"""
    assert (
        relative_instant.get_registered_maps_as_objects_by_granularity(gran=0) is None
    )


@pytest.mark.parametrize(
    ("grans", "starts", "expected"),
    [
        # Daily at midnight and daily at noon: a granule of one day starts at
        # one of the two times only, an hour fits both.
        (["1 day", "1 day"], [D(2026, 6, 1), D(2026, 6, 1, 12)], "1 hour"),
        # Monthly from the first and from the fifteenth of a month
        (["1 month", "1 month"], [D(2026, 1, 1), D(2026, 1, 15)], "1 day"),
        # Yearly from January and from July
        (["1 year", "1 year"], [D(2025, 1, 1), D(2026, 7, 1)], "1 month"),
        # The finest unit that differs decides: the days and the minutes differ.
        (["2 days", "1 day"], [D(2026, 6, 1), D(2026, 6, 2, 0, 30)], "1 minute"),
        # Starts that differ only in a coarser unit than the granule keep it.
        (["1 day", "1 day"], [D(2026, 6, 1, 12), D(2026, 7, 1, 12)], "1 day"),
        (["1 year", "1 year"], [D(2025, 3, 1), D(2026, 3, 1)], "1 year"),
    ],
    ids=["noon", "fifteenth", "july", "finest", "same time of day", "same month"],
)
def test_common_granule_aligns_starts_that_differ_in_a_finer_unit(
    grans, starts, expected
):
    """The common granule is one unit of the finest unit in which the starts
    differ, if that unit is finer than the granule"""
    assert (
        tgis.temporal_granularity.compute_common_absolute_time_granularity(
            grans, starts
        )
        == expected
    )
