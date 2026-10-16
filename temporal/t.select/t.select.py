#!/usr/bin/env python3

############################################################################
#
# MODULE:       t.select
# AUTHOR(S):    Thomas Leppelt, Soeren Gebbert
#
# PURPOSE:      Select maps from space time datasets by topological relationships to
#               other space time datasets using temporal algebra.
# SPDX-FileCopyrightText: 2011-2017 GRASS Development Team
# SPDX-License-Identifier: GPL-2.0-or-later
#
#############################################################################

# %module
# % description: Select maps from space time datasets by topological relationships to other space time datasets using temporal algebra.
# % keyword: temporal
# % keyword: metadata
# % keyword: time
# %end

# %option G_OPT_STDS_TYPE
# % guidependency: input
# % guisection: Required
# %end

# %option
# % key: expression
# % type: string
# % description: The temporal mapcalc expression
# % key_desc: expression
# % required : yes
# %end

# %flag
# % key: s
# % description: Check the spatial topology of temporally related maps and select only spatially related maps
# %end

# %flag
# % key: d
# % description: Perform a dry run, compute all dependencies and module calls but don't run them
# %end

# %flag
# % key: c
# % description: Use the classic algebra instead of the algebra core
# %end


import sys

import grass.script as gs
from grass.exceptions import FatalError

MIXING_FUNCTIONS = ("strds", "str3ds", "stvds")

############################################################################


def main():
    # lazy imports
    import grass.temporal as tgis
    from grass.temporal.algebra.maptypes import KINDS_OF_STDS
    from grass.temporal.algebra.parser import evaluate
    from grass.temporal.algebra.parser.switch import classic_selected
    from grass.temporal.algebra.profile import CLASSIC, CORE

    expression = options["expression"]
    spatial = flags["s"]
    dry_run = flags["d"]
    stdstype = options["type"]

    tgis.init()
    # t.select has no basename option; the copies of retimed maps are named
    # after the result dataset, otherwise they would be None_1, None_2, ...
    basename = expression.partition("=")[0].strip().partition("@")[0]
    try:
        pc = evaluate(
            expression,
            kind=KINDS_OF_STDS[stdstype],
            basename=basename,
            overwrite=gs.overwrite(),
            run=True,
            dry_run=dry_run,
            debug=False,
            spatial=spatial,
            selection=True,
            profile=CLASSIC if classic_selected(flags["c"] or None) else CORE,
        )
    except (SyntaxError, FatalError, ValueError, TypeError) as error:
        message = str(error)
        # Only the classic algebra pulls maps of another dataset type into a
        # selection; the user cannot guess that from "Unknown function".
        if message in {f"Unknown function {name}()" for name in MIXING_FUNCTIONS}:
            message += _(". Use the flag -c to select with the classic algebra.")
        gs.fatal(message)

    if dry_run is True:
        import pprint

        pprint.pprint(pc)


if __name__ == "__main__":
    options, flags = gs.parser()
    sys.exit(main())
