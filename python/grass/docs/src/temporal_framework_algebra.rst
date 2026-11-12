Extending the algebra core
==========================

This page shows how the algebra core of the temporal framework is built, how a
function or an operator is added to it, and which tests keep the algebra
computing as before. It complements the section on the algebra core in
:doc:`temporal_framework` and the manual of *t.rast.algebra*, which describes
the syntax for users.

The example in the second section computes with the Python API of the core. The
documentation tests of the repository run its commands in a new project and
compare what they print with what the page shows, and every name of
``grass.temporal`` that the example calls is part of the public contract of the
library. The excerpts of the source files are included from the files
themselves, so they show the code of this version.

The page uses the terms of the docstring of :mod:`grass.temporal.algebra`:

the core
    :mod:`grass.temporal.algebra`, the package.
the public parser classes
    :class:`~grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser`,
    :class:`~grass.temporal.algebra.parser.facade.TemporalRaster3DAlgebraParser`
    and :class:`~grass.temporal.algebra.parser.facade.TemporalVectorAlgebraParser`,
    which the tools and addons call.
the temporal reference
    One of ``l``, ``r``, ``u``, ``i`` and ``d`` in a temporal operator such as
    ``{+,during,l}``.

.. contents::
   :local:
   :depth: 1

The layout of the core
----------------------

The core is built in layers, from the bottom up:

1. Values: :mod:`~grass.temporal.algebra.series` has the time stamps, the boxes,
   the slots and the series; :mod:`~grass.temporal.algebra.content` has the
   content trees of a slot and :func:`~grass.temporal.algebra.content.call`,
   which builds a call and folds constants as *r.mapcalc* would compute them.
2. The link to the rest of ``grass.temporal``:
   :mod:`~grass.temporal.algebra.adapters` builds throw-away map objects, so that
   the relations, the time arithmetic and the granularity of the library are
   used and not written a second time; :mod:`~grass.temporal.algebra.maptypes`
   names each map type for the temporal database and the tools;
   :mod:`~grass.temporal.algebra.sources` reads datasets and maps as series.
3. Relations: :mod:`~grass.temporal.algebra.relations`.
4. Operations: :mod:`~grass.temporal.algebra.operations` (``select``, ``pairs``,
   ``gather``, ``apply``, ``where``, ``choose``, ``merge``, ``cell_offset``,
   ``buffer``, ``lift``); :mod:`~grass.temporal.algebra.reducers`, how ``gather``
   combines related slots; :mod:`~grass.temporal.algebra.time_functions`
   (``timevar``, ``retime``, ``neighbour``, ``granules``).
5. Computing: :mod:`~grass.temporal.algebra.backends` turns a content tree into
   module calls (*r.mapcalc*, *r3.mapcalc*, *r.series*, *g.copy*, *v.overlay*,
   *v.patch*, *v.buffer*); in :mod:`~grass.temporal.algebra.materialize`,
   :func:`~grass.temporal.algebra.materialize.plan` returns these calls with the
   map names and the registration as a
   :class:`~grass.temporal.algebra.materialize.ProcessChain`, and
   :func:`~grass.temporal.algebra.materialize.materialize` runs them and
   registers the maps.
6. Syntax, in :mod:`~grass.temporal.algebra.parser`: the lexer, the grammar, the
   nodes of the syntax tree and the operators in braces of the core
   (:mod:`~grass.temporal.algebra.parser.lexer`,
   :mod:`~grass.temporal.algebra.parser.grammar`,
   :mod:`~grass.temporal.algebra.parser.ast`,
   :mod:`~grass.temporal.algebra.parser.operators`); the
   :class:`~grass.temporal.algebra.parser.translate.Translator`, which gives the
   tree its meaning with the operations; the granularity mode
   (:mod:`~grass.temporal.algebra.parser.granularity`);
   :mod:`~grass.temporal.algebra.parser.shared` has checks of the translator
   that do not depend on the syntax tree. The package
   :mod:`~grass.temporal.algebra.parser` has
   :func:`~grass.temporal.algebra.parser.evaluate`, and
   :mod:`~grass.temporal.algebra.parser.facade` the public parser classes.

The way of an expression
^^^^^^^^^^^^^^^^^^^^^^^^

*t.rast.algebra* creates a
:class:`~grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser` and
calls its ``parse()`` method; with ``-g`` the tool first lets the parser find
the common granularity of the datasets
(``grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser.setup_common_granularity``).
The parser passes the expression and its options on:

.. literalinclude:: ../../temporal/algebra/parser/facade.py
    :caption: The call of evaluate in grass.temporal.algebra.parser.facade
    :language: python
    :pyobject: _AlgebraParser._evaluate

