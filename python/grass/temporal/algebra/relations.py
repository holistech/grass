"""Temporal and spatial relations between the slots of two series

There is one reading: a relation R between L and X relates the pairs (l, x)
for which "l R x" holds, as the selection L {:,R} X of the algebra does.
during includes starts and finishes, contains includes started and
finished, as the topology builder of grass.temporal defines them. precedes
and follows are adjacent intervals; intervals with a gap have no relation.
"""

from dataclasses import dataclass

from grass.temporal.spatio_temporal_relationships import SpatioTemporalTopologyBuilder

from ._adapters import as_map

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

    spatial is None if only time relates two slots. Otherwise two slots must
    also touch or overlap in space and, if the set is not empty, have one of
    its spatial relations.
    """

    temporal: frozenset
    spatial: frozenset | None = None

    def __post_init__(self):
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
            msg = "A relation needs at least one temporal relation"
            raise ValueError(msg)

    def __or__(self, other):
        if self.spatial is None and other.spatial is None:
            spatial = None
        else:
            spatial = (self.spatial or frozenset()) | (other.spatial or frozenset())
        return Relation(self.temporal | other.temporal, spatial)

    def __str__(self):
        return "|".join(sorted(self.temporal | (self.spatial or frozenset())))


def relation(text, *, spatial=False):
    """Return the relation of names joined with |, e.g. "during|starts"

    Spatial names in the text, or spatial=True, make space count.
    """
    names = {name.strip().lower() for name in text.split("|") if name.strip()}
    temporal = names & set(TEMPORAL_RELATIONS)
    spatial_names = names - temporal
    if spatial_names or spatial:
        return Relation(temporal, spatial_names)
    return Relation(temporal)


def inverse(relation_):
    """Return the relation R' with "x R' l" exactly where "l R x" holds"""
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


def related(left, relation_, other):
    """Return, per slot l of left, the indices of the slots x of other with
    "l R x", in the order of other

    :param left: sequence of slots
    :param other: sequence of slots
    """
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
        left_maps, other_maps, spatial=None if relation_.spatial is None else "2D"
    )
    result = []
    for map_ in left_maps:
        found = _partners(map_.get_temporal_relations(), relation_.temporal, index)
        # With spatial=True and no names the builder has already dropped the
        # pairs that neither touch nor overlap, which is all that is asked.
        if relation_.spatial:
            found &= _partners(map_.get_spatial_relations(), relation_.spatial, index)
        result.append(sorted(found))
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
