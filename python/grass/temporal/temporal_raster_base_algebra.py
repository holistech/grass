"""@package grass.temporal

Temporal raster algebra

SPDX-FileCopyrightText: 2013 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

.. code-block:: pycon

    >>> p = TemporalRasterAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "R = A {+,equal,l} B"
    >>> p.test(expression)
    R = A {+,equal,l} B
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(T_ARITH2_OPERATOR,'{+,equal,l}',1,6)
    LexToken(NAME,'B',1,18)
    >>> expression = "R = A {*,equal|during,r} B"
    >>> p.test(expression)
    R = A {*,equal|during,r} B
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(T_ARITH1_OPERATOR,'{*,equal|during,r}',1,6)
    LexToken(NAME,'B',1,25)
    >>> expression = "R = A {+,equal|during} B"
    >>> p.test(expression)
    R = A {+,equal|during} B
    LexToken(NAME,'R',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(T_ARITH2_OPERATOR,'{+,equal|during}',1,6)
    LexToken(NAME,'B',1,23)

"""

from __future__ import annotations

import copy

import grass.pygrass.modules as pymod
from grass.exceptions import FatalError

from .abstract_dataset import AbstractDatasetComparisonKeyStartTime
from .factory import dataset_factory
from .space_time_datasets import RasterDataset
from .temporal_algebra import (
    GlobalTemporalVar,
    TemporalAlgebraLexer,
    TemporalAlgebraParser,
)


class TemporalRasterAlgebraLexer(TemporalAlgebraLexer):
    """Lexical analyzer for the GRASS temporal algebra"""

    def __init__(self) -> None:
        TemporalAlgebraLexer.__init__(self)

    # Supported r.mapcalc functions.
    mapcalc_functions = {
        "exp": "EXP",
        "log": "LOG",
        "sqrt": "SQRT",
        "abs": "ABS",
        "cos": "COS",
        "acos": "ACOS",
        "sin": "SIN",
        "asin": "ASIN",
        "tan": "TAN",
        "double": "DOUBLE",
        "float": "FLOATEXP",
        "int": "INTEXP",
        "isnull": "ISNULL",
        "isntnull": "ISNTNULL",
        "null": "NULL",
        "exist": "EXIST",
    }

    # Functions that defines single maps with time stamp and without temporal extent.
    map_functions = {"map": "MAP"}

    # This is the list of token names.
    raster_tokens = (
        "MOD",
        "DIV",
        "MULT",
        "ADD",
        "SUB",
        "T_ARITH1_OPERATOR",
        "T_ARITH2_OPERATOR",
        "L_SPAREN",
        "R_SPAREN",
    )

    # Build the token list
    tokens = (
        TemporalAlgebraLexer.tokens
        + raster_tokens
        + tuple(mapcalc_functions.values())
        + tuple(map_functions.values())
    )

    # Regular expression rules for simple tokens
    t_MOD = r"[\%]"
    t_DIV = r"[\/]"
    t_MULT = r"[\*]"
    t_ADD = r"[\+]"
    t_SUB = r"[-]"
    t_T_ARITH1_OPERATOR = r"\{[\%\*\/][,]?[a-zA-Z\| ]*([,])?([lrudi]|left|right|union|disjoint|intersect)?\}"  # noqa: E501
    t_T_ARITH2_OPERATOR = (
        r"\{[+-][,]?[a-zA-Z\| ]*([,])?([lrudi]|left|right|union|disjoint|intersect)?\}"
    )
    t_L_SPAREN = r"\["
    t_R_SPAREN = r"\]"

    # The base class looks the names up in these tables, in this order
    _reserved_tables = TemporalAlgebraLexer._reserved_tables + (
        "mapcalc_functions",
        "map_functions",
    )


