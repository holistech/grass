"""The classic algebra keeps what shared functions of the library computed

The classic algebra, the reference implementation grass.temporal.classic and
the classic profile of the core (t.rast.algebra -c,
GRASS_TEMPORAL_ALGEBRA=classic), computes what the releases computed that
publications cite. Some functions of the temporal library that serve all
tools may change their results: the granularity of a month series that
starts on the last day of a month, the gaps between maps, the relations of
the sampling method "start" and the start of a week granule. The classic
algebra calls only the granularity of these; it keeps its own copy of that
function (grass.temporal.classic.granularity).

Each test runs the reference (from the corpus, or live with
GRASS_TEMPORAL_REFERENCE=live) and the classic profile the way the tools run
it, and states the result by hand. The data is chosen so that a change of the
shared function would change the result, had the classic algebra no copy.
The classic algebra reads no gap list, no sampling method and no week start of
the library (measured 04.11.2026: a sys.monitoring probe recorded no call of
count_gaps(), get_registered_maps_as_objects_with_gaps(), method_relations()
or adjust_datetime_to_granularity() from grass.temporal.classic or
grass.temporal.algebra while the tests of the library and of the four algebra
tools ran with GRASS_TEMPORAL_REFERENCE=live and with
GRASS_TEMPORAL_ALGEBRA=classic); those tests hold its result on such data all
the same.

Every dataset has maps with constant values on a region of 3 x 3 cells, so
the minimum and the maximum of a result map are its value.

One correction of the library holds for the classic algebra too, by decision
of 05.11.2026: compute_datetime_delta() counts the months between two firsts
of a month over more than a year in full and a unit of the time of the day
only where the two times differ in it or a finer unit. The copy computes the
delta as the library does.

The granularity mode (-g) computes the common granularity of the datasets with
the function of the library that the algebra core calls too. The classic
algebra keeps a copy of it as on 06.11.2026; the guard test holds the values of
that day, recorded in data/classic_common_granularity.json, and a wiring test
shows that the reference and the classic profile call the copy and the core
the library.
"""

import datetime
import json
import sys
from itertools import pairwise
from pathlib import Path

import pytest

from grass.temporal import datetime_math, temporal_granularity
from grass.temporal.classic import granularity as classic_granularity
from grass.temporal.classic.granularity import dataset_granularity
from grass.temporal.testing.corpus import reference_outcome
from grass.temporal.testing.data import MapSpec, create_stds
from grass.temporal.testing.differential import compare, outcome_of_runner
from grass.tools import Tools

# Every test chooses its algebra itself, see the marker in pyproject.toml.
pytestmark = [pytest.mark.slow, pytest.mark.fixed_algebra]

KIND = "raster"
DAY = datetime.timedelta(days=1)
HOUR = datetime.timedelta(hours=1)


def day(month, number):
    return datetime.datetime(2026, month, number)


# Months from the last day of January: a month step from 31 January ends on
# the last day of each shorter month.
MONTH_ENDS = [day(1, 31), day(2, 28), day(3, 31), day(4, 30)]
MONTHS = list(pairwise(MONTH_ENDS))


