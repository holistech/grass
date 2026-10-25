"""The six dataset types of the temporal framework in one place

Three kinds of maps (raster, 3D raster, vector) and the three kinds of space
time datasets that hold them (strds, str3ds, stvds) differ in their names:
the names the user may type, the tables of the temporal database and the
prefix of the functions of the C interface. This module is the only table of
these names; the entry functions of the library look a type up here and
never compare a type with a list of strings of their own.

A name can mean different things to different entry functions. "raster" is
a map to dataset_factory() but names the space time dataset type in
open_old_stds(). kind_of() resolves the name as it is written; stds_kind_of()
resolves it to the space time dataset type.

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass

# The parts of a table name. Maps and datasets have a table of each part
# except "register": a map keeps the list of its datasets in <map>_stds_register,
# a dataset keeps its maps in a table of its own, called
# <map>_map_register_<32 hex digits> after a random identifier.
_PARTS = (
    "base",
    "spatial_extent",
    "absolute_time",
    "relative_time",
    "metadata",
    "register",
    "view_abs_time",
    "view_rel_time",
)


@dataclass(frozen=True)
class Kind:
    """One dataset type

    :param name: The canonical name, equal to what get_type() of the dataset
                 classes returns
    :param aliases: Every name that selects this kind, the canonical name
                    included
    :param is_stds: True for a space time dataset, False for a map
    :param map_kind: Name of the kind of the maps a space time dataset holds
    :param stds_kind: Name of the kind of the datasets that hold a map
    :param table_prefix: Prefix of the tables and views of the kind
    :param ciface_prefix: Prefix of the functions of the C interface that
                          read and write a map, None for datasets
    """

    name: str
    aliases: tuple[str, ...]
    is_stds: bool
    map_kind: str | None
    stds_kind: str | None
    table_prefix: str
    ciface_prefix: str | None

    def table(self, part: str) -> str:
        """Return the name of the table or view of a part

        The parts are base, spatial_extent, absolute_time, relative_time,
        metadata, register, view_abs_time and view_rel_time. For a space time
        dataset register is only the prefix of the register tables; the
        table of a dataset ends in an identifier of its own.

        :raises ValueError: for any other part
        """
        if part not in _PARTS:
            msg = f"Unknown table part <{part}>, use one of {', '.join(_PARTS)}"
            raise ValueError(msg)
        if part == "register":
            if self.is_stds:
                return f"{KINDS[self.map_kind].table_prefix}_map_register"
            return f"{self.table_prefix}_stds_register"
        return f"{self.table_prefix}_{part}"


KINDS: dict[str, Kind] = {
    kind.name: kind
    for kind in (
        Kind("raster", ("raster", "rast"), False, None, "strds", "raster", "raster"),
        Kind(
            "raster3d",
            ("raster3d", "raster_3d", "rast3d"),
            False,
            None,
            "str3ds",
            "raster3d",
            "raster3d",
        ),
        Kind("vector", ("vector", "vect"), False, None, "stvds", "vector", "vector"),
        Kind("strds", ("strds",), True, "raster", None, "strds", None),
        Kind("str3ds", ("str3ds",), True, "raster3d", None, "str3ds", None),
        Kind("stvds", ("stvds",), True, "vector", None, "stvds", None),
    )
}

_BY_ALIAS: dict[str, Kind] = {
    alias: kind for kind in KINDS.values() for alias in kind.aliases
}

# Every name that selects a map kind
MAP_ALIASES = frozenset(
    alias for kind in KINDS.values() if not kind.is_stds for alias in kind.aliases
)


def find_kind(name: str) -> Kind | None:
    """Return the kind that name selects, None for an unknown name"""
    return _BY_ALIAS.get(name)


def kind_of(name: str) -> Kind:
    """Return the kind that name selects

    :raises ValueError: for an unknown name
    """
    kind = _BY_ALIAS.get(name)
    if kind is None:
        msg = f"Unknown dataset type <{name}>, use one of {', '.join(_BY_ALIAS)}"
        raise ValueError(msg)
    return kind


def stds_kind_of(name: str) -> Kind:
    """Return the space time dataset kind that name selects

    A map type selects the kind of the datasets that hold such maps, so
    "raster" gives strds and "vect" gives stvds.

    :raises ValueError: for an unknown name
    """
    kind = kind_of(name)
    return KINDS[kind.stds_kind] if kind.stds_kind else kind
