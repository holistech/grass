"""
Topology of datasets: the links a map keeps to its related maps and the
builder that finds them

A map links to the maps it is temporally and spatially related to. The
relations come in pairs, because A follows B exactly when B precedes A; the
tables INVERSE_TEMPORAL_RELATION and INVERSE_SPATIAL_RELATION hold the pairs and
are the only place that knows them. The SpatioTemporalTopologyBuilder finds the
related maps of one or two lists of maps with an R*-tree and enters the links.

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.print_temporal_relations(maps)


SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import copy
from datetime import datetime

from grass.lib import gis, rtree, vector

from .datetime_math import time_delta_to_relative_time_seconds
from .db import connection

# The temporal relations of a map to another map, each with the relation the
# other map has to it. The order is the one of the counts of the relations.
INVERSE_TEMPORAL_RELATION = {
    "equal": "equal",
    "follows": "precedes",
    "precedes": "follows",
    "overlaps": "overlapped",
    "overlapped": "overlaps",
    "during": "contains",
    "contains": "during",
    "starts": "started",
    "started": "starts",
    "finishes": "finished",
    "finished": "finishes",
}

# The same for the spatial relations
INVERSE_SPATIAL_RELATION = {
    "equivalent": "equivalent",
    "overlap": "overlap",
    "in": "contain",
    "contain": "in",
    "meet": "meet",
    "cover": "covered",
    "covered": "cover",
}

# A map that starts or finishes another one is during it, too, and a map that
# is started or finished by another one contains it. The relation is entered
# after the one it implies, which fixes the order of the keys of the map.
_IMPLIED_RELATION = {
    "starts": "during",
    "finishes": "during",
    "started": "contains",
    "finished": "contains",
}

# What the printed topology shows, in its order: the name of the relation
# and the text before the list of maps. The two kinds of output differ in
# the wording only, the shell output has the name and an equals sign.
_TEMPORAL_PRINT = (
    ("equal", " | Equal:...................... "),
    ("follows", " | Follows: ................... "),
    ("precedes", " | Precedes: .................. "),
    ("overlaps", " | Overlaps: .................. "),
    ("overlapped", " | Overlapped: ................ "),
    ("during", " | During: .................... "),
    ("contains", " | Contains: .................. "),
    ("starts", " | Starts:.. .................. "),
    ("started", " | Started:. .................. "),
    ("finishes", " | Finishes:................... "),
    ("finished", " | Finished:................... "),
)
_SPATIAL_PRINT = (
    ("equivalent", " | Equivalent: ................ "),
    ("cover", " | Cover: ..................... "),
    ("covered", " | Covered: ................... "),
    ("overlap", " | Overlap: ................... "),
    ("in", " | In: ........................ "),
    ("contain", " | Contain: ................... "),
    ("meet", " | Meet: ...................... "),
)


def map_list_string(map_list, line_wrap: bool = True) -> str:
    """Return the identifiers of the maps, three per line if line_wrap is set"""
    count = 0
    string = ""
    for map_ in map_list:
        if line_wrap and count > 0 and (count % 3 == 0):
            string += "\n | ............................ "
            count = 0
        if count == 0:
            string += map_.get_id()
        else:
            string += ",%s" % map_.get_id()
        count += 1

    return string


def _temporal_getter(relation: str):
    """Return the method that returns the maps of a temporal relation"""

    def getter(self):
        return self._links["temporal"].get(relation.upper())

    getter.__name__ = f"get_{relation}"
    getter.__doc__ = f"""Return the list of maps this map has the relation "{relation}" to

    :return: A list of map objects or None
    """
    return getter


class TopologyLinks:
    """The links of a map to the maps it is temporally and spatially related to

    The links are set up by the SpatioTemporalTopologyBuilder. Two maps are
    equal only if they are the same object, whatever their identifiers say,
    so a map is linked once per relation and object. The links keep the order
    in which they were entered, and so do the keys of the relation
    dictionaries.

    If the temporal topology is built, next() and prev() let the user walk
    forward and backward in time:

    .. code-block:: python

        # We have build the temporal topology and we know the first map
        start = first
        while start:
            # Print all maps this map temporally contains
            for map in start.get_contains() or []:
                map.print_info()

            start = start.next()

    .. code-block:: pycon

        >>> import grass.temporal as tgis
        >>> tgis.init()
        >>> a = tgis.RasterDataset("a@P")
        >>> b = tgis.RasterDataset("b@P")
        >>> set_temporal_relationship(a, b, "starts")
        >>> set_spatial_relationship(a, b, "cover")
        >>> [m.get_id() for m in b.get_during()]
        ['a@P']
        >>> [m.get_id() for m in a.get_temporal_relations()["CONTAINS"]]
        ['b@P']
        >>> print_temporal_topology_info(b)
         +-------------------- Temporal Topology -------------------------------------+
         | During: .................... a@P
         | Starts:.. .................. a@P
        >>> print_temporal_topology_shell_info(a)
        contains=b@P
        started=b@P
        >>> print_spatial_topology_shell_info(a)
        covered=b@P
        >>> b.set_next(a)
        >>> sorted(b.get_temporal_relations())
        ['DURING', 'NEXT', 'STARTS']
    """

    def __init__(self) -> None:
        self.reset_topology()

    def reset_topology(self) -> None:
        """Reset any information about the temporal and spatial topology"""
        # Per scope the relation lists by name in upper case, for the temporal
        # topology with the maps NEXT and PREV among them, and per relation
        # the set of the maps in the list for the check whether a map is
        # linked already. Plain containers, so that copy and pickle work.
        self._links = {"temporal": {}, "spatial": {}}
        self._members = {"temporal": {}, "spatial": {}}
        self._built = {"temporal": False, "spatial": False}

    def _link(self, scope: str, relation: str, map_) -> None:
        """Append a map to the list of a relation, unless it is linked already"""
        key = relation.upper()
        members = self._members[scope].setdefault(key, set())
        if map_ in members:
            return
        members.add(map_)
        self._links[scope].setdefault(key, []).append(map_)

    def get_temporal_relations(self):
        """Return the dictionary of temporal relationships

        Keys are the temporal relationships in upper case,
        values are lists of abstract map objects. The maps of next() and
        prev() are entered as NEXT and PREV.

        :return: The temporal relations dictionary
        """
        return copy.copy(self._links["temporal"])

    def get_spatial_relations(self):
        """Return the dictionary of spatial relationships

        Keys are the spatial relationships in upper case,
        values are lists of abstract map objects.

        :return: The spatial relations dictionary
        """
        return copy.copy(self._links["spatial"])

    def _number_of(self, scope: str, relations):
        """Return the number of links per relation, None if not built"""
        if not self._built[scope]:
            return None
        return {
            name: len(self._links[scope].get(name.upper(), ())) for name in relations
        }

    def get_number_of_temporal_relations(self):
        """Return a dictionary in which the keys are the relation names and
        the value are the number of relations.

        The following relations are available:

        - equal
        - follows
        - precedes
        - overlaps
        - overlapped
        - during (including starts, finishes)
        - contains (including started, finished)
        - starts
        - started
        - finishes
        - finished

        To access topological information the temporal topology must be build
        first using the SpatioTemporalTopologyBuilder.

        :return: the dictionary with relations as keys and number as values
                 or None in case the topology wasn't build
        """
        return self._number_of("temporal", INVERSE_TEMPORAL_RELATION)

    def get_number_of_spatial_relations(self):
        """Return a dictionary in which the keys are the relation names and the value
        are the number of relations.

        The following relations are available:

        - equivalent
        - overlap
        - in
        - contain
        - meet
        - cover
        - covered

        To access topological information the spatial topology must be
        build first using the SpatioTemporalTopologyBuilder.

        :return: the dictionary with relations as keys and number as
                 values or None in case the topology wasn't build
        """
        return self._number_of("spatial", INVERSE_SPATIAL_RELATION)

    def set_temporal_topology_build_true(self) -> None:
        """Same as name"""
        self._built["temporal"] = True

    def set_temporal_topology_build_false(self) -> None:
        """Same as name"""
        self._built["temporal"] = False

    def is_temporal_topology_build(self):
        """Check if the temporal topology was build"""
        return self._built["temporal"]

    def set_spatial_topology_build_true(self) -> None:
        """Same as name"""
        self._built["spatial"] = True

    def set_spatial_topology_build_false(self) -> None:
        """Same as name"""
        self._built["spatial"] = False

    def is_spatial_topology_build(self):
        """Check if the spatial topology was build"""
        return self._built["spatial"]

    def set_next(self, map) -> None:
        """Set the map that is temporally as closest located after this map.

        Temporally located means that the start time of the "next" map is
        temporally located AFTER the start time of this map, but temporally
        near than other maps of the same dataset.

        :param map: This object should be of type AbstractMapDataset
                    or derived classes
        """
        self._links["temporal"]["NEXT"] = map

    def set_prev(self, map) -> None:
        """Set the map that is temporally as closest located before this map.

        Temporally located means that the start time of the "previous" map
        is temporally located BEFORE the start time of this map, but
        temporally near than other maps of the same dataset.

        :param map: This object should be of type AbstractMapDataset
                    or derived classes
        """
        self._links["temporal"]["PREV"] = map

    def next(self):
        """Return the map with a start time temporally located after
        the start time of this map, but temporal closer than other maps

        :return: A map object or None
        """
        return self._links["temporal"].get("NEXT")

    def prev(self):
        """Return the map with a start time temporally located before
        the start time of this map, but temporal closer than other maps

        :return: A map object or None
        """
        return self._links["temporal"].get("PREV")

    get_equal = _temporal_getter("equal")
    get_follows = _temporal_getter("follows")
    get_precedes = _temporal_getter("precedes")
    get_overlaps = _temporal_getter("overlaps")
    get_overlapped = _temporal_getter("overlapped")
    get_during = _temporal_getter("during")
    get_contains = _temporal_getter("contains")
    get_starts = _temporal_getter("starts")

    # The only accessor that is a property: the public contract names it.
    contains = property(get_contains)


def _print_header(scope: str) -> None:
    """Print the title line of the human readable topology"""
    if scope == "temporal":
        print(
            " +-------------------- Temporal Topology -------------------------------------+"  # noqa: E501
        )
    else:
        print(
            " +-------------------- Spatial Topology --------------------------------------+"  # noqa: E501
        )


def print_temporal_topology_info(map_) -> None:
    """Print the temporal topology of a map in human readable style"""
    _print_header("temporal")
    #          0123456789012345678901234567890
    if map_.next() is not None:
        print(" | Next: ...................... " + str(map_.next().get_id()))
    if map_.prev() is not None:
        print(" | Previous: .................. " + str(map_.prev().get_id()))
    links = map_.get_temporal_relations()
    for name, text in _TEMPORAL_PRINT:
        if name.upper() in links:
            print(text + map_list_string(links[name.upper()]))


def print_temporal_topology_shell_info(map_) -> None:
    """Print the temporal topology of a map in shell style"""
    if map_.next() is not None:
        print("next=" + map_.next().get_id())
    if map_.prev() is not None:
        print("prev=" + map_.prev().get_id())
    links = map_.get_temporal_relations()
    for name, _text in _TEMPORAL_PRINT:
        if name.upper() in links:
            print(f"{name}=" + map_list_string(links[name.upper()], False))


def print_spatial_topology_info(map_) -> None:
    """Print the spatial topology of a map in human readable style"""
    _print_header("spatial")
    #          0123456789012345678901234567890
    links = map_.get_spatial_relations()
    for name, text in _SPATIAL_PRINT:
        if name.upper() in links:
            print(text + map_list_string(links[name.upper()]))


def print_spatial_topology_shell_info(map_) -> None:
    """Print the spatial topology of a map in shell style"""
    links = map_.get_spatial_relations()
    for name, _text in _SPATIAL_PRINT:
        if name.upper() in links:
            print(f"{name}=" + map_list_string(links[name.upper()], False))


def _start_time(map_):
    """Return the start time of a map, the key to sort maps chronologically"""
    return map_.get_temporal_extent_as_tuple()[0]


class SpatioTemporalTopologyBuilder:
    """This class is designed to build the spatio-temporal topology
    of spatio-temporally related abstract dataset objects.

    The abstract dataset objects must be provided as a single list, or in
    two lists.

    :Example:
      .. code-block:: python

        # We have a space time raster dataset and build a map list
        # from all registered maps ordered by start time
        maps = strds.get_registered_maps_as_objects()

        # Now lets build the temporal topology of the maps in the list

        tb = SpatioTemporalTopologyBuilder()

        tb.build(maps)

        dbif, connection_state_changed = init_dbif(None)

        for map in tb:
            map.select(dbif)
            map.print_info()

        # Same can be done with the existing map list
        # But be aware that this is might not be temporally ordered
        for map in maps:
            map.select(dbf)
            map.print_info()

        # Using the next and previous methods, we can iterate over the
        # topological related maps in this way

        first = tb.get_first()

        while first:
            first.print_topology_info()
            first = first.next()

        # Dictionary like accessed
        map = tb["name@mapset"]

      .. code-block:: pycon

        >>> # Example with two lists of maps
        >>> import grass.temporal as tgis
        >>> import datetime
        >>> # Create two list of maps with equal time stamps
        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     check = mapA.set_relative_time(i, i + 1, "months")
        ...     check = mapB.set_relative_time(i, i + 1, "months")
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     if map.get_equal():
        ...         relations = map.get_equal()
        ...         print(
        ...             "Map %s has equal relation to map %s"
        ...             % (map.get_name(), relations[0].get_name())
        ...         )
        Map a0 has equal relation to map b0
        Map a1 has equal relation to map b1
        Map a2 has equal relation to map b2
        Map a3 has equal relation to map b3
        >>> # Check relations of mapsB
        >>> for map in mapsB:
        ...     if map.get_equal():
        ...         relations = map.get_equal()
        ...         print(
        ...             "Map %s has equal relation to map %s"
        ...             % (map.get_name(), relations[0].get_name())
        ...         )
        Map b0 has equal relation to map a0
        Map b1 has equal relation to map a1
        Map b2 has equal relation to map a2
        Map b3 has equal relation to map a3


        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     check = mapA.set_relative_time(i, i + 1, "months")
        ...     check = mapB.set_relative_time(i + 1, i + 2, "months")
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (0, 1)
        ('PRECEDES', (1, 2))
        (1, 2)
        ('EQUAL', (1, 2))
        ('PRECEDES', (2, 3))
        (2, 3)
        ('EQUAL', (2, 3))
        ('FOLLOWS', (1, 2))
        ('PRECEDES', (3, 4))
        (3, 4)
        ('EQUAL', (3, 4))
        ('FOLLOWS', (2, 3))
        ('PRECEDES', (4, 5))

        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     start = datetime.datetime(2000 + i, 1, 1)
        ...     end = datetime.datetime(2000 + i + 1, 1, 1)
        ...     check = mapA.set_absolute_time(start, end)
        ...     start = datetime.datetime(2000 + i + 1, 1, 1)
        ...     end = datetime.datetime(2000 + i + 2, 1, 1)
        ...     check = mapB.set_absolute_time(start, end)
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0))
        ('PRECEDES', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0)))
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0))
        ('EQUAL', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0))
        ('EQUAL', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('FOLLOWS', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0))
        ('EQUAL', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('FOLLOWS', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2004, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))

        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     start = datetime.datetime(2000 + i, 1, 1)
        ...     end = datetime.datetime(2000 + i + 1, 1, 1)
        ...     check = mapA.set_absolute_time(start, end)
        ...     start = datetime.datetime(2000 + i, 1, 1)
        ...     end = datetime.datetime(2000 + i + 3, 1, 1)
        ...     check = mapB.set_absolute_time(start, end)
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2001, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('FINISHES', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2006, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('FINISHES', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('FOLLOWS', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2006, 1, 1, 0, 0)))

        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     start = datetime.datetime(2000 + i, 1, 1)
        ...     end = datetime.datetime(2000 + i + 2, 1, 1)
        ...     check = mapA.set_absolute_time(start, end)
        ...     start = datetime.datetime(2000 + i, 1, 1)
        ...     end = datetime.datetime(2000 + i + 3, 1, 1)
        ...     check = mapB.set_absolute_time(start, end)
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2002, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('OVERLAPS', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('FINISHES', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('OVERLAPS', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        ('PRECEDES', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2006, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('FINISHES', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('OVERLAPS', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2006, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0))
        ('DURING', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        ('FINISHES', (datetime.datetime(2002, 1, 1, 0, 0), datetime.datetime(2005, 1, 1, 0, 0)))
        ('FOLLOWS', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2003, 1, 1, 0, 0)))
        ('OVERLAPPED', (datetime.datetime(2001, 1, 1, 0, 0), datetime.datetime(2004, 1, 1, 0, 0)))
        ('STARTS', (datetime.datetime(2003, 1, 1, 0, 0), datetime.datetime(2006, 1, 1, 0, 0)))

        >>> mapsA = []
        >>> mapsB = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     idB = "b%i@B" % (i)
        ...     mapB = tgis.RasterDataset(idB)
        ...     start = datetime.datetime(2000, 1, 1, 0, 0, i)
        ...     end = datetime.datetime(2000, 1, 1, 0, 0, i + 2)
        ...     check = mapA.set_absolute_time(start, end)
        ...     start = datetime.datetime(2000, 1, 1, 0, 0, i + 1)
        ...     end = datetime.datetime(2000, 1, 1, 0, 0, i + 3)
        ...     check = mapB.set_absolute_time(start, end)
        ...     mapsA.append(mapA)
        ...     mapsB.append(mapB)
        >>> # Build the topology between the two map lists
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA, mapsB, None)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 1, 0, 0, 2))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('PRECEDES', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3))
        ('EQUAL', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        ('PRECEDES', (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5)))
        (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4))
        ('EQUAL', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5)))
        ('PRECEDES', (datetime.datetime(2000, 1, 1, 0, 0, 4), datetime.datetime(2000, 1, 1, 0, 0, 6)))
        (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5))
        ('EQUAL', (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5)))
        ('FOLLOWS', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 4), datetime.datetime(2000, 1, 1, 0, 0, 6)))

        >>> mapsA = []
        >>> for i in range(4):
        ...     idA = "a%i@B" % (i)
        ...     mapA = tgis.RasterDataset(idA)
        ...     start = datetime.datetime(2000, 1, 1, 0, 0, i)
        ...     end = datetime.datetime(2000, 1, 1, 0, 0, i + 2)
        ...     check = mapA.set_absolute_time(start, end)
        ...     mapsA.append(mapA)
        >>> tb = SpatioTemporalTopologyBuilder()
        >>> tb.build(mapsA)
        >>> # Check relations of mapsA
        >>> for map in mapsA:
        ...     print(map.get_temporal_extent_as_tuple())
        ...     m = map.get_temporal_relations()
        ...     for key in sorted(m.keys()):
        ...         if key not in ["NEXT", "PREV"]:
        ...             print((key, m[key][0].get_temporal_extent_as_tuple()))
        (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 1, 0, 0, 2))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('PRECEDES', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 1, 0, 0, 2)))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))
        ('PRECEDES', (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5)))
        (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4))
        ('FOLLOWS', (datetime.datetime(2000, 1, 1, 0, 0), datetime.datetime(2000, 1, 1, 0, 0, 2)))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('OVERLAPS', (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5)))
        (datetime.datetime(2000, 1, 1, 0, 0, 3), datetime.datetime(2000, 1, 1, 0, 0, 5))
        ('FOLLOWS', (datetime.datetime(2000, 1, 1, 0, 0, 1), datetime.datetime(2000, 1, 1, 0, 0, 3)))
        ('OVERLAPPED', (datetime.datetime(2000, 1, 1, 0, 0, 2), datetime.datetime(2000, 1, 1, 0, 0, 4)))

    """

    def __init__(self) -> None:
        self._reset()
        # 0001-01-01 00:00:00
        self._timeref = datetime(1, 1, 1)

    def _reset(self) -> None:
        self._store = {}
        self._first = None

    def _detect_first(self) -> None:
        if len(self) > 0:
            prev_ = list(self._store.values())[0]
            while prev_ is not None:
                self._first = prev_
                prev_ = prev_.prev()

    def _insert(self, t) -> None:
        self._store[t.get_id()] = t

    def get_first(self):
        """Return the first map with the earliest start time

        :return: The map with the earliest start time
        """
        return self._first

    def _build_internal_iteratable(self, maps, spatial) -> None:
        """Build an iterable temporal topology structure for all maps in
        the list and store the maps internally

        Basically the "next" and "prev" relations will be set in the
        temporal topology structure of each map
        The maps will be added to the object, so they can be
        accessed using the iterator of this class

        :param maps: A sorted (by start_time) list of abstract_dataset
                     objects with initiated temporal extent
        """
        self._build_iteratable(maps, spatial)

        for map_ in maps:
            self._insert(map_)

        # Detect the first map
        self._detect_first()

    def _build_iteratable(self, maps, spatial) -> None:
        """Build an iterable temporal topology structure for
        all maps in the list

        Basically the "next" and "prev" relations will be set in
        the temporal topology structure of each map.

        :param maps: A sorted (by start_time)list of abstract_dataset
                     objects with initiated temporal extent
        """
        # First we need to order the map list chronologically
        sorted_maps = sorted(maps, key=_start_time)

        for i in range(len(sorted_maps) - 1):
            sorted_maps[i].set_next(sorted_maps[i + 1])

        for map_ in sorted_maps:
            next_ = map_.next()
            if next_:
                next_.set_prev(map_)
            map_.set_temporal_topology_build_true()
            if spatial is not None:
                map_.set_spatial_topology_build_true()

    def _map_to_rect(self, tree, map_, spatial=None):
        """Use the spatio-temporal extent of a map to create and
        return a RTree rectangle

        :param spatial: This indicates if the spatial topology is created
                        as well: spatial can be None (no spatial topology),
                        "2D" using west, east, south, north or "3D" using
                        west, east, south, north, bottom, top
        """
        rect = rtree.RTreeAllocRect(tree)

        start, end = map_.get_temporal_extent_as_tuple()

        if not end:
            end = start

        if map_.is_time_absolute():
            start = time_delta_to_relative_time_seconds(start - self._timeref)
            end = time_delta_to_relative_time_seconds(end - self._timeref)

        if spatial is None:
            rtree.RTreeSetRect1D(rect, tree, float(start), float(end))
        elif spatial == "2D":
            north, south, east, west, top, bottom = map_.get_spatial_extent_as_tuple()
            rtree.RTreeSetRect3D(
                rect, tree, west, east, south, north, float(start), float(end)
            )
        elif spatial == "3D":
            north, south, east, west, top, bottom = map_.get_spatial_extent_as_tuple()
            rtree.RTreeSetRect4D(
                rect,
                tree,
                west,
                east,
                south,
                north,
                bottom,
                top,
                float(start),
                float(end),
            )

        return rect

    def _build_rtree(self, maps, spatial=None):
        """Build and return the 1-4 dimensional R*-Tree

        :param spatial: This indicates if the spatial topology is created
                        as well: spatial can be None (no spatial topology),
                        "2D" using west, east, south, north or "3D" using
                        west, east, south, north, bottom, top
        """
        dim = 1
        if spatial == "2D":
            dim = 3
        if spatial == "3D":
            dim = 4

        tree = rtree.RTreeCreateTree(-1, 0, dim)

        for i in range(len(maps)):
            rect = self._map_to_rect(tree, maps[i], spatial)
            rtree.RTreeInsertRect(rect, i + 1, tree)

        return tree

    def build(self, mapsA, mapsB=None, spatial=None) -> None:
        """Build the spatio-temporal topology structure between
        one or two unordered lists of abstract dataset objects

        This method builds the temporal or spatio-temporal topology from
        mapsA to mapsB and vice verse. The spatio-temporal topology
        structure of each map will be reset and rebuild for mapsA and
        mapsB.

        After building the temporal or spatio-temporal topology the modified
        map objects of mapsA can be accessed
        in the same way as a dictionary using there id.
        The implemented iterator assures
        the chronological iteration over the mapsA.

        :param mapsA: A list of abstract_dataset
                      objects with initiated spatio-temporal extent
        :param mapsB: An optional list of abstract_dataset
                      objects with initiated spatio-temporal extent
        :param spatial: This indicates if the spatial topology is created
                        as well: spatial can be None (no spatial topology),
                        "2D" using west, east, south, north or "3D" using
                        west, east, south, north, bottom, top
        """

        identical = False
        if mapsA == mapsB:
            identical = True

        if mapsB is None:
            mapsB = mapsA
            identical = True

        for map_ in mapsA:
            map_.reset_topology()

        if not identical:
            for map_ in mapsB:
                map_.reset_topology()

        tree = self._build_rtree(mapsA, spatial)
        list_ = gis.G_new_ilist()
        # The tree and the list belong to the C library, the garbage collector
        # does not free them, and an error in the loop must not leak them.
        try:
            for j in range(len(mapsB)):
                rect = self._map_to_rect(tree, mapsB[j], spatial)
                vector.RTreeSearch2(tree, rect, list_)
                rtree.RTreeFreeRect(rect)

                for k in range(list_.contents.n_values):
                    i = list_.contents.value[k] - 1

                    # Get the temporal relationship
                    relation = mapsB[j].temporal_relation(mapsA[i])

                    A = mapsA[i]
                    B = mapsB[j]
                    set_temporal_relationship(A, B, relation)

                    if spatial is not None:
                        relation = mapsB[j].spatial_relation(mapsA[i])
                        set_spatial_relationship(A, B, relation)

            self._build_internal_iteratable(mapsA, spatial)
            if not identical and mapsB is not None:
                self._build_iteratable(mapsB, spatial)
        finally:
            gis.G_free_ilist(list_)
            rtree.RTreeDestroyTree(tree)

    def __iter__(self):
        start_ = self._first
        while start_ is not None:
            yield start_
            start_ = start_.next()

    def __getitem__(self, index):
        return self._store[index.get_id()]

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, map_) -> bool:
        return map_ in self._store.values()


def set_temporal_relationship(A, B, relation) -> None:
    """Link two maps by the temporal relation of B to A, both ways

    B gets A in the list of the relation, A gets B in the list of the inverse
    relation. A relation that is none of the temporal relations links nothing.
    A map is not equal to itself in this sense.

    :param A: A map, the one the relation of B is given to
    :param B: A map
    :param relation: The name of the relation, "equals" is "equal"
    """
    if relation == "equals":
        relation = "equal"
    if relation not in INVERSE_TEMPORAL_RELATION:
        return
    if relation == "equal" and A == B:
        return
    implied = _IMPLIED_RELATION.get(relation)
    for name in (relation,) if implied is None else (implied, relation):
        B._link("temporal", name, A)
        A._link("temporal", INVERSE_TEMPORAL_RELATION[name], B)


def set_spatial_relationship(A, B, relation) -> None:
    """Link two maps by the spatial relation of B to A, both ways

    B gets A in the list of the relation, A gets B in the list of the inverse
    relation. A relation that is none of the spatial relations links nothing.
    A map is not equivalent to itself in this sense.

    :param A: A map, the one the relation of B is given to
    :param B: A map
    :param relation: The name of the relation
    """
    if relation not in INVERSE_SPATIAL_RELATION:
        return
    if relation == "equivalent" and A == B:
        return
    B._link("spatial", relation, A)
    A._link("spatial", INVERSE_SPATIAL_RELATION[relation], B)


def print_temporal_topology_relationships(maps1, maps2=None, dbif=None) -> None:
    """Print the temporal relationships of the
    map lists maps1 and maps2 to stdout.

     :param maps1: A list of abstract_dataset
                   objects with initiated temporal extent
     :param maps2: An optional list of abstract_dataset
                   objects with initiated temporal extent
     :param dbif: The database interface to be used
    """

    tb = SpatioTemporalTopologyBuilder()

    tb.build(maps1, maps2)

    with connection(dbif) as dbif:
        for map_ in tb:
            map_.select(dbif)
            map_.print_info()


def print_spatio_temporal_topology_relationships(
    maps1, maps2=None, spatial="2D", dbif=None
) -> None:
    """Print the temporal relationships of the
    map lists maps1 and maps2 to stdout.

     :param maps1: A list of abstract_dataset
                   objects with initiated temporal extent
     :param maps2: An optional list of abstract_dataset
                   objects with initiated temporal extent
     :param spatial: The dimension of the spatial extent to be used: "2D"
                     using west, east, south, north or "3D" using west,
                     east, south, north, bottom, top
     :param dbif: The database interface to be used
    """

    tb = SpatioTemporalTopologyBuilder()

    tb.build(maps1, maps2, spatial)

    with connection(dbif) as dbif:
        for map_ in tb:
            map_.select(dbif)
            map_.print_info()


def count_temporal_topology_relationships(maps1, maps2=None, dbif=None):
    """Count the temporal relations of a single list of maps or between two
    lists of maps

    :param maps1: A list of abstract_dataset
                objects with initiated temporal extent
    :param maps2: A list of abstract_dataset
                objects with initiated temporal extent
    :param dbif: The database interface to be used
    :return: A dictionary with counted temporal relationships
    """

    tb = SpatioTemporalTopologyBuilder()
    tb.build(maps1, maps2)

    with connection(dbif) as dbif:
        relations = None

        for map_ in tb:
            if relations is not None:
                r = map_.get_number_of_relations()
                for k in r.keys():
                    relations[k] += r[k]
            else:
                relations = map_.get_number_of_relations()

        return relations


# The relations, counted between neighbouring maps, that a dataset with a
# correct temporal topology must not have. Intervals may only follow or
# precede each other. Instants may only be told apart by their time, hence
# only "equal" is forbidden. A dataset with mixed time is checked like one
# with intervals.
_FORBIDDEN_RELATIONS = {
    "interval": (
        "equal",
        "during",
        "contains",
        "overlaps",
        "overlapped",
        "starts",
        "finishes",
        "started",
        "finished",
    ),
    "point": ("equal",),
}
_FORBIDDEN_RELATIONS["mixed"] = _FORBIDDEN_RELATIONS["interval"]


def has_correct_temporal_topology(relations, map_time) -> bool:
    """Check counted temporal relations against the topology rules

    :param relations: The dictionary of count_temporal_topology_relationships(),
                      None if no relation was counted
    :param map_time: The map time of the dataset: "interval", "point" or
                     "mixed"
    :return: True if none of the relations that the map time forbids was
             counted; False for no counts and for any other map time (a
             dataset with invalid time has no correct topology)
    """
    if relations is None or map_time not in _FORBIDDEN_RELATIONS:
        return False
    return not any(
        relations.get(name, 0) > 0 for name in _FORBIDDEN_RELATIONS[map_time]
    )


def create_temporal_relation_sql_where_statement(
    start,
    end,
    use_start: bool = True,
    use_during: bool = False,
    use_overlap: bool = False,
    use_contain: bool = False,
    use_equal: bool = False,
    use_follows: bool = False,
    use_precedes: bool = False,
):
    """Create a SQL WHERE statement for temporal relation selection of maps in
    space time datasets

    :param start: The start time
    :param end: The end time
    :param use_start: Select maps of which the start time is located in
                        the selection granule:

                        .. code-block:: output

                            map    :        s
                            granule:  s-----------------e

                            map    :        s--------------------e
                            granule:  s-----------------e

                            map    :        s--------e
                            granule:  s-----------------e
    :param use_during: Select maps which are temporal during the selection
                        granule:

                        .. code-block:: output

                            map    :     s-----------e
                            granule:  s-----------------e
    :param use_overlap: Select maps which temporal overlap the selection
                        granule:

                        .. code-block:: output

                            map    :     s-----------e
                            granule:        s-----------------e

                            map    :     s-----------e
                            granule:  s----------e
    :param use_contain: Select maps which temporally contain the selection
                        granule:

                        .. code-block:: output

                            map    :  s-----------------e
                            granule:     s-----------e
    :param use_equal: Select maps which temporally equal to the selection
                        granule:

                        .. code-block:: output

                            map    :  s-----------e
                            granule:  s-----------e
    :param use_follows: Select maps which temporally follow the selection
                        granule:

                        .. code-block:: output

                            map    :              s-----------e
                            granule:  s-----------e
    :param use_precedes: Select maps which temporally precedes the
                        selection granule:

                        .. code-block:: output

                            map    :  s-----------e
                            granule:              s-----------e

    Usage:

    .. code-block:: pycon

        >>> # Relative time
        >>> start = 1
        >>> end = 2
        >>> create_temporal_relation_sql_where_statement(start, end, use_start=False)
        >>> create_temporal_relation_sql_where_statement(start, end)
        '((start_time >= 1 and start_time < 2) )'
        >>> create_temporal_relation_sql_where_statement(start, end, use_start=True)
        '((start_time >= 1 and start_time < 2) )'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_during=True
        ... )
        '(((start_time > 1 and end_time < 2) OR (start_time >= 1 and end_time < 2) OR (start_time > 1 and end_time <= 2)))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_overlap=True
        ... )
        '(((start_time < 1 and end_time > 1 and end_time < 2) OR (start_time < 2 and start_time > 1 and end_time > 2)))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_contain=True
        ... )
        '(((start_time < 1 and end_time > 2) OR (start_time <= 1 and end_time > 2) OR (start_time < 1 and end_time >= 2)))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_equal=True
        ... )
        '((start_time = 1 and end_time = 2))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_follows=True
        ... )
        '((start_time = 2))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_precedes=True
        ... )
        '((end_time = 1))'
        >>> create_temporal_relation_sql_where_statement(
        ...     start,
        ...     end,
        ...     use_start=True,
        ...     use_during=True,
        ...     use_overlap=True,
        ...     use_contain=True,
        ...     use_equal=True,
        ...     use_follows=True,
        ...     use_precedes=True,
        ... )
        '((start_time >= 1 and start_time < 2)  OR ((start_time > 1 and end_time < 2) OR (start_time >= 1 and end_time < 2) OR (start_time > 1 and end_time <= 2)) OR ((start_time < 1 and end_time > 1 and end_time < 2) OR (start_time < 2 and start_time > 1 and end_time > 2)) OR ((start_time < 1 and end_time > 2) OR (start_time <= 1 and end_time > 2) OR (start_time < 1 and end_time >= 2)) OR (start_time = 1 and end_time = 2) OR (start_time = 2) OR (end_time = 1))'

    .. code-block:: pycon

        >>> # Absolute time
        >>> start = datetime(2001, 1, 1, 12, 30)
        >>> end = datetime(2001, 3, 31, 14, 30)
        >>> create_temporal_relation_sql_where_statement(start, end, use_start=False)
        >>> create_temporal_relation_sql_where_statement(start, end)
        "((start_time >= '2001-01-01 12:30:00' and start_time < '2001-03-31 14:30:00') )"
        >>> create_temporal_relation_sql_where_statement(start, end, use_start=True)
        "((start_time >= '2001-01-01 12:30:00' and start_time < '2001-03-31 14:30:00') )"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_during=True
        ... )
        "(((start_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time >= '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time > '2001-01-01 12:30:00' and end_time <= '2001-03-31 14:30:00')))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_overlap=True
        ... )
        "(((start_time < '2001-01-01 12:30:00' and end_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time < '2001-03-31 14:30:00' and start_time > '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00')))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_contain=True
        ... )
        "(((start_time < '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time <= '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time < '2001-01-01 12:30:00' and end_time >= '2001-03-31 14:30:00')))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_equal=True
        ... )
        "((start_time = '2001-01-01 12:30:00' and end_time = '2001-03-31 14:30:00'))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_follows=True
        ... )
        "((start_time = '2001-03-31 14:30:00'))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start, end, use_start=False, use_precedes=True
        ... )
        "((end_time = '2001-01-01 12:30:00'))"
        >>> create_temporal_relation_sql_where_statement(
        ...     start,
        ...     end,
        ...     use_start=True,
        ...     use_during=True,
        ...     use_overlap=True,
        ...     use_contain=True,
        ...     use_equal=True,
        ...     use_follows=True,
        ...     use_precedes=True,
        ... )
        "((start_time >= '2001-01-01 12:30:00' and start_time < '2001-03-31 14:30:00')  OR ((start_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time >= '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time > '2001-01-01 12:30:00' and end_time <= '2001-03-31 14:30:00')) OR ((start_time < '2001-01-01 12:30:00' and end_time > '2001-01-01 12:30:00' and end_time < '2001-03-31 14:30:00') OR (start_time < '2001-03-31 14:30:00' and start_time > '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00')) OR ((start_time < '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time <= '2001-01-01 12:30:00' and end_time > '2001-03-31 14:30:00') OR (start_time < '2001-01-01 12:30:00' and end_time >= '2001-03-31 14:30:00')) OR (start_time = '2001-01-01 12:30:00' and end_time = '2001-03-31 14:30:00') OR (start_time = '2001-03-31 14:30:00') OR (end_time = '2001-01-01 12:30:00'))"

    """  # noqa: E501

    where = "("

    if use_start:
        if isinstance(start, datetime):
            where += "(start_time >= '%s' and start_time < '%s') " % (start, end)
        else:
            where += "(start_time >= %i and start_time < %i) " % (start, end)

    if use_during:
        if use_start:
            where += " OR "

        if isinstance(start, datetime):
            where += "((start_time > '%s' and end_time < '%s') OR " % (start, end)
            where += "(start_time >= '%s' and end_time < '%s') OR " % (start, end)
            where += "(start_time > '%s' and end_time <= '%s'))" % (start, end)
        else:
            where += "((start_time > %i and end_time < %i) OR " % (start, end)
            where += "(start_time >= %i and end_time < %i) OR " % (start, end)
            where += "(start_time > %i and end_time <= %i))" % (start, end)

    if use_overlap:
        if use_start or use_during:
            where += " OR "

        if isinstance(start, datetime):
            where += (
                "((start_time < '%s' and end_time > '%s' and end_time <"
                " '%s') OR " % (start, start, end)
            )
            where += (
                "(start_time < '%s' and start_time > '%s' and end_time "
                "> '%s'))" % (end, start, end)
            )
        else:
            where += "((start_time < %i and end_time > %i and end_time < %i) OR " % (
                start,
                start,
                end,
            )
            where += "(start_time < %i and start_time > %i and end_time > %i))" % (
                end,
                start,
                end,
            )

    if use_contain:
        if use_start or use_during or use_overlap:
            where += " OR "

        if isinstance(start, datetime):
            where += "((start_time < '%s' and end_time > '%s') OR " % (start, end)
            where += "(start_time <= '%s' and end_time > '%s') OR " % (start, end)
            where += "(start_time < '%s' and end_time >= '%s'))" % (start, end)
        else:
            where += "((start_time < %i and end_time > %i) OR " % (start, end)
            where += "(start_time <= %i and end_time > %i) OR " % (start, end)
            where += "(start_time < %i and end_time >= %i))" % (start, end)

    if use_equal:
        if use_start or use_during or use_overlap or use_contain:
            where += " OR "

        if isinstance(start, datetime):
            where += "(start_time = '%s' and end_time = '%s')" % (start, end)
        else:
            where += "(start_time = %i and end_time = %i)" % (start, end)

    if use_follows:
        if use_start or use_during or use_overlap or use_contain or use_equal:
            where += " OR "

        if isinstance(start, datetime):
            where += "(start_time = '%s')" % (end)
        else:
            where += "(start_time = %i)" % (end)

    if use_precedes:
        if (
            use_start
            or use_during
            or use_overlap
            or use_contain
            or use_equal
            or use_follows
        ):
            where += " OR "

        if isinstance(start, datetime):
            where += "(end_time = '%s')" % (start)
        else:
            where += "(end_time = %i)" % (start)

    where += ")"

    # Catch empty where statement
    if where == "()":
        where = None

    return where


###############################################################################

if __name__ == "__main__":
    import doctest

    doctest.testmod()
