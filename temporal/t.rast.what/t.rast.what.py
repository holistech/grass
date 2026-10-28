#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.what
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Sample a space time raster dataset at specific vector point
#               coordinates and write the output to stdout using different
#               layouts
# SPDX-FileCopyrightText: 2015-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Sample a space time raster dataset at specific vector point coordinates and write the output to stdout using different layouts
# % keyword: temporal
# % keyword: sampling
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_V_INPUT
# % key: points
# % required: no
# %end

# %option G_OPT_M_COORDS
# % required: no
# % description: Comma separated list of coordinates
# %end

# %option G_OPT_STRDS_INPUT
# % key: strds
# %end

# %option G_OPT_F_OUTPUT
# % required: no
# % description: Name for the output file or "-" in case stdout should be used
# % answer: -
# %end

# %option G_OPT_T_WHERE
# %end

# %option G_OPT_M_NULL_VALUE
# %end

# %option G_OPT_F_SEP
# %end

# %option
# % key: order
# % type: string
# % description: Sort the maps by category
# % required: no
# % multiple: yes
# % options: id, name, creator, mapset, creation_time, modification_time, start_time, end_time, north, south, west, east, min, max
# % answer: start_time
# %end

# %option
# % key: layout
# % type: string
# % description: The layout of the output. One point per row (row), one point per column (col), all timsteps in one row (timerow)
# % required: no
# % multiple: no
# % options: row, col, timerow
# % answer: row
# %end

# %option
# % key: nprocs
# % type: integer
# % description: Number of r.what processes to run in parallel
# % required: no
# % multiple: no
# % answer: 1
# %end

# %flag
# % key: n
# % description: Output header row
# %end

# %flag
# % key: i
# % description: Use stdin as input and ignore coordinates and point option
# %end

# %flag
# % key: v
# % description: Show the category for vector points map
# %end

import copy
import sys
from contextlib import ExitStack, nullcontext

import grass.script as gs
from grass.exceptions import CalledModuleError

############################################################################


def check_options(coordinates, points, use_stdin, vcat):
    """Stop with a message when the options contradict each other"""
    if coordinates and points:
        gs.fatal(_("Options coordinates and points are mutually exclusive"))

    if not coordinates and not points and not use_stdin:
        gs.fatal(
            _(
                "Please specify the coordinates, the points option or use the 'i' flag "
                "to pipe coordinate positions to t.rast.what from stdin, to provide "
                "the sampling coordinates"
            )
        )

    if vcat and not points:
        gs.fatal(_("Flag 'v' required option 'points'"))


def read_stdin_coordinates():
    """Read the coordinates from stdin; return them and whether they have sites

    The first line decides: three or more columns mean that the third one is
    the name or the ID of the site.
    """
    coordinates_stdin = str(sys.__stdin__.read())
    stdin_length = len(coordinates_stdin.split("\n", maxsplit=1)[0].split())
    return coordinates_stdin, stdin_length >= 3


def open_maps(strds, where, order):
    """Return the maps of the dataset that where selects, in the given order"""
    import grass.temporal as tgis

    # Make sure the temporal database exists
    tgis.init()
    # We need a database interface
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    sp = tgis.open_old_stds(strds, "strds", dbif)
    try:
        maps = sp.get_registered_maps_as_objects(where=where, order=order, dbif=dbif)
    except tgis.SQLStatementError as error:
        dbif.close()
        gs.fatal(_("Invalid where condition <{}>: {}").format(where, error))
    dbif.close()
    if not maps:
        gs.fatal(_("Space time raster dataset <%s> is empty") % sp.get_id())
    return maps


def prepare_r_what(
    *,
    separator,
    vcat,
    null_value,
    use_stdin,
    coordinates_stdin,
    points,
    coordinates,
):
    """Return the r.what call that every process copies and gives its maps

    stdin comes before points and points before coordinates.
    """
    import grass.pygrass.modules as pymod

    overwrite = gs.overwrite()

    flags = ""
    if vcat is True:
        flags += "v"

    # Flag -i comes first: its description says it ignores the coordinates option.
    if use_stdin:
        r_what = pymod.Module(
            "r.what",
            map="dummy",
            output="dummy",
            run_=False,
            separator=separator,
            stdin_=coordinates_stdin,
            overwrite=overwrite,
            flags=flags,
            null_value=null_value,
            quiet=True,
        )
    elif points:
        r_what = pymod.Module(
            "r.what",
            map="dummy",
            output="dummy",
            run_=False,
            separator=separator,
            points=points,
            overwrite=overwrite,
            flags=flags,
            null_value=null_value,
            quiet=True,
        )
    elif coordinates:
        # Create a list of values
        coord_list = coordinates.split(",")
        r_what = pymod.Module(
            "r.what",
            map="dummy",
            output="dummy",
            run_=False,
            separator=separator,
            coordinates=coord_list,
            overwrite=overwrite,
            flags=flags,
            null_value=null_value,
            quiet=True,
        )
    else:
        gs.error(_("Please specify points or coordinates"))
    return r_what


