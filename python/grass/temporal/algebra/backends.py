"""Backends turn the content of a slot into module calls"""

import math
from dataclasses import dataclass

from .content import (
    COMPARISONS,
    LEFT_ASSOCIATIVE,
    Call,
    Const,
    MapRef,
    SeriesAggregate,
    SeriesReduce,
)

# Operators of r.mapcalc written before one operand; the content tree names
# the negation "neg" so that it cannot be mistaken for the subtraction.
_PREFIX = {"neg": "-", "!": "!", "~": "~"}
# The functions of r.mapcalc. Any other name would reach r.mapcalc as the
# name of a map and fail only there, so it is rejected when planning.
_FUNCTIONS = frozenset(
    {"abs", "acos", "asin", "atan", "ceil", "cos", "double", "eval", "exp"}
    | {"float", "floor", "graph", "graph2", "if", "int", "isnull", "log", "max"}
    | {"median", "min", "mod", "mode", "nmax", "nmedian", "nmin", "nmode", "not"}
    | {"pow", "rand", "round", "sin", "sqrt", "tan", "xor"}
)


# The overlays of vector maps: the content names the operator of v.overlay,
# and "disor" is the name of the classic algebra for v.patch. Only "and",
# "or" and "disor" are no names of r.mapcalc; "xor" and "not" are, so the map
# type of a series, not the name in its content, tells which backend reads
# the content. None of the names is in LEFT_ASSOCIATIVE or variadic, so
# chain() nests them to the left instead of flattening them into one call.
OVERLAYS = frozenset({"and", "or", "xor", "not"})
PATCH = "disor"
VECTOR_FUNCTIONS = frozenset({*OVERLAYS, PATCH})
# The feature type of v.buffer to the content name of a buffer.
BUFFERS = {"point": "buff_p", "line": "buff_l", "area": "buff_a"}
BUFFER_TYPES = {name: features for features, name in BUFFERS.items()}


@dataclass(frozen=True)
class MapcalcStyle:
    """How the r.mapcalc text of a content is written

    The defaults are the text of the core, which is safe for any map name and
    any number. The classic algebra writes the text more plainly, and the
    result of a call depends on it only where the fields below say so.

    :param quote_names: put every map name in double quotes, so that a name
        such as a-b or 5 is not read as an expression; without it the name is
        written as it is, which fails for those names
    :param written_integers: write an integer as it is, also beyond the CELL
        range, where r.mapcalc wraps it around or reads it as null; by default
        such an integer is written as a float, which keeps its value
    :param bare_comparisons: write a comparison without parentheses, as
        "a == b", where it stands at the top, as an argument of a function
        or as an operand of && and ||. As an operand of any other operator
        it keeps its parentheses, which "(a > 1) + b" needs; the operands of
        the comparison keep theirs as well
    """

    quote_names: bool = True
    written_integers: bool = False
    bare_comparisons: bool = False


# The operators whose operands may be bare comparisons: r.mapcalc reads
# "a > 1 && b < 2" as "(a > 1) && (b < 2)". Measured 2026-10-16 in a temporal
# session of an XY project: the maps of "if(A > 2 && N < 4, A, N)" and of
# "if(A > 3 || N < 2, A, N)" computed with bare comparisons equal those
# computed with parentheses (temporal_algebra_core_plan_options_io_test.py).
_LOOSE = frozenset({"&&", "||"})


@dataclass(frozen=True)
class ModuleCall:
    """A planned module call: the module, its parameters, and, for r.series
    over a file, the related map names to write into that file at run time"""

    name: str
    parameters: dict
    inputs: tuple = ()


# CELL is a 32 bit integer whose lowest value is null in GRASS (measured
# 2026-10-11 with r.mapcalc: -2147483648 gives a map of null cells).
_CELL_MIN = -(2**31) + 1
_CELL_MAX = 2**31 - 1


def _float_literal(value):
    # r.mapcalc reads "1e-05" as the map name "1e" followed by "-05": its
    # scanner needs a dot in the mantissa (measured 2026-10-11).
    text = repr(value)
    mantissa, marker, exponent = text.partition("e")
    if marker and "." not in mantissa:
        mantissa += ".0"
    return f"{mantissa}{marker}{exponent}"


