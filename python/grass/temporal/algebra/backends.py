"""Backends turn the content of a slot into module calls"""

import math
from dataclasses import dataclass

from .content import Call, Const, MapRef, SeriesReduce

# Operators of r.mapcalc, written between two operands.
_INFIX = frozenset(
    {"+", "-", "*", "/", "%", "^", "==", "!=", ">", ">=", "<", "<=", "&&", "||"}
    | {"&&&", "|||", "&", "|", "<<", ">>", ">>>"}
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


@dataclass(frozen=True)
class ModuleCall:
    """A planned module call: the module and its parameters"""

    name: str
    parameters: dict


def _literal(value):
    if value is None:
        return "null()"
    if isinstance(value, bool):
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    # nan and inf would reach r.mapcalc as the names of maps.
    if isinstance(value, float) and math.isfinite(value):
        return repr(value)
    msg = f"The value {value!r} cannot be part of a raster map expression"
    raise TypeError(msg)


class RasterBackend:
    """Plan raster maps with r.mapcalc, and with r.series where a reduction
    skips null cells

    r.series has no region option and computes in the current region, also
    for a series whose maps were related in space; r.mapcalc computes those
    in the union of the regions.
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
                return f"{ident}[{','.join(str(step) for step in offset)}]"
            case MapRef(ident=ident):
                return ident
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
        if function in _INFIX:
            if len(parts) != 2:
                msg = f"The operator {function} needs two operands, got {len(parts)}"
                raise ValueError(msg)
            return f"({parts[0]} {function} {parts[1]})"
        if function in _PREFIX:
            if len(parts) != 1:
                msg = f"The operator {function} needs one operand, got {len(parts)}"
                raise ValueError(msg)
            # "--1" is a parse error in r.mapcalc (measured 2026-10-11 with
            # r.mapcalc expression="b=(--a)"), a negative literal needs its
            # own parentheses.
            operand = f"({parts[0]})" if parts[0].startswith("-") else parts[0]
            return f"({_PREFIX[function]}{operand})"
        if function in _FUNCTIONS:
            return f"{function}({', '.join(parts)})"
        msg = f"{function!r} is neither an operator nor a function of r.mapcalc"
        raise ValueError(msg)

    @staticmethod
    def _mapcalc(output, expression, spatial):
        parameters = {"expression": f"{output}={expression}"}
        if spatial:
            parameters["region"] = "union"
        # One process per call: how many calls run at once is up to whoever
        # runs them.
        parameters["nprocs"] = 1
        return ModuleCall("r.mapcalc", parameters)

    def plan(self, content, output, *, spatial=False):
        """Return the module calls that compute the content into the map
        output, in the order to run them, and the temporary maps to remove
        afterwards

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
