"""The choice between the algebra core and the classic algebra

The parser classes of the raster, 3D raster and vector algebra translate an
expression onto grass.temporal.algebra unless the classic algebra is chosen.
The classic algebra stays, because published results rely on it.
"""

import os

#: The environment variable that chooses the algebra for every expression
#: of a session or script: "core" or "classic".
ALGEBRA_VARIABLE = "GRASS_TEMPORAL_ALGEBRA"
DEFAULT_ALGEBRA = "core"


def classic_selected(classic):
    """Tell whether the classic algebra computes an expression

    :param classic: True or False decides; None follows the environment
        variable GRASS_TEMPORAL_ALGEBRA, whose default is the core
    :raises ValueError: for a value of the variable other than core and
        classic
    """
    if classic is not None:
        return classic
    choice = os.environ.get(ALGEBRA_VARIABLE, DEFAULT_ALGEBRA)
    if choice not in ("core", "classic"):
        msg = f"{ALGEBRA_VARIABLE} is core or classic, not {choice!r}"
        raise ValueError(msg)
    return choice == "classic"
