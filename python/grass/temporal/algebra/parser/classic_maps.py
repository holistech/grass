"""The maps of the classic algebra as the profile tells them apart

The classic algebra lists maps of several temporal types in one list and
tells maps apart by the identity of their map objects; a series of the core
has neither. These classes and functions hold both for ClassicTranslator
(classic.py); they are for variants of the algebra, not for users.

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from grass.temporal.algebra.series import Series

from .shared import ABSENT

if TYPE_CHECKING:
    from grass.temporal.algebra.content import Content


def unit_of(series):
    """The temporal type and unit of a series: the unit of relative time,
    None for absolute time, ABSENT for a map without time stamp"""
    extent = series.slots[0].extent
    return ABSENT if extent is None else extent.unit


@dataclasses.dataclass(frozen=True)
class Mixed:
    """A classic list of maps of more than one temporal type or unit

    The classic lists take any maps; maps of different types or units relate
    to nothing, and registering them in one dataset fails. A series of the
    core has one type and unit, so the list is held as one series per type
    and unit, in the order in which the list first shows each. Only merge()
    makes such a list; ClassicTranslator._each_unit() evaluates what takes
    it once per series.
    """

    parts: tuple[Series, ...]

    def part(self, unit):
        """The series of maps of a unit; for a unit the list lacks, a series
        that relates to nothing of that unit"""
        return next(
            (part for part in self.parts if unit_of(part) == unit), self.parts[0]
        )


def listed(parts):
    """The slots of the parts of a list in its order"""
    slots = [slot for part in parts for slot in part.listed()]
    if all(slot.rank is not None for slot in slots):
        slots.sort(key=lambda slot: slot.rank)
    return slots


def gathered(parts):
    """One series, or a Mixed if the non-empty parts differ in unit"""
    groups = {}
    for part in parts:
        if part.slots:
            unit = unit_of(part)
            groups[unit] = (
                dataclasses.replace(groups[unit], slots=groups[unit].slots + part.slots)
                if unit in groups
                else part
            )
    if not groups:
        return parts[0]
    if len(groups) == 1:
        return next(iter(groups.values()))
    return Mixed(tuple(groups.values()))


def with_slots(series, slots, sort=None):
    """A series of slots with the map type, order and flags of series"""
    return Series(
        tuple(slots),
        series.kind,
        series.sort if sort is None else sort,
        series.spatial,
        series.order,
    )


# The map that a content stands for is its own, a new map object of the
# classic algebra, as long as the map of its mark is this value.
OWN = object()


@dataclasses.dataclass(eq=False)
class MapObject:
    """The map object of the classic algebra that a content stands for

    The classic algebra tells maps apart by the id of their map object, their
    time stamp and the command written on them (_merge_key() of the classic
    algebra). The profile attaches this object to the content as its mark,
    which the core never reads. A new map object is its own id; the classic
    algebra makes one for each result of an operation of two map lists, each
    map read at an offset, each buffer and each value of a time function at
    an offset. A number or a function keeps the object, and the hash operator
    counts on the object of the left map.

    It compares and hashes by identity, because a mark that is its own map
    object is the identity.

    map: OWN for a new map object, whose id is this mark; else the id it
        keeps, the identifier of a registered map or the mark of a new one,
        or None for a map that has no id
    first: the first count of a counted map (see
        ClassicTranslator._first_counts()), which is
        the content itself for the first count; None for a map that is not
        counted. Set after the content is made, because the content that
        carries the mark is the first count.
    text: the command as the classic algebra writes it, unfolded, where the
        content was folded to a number (a count changed by numbers, a value
        of a time function at an offset); None for the content itself. The
        classic algebra compares this text in merge(), and the profile folds
        a count plus 0 to the number of the count.
    bare: True for a neighbour map, a new map object whose command is its own
        reference; see ClassicTranslator._has_command().
    """

    map: object = OWN
    first: Content | None = None
    text: Content | None = None
    bare: bool = False


class SeriesNotes:
    """Notes about series, found by identity

    A series is not hashable, so the notes are keyed by id(). Each entry holds
    its series: once a series is gone, a later one can take its id and would
    read the note of another.
    """

    def __init__(self):
        self._notes = {}

    def note(self, series, value=None):
        """Remember value for series"""
        self._notes[id(series)] = (series, value)

    def get(self, series):
        """Return the value noted for series, or None"""
        entry = self._notes.get(id(series))
        return None if entry is None else entry[1]

    def __contains__(self, series):
        return id(series) in self._notes
