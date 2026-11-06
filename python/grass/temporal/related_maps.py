"""The classic per-relation sampling of maps by granules

t.rast.mapcalc, t.rast3d.mapcalc and t.sample have no switch between the
classic and the core algebra, so their results are those of the classic
sample_by_dataset(), which grass.temporal.testing.reference keeps as the
reference, except for one fixed fault (below). This module is the one place
that reproduces its rules on the temporal algebra core, so that the tools do
not carry diverging copies:

- the sampling method names expand into relation names in the order in which
  sample_by_dataset() tries them,
- the maps related to a granule are collected relation by relation in that
  order, without repetition, and
- the sampler must pass the two guards at the top of sample_by_dataset().

The fixed fault: the method "start" also selects a map of the same time as
the granule, which sample_by_dataset() meant to select but never did (see
_METHOD_GROUPS).

It does not call gather(), which differs from the classic rules in two ways.
A classic caller that takes one map takes the first map of the first relation
that has one, while gather() takes the earliest start over all relations.
And the spatial relation of the core is not the classic one: the classic
builder relates maps by their 2D extent, also for 3D rasters, as closed boxes,
because it searches an R-tree that counts contact at an edge or a corner as
intersection. The spatial relations of the core are 3D for 3D rasters and give
no relation to boxes that share only a corner. So under spatial the temporal
partners come from related() without a spatial part, and a closed 2D box test
filters them (see boxes_intersect()).

Aggregation does not use this module. aggregation_core takes the union of the
related maps in time order, which is a documented change from the classic
order.

SPDX-FileCopyrightText: 2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from .algebra.content import NULL
from .algebra.relations import relation, related
from .algebra.series import Extent, Series, Slot, Space

# The relations that sample_by_dataset() reads for a method, from the side of
# the granule: the topology builder files, under a relation name, the maps that
# stand in that relation to the granule, and the method names are read the
# same way ("during" selects the maps the granule lies during). So there is no
# inversion.
# The names of the standard option G_OPT_T_SAMPLE, other than the groups below
_OPTION_NAMES = ("equal", "during", "follows", "precedes")
# sample_by_dataset() read every other name as a relation of the topology
# builder: stripped and upper-cased, then looked up among the relations it
# files. "equals" is no such relation (the builder files "EQUAL"), so it selects
# nothing, as it always did.
_PLAIN_RELATIONS = {
    "EQUAL": ("equal",),
    "EQUALS": (),
    "DURING": ("during",),
    "CONTAINS": ("contains",),
    "OVERLAPS": ("overlaps",),
    "OVERLAPPED": ("overlapped",),
    "FOLLOWS": ("follows",),
    "PRECEDES": ("precedes",),
    "STARTS": ("starts",),
    "STARTED": ("started",),
    "FINISHES": ("finishes",),
    "FINISHED": ("finished",),
}
# These names stand for a group of relations that sample_by_dataset() appends
# after the plain method names, in this order. They are read as written, not
# upper-cased. "over" is an old short form of "overlap".
# sample_by_dataset() ended "start" with "equals", which upper-cases to the key
# "EQUALS" that the builder never files (it files "EQUAL"), so the classic
# "start" never matched a map of equal time (measured 2026-10-14 in a
# temporary project: method=equal listed an equal map, method=start printed
# None for it). "start" here ends with "equal" instead, so that a map with the
# same time as the granule is selected, as the name "equals" intended. The
# reference in grass.temporal.testing.reference keeps the classic result.
_METHOD_GROUPS = {
    "start": ("overlapped", "starts", "started", "finishes", "contains", "equal"),
    "overlap": ("overlapped", "overlaps"),
    "over": ("overlapped", "overlaps"),
    "contain": ("contains",),
}


def method_relations(method, any_relation: bool = False):
    """The relation names of a list of sampling method names, in the order in
    which sample_by_dataset() tries them

    The plain names come first, in the order of the list, then the groups
    "start", "overlap" and "contain", each as far as not yet in the list. The
    order matters because the first relation with a map decides which map a
    caller that takes only one uses. "start" ends with "equal", which
    sample_by_dataset() never matched (see _METHOD_GROUPS).

    :param method: names from "start", "during", "overlap", "contain",
        "equal", "follows" and "precedes", the values that the standard
        option G_OPT_T_SAMPLE offers
    :param any_relation: Also accept what sample_by_dataset() accepted: the
        name of any relation of the topology builder (contains, overlaps,
        overlapped, starts, started, finishes, finished, equals), in any case
        and with white space, and "over" for "overlap". Any other name
        selects nothing and is skipped.
    :raises ValueError: for another name, unless any_relation is set
    """
    groups = (
        _METHOD_GROUPS
        if any_relation
        else {k: v for k, v in _METHOD_GROUPS.items() if k != "over"}
    )

    def plain_key(name):
        return name.strip().upper() if any_relation else name.upper()

    def known(name):
        if name in groups:
            return True
        if any_relation:
            return plain_key(name) in _PLAIN_RELATIONS
        return name in _OPTION_NAMES

    if not any_relation:
        for name in method:
            if not known(name):
                msg = f"Unknown sampling method <{name}>"
                raise ValueError(msg)
    names = []
    for name in method:
        # The sampling before this module existed matched every name against
        # the relations of the topology builder and skipped what matched
        # nothing, so a misspelt name selects nothing instead of stopping
        # the run. Callers with the fixed option values use the strict path.
        if name in groups or not known(name):
            continue
        for relation_name in _PLAIN_RELATIONS[plain_key(name)]:
            if relation_name not in names:
                names.append(relation_name)
    for group, relation_names in groups.items():
        if group in method:
            names.extend(
                relation_name
                for relation_name in relation_names
                if relation_name not in names
            )
    return names


def boxes_intersect(left, right):
    """True if the 2D extents touch or overlap, edges and corners included

    The classic -s searches an R-tree over west, east, south and north, which
    counts contact as intersection, whatever the bottom and top of 3D maps.
    """
    return (
        left.west <= right.east
        and right.west <= left.east
        and left.south <= right.north
        and right.south <= left.north
    )


def related_per_granule(granules, names, inputs, *, spatial=False):
    """Per granule, the slots of inputs related through names

    The classic function collects the maps relation by relation in the order
    of names and drops duplicates. One merged relation would return a single
    start-time order, which differs whenever a granule relates maps through
    more than one relation, so the relations are kept apart. A relation
    reads "granule R input", as the topology builder files the maps.

    Within a relation the maps come by start time and, for an equal start
    time, by map id. This is the order the classic function lists them in,
    as the database returns them; the core would order such ties by end time,
    so the inputs are put in the classic order before related() numbers
    them. The order was pinned for t.sample by its characterization tests.
    The classic mapcalc took the hit order of the R-tree, which is undefined,
    so the same rule serves it.

    With spatial, a map must also touch the granule in 2D.

    :param granules: the Series of the granules, gap slots included
    :param names: relation names, see method_relations()
    :param inputs: the Series whose maps are sampled
    :returns: one list of slots of inputs per granule, empty where nothing
        relates
    """
    partners = sorted(inputs.slots, key=lambda slot: (slot.extent.start, slot.origin))
    per_relation = [related(granules.slots, relation(name), partners) for name in names]
    rows = []
    for number, granule in enumerate(granules.slots):
        found = []
        for indices in per_relation:
            for index in indices[number]:
                if index in found:
                    continue
                if spatial and not boxes_intersect(
                    granule.space, partners[index].space
                ):
                    continue
                found.append(index)
        rows.append([partners[index] for index in found])
    return rows


def with_gaps(series):
    """The slots of series with a gap slot (origin None) where no granule lies

    A gap is time that no granule covers, as in
    get_registered_maps_as_objects_with_gaps(): it lies before a granule that
    starts after the latest end of the granules before it and runs from that
    end to its start. A granule that ends inside a longer one leaves no gap;
    touching granules give no gap. The series must be an interval dataset. A
    gap has the spatial extent (0, 0, 0, 0, 0, 0) as in the classic
    function, which matters under spatial: the gap then relates only to maps
    whose box touches the origin.
    """
    out = []
    covered_until = None
    for slot in series.slots:
        extent = slot.extent
        if covered_until is not None and covered_until < extent.start:
            out.append(
                Slot(
                    Extent(covered_until, extent.start, extent.unit),
                    NULL,
                    Space(0, 0, 0, 0, 0, 0),
                    None,
                )
            )
        out.append(slot)
        if covered_until is None or extent.end > covered_until:
            covered_until = extent.end
    return Series(tuple(out), series.kind, series.sort, series.spatial)


def sampler_refusal(sampler, dataset, check_map_time=True):
    """The classic message why sampler cannot sample dataset, or None

    These are the two guards at the top of sample_by_dataset(): the temporal
    types must be equal, and the sampler must have interval time.

    :param sampler: the sampler space time dataset object
    :param dataset: the space time dataset object to sample
    :param check_map_time: False skips the interval check, for a sampler
        without registered maps, which has no map time to check
    """
    if dataset.get_temporal_type() != sampler.get_temporal_type():
        return _("The space time datasets must be of the same temporal type")
    if check_map_time and sampler.get_map_time() != "interval":
        return _("The temporal map type of the sample dataset must be interval")
    return None


def sampler_refused(sampler, dataset, msgr):
    """True, with the classic message, if sampler cannot sample dataset

    The message of sampler_refusal() goes to msgr.error() and the caller
    decides what refusing means. A tool that ends on a refusal calls
    sampler_refusal() and makes the message fatal instead.

    :param sampler: the sampler space time dataset object
    :param dataset: the space time dataset object to sample
    """
    refusal = sampler_refusal(sampler, dataset)
    if refusal is None:
        return False
    msgr.error(refusal)
    return True
