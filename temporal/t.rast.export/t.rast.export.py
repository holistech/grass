#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.rast.export
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Export a space time raster dataset
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Exports space time raster dataset.
# % keyword: temporal
# % keyword: export
# % keyword: raster
# % keyword: time
# %end

# %option G_OPT_STRDS_INPUT
# %end

# %option G_OPT_F_OUTPUT
# % description: Name of a space time raster dataset archive
# %end

# %option G_OPT_M_DIR
# % key: directory
# % label: Working directory for the export (the archive is written to output)
# % description: The maps are exported and packed in a temporary subdirectory of it, which is removed afterwards
# % required: no
# % multiple: no
# % answer: ./
# %end

# %option
# % key: compression
# % type: string
# % description: Compression method of the tar archive
# % required: no
# % multiple: no
# % options: no,gzip,bzip2
# % answer: bzip2
# %end

# %option
# % key: format
# % type: string
# % label: The export format of a single raster map
# % description: Supported are GTiff, AAIGrid via r.out.gdal and the GRASS package format of r.pack
# % required: no
# % multiple: no
# % options: GTiff,AAIGrid,pack
# % answer: GTiff
# %end

# %option
# % key: type
# % type: string
# % label: Data type
# % description: Supported only for GTiff
# % required: no
# % multiple: no
# % options: Byte,Int16,UInt16,Int32,UInt32,Float32,Float64,CInt16,CInt32,CFloat32,CFloat64
# %end

# %option
# % key: createopt
# % type: string
# % label: Creation option(s) to pass to the output format driver
# % description: In the form of "NAME=VALUE", separate multiple entries with a comma
# % required: no
# % multiple: yes
# %end

# %option
# % key: metaopt
# % type: string
# % label: Metadata key(s) and value(s) to include
# % description: In the form of "META-TAG=VALUE", separate multiple entries with a comma. Not supported by all output format drivers.
# % required: no
# % multiple: yes
# %end

# %option
# % key: nodata
# % type: double
# % label: Assign a specified nodata value to output bands
# % description: If given, the nodata value is always written to metadata even if there are no NULL cells in the input band (enhances output compatibility).
# % required: no
# %end

# %option G_OPT_T_WHERE
# %end


import grass.script as gs


############################################################################
def main():
    # lazy imports
    import grass.temporal as tgis

    # Get the options
    input_ = options["input"]
    output = options["output"]
    compression = options["compression"]
    directory = options["directory"]
    where = options["where"]
    format_ = options["format"]
    type_ = options["type"]
    kws = {
        key: options[key] for key in ("createopt", "metaopt", "nodata") if options[key]
    }

    if type_ and format_ in {"pack", "AAIGrid"}:
        gs.warning(
            _(
                "The type option is not used with the {} format, it will be skipped."
            ).format(format_)
        )
    # AAIGrid is written by r.out.gdal, which takes nodata and createopt like
    # for GTiff. metaopt ends up in a side file (<map>.asc.aux.xml) that the
    # archive does not hold, so it is lost for AAIGrid.
    if format_ == "AAIGrid" and kws.get("metaopt"):
        gs.warning(
            _(
                "The metaopt option is not used with the AAIGrid format, "
                "it will be skipped."
            )
        )
    if format_ == "pack" and kws:
        gs.warning(
            _(
                "Createopt, metaopt and nodata options are not "
                "working with pack format, they will be skipped"
            )
        )
    # Make sure the temporal database exists
    tgis.init()
    # Export the space time raster dataset
    tgis.export_stds(
        input_, output, compression, directory, where, format_, "strds", type_, **kws
    )


############################################################################
if __name__ == "__main__":
    options, flags = gs.parser()
    main()
