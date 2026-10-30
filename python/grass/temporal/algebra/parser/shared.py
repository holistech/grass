"""Constants and checks that the translators of the parser share

These names are for variants of the algebra, not for users. Translator and
ClassicTranslator (classic.py) read the same marks and refuse the same
operands with them; a change here must therefore be checked against both.
"""

from grass.temporal.algebra import time_functions
from grass.temporal.algebra.content import Const
from grass.temporal.algebra.series import Series

EXTENTS = {"l": "left", "u": "union", "i": "intersection", "d": "disjoint"}
# Marks an if() without else, which differs from an else of null().
ABSENT = object()


def timed(value):
    """Tell whether value is a series with time stamps"""
    return isinstance(value, Series) and not value.timeless


def vector_field(*values):
    """Tell whether one of values holds vector maps rather than numbers"""
    return any(
        isinstance(value, Series) and value.kind == "vector" and value.sort == "field"
        for value in values
    )


def check_time_variable(name, series):
    """Raise for a temporal variable that a map of series does not have

    timevar() gives null for the end of an instant and for the calendar of
    relative time. A null condition selects no map, so a slip such as end_doy
    for start_doy would give an empty result without a word. The classic
    algebra stops with an error that names the map, and so does this
    translation. td() of an instant stays null, as in t.rast.mapcalc.
    """
    if name == "td":
        return
    for slot in series.slots:
        extent = slot.extent
        if extent.unit is None and (
            extent.end is not None or name.startswith("start_")
        ):
            continue
        what = f"map <{slot.origin}>" if slot.origin else f"the map at {extent.start}"
        msg = (
            f"Temporal function {name}() is not available for {what}: it needs "
            "absolute time, and the end functions also an end time"
        )
        raise time_functions.TimeFunctionError(msg, name, slot.origin)


def whole(value, name):
    """The whole number of the offset value of function name"""
    if not (isinstance(value, Const) and isinstance(value.value, int)):
        msg = f"The offset of {name}() is a whole number"
        raise SyntaxError(msg)
    return value.value