def split_into_loops(num_maps, nprocs):
    """Divide the maps into loops of at most 400 maps per process

    Return the number of loops, the number of maps that no loop takes, the
    number of maps per process and the number of maps that the first process
    of each loop takes in addition.
    """
    # 400 Maps is the absolute maximum in r.what
    # We need to determie the number of maps that can be processed
    # in parallel

    # First estimate the number of maps per process. We use 400 maps
    # simultaneously as maximum for a single process

    num_loops = int(num_maps / (400 * nprocs))
    remaining_maps = num_maps % (400 * nprocs)

    if num_loops == 0:
        num_loops = 1
        remaining_maps = 0

    # Compute the number of maps for each process
    maps_per_loop = int((num_maps - remaining_maps) / num_loops)
    maps_per_process = int(maps_per_loop / nprocs)
    remaining_maps_per_loop = maps_per_loop % nprocs
    return num_loops, remaining_maps, maps_per_process, remaining_maps_per_loop


def sample_remaining_maps(
    *,
    r_what,
    maps,
    nprocs,
    remaining_maps,
    count,
    output_files,
    output_time_list,
    queue,
):
    """Sample the maps that the loops left

    Up to 100 maps run in one process, more are spread over all processes.
    """
    if remaining_maps <= 100:
        # Use a single process if less then 100 maps
        map_names = []
        map_list = []
        for _i in range(remaining_maps):
            map = maps[count]
            map_names.append(map.get_id())
            map_list.append(map)
            count += 1
        remain_file_name = gs.tempfile() + "_remain"
        output_files.append(remain_file_name)
        output_time_list.append(map_list)
        mod = copy.deepcopy(r_what)
        mod(map=map_names, output=remain_file_name)
        queue.put(mod)
    else:
        maps_per_process = int(remaining_maps / nprocs)
        remaining_maps_per_loop = remaining_maps % nprocs

        file_name = gs.tempfile() + "_remain"
        process_loop(
            nprocs,
            maps,
            file_name,
            count,
            maps_per_process,
            remaining_maps_per_loop,
            output_files,
            output_time_list,
            r_what,
            queue,
        )


def run_r_what(r_what, maps, nprocs):
    """Sample the maps in parallel processes

    Return the output file of each process and the maps it sampled, both in
    the order of the maps.
    """
    import grass.pygrass.modules as pymod

    nprocs = min(len(maps), nprocs)

    # The module queue for parallel execution
    process_queue = pymod.ParallelModuleQueue(int(nprocs))
    num_maps = len(maps)

    num_loops, remaining_maps, maps_per_process, remaining_maps_per_loop = (
        split_into_loops(num_maps, nprocs)
    )

    # We put the output files in an ordered list
    output_files = []
    output_time_list = []

    # A failing r.what surfaces at put() or wait() of the queue.
    try:
        count = 0
        for loop in range(num_loops):
            file_name = gs.tempfile() + "_%i" % (loop)
            count = process_loop(
                nprocs,
                maps,
                file_name,
                count,
                maps_per_process,
                remaining_maps_per_loop,
                output_files,
                output_time_list,
                r_what,
                process_queue,
            )

        process_queue.wait()

        gs.verbose(
            "Number of raster map layers remaining for sampling %i" % (remaining_maps)
        )
        if remaining_maps > 0:
            sample_remaining_maps(
                r_what=r_what,
                maps=maps,
                nprocs=nprocs,
                remaining_maps=remaining_maps,
                count=count,
                output_files=output_files,
                output_time_list=output_time_list,
                queue=process_queue,
            )

        # Wait for unfinished processes
        process_queue.wait()
    except CalledModuleError as error:
        gs.fatal(_("Error running r.what: {}").format(error))
    return output_files, output_time_list


def write_output(
    layout,
    separator,
    output_files,
    output_time_list,
    output,
    write_header,
    site_input,
    vcat,
):
    """Put the output files of r.what together in the layout that was asked for"""
    if layout == "row":
        write = one_point_per_row_output
    elif layout == "col":
        write = one_point_per_col_output
    else:
        write = one_point_per_timerow_output
    write(
        separator,
        output_files,
        output_time_list,
        output,
        write_header,
        site_input,
        vcat,
    )


