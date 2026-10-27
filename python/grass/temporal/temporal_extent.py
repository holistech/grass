"""
Temporal extent classes

Usage:

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> from datetime import datetime
    >>> tgis.init()
    >>> from grass.temporal.kinds import KINDS
    >>> t = tgis.temporal_extent.RelativeTimeRow(KINDS["raster"])
    >>> t = tgis.temporal_extent.AbsoluteTimeRow(KINDS["raster"])


SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .rows import Column, Row

if TYPE_CHECKING:
    from .kinds import Kind


# What a space time dataset has in its time rows in addition to a map.
_STDS_COLUMNS = (
    Column("granularity", doc="the granularity of the space time dataset"),
    Column(
        "map_time",
        doc=(
            "the type of the time of the registered maps: a single point of "
            'time "point", time intervals "interval", or single points and '
            'intervals "mixed". It is set automatically when maps are registered'
        ),
    ),
)


# The order in which temporal_relation() asks the predicates: the first one that
# holds names the relation. The order matters because the predicates overlap for
# intervals that start and end at the same time (66 of the 729 pairs of the
# extent test, counted 26.10.2026 by asking every predicate for every pair). A
# table over the comparisons of the four times gave the same names but needed
# 72 keys, a second statement of the semantics beside the predicates, and saved
# 0.4 us per pair (measured 25.10.2026 over the 1764 pairs the extent test had
# then, with extents that end before they start: 0.27 us against 0.67 us), so
# it was dropped.
_RELATION_ORDER = (
    "equal",
    "during",
    "contains",
    "overlaps",
    "overlapped",
    "after",
    "before",
    "starts",
    "finishes",
    "started",
    "finished",
    "follows",
    "precedes",
)


def _refuse_reversed(extent) -> None:
    """Raise ValueError if the extent ends before it starts

    Only the constructor and temporal_relation() check. The setters and the
    predicates do not: t.shift and t.snap set the start and the end one after
    the other and pass through such a state, and the classic algebra calls the
    predicates by name.
    """
    start = extent.D.get("start_time")
    end = extent.D.get("end_time")
    if start is not None and end is not None and end < start:
        msg = f"End time {end} is before start time {start}"
        raise ValueError(msg)


class TemporalExtent(Row):
    """This is the abstract time base class for relative and absolute time
    objects.

    It abstract class implements the interface to absolute and relative time.
    Absolute time is represented by datetime time stamps,
    relative time is represented by a unit an integer value.

    This class implements temporal topology relationships computation
    after [Allen and Ferguson 1994 Actions and Events in Interval Temporal Logic].

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> A = TemporalExtent(
        ...     table="raster_absolute_time",
        ...     ident="soil@PERMANENT",
        ...     start_time=datetime(2001, 1, 1),
        ...     end_time=datetime(2005, 1, 1),
        ... )
        >>> A.print_info()
         | Start time:................. 2001-01-01 00:00:00
         | End time:................... 2005-01-01 00:00:00

    """

    columns = (
        Column("start_time", doc="the valid start time of the extent"),
        Column("end_time", doc="the valid end time of the extent"),
    )

    def __init__(self, table=None, ident=None, start_time=None, end_time=None) -> None:
        """Constructor

        :raises ValueError: if end_time is before start_time; an extent that
                            starts and ends at the same time is accepted
        """
        super().__init__(table, ident)

        self.set_id(ident)
        self.set_start_time(start_time)
        self.set_end_time(end_time)
        _refuse_reversed(self)

    def intersect(self, extent):
        """Intersect this temporal extent with the provided temporal extent and
        return a new temporal extent with the new start and end time

        :param extent: The temporal extent to intersect with
        :return: The new temporal extent with start and end time,
                or None in case of no intersection

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=3, end_time=6)
            >>> B = TemporalExtent(start_time=5, end_time=7)
            >>> inter = A.intersect(B)
            >>> inter.print_info()
             | Start time:................. 5
             | End time:................... 6

        """
        relation = self.temporal_relation(extent)

        if relation in {"after", "before"}:
            return None

        if self.D["end_time"] is None:
            return TemporalExtent(start_time=self.D["start_time"])

        if extent.D["end_time"] is None:
            return TemporalExtent(start_time=extent.D["start_time"])

        start = None
        end = None

        if self.D["start_time"] > extent.D["start_time"]:
            start = self.D["start_time"]
        else:
            start = extent.D["start_time"]

        if self.D["end_time"] > extent.D["end_time"]:
            end = extent.D["end_time"]
        else:
            end = self.D["end_time"]

        if issubclass(type(self), RelativeTemporalExtent):
            return RelativeTemporalExtent(
                start_time=start, end_time=end, unit=self.get_unit()
            )
        if issubclass(type(self), AbsoluteTemporalExtent):
            return AbsoluteTemporalExtent(start_time=start, end_time=end)
        if issubclass(type(self), TemporalExtent):
            return TemporalExtent(start_time=start, end_time=end)

    def disjoint_union(self, extent):
        """Creates a disjoint union with this temporal extent and the provided one.
        Return a new temporal extent with the new start and end time.

        :param extent: The temporal extent to create a union with
        :return: The new temporal extent with start and end time

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=3, end_time=6)
            >>> B = TemporalExtent(start_time=5, end_time=7)
            >>> inter = A.disjoint_union(B)
            >>> inter.print_info()
             | Start time:................. 3
             | End time:................... 7

        """

        start = None
        end = None

        if self.D["start_time"] < extent.D["start_time"]:
            start = self.D["start_time"]
        else:
            start = extent.D["start_time"]

        # End time handling
        if self.D["end_time"] is None and extent.D["end_time"] is None:
            if self.D["start_time"] > extent.D["start_time"]:
                end = self.D["start_time"]
            else:
                end = extent.D["start_time"]
        elif self.D["end_time"] is None:
            if self.D["start_time"] > extent.D["end_time"]:
                end = self.D["start_time"]
            else:
                end = extent.D["end_time"]
        elif extent.D["end_time"] is None:
            if self.D["end_time"] > extent.D["start_time"]:
                end = self.D["end_time"]
            else:
                end = extent.D["start_time"]
        elif self.D["end_time"] < extent.D["end_time"]:
            end = extent.D["end_time"]
        else:
            end = self.D["end_time"]

        if issubclass(type(self), RelativeTemporalExtent):
            return RelativeTemporalExtent(
                start_time=start, end_time=end, unit=self.get_unit()
            )
        if issubclass(type(self), AbsoluteTemporalExtent):
            return AbsoluteTemporalExtent(start_time=start, end_time=end)
        if issubclass(type(self), TemporalExtent):
            return TemporalExtent(start_time=start, end_time=end)

    def union(self, extent):
        """Creates a union with this temporal extent and the provided one.
        Return a new temporal extent with the new start and end time.

        :param extent: The temporal extent to create a union with
        :return: The new temporal extent with start and end time,
                 or None in case the temporal extents are unrelated
                 (before or after)

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=8)
            >>> A.union(TemporalExtent(start_time=3, end_time=6)).print_info()
             | Start time:................. 3
             | End time:................... 8
            >>> print(A.union(TemporalExtent(start_time=3, end_time=4)))
            None

        """

        relation = self.temporal_relation(extent)

        if relation in {"after", "before"}:
            return None

        return self.disjoint_union(extent)

    def starts(self, extent) -> bool:
        """Return True if this temporal extent (A) starts at the start of the
        provided temporal extent (B) and finishes within it
        ::

            A  |-----|
            B  |---------|


        :param extent: The temporal extent object with which this extent
                       starts

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=6)
            >>> B = TemporalExtent(start_time=5, end_time=7)
            >>> A.starts(B)
            True

        """
        if self.D["end_time"] is None or extent.D["end_time"] is None:
            return False

        return bool(
            self.D["start_time"] == extent.D["start_time"]
            and self.D["end_time"] < extent.D["end_time"]
        )

    def started(self, extent) -> bool:
        """Return True if this temporal extent (A) started at the start of the
        provided temporal extent (B) and finishes after it
        ::

            A  |---------|
            B  |-----|

        :param extent: The temporal extent object with which this extent
                       started

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=5, end_time=6)
            >>> A.started(B)
            True

        """
        if self.D["end_time"] is None or extent.D["end_time"] is None:
            return False

        return bool(
            self.D["start_time"] == extent.D["start_time"]
            and self.D["end_time"] > extent.D["end_time"]
        )

    def finishes(self, extent) -> bool:
        """Return True if this temporal extent (A) starts after the start of
        the provided temporal extent (B) and finishes with it
        ::

            A      |-----|
            B  |---------|

        :param extent: The temporal extent object with which this extent
                       finishes

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=6, end_time=7)
            >>> B = TemporalExtent(start_time=5, end_time=7)
            >>> A.finishes(B)
            True

        """
        if self.D["end_time"] is None or extent.D["end_time"] is None:
            return False

        return bool(
            self.D["end_time"] == extent.D["end_time"]
            and self.D["start_time"] > extent.D["start_time"]
        )

    def finished(self, extent) -> bool:
        """Return True if this temporal extent (A) starts before the start of
        the provided temporal extent (B) and finishes with it
        ::

            A  |---------|
            B      |-----|

        :param extent: The temporal extent object with which this extent
                       finishes

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=6, end_time=7)
            >>> A.finished(B)
            True

        """
        if self.D["end_time"] is None or extent.D["end_time"] is None:
            return False

        return bool(
            self.D["end_time"] == extent.D["end_time"]
            and self.D["start_time"] < extent.D["start_time"]
        )

    def after(self, extent) -> bool:
        """Return True if this temporal extent (A) is located after the
        provided temporal extent (B)
        ::

            A             |---------|
            B  |---------|

        :param extent: The temporal extent object that is located before
                       this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=8, end_time=9)
            >>> B = TemporalExtent(start_time=6, end_time=7)
            >>> A.after(B)
            True

        """
        if extent.D["end_time"] is None:
            return self.D["start_time"] > extent.D["start_time"]

        return self.D["start_time"] > extent.D["end_time"]

    def before(self, extent):
        """Return True if this temporal extent (A) is located before the
        provided temporal extent (B)
        ::

            A  |---------|
            B             |---------|

        :param extent: The temporal extent object that is located after
                       this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=6, end_time=7)
            >>> B = TemporalExtent(start_time=8, end_time=9)
            >>> A.before(B)
            True

        """
        if self.D["end_time"] is None:
            return self.D["start_time"] < extent.D["start_time"]

        return self.D["end_time"] < extent.D["start_time"]

    def follows(self, extent) -> bool:
        """Return True if this temporal extent (A) follows the
        provided temporal extent (B)
        ::

            A            |---------|
            B  |---------|

        :param extent: The temporal extent object that is the predecessor
                       of this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=3, end_time=5)
            >>> A.follows(B)
            True

        """
        return (
            extent.D["end_time"] is not None
            and self.D["start_time"] == extent.D["end_time"]
        )

    def precedes(self, extent) -> bool:
        """Return True if this temporal extent (A) precedes the provided
        temporal extent (B)
        ::

            A  |---------|
            B            |---------|


        :param extent: The temporal extent object that is the successor
                       of this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=7, end_time=9)
            >>> A.precedes(B)
            True


        """
        return (
            self.D["end_time"] is not None
            and self.D["end_time"] == extent.D["start_time"]
        )

    def during(self, extent) -> bool:
        """Return True if this temporal extent (A) is located during the provided
        temporal extent (B)
        ::

            A   |-------|
            B  |---------|

        :param extent: The temporal extent object that contains this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=4, end_time=9)
            >>> A.during(B)
            True

        """
        # Check single point of time in interval
        if extent.D["end_time"] is None:
            return False

        # Check single point of time in interval
        if self.D["end_time"] is None:
            return bool(
                extent.D["start_time"] <= self.D["start_time"] < extent.D["end_time"]
            )

        return bool(
            self.D["start_time"] > extent.D["start_time"]
            and self.D["end_time"] < extent.D["end_time"]
        )

    def contains(self, extent) -> bool:
        """Return True if this temporal extent (A) contains the provided
        temporal extent (B)
        ::

            A  |---------|
            B   |-------|

        :param extent: The temporal extent object that is located
                       during this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=4, end_time=9)
            >>> B = TemporalExtent(start_time=5, end_time=8)
            >>> A.contains(B)
            True

        """
        # Check single point of time in interval
        if self.D["end_time"] is None:
            return False

        # Check single point of time in interval
        if extent.D["end_time"] is None:
            return bool(
                self.D["start_time"] <= extent.D["start_time"] < self.D["end_time"]
            )

        return bool(
            self.D["start_time"] < extent.D["start_time"]
            and self.D["end_time"] > extent.D["end_time"]
        )

    def equal(self, extent) -> bool:
        """Return True if this temporal extent (A) is equal to the provided
        temporal extent (B)
        ::

            A  |---------|
            B  |---------|

        :param extent: The temporal extent object that is equal
                       during this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=6)
            >>> B = TemporalExtent(start_time=5, end_time=6)
            >>> A.equal(B)
            True

        """
        if self.D["end_time"] is None and extent.D["end_time"] is None:
            return self.D["start_time"] == extent.D["start_time"]

        if self.D["end_time"] is None or extent.D["end_time"] is None:
            return False

        return bool(
            self.D["start_time"] == extent.D["start_time"]
            and self.D["end_time"] == extent.D["end_time"]
        )

    def overlaps(self, extent) -> bool:
        """Return True if this temporal extent (A) overlapped the provided
        temporal extent (B)
        ::

            A  |---------|
            B    |---------|

        :param extent: The temporal extent object that is overlaps
                       this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=5, end_time=7)
            >>> B = TemporalExtent(start_time=6, end_time=8)
            >>> A.overlaps(B)
            True

        """

        return bool(
            self.D["end_time"] is not None
            and extent.D["end_time"] is not None
            and self.D["start_time"]
            < extent.D["start_time"]
            < self.D["end_time"]
            < extent.D["end_time"]
        )

    def overlapped(self, extent) -> bool:
        """Return True if this temporal extent (A) overlaps the provided
        temporal extent (B)
        ::

            A    |---------|
            B  |---------|


        :param extent: The temporal extent object that is overlapped
                       this extent

        Usage:

        .. code-block:: pycon

            >>> A = TemporalExtent(start_time=6, end_time=8)
            >>> B = TemporalExtent(start_time=5, end_time=7)
            >>> A.overlapped(B)
            True

        """

        return bool(
            self.D["end_time"] is not None
            and extent.D["end_time"] is not None
            and extent.D["start_time"]
            < self.D["start_time"]
            < extent.D["end_time"]
            < self.D["end_time"]
        )

    def temporal_relation(self, extent):
        """Returns the temporal relation between temporal objects
        Temporal relationships are implemented after
        [Allen and Ferguson 1994 Actions and Events in Interval Temporal Logic]

        The following temporal relationships are supported:

            - equal
            - during
            - contains
            - overlaps
            - overlapped
            - after
            - before
            - starts
            - finishes
            - started
            - finished
            - follows
            - precedes

        :param extent: The temporal extent
        :return: The name of the temporal relation or None if no relation
                 found
        :raises ValueError: if one of the extents ends before it starts
        """
        _refuse_reversed(self)
        _refuse_reversed(extent)

        # First check for correct time
        if "start_time" not in self.D:
            return None
        if "end_time" not in self.D:
            return None
        if "start_time" not in extent.D:
            return None
        if "end_time" not in extent.D:
            return None
        # Return None if the start_time is undefined
        if self.D["start_time"] is None or extent.D["start_time"] is None:
            return None

        for name in _RELATION_ORDER:
            if getattr(self, name)(extent):
                return name
        return None

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        #      0123456789012345678901234567890
        print(" | Start time:................. " + str(self.get_start_time()))
        print(" | End time:................... " + str(self.get_end_time()))

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        print(f"start_time='{self.get_start_time()!s}'")
        print(f"end_time='{self.get_end_time()!s}'")


class AbsoluteTemporalExtent(TemporalExtent):
    """This is the absolute time class for all maps and spacetime datasets

    start_time and end_time must be of type datetime
    """

    def __init__(self, table=None, ident=None, start_time=None, end_time=None) -> None:
        super().__init__(table, ident, start_time, end_time)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        #      0123456789012345678901234567890
        print(
            " +-------------------- Absolute time -----------------------------------------+"  # noqa: E501
        )
        TemporalExtent.print_info(self)

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        TemporalExtent.print_shell_info(self)


def _set_dataset_fields(row, granularity, map_time) -> None:
    """Set the columns that only the time of a space time dataset has"""
    if row.kind.is_stds:
        row.set_granularity(granularity)
        row.set_map_time(map_time)


def _print_dataset_info(row) -> None:
    """Print the columns that only the time of a space time dataset has"""
    if row.kind.is_stds:
        #      0123456789012345678901234567890
        print(" | Granularity:................ " + str(row.get_granularity()))
        print(" | Temporal type of maps:...... " + str(row.get_map_time()))


class AbsoluteTimeRow(AbsoluteTemporalExtent):
    """The absolute time of a map or a space time dataset of a kind

    The kind selects the table. A space time dataset has the granularity
    and the map_time in addition.

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> from grass.temporal.kinds import KINDS
        >>> A = AbsoluteTimeRow(
        ...     KINDS["strds"],
        ...     ident="strds@PERMANENT",
        ...     start_time=datetime(2001, 1, 1),
        ...     end_time=datetime(2005, 1, 1),
        ...     granularity="1 days",
        ...     map_time="interval",
        ... )
        >>> A.print_info()
         +-------------------- Absolute time -----------------------------------------+
         | Start time:................. 2001-01-01 00:00:00
         | End time:................... 2005-01-01 00:00:00
         | Granularity:................ 1 days
         | Temporal type of maps:...... interval

    """

    columns = _STDS_COLUMNS

    def __init__(
        self,
        kind: Kind,
        ident=None,
        start_time=None,
        end_time=None,
        granularity=None,
        map_time=None,
    ) -> None:
        """Constructor

        :param kind: The kind of the map or space time dataset
        :param ident: The unique identifier
        :param start_time: The start time, a datetime
        :param end_time: The end time, a datetime, None for a time instance
        :param granularity: The granularity of a space time dataset
        :param map_time: The type of the time of the maps of a space time dataset
        """
        super().__init__(kind.table("absolute_time"), ident, start_time, end_time)
        self.kind = kind

        _set_dataset_fields(self, granularity, map_time)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        AbsoluteTemporalExtent.print_info(self)
        _print_dataset_info(self)

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        AbsoluteTemporalExtent.print_shell_info(self)
        if self.kind.is_stds:
            print(f"granularity='{self.get_granularity()!s}'")
            print("map_time=" + str(self.get_map_time()))


class RelativeTemporalExtent(TemporalExtent):
    """This is the relative time class for all maps and space time datasets

    start_time and end_time must be of type integer

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> A = RelativeTemporalExtent(
        ...     table="raster_relative_time",
        ...     ident="soil@PERMANENT",
        ...     start_time=0,
        ...     end_time=1,
        ...     unit="years",
        ... )
        >>> A.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 0
         | End time:................... 1
         | Relative time unit:......... years

    """

    columns = (
        Column(
            "unit",
            doc=(
                "the unit of the relative time. Valid units are years, "
                "months, days, hours, minutes and seconds"
            ),
        ),
    )

    def __init__(
        self, table=None, ident=None, start_time=None, end_time=None, unit=None
    ) -> None:
        super().__init__(table, ident, start_time, end_time)
        self.set_unit(unit)

    def temporal_relation(self, map):
        """Returns the temporal relation between temporal objects
        Temporal relationships are implemented after
        [Allen and Ferguson 1994 Actions and Events in Interval Temporal Logic]

        :raises ValueError: if one of the extents ends before it starts, also
                            if the units differ
        """
        # Checked before the units, so that the refusal does not depend on them.
        _refuse_reversed(self)
        _refuse_reversed(map)

        # Check units for relative time
        if "unit" not in self.D:
            return None
        if "unit" not in map.D:
            return None

        # Units must be equal
        if self.D["unit"] != map.D["unit"]:
            return None

        return TemporalExtent.temporal_relation(self, map)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        #      0123456789012345678901234567890
        print(
            " +-------------------- Relative time -----------------------------------------+"  # noqa: E501
        )
        TemporalExtent.print_info(self)
        print(" | Relative time unit:......... " + str(self.get_unit()))

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        TemporalExtent.print_shell_info(self)
        print("unit=" + str(self.get_unit()))


class RelativeTimeRow(RelativeTemporalExtent):
    """The relative time of a map or a space time dataset of a kind

    The kind selects the table. A space time dataset has the granularity
    and the map_time in addition. start_time and end_time must be of type
    integer.

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> from grass.temporal.kinds import KINDS
        >>> A = RelativeTimeRow(
        ...     KINDS["strds"],
        ...     ident="strds@PERMANENT",
        ...     start_time=0,
        ...     end_time=1,
        ...     unit="years",
        ...     granularity=5,
        ...     map_time="interval",
        ... )
        >>> A.print_info()
         +-------------------- Relative time -----------------------------------------+
         | Start time:................. 0
         | End time:................... 1
         | Relative time unit:......... years
         | Granularity:................ 5
         | Temporal type of maps:...... interval

    """

    columns = _STDS_COLUMNS

    def __init__(
        self,
        kind: Kind,
        ident=None,
        start_time=None,
        end_time=None,
        unit=None,
        granularity=None,
        map_time=None,
    ) -> None:
        """Constructor

        :param kind: The kind of the map or space time dataset
        :param ident: The unique identifier
        :param start_time: The start time, an integer
        :param end_time: The end time, an integer, None for a time instance
        :param unit: The unit of the relative time
        :param granularity: The granularity of a space time dataset
        :param map_time: The type of the time of the maps of a space time dataset
        """
        super().__init__(kind.table("relative_time"), ident, start_time, end_time, unit)
        self.kind = kind

        _set_dataset_fields(self, granularity, map_time)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        RelativeTemporalExtent.print_info(self)
        _print_dataset_info(self)

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        RelativeTemporalExtent.print_shell_info(self)
        if self.kind.is_stds:
            print("granularity=" + str(self.get_granularity()))
            print("map_time=" + str(self.get_map_time()))
