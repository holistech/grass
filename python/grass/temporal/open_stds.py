"""Functions to open or create space time datasets

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.register_maps_in_space_time_dataset(type, name, maps)

SPDX-FileCopyrightText: 2012-2026 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from __future__ import annotations

import contextlib

import grass.script as gs
from grass.exceptions import FatalError

from .abstract_map_dataset import AbstractMapDataset
from .db import connection
from .factory import dataset_factory
from .kinds import find_kind, stds_kind_of
from .state import get_current_mapset, get_tgis_message_interface


def _parse_id(
    ident: str, stds_type: str = "strds"
) -> tuple[str, str | None, str | None]:
    """Parse parts of a user given dataset name.

    :param ident: The id of a space time dataset
    :param stds_type: The type of the dataset; only "strds" splits a
                      semantic label ("name.label") off the name, for all
                      other types the dot stays in the name

    :return: Tuple with ID components: name, mapset, semantic_label
    """
    msgr = get_tgis_message_interface()
    name = ident

    mapset = None
    if "@" in ident:
        name, mapset = ident.split("@", 1)

    semantic_label = None
    if "." in name and stds_type == "strds":
        name, semantic_label = name.split(".", 1)
        if "." in semantic_label:
            msgr.fatal(_("Invalid semantic_label <%s>") % semantic_label)

    return name, mapset, semantic_label


def _stds_if_in_db(ds_id, stds_type, semantic_label, dbif):
    """Return the dataset with the id if the temporal database holds it, else None"""
    # A map type selects the datasets that hold such maps: "raster" is a
    # space time raster dataset here.
    stds_kind = stds_kind_of(stds_type).name
    sp = dataset_factory(stds_kind, ds_id)
    # Set the semantic label if it was given
    if semantic_label and stds_kind == "strds":
        sp.set_semantic_label(semantic_label)

    with contextlib.suppress(SystemExit, FatalError):
        if sp.is_in_db(dbif):
            return sp
    return None


def _find_old_stds(name, mapset, stds_type, semantic_label, dbif):
    """Find the dataset in the given mapset, else in the current one and the search path

    A name without a mapset is searched in the mapsets that the connection had
    when it was opened, not in a mapset that a name given with it added since
    (dbif.search_path_mapsets, not dbif.tgis_mapsets).
    """
    if mapset:
        return _stds_if_in_db(f"{name}@{mapset}", stds_type, semantic_label, dbif)
    # Check current mapset first
    sp = _stds_if_in_db(
        f"{name}@{get_current_mapset()}", stds_type, semantic_label, dbif
    )
    if sp:
        return sp
    for tgis_mapset in dbif.search_path_mapsets:
        if tgis_mapset == get_current_mapset():
            continue
        sp = _stds_if_in_db(f"{name}@{tgis_mapset}", stds_type, semantic_label, dbif)
        if sp:
            return sp
    return None


def find_stds_id(name: str, type: str, dbif=None) -> str:
    """Return the id of the dataset that a name selects, whole as it is given

    Without a mapset in name the current mapset is searched first, then the
    search path, as open_old_stds() does. Unlike open_old_stds() no text after
    a dot is read as a semantic label, and a dataset that does not exist is not
    an error: the id then has the current mapset, so that the caller reports
    the dataset as not found with its usual message.

    :param name: The name of the dataset, with or without the mapset
    :param type: The type of the dataset (strds, str3ds, stvds)
    :param dbif: The optional database interface to be used
    :return: The id name@mapset
    """
    bare, _at, mapset = name.partition("@")
    with connection(dbif) as dbif:
        sp = _find_old_stds(bare, mapset or None, type, None, dbif)
    if sp:
        return sp.get_id()
    return f"{bare}@{mapset or get_current_mapset()}"


def open_old_stds(name, type, dbif=None, *, whole_name_first=True):
    """This function opens an existing space time dataset and return the
    created and initialized object of the specified type.

    This function will call exit() or raise a
    grass.pygrass.messages.FatalError in case the type is wrong,
    or the space time dataset was not found.

    :param name: The name of the space time dataset, if the name does not
                 contain the mapset (name@mapset) then the space time dataset
                 is searched first in the current mapset, then on the search
                 path. The mapset of the first match will be used to identify
                 the space time dataset.
    :param type: The type of the space time dataset (strd, str3ds, stvds,
                 raster, vector, raster3d)
    :param dbif: The optional database interface to be used
    :param whole_name_first: Whether the name with a dot is tried whole before
                             the text after the dot is read as a semantic
                             label. The classic algebra passes False, as it
                             always read the label.

    :return: New stds object

    """
    msgr = get_tgis_message_interface()
    stds_type = type
    kind = find_kind(stds_type)
    if kind is None:
        msgr.fatal(_("Unknown type: %s") % (stds_type))

    with connection(dbif) as dbif:
        sp = None
        # A dataset of an older release can have a dot in its name. The whole
        # name is tried before a label is split off, so that such a dataset
        # can be read and removed; "name.label" then still selects the maps
        # of the dataset "name" unless a dataset of that name exists.
        bare, _at, whole_mapset = name.partition("@")
        if whole_name_first and "." in bare and stds_kind_of(stds_type).name == "strds":
            sp = _find_old_stds(bare, whole_mapset or None, stds_type, None, dbif)
        if not sp:
            # Check if the dataset name contains the mapset and the semantic
            # label as well
            name, mapset, semantic_label = _parse_id(name, stds_type=stds_type)
            sp = _find_old_stds(name, mapset, stds_type, semantic_label, dbif)
        if not sp:
            msgr.fatal(
                _("Space time dataset <%(name)s> of type <%(sp)s> not found")
                % {"name": name, "sp": stds_type},
            )
        # Read content from temporal database
        sp.select(dbif)

        return sp


def check_new_stds_name(name: str) -> None:
    """Refuse a dot in the name part of a new space time dataset

    The name part is the text before an optional "@mapset". A dot in it was
    accepted inconsistently: a strds dropped everything after the dot as a
    semantic label, the other types kept the dot in the name. Reading an
    existing dataset is not affected, so "name.label" still selects the maps
    of a strds with that label and a dataset that already has a dot in its
    name stays usable.

    The check runs on the name as the user gave it, before _parse_id() can
    split it, so that callers passing a map type such as "raster" are covered
    too.

    :param name: The name of the new space time dataset, with or without
                 the mapset

    This function will raise a FatalError if the name contains a dot.
    """
    if "." in name.split("@", 1)[0]:
        get_tgis_message_interface().fatal(
            _(
                "<{}> is not a valid name for a new space time dataset: "
                "a dot is not allowed"
            ).format(name)
        )


def check_new_stds(name, type, dbif=None, overwrite: bool = False):
    """Check if a new space time dataset of a specific type can be created

    :param name: The name of the new space time dataset
    :param type: The type of the new space time dataset (strd, str3ds,
                 stvds, raster, vector, raster3d)
    :param dbif: The temporal database interface to be used
    :param overwrite: Flag to allow overwriting

    :return: A space time dataset object that must be filled with
            content before insertion in the temporal database

    This function will raise a FatalError in case of an error.
    """
    stds_type = type
    # Get the current mapset to create the id of the space time dataset

    msgr = get_tgis_message_interface()

    check_new_stds_name(name)
    given_name = name
    name, mapset, _semantic_label = _parse_id(name, stds_type=stds_type)
    # An empty name (".dot" of a strds is split into the name "" and the
    # label "dot") would be stored under the id "@mapset" and could never be
    # found by the name it was given. The command line parser only warns about
    # a name that G_legal_filename() refuses, so the check is made here.
    if not gs.legal_name(name):
        msgr.fatal(_("<%s> is not a valid name for a space time dataset") % given_name)
    if mapset:
        if mapset != get_current_mapset():
            msgr.fatal(
                _("Space time datasets can only be created in the current mapset"),
            )
        id_ = f"{name}@{mapset}"
    else:
        id_ = f"{name}@{get_current_mapset()}"

    if find_kind(stds_type) is None:
        msgr.error(_("Unknown type: %s") % (stds_type))
        return None
    sp = dataset_factory(stds_kind_of(stds_type).name, id_)

    with connection(dbif) as dbif:
        if sp.is_in_db(dbif) and overwrite is False:
            msgr.fatal(
                _(
                    "Space time %(sp)s dataset <%(name)s> is already in the"
                    " database. Use the overwrite flag.",
                )
                % {"sp": sp.get_new_map_instance(None).get_type(), "name": name},
            )

        return sp


def open_new_stds(
    name,
    type,
    temporaltype,
    title,
    descr,
    semantic,
    dbif=None,
    overwrite: bool = False,
):
    """Create a new space time dataset of a specific type

    :param name: The name of the new space time dataset
    :param type: The type of the new space time dataset (strd, str3ds,
                 stvds, raster, vector, raster3d)
    :param temporaltype: The temporal type (relative or absolute)
    :param title: The title
    :param descr: The dataset description
    :param semantic: Semantical information
    :param dbif: The temporal database interface to be used
    :param overwrite: Flag to allow overwriting

    :return: The new created space time dataset

    This function will raise a FatalError in case of an error.
    """
    with connection(dbif) as dbif:
        msgr = get_tgis_message_interface()
        sp = check_new_stds(name, type, dbif, overwrite)

        if sp.is_in_db(dbif):
            msgr.warning(
                _(
                    "Overwriting space time %(sp)s dataset <%(name)s> and "
                    "unregistering all maps",
                )
                % {"sp": sp.get_new_map_instance(None).get_type(), "name": name},
            )
            id_ = sp.get_id()
            sp.delete(dbif)
            sp = sp.get_new_instance(id_)

        msgr.verbose(
            _("Creating a new space time %s dataset")
            % sp.get_new_map_instance(None).get_type(),
        )

        sp.set_initial_values(
            temporal_type=temporaltype,
            semantic_type=semantic,
            title=title,
            description=descr,
        )

        sp.insert(dbif)

        return sp


def check_new_map_dataset(
    name,
    layer=None,
    type="raster",
    overwrite: bool = False,
    dbif=None,
):
    """Check if a new map dataset of a specific type can be created in
     the temporal database

    :param name: The name of the new map dataset
    :param layer: The layer of the new map dataset
    :param type: The type of the new map dataset (raster, vector, raster3d)
    :param dbif: The temporal database interface to be used
    :param overwrite: Flag to allow overwriting

    :return: A map dataset object

    This function will raise a FatalError in case of an error.
    """
    mapset = get_current_mapset()
    msgr = get_tgis_message_interface()

    with connection(dbif) as dbif:
        map_id = AbstractMapDataset.build_id(name, mapset, layer)

        new_map = dataset_factory(type, map_id)
        # Check if new map is in the temporal database
        if new_map.is_in_db(dbif) and not overwrite:
            msgr.fatal(
                _(
                    "Map <%s> is already in temporal database,"
                    " use overwrite flag to overwrite",
                )
                % (map_id),
            )

        return new_map


def open_new_map_dataset(
    name,
    layer=None,
    type="raster",
    temporal_extent=None,
    overwrite: bool = False,
    dbif=None,
):
    """Create a new map dataset object of a specific type that can be
     registered in the temporal database

    :param name: The name of the new map dataset
    :param layer: The layer of the new map dataset
    :param type: The type of the new map dataset (raster, vector, raster3d)
    :param dbif: The temporal database interface to be used
    :param overwrite: Flag to allow overwriting

    :return: A map dataset object

    """
    with connection(dbif) as dbif:
        new_map = check_new_map_dataset(name, layer, type, overwrite, dbif)

        # Check if new map is in the temporal database
        if new_map.is_in_db(dbif):
            # Remove the existing temporal database entry
            map_id = new_map.get_id()
            new_map.delete(dbif)
            new_map = new_map.get_new_instance(map_id)

        if temporal_extent:
            new_map.set_temporal_extent(temporal_extent)

        return new_map