@pytest.fixture(scope="module")
def datasets(temporal_module_session):
    """The datasets of the tests, in one session for the module"""
    tools = Tools(session=temporal_module_session, overwrite=True, quiet=True)
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    create_stds(
        tools,
        "strds",
        "MON",
        [
            MapSpec(f"mon{number}", number, start, end)
            for number, (start, end) in enumerate(MONTHS, start=1)
        ],
    )
    create_stds(
        tools,
        "strds",
        "INST",
        [
            MapSpec(f"inst{number}", number, start)
            for number, start in enumerate(MONTH_ENDS[:3], start=1)
        ],
    )
    # The second map lies within the first, the third overlaps its end: the
    # time from 5 to 8 January lies between two maps but is covered by the
    # first one.
    create_stds(
        tools,
        "strds",
        "COVER",
        [
            MapSpec("cover1", 1, day(1, 1), day(1, 11)),
            MapSpec("cover2", 2, day(1, 3), day(1, 5)),
            MapSpec("cover3", 3, day(1, 8), day(1, 13)),
        ],
    )
    # The time from 3 January to the instant on 4 January, 12:00, lies between
    # the second map and the instant but within the first map. Counted as a
    # gap, its 36 hours make the granularity "12 hours"; the intervals of 4
    # and 1 days alone would give "1 day".
    create_stds(
        tools,
        "strds",
        "HOURS",
        [
            MapSpec("hours1", 1, day(1, 1), day(1, 5)),
            MapSpec("hours2", 2, day(1, 2), day(1, 3)),
            MapSpec("hours3", 3, day(1, 4) + 12 * HOUR),
        ],
    )
    # equa1 equals equb1; equa2 starts equb2.
    create_stds(
        tools,
        "strds",
        "EQA",
        [
            MapSpec("equa1", 1, day(1, 1), day(1, 5)),
            MapSpec("equa2", 2, day(1, 10), day(1, 15)),
        ],
    )
    create_stds(
        tools,
        "strds",
        "EQB",
        [
            MapSpec("equb1", 10, day(1, 1), day(1, 5)),
            MapSpec("equb2", 20, day(1, 10), day(1, 20)),
        ],
    )
    # 3 January 2026 is a Saturday; the week of the granules starts there.
    create_stds(
        tools,
        "strds",
        "WEEK",
        [
            MapSpec("week1", 1, day(1, 3), day(1, 10)),
            MapSpec("week2", 2, day(1, 10), day(1, 17)),
        ],
    )


def both(expression, **options):
    """The outcomes of the reference and the classic profile, after comparing

    The profile is the runner "classic" of grass.temporal.testing.differential,
    which finds the common granularity of the granularity mode (-g) as
    t.rast.algebra -c -g does.

    :param options: options of the runs, such as granularity=True or
        time_suffix="gran"; register_null is set as in outcome_of_runner
    """
    options = {"register_null": True, **options}
    reference = reference_outcome(KIND, expression, **options)
    profile = outcome_of_runner(KIND, expression, "classic", "fb", **options)
    assert compare(KIND, expression, reference, profile) is None
    return reference, profile


def rows(start_end_values, names=None):
    """Rows of an outcome: [name, start, end, minimum, maximum]

    Without names, the rows are compared without the name. An end of None
    is a time instant.
    """
    result = [
        [start.isoformat(), end and end.isoformat(), float(value), float(value)]
        for start, end, value in start_end_values
    ]
    if names is None:
        return result
    return [[name, *row] for name, row in zip(names, result, strict=True)]


def maps(result, with_names=True):
    assert "error" not in result, result
    return [row if with_names else row[1:] for row in result["maps"]]


def test_classic_keeps_old_granularity(datasets):
    """The granularity of a month series from 31 January is "1 day"

    The steps 31 January, 28 February, 31 March, 30 April take 28, 31 and
    30 days and are no whole months from the first day of a month, so the
    greatest common unit is one day. The time suffix "gran" names the maps
    by the day.
    """
    expected = rows(
        [(start, end, number) for number, (start, end) in enumerate(MONTHS, start=1)],
        names=["N_2026_01_31", "N_2026_02_28", "N_2026_03_31"],
    )
    for result in both("MON * 1", time_suffix="gran"):
        assert maps(result) == expected


def test_classic_keeps_old_granularity_in_the_granularity_mode(datasets):
    """-g samples the month series by its granularity "1 day"

    The granules are the 89 days from 31 January to 29 April; each takes the
    value of the map it lies in and is named by its day.
    """
    days = [MONTH_ENDS[0] + number * DAY for number in range(89)]
    values = [
        next(
            number for number, end in enumerate(MONTH_ENDS[1:], start=1) if start < end
        )
        for start in days
    ]
    expected = rows(
        [
            (start, start + DAY, value)
            for start, value in zip(days, values, strict=True)
        ],
        names=[f"N_{start:%Y_%m_%d}" for start in days],
    )
    assert values.count(1) == 28
    assert values.count(2) == 31
    assert values.count(3) == 30
    for result in both("MON * 1", granularity=True, time_suffix="gran"):
        assert maps(result) == expected


