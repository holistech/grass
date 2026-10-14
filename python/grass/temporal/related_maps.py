"""The classic per-relation sampling of maps by granules

t.rast.mapcalc, t.rast3d.mapcalc and t.sample have no switch between the
classic and the core algebra, so their results must stay those of
AbstractSpaceTimeDataset.sample_by_dataset(). This module is the one place
that reproduces its rules on the temporal algebra core, so that the tools do
not carry diverging copies:

- the sampling method names expand into relation names in the order in which
  sample_by_dataset() tries them,
- the maps related to a granule are collected relation by relation in that
  order, without repetition, and
- the sampler must pass the two guards at the top of sample_by_dataset().

It does not call gather(), and it does not use the spatial relation of the
core. The classic builder relates maps by their 2D extent, also for 3D
rasters, as closed boxes: it searches an R-tree that counts contact at an edge
or a corner as intersection. The spatial relations of the core are 3D for 3D
rasters and give no relation to boxes that share only a corner, so under
spatial the temporal partners come from related() without a spatial part, and
a closed 2D box test filters them (see boxes_intersect()).

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
# inversion. "start" appends "equals", which upper-cases to the key "EQUALS"
# that the builder never files (it files "EQUAL"), so the classic "start" never
# matches a map of equal time (measured 2026-10-14 in a temporary project:
# method=equal lists an equal map, method=start prints None for it). The name
# is left out here, which keeps that result, and the core would reject it as an
# unknown relation.
_METHOD_RELATIONS = {
    "equal": ("equal",),
    "during": ("during",),
    "contain": ("contains",),
    "overlap": ("overlapped", "overlaps"),
    "follows": ("follows",),
    "precedes": ("precedes",),
    "start": ("overlapped", "starts", "started", "finishes", "contains"),
}
# These names stand for a group of relations that sample_by_dataset() appends
# after the plain method names.
_METHOD_GROUPS = ("start", "overlap", "contain")


def method_relations(method):
    """The relation names of a list of sampling method names, in the order in
    which sample_by_dataset() tries them

    The plain names come first, in the order of the list, then the groups
    "start", "overlap" and "contain", each as far as not yet in the list. The
    order matters because the first relation with a map decides which map a
    caller that takes only one uses.

    :param method: names from "start", "during", "overlap", "contain",
        "equal", "follows" and "precedes", the values that the standard
        option G_OPT_T_SAMPLE offers
    :raises ValueError: for another name
    """
    for name in method:
        if name not in _METHOD_RELATIONS:
            msg = f"Unknown sampling method <{name}>"
            raise ValueError(msg)
    names = []
    for name in method:
        if name in _METHOD_GROUPS:
            continue
        for relation_name in _METHOD_RELATIONS[name]:
            if relation_name not in names:
                names.append(relation_name)
    for group in _METHOD_GROUPS:
        if group in method:
            names.extend(
                relation_name
                for relation_name in _METHOD_RELATIONS[group]
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
    """The slots of series with a gap slot (origin None) between granules
    that have a hole between them

    get_registered_maps_as_objects_with_gaps() puts a map with id None between
    two consecutive maps if the later one is strictly after the earlier one.
    The series must be an interval dataset, so a gap runs from the end of the
    earlier granule to the start of the later one; touching granules give no
    gap. A gap has the spatial extent (0, 0, 0, 0, 0, 0) as in the classic
    function, which matters under spatial: the gap then relates only to maps
    whose box touches the origin.
    """
    slots = list(series.slots)
    out = []
    for i, slot in enumerate(slots):
        out.append(slot)
        if i < len(slots) - 1:
            extent = slot.extent
            following = slots[i + 1].extent
            if extent.end < following.start:
                out.append(
                    Slot(
                        Extent(extent.end, following.start, extent.unit),
                        NULL,
                        Space(0, 0, 0, 0, 0, 0),
                        None,
                    )
                )
    return Series(tuple(out), series.kind, series.sort, series.spatial)


def sampler_refused(sampler, dataset, msgr):
    """True, with the classic message, if sampler cannot sample dataset

    These are the two guards at the top of sample_by_dataset(): the temporal
    types must be equal, and the sampler must have interval time. The
    message goes to msgr.error() and the caller decides what refusing means.

    :param sampler: the sampler space time dataset object
    :param dataset: the space time dataset object to sample
    """
    if dataset.get_temporal_type() != sampler.get_temporal_type():
        msgr.error(_("The space time datasets must be of the same temporal type"))
        return True
    if sampler.get_map_time() != "interval":
        msgr.error(_("The temporal map type of the sample dataset must be interval"))
        return True
    return False