def _literal(value, written_integers=False):
    if value is None:
        return "null()"
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        if written_integers or _CELL_MIN <= value <= _CELL_MAX:
            return str(value)
        # r.mapcalc wraps larger integers around or reads them as null
        # (3000000000 gave -1294967296, 2147483648 gave null, measured
        # 2026-10-11), so they are written as floats: the value is kept and
        # the result map becomes DCELL.
        try:
            value = float(value)
        except OverflowError:
            msg = f"The integer {value} is too large for a raster map expression"
            raise ValueError(msg) from None
    # nan and inf would reach r.mapcalc as the names of maps.
    if isinstance(value, float) and math.isfinite(value):
        return _float_literal(value)
    msg = f"The value {value!r} cannot be part of a raster map expression"
    raise TypeError(msg)


def _quote(name, quote_names=True):
    """Quote a map name: GRASS allows names that r.mapcalc would read as an
    expression, such as a-b or 5 (measured 2026-10-11)"""
    if not quote_names:
        return name
    if '"' in name:
        msg = f"The map name {name!r} contains a quote and cannot be used in r.mapcalc"
        raise ValueError(msg)
    return f'"{name}"'


class RasterBackend:
    """Plan raster maps with r.mapcalc, and with r.series where a reduction
    skips null cells

    r.series has no region option and computes in the current region, also
    for a series whose maps were related in space; r.mapcalc computes those
    in the union of the regions.

    One r.mapcalc expression travels as one argument of the process, which
    the operating system limits in size: on Linux an expression of 131000
    bytes ran and one of 131071 bytes failed (measured 2026-10-11 with
    r.mapcalc expression="out = ..." of "m" + "m" + ... in grass
    --tmp-project XY), which is a few thousand related maps in a reduction
    with nulls="propagate". With nulls="skip" the maps are listed in the
    input of r.series, which is not limited this way.
    """

    kind = "raster"
    # Raster maps are computed even when unchanged, as in the classic algebra,
    # so that a map of another mapset becomes a map of this one.
    registers_origins = False

    def expression(self, content, style=MapcalcStyle()):
        """The r.mapcalc expression of a content

        It is fully parenthesized, so the precedence of r.mapcalc never
        matters, unless style asks for bare comparisons.

        :param style: how names, integers and comparisons are written
        :raises ValueError: for an operator or function that r.mapcalc does
            not have, or that is given the wrong number of operands
        :raises TypeError: for a value that is not a number
        """
        return self._expression(content, style, True)

    def _expression(self, content, style, bare_allowed):
        match content:
            case MapRef(ident=ident, offset=offset) if offset:
                name = _quote(ident, style.quote_names)
                return f"{name}[{','.join(str(step) for step in offset)}]"
            case MapRef(ident=ident):
                return _quote(ident, style.quote_names)
            case Const(value=value):
                return _literal(value, style.written_integers)
            case Call(function=function, args=args):
                # An operand of an operator other than && and || needs its
                # parentheses; the arguments of a function do not.
                inner = function in _LOOSE or function in _FUNCTIONS
                parts = [self._expression(arg, style, inner) for arg in args]
                text = self._call(function, parts)
                if bare_allowed and style.bare_comparisons and function in COMPARISONS:
                    # _call() wraps the comparison in one pair of parentheses.
                    return text[1:-1]
                return text
            case SeriesReduce():
                msg = "A reduction with r.series is planned as a call of its own"
                raise ValueError(msg)
            case SeriesAggregate():
                msg = "An r.series aggregation is planned as a call of its own"
                raise ValueError(msg)
        msg = f"Unknown content {content!r}"
        raise TypeError(msg)

    @staticmethod
    def _call(function, parts):
        if function in LEFT_ASSOCIATIVE:
            # Written flat: r.mapcalc parses "(a - b - c)" like "((a - b) - c)".
            if len(parts) < 2:
                msg = (
                    f"The operator {function} needs at least two operands, "
                    f"got {len(parts)}"
                )
                raise ValueError(msg)
            return f"({f' {function} '.join(parts)})"
        if function == "^":
            # Right-associative in r.mapcalc, so a call with three operands
            # would not mean what its order says.
            if len(parts) != 2:
                msg = f"The operator ^ needs two operands, got {len(parts)}"
                raise ValueError(msg)
            return f"({parts[0]} ^ {parts[1]})"
        if function in _PREFIX:
            if len(parts) != 1:
                msg = f"The operator {function} needs one operand, got {len(parts)}"
                raise ValueError(msg)
            # "--1" is a parse error in r.mapcalc (measured 2026-10-11 with
            # r.mapcalc expression="b=(--a)"), a negative literal needs its
            # own parentheses.
            operand = f"({parts[0]})" if parts[0].startswith("-") else parts[0]
            return f"({_PREFIX[function]}{operand})"
        if function == "if" and not 3 <= len(parts) <= 4:
            # if(c, t) is 0 where c is false, not null.
            msg = f"if() needs three or four arguments, got {len(parts)}"
            raise ValueError(msg)
        if function in _FUNCTIONS:
            return f"{function}({', '.join(parts)})"
        msg = f"{function!r} is neither an operator nor a function of r.mapcalc"
        raise ValueError(msg)

    def _mapcalc(self, output, expression, spatial, style):
        name = _quote(output, style.quote_names)
        parameters = {"expression": f"{name}={expression}"}
        if spatial:
            parameters["region"] = "union"
        # One process per call: how many calls run at once is up to whoever
        # runs them.
        parameters["nprocs"] = 1
        return ModuleCall("r.mapcalc", parameters)

    def plan(self, content, output, *, spatial=False, style=MapcalcStyle()):
        """Plan the computation of the map output from the content

        Return the module calls in the order to run them, and the temporary
        maps to remove afterwards. style is the way the r.mapcalc text is
        written, see MapcalcStyle.

        One r.mapcalc call computes the map, unless reductions that skip
        null cells need r.series; their inputs that are expressions are
        computed into temporary maps first.
        """
        calls = []
        temporaries = []

        def temporary():
            name = f"{output}_tmp{len(temporaries)}"
            temporaries.append(name)
            return name

        def map_name_of(node):
            # r.series reads maps, and a map at an offset is not one.
            if isinstance(node, MapRef) and not node.offset:
                return node.ident
            name = temporary()
            calls.append(
                self._mapcalc(name, self.expression(node, style), spatial, style)
            )
            return name

        def lower(node, target=None):
            if isinstance(node, SeriesAggregate):
                inputs = [map_name_of(lower(arg)) for arg in node.args]
                name = target or temporary()
                if len(inputs) == 1:
                    # A lone related map is copied verbatim: g.copy keeps its
                    # data type (CELL stays CELL) and its color table, which
                    # r.series would drop, and the method never touches its
                    # values (measured 2026-10-14, see SeriesAggregate).
                    calls.append(ModuleCall("g.copy", {"raster": (inputs[0], name)}))
                else:
                    parameters = {"output": name, "method": node.method}
                    if len(inputs) > node.file_limit:
                        # r.series opens every input at once unless -z makes
                        # it read them cell by cell; the limit is file_limit.
                        parameters["flags"] = "z"
                    calls.append(
                        ModuleCall("r.series", parameters, inputs=tuple(inputs))
                    )
                return MapRef(name)
            if isinstance(node, SeriesReduce):
                inputs = [map_name_of(lower(arg)) for arg in node.args]
                name = target or temporary()
                calls.append(
                    ModuleCall(
                        "r.series",
                        {"output": name, "method": node.method},
                        inputs=tuple(inputs),
                    )
                )
                return MapRef(name)
            if isinstance(node, Call):
                return Call(node.function, tuple(lower(arg) for arg in node.args))
            return node

        if isinstance(content, (SeriesReduce, SeriesAggregate)):
            lower(content, target=output)
        else:
            lowered = lower(content)
            calls.append(
                self._mapcalc(output, self.expression(lowered, style), spatial, style)
            )
        return calls, temporaries


