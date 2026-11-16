"""Temporal and spatial relations between the slots of two series

There is one reading: a relation R between L and X relates the pairs (l, x)
for which "l R x" holds, as the selection L {:,R} X of the algebra does.
during includes starts and finishes, contains includes started and
finished, as the topology builder of grass.temporal defines them. precedes
and follows are adjacent intervals; intervals with a gap have no relation.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

import datetime
from dataclasses import dataclass

from grass.temporal.topology import SpatioTemporalTopologyBuilder, check_time_zones

from .adapters import as_map

TEMPORAL_RELATIONS = (
    "equal",
    "during",
    "contains",
    "starts",
    "started",
    "finishes",
    "finished",
    "precedes",
    "follows",
    "overlaps",
    "overlapped",
)
SPATIAL_RELATIONS = (
    "equivalent",
    "cover",
    "covered",
    "in",
    "contain",
    "overlap",
    "meet",
)

# The manual names both overlap relations "over". The published paper writes
# "equals" for the relation that is called "equal"; the classic algebra
# read it the same way. Both are second names, so that the printed
# expressions run; relation() reads them too, so that the Python API takes
# the names of the operators in braces. TEMPORAL_RELATIONS keeps the
# canonical names only.
_SHORTHANDS = {"over": ("overlaps", "overlapped"), "equals": ("equal",)}

_INVERSE = {
    "equal": "equal",
    "during": "contains",
    "contains": "during",
    "starts": "started",
    "started": "starts",
    "finishes": "finished",
    "finished": "finishes",
    "precedes": "follows",
    "follows": "precedes",
    "overlaps": "overlapped",
    "overlapped": "overlaps",
    "equivalent": "equivalent",
    "cover": "covered",
    "covered": "cover",
    "in": "contain",
    "contain": "in",
    "overlap": "overlap",
    "meet": "meet",
}


@dataclass(frozen=True)
class Relation:
    """A set of temporal relations, and of spatial relations if space counts

    A temporal relation is required, a spatial one cannot stand alone. spatial
    is None if only time relates two slots. Otherwise two slots must also
    have a spatial relation, one of the set if it is not empty. Boxes that
    share only a corner have none.
    """

    temporal: frozenset
    spatial: frozenset | None = None

    def __post_init__(self):
        if isinstance(self.temporal, str) or isinstance(self.spatial, str):
            msg = "The names of a relation are a set of strings, not a string"
            raise TypeError(msg)
        object.__setattr__(self, "temporal", frozenset(self.temporal))
        if self.spatial is not None:
            object.__setattr__(self, "spatial", frozenset(self.spatial))
        unknown = self.temporal - set(TEMPORAL_RELATIONS)
        if self.spatial is not None:
            unknown |= self.spatial - set(SPATIAL_RELATIONS)
        if unknown:
            msg = f"Unknown relations: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        if not self.temporal:
            if self.spatial:
                msg = (
                    f"{'|'.join(sorted(self.spatial))} is a spatial relation and "
                    "needs a temporal one, as in equal|overlap"
                )
            else:
                msg = "A relation needs at least one temporal relation"
            raise ValueError(msg)

    def __or__(self, other):
        if not isinstance(other, Relation):
            return NotImplemented
        if self.spatial is None and other.spatial is None:
            spatial = None
        else:
            spatial = (self.spatial or frozenset()) | (other.spatial or frozenset())
        return Relation(self.temporal | other.temporal, spatial)

    def __str__(self):
        return "|".join(sorted(self.temporal | (self.spatial or frozenset())))


def relation_names(name):
    """Return the canonical relation names that a written name stands for

    ``over`` is both overlap relations and ``equals`` is ``equal``; any other
    name stands for itself, known or not.
    """
    return _SHORTHANDS.get(name, (name,))


def relation(text, *, spatial=False):
    """Return the relation of names joined with ``|``, e.g. ``during|starts``

    Names are read in any case, and ``over`` and ``equals`` as in the
    operators of the algebra (see relation_names()). Spatial names in the
    text, or spatial=True, make space count. The text needs at least one
    temporal name.
    """
    names = {
        each
        for name in text.split("|")
        if name.strip()
        for each in relation_names(name.strip().lower())
    }
    temporal = names & set(TEMPORAL_RELATIONS)
    spatial_names = names - temporal
    if spatial_names or spatial:
        return Relation(temporal, spatial_names)
    return Relation(temporal)


def inverse(relation_):
    """Return the relation R' with "x R' l" exactly where "l R x" holds

    This holds for every temporal name and for the spatial names except
    cover and covered. The spatial classification of grass.temporal is not
    antisymmetric for them: for the boxes N9 S8 E7 W5 and N9 S6 E7 W6 it
    reports the same name in both directions (measured 2026-10-11).
    related() does not compensate for that.
    """
    spatial = relation_.spatial
    return Relation(
        frozenset(_INVERSE[name] for name in relation_.temporal),
        None if spatial is None else frozenset(_INVERSE[name] for name in spatial),
    )


def _partners(topology, names, index):
    """Return the indices of the maps that topology lists under names

    topology is the dictionary of a map object; the builder files the
    partners under upper case names and also lists NEXT and PREV, which are
    not relations and which this lookup never asks for.
    """
    return {
        index[partner.get_id()]
        for name in names
        for partner in topology.get(name.upper(), ())
    }


def _check_time_zones(left, other):
    """Raise ValueError if the slots mix times with and without an offset

    The builder would refuse the mix as well, but it only knows the stand-ins
    made by related(). The message names the maps of the first slot of each
    kind. A slot without origin, such as a granule, is no map, so if either
    has none, the message names the time stamps instead.
    """
    aware = naive = None
    for slot in (*left, *other):
        start = slot.extent.start
        if not isinstance(start, datetime.datetime):
            continue
        if start.tzinfo is None:
            naive = slot if naive is None else naive
        else:
            aware = slot if aware is None else aware
    if aware is None or naive is None:
        return
    if aware.origin and naive.origin:
        # Raises, as the two starts differ in their offset.
        check_time_zones((slot.origin, slot.extent.start) for slot in (aware, naive))
    first, second = aware.extent.start, naive.extent.start
    msg = (
        f"Time stamps with a time zone offset, such as {first}, and time "
        f"stamps without one, such as {second}, cannot be related in time; "
        "register all maps with or all without an offset"
    )
    raise ValueError(msg)


def related(left, relation_, other, *, dimension="2D"):
    """Return, per slot l of left, the indices of the slots x with "l R x"

    The slots x are those of other, each listed once and in the order of
    other.

    :param left: sequence of slots
    :param relation_: the Relation "R" to test; it may name temporal and
        spatial relations, and a spatial one needs the box of every slot
    :param other: sequence of slots
    :param dimension: "2D" relates the spatial extents as rectangles, "3D"
        as boxes; only used if the relation has a spatial part
    :raises ValueError: for a slot without time stamp, or without spatial
        extent where the relation has a spatial part, and for slots with
        absolute times with and without a time zone offset
    """
    for slot in (*left, *other):
        if slot.extent is None:
            msg = "A map without time stamp has no temporal relation"
            raise ValueError(msg)
        if relation_.spatial is not None and slot.space is None:
            msg = "A spatial relation needs the spatial extent of every map"
            raise ValueError(msg)
    _check_time_zones(left, other)
    if not left or not other:
        return [[] for _ in left]
    left_maps = [
        as_map(slot.extent, slot.space, f"l{i}") for i, slot in enumerate(left)
    ]
    other_maps = [
        as_map(slot.extent, slot.space, f"x{j}") for j, slot in enumerate(other)
    ]
    index = {map_.get_id(): j for j, map_ in enumerate(other_maps)}
    SpatioTemporalTopologyBuilder().build(
        left_maps,
        other_maps,
        spatial=None if relation_.spatial is None else dimension,
    )
    result = []
    for map_ in left_maps:
        temporal = map_.get_temporal_relations()
        spatial = None
        if relation_.spatial is not None:
            # The search of the builder also finds boxes that share only a
            # corner, which have no spatial relation. Without names any
            # spatial relation is required, as in the classic algebra.
            spatial = _partners(
                map_.get_spatial_relations(),
                relation_.spatial or SPATIAL_RELATIONS,
                index,
            )
        found = _partners(temporal, relation_.temporal, index)
        result.append(sorted(found if spatial is None else found & spatial))
    return result


equal = Relation(frozenset({"equal"}))
during = Relation(frozenset({"during"}))
contains = Relation(frozenset({"contains"}))
starts = Relation(frozenset({"starts"}))
started = Relation(frozenset({"started"}))
finishes = Relation(frozenset({"finishes"}))
finished = Relation(frozenset({"finished"}))
precedes = Relation(frozenset({"precedes"}))
follows = Relation(frozenset({"follows"}))
overlaps = Relation(frozenset({"overlaps"}))
overlapped = Relation(frozenset({"overlapped"}))
