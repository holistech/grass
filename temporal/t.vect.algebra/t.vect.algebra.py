#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.vect.algebra
# AUTHOR(S):    Thomas Leppelt, Soeren Gebbert
#
# PURPOSE:      Provide temporal vector algebra to perform spatial and temporal operations
#               for space time datasets by topological relationships to other space time
#               datasets.
# SPDX-FileCopyrightText: 2014-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Apply temporal and spatial operations on space time vector datasets using temporal vector algebra.
# % keyword: temporal
# % keyword: algebra
# % keyword: vector
# % keyword: time
# %end

# %option
# % key: expression
# % type: string
# % description: Spatio-temporal mapcalc expression
# % key_desc: expression
# % required : yes
# %end

# %option
# % key: basename
# % type: string
# % label: Basename of the new generated output maps
# % description: A numerical suffix separated by an underscore will be attached to create a unique identifier
# % key_desc: basename
# % required : yes
# %end

# %flag
# % key: s
# % description: Check the spatial topology of temporally related maps and process only spatially related maps
# %end

# %flag
# % key: c
# % description: Use the classic algebra instead of the algebra core
# %end

import sys

import grass.script as gs
from grass.exceptions import FatalError


def main():
    # lazy imports
    import grass.temporal as tgis

    expression = options["expression"]
    basename = options["basename"]
    spatial = flags["s"]

    tgis.init(True)
    p = tgis.TemporalVectorAlgebraParser(
        run=True, debug=False, spatial=spatial, classic=flags["c"] or None
    )
    try:
        pc = p.parse(expression, basename, gs.overwrite())
    except (SyntaxError, FatalError, ValueError, TypeError) as error:
        gs.fatal(str(error))

    if not (pc or {}).get("register"):
        gs.warning(_("The expression produced no map, the result is empty"))


if __name__ == "__main__":
    options, flags = gs.parser()
    sys.exit(main())