def test_classic_keeps_old_granularity_in_tsnap(datasets):
    """tsnap() ends the last time instant after the granularity "1 day"

    The instants 31 January, 28 February and 31 March end at the start of
    the next one; the last one, which has no next, ends one granule later,
    on 1 April.
    """
    expected = rows(
        [
            (day(1, 31), day(2, 28), 1),
            (day(2, 28), day(3, 31), 2),
            (day(3, 31), day(4, 1), 3),
        ]
    )
    for result in both("tsnap(INST)"):
        assert maps(result, with_names=False) == expected


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        # Each map ends where the next one starts; the last keeps its end.
        (
            "tsnap(COVER)",
            [
                (day(1, 1), day(1, 3), 1),
                (day(1, 3), day(1, 8), 2),
                (day(1, 8), day(1, 13), 3),
            ],
        ),
        # The first map contains the second one only; the third overlaps it.
        ("COVER {#,contains} COVER", [(day(1, 1), day(1, 11), 1)]),
    ],
    ids=["tsnap", "count"],
)
def test_classic_keeps_old_gaps(datasets, expression, expected):
    """A dataset whose maps leave a gap that a longer map covers"""
    for result in both(expression):
        assert maps(result, with_names=False) == rows(expected)


def test_classic_keeps_old_gaps_in_the_granularity(datasets):
    """The granularity counts a gap that a longer map covers: "12 hours"

    The time suffix "gran" names the maps by the hour.
    """
    expected = rows(
        [
            (day(1, 1), day(1, 5), 1),
            (day(1, 2), day(1, 3), 2),
            (day(1, 4) + 12 * HOUR, None, 3),
        ],
        names=["N_2026_01_01_00", "N_2026_01_02_00", "N_2026_01_04_12"],
    )
    for result in both("HOURS * 1", time_suffix="gran"):
        assert maps(result) == expected


def test_classic_keeps_old_gaps_in_the_granularity_mode(datasets):
    """-g refuses maps that lie in or overlap each other"""
    for result in both("COVER * 1", granularity=True):
        assert result["error"] == "FatalError"


def test_classic_keeps_old_start_relations(datasets):
    """starts relates a map that starts another and ends before it, not an
    equal one: equa2 + equb2 = 22 in the time of equa2"""
    expected = rows([(day(1, 10), day(1, 15), 22)])
    for result in both("EQA {+,starts} EQB"):
        assert maps(result, with_names=False) == expected


def test_classic_keeps_old_start_relations_in_a_selection(datasets):
    """t.select keeps equa2, which starts equb2, and not equa1, which equals
    equb1"""
    expression = "EQA {:,starts} EQB"
    reference = reference_outcome("select", expression)
    profile = outcome_of_runner("select", expression, "classic", "fb")
    assert compare("select", expression, reference, profile) is None
    for result in (reference, profile):
        assert maps(result) == rows([(day(1, 10), day(1, 15), 2)], names=["equa2"])


def test_classic_keeps_old_week_granules(datasets):
    """-g with the granularity "7 days" starts the granules with the first map

    The first map starts on Saturday, 3 January 2026; the granules are the
    two weeks of the maps, not weeks from a Monday.
    """
    expected = rows(
        [(day(1, 3), day(1, 10), 1), (day(1, 10), day(1, 17), 2)],
        names=["N_2026_01_03", "N_2026_01_10"],
    )
    for result in both("WEEK * 1", granularity=True, time_suffix="gran"):
        assert maps(result) == expected


class RowsOnly:
    """A dataset that has registered maps but no stored granularity to read

    dataset_granularity() gets the rows of the maps; get_granularity() fails
    the test, because the classic algebra must not follow the value that the
    library stored.
    """

    def __init__(self, rows, absolute=True):
        self.rows = rows
        self.absolute = absolute

    def get_registered_maps(self, order, dbif):
        assert order == "start_time"
        return self.rows

    def is_time_absolute(self):
        return self.absolute

    def get_granularity(self):
        pytest.fail("dataset_granularity() read the stored granularity")


def row(start, end=None):
    return {"start_time": start, "end_time": end}


