"""@package grass.temporal

Temporal vector algebra

SPDX-FileCopyrightText: 2014 GRASS Development Team
SPDX-License-Identifier: GPL-2.0-or-later

:authors: Thomas Leppelt and Soeren Gebbert

.. code-block:: pycon

    >>> import grass.temporal as tgis
    >>> tgis.init(True)
    >>> p = tgis.TemporalVectorAlgebraLexer()
    >>> p.build()
    >>> p.debug = True
    >>> expression = "E = A : B ^ C : D"
    >>> p.test(expression)
    E = A : B ^ C : D
    LexToken(NAME,'E',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(NAME,'A',1,4)
    LexToken(T_SELECT,':',1,6)
    LexToken(NAME,'B',1,8)
    LexToken(XOR,'^',1,10)
    LexToken(NAME,'C',1,12)
    LexToken(T_SELECT,':',1,14)
    LexToken(NAME,'D',1,16)
    >>> expression = "E = buff_a(A, 10)"
    >>> p.test(expression)
    E = buff_a(A, 10)
    LexToken(NAME,'E',1,0)
    LexToken(EQUALS,'=',1,2)
    LexToken(BUFF_AREA,'buff_a',1,4)
    LexToken(LPAREN,'(',1,10)
    LexToken(NAME,'A',1,11)
    LexToken(COMMA,',',1,12)
    LexToken(INT,10,1,14)
    LexToken(RPAREN,')',1,16)

"""

from __future__ import annotations

import copy

import grass.pygrass.modules as pygrass

from .algebra.parser import evaluate
from .space_time_datasets import VectorDataset
from .temporal_algebra import TemporalAlgebraLexer, TemporalAlgebraParser


class TemporalVectorAlgebraLexer(TemporalAlgebraLexer):
    """Lexical analyzer for the GRASS temporal vector algebra"""

    # Buffer functions from v.buffer
    vector_buff_functions = {
        "buff_p": "BUFF_POINT",
        "buff_l": "BUFF_LINE",
        "buff_a": "BUFF_AREA",
    }

    # This is the list of token names.
    vector_tokens = (
        "DISOR",
        "XOR",
        "NOT",
        "T_OVERLAY_OPERATOR",
    )

    # Build the token list
    tokens = (
        TemporalAlgebraLexer.tokens
        + vector_tokens
        + tuple(vector_buff_functions.values())
    )

    # Regular expression rules for simple tokens
    t_DISOR = r"\+"
    t_XOR = r"\^"
    t_NOT = r"\~"
    t_T_OVERLAY_OPERATOR = (
        r"\{[\|&+\^\~][,]?[a-zA-Z\| ]*" + TemporalAlgebraLexer._OPERATOR_TAIL
    )

    _reserved_tables = TemporalAlgebraLexer._reserved_tables + (
        "vector_buff_functions",
    )


# Overlay operator symbol to the operator of v.overlay; "disor" is v.patch
OVERLAY_OPERATORS = {"&": "and", "|": "or", "^": "xor", "~": "not", "+": "disor"}

# Buffer function to the feature type of v.buffer
BUFFER_TYPES = {"buff_p": "point", "buff_l": "line", "buff_a": "area"}


