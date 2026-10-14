"""Reducers: how gather() combines the related slots of a target slot"""

from dataclasses import dataclass

from .content import Const, call, chain, series_aggregate, series_reduce

REDUCERS = ("sum", "prod", "min", "max", "mean", "count", "all", "any", "first", "last")

# Kept in step with r.series by a test, so that a typo fails when the reducer
# is made, not when r.series runs.
SERIES_METHODS = (
    "average",
    "count",
    "median",
    "mode",
    "minimum",
    "min_raster",
    "maximum",
    "max_raster",
    "stddev",
    "range",
    "sum",
    "variance",
    "diversity",
    "slope",
    "offset",
    "detcoeff",
    "tvalue",
    "quart1",
    "quart3",
    "perc90",
    "quantile",
    "skewness",
    "kurtosis",
)


@dataclass(frozen=True)
class Fold:
    """Fold with an operator, starting with the target: ((t op x1) op x2)

    This is the arithmetic of the algebra: B {-,contains} A is b - a1 - a2.
    """

    operator: str


def fold(operator):
    """Return the reducer that folds the target and the related slots"""
    return Fold(operator)


@dataclass(frozen=True)
class SeriesMethod:
    """Reduce with any method of r.series, as t.rast.aggregate does

    method is one of SERIES_METHODS and reaches r.series unchanged. A lone
    related map is copied verbatim instead (see series_aggregate), so the
    method is applied only from two maps on. file_limit is the open file
    limit of r.series, carried here so the backend can set the -z flag per
    granule.
    """

    method: str
    file_limit: int = 1000


def series_method(method, *, file_limit=1000):
    """Return the reducer that aggregates the related maps with r.series

    :raises ValueError: if method is not one of SERIES_METHODS
    """
    if method not in SERIES_METHODS:
        msg = f"Unknown r.series method {method!r}, use one of {', '.join(SERIES_METHODS)}"
        raise ValueError(msg)
    return SeriesMethod(method, file_limit)


def check(reducer, nulls):
    """Stop for an unknown reducer or one that cannot skip null cells"""
    if reducer is None:
        return
    if isinstance(reducer, SeriesMethod):
        # r.series always skips null cells, so nulls does not restrict it.
        return
    if isinstance(reducer, Fold):
        if nulls == "skip":
            msg = "fold() has no meaningful way to skip null cells"
            raise ValueError(msg)
        return
    if reducer not in REDUCERS:
        msg = (
            f"Unknown reducer {reducer!r}, use one of {', '.join(REDUCERS)}, "
            "fold(operator) or None"
        )
        raise ValueError(msg)
    if reducer == "prod" and nulls == "skip":
        msg = "prod cannot skip null cells: r.series has no product"
        raise ValueError(msg)


def sort_of(reducer, target_sort, other_sort):
    """The sort of the reduced series"""
    if reducer is None:
        return target_sort
    if reducer == "count":
        return "scalar"
    if isinstance(reducer, SeriesMethod):
        return "field"
    if isinstance(reducer, Fold):
        return "field" if "field" in {target_sort, other_sort} else "scalar"
    return other_sort


def _extreme(function, related):
    return related[0] if len(related) == 1 else call(function, *related)


def _truth(related):
    return [call("!=", content, Const(0)) for content in related]


def _every(function, related):
    # A single map would pass through unchanged, so a cell value 5 would stay
    # 5 while two maps give 0 or 1. Its truth value keeps the result boolean.
    if len(related) == 1:
        return _truth(related)[0]
    return chain(function, related)


def _mean(related):
    return call("/", chain("+", related), Const(float(len(related))))


_PROPAGATE = {
    "sum": lambda related: chain("+", related),
    "prod": lambda related: chain("*", related),
    "min": lambda related: _extreme("min", related),
    "max": lambda related: _extreme("max", related),
    "mean": _mean,
    "all": lambda related: _every("&&", related),
    "any": lambda related: _every("||", related),
}

# nmin and nmax of r.mapcalc skip null cells in one call, sum and mean need
# r.series.
_SKIP = {
    "sum": lambda related: series_reduce("sum", related),
    "mean": lambda related: series_reduce("average", related),
    "min": lambda related: _extreme("nmin", related),
    "max": lambda related: _extreme("nmax", related),
    "all": lambda related: _extreme("nmin", _truth(related)),
    "any": lambda related: _extreme("nmax", _truth(related)),
}


def reduce(reducer, target, related, nulls):
    """Return the content that reduces the related contents

    Only fold() includes the target; None keeps the content of the target.
    """
    if reducer is None:
        return target
    if isinstance(reducer, SeriesMethod):
        return series_aggregate(reducer.method, related, reducer.file_limit)
    if isinstance(reducer, Fold):
        return chain(reducer.operator, [target, *related])
    if reducer == "count":
        return Const(len(related))
    if reducer == "first":
        return related[0]
    if reducer == "last":
        return related[-1]
    table = _SKIP if nulls == "skip" else _PROPAGATE
    return table[reducer](related)