@pytest.mark.parametrize(
    ("dataset", "expected"),
    [
        # No maps; get_registered_maps() may also give None
        (RowsOnly([]), None),
        (RowsOnly(None), None),
        # A map without start time makes the map time "invalid"
        (RowsOnly([row(day(1, 1), day(1, 2)), row(None)]), None),
        # A single instant has no time difference
        (RowsOnly([row(day(1, 31))]), None),
        (RowsOnly([row(start, end) for start, end in MONTHS]), "1 day"),
        (RowsOnly([row(1, 2), row(4, 5)], absolute=False), 1),
        (RowsOnly([row(0), row(4)], absolute=False), 4),
    ],
    ids=["no maps", "none", "invalid", "instant", "months", "relative", "points"],
)
def test_the_granularity_of_a_dataset_comes_from_its_maps(dataset, expected):
    """dataset_granularity() decides from the rows, also when there is none"""
    assert dataset_granularity(dataset, dbif=None) == expected


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime.datetime(2024, 1, 1), datetime.datetime(2025, 3, 1)),
        (datetime.datetime(2024, 11, 1), datetime.datetime(2025, 2, 1)),
        (datetime.datetime(2024, 3, 1), datetime.datetime(2026, 3, 1)),
        (datetime.datetime(2024, 1, 1), datetime.datetime(2026, 1, 1)),
        (datetime.datetime(2026, 6, 1, 10, 30), datetime.datetime(2026, 6, 11, 10, 30)),
        (datetime.datetime(2026, 6, 1, 10, 30), datetime.datetime(2026, 6, 11, 11, 30)),
        (datetime.datetime(2026, 6, 1, 10), datetime.datetime(2026, 6, 1, 10, 0, 30)),
        (datetime.datetime(2026, 6, 1), datetime.datetime(2026, 6, 11)),
    ],
)
def test_classic_copy_equals_library_delta(start, end):
    """The copy of compute_datetime_delta() computes what the library does"""
    assert classic_granularity.compute_datetime_delta(
        start, end
    ) == datetime_math.compute_datetime_delta(start, end)


COMMON = json.loads(
    (Path(__file__).parent / "data" / "classic_common_granularity.json").read_text()
)
COMMON_DATES = {
    key: dates and [datetime.datetime.fromisoformat(date) for date in dates]
    for key, dates in COMMON["dates"].items()
}


@pytest.mark.parametrize(("grans", "dates", "expected"), COMMON["starts"])
def test_classic_common_granule_keeps_its_values(grans, dates, expected):
    """The copy of the common granule computes the values of 06.11.2026

    The cases and dates are those of the characterization test of the library
    function; the values are recorded, so that a change of the copy shows here
    even if the library changes the same way.
    """
    result = classic_granularity.compute_common_absolute_time_granularity(
        grans, COMMON_DATES[dates]
    )

    assert result == expected
    assert type(result) is type(expected)


class LibraryCalledError(Exception):
    """Raised in place of the common granule of the library"""


def test_reference_uses_the_classic_common_granule(datasets, monkeypatch):
    """-g of the reference and of the classic profile does not reach the library

    Every name in a loaded module of grass.temporal that holds the library
    function is replaced by one that raises, however a module imported it.
    The core, which keeps the function of the library, fails with it; that
    shows that the replacement takes effect.
    """
    library = temporal_granularity.compute_common_absolute_time_granularity

    def raising(*args, **kwargs):
        raise LibraryCalledError

    for name, module in list(sys.modules.items()):
        if module is None or not name.startswith("grass.temporal"):
            continue
        for attribute, value in list(vars(module).items()):
            if value is library:
                monkeypatch.setattr(module, attribute, raising)

    # The reference runs here, not from the corpus, which would not reach it.
    expression = "EQA + EQB"
    reference = outcome_of_runner(KIND, expression, "reference", "fa", granularity=True)
    profile = outcome_of_runner(KIND, expression, "classic", "fb", granularity=True)
    core = outcome_of_runner(KIND, expression, "core", "fc", granularity=True)

    assert compare(KIND, expression, reference, profile) is None
    assert maps(reference)
    assert core["error"] == "Other:LibraryCalledError"