def main(options, flags):
    # Get the options
    points = options["points"]
    coordinates = options["coordinates"]
    strds = options["strds"]
    output = options["output"]
    where = options["where"]
    order = options["order"]
    layout = options["layout"]
    null_value = options["null_value"]
    separator = gs.separator(options["separator"])

    nprocs = int(options["nprocs"])
    write_header = flags["n"]
    use_stdin = flags["i"]
    vcat = flags["v"]

    check_options(coordinates, points, use_stdin, vcat)

    coordinates_stdin = ""
    site_input = False
    if use_stdin:
        coordinates_stdin, site_input = read_stdin_coordinates()

    maps = open_maps(strds, where, order)
    r_what = prepare_r_what(
        separator=separator,
        vcat=vcat,
        null_value=null_value,
        use_stdin=use_stdin,
        coordinates_stdin=coordinates_stdin,
        points=points,
        coordinates=coordinates,
    )
    output_files, output_time_list = run_r_what(r_what, maps, nprocs)

    write_output(
        layout,
        separator,
        output_files,
        output_time_list,
        output,
        write_header,
        site_input,
        vcat,
    )


############################################################################


def one_point_per_row_output(
    separator, output_files, output_time_list, output, write_header, site_input, vcat
):
    """Write one point per row
    output is of type: x,y,start,end,value
    """
    # open the output file for writing
    with open(output, "w") if output != "-" else nullcontext(sys.stdout) as out_file:
        if write_header is True:
            out_str = ""
            if vcat:
                out_str += "cat{sep}"
            if site_input:
                out_str += "x{sep}y{sep}site{sep}start{sep}end{sep}value\n"
            else:
                out_str += "x{sep}y{sep}start{sep}end{sep}value\n"
            out_file.write(out_str.format(sep=separator))

        # Every r.what output file holds the same points in the same order, so
        # reading the files side by side lists the rows point by point in the
        # time order of the maps, whatever the number of processes was.
        with ExitStack() as stack:
            in_files = []
            for file_name in output_files:
                gs.verbose(_("Transforming r.what output file %s") % (file_name))
                in_files.append(stack.enter_context(open(file_name)))
            for point_lines in zip(*in_files, strict=True):
                for line, map_list in zip(point_lines, output_time_list, strict=True):
                    line = line.split(separator)
                    if vcat:
                        cat = line[0]
                        x = line[1]
                        y = line[2]
                        values = line[4:]
                        if site_input:
                            site = line[3]
                            values = line[5:]

                    else:
                        x = line[0]
                        y = line[1]
                        if site_input:
                            site = line[2]
                        values = line[3:]

                    for i in range(len(values)):
                        start, end = map_list[i].get_temporal_extent_as_tuple()
                        cat_str = f"{cat}{separator}" if vcat else ""
                        if site_input:
                            coor_string = (
                                "%(x)10.10f%(sep)s%(y)10.10f%(sep)s%(site_name)s%(sep)s"
                                % (
                                    {
                                        "x": float(x),
                                        "y": float(y),
                                        "site_name": str(site),
                                        "sep": separator,
                                    }
                                )
                            )
                        else:
                            coor_string = "%(x)10.10f%(sep)s%(y)10.10f%(sep)s" % (
                                {"x": float(x), "y": float(y), "sep": separator}
                            )
                        time_string = "%(start)s%(sep)s%(end)s%(sep)s%(val)s\n" % (
                            {
                                "start": str(start),
                                "end": str(end),
                                "val": (values[i].strip()),
                                "sep": separator,
                            }
                        )

                        out_file.write(cat_str + coor_string + time_string)


############################################################################


