"""Backends turn the content of a slot into module calls"""

import math
from dataclasses import dataclass

from .content import LEFT_ASSOCIATIVE, Call, Const, MapRef, SeriesReduce

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


@dataclass(frozen=True)
class ModuleCall:
    """A planned module call: the module and its parameters"""

    name: str
    parameters: dict


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


def _literal(value):
    if value is None:
        return "null()"
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        if _CELL_MIN <= value <= _CELL_MAX:
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


def _quote(name):
    """Quote a map name: GRASS allows names that r.mapcalc would read as an
    expression, such as a-b or 5 (measured 2026-10-11)"""
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

    def expression(self, content):
        """The r.mapcalc expression of a content

        It is fully parenthesized, so the precedence of r.mapcalc never
        matters.

        :raises ValueError: for an operator or function that r.mapcalc does
            not have, or that is given the wrong number of operands
        :raises TypeError: for a value that is not a number
        """
        match content:
            case MapRef(ident=ident, offset=offset) if offset:
                return f"{_quote(ident)}[{','.join(str(step) for step in offset)}]"
            case MapRef(ident=ident):
                return _quote(ident)
            case Const(value=value):
                return _literal(value)
            case Call(function=function, args=args):
                return self._call(function, [self.expression(arg) for arg in args])
            case SeriesReduce():
                msg = "A reduction with r.series is planned as a call of its own"
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
        if function == "if" and len(parts) < 3:
            # if(c, t) is 0 where c is false, not null.
            msg = f"if() needs three arguments, got {len(parts)}"
            raise ValueError(msg)
        if function in _FUNCTIONS:
            return f"{function}({', '.join(parts)})"
        msg = f"{function!r} is neither an operator nor a function of r.mapcalc"
        raise ValueError(msg)

    @staticmethod
    def _mapcalc(output, expression, spatial):
        parameters = {"expression": f"{_quote(output)}={expression}"}
        if spatial:
            parameters["region"] = "union"
        # One process per call: how many calls run at once is up to whoever
        # runs them.
        parameters["nprocs"] = 1
        return ModuleCall("r.mapcalc", parameters)

    def plan(self, content, output, *, spatial=False):
        """Plan the computation of the map output from the content

        Return the module calls in the order to run them, and the temporary
        maps to remove afterwards.

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

        def as_map(node):
            # r.series reads maps, and a map at an offset is not one.
            if isinstance(node, MapRef) and not node.offset:
                return node.ident
            name = temporary()
            calls.append(self._mapcalc(name, self.expression(node), spatial))
            return name

        def lower(node, target=None):
            if isinstance(node, SeriesReduce):
                inputs = [as_map(lower(arg)) for arg in node.args]
                name = target or temporary()
                calls.append(
                    ModuleCall(
                        "r.series",
                        {
                            "input": ",".join(inputs),
                            "output": name,
                            "method": node.method,
                        },
                    )
                )
                return MapRef(name)
            if isinstance(node, Call):
                return Call(node.function, tuple(lower(arg) for arg in node.args))
            return node

        if isinstance(content, SeriesReduce):
            lower(content, target=output)
        else:
            lowered = lower(content)
            calls.append(self._mapcalc(output, self.expression(lowered), spatial))
        return calls, temporaries


_BACKENDS = {"raster": RasterBackend()}


def backend_for(kind):
    """Return the backend of a map type

    :raises NotImplementedError: for a map type without backend
    """
    if kind not in _BACKENDS:
        msg = f"Computing {kind} maps is not supported yet"
        raise NotImplementedError(msg)
    return _BACKENDS[kind]