class TemporalRasterBaseAlgebraParser(TemporalAlgebraParser):
    """The temporal algebra class

    The class implements the grammar rules that are common to the raster and
    raster3d algebra. The subclasses select the dataset and map types and the
    module that computes the maps through the ``_default_*`` attributes.
    """

    # Get the tokens from the lexer class
    tokens = TemporalRasterAlgebraLexer.tokens

    # Setting equal precedence level for select and hash operations.
    precedence = (
        ("left", "T_SELECT_OPERATOR", "T_SELECT", "T_NOT_SELECT"),  # 1
        ("left", "ADD", "SUB", "T_ARITH2_OPERATOR", "T_HASH_OPERATOR", "HASH"),  # 2
        (
            "left",
            "AND",
            "OR",
            "T_COMP_OPERATOR",
            "MOD",
            "DIV",
            "MULT",
            "T_ARITH1_OPERATOR",
        ),
    )

    _default_stdstype = "strds"
    _default_maptype = "raster"
    _default_mapclass = RasterDataset

    def __init__(
        self,
        pid: int | None = None,
        run: bool = True,
        debug: bool = False,
        spatial: bool = False,
        register_null: bool = False,
        dry_run: bool = False,
        nprocs: int = 1,
        time_suffix=None,
    ) -> None:
        TemporalAlgebraParser.__init__(
            self,
            pid=pid,
            run=run,
            debug=debug,
            spatial=spatial,
            register_null=register_null,
            dry_run=dry_run,
            nprocs=nprocs,
            time_suffix=time_suffix,
        )
        self.m_mapcalc = self._create_mapcalc_module(spatial)

    def _create_mapcalc_module(self, spatial):
        """Return the not yet executed module that computes the result maps"""
        if spatial is True:
            # Spatially related maps may differ in extent
            return self._new_module("r.mapcalc", region="union", nprocs=1)
        return self._new_module("r.mapcalc", nprocs=1)

    def parse(self, expression, basename=None, overwrite: bool = False):
        """Parse the algebra expression and compute the result dataset

        :param expression: The expression, e.g. ``R = A + B``
        :param basename: The basename of the result maps
        :param overwrite: Overwrite existing maps and datasets
        :return: The process chain dictionary
        :raises SyntaxError: for invalid expressions
        """
        self._reject_dataset_type_tokens(TemporalRasterAlgebraLexer(), expression)
        return self._parse(
            TemporalRasterAlgebraLexer(),
            expression,
            self._default_stdstype,
            self._default_maptype,
            self._default_mapclass,
            basename,
            overwrite,
        )

    @staticmethod
    def _command_of(map_i):
        """Return the r.mapcalc command of a map, or its id if it has none"""
        return map_i.cmd_list if hasattr(map_i, "cmd_list") else map_i.get_id()

    def _dry_name(self, *operands):
        """Return the name of the result for a run without computation

        Rules return ``<name>*`` when ``run`` is False, like the rules of the
        base parser. The first operand that is a string names the result.
        """
        for operand in operands:
            if isinstance(operand, str):
                return self._placeholder(operand)
        return None

    def _debug_commands(self, resultlist):
        """Print the commands of the maps if debugging is enabled"""
        if self.debug and isinstance(resultlist, list):
            for map_i in resultlist:
                print(map_i.cmd_list)

    def _transform_commands(self, source, build):
        """Replace the command of each map of source by build(command)

        :param source: Name of a STDS, list of maps or single map
        :param build: Function that gets the current command (or map id) and
                      returns the new command
        :return: The list of maps
        """
        maplist = self.check_stds(source)
        for map_i in maplist:
            map_i.cmd_list = build(self._command_of(map_i))
        return maplist

    def _operate(self, left, right, relations, temporal, operator):
        """Combine two map lists with an arithmetic operator

        Each map of the left list is combined with all maps of the right list
        that have one of the temporal (and spatial) relations to it. The
        maps are aggregated in the order of the relations.
        """
        maplist_a = self.check_stds(left)
        maplist_b = self.check_stds(right)
        complist = self.build_spatio_temporal_topology_list(
            maplist_a,
            maplist_b,
            topolist=relations,
            operator_cmd=True,
            compop=operator,
        )
        return self.set_temporal_extent_list(
            complist, topolist=relations, temporal=temporal
        )

    def _compare(self, left, right, relations, temporal, function, aggregate, convert):
        """Combine two lists of conditions with a boolean operator"""
        complist = self.build_spatio_temporal_topology_list(
            self.check_stds(left),
            self.check_stds(right),
            topolist=relations,
            compare_cmd=True,
            compop=function,
            aggregate=aggregate,
            convert=convert,
        )
        return self.set_temporal_extent_list(
            complist, topolist=relations, temporal=temporal
        )

    def _neighbour_maps(self, name, temporal_offset, spatial_offsets=()):
        """Return the temporal (and spatial) neighbours of the maps of a STDS

        Each result map has the temporal extent of the current map and the
        command of the map at ``temporal_offset`` positions in the dataset,
        indexed spatially with ``spatial_offsets``. Maps without such a
        neighbour are dropped.

        :param name: Name of the STDS
        :param temporal_offset: Offset in the map list; negative for predecessors
        :param spatial_offsets: Row, column (and depth) offsets, may be empty
        """
        maplist = self.check_stds(name)
        resultlist = []
        for index, map_i in enumerate(maplist):
            new_index = index + temporal_offset
            if not 0 <= new_index < len(maplist):
                continue
            map_n = maplist[new_index]
            # Generate an intermediate map for the result map list.
            map_new = self.generate_new_map(map_n, bool_op="and", copy=True)
            map_new.set_temporal_extent(map_i.get_temporal_extent())
            reference = (
                map_new.cmd_list if hasattr(map_new, "cmd_list") else map_n.get_id()
            )
            if spatial_offsets:
                reference += "[%s]" % ",".join(
                    str(offset) for offset in spatial_offsets
                )
            map_new.cmd_list = reference
            # The bare reference, so that a truth value of this map is
            # recognised in _convert_condition_value().
            map_new.neighbour_cmd = reference
            resultlist.append(map_new)
        return resultlist

    def build_command_string(self, map_i, relmap, operator=None, cmd_type=None):
        """This function build the r.mapcalc command string for conditionals,
        spatial variable combinations and boolean comparisons.

        For Example: 'if(a1 == 1, b1, c2)' or 'exist(a1) && sin(b1)'

        :param map_i: map object with temporal extent and built relations.
        :param relmap: map object with defined temporal relation to map_i.
        :param operator: String representing operator between two spatial variables
                        (&&,||,+,-,*,/).
        :param cmd_type: map object with defined temporal relation to map_i:
                        condition, conclusion or operator.

        :return: the resulting command string for conditionals or spatial variable
            combinations
        """
        if cmd_type in {"condition", "conclusion"}:
            template = "if(%s, %s)" if cmd_type == "condition" else "%s, %s"
            return template % (
                self._operand_string(map_i),
                self._operand_string(relmap),
            )
        if cmd_type == "operator":
            if operator is None:
                self.msgr.fatal(
                    _(
                        "Error: Can't build command string for map {name}, "
                        "operator is missing"
                    ).format(name=map_i.get_map_id())
                )
            return "(%s %s %s)" % (
                self._operand_string(map_i),
                operator,
                self._operand_string(relmap),
            )
        return ""

    @staticmethod
    def _operand_string(map_i):
        """Return the command of an operand: the command list of a map, the
        time difference of a td() variable, the map id or the string itself"""
        # td() of an expression such as td(A * 2) hands out maps that carry
        # both the command of the expression and the duration. The operand
        # is the duration, so this check must come before the command list;
        # otherwise N - td(A * 2) computed N - A * 2.
        if (
            hasattr(map_i, "map_value")
            and len(map_i.map_value) > 0
            and map_i.map_value[0].get_type() == "timediff"
        ):
            return map_i.map_value[0].get_type_value()[0]
        if hasattr(map_i, "cmd_list"):
            return map_i.cmd_list
        try:
            return map_i.get_id()
        except AttributeError:
            return map_i

    def compare_cmd_value(
        self,
        map_i,
        compop,
        aggregate,
        temporal_topo_list=None,
        spatial_topo_list=None,
        convert: bool = False,
    ):
        """Function to evaluate two map lists with boolean values by boolean
        comparison operator.

        R = A && B

        R = if(A < 1 && B > 1, A, B)

        R = if(A < 1 {&&,equal|equivalent} B > 1, A, B)

        Extended temporal algebra version with command
        list builder for temporal raster algebra.

        :param map_i: Map object with temporal extent.
        :param compop: Comparison operator, && or ||.
        :param aggregate: Aggregation operator for relation map list, & or \\|.
        :param temporal_topo_list: List of strings for given temporal relations.
        :param spatial_topo_list: List of strings for given spatial relations.
        :param convert: Boolean if conditional values should be converted to
                        r.mapcalc command strings.

        :return: Map object with conditional value that has been evaluated by
                    comparison operators.
        """
        temporal_topo_list = (
            ["EQUAL"] if temporal_topo_list is None else temporal_topo_list
        )
        spatial_topo_list = [] if spatial_topo_list is None else spatial_topo_list
        if convert:
            self._convert_condition_value(map_i)
        if not hasattr(map_i, "cmd_list"):
            return None

        # Build command list list with elements from related maps and given relation
        # operator.
        related_commands = []
        for relationmap in self._related_maps(
            map_i, temporal_topo_list, spatial_topo_list
        ):
            if convert:
                self._convert_condition_value(relationmap)
            if hasattr(relationmap, "cmd_list"):
                related_commands.append(relationmap.cmd_list)

        if not related_commands:
            return None
        # Add command list to result map.
        map_i.cmd_list = "%s%s(%s)" % (
            map_i.cmd_list,
            compop,
            (aggregate + aggregate).join(str(cmd) for cmd in related_commands),
        )
        self._trace(map_i.cmd_list)
        return map_i.cmd_list

    @staticmethod
    def _convert_condition_value(map_i):
        """Turn the boolean condition value of a map into a command (0 or 1)

        A map that already carries a command (a raster comparison chained
        behind a temporal condition) keeps it; overwriting it would discard
        the raster part of the chain. A neighbour map carries only its own
        reference as command, which is no raster part: its condition value
        is the truth value (a time function of A[1] is not the cell value of
        A[1]).
        """
        if getattr(map_i, "condition_value", None) and (
            not hasattr(map_i, "cmd_list")
            or map_i.cmd_list == getattr(map_i, "neighbour_cmd", None)
        ):
            map_i.cmd_list = str(int(map_i.condition_value[0]))

    def operator_cmd_value(
        self, map_i, operator, temporal_topo_list=None, spatial_topo_list=None
    ):
        """Function to evaluate two map lists by given arithmetic operator.

        :param map_i: Map object with temporal extent.
        :param operator: Arithmetic operator, +-\\*/%.
        :param temporal_topo_list: List of strings for given temporal relations.
        :param spatial_topo_list: List of strings for given spatial relations.

        :return: Map object with command list with operators that has been
                    evaluated by implicit aggregation.
        """
        temporal_topo_list = (
            ["EQUAL"] if temporal_topo_list is None else temporal_topo_list
        )
        spatial_topo_list = [] if spatial_topo_list is None else spatial_topo_list

        # Build the command with elements from related maps and given relation
        # operator, the maps are aggregated one after the other.
        command = map_i
        for relationmap in self._related_maps(
            map_i, temporal_topo_list, spatial_topo_list
        ):
            command = self.build_command_string(
                command, relationmap, operator=operator, cmd_type="operator"
            )

        # Add command list to result map.
        map_i.cmd_list = command if command is not map_i else ""
        self._trace("map command string", map_i.cmd_list)
        return map_i.cmd_list

    def set_temporal_extent_list(
        self,
        maplist,
        topolist=None,
        temporal="l",
        cmd_bool: bool = False,
        cmd_type=None,
        operator=None,
    ):
        """Change temporal extent of map list based on temporal relations to
        other map list and given temporal operator.

        :param maplist: List of map objects for which relations has been build
                        correctly.
        :param topolist: List of strings of temporal relations.
        :param temporal: The temporal operator specifying the temporal
                         extent operation (intersection, union, disjoint
                         union, right reference, left reference).
        :param cmd_bool: Boolean if command string should be merged for related maps.
        :param cmd_type: map object with defined temporal relation to map_i:
                        condition, conclusion or operator.
        :param operator: String defining the type of operator.

        :return: Map list with specified temporal extent and optional command string.
        """

        def combine(map_new, map_i, map_j):
            # The r.mapcalc expression string for the operation
            map_new.cmd_list = self.build_command_string(
                map_i, map_j, operator=operator, cmd_type=cmd_type
            )

        # An operator aggregates all related maps of equal time (E + E), a
        # conditional must choose one of them.
        return super().set_temporal_extent_list(
            maplist,
            topolist,
            temporal,
            combine=combine if cmd_bool else None,
            pair_equal_times=cmd_type in {"condition", "conclusion"},
        )

    def build_condition_cmd_list(
        self,
        iflist,
        thenlist,
        elselist=None,
        condition_topolist=None,
        conclusion_topolist=None,
        temporal="l",
        null: bool = False,
    ):
        """This function build the r.mapcalc command strings for spatial conditionals.
        For Example: 'if(a1 == 1, b1, c2)'

        :param iflist: Map list with temporal extents and command list.
        :param thenlist: Map list with temporal extents and command list or numeric
                         string.
        :param elselist: Map list with temporal extents and command list or numeric
                         string.
        :param condition_topolist: List of strings for given temporal relations between
                                   conditions and conclusions.
        :param conclusion_topolist: List of strings for given temporal relations between
                                    conditions (then and else).
        :param temporal: The temporal operator specifying the temporal
                         extent operation (intersection, union, disjoint
                         union, right reference, left reference).
        :param null: Not used, kept for compatibility with earlier versions.

        :return: map list with resulting command string for given condition type.
        """
        condition_topolist = (
            ["EQUAL"] if condition_topolist is None else condition_topolist
        )
        conclusion_topolist = (
            ["EQUAL"] if conclusion_topolist is None else conclusion_topolist
        )
        conclusion = self._build_conclusion(
            thenlist, elselist, conclusion_topolist, temporal
        )
        if isinstance(conclusion, str):
            return self._apply_condition(iflist, conclusion)
        # Build result command map list between conditions and conclusions.
        conditiontopolist = self.build_spatio_temporal_topology_list(
            iflist, conclusion, topolist=condition_topolist
        )
        return self.set_temporal_extent_list(
            conditiontopolist,
            topolist=condition_topolist,
            temporal="r",
            cmd_bool=True,
            cmd_type="condition",
        )

    def _build_conclusion(self, thenlist, elselist, topolist, temporal):
        """Merge the then and else part of a conditional

        :return: A map list with commands "then, else", or a string of
                 numbers if both parts are numeric
        """
        if isinstance(thenlist, list) and isinstance(elselist, list):
            conclusiontopolist = self.build_spatio_temporal_topology_list(
                thenlist, elselist, topolist
            )
            return self.set_temporal_extent_list(
                conclusiontopolist,
                topolist=topolist,
                temporal=temporal,
                cmd_bool=True,
                cmd_type="conclusion",
            )
        if isinstance(thenlist, str) and isinstance(elselist, str):
            return thenlist + "," + elselist
        if isinstance(thenlist, list) and isinstance(elselist, str):
            return self._merge_with_number(thenlist, elselist, number_first=False)
        if isinstance(thenlist, str) and isinstance(elselist, list):
            return self._merge_with_number(elselist, thenlist, number_first=True)
        if isinstance(thenlist, str) or isinstance(elselist, str):
            # A number without counterpart concludes nothing
            return []
        return thenlist

    def _merge_with_number(self, maplist, number, number_first):
        """Add the number as then or else part to the command of each map"""
        for map_i in maplist:
            if number_first:
                map_i.cmd_list = self.build_command_string(
                    number, map_i, cmd_type="conclusion"
                )
            else:
                map_i.cmd_list = self.build_command_string(
                    map_i, number, cmd_type="conclusion"
                )
        return maplist

    def _apply_condition(self, iflist, conclusion):
        """Make the commands of the condition maps if(condition, conclusion)

        :param conclusion: Command string with the then (and else) part
        """
        for map_i in iflist:
            map_i.cmd_list = self.build_command_string(
                map_i, conclusion, cmd_type="condition"
            )
        return iflist

    def _conclusion_operands(self, t, position):
        """Read the then (and else) operands of an if() rule

        The operands are separated by commas, followed by the closing
        parenthesis. A number is returned as string, null() as "null()"
        and a STDS or expression as map list.

        :param t: The symbols of the grammar rule
        :param position: Index in t of the first operand
        """
        operands = []
        while True:
            value = t[position]
            if value == "null":
                # NULL LPAREN RPAREN
                operands.append("null()")
                position += 3
            elif isinstance(value, (int, float)):
                operands.append(str(value))
                position += 1
            else:
                operands.append(self.check_stds(value))
                position += 1
            if t[position] != ",":
                return operands
            position += 1

    def _temporal_conditional_with_number(self, t, first_operand):
        """Evaluate if([relations,] t_var_expr, then, number) of a grammar rule

        The base grammar has no rule for a number as else part of a purely
        temporal condition. The maps rejected by the condition get the number
        as their command, so the result keeps one map per then map.

        :param t: The symbols of the grammar rule
        :param first_operand: Index in t of the then part
        """
        if not self.run:
            t[0] = self._dry_name(*(t[i] for i in range(first_operand, len(t))))
            return
        topolist = None
        if first_operand == 7:
            topolist = self.eval_toperator(t[3], optype="relation")[0]
        thenlist, number = self._conclusion_operands(t, first_operand)
        condition = self.build_condition_list(
            t[first_operand - 2], thenlist, topolist or ("EQUAL",)
        )
        selected = self.eval_condition_list(condition)
        rejected = self.eval_condition_list(condition, inverse=True)
        if self._else_takes_unrelated(topolist):
            rejected += self._unrelated(thenlist, condition)
        for map_i in rejected:
            map_i.cmd_list = number
        for map_i in selected + rejected:
            # Maps without related condition never got a condition value.
            if hasattr(map_i, "condition_value"):
                del map_i.condition_value
        t[0] = sorted(selected + rejected, key=AbstractDatasetComparisonKeyStartTime)
        self._debug_commands(t[0])

    def _conditional(self, t, first_operand):
        """Evaluate if([relations,] condition, then[, else]) of a grammar rule

        :param t: The symbols of the grammar rule
        :param first_operand: Index in t of the then part: 5 without and 7
                              with relations
        """
        if not self.run:
            t[0] = self._dry_name(*(t[i] for i in range(first_operand, len(t))))
            return
        condition_topolist = ["EQUAL"]
        if first_operand == 7:
            condition_topolist = self.eval_toperator(t[3], optype="relation")[0]
        iflist = self.check_stds(t[first_operand - 2])
        operands = self._conclusion_operands(t, first_operand)
        if len(operands) == 1 and isinstance(operands[0], str):
            t[0] = self._apply_condition(iflist, operands[0])
        else:
            t[0] = self.build_condition_cmd_list(
                iflist,
                operands[0],
                operands[1] if len(operands) > 1 else None,
                condition_topolist=condition_topolist,
                conclusion_topolist=["EQUAL"],
                temporal="r",
            )
        self._debug_commands(t[0])

    # Result maps are numbered from 0
    _first_result_number = 0

    def _needs_new_map(self, map_i, dbif):
        """Every result map is computed by mapcalc, also an unchanged one"""
        return True

    def _handle_empty_result(self, stds_name):
        """Report an empty result and describe its dataset in the process chain"""
        super()._handle_empty_result(stds_name)
        self.process_chain_dict["STDS"] = {
            "name": stds_name,
            "stdstype": self.stdstype,
            "temporal_type": self._result_temporal_type([]),
        }

    def _materialize_maps(self, maps, names, needs_new):
        """Compute the result maps with the mapcalc module

        The expression of a map is its command list. A map without command
        is copied, if it exists.

        :return: The result maps with temporal and spatial extent
        """
        expressions = [self._mapcalc_expression(map_i) for map_i in maps]
        queue = None
        if self.dry_run is False:
            # Process queue for parallel mapcalc processing
            queue = pymod.ParallelModuleQueue(int(self.nprocs))

        result_maps = []
        for map_i, name, expression in zip(maps, names, expressions, strict=True):
            new_map = map_i.get_new_instance(f"{name}@{self.mapset}")
            new_map.set_temporal_extent(map_i.get_temporal_extent())
            new_map.set_spatial_extent(map_i.get_spatial_extent())
            new_map.is_new = True
            result_maps.append(new_map)

            # Change map name to given basename in a copy of the module.
            module = copy.deepcopy(self.m_mapcalc)
            module.inputs["expression"].value = f"{name}={expression}"
            module.flags["overwrite"].value = self.overwrite
            if self.debug:
                print(module.get_bash())
            self.process_chain_dict["processes"].append(module.get_dict())
            if queue is not None:
                queue.put(module)

        if queue is not None:
            queue.wait()
        return result_maps

    def _mapcalc_expression(self, map_i):
        """Return the mapcalc expression that produces the content of the map"""
        if hasattr(map_i, "cmd_list"):
            return map_i.cmd_list
        if map_i.map_exists():
            # Copy map if it exists b = a
            return map_i.get_map_id()
        self.msgr.fatal(_("Error computing map <{name}>").format(name=map_i.get_id()))

    def p_expr_spmap_function(self, t):
        # Add a single map.
        # Only the spatial extent of the map is evaluated.
        # Temporal extent is not existing.
        # Examples:
        #    R = map(A)
        """
        mapexpr : MAP LPAREN stds RPAREN
        """
        if self.run:
            t[0] = self._single_map_command(t[3])
        else:
            t[0] = "map(" + t[3] + ")"

        self._trace("map(" + t[3] + ")")

    def _single_map_command(self, name):
        """Return the mapcalc command of a raster map without time stamp

        :raises FatalError: if the map does not exist
        """
        # Check for mapset in given map input.
        id_input = name if "@" in name else name + "@" + self.mapset
        map_i = dataset_factory(self.maptype, id_input)
        if map_i.map_exists() is False:
            raise FatalError(
                _("%s map <%s> not found in GRASS spatial database")
                % (map_i.get_type(), id_input)
            )
        # Select dataset entry from database.
        map_i.select(dbif=self.dbif)
        map_i.cmd_list = "(%s)" % (map_i.get_map_id())
        return map_i.cmd_list

    def p_arith1_operation(self, t) -> None:
        # A % B
        # A / B
        # A * B
        # A % td(B)
        # A * td(B)
        # A / td(B)
        """
        expr : stds MOD  stds
             | expr MOD  stds
             | stds MOD  expr
             | expr MOD  expr
             | stds DIV  stds
             | expr DIV  stds
             | stds DIV  expr
             | expr DIV  expr
             | stds MULT stds
             | expr MULT stds
             | stds MULT expr
             | expr MULT expr
             | stds MOD  t_td_var
             | expr MOD  t_td_var
             | stds DIV  t_td_var
             | expr DIV  t_td_var
             | stds MULT t_td_var
             | expr MULT t_td_var
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[3])
            return
        # The simple operator is the one with the equal relation and the
        # left time stamp, see the manual.
        t[0] = self._operate(t[1], t[3], ["EQUAL"], "l", t[2])
        self._debug_commands(t[0])

    def p_arith1_operation_numeric1(self, t) -> None:
        # A % 1
        # A / 4
        # A * 5
        # A % map(b1)
        # A * map(b2)
        # A / map(b3)
        """
        expr : stds MOD  number
             | expr MOD  number
             | stds DIV  number
             | expr DIV  number
             | stds MULT number
             | expr MULT number
             | stds MOD  numberstr
             | expr MOD  numberstr
             | stds DIV  numberstr
             | expr DIV  numberstr
             | stds MULT numberstr
             | expr MULT numberstr
             | stds MOD  mapexpr
             | expr MOD  mapexpr
             | stds DIV  mapexpr
             | expr DIV  mapexpr
             | stds MULT mapexpr
             | expr MULT mapexpr
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        t[0] = self._transform_commands(
            t[1], lambda command: "(%s %s %s)" % (command, t[2], t[3])
        )
        self._debug_commands(t[0])

    def p_arith1_operation_numeric2(self, t) -> None:
        # 1 % A
        # 4 / A
        # 5 * A
        # map(b1) % A
        # map(b4) / A
        # map(b5) * A
        """
        expr : number    MOD  stds
             | number    MOD  expr
             | number    DIV  stds
             | number    DIV  expr
             | number    MULT stds
             | number    MULT expr
             | numberstr MOD  stds
             | numberstr MOD  expr
             | numberstr DIV  stds
             | numberstr DIV  expr
             | numberstr MULT stds
             | numberstr MULT expr
             | mapexpr   MOD  stds
             | mapexpr   MOD  expr
             | mapexpr   DIV  stds
             | mapexpr   DIV  expr
             | mapexpr   MULT stds
             | mapexpr   MULT expr
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(
            t[3], lambda command: "(%s %s %s)" % (t[1], t[2], command)
        )
        self._debug_commands(t[0])

    def p_arith2_operation(self, t) -> None:
        # A + B
        # A - B
        # A + td(B)
        # A - td(B)
        """
        expr : stds ADD stds
             | expr ADD stds
             | stds ADD expr
             | expr ADD expr
             | stds SUB stds
             | expr SUB stds
             | stds SUB expr
             | expr SUB expr
             | stds ADD t_td_var
             | expr ADD t_td_var
             | expr SUB t_td_var
             | stds SUB t_td_var

        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[3])
            return
        # The simple operator is the one with the equal relation and the
        # left time stamp, see the manual.
        t[0] = self._operate(t[1], t[3], ["EQUAL"], "l", t[2])
        self._debug_commands(t[0])

    def p_arith2_operation_numeric1(self, t) -> None:
        # A + 2
        # A - 3
        # A + map(b4)
        # A - map(b5)
        """
        expr : stds ADD number
             | expr ADD number
             | stds SUB number
             | expr SUB number
             | stds ADD numberstr
             | expr ADD numberstr
             | stds SUB numberstr
             | expr SUB numberstr
             | stds ADD mapexpr
             | expr ADD mapexpr
             | stds SUB mapexpr
             | expr SUB mapexpr
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        t[0] = self._transform_commands(
            t[1], lambda command: "(%s %s %s)" % (command, t[2], t[3])
        )
        self._debug_commands(t[0])

    def p_arith2_operation_numeric2(self, t) -> None:
        # 2 + A
        # 3 - A
        # map(b2) + A
        # map(b3) - A
        """
        expr : number    ADD stds
             | number    ADD expr
             | number    SUB stds
             | number    SUB expr
             | numberstr ADD stds
             | numberstr ADD expr
             | numberstr SUB stds
             | numberstr SUB expr
             | mapexpr   ADD stds
             | mapexpr   ADD expr
             | mapexpr   SUB stds
             | mapexpr   SUB expr
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(
            t[3], lambda command: "(%s %s %s)" % (t[1], t[2], command)
        )
        self._debug_commands(t[0])

    def p_arith1_operation_relation(self, t) -> None:
        # A {*, equal, l} B
        # A {*, equal, l} td(B)
        # A {*, equal, l} B {/, during, r} C
        # A {*, equal, l} B {/, equal, l}  C {/, during, r} D
        """
        expr : stds T_ARITH1_OPERATOR stds
             | expr T_ARITH1_OPERATOR stds
             | stds T_ARITH1_OPERATOR expr
             | expr T_ARITH1_OPERATOR expr
             | stds T_ARITH1_OPERATOR t_td_var
             | expr T_ARITH1_OPERATOR t_td_var
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[3])
            return
        relations, temporal, function, aggregate = self.eval_toperator(
            t[2], optype="raster"
        )
        t[0] = self._operate(t[1], t[3], relations, temporal, function)
        self._debug_commands(t[0])

    def p_arith2_operation_relation(self, t) -> None:
        # A {+, equal, l} B
        # A {+, equal, l} td(b)
        # A {+, equal, l} B {-, during, r} C
        # A {+, equal, l} B {+, equal, l}  C {-, during, r} D
        """
        expr : stds T_ARITH2_OPERATOR stds
             | expr T_ARITH2_OPERATOR stds
             | stds T_ARITH2_OPERATOR expr
             | expr T_ARITH2_OPERATOR expr
             | stds T_ARITH2_OPERATOR t_td_var
             | expr T_ARITH2_OPERATOR t_td_var
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[3])
            return
        relations, temporal, function, aggregate = self.eval_toperator(
            t[2], optype="raster"
        )
        t[0] = self._operate(t[1], t[3], relations, temporal, function)
        self._debug_commands(t[0])

    def p_arith_operation_numeric_string(self, t) -> None:
        # 1 + 1
        # 1 - 1
        # 1 * 1
        # 1 / 1
        # 1 % 1
        """
        numberstr : number ADD number
                  | number SUB number
                  | number DIV number
                  | number MULT number
                  | number MOD number
        """
        numstring = "(%s %s %s)" % (t[1], t[2], t[3])

        t[0] = numstring

        self._trace(numstring)

    def p_mapcalc_function(self, t) -> None:
        # Supported mapcalc functions.
        """
        mapcalc_arith : ABS
                      | LOG
                      | SQRT
                      | EXP
                      | COS
                      | ACOS
                      | SIN
                      | ASIN
                      | TAN
                      | DOUBLE
                      | FLOATEXP
                      | INTEXP
        """
        t[0] = t[1]

        self._trace(t[1])

    def p_mapcalc_operation1(self, t) -> None:
        # sin(A)
        # log(B)
        """
        expr : mapcalc_arith LPAREN stds RPAREN
             | mapcalc_arith LPAREN expr RPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(
            t[3], lambda command: "%s(%s)" % (t[1].lower(), command)
        )
        self._debug_commands(t[0])

    def p_mapexpr_operation(self, t) -> None:
        # sin(map(a))
        """
        mapexpr : mapcalc_arith LPAREN mapexpr RPAREN
        """
        if self.run:
            t[0] = "%s(%s)" % (t[1].lower(), t[3])

        self._trace(t[3])

    def p_s_var_expr_1(self, t) -> None:
        #   isnull(A)
        """
        s_var_expr : ISNULL LPAREN stds RPAREN
                   | ISNULL LPAREN expr RPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(
            t[3], lambda command: "%s(%s)" % (t[1].lower(), command)
        )
        self._debug_commands(t[0])

    def p_s_var_expr_2(self, t) -> None:
        #   isntnull(A)
        """
        s_var_expr : ISNTNULL LPAREN stds RPAREN
                   | ISNTNULL LPAREN expr RPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(t[3], lambda command: "!isnull(%s)" % command)
        self._debug_commands(t[0])

    def p_s_var_expr_3(self, t) -> None:
        #   A <= 2
        """
        s_var_expr : stds comp_op number
                   | expr comp_op number
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        t[0] = self._transform_commands(
            t[1], lambda command: "%s %s %s" % (command, t[2], t[3])
        )
        self._debug_commands(t[0])

    def p_s_var_expr_4(self, t) -> None:
        #   exist(B)
        """
        s_var_expr : EXIST LPAREN stds RPAREN
                   | EXIST LPAREN expr RPAREN
        """
        if not self.run:
            t[0] = self._dry_name(t[3])
            return
        t[0] = self._transform_commands(t[3], lambda command: command)
        self._debug_commands(t[0])

    def p_s_var_expr_comp(self, t) -> None:
        #   A <= 2 || B == 10
        #   A < 3 && A > 1
        """
        s_var_expr : s_var_expr AND AND s_var_expr
                   | s_var_expr OR  OR  s_var_expr
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[4])
            return
        t[0] = self._compare(
            t[1], t[4], ["EQUAL"], "l", t[2] + t[3], t[2], convert=False
        )
        self._debug_commands(t[0])

    def p_s_var_expr_comp_op(self, t) -> None:
        #   A <= 2 {||} B == 10
        #   A < 3 {&&, equal} A > 1
        """
        s_var_expr : s_var_expr T_COMP_OPERATOR s_var_expr
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[3])
            return
        relations, temporal, function, aggregate = self.eval_toperator(
            t[2], optype="boolean"
        )
        t[0] = self._compare(
            t[1], t[3], relations, temporal, function, aggregate, convert=False
        )
        self._debug_commands(t[0])

    def p_s_expr_condition_if(self, t) -> None:
        #   if(s_var_expr, B)
        #   if(A == 1, B)
        """
        expr : IF LPAREN s_var_expr  COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA expr RPAREN
        """
        self._conditional(t, 5)

    def p_s_numeric_condition_if(self, t) -> None:
        #   if(s_var_expr, 1)
        #   if(A == 5, 10)
        """
        expr : IF LPAREN s_var_expr  COMMA number RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN RPAREN
        """
        self._conditional(t, 5)

    def p_t_numeric_else_condition_if(self, t) -> None:
        #   if(td(A) == 1, A, 0)
        """
        expr : IF LPAREN t_var_expr COMMA stds COMMA number RPAREN
             | IF LPAREN t_var_expr COMMA stds COMMA NULL LPAREN RPAREN RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA number RPAREN
             | IF LPAREN t_var_expr COMMA expr COMMA NULL LPAREN RPAREN RPAREN
        """
        self._temporal_conditional_with_number(t, 5)

    def p_t_numeric_else_condition_if_relation(self, t) -> None:
        #   if({during}, td(B) == 2, A, 0)
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA stds COMMA NULL LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA t_var_expr COMMA expr COMMA NULL LPAREN RPAREN RPAREN
        """
        self._temporal_conditional_with_number(t, 7)

    def p_s_expr_condition_if_relation(self, t) -> None:
        #   if({equal||during}, s_var_expr, A)
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr RPAREN
        """
        self._conditional(t, 7)

    def p_s_expr_condition_elif(self, t) -> None:
        #   if(s_var_expr, A, B)
        """
        expr : IF LPAREN s_var_expr  COMMA stds COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA stds COMMA expr RPAREN
             | IF LPAREN s_var_expr  COMMA expr COMMA stds RPAREN
             | IF LPAREN s_var_expr  COMMA expr COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN ts_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN ts_var_expr COMMA expr COMMA expr RPAREN
        """
        self._conditional(t, 5)

    def p_s_numeric_condition_elif(self, t) -> None:
        #   if(s_var_expr, 1, 2)
        #   if(A == 5, 10, 0)
        """
        expr : IF LPAREN s_var_expr  COMMA number COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA number COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  NULL   LPAREN RPAREN RPAREN
        """  # noqa: E501
        self._conditional(t, 5)

    def p_s_numeric_expr_condition_elif(self, t) -> None:
        #   if(s_var_expr, 1, A)
        #   if(A == 5 && C > 5, A, null())
        """
        expr : IF LPAREN s_var_expr  COMMA number COMMA  stds   RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN s_var_expr  COMMA number COMMA  expr   RPAREN
             | IF LPAREN s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN s_var_expr  COMMA stds   COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN s_var_expr  COMMA expr   COMMA  number RPAREN
             | IF LPAREN s_var_expr  COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  stds   RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN ts_var_expr COMMA number COMMA  expr   RPAREN
             | IF LPAREN ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN ts_var_expr COMMA stds   COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN ts_var_expr COMMA expr   COMMA  number RPAREN
             | IF LPAREN ts_var_expr COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
        """
        self._conditional(t, 5)

    def p_s_numeric_expr_condition_elif_relation(self, t) -> None:
        #   if({during},s_var_expr, 1, A)
        #   if({during}, A == 5, A, null())
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA number COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA number COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA number COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  stds   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA number COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA NULL   LPAREN RPAREN COMMA  expr   RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds   COMMA  NULL   LPAREN RPAREN RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr   COMMA  number RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr   COMMA  NULL   LPAREN RPAREN RPAREN
        """  # noqa: E501
        self._conditional(t, 7)

    def p_s_expr_condition_elif_relation(self, t) -> None:
        #   if({equal||during}, s_var_expr, A, B)
        """
        expr : IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA s_var_expr  COMMA expr COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA stds COMMA expr RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr COMMA stds RPAREN
             | IF LPAREN T_REL_OPERATOR COMMA ts_var_expr COMMA expr COMMA expr RPAREN
        """
        self._conditional(t, 7)

    def p_ts_var_expr1(self, t) -> None:
        # Combination of spatial and temporal conditional expressions.
        # Examples:
        #   A <= 2 || start_date <= 2013-01-01
        #   end_date > 2013-01-15 && A > 10
        #  IMPORTANT: Only the intersection of map lists in conditionals are
        #  exported.
        """
        ts_var_expr : s_var_expr  AND AND t_var_expr
                    | t_var_expr  AND AND s_var_expr
                    | t_var_expr  OR  OR  s_var_expr
                    | s_var_expr  OR  OR  t_var_expr
                    | ts_var_expr AND AND s_var_expr
                    | ts_var_expr AND AND t_var_expr
                    | ts_var_expr OR  OR  s_var_expr
                    | ts_var_expr OR  OR  t_var_expr
                    | s_var_expr  AND AND ts_var_expr
                    | t_var_expr  AND AND ts_var_expr
                    | s_var_expr  OR  OR  ts_var_expr
                    | t_var_expr  OR  OR  ts_var_expr
        """
        if not self.run:
            t[0] = self._dry_name(t[1], t[4])
            return
        t[0] = self._compare(
            t[1], t[4], ["EQUAL"], "l", t[2] + t[3], t[2], convert=True
        )

    def p_hash_operation(self, t) -> None:
        # Calculate the number of maps within an interval of another map from a
        # second space time dataset.
        # A # B
        # A {equal,r#} B
        """
        expr : t_hash_var
        """
        if not self.run:
            t[0] = self._dry_name(t[1])
            return
        resultlist = self.check_stds(t[1])
        for map_i in resultlist:
            counts = [
                obj.td for obj in map_i.map_value if isinstance(obj, GlobalTemporalVar)
            ]
            # The number of maps related to map_i; later values replace earlier ones
            map_i.cmd_list = "(%s)" % (counts[-1])
        t[0] = resultlist
        self._debug_commands(resultlist)

    def p_mapexpr_numeric(self, t) -> None:
        # map(L) + 1
        # 2 * map(L)
        # map(L) - map(L)
        # Every pair of the operands that are computed as text (a number, a
        # chain of numbers and a map) has a production, so that the pair is
        # reduced with the precedence of its operator. Without one the parser
        # shifted, and map(L) - 1 - A was read as L - (1 - A).
        """
        mapexpr : mapexpr   MOD  number
                | mapexpr   DIV  number
                | mapexpr   MULT number
                | mapexpr   ADD  number
                | mapexpr   SUB  number
                | number    MOD  mapexpr
                | number    DIV  mapexpr
                | number    MULT mapexpr
                | number    ADD  mapexpr
                | number    SUB  mapexpr
                | mapexpr   MOD  numberstr
                | mapexpr   DIV  numberstr
                | mapexpr   MULT numberstr
                | mapexpr   ADD  numberstr
                | mapexpr   SUB  numberstr
                | numberstr MOD  mapexpr
                | numberstr DIV  mapexpr
                | numberstr MULT mapexpr
                | numberstr ADD  mapexpr
                | numberstr SUB  mapexpr
                | mapexpr   MOD  mapexpr
                | mapexpr   DIV  mapexpr
                | mapexpr   MULT mapexpr
                | mapexpr   ADD  mapexpr
                | mapexpr   SUB  mapexpr
        """
        t[0] = "(%s %s %s)" % (t[1], t[2], t[3])

        self._trace(t[0])

    def p_mapexpr_paren(self, t) -> None:
        # (map(L) + 1)
        """
        mapexpr : LPAREN mapexpr RPAREN
        """
        t[0] = t[2]

    def p_numberstr_chain(self, t) -> None:
        # 1 + 2 - 3
        # Chains of numbers, grouped from the left as in mathematics.
        """
        numberstr : numberstr MOD  number
                  | numberstr DIV  number
                  | numberstr MULT number
                  | numberstr ADD  number
                  | numberstr SUB  number
                  | number    MOD  numberstr
                  | number    DIV  numberstr
                  | number    MULT numberstr
                  | number    ADD  numberstr
                  | number    SUB  numberstr
                  | numberstr MOD  numberstr
                  | numberstr DIV  numberstr
                  | numberstr MULT numberstr
                  | numberstr ADD  numberstr
                  | numberstr SUB  numberstr
        """
        t[0] = "(%s %s %s)" % (t[1], t[2], t[3])

        self._trace(t[0])


if __name__ == "__main__":
    import doctest

    doctest.testmod()