class TemporalVectorAlgebraParser(TemporalAlgebraParser):
    """The temporal algebra class"""

    # Get the tokens from the lexer class
    tokens = TemporalVectorAlgebraLexer.tokens

    # Setting equal precedence level for select and hash operations.
    precedence = (
        (
            "left",
            "T_SELECT_OPERATOR",
            "T_SELECT",
            "T_NOT_SELECT",
            "T_HASH_OPERATOR",
            "HASH",
        ),  # 1
        (
            "left",
            "AND",
            "OR",
            "T_COMP_OPERATOR",
            "T_OVERLAY_OPERATOR",
            "DISOR",
            "NOT",
            "XOR",
        ),  # 2
    )

    # The vector maps of the result are numbered from 0
    _first_result_number = 0

    def __init__(
        self,
        pid: int | None = None,
        run: bool = False,
        debug: bool = True,
        spatial: bool = False,
        classic: bool | None = None,
    ) -> None:
        """Create the parser

        classic selects the classic algebra of this module (True) or the
        algebra core (False).
        """
        TemporalAlgebraParser.__init__(self, pid, run, debug, spatial)

        self.m_overlay = self._new_module("v.overlay", quiet=True)
        self.m_rename = self._new_module("g.rename", quiet=True)
        self.m_patch = self._new_module("v.patch", quiet=True)
        self.m_buffer = self._new_module("v.buffer", quiet=True)
        self.classic = classic

    def parse(self, expression, basename: str | None = None, overwrite: bool = False):
        """Parse the expression and run the computation

        The expression is translated onto grass.temporal.algebra, unless the
        classic algebra of this module is selected (see __init__).

        :param expression: The assignment, e.g. ``"R = A & B"``
        :param basename: Prefix of the names of the new vector maps
        :param overwrite: Overwrite existing result maps and datasets
        :return: The process chain dictionary; its ``register`` entry lists the
            (name, start, end) of the registered maps
        :raises SyntaxError: for invalid expressions
        """
        if not self._classic():
            return evaluate(
                expression,
                kind="vector",
                basename=basename,
                overwrite=overwrite,
                run=self.run,
                debug=self.debug,
                spatial=self.spatial,
            )
        self._reject_dataset_type_tokens(TemporalVectorAlgebraLexer(), expression)
        return self._parse(
            TemporalVectorAlgebraLexer(),
            expression,
            "stvds",
            "vector",
            VectorDataset,
            basename,
            overwrite,
        )

    def _classic(self):
        # Only an explicit classic=False selects the core here, until the
        # tests of t.vect.algebra hold for both algebras.
        return True if self.classic is None else self.classic

    def _new_result_map(self, map_i):
        """Create the result map of an overlay: it keeps the id of the last
        intermediate map of the command list, which is renamed to the final name.

        The map is not registered as removable. The intermediate maps are
        registered by ``operator_cmd_value``; the final one must survive.
        """
        return self.generate_new_map(
            base_map=map_i, bool_op="and", copy=True, rename=False, remove=False
        )

    def operator_cmd_value(
        self, map_i, operator, temporal_topo_list=None, spatial_topo_list=None
    ):
        """Aggregate the related maps of map_i with an overlay operator.

        :param map_i: Map object with temporal extent.
        :param operator: Overlay operator, &|+^~.
        :param temporal_topo_list: List of strings for given temporal relations.
        :param spatial_topo_list: List of strings for given spatial relations.

        :return: Command list with the v.overlay and v.patch modules that
            aggregate the related maps into one result map. The id of
            map_i is set to the temporary name of the last output.
        """
        overlay_operator = OVERLAY_OPERATORS[operator]
        temporal_topo_list = temporal_topo_list or ["EQUAL"]
        commands = list(getattr(map_i, "cmd_list", []))
        first_input = map_i.get_id()
        for relationmap in self._related_maps(
            map_i, temporal_topo_list, spatial_topo_list or []
        ):
            commands += getattr(relationmap, "cmd_list", [])
            name = self.generate_map_name()
            self.removable_maps[name] = VectorDataset(f"{name}@{self.mapset}")
            map_i.set_id(f"{name}@{self.mapset}")
            commands.append(
                self._overlay_command(
                    overlay_operator, first_input, relationmap.get_id(), name
                )
            )
            first_input = name
        map_i.cmd_list = commands
        return commands

    def overlay_cmd_value(self, map_i, tbrelations, function, topolist=None):
        """Deprecated alias of ``operator_cmd_value`` with its former signature.

        ``tbrelations`` is not used any more, the relations are taken from map_i.
        """
        return self.operator_cmd_value(map_i, function, topolist)

    def _overlay_command(self, operator, first_input, second_input, output):
        """Create the (not yet run) v.overlay or v.patch module"""
        if operator == "disor":
            module = copy.deepcopy(self.m_patch)
            module.inputs["input"].value = f"{first_input},{second_input}"
        else:
            module = copy.deepcopy(self.m_overlay)
            module.inputs["operator"].value = operator
            module.inputs["ainput"].value = str(first_input)
            module.inputs["binput"].value = str(second_input)
        module.run_ = False
        module.outputs["output"].value = output
        module.flags["overwrite"].value = self.overwrite
        return module

    def _needs_new_map(self, map_i, dbif) -> bool:
        """Maps with commands are computed, the others copied if their extent changed"""
        return hasattr(map_i, "cmd_list") or super()._needs_new_map(map_i, dbif)

    def _handle_empty_result(self, stds_name) -> None:
        """A result without maps creates no dataset"""

    def _materialize_maps(self, maps, names, needs_new):
        """Run the command lists, rename their output, copy maps of changed extent.

        Maps whose commands produce no map (empty overlay) are left out.
        """
        queue = pygrass.ParallelModuleQueue(int(self.nprocs))
        result_maps = []
        for map_i, name, new in zip(maps, names, needs_new, strict=True):
            if hasattr(map_i, "cmd_list"):
                if self._run_commands(map_i):
                    self._rename_map(map_i, name)
                    result_maps.append(map_i)
            elif new:
                result_maps.append(self._copy_map(map_i, name, queue))
            else:
                result_maps.append(map_i)
        queue.wait()
        return result_maps

    def _qualified(self, name):
        """The map name with mapset"""
        return name if "@" in name else f"{name}@{self.mapset}"

    def _run_commands(self, map_i):
        """Run the command list of a result map.

        :return: False if the result is empty and has to be dropped
        """
        for cmd in map_i.cmd_list:
            if cmd.name == "v.overlay" and not self._overlay_inputs_usable(map_i, cmd):
                return False
            self.msgr.message("Run command:\n" + cmd.get_bash())
            cmd.run()
            if cmd.returncode != 0:
                self.msgr.fatal(
                    _("Error starting {command} : \n{error}").format(
                        command=cmd.get_bash(), error=cmd.outputs.stderr
                    )
                )
            output = self._qualified(cmd.outputs["output"].value)
            if not map_i.get_new_instance(output).map_exists():
                self.msgr.warning(_("Command created no map <{}>").format(output))
                return False
        return True

    def _overlay_inputs_usable(self, map_i, cmd):
        """Check that the inputs of v.overlay exist and have areas.

        v.overlay breaks on maps without areas. Intermediate results can be
        empty, then the result is dropped with a warning. An input map of the
        expression without areas is an error of the user and reported as such.
        """
        for name in (cmd.inputs["ainput"].value, cmd.inputs["binput"].value):
            vector = map_i.get_new_instance(self._qualified(name))
            intermediate = name.split("@")[0] in self.names
            if not vector.map_exists():
                if not intermediate:
                    self.msgr.fatal(_("Vector map <{}> not found").format(name))
                self.msgr.warning(
                    _("Dropping result: <{}> was not created").format(name)
                )
                return False
            vector.load()
            if vector.metadata.get_number_of_areas() == 0:
                if not intermediate:
                    self.msgr.fatal(
                        _("Vector map <{}> has no areas, v.overlay needs areas").format(
                            name
                        )
                    )
                self.msgr.warning(
                    _("Dropping result: intermediate map <{}> has no areas").format(
                        name
                    )
                )
                return False
        return True

    def _rename_map(self, map_i, newident):
        """Give the computed map its final name"""
        # The temporary name is not removable any more
        self.removable_maps.pop(map_i.get_name(), None)
        mapset = map_i.get_mapset()
        module = copy.deepcopy(self.m_rename)
        module.inputs["vector"].value = (map_i.get_name(), newident)
        module.flags["overwrite"].value = self.overwrite
        module.run()
        map_i.set_id(f"{newident}@{mapset}")
        map_i.is_new = True

    def p_overlay_operation(self, t) -> None:
        """
        expr : stds AND stds
             | expr AND stds
             | stds AND expr
             | expr AND expr
             | stds OR stds
             | expr OR stds
             | stds OR expr
             | expr OR expr
             | stds XOR stds
             | expr XOR stds
             | stds XOR expr
             | expr XOR expr
             | stds NOT stds
             | expr NOT stds
             | stds NOT expr
             | expr NOT expr
             | stds DISOR stds
             | expr DISOR stds
             | stds DISOR expr
             | expr DISOR expr
        """
        if self.run:
            t[0] = self._overlay(t[1], t[3], ["EQUAL"], "l", t[2])
        self._trace(str(t[1]) + t[2] + str(t[3]))

    def p_overlay_operation_relation(self, t) -> None:
        """
        expr : stds T_OVERLAY_OPERATOR stds
             | expr T_OVERLAY_OPERATOR stds
             | stds T_OVERLAY_OPERATOR expr
             | expr T_OVERLAY_OPERATOR expr
        """
        if self.run:
            t[0] = self._overlay_with_operator(t[1], t[3], t[2])
        self._trace(str(t[1]) + t[2] + str(t[3]))

    def _overlay_with_operator(self, left, right, operator):
        """Overlay with a ``{operator,relations,temporal}`` expression"""
        with self._reporting_syntax_errors():
            relations, temporal, function, _aggregate = self.eval_toperator(
                operator, optype="overlay"
            )
            return self._overlay(left, right, relations, temporal, function)
        return []

    def _overlay(self, left, right, relations, temporal, function):
        """Build the overlay command lists and temporal extents of two operands

        An invalid relation name is reported as syntax error (see
        ``_report_error``), because PLY would swallow it here.
        """
        maplist_a = self.check_stds(left)
        maplist_b = self.check_stds(right)
        with self._reporting_syntax_errors():
            complist = self.build_spatio_temporal_topology_list(
                maplist_a,
                maplist_b,
                topolist=relations,
                operator_cmd=True,
                compop=function,
            )
            bool_op = "and" if function == "&" else "disor"
            return self.set_temporal_extent_list(
                complist, topolist=relations, temporal=temporal, bool_op=bool_op
            )
        return []

    def p_buffer_operation(self, t) -> None:
        """
        expr : buff_function LPAREN stds COMMA number RPAREN
             | buff_function LPAREN expr COMMA number RPAREN
        """

        if self.run:
            resultlist = []
            for map_i in self.check_stds(t[3]):
                # Generate an intermediate name for the result map list.
                map_new = self.generate_new_map(
                    base_map=map_i, bool_op=None, copy=True, remove=True
                )
                # Change spatial extent based on buffer size.
                map_new.spatial_buffer(float(t[5]))
                module = copy.deepcopy(self.m_buffer)
                module.run_ = False
                module.inputs["type"].value = BUFFER_TYPES[t[1]]
                module.inputs["input"].value = str(map_i.get_id())
                module.inputs["distance"].value = float(t[5])
                module.outputs["output"].value = map_new.get_name()
                module.flags["overwrite"].value = self.overwrite
                # Do not append to the list shared with map_i
                map_new.cmd_list = [*getattr(map_new, "cmd_list", []), module]
                resultlist.append(map_new)

            t[0] = resultlist

    def p_buff_function(self, t) -> None:
        """buff_function    : BUFF_POINT
        | BUFF_LINE
        | BUFF_AREA
        """
        t[0] = t[1]


###############################################################################

if __name__ == "__main__":
    import doctest

    doctest.testmod()