def one_point_per_col_output(
    separator, output_files, output_time_list, output, write_header, site_input, vcat
):
    """Write one point per col
    output is of type:
    start,end,point_1 value,point_2 value,...,point_n value

    Each row represents a single raster map, hence a single time stamp
    """
    # open the output file for writing

    first = True
    with open(output, "w") if output != "-" else nullcontext(sys.stdout) as out_file:
        for count in range(len(output_files)):
            file_name = output_files[count]
            gs.verbose(_("Transforming r.what output file %s") % (file_name))
            with open(file_name) as in_file:
                lines = in_file.readlines()

            matrix = [line.split(separator) for line in lines]

            num_cols = len(matrix[0])

            if first is True and write_header is True:
                out_str = "start%(sep)send" % ({"sep": separator})

                # Define different separator for coordinates and sites
                coor_sep = ";" if separator == "," else ","

                for row in matrix:
                    if vcat:
                        cat = row[0]
                        x = row[1]
                        y = row[2]
                        out_str += f"{separator}{cat}{coor_sep}{float(x):10.10f}{coor_sep}{float(y):10.10f}"
                        if site_input:
                            site = row[3]
                            out_str += f"{coor_sep}{site}"
                    else:
                        x = row[0]
                        y = row[1]
                        out_str += (
                            f"{separator}{float(x):10.10f}{coor_sep}{float(y):10.10f}"
                        )
                        if site_input:
                            site = row[2]
                            out_str += f"{coor_sep}{site}"

                out_file.write(out_str + "\n")

            first = False

            ncol = 4 if vcat else 3
            for col in range(num_cols - ncol):
                start, end = output_time_list[count][col].get_temporal_extent_as_tuple()
                time_string = "%(start)s%(sep)s%(end)s" % (
                    {"start": str(start), "end": str(end), "sep": separator}
                )
                out_file.write(time_string)
                for row in range(len(matrix)):
                    value = matrix[row][col + ncol]
                    out_file.write(
                        "%(sep)s%(value)s"
                        % ({"sep": separator, "value": value.strip()})
                    )
                out_file.write("\n")


############################################################################


def one_point_per_timerow_output(
    separator, output_files, output_time_list, output, write_header, site_input, vcat
):
    """Use the original layout of the r.what output and print instead of
    the raster names, the time stamps as header

    One point per line for all time stamps:
     x|y|1991-01-01 00:00:00;1991-01-02 00:00:00|1991-01-02 00:00:00;1991-01-03 00:00:00|1991-01-03 00:00:00;1991-01-04 00:00:00|1991-01-04 00:00:00;1991-01-05 00:00:00
     3730731.49590371|5642483.51236521|6|8|7|7
     3581249.04638104|5634411.97526282|5|8|7|7
    """  # noqa: E501

    matrix = []
    header = ""

    first = True
    for count in range(len(output_files)):
        file_name = output_files[count]
        gs.verbose("Transforming r.what output file %s" % (file_name))
        map_list = output_time_list[count]

        if write_header:
            if first is True:
                header = f"cat{separator}" if vcat else ""
                if site_input:
                    header += "x%(sep)sy%(sep)ssite" % ({"sep": separator})
                else:
                    header += "x%(sep)sy" % ({"sep": separator})
            for map in map_list:
                start, end = map.get_temporal_extent_as_tuple()
                time_string = "%(sep)s%(start)s;%(end)s" % (
                    {"start": str(start), "end": str(end), "sep": separator}
                )
                header += time_string

        with open(file_name) as in_file:
            lines = in_file.readlines()

        for i in range(len(lines)):
            cols = lines[i].split(separator)

            if first is True:
                if vcat and site_input:
                    matrix.append(cols[:4])
                elif vcat or site_input:
                    matrix.append(cols[:3])
                else:
                    matrix.append(cols[:2])

            if vcat:
                matrix[i] += cols[4:]
            else:
                matrix[i] += cols[3:]

        first = False

    with open(output, "w") if output != "-" else nullcontext(sys.stdout) as out_file:
        if write_header:
            out_file.write(header + "\n")

        gs.verbose(_("Writing the output file <%s>") % (output))
        for row in matrix:
            first = True
            for col in row:
                value = col.strip()

                if first is False:
                    out_file.write("%s" % (separator))
                out_file.write(value)

                first = False

            out_file.write("\n")


############################################################################


def process_loop(
    nprocs,
    maps,
    file_name,
    count,
    maps_per_process,
    remaining_maps_per_loop,
    output_files,
    output_time_list,
    r_what,
    process_queue,
):
    """Call r.what in parallel subprocesses"""
    first = True
    for process in range(nprocs):
        num = maps_per_process
        # Add the remaining maps to the first process
        if first is True:
            num += remaining_maps_per_loop
        first = False

        # Temporary output file
        final_file_name = file_name + "_%i" % (process)
        output_files.append(final_file_name)

        map_names = []
        map_list = []
        for _i in range(num):
            map = maps[count]
            map_names.append(map.get_id())
            map_list.append(map)
            count += 1

        output_time_list.append(map_list)

        gs.verbose(
            _("Process maps %(samp_start)i to %(samp_end)i (of %(total)i)")
            % (
                {
                    "samp_start": count - len(map_names) + 1,
                    "samp_end": count,
                    "total": len(maps),
                }
            )
        )
        mod = copy.deepcopy(r_what)
        mod(map=map_names, output=final_file_name)
        process_queue.put(mod)

    return count


############################################################################

if __name__ == "__main__":
    options, flags = gs.parser()
    main(options, flags)
