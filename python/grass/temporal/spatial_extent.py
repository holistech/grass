"""
Spatial extents classes for map layer and space time datasets

Usage:

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> from grass.temporal.kinds import KINDS
    >>> tgis.init()
    >>> for name in ("raster", "raster3d", "vector", "strds", "str3ds", "stvds"):
    ...     extent = tgis.spatial_extent.SpatialExtentRow(
    ...         KINDS[name],
    ...         ident=f"{name}@PERMANENT",
    ...         north=90,
    ...         south=90,
    ...         east=180,
    ...         west=180,
    ...         top=100,
    ...         bottom=-20,
    ...     )
    ...     print(extent.get_table_name())
    raster_spatial_extent
    raster3d_spatial_extent
    vector_spatial_extent
    strds_spatial_extent
    str3ds_spatial_extent
    stvds_spatial_extent

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .rows import Column, Row

if TYPE_CHECKING:
    from .kinds import Kind


def _optional_float(value) -> float | None:
    """Convert an edge to float, an edge that is not set stays None"""
    return None if value is None else float(value)


def _projections_differ(name: str) -> str:
    """Return the message for the relation name, one whole sentence each

    The method is part of the message id, so that a translation of the
    sentence is found for each of them.
    """
    return {
        "overlapping_2d": _(
            "Projections are different. Unable to compute overlapping_2d "
            "for spatial extents"
        ),
        "is_in_2d": _(
            "Projections are different. Unable to compute is_in_2d for spatial extents"
        ),
        "equivalent_2d": _(
            "Projections are different. Unable to compute equivalent_2d "
            "for spatial extents"
        ),
        "cover_2d": _(
            "Projections are different. Unable to compute cover_2d for spatial extents"
        ),
        "cover": _(
            "Projections are different. Unable to compute cover for spatial extents"
        ),
    }[name]


def _shift_into(west: float, east: float, e_west: float, e_east: float):
    """Shift an interval by whole turns of the globe until it meets the first

    This is how the relations compare longitudes in a LL projection, where an
    extent that crosses the date line has its east edge beyond 180 or its west
    edge below -180. The interval (e_west, e_east) moves up by 360 while it
    lies west of (west, east), then down while it lies east of it.

    :return: The shifted (e_west, e_east)
    """
    while e_east < west:
        e_east += 360.0
        e_west += 360.0

    while e_west > east:
        e_east -= 360.0
        e_west -= 360.0
    return e_west, e_east


class SpatialExtent(Row):
    """This is the spatial extent base class for all maps and space time datasets

    This class implements a three dimensional axis aligned bounding box
    and functions to compute topological relationships

    Usage:

    .. code-block:: pycon

        >>> init()
        >>> extent = SpatialExtent(
        ...     table="raster_spatial_extent",
        ...     ident="soil@PERMANENT",
        ...     north=90,
        ...     south=90,
        ...     east=180,
        ...     west=180,
        ...     top=100,
        ...     bottom=-20,
        ... )
        >>> extent.id
        'soil@PERMANENT'
        >>> extent.north
        90.0
        >>> extent.south
        90.0
        >>> extent.east
        180.0
        >>> extent.west
        180.0
        >>> extent.top
        100.0
        >>> extent.bottom
        -20.0
        >>> extent.print_info()
         +-------------------- Spatial extent ----------------------------------------+
         | North:...................... 90.0
         | South:...................... 90.0
         | East:.. .................... 180.0
         | West:....................... 180.0
         | Top:........................ 100.0
         | Bottom:..................... -20.0
        >>> extent.print_shell_info()
        north=90.0
        south=90.0
        east=180.0
        west=180.0
        top=100.0
        bottom=-20.0

    """

    columns = (
        Column("north", convert=_optional_float, doc="the northern edge of the map"),
        Column("south", convert=_optional_float, doc="the southern edge of the map"),
        Column("east", convert=_optional_float, doc="the eastern edge of the map"),
        Column("west", convert=_optional_float, doc="the western edge of the map"),
        Column("top", convert=_optional_float, doc="the top edge of the map"),
        Column("bottom", convert=_optional_float, doc="the bottom edge of the map"),
    )

    def __init__(
        self,
        table=None,
        ident=None,
        north=None,
        south=None,
        east=None,
        west=None,
        top=None,
        bottom=None,
        proj="XY",
    ) -> None:
        super().__init__(table, ident)
        self.set_id(ident)
        self.set_spatial_extent_from_values(north, south, east, west, top, bottom)
        self.set_projection(proj)

    def overlapping_2d(self, extent) -> bool:
        """Return True if this (A) and the provided spatial extent (B) overlaps
        in two dimensional space.
        Code is lend from wind_overlap.c in lib/gis

        Overlapping includes the spatial relations:

        - contain
        - in
        - cover
        - covered
        - equivalent

        .. code-block:: pycon

            >>> A = SpatialExtent(north=80, south=20, east=60, west=10)
            >>> B = SpatialExtent(north=80, south=20, east=60, west=10)
            >>> A.overlapping_2d(B)
            True

        :param extent: The spatial extent to check overlapping with
        :return: True or False
        """

        return self._overlapping(extent)

    def overlapping(self, extent) -> bool:
        """Return True if this (A) and the provided spatial
        extent (B) overlaps in three dimensional space.

        Overlapping includes the spatial relations:

        - contain
        - in
        - cover
        - covered
        - equivalent

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.overlapping(B)
            True

        :param extent: The spatial extent to check overlapping with
        :return: True or False
        """

        return self._overlapping(extent, 3)

    def intersect_2d(self, extent):
        """Return the two dimensional intersection as spatial_extent
           object or None in case no intersection was found.

        :param extent: The spatial extent to intersect with
        :return: The intersection spatial extent
        """

        if not self.overlapping_2d(extent):
            return None

        return self._merge(extent, 2, inner=True)

    def intersect(self, extent):
        """Return the three dimensional intersection as spatial_extent
        object or None in case no intersection was found.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> C = A.intersect(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=10, bottom=-50, top=50
            ... )
            >>> C = A.intersect(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 40.0
             | South:...................... 30.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-50, top=50
            ... )
            >>> C = A.intersect(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 40.0
             | South:...................... 30.0
             | East:.. .................... 60.0
             | West:....................... 30.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-30, top=50
            ... )
            >>> C = A.intersect(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 40.0
             | South:...................... 30.0
             | East:.. .................... 60.0
             | West:....................... 30.0
             | Top:........................ 50.0
             | Bottom:..................... -30.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-30, top=30
            ... )
            >>> C = A.intersect(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 40.0
             | South:...................... 30.0
             | East:.. .................... 60.0
             | West:....................... 30.0
             | Top:........................ 30.0
             | Bottom:..................... -30.0


        :param extent: The spatial extent to intersect with
        :return: The intersection spatial extent
        """  # noqa: E501

        if not self.overlapping(extent):
            return None

        return self._merge(extent, 3, inner=True)

    def union_2d(self, extent):
        """Return the two dimensional union as spatial_extent
           object or None in case the extents does not overlap or meet.

        :param extent: The spatial extent to create a union with
        :return: The union spatial extent
        """
        if not self.overlapping_2d(extent) and not self.meet_2d(extent):
            return None

        return self.disjoint_union_2d(extent)

    def disjoint_union_2d(self, extent):
        """Return the two dimensional union as spatial_extent.

        :param extent: The spatial extent to create a union with
        :return: The union spatial extent
        """
        return self._merge(extent, 2, inner=False)

    def union(self, extent):
        """Return the three dimensional union as spatial_extent
           object or None in case the extents does not overlap or meet.

        :param extent: The spatial extent to create a union with
        :return: The union spatial extent
        """
        if not self.overlapping(extent) and not self.meet(extent):
            return None

        return self.disjoint_union(extent)

    def disjoint_union(self, extent):
        """Return the three dimensional union as spatial_extent .

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=10, bottom=-50, top=50
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-50, top=50
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-30, top=50
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> B = SpatialExtent(
            ...     north=40, south=30, east=60, west=30, bottom=-30, top=30
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 80.0
             | South:...................... 20.0
             | East:.. .................... 60.0
             | West:....................... 10.0
             | Top:........................ 50.0
             | Bottom:..................... -50.0
            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=80, east=70, west=20, bottom=-30, top=60
            ... )
            >>> C = A.disjoint_union(B)
            >>> C.print_info()
             +-------------------- Spatial extent ----------------------------------------+
             | North:...................... 90.0
             | South:...................... 20.0
             | East:.. .................... 70.0
             | West:....................... 10.0
             | Top:........................ 60.0
             | Bottom:..................... -50.0


        :param extent: The spatial extent to create a disjoint union with
        :return: The union spatial extent
        """  # noqa: E501

        return self._merge(extent, 3, inner=False)

    def is_in_2d(self, extent) -> bool:
        """Return True if this extent (A) is located in the provided spatial
        extent (B) in two dimensions.

        ::

             _____
            |A _  |
            | |_| |
            |_____|B


        :param extent: The spatial extent
        :return: True or False
        """
        return self._is_in(extent, 2)

    def is_in(self, extent) -> bool:
        """Return True if this extent (A) is located in the provided spatial
        extent (B) in three dimensions.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=79, south=21, east=59, west=11, bottom=-49, top=49
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.is_in(B)
            True
            >>> B.is_in(A)
            False

        :param extent: The spatial extent
        :return: True or False
        """
        return self._is_in(extent, 3)

    def contain_2d(self, extent):
        """Return True if this extent (A) contains the provided spatial
        extent (B) in two dimensions.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(north=80, south=20, east=60, west=10)
            >>> B = SpatialExtent(north=79, south=21, east=59, west=11)
            >>> A.contain_2d(B)
            True
            >>> B.contain_2d(A)
            False

        :param extent: The spatial extent
        :return: True or False
        """
        return extent.is_in_2d(self)

    def contain(self, extent):
        """Return True if this extent (A) contains the provided spatial
        extent (B) in three dimensions.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=79, south=21, east=59, west=11, bottom=-49, top=49
            ... )
            >>> A.contain(B)
            True
            >>> B.contain(A)
            False

        :param extent: The spatial extent
        :return: True or False
        """
        return extent.is_in(self)

    def equivalent_2d(self, extent) -> bool:
        """Return True if this extent (A) is equal to the provided spatial
        extent (B) in two dimensions.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(north=80, south=20, east=60, west=10)
            >>> B = SpatialExtent(north=80, south=20, east=60, west=10)
            >>> A.equivalent_2d(B)
            True
            >>> B.equivalent_2d(A)
            True

        :param extent: The spatial extent
        :return: True or False
        """
        return self._equivalent(extent, 2)

    def equivalent(self, extent) -> bool:
        """Return True if this extent (A) is equal to the provided spatial
        extent (B) in three dimensions.

        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.equivalent(B)
            True
            >>> B.equivalent(A)
            True

        :param extent: The spatial extent
        :return: True or False
        """
        return self._equivalent(extent, 3)

    def cover_2d(self, extent) -> bool:
        """Return True if this extent (A) covers the provided spatial
        extent (B) in two dimensions.

        ::

             _____    _____    _____    _____
            |A  __|  |__  A|  |A | B|  |B | A|
            |  |B |  | B|  |  |  |__|  |__|  |
            |__|__|  |__|__|  |_____|  |_____|

             _____    _____    _____    _____
            |A|B| |  |A  __|  |A _  |  |__  A|
            | |_| |  |  |__|B | |B| | B|__|  |
            |_____|  |_____|  |_|_|_|  |_____|

             _____    _____    _____    _____
            |A|B  |  |_____|A |A|B|A|  |_____|A
            | |   |  |B    |  | | | |  |_____|B
            |_|___|  |_____|  |_|_|_|  |_____|A


        The following cases are excluded:

        - contain
        - in
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """
        return self._cover(extent, 2, "cover_2d")

    def cover(self, extent) -> bool:
        """Return True if this extent covers the provided spatial
        extent in three dimensions.

        The following cases are excluded:

        - contain
        - in
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """
        return self._cover(extent, 3, "cover")

    def covered_2d(self, extent):
        """Return True if this extent is covered by the provided spatial
        extent in two dimensions.

        The following cases are excluded:

        - contain
        - in
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """

        return extent.cover_2d(self)

    def covered(self, extent):
        """Return True if this extent is covered by the provided spatial
        extent in three dimensions.

        The following cases are excluded:

        - contain
        - in
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """

        return extent.cover(self)

    def overlap_2d(self, extent) -> bool:
        """Return True if this extent (A) overlaps with the provided spatial
        extent (B) in two dimensions.
        Code is lend from wind_overlap.c in lib/gis

        ::

             _____
            |A  __|__
            |  |  | B|
            |__|__|  |
               |_____|


        The following cases are excluded:

        - contain
        - in
        - cover
        - covered
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """
        return self._overlap(extent, 2)

    def overlap(self, extent) -> bool:
        """Return True if this extent overlaps with the provided spatial
        extent in three dimensions.

        The following cases are excluded:

        - contain
        - in
        - cover
        - covered
        - equivalent

        :param extent: The spatial extent
        :return: True or False
        """
        return self._overlap(extent, 3)

    def meet_2d(self, extent) -> bool:
        """Return True if this extent (A) meets with the provided spatial
        extent (B) in two dimensions.

        ::

              _____ _____
             |  A  |  B  |
             |_____|     |
                   |_____|
              _____ _____
             |  B  |  A  |
             |     |     |
             |_____|_____|
               ___
              | A |
              |   |
              |___|
             |  B  |
             |     |
             |_____|
              _____
             |  B  |
             |     |
             |_____|_
               |  A  |
               |     |
               |_____|


        :param extent: The spatial extent
        :return: True or False
        """
        return self._meet(extent, 2)

    def meet(self, extent) -> bool:
        """Return True if this extent meets with the provided spatial
        extent in three dimensions.

        :param extent: The spatial extent
        :return: True or False
        """
        return self._meet(extent, 3)

    def disjoint_2d(self, extent) -> bool:
        """Return True if this extent (A) is disjoint with the provided spatial
        extent (B) in three dimensions.

        ::

              _____
             |  A  |
             |_____|
             _______
            |   B   |
            |_______|


        :param extent: The spatial extent
        :return: True or False
        """
        return self._disjoint(extent, "_2d")

    def disjoint(self, extent) -> bool:
        """Return True if this extent is disjoint with the provided spatial
        extent in three dimensions.

        :param extent: The spatial extent
        :return: True or False
        """
        return self._disjoint(extent, "")

    def _check_projection(self, extent, name: str) -> bool:
        """Return False and report it if the projections of the extents differ

        :param name: The method named in the message
        """
        if self.get_projection() != extent.get_projection():
            self.msgr.error(_projections_differ(name))
            return False
        return True

    def _overlapping(self, extent, dims: int = 2) -> bool:
        """Tell whether the extents share a volume or an area, see overlapping_2d()

        The message of a difference of projections names the 2D method also for
        three dimensions, because the 3D method has always asked the 2D one
        first.
        """
        if not self._check_projection(extent, "overlapping_2d"):
            return False
        mine, theirs = self._intervals(extent, dims)
        return not any(
            high <= e_low or low >= e_high
            for (low, high), (e_low, e_high) in zip(mine, theirs, strict=True)
        )

    def _is_in(self, extent, dims: int) -> bool:
        """Tell whether this extent lies strictly inside the other, see is_in_2d()"""
        if not self._check_projection(extent, "is_in_2d"):
            return False
        mine, theirs = self._intervals(extent, dims)
        return not any(
            e_low >= low or e_high <= high
            for (low, high), (e_low, e_high) in zip(mine, theirs, strict=True)
        )

    def _equivalent(self, extent, dims: int) -> bool:
        """Tell whether both extents have the same edges, see equivalent_2d()"""
        if not self._check_projection(extent, "equivalent_2d"):
            return False
        mine, theirs = self._intervals(extent, dims)
        return not any(
            e_low != low or e_high != high
            for (low, high), (e_low, e_high) in zip(mine, theirs, strict=True)
        )

    def _merge(self, extent, dims: int, inner: bool):
        """Return the intersection (inner) or the bounding union of both extents

        The caller has decided that the relation is allowed. A result in two
        dimensions has top and bottom 0, as it always had.
        """
        mine, theirs = self._intervals(extent, dims)
        first, second = (max, min) if inner else (min, max)
        (west, east), (south, north), *vertical = (
            (first(low, e_low), second(high, e_high))
            for (low, high), (e_low, e_high) in zip(mine, theirs, strict=True)
        )
        bottom, top = vertical[0] if vertical else (0, 0)
        return SpatialExtent(
            north=north,
            south=south,
            east=east,
            west=west,
            top=top,
            bottom=bottom,
            proj=self.get_projection(),
        )

    def _disjoint(self, extent, suffix: str) -> bool:
        """Tell whether none of the other relations holds, suffix is "_2d" or an empty string"""
        return not any(
            getattr(self, name + suffix)(extent)
            for name in (
                "is_in",
                "contain",
                "cover",
                "covered",
                "equivalent",
                "overlapping",
                "meet",
            )
        )

    def _relation(self, extent, suffix: str) -> str:
        """Return the name of the relation, suffix is "_2d" or an empty string"""
        for name, relation in (
            ("equivalent", "equivalent"),
            ("contain", "contain"),
            ("is_in", "in"),
            ("cover", "cover"),
            ("covered", "covered"),
            ("overlap", "overlap"),
            ("meet", "meet"),
            ("disjoint", "disjoint"),
        ):
            if getattr(self, name + suffix)(extent):
                return relation
        return "unknown"

    def _intervals(self, extent, dims: int):
        """Return the intervals (low, high) of both extents on the first axes

        The axes are east-west, north-south and bottom-top, and dims says how
        many are used. On the east-west axis of a LL projection the interval of
        the other extent is shifted by whole turns until it meets this one.

        :return: The intervals of this extent and the intervals of the other
        """
        mine = [
            (self.get_west(), self.get_east()),
            (self.get_south(), self.get_north()),
            (self.get_bottom(), self.get_top()),
        ][:dims]
        theirs = [
            (extent.get_west(), extent.get_east()),
            (extent.get_south(), extent.get_north()),
            (extent.get_bottom(), extent.get_top()),
        ][:dims]
        if self.get_projection() == "LL":
            theirs[0] = _shift_into(*mine[0], *theirs[0])
        return mine, theirs

    def _cover(self, extent, dims: int, name: str) -> bool:
        """Tell whether this extent covers the other in dims dimensions

        The relation is explained at cover_2d(). A pair that is equivalent in
        two dimensions is excluded in three, too: the exclusion has always
        looked at the plane only, which the recordings of the relation keep.

        :param name: The method that reports a difference of the projections
        """
        if not self._check_projection(extent, name):
            return False

        # Exclude equivalent_2d
        if self.equivalent_2d(extent):
            return False

        mine, theirs = self._intervals(extent, dims)
        pairs = list(zip(mine, theirs, strict=True))

        # Edges of extent located outside of self are not allowed
        if any(
            e_low >= high or e_high <= low for (low, high), (e_low, e_high) in pairs
        ):
            return False

        # First we check that at least one edge of extent meets an edge of self
        if all(
            e_low != low and e_high != high for (low, high), (e_low, e_high) in pairs
        ):
            return False

        # We check that at least one edge of extent is located in self
        return any(
            low < edge < high
            for (low, high), (e_low, e_high) in pairs
            for edge in (e_low, e_high)
        )

    def _overlap(self, extent, dims: int) -> bool:
        """Tell whether this extent overlaps the other in dims dimensions

        The relation is explained at overlap_2d(): the other relations are
        excluded, then what is left must share a volume.
        """
        # The order differs between the two, which changes nothing but the
        # order of the messages about different projections.
        names = (
            ("contain", "is_in", "cover", "covered", "equivalent")
            if dims == 2
            else ("is_in", "contain", "cover", "covered", "equivalent")
        )
        suffix = "_2d" if dims == 2 else ""
        if any(getattr(self, name + suffix)(extent) for name in names):
            return False

        mine, theirs = self._intervals(extent, dims)
        return not any(
            high <= e_low or low >= e_high
            for (low, high), (e_low, e_high) in zip(mine, theirs, strict=True)
        )

    def _meet(self, extent, dims: int) -> bool:
        """Tell whether this extent meets the other in dims dimensions

        They meet when exactly one face of one lies on a face of the other and
        the two overlap or touch on every other axis.
        """
        mine, theirs = self._intervals(extent, dims)
        faces = [
            axis
            for axis, ((low, high), (e_low, e_high)) in enumerate(
                zip(mine, theirs, strict=True)
            )
            for touching in (e_low == high, e_high == low)
            if touching
        ]
        # Meet a single face only
        if len(faces) != 1:
            return False
        # Check boundaries of the faces
        return not any(
            e_low > high or e_high < low
            for axis, ((low, high), (e_low, e_high)) in enumerate(
                zip(mine, theirs, strict=True)
            )
            if axis != faces[0]
        )

    def spatial_relation_2d(
        self, extent
    ) -> Literal[
        "equivalent",
        "contain",
        "in",
        "cover",
        "covered",
        "overlap",
        "meet",
        "disjoint",
        "unknown",
    ]:
        """Returns the two dimensional spatial relation between this
        extent and the provided spatial extent in two dimensions.

        Spatial relations are:

        - disjoint
        - meet
        - overlap
        - cover
        - covered
        - in
        - contain
        - equivalent

        Usage: see self.spatial_relation()
        """
        return self._relation(extent, "_2d")

    def spatial_relation(
        self, extent
    ) -> Literal[
        "equivalent",
        "contain",
        "in",
        "cover",
        "covered",
        "overlap",
        "meet",
        "disjoint",
        "unknown",
    ]:
        """Returns the two dimensional spatial relation between this
        extent and the provided spatial extent in three dimensions.

        Spatial relations are:

        - disjoint
        - meet
        - overlap
        - cover
        - covered
        - in
        - contain
        - equivalent


        Usage:

        .. code-block:: pycon

            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation(B)
            'equivalent'
            >>> B.spatial_relation(A)
            'equivalent'
            >>> B = SpatialExtent(
            ...     north=70, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'cover'
            >>> A.spatial_relation(B)
            'cover'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'cover'
            >>> A.spatial_relation(B)
            'cover'
            >>> B.spatial_relation_2d(A)
            'covered'
            >>> B.spatial_relation(A)
            'covered'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'cover'
            >>> B.spatial_relation_2d(A)
            'covered'
            >>> A.spatial_relation(B)
            'cover'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=20, bottom=-50, top=50
            ... )
            >>> B.spatial_relation(A)
            'covered'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=20, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'contain'
            >>> A.spatial_relation(B)
            'cover'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=20, bottom=-40, top=50
            ... )
            >>> A.spatial_relation(B)
            'cover'
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=20, bottom=-40, top=40
            ... )
            >>> A.spatial_relation(B)
            'contain'
            >>> B.spatial_relation(A)
            'in'
            >>> B = SpatialExtent(
            ...     north=90, south=30, east=50, west=20, bottom=-40, top=40
            ... )
            >>> A.spatial_relation_2d(B)
            'overlap'
            >>> A.spatial_relation(B)
            'overlap'
            >>> B = SpatialExtent(
            ...     north=90, south=5, east=70, west=5, bottom=-40, top=40
            ... )
            >>> A.spatial_relation_2d(B)
            'in'
            >>> A.spatial_relation(B)
            'overlap'
            >>> B = SpatialExtent(
            ...     north=90, south=5, east=70, west=5, bottom=-40, top=60
            ... )
            >>> A.spatial_relation(B)
            'overlap'
            >>> B = SpatialExtent(
            ...     north=90, south=5, east=70, west=5, bottom=-60, top=60
            ... )
            >>> A.spatial_relation(B)
            'in'
            >>> A = SpatialExtent(
            ...     north=80, south=60, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=60, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=60, south=40, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=60, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=40, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=30, east=60, west=40, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=70, south=50, east=60, west=40, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=60, south=20, east=60, west=40, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'meet'
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=40, south=20, east=60, west=40, bottom=-50, top=50
            ... )
            >>> A.spatial_relation_2d(B)
            'disjoint'
            >>> A.spatial_relation(B)
            'disjoint'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=60, south=20, east=60, west=40, bottom=-60, top=60
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=40, west=20, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=30, east=60, west=40, bottom=-40, top=40
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=50, east=60, west=30, bottom=-50, top=0
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=70, south=50, east=50, west=30, bottom=-50, top=0
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=30, east=70, west=10, bottom=-50, top=0
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=10, bottom=-50, top=0
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=0, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> B = SpatialExtent(
            ...     north=80, south=50, east=60, west=30, bottom=0, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> B = SpatialExtent(
            ...     north=70, south=50, east=50, west=30, bottom=0, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=30, east=70, west=10, bottom=0, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=40, east=60, west=20, bottom=-50, top=0
            ... )
            >>> B = SpatialExtent(
            ...     north=70, south=30, east=50, west=10, bottom=0, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'
            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=81, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation(B)
            'disjoint'
            >>> A = SpatialExtent(
            ...     north=80, south=20, east=60, west=10, bottom=-50, top=50
            ... )
            >>> B = SpatialExtent(
            ...     north=90, south=80, east=60, west=10, bottom=-50, top=50
            ... )
            >>> A.spatial_relation(B)
            'meet'

        """
        return self._relation(extent, "")

    def set_spatial_extent_from_values(
        self, north, south, east, west, top, bottom
    ) -> None:
        """Set the three dimensional spatial extent

        :param north: The northern edge
        :param south: The southern edge
        :param east: The eastern edge
        :param west: The western edge
        :param top: The top edge
        :param bottom: The bottom edge
        """

        self.set_north(north)
        self.set_south(south)
        self.set_east(east)
        self.set_west(west)
        self.set_top(top)
        self.set_bottom(bottom)

    def set_spatial_extent(self, spatial_extent) -> None:
        """Set the three dimensional spatial extent

        :param spatial_extent: An object of type SpatialExtent or its subclasses
        """

        self.set_north(spatial_extent.get_north())
        self.set_south(spatial_extent.get_south())
        self.set_east(spatial_extent.get_east())
        self.set_west(spatial_extent.get_west())
        self.set_top(spatial_extent.get_top())
        self.set_bottom(spatial_extent.get_bottom())

    def set_projection(self, proj) -> None:
        """Set the projection of the spatial extent it should be XY or LL.
        As default the projection is XY
        """
        if proj is None or (proj not in {"XY", "LL"}):
            self.D["proj"] = "XY"
        else:
            self.D["proj"] = proj

    def get_projection(self):
        """Get the projection of the spatial extent"""
        return self.D["proj"]

    def get_area(self):
        """Compute the area of the extent, extent in z direction is ignored"""

        if self.get_projection() == "LL":
            self.msgr.error(_("Area computation is not supported for LL projections"))

        bbox = self.get_spatial_extent_as_tuple()

        y = abs(bbox[0] - bbox[1])
        x = abs(bbox[2] - bbox[3])

        return x * y

    def get_spatial_extent_as_tuple(self):
        """Return a tuple (north, south, east, west, top, bottom)
        of the spatial extent"""

        return (self.north, self.south, self.east, self.west, self.top, self.bottom)

    def print_info(self) -> None:
        """Print information about this class in human readable style"""
        #      0123456789012345678901234567890
        print(
            " +-------------------- Spatial extent ----------------------------------------+"  # noqa: E501
        )
        print(" | North:...................... " + str(self.get_north()))
        print(" | South:...................... " + str(self.get_south()))
        print(" | East:.. .................... " + str(self.get_east()))
        print(" | West:....................... " + str(self.get_west()))
        print(" | Top:........................ " + str(self.get_top()))
        print(" | Bottom:..................... " + str(self.get_bottom()))

    def print_shell_info(self) -> None:
        """Print information about this class in shell style"""
        print("north=" + str(self.get_north()))
        print("south=" + str(self.get_south()))
        print("east=" + str(self.get_east()))
        print("west=" + str(self.get_west()))
        print("top=" + str(self.get_top()))
        print("bottom=" + str(self.get_bottom()))


class SpatialExtentRow(SpatialExtent):
    """The spatial extent of a map or a space time dataset of a kind

    The kind selects the table. The projection is XY until it is set.
    """

    def __init__(
        self,
        kind: Kind,
        ident=None,
        north=None,
        south=None,
        east=None,
        west=None,
        top=None,
        bottom=None,
    ) -> None:
        super().__init__(
            kind.table("spatial_extent"),
            ident,
            north,
            south,
            east,
            west,
            top,
            bottom,
        )
        self.kind = kind


if __name__ == "__main__":
    import doctest

    doctest.testmod()
