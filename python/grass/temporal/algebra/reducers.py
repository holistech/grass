"""Reducers: how gather() combines the related slots of a target slot

SPDX-FileCopyrightText: 2026 Soeren Gebbert
SPDX-FileCopyrightText: GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Soeren Gebbert
"""

from dataclasses import dataclass

from .content import Const, call, chain, series_aggregate, series_reduce

REDUCERS = (
    "sum",
    "prod",
    "min",
    "max",
    "mean",
    "count",
    "all",
    "any",
    "and",
    "or",
    "first",
    "last",
)

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

# The methods of SERIES_METHODS that r.series computes with weights: those
# with a w_* function in the menu of raster/r.series/main.c, kept in step by
# a test. For any other method r.series only warns and ignores the weights.
# Left out although they have one, because the result means nothing:
# - count: w_count sums the weights, the covered share of a granule, not a
#   number of maps;
# - slope, offset, detcoeff and tvalue: regression_w() in lib/stats/c_reg.c
#   adds the weights to an int, so weights below 1 count as 0 and the result
#   is null (measured 2026-11-10 with r.series file= of two maps 7 and 14
#   weighted 0.7 and 0.3: null for all four).
WEIGHTED_SERIES_METHODS = (
    "average",
    "median",
    "mode",
    "stddev",
    "sum",
    "variance",
    "quart1",
    "quart3",
    "perc90",
    "quantile",
    "skewness",
    "kurtosis",
)

# What the overlap of a related map with the target slot is divided by.
WEIGHTS = ("granule", "map")


@dataclass(frozen=True)
class Fold:
    """Fold with an operator, starting with the target: ((t op x1) op x2)

    This is the arithmetic of the algebra: B {-,contains} A is b - a1 - a2.
    """

    operator: str


@dataclass(frozen=True)
class Compare:
    """Compare the target with each related slot and join the comparisons

    The target is compared with every related content separately:
    (t >= x1 && t >= x2) for "&" and (t >= x1 || t >= x2) for "|". Folding the
    comparisons would compare the result of the first with the second slot.
    """

    symbol: str
    join: str


def compare(symbol, join):
    """Return the reducer that compares the target with each related slot

    :param symbol: ==, !=, >, >=, < or <=
    :param join: "&" for all comparisons, "|" for any
    """
    return Compare(symbol, join)


def fold(operator):
    """Return the reducer that folds the target and the related slots"""
    return Fold(operator)


@dataclass(frozen=True)
class SeriesMethod:
    """Reduce with any method of r.series, as t.rast.aggregate does

    method is one of SERIES_METHODS and reaches r.series unchanged. A lone
    related map is copied verbatim instead (see series_aggregate), so the
    method is applied only from two maps on. file_limit is the number of maps
    above which r.series runs with -z; fewer maps also do when they exceed
    the open files of the process (see series_limits). It is carried here so
    the backend can set the flag per granule.

    weights is None, or how gather() weights each related map by the time it
    shares with the target slot, see overlap_weights(): "granule" divides
    the overlap by the length of the target slot, "map" by the length of the
    map.
    """

    method: str
    file_limit: int = 1000
    weights: str | None = None


def series_method(method, *, file_limit=1000, weights=None):
    """Return the reducer that aggregates the related maps with r.series

    :param weights: None, "granule" or "map", see SeriesMethod; only a
        method of WEIGHTED_SERIES_METHODS takes weights
    :raises ValueError: if method is not one of SERIES_METHODS, if weights is
        unknown, or if the method cannot be weighted
    """
    if method not in SERIES_METHODS:
        msg = f"Unknown r.series method {method!r}, use one of {', '.join(SERIES_METHODS)}"
        raise ValueError(msg)
    if weights is not None:
        if weights not in WEIGHTS:
            msg = (
                f"Unknown weights {weights!r}, use one of {', '.join(WEIGHTS)} or None"
            )
            raise ValueError(msg)
        if method not in WEIGHTED_SERIES_METHODS:
            msg = (
                f"The r.series method {method!r} cannot be weighted, use one of "
                f"{', '.join(WEIGHTED_SERIES_METHODS)}"
            )
            raise ValueError(msg)
    return SeriesMethod(method, file_limit, weights)


def overlap_weights(weights, target, partners):
    """The share of time that each partner has in common with the target

    The overlap of a partner with the target is divided by the length of the
    target for weights "granule" and by the length of the partner for "map".
    Extents that only touch share no time and get 0. The same arithmetic
    serves both time types: the ratio of two differences of relative times
    (numbers of one unit) and of absolute times (timedelta / timedelta) is a
    float.

    :param weights: "granule" or "map"
    :param target: the Extent of the target slot
    :param partners: the Extents of the related slots
    :raises ValueError: if the target or a partner is a time instant, which
        has no length to weight by
    """
    for extent in (target, *partners):
        if extent.end is None:
            msg = (
                f"The time instant {extent.start} has no length, so it cannot be "
                "weighted by its overlap in time"
            )
            raise ValueError(msg)
    shares = []
    for partner in partners:
        start = max(target.start, partner.start)
        end = min(target.end, partner.end)
        if end <= start:
            shares.append(0.0)
            continue
        length = target if weights == "granule" else partner
        shares.append((end - start) / (length.end - length.start))
    return tuple(shares)


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
    if isinstance(reducer, Compare):
        if nulls == "skip":
            msg = "compare() has no meaningful way to skip null cells"
            raise ValueError(msg)
        return
    if reducer not in REDUCERS:
        msg = (
            f"Unknown reducer {reducer!r}, use one of {', '.join(REDUCERS)}, "
            "fold(operator), compare(symbol, join), series_method(method) or None"
        )
        raise ValueError(msg)
    if reducer == "prod" and nulls == "skip":
        msg = "prod cannot skip null cells: r.series has no product"
        raise ValueError(msg)
    if reducer in ("and", "or") and nulls == "skip":
        msg = f"{reducer} cannot skip null cells: it joins the contents as they are"
        raise ValueError(msg)


def sort_of(reducer, target_sort, other_sort):
    """The sort of the reduced series"""
    if reducer is None:
        return target_sort
    if reducer == "count":
        return "scalar"
    if isinstance(reducer, (SeriesMethod, Compare)):
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
    # A single related content stays as it is, also a floating point map that
    # r.mapcalc refuses as an operand of && and ||.
    "and": lambda related: chain("&&", related),
    "or": lambda related: chain("||", related),
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


def reduce(reducer, target, related, nulls, weights=None):
    """Return the content that reduces the related contents

    Only fold() and compare() include the target; None keeps the content of the target.
    weights are the weights of the related contents for a series_method()
    with weights, see overlap_weights(); the other reducers take none.
    """
    if reducer is None:
        return target
    if isinstance(reducer, SeriesMethod):
        return series_aggregate(reducer.method, related, reducer.file_limit, weights)
    if isinstance(reducer, Fold):
        return chain(reducer.operator, [target, *related])
    if isinstance(reducer, Compare):
        comparisons = [call(reducer.symbol, target, content) for content in related]
        return chain("&&" if reducer.join == "&" else "||", comparisons)
    if reducer == "count":
        return Const(len(related))
    if reducer == "first":
        return related[0]
    if reducer == "last":
        return related[-1]
    table = _SKIP if nulls == "skip" else _PROPAGATE
    return table[reducer](related)
