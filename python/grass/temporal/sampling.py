"""
Sampling functions for space time datasets

Usage:

.. code-block:: python

    import grass.temporal as tgis

    tgis.register_maps_in_space_time_dataset(type, name, maps)

SPDX-FileCopyrightText: 2012-2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from .algebra.sources import source
from .datetime_math import time_delta_to_relative_time
from .db import SQLDatabaseInterfaceConnection
from .factory import dataset_factory
from .related_maps import (
    method_relations,
    related_per_granule,
    sampler_refused,
    with_gaps,
)
from .state import get_current_mapset, get_tgis_message_interface


def _map_object(stds, ident, extent, space):
    """A map object of the type of the dataset with the given extents

    The objects of the map matrix hold the identifier and the spatio-temporal
    extent, as the objects that get_registered_maps_as_objects() makes; whoever
    needs more calls select() on them.
    """
    map_ = stds.get_new_map_instance(ident)
    if extent.unit is None:
        map_.set_absolute_time(extent.start, extent.end)
    else:
        map_.set_relative_time(extent.start, extent.end, extent.unit)
    map_.set_spatial_extent_from_values(
        space.north, space.south, space.east, space.west, space.top, space.bottom
    )
    return map_


def _map_matrix(sampler, stds, granules, rows):
    """The entries of the map matrix of one input dataset

    :param sampler: the sampler dataset, whose maps the granules are
    :param stds: the input dataset
    :param granules: the Series of the granules, gap slots included
    :param rows: the slots of the input related to each granule
    :return: for each granule a dictionary with the map object of the
        "granule" and the list of its "samples"; a granule without a related
        map has one sample without an identifier, with the extents of the
        granule
    """
    matrix = []
    for granule, related in zip(granules.slots, rows, strict=True):
        samples = [
            _map_object(stds, slot.content.ident, slot.extent, slot.space)
            for slot in related
        ] or [_map_object(stds, None, granule.extent, granule.space)]
        matrix.append(
            {
                "granule": _map_object(
                    sampler, granule.origin, granule.extent, granule.space
                ),
                "samples": samples,
            }
        )
    return matrix


def sample_stds_by_stds_topology(
    intype,
    sampletype,
    inputs,
    sampler,
    header,
    separator,
    method,
    spatial: bool = False,
    print_only: bool = True,
):
    """Sample the input space time datasets with a sample
    space time dataset, return the created map matrix and optionally
    print the result to stdout

     In case multiple maps are located in the current granule,
     the map names are separated by comma.

     In case a layer is present, the names map ids are extended
     in this form: "name:layer@mapset"

     Attention: Do not use the comma as separator for printing

     :param intype: Type of the input space time dataset (strds, stvds or str3ds)
     :param sampletype: Type of the sample space time datasets (strds, stvds or str3ds)
     :param inputs: Name or comma separated names of space time datasets or
                    a list of map names
     :param sampler: Name of a space time dataset used for temporal sampling
     :param header: Set True to print column names
     :param separator: The field separator character between the columns
     :param method: The method to be used for temporal sampling
                    (start,during,contain,overlap,equal) as comma separated
                    string or as a list of methods
     :param spatial: Perform spatial overlapping check
     :param print_only: If set True (default) then the result of the
                        sampling will be printed to stdout, if set to False
                        the resulting map matrix will be returned.

     :return: The map matrix or None if nothing found
    """
    mapset = get_current_mapset()
    msgr = get_tgis_message_interface()

    # Make a method list
    if not issubclass(type(method), type([])):
        method = method.split(",")

    # Split the inputs
    if not issubclass(type(inputs), type([])):
        inputs = inputs.split(",")

    sts = []

    for input in inputs:
        id = input if input.find("@") >= 0 else input + "@" + mapset
        st = dataset_factory(intype, id)
        sts.append(st)

    sid = sampler if sampler.find("@") >= 0 else sampler + "@" + mapset
    sst = dataset_factory(sampletype, sid)

    dbif = SQLDatabaseInterfaceConnection()
    dbif.connect()

    for st in sts:
        if st.is_in_db(dbif) is False:
            msgr.fatal(_("Dataset <%s> not found in temporal database") % (st.get_id()))
        st.select(dbif)

    if sst.is_in_db(dbif) is False:
        msgr.fatal(_("Dataset <%s> not found in temporal database") % (sid))

    sst.select(dbif)

    if separator is None or separator == "" or separator.find(",") >= 0:
        separator = " | "

    try:
        names = method_relations(method)
    except ValueError as error:
        msgr.fatal(str(error))
    granules = None
    mapmatrizes = []
    for st in sts:
        # An input that cannot be sampled is reported and left out
        if sampler_refused(sst, st, msgr):
            continue
        # Only an interval sampler can be given gaps, so this waits for the
        # check above
        if granules is None:
            granules = with_gaps(source(sst.get_id(), stds_type=sampletype))
        rows = related_per_granule(
            granules,
            names,
            source(st.get_id(), stds_type=intype),
            spatial=spatial,
        )
        mapmatrix = _map_matrix(sst, st, granules, rows)
        if mapmatrix:
            mapmatrizes.append(mapmatrix)

    if len(mapmatrizes) > 0:
        # Simply return the map matrix
        if not print_only:
            dbif.close()
            return mapmatrizes

        if header:
            string = ""
            string += "%s%s" % (sst.get_id(), separator)
            for st in sts:
                string += "%s%s" % (st.get_id(), separator)
            string += "%s%s" % ("start_time", separator)
            string += "%s%s" % ("end_time", separator)
            string += "%s%s" % ("interval_length", separator)
            string += "%s" % ("distance_from_begin")
            print(string)

        first_time, dummy = mapmatrizes[0][0]["granule"].get_temporal_extent_as_tuple()

        for i in range(len(mapmatrizes[0])):
            mapname_list = []
            for mapmatrix in mapmatrizes:
                mapnames = ""
                count = 0
                entry = mapmatrix[i]
                for sample in entry["samples"]:
                    if count == 0:
                        mapnames += str(sample.get_id())
                    else:
                        mapnames += ",%s" % str(sample.get_id())
                    count += 1
                mapname_list.append(mapnames)

            entry = mapmatrizes[0][i]
            map = entry["granule"]

            start, end = map.get_temporal_extent_as_tuple()
            delta = end - start if end else None
            delta_first = start - first_time

            if map.is_time_absolute():
                if end:
                    delta = time_delta_to_relative_time(delta)
                delta_first = time_delta_to_relative_time(delta_first)

            string = ""
            string += "%s%s" % (map.get_id(), separator)
            for mapnames in mapname_list:
                string += "%s%s" % (mapnames, separator)
            string += "%s%s" % (start, separator)
            string += "%s%s" % (end, separator)
            string += "%s%s" % (delta, separator)
            string += "%s" % (delta_first)
            print(string)

    dbif.close()
    if len(mapmatrizes) > 0:
        return mapmatrizes

    return None