:func:`~grass.temporal.algebra.parser.evaluate` reads the expression with the
grammar of the core into a syntax tree, lets the translator turn the tree into
a series, which reads each dataset with
:func:`~grass.temporal.algebra.sources.source`, and plans the maps with
:func:`~grass.temporal.algebra.materialize.plan`:

.. literalinclude:: ../../temporal/algebra/parser/__init__.py
    :caption: From the expression to the plan in grass.temporal.algebra.parser.evaluate
    :language: python
    :start-after: without overwrite for an existing result dataset or map
    :end-before: # Also for a result without maps, which gets an empty dataset.

A dry run (``-d`` of *t.rast.algebra*) prints the process chain, the dictionary
that :func:`~grass.temporal.algebra.parser.evaluate` returns for this plan; a
run passes the plan to
:func:`~grass.temporal.algebra.materialize.materialize`, which computes and
registers the maps.

Computing with the Python API
-----------------------------

The functions of the core take series and return series; no map is computed
until :func:`~grass.temporal.algebra.materialize.materialize` runs. The example
reads a dataset of daily temperatures, takes the mean of each period of two
days and rounds it with the function ``round()`` of *r.mapcalc*. It prints the
plan, the maps and module calls that
:func:`~grass.temporal.algebra.materialize.plan` returns, before anything is
written.

The data are four maps, one per day:

.. code-block:: text
    :name: example-commands-algebra-data

    r.mapcalc expression="temperature_1 = 4"
    r.mapcalc expression="temperature_2 = 7"
    r.mapcalc expression="temperature_3 = 10"
    r.mapcalc expression="temperature_4 = 15"
    t.create output=temperature type=strds temporaltype=absolute title=Temperature description="Daily temperature"
    t.register input=temperature maps=temperature_1,temperature_2,temperature_3,temperature_4 start=2020-01-01 increment="1 days"

The script:

.. code-block:: python
    :caption: two_day_means.py
    :name: example-tool-file-algebra

    import grass.temporal as tgis
    import grass.temporal.algebra as ta

    tgis.init()
    temperature = ta.source("temperature")
    periods = ta.granules("2020-01-01", "2020-01-05", "2 days")
    mean = ta.gather(periods, ta.contains, temperature, reduce="mean")
    rounded = ta.apply("round", mean)

    chain = ta.plan(rounded, "temperature_two_days")
    for planned in chain.maps:
        print(planned.name, planned.extent.start, planned.extent.end)
        for call in planned.calls:
            options = [f"{key}={value}" for key, value in call.parameters.items()]
            print("   ", call.name, " ".join(options))

    ta.materialize(rounded, "temperature_two_days")

It prints the plan:

.. code-block:: text
    :name: example-commands-algebra-plan

    python3 two_day_means.py

.. code-block:: text
    :name: example-output-algebra-plan

    temperature_two_days_0 2020-01-01 00:00:00 2020-01-03 00:00:00
        r.mapcalc expression="temperature_two_days_0"=round((("temperature_1@PERMANENT" + "temperature_2@PERMANENT") / 2.0)) nprocs=1
    temperature_two_days_1 2020-01-03 00:00:00 2020-01-05 00:00:00
        r.mapcalc expression="temperature_two_days_1"=round((("temperature_3@PERMANENT" + "temperature_4@PERMANENT") / 2.0)) nprocs=1

and :func:`~grass.temporal.algebra.materialize.materialize` computes the planned
maps, so that the means 5.5 and 12.5 are registered as 6 and 13:

.. code-block:: text
    :name: example-commands-algebra-result

    t.rast.list input=temperature_two_days columns=name,start_time,end_time,min,max

.. code-block:: text
    :name: example-output-algebra-result

    name|start_time|end_time|min|max
    temperature_two_days_0|2020-01-01 00:00:00|2020-01-03 00:00:00|6.0|6.0
    temperature_two_days_1|2020-01-03 00:00:00|2020-01-05 00:00:00|13.0|13.0

:func:`~grass.temporal.algebra.time_functions.granules` makes a series of
periods without maps, and :func:`~grass.temporal.algebra.operations.gather`
relates the slots of the temperature to each period (``contains``: the period
contains the day) and reduces them; :func:`~grass.temporal.algebra.operations.pairs`
makes one slot for each related pair instead. Both name their relation, and
``gather`` its reducer; :func:`~grass.temporal.algebra.operations.apply` needs
series with equal time stamps and aligns none silently.

:func:`~grass.temporal.algebra.operations.apply` takes the name of an operator or
a function of *r.mapcalc* as a string; a Python function is refused with a
``TypeError``, and a name that *r.mapcalc* does not have is refused with a
``ValueError`` when the series is planned. ``round()`` is such a function of
*r.mapcalc* that the syntax of *t.rast.algebra* does not offer: the Python API
reaches every function in ``grass.temporal.algebra.backends._FUNCTIONS``, the
syntax only those that the translator knows.
:func:`~grass.temporal.algebra.operations.lift` turns a series of numbers into a
series of maps that are constant; it adds no computation. A new kind of
computation therefore needs a change of the core, as the next section shows.

