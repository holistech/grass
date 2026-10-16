"""The variant of the algebra that evaluate() computes

A profile collects what differs between the core algebra and another
variant of the algebra that is built on the core: the grammar that reads an
expression and the translator class that turns the syntax tree into
operations, and the rules for planning and computing the result maps.

The profile is an object that is handed down to the places that use it, not a
global setting, so that two variants can run in one process. The places that
plan and compute maps do not see the profile: plan(), materialize(), source()
and the backends take the single options they need as keywords, and
evaluate() fills them from the profile. A field of the profile and the
keyword it feeds have the same default, the rule of the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .backends import MapcalcStyle


@dataclass(frozen=True)
class Profile:
    """The rules of one variant of the algebra

    The defaults are the rules of the core.

    :param grammar: an object with parse(text) that returns the syntax tree
        (grass.temporal.algebra.parser.ast.Statement) of "name = expression";
        None reads the syntax of the core
    :param translator: the Translator class (or a subclass of it) that
        translates the tree; evaluate() calls it with the keywords of
        Translator and profile=; None takes Translator
    :param mapcalc: how the r.mapcalc text is written (plan())
    :param classic_absence_check: look for existing result maps first and
        report them and an existing dataset in the words of the parser
        classes (materialize(), check_absent())
    :param keep_empty_vector_maps: register a computed vector map that has no
        primitives (materialize())
    :param vector_dataset_if_empty: create the dataset of a vector result
        that has no map; False creates none and says nothing, as the parser
        class for vector maps (materialize())
    :param copies_by_position: number the copies of a selection by the
        position in the result, not by their own count (plan())
    :param empty_result_type_from_input: give a result without maps the
        temporal type of the first dataset with maps that the expression
        reads, not "absolute" (plan())
    :param one_temporal_type: refuse a dataset whose temporal type differs
        from that of the first dataset with maps (evaluate())
    :param union_region_when_spatial: compute every raster map of a spatial
        run in the union of the regions of its input maps, also when no
        spatial relation was used (plan())
    :param list_order: number, plan and register the results in the list
        order of the series (Series.listed()), not in time order (plan())
    :param database_order: read the maps of a dataset sorted by start only,
        so that maps with equal start keep the order of the temporal
        database (source())
    :param classic_errors: report ValueErrors of the core as the exception
        classes of the parser classes (evaluate())
    """

    grammar: Any = None
    translator: Any = None
    mapcalc: MapcalcStyle = field(default_factory=MapcalcStyle)
    classic_absence_check: bool = False
    keep_empty_vector_maps: bool = False
    vector_dataset_if_empty: bool = True
    copies_by_position: bool = False
    empty_result_type_from_input: bool = False
    one_temporal_type: bool = False
    union_region_when_spatial: bool = False
    list_order: bool = False
    database_order: bool = False
    classic_errors: bool = False


CORE = Profile()