class Raster3DBackend(RasterBackend):
    """Plan 3D raster maps with r3.mapcalc

    r3.mapcalc reads the expressions of r.mapcalc, with three cell offsets
    (checked 2026-10-13 with r3.mapcalc in grass --tmp-project XY on a 3x3x3
    grid: offsets [1,0,-1], nmin(), if(), isnull() and 1.0e-05 are accepted).

    Two things differ from r.mapcalc:

    - region=union is accepted by the parser of r3.mapcalc but fails with
      "Union or intersection of regions is not implemented" (same
      measurement, region=intersect fails alike). Maps related in space are
      therefore computed in the current 3D region, which is what the
      classic algebra does as well.
    - There is no r3.series, so a reduction that skips null cells and
      needs r.series cannot be planned.
    """

    kind = "raster3d"

    def _mapcalc(self, output, expression, spatial, style):
        # No region option, whether or not the maps are related in space.
        call = super()._mapcalc(output, expression, False, style)
        return ModuleCall("r3.mapcalc", call.parameters)

    def plan(self, content, output, *, spatial=False, style=MapcalcStyle()):
        """Plan the computation of the map output from the content

        :raises ValueError: for a reduction that needs r.series
        """
        found = _find_series_node(content)
        if isinstance(found, SeriesAggregate):
            msg = (
                f"The r.series aggregation {found.method} has no counterpart "
                "for 3D raster maps"
            )
            raise ValueError(msg)
        if found is not None:
            msg = (
                "Skipping null cells in a sum or mean needs r.series, which has "
                "no counterpart for 3D raster maps"
            )
            raise ValueError(msg)
        return super().plan(content, output, spatial=spatial, style=style)


