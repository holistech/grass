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

from dataclasses import dataclass, field

from grass.temporal.topology import SpatioTemporalTopologyBuilder

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
ORDERS = ("sorted", "written")

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

    written lists the temporal names in the order and with the repetitions
    of the text the relation was read from. A set has no order, but
    related(order="written") needs one. It is no part of the identity of a
    relation: "during|equal" and "equal|during" are equal.
    """

    temporal: frozenset
    spatial: frozenset | None = None
    written: tuple = field(default=(), compare=False, repr=False)

    def __post_init__(self):
        if isinstance(self.temporal, str) or isinstance(self.spatial, str):
            msg = "The names of a relation are a set of strings, not a string"
            raise TypeError(msg)
        object.__setattr__(self, "temporal", frozenset(self.temporal))
        object.__setattr__(self, "written", tuple(self.written))
        if self.spatial is not None:
            object.__setattr__(self, "spatial", frozenset(self.spatial))
        unknown = self.temporal - set(TEMPORAL_RELATIONS)
        if self.spatial is not None:
            unknown |= self.spatial - set(SPATIAL_RELATIONS)
        if unknown:
            msg = f"Unknown relations: {', '.join(sorted(unknown))}"
            raise ValueError(msg)
        if self.written and set(self.written) != self.temporal:
            msg = "The written names of a relation must be its temporal names"
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
        written = (
            (*self.names(), *other.names()) if self.written or other.written else ()
        )
        return Relation(self.temporal | other.temporal, spatial, written)

    def names(self):
        """The temporal names in written order, sorted if none was written"""
        return self.written or tuple(sorted(self.temporal))

    def __str__(self):
        return "|".join(sorted(self.temporal | (self.spatial or frozenset())))


def relation(text, *, spatial=False):
    """Return the relation of names joined with ``|``, e.g. ``during|starts``

    Spatial names in the text, or spatial=True, make space count. The text
    needs at least one temporal name. The temporal names are kept in written
    order, see Relation.written.
    """
    names = [name.strip().lower() for name in text.split("|") if name.strip()]
    written = tuple(name for name in names if name in TEMPORAL_RELATIONS)
    spatial_names = set(names) - set(written)
    if spatial_names or spatial:
        return Relation(set(written), spatial_names, written)
    return Relation(set(written), None, written)


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
        tuple(_INVERSE[name] for name in relation_.written),
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


def related(left, relation_, other, *, dimension="2D", order="sorted", unique=True):
    """Return, per slot l of left, the indices of the slots x with "l R x"

    The slots x are those of other, listed in its order unless order says
    otherwise.

    :param left: sequence of slots
    :param other: sequence of slots
    :param dimension: "2D" relates the spatial extents as rectangles, "3D"
        as boxes; only used if the relation has a spatial part
    :param order: "sorted" lists the partners in the order of other;
        "written" lists those of the first temporal name of the relation
        (Relation.written) first, then those of the second name, and so on,
        each name in the list order of other (the order of the ranks, if
        every slot of other has one, as Series.listed()), as the classic
        algebra visits them
    :param unique: False lists a partner once for every written name that
        relates it, so a name written twice lists its partners twice; True
        lists each partner once, at its first position
    :raises ValueError: for an unknown order
    """
    if order not in ORDERS:
        msg = f"order must be one of {', '.join(ORDERS)}, got {order!r}"
        raise ValueError(msg)
    for slot in (*left, *other):
        if slot.extent is None:
            msg = "A map without time stamp has no temporal relation"
            raise ValueError(msg)
        if relation_.spatial is not None and slot.space is None:
            msg = "A spatial relation needs the spatial extent of every map"
            raise ValueError(msg)
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
    names = relation_.names()
    # The classic topology builder visits the partners in the order of their
    # list, which a merge() or buff_t() sets apart from the time order.
    listed = order == "written" and all(slot.rank is not None for slot in other)
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
        groups = []
        for name in names:
            found = _partners(temporal, (name,), index)
            groups.append(sorted(found if spatial is None else found & spatial))
        if listed:
            groups = [sorted(group, key=lambda j: other[j].rank) for group in groups]
        result.append(_joined_partners(groups, order, unique))
    return result


def _joined_partners(groups, order, unique):
    """Join the partners of the single names into the list of one slot"""
    joined = [partner for group in groups for partner in group]
    if unique:
        joined = list(dict.fromkeys(joined))
    return sorted(joined) if order == "sorted" else joined


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