Adding a function or an operator
--------------------------------

A function
^^^^^^^^^^

The steps below add a function of *r.mapcalc* with one argument, such as
``round()``, to the syntax of the core, in the order in which an expression
meets them.

**The grammar** needs no change: it reads every ``name(arguments)`` as a
function node (``grass.temporal.algebra.parser.grammar.Grammar.p_function``),
and the translator decides which names exist.

**The translator**: ``grass.temporal.algebra.parser.translate.Translator._function``
reads ``tmap()`` and ``map()`` and, in a selection, the functions that name the
type of a dataset; any other name must be in
``grass.temporal.algebra.parser.translate._CELL_FUNCTIONS``,
``grass.temporal.algebra.parser.translate._OTHER_FUNCTIONS`` or
``grass.temporal.algebra.time_functions.TIMEVARS``, or the translator refuses it
with "Unknown function" before it reads a dataset. A function of the cells
with one argument is added to
``grass.temporal.algebra.parser.translate._CELL_FUNCTIONS``; that is all
``round()`` needs. A function with other arguments goes to
``grass.temporal.algebra.parser.translate._OTHER_FUNCTIONS`` and gets its own
branch in ``grass.temporal.algebra.parser.translate.Translator._call``.

.. literalinclude:: ../../temporal/algebra/parser/translate.py
    :caption: The functions of the cells that the syntax of the core reads
    :language: python
    :start-after: _CELL_FUNCTIONS = (
    :end-before: _OTHER_FUNCTIONS = (

.. literalinclude:: ../../temporal/algebra/parser/translate.py
    :caption: Translator._call, the meaning of each known function
    :language: python
    :pyobject: Translator._call

**The backends** write *r.mapcalc* and *r3.mapcalc* text, so the function must
be one of *r.mapcalc*. ``grass.temporal.algebra.backends._FUNCTIONS`` lists the
names that :class:`~grass.temporal.algebra.backends.RasterBackend` writes as a
call (in ``grass.temporal.algebra.backends.RasterBackend._call``), and ``round``
is among them. A name that is missing there is added there, after checking that
*r.mapcalc* and *r3.mapcalc* compute it. Vector maps take only the overlays of
``grass.temporal.algebra.backends.VECTOR_FUNCTIONS``.

.. literalinclude:: ../../temporal/algebra/backends.py
    :caption: The functions of r.mapcalc that the backends write
    :language: python
    :start-after: # name of a map and fail only there, so it is rejected when planning.
    :end-before: # The overlays of vector maps: the content names the operator of v.overlay,

**Numbers and time values**: a series of numbers, such as the result of
``td()``, is computed in Python, and so are calls whose arguments are all
constants. :func:`~grass.temporal.algebra.content.call` folds a call with the
Python implementation in ``grass.temporal.algebra.content._SCALAR`` or, for a
function that decides about null itself such as ``if`` or ``isnull``, in
``grass.temporal.algebra.content._NULL_AWARE``;
``grass.temporal.algebra.content.evaluate`` reads both. A function without an
entry in either cannot be applied to a series of numbers:
:func:`~grass.temporal.algebra.operations.apply` raises
``grass.temporal.algebra.content.ScalarFunctionError`` ("cannot be computed for
scalar values"), as it does today for ``sin(td(A))``. An entry there must
compute what *r.mapcalc* computes, with nulls and integer arithmetic; the
comments above the table name the measurements it relies on.

.. literalinclude:: ../../temporal/algebra/content.py
    :caption: The Python implementations of the operators and functions
    :language: python
    :start-after: # check above), comparisons give 1 or 0 and a null operand gives null.
    :end-before: # Functions that decide about null themselves instead of propagating it

**Tests and manual**: a case in ``temporal_algebra_syntax_translate_test.py`` of
the library, as for ``sin(A)``, and a computed case in the tests of
*t.rast.algebra*, both with values derived by hand; the function in the list of
raster functions of the manual of *t.rast.algebra*, which no test compares with
the translator. One test stands in the way of ``round()`` on purpose:
``test_round_function_is_not_part_of_the_algebra`` in
``temporal/t.rast.algebra/tests/t_rast_algebra_arithmetic_test.py`` expects a
syntax error and fails on the core as soon as ``round`` is in
``grass.temporal.algebra.parser.translate._CELL_FUNCTIONS``. Adding the function
means changing that test, which is a decision of the maintainers, not a side
effect.

The published expressions
^^^^^^^^^^^^^^^^^^^^^^^^^

A new function or operator adds to the language; it must not change what an
expression that was valid before computes. The expressions printed in the
publication of the algebra (Gebbert, Leppelt and Pebesma, 2019) are kept with
their results in ``t_rast_algebra_published_test.py`` and
``t_select_published_test.py``, with values derived by hand. Every change of
what such an expression computes, a different map, a different value, or an
expression that is accepted instead of refused or the other way round, needs an
explicit decision of the maintainers, a test, and an entry in the manual page
*temporalchanges*.

An operator
^^^^^^^^^^^

An operator of the core touches more places than a function, all of them in
the core:

- the lexer: a token in ``grass.temporal.algebra.parser.lexer.TOKENS`` with its
  rule in ``grass.temporal.algebra.parser.lexer.Lexer``, and, for the form in
  braces such as ``{+,during}``, its first symbol in
  ``grass.temporal.algebra.parser.lexer._OPERATOR_KINDS`` and its symbol in
  ``grass.temporal.algebra.parser.operators.SYMBOLS``;
- the grammar: its precedence in
  ``grass.temporal.algebra.parser.grammar.Grammar.precedence`` and its production
  in ``grass.temporal.algebra.parser.grammar.Grammar.p_binary`` (or
  ``grass.temporal.algebra.parser.grammar.Grammar.p_operator`` for the form in
  braces);
- the translator: its meaning in
  ``grass.temporal.algebra.parser.translate.Translator._binary_values``;
- the content: ``grass.temporal.algebra.content.LEFT_ASSOCIATIVE`` if
  *r.mapcalc* reads it from left to right, and its Python implementation in
  ``grass.temporal.algebra.content._SCALAR``;
- the backend: how ``grass.temporal.algebra.backends.RasterBackend._call``
  writes it.

The safeguards
--------------

The tests below keep the algebra computing as the reference implementation
did, except for the differences that the manuals list, and the tools on the
core computing as they did before the core. The reference implementation is
not part of GRASS any more, so the tests hold its results as recorded values.
The values were recorded on 2026-11-12 from a reference implementation that
already included the corrections listed in the changes page, so they are not
the results of GRASS 8.5.

Tests of lists of expressions
    The files ``*_recorded_outcomes_test.py`` of *t.rast.algebra*,
    *t.rast3d.algebra*, *t.vect.algebra* and *t.select* compute each expression
    of their lists on the core. Each expression of one list must give the
    outcome that the reference implementation gave on 2026-11-12, recorded in
    ``data/reference_outcomes.json`` next to the test. Each expression of the
    list of differences must give the outcome that the list names, which the
    manual lists as a difference from the releases before GRASS 8.6.
    :mod:`grass.temporal.testing.outcomes` runs them;
    ``t_rast_algebra_published_test.py`` and
    ``t_select_published_test.py`` hold the expressions printed in the
    publication of the algebra (Gebbert, Leppelt and Pebesma, 2019) with
    fixed target values.

Characterization tests
    *t.rast.aggregate*, *t.rast.aggregate.ds*, *t.rast.mapcalc*,
    *t.rast3d.mapcalc* and *t.sample* compute on the core and keep the
    results they had before. Their files
    ``*_characterization_test.py`` hold the results measured on the tools before
    the port onto the core. A change of the backends that computes a map of a
    granule otherwise fails them: when a granule with one map is computed with
    *r.series* instead of copied with *g.copy*,
    ``test_single_map_granule_keeps_value_type_and_color`` and
    ``test_two_map_granule_method_families`` in
    ``temporal/t.rast.aggregate/tests/t_rast_aggregate_characterization_test.py``
    fail.

The manuals
-----------

The manuals of *t.rast.algebra*, *t.rast3d.algebra*, *t.select* and
*t.vect.algebra* show many expressions, each with its result, in examples
without a Python tab (``<!-- example: shell-only -->``); the four are the only
manuals that may have such examples. The manual tests in
``temporal/tests`` run the examples and compare their output with the output the
manual shows.

The semantics test of *t.rast.algebra*
(``temporal/t.rast.algebra/tests/t_rast_algebra_semantics_test.py``) reads every
assignment of the manual: the lines ``X = ...`` of its ``sh`` code blocks and
the ``expression=`` of each *t.rast.algebra* command.
``test_manual_example_runs`` plans each of them as a dry run on the datasets of
its fixture, or expects the error that the list ``MANUAL_ERRORS`` of the test
names for it; an
assignment that reads a map or dataset the fixture lacks is skipped. A change of
the core that breaks an expression of the manual fails it: without ``exp`` in
``grass.temporal.algebra.parser.translate._CELL_FUNCTIONS``, the case
``C = exp(A * 1000)`` fails with "Unknown function exp()". An expression of the
manual that a change makes valid, or invalid, is changed in the manual text and
in this list in the same commit.

The catalogs of *t.rast.algebra* keep the expressions of the publication and
those of the original manual that the algebra computes as they were printed, so
that a reader can find them.