def _find_series_node(content):
    """Return the first node that needs r.series, or None"""
    if isinstance(content, (SeriesReduce, SeriesAggregate)):
        return content
    if isinstance(content, Call):
        for arg in content.args:
            found = _find_series_node(arg)
            if found is not None:
                return found
    return None


def describe(node):
    """Name a content node in words for a message to the user; the sentence
    starts with a capital letter"""
    match node:
        case Const(value=None):
            return "null()"
        case Const(value=value):
            return f"The number {value}"
        case MapRef(ident=ident, offset=offset):
            return f"The map <{ident}> at the cell offset {offset}"
        case Call(function=function):
            return f"The function {function}()"
        case SeriesReduce(method=method):
            return f"The reduction {method} of a series"
        case SeriesAggregate(method=method):
            return f"The r.series aggregation {method} of a series"


class VectorBackend:
    """Plan vector maps with v.overlay, v.patch, v.buffer and g.copy

    Each overlay and buffer is one module call, so a nested expression
    computes its parts into temporary maps, as the classic algebra does. A
    registered map that reaches the result unchanged is registered as it
    is; a map with another time stamp is copied.
    """

    kind = "vector"
    registers_origins = True

    def plan(self, content, output, *, spatial=False, style=MapcalcStyle()):
        """Plan the computation of the map output from the content

        spatial and style have no effect: the vector modules compute every
        feature and write no expression.

        :raises ValueError: for a content that is no vector map, overlay or
            buffer
        """
        calls = []
        temporaries = []

        def map_name_of(node):
            if isinstance(node, MapRef) and not node.offset:
                return node.ident
            name = f"{output}_tmp{len(temporaries)}"
            temporaries.append(name)
            compute(node, name)
            return name

        def compute(node, target):
            match node:
                case MapRef(ident=ident, offset=()):
                    # pygrass.modules.Module takes the from,to pair of g.copy
                    # only as a tuple; the string "from,to" raises TypeError
                    # (checked 2026-10-13 with Module("g.copy", run_=False)).
                    calls.append(ModuleCall("g.copy", {"vector": (ident, target)}))
                case Call(function=function, args=(first, second)) if (
                    function in OVERLAYS
                ):
                    calls.append(
                        ModuleCall(
                            "v.overlay",
                            {
                                "ainput": map_name_of(first),
                                "binput": map_name_of(second),
                                "operator": function,
                                "output": target,
                            },
                        )
                    )
                case Call(function=function, args=args) if (
                    function == PATCH and len(args) >= 2
                ):
                    inputs = ",".join(map_name_of(arg) for arg in args)
                    calls.append(
                        ModuleCall("v.patch", {"input": inputs, "output": target})
                    )
                case Call(
                    function=function, args=(features, Const(value=distance))
                ) if function in BUFFER_TYPES:
                    calls.append(
                        ModuleCall(
                            "v.buffer",
                            {
                                "input": map_name_of(features),
                                "type": BUFFER_TYPES[function],
                                "distance": distance,
                                "output": target,
                            },
                        )
                    )
                case _:
                    msg = f"{describe(node)} cannot be computed as a vector map"
                    raise ValueError(msg)

        compute(content, output)
        return calls, temporaries


_BACKENDS = {
    "raster": RasterBackend(),
    "raster3d": Raster3DBackend(),
    "vector": VectorBackend(),
}


def backend_for(kind):
    """Return the backend of a map type

    :raises NotImplementedError: for a map type without backend
    """
    if kind not in _BACKENDS:
        msg = f"Computing {kind} maps is not supported yet"
        raise NotImplementedError(msg)
    return _BACKENDS[kind]
