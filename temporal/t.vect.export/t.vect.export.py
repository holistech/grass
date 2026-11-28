#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.vect.export
# AUTHOR(S):    Soeren Gebbert
#
# PURPOSE:      Export a space time vector dataset.as GRASS specific archive file
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Exports a space time vector dataset as GRASS specific archive file.
# % keyword: temporal
# % keyword: export
# % keyword: vector
# % keyword: time
# %end

# %option G_OPT_STVDS_INPUT
# %end

# %option G_OPT_F_OUTPUT
# % description: Name of a space time vector dataset archive
# %end

# %option G_OPT_M_DIR
# % key: directory
# % label: Working directory for the export (the archive is written to output)
# % description: The maps are exported and packed in a temporary subdirectory of it, which is removed afterwards; default is the temporary directory of the system
# % required: no
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
# % label: The export format of a single vector map
# % description: Supported are GML and GPKG via v.out.ogr and the GRASS package format of v.pack
# % required: no
# % multiple: no
# % options: GML,GPKG,pack
# % answer: GML
# %end

# %option G_OPT_T_WHERE
# %end

import tempfile

import grass.script as gs


############################################################################
def main():
    # lazy imports
    import grass.temporal as tgis

    # Get the options
    input_ = options["input"]
    output = options["output"]
    compression = options["compression"]
    # A fixed default such as /tmp does not exist on Windows.
    directory = options["directory"] or tempfile.gettempdir()
    where = options["where"]
    format_ = options["format"]

    # Make sure the temporal database exists
    tgis.init()
    # Export the space time vector dataset
    tgis.export_stds(input_, output, compression, directory, where, format_, "stvds")


############################################################################
if __name__ == "__main__":
    options, flags = gs.parser()
    main()
