Extending the algebra core
==========================

This page shows how the algebra core of the temporal framework is built, how a
function or an operator is added to it, and which tests keep the classic algebra
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
the classic algebra
    The language of the temporal algebra as the manuals and the publications
    define it. The flag ``-c`` of *t.rast.algebra*, *t.rast3d.algebra*,
    *t.vect.algebra* and *t.select*, or ``GRASS_TEMPORAL_ALGEBRA=classic``,
    selects it.
the classic profile
    ``grass.temporal.algebra.parser.classic.CLASSIC``, the classic algebra
    computed on the core.
the reference implementation
    :mod:`grass.temporal.classic`, the implementation of the classic algebra that
    is older than the core, kept because published results rely on it. After
    its first mention it is called "the reference".
the public parser classes
    :class:`~grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser`,
    :class:`~grass.temporal.algebra.parser.facade.TemporalRaster3DAlgebraParser`
    and :class:`~grass.temporal.algebra.parser.facade.TemporalVectorAlgebraParser`,
    which the tools and addons call.
the temporal reference
    One of ``l``, ``r``, ``u``, ``i`` and ``d`` in a temporal operator such as
    ``{+,during,l}``; it has nothing to do with the reference implementation.

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
6. Variants: :mod:`~grass.temporal.algebra.profile` has
   :class:`~grass.temporal.algebra.profile.Profile` and
   ``grass.temporal.algebra.profile.CORE``, the rules of the core;
   :mod:`~grass.temporal.algebra.variants` has the helpers of the operations that
   the classic profile uses as well.
7. Syntax, in :mod:`~grass.temporal.algebra.parser`: the lexer, the grammar, the
   nodes of the syntax tree and the operators in braces of the core
   (:mod:`~grass.temporal.algebra.parser.lexer`,
   :mod:`~grass.temporal.algebra.parser.grammar`,
   :mod:`~grass.temporal.algebra.parser.ast`,
   :mod:`~grass.temporal.algebra.parser.operators`); the
   :class:`~grass.temporal.algebra.parser.translate.Translator`, which gives the
   tree its meaning with the operations; the granularity mode
   (:mod:`~grass.temporal.algebra.parser.granularity`). The classic profile has
   its own grammar (:mod:`~grass.temporal.algebra.parser.classic_grammar` with
   the productions in :mod:`~grass.temporal.algebra.parser.classic_productions`)
   and translator (:mod:`~grass.temporal.algebra.parser.classic`, a subclass of
   the translator of the core, with
   :mod:`~grass.temporal.algebra.parser.classic_maps` and
   :mod:`~grass.temporal.algebra.parser.classic_numbers`);
   :mod:`~grass.temporal.algebra.parser.shared` has what both translators check
   alike. :mod:`~grass.temporal.algebra.parser.switch` chooses the algebra, the
   package :mod:`~grass.temporal.algebra.parser` has
   :func:`~grass.temporal.algebra.parser.evaluate`, and
   :mod:`~grass.temporal.algebra.parser.facade` the public parser classes.

The way of an expression
^^^^^^^^^^^^^^^^^^^^^^^^

*t.rast.algebra* creates a
:class:`~grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser` and
calls its ``parse()`` method; with ``-g`` the tool first lets the parser find
the common granularity of the datasets
(``grass.temporal.algebra.parser.facade.TemporalRasterAlgebraParser.setup_common_granularity``).
The parser chooses the profile: the classic one if
``-c`` is given or :func:`~grass.temporal.algebra.parser.switch.classic_selected`
finds ``GRASS_TEMPORAL_ALGEBRA=classic``, the core otherwise.

.. literalinclude:: ../../temporal/algebra/parser/facade.py
    :caption: The choice of the profile in grass.temporal.algebra.parser.facade
    :language: python
    :pyobject: _AlgebraParser._evaluate

:func:`~grass.temporal.algebra.parser.evaluate` reads the expression with the
grammar of the profile into a syntax tree, lets the translator of the profile
turn the tree into a series, which reads each dataset with
:func:`~grass.temporal.algebra.sources.source`, and plans the maps with
:func:`~grass.temporal.algebra.materialize.plan`, with the options that the
profile sets:

.. literalinclude:: ../../temporal/algebra/parser/__init__.py
    :caption: From the expression to the plan in grass.temporal.algebra.parser.evaluate
    :language: python
    :start-after: without overwrite for an existing result dataset or map
    :end-before: # A vector result without maps has no dataset, if the profile says so.

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

The classic algebra
^^^^^^^^^^^^^^^^^^^

The classic profile reads the expression with its own grammar, a frozen copy of
the productions of the reference
(``grass.temporal.algebra.parser.classic_productions.TEXTS``) with the lexer of
the reference. It knows the functions of the cells as tokens of their own:

.. literalinclude:: ../../temporal/algebra/parser/classic_productions.py
    :caption: The functions of the cells in the classic grammar
    :language: python
    :start-after: "p_mapcalc_function": """
    :end-before: "p_mapcalc_operation1": """

A function added to the translator of the core therefore stays a syntax error
with ``-c``. The classic translator
(``grass.temporal.algebra.parser.classic.ClassicTranslator``) overrides
``grass.temporal.algebra.parser.classic.ClassicTranslator._function`` and
``grass.temporal.algebra.parser.classic.ClassicTranslator._call``, but both hand
a function of the cells to the methods of the core (``_call`` once for each
unit of a classic map list), so the new name would be known there; the classic
grammar never builds the node. Adding a function to the classic syntax changes
the classic algebra. Changing the copy alone fails the tests of
``grass_temporal_algebra_classic_grammar_test.py``, among them
``test_frozen_copy_equals_the_parser_classes``, which keeps the copy equal to the
productions of the reference.

The classic profile computes with the same operations, content trees and
backends as the core. A change there can change a result of the classic
algebra as well, and the comparisons with the recorded results of the reference
(see `The safeguards`_) show it. Every change of what ``-c`` computes, a
different map, a different value, or an expression that is accepted instead of
refused or the other way round, needs an explicit decision of the maintainers,
a test, and an entry in the section Classic algebra of the manual page
*temporalchanges* (the manual of *t.rast.algebra* lists some of them). Published results rely on the classic algebra, so it changes
only where it was wrong.

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

The classic grammar has its own tokens and precedence, so the same holds as for
a function: an operator of the core is a syntax error with ``-c`` unless the
classic algebra is changed on purpose.

The safeguards
--------------

The tests below keep the classic algebra computing as it did and the tools on
the core computing as they did before the core.

The gold corpus
    :mod:`grass.temporal.testing.corpus` holds what the reference computed for
    each case of the test suite that compares with it, and the comparisons read
    the stored outcome instead of running the reference. The annotated tag
    ``classic-reference-corpus`` of the repository marks the commit at which the
    corpus was recorded and the comparisons started to read it; since then,
    cases were added and a few entries recorded again, in the commits that
    ``git log classic-reference-corpus.. -- python/grass/temporal/testing/corpus``
    lists. A change that makes the classic profile
    compute another result fails these comparisons, for example
    ``test_profile_equals_reference`` in
    ``temporal/t.rast.algebra/tests/t_rast_algebra_differential_test.py``. The
    corpus key holds the node id of the test, so a test that is renamed or moved
    finds no entry and fails, until the corpus is recorded again
    (``GRASS_TEMPORAL_REFERENCE=record``, see the module docstring).

``GRASS_TEMPORAL_REFERENCE=live``
    runs the reference instead of reading the corpus and fails where the
    reference no longer computes what the corpus holds ("The reference
    implementation no longer computes what the corpus holds"). The comparisons
    that read the corpus stay green after a change of
    :mod:`grass.temporal.classic`, because they do not run it; this mode shows
    the difference. Run it after any change of the reference.

Unread entries
    ``python3 -m grass.temporal.testing.corpus_orphans <directory>`` lists the
    entries of the corpus that no test read and exits with 1 if there is one.
    The directory is the one that ``GRASS_TEMPORAL_CORPUS_TRACE_DIR`` named
    during a run of the tests in both settings of the algebra; with a part of
    the tests, it lists the entries of the others.

Differential tests
    The files ``*_differential_test.py`` of *t.rast.algebra*,
    *t.rast3d.algebra*, *t.vect.algebra* and *t.select* compute each expression
    of their lists with the core and the classic profile and compare the maps,
    except for the differences that the manual lists, and compare the classic
    profile with the corpus. :mod:`grass.temporal.testing.differential` runs
    them; ``t_rast_algebra_published_test.py`` and
    ``t_select_published_test.py`` hold the expressions printed in the
    publication of the algebra (Gebbert, Leppelt and Pebesma, 2019).

Characterization tests
    *t.rast.aggregate*, *t.rast.aggregate.ds*, *t.rast.mapcalc*,
    *t.rast3d.mapcalc* and *t.sample* have no flag for the classic algebra;
    they compute on the core and keep the results they had before. Their files
    ``*_characterization_test.py`` hold the results measured on the tools before
    the port onto the core. A change of the backends that computes a map of a
    granule otherwise fails them: when a granule with one map is computed with
    *r.series* instead of copied with *g.copy*,
    ``test_single_map_granule_keeps_value_type_and_color`` and
    ``test_two_map_granule_method_families`` in
    ``temporal/t.rast.aggregate/tests/t_rast_aggregate_characterization_test.py``
    fail.

The marker ``fixed_algebra``
    The tests of the algebra tools compute on the algebra that
    ``GRASS_TEMPORAL_ALGEBRA`` selects, so a second run with
    ``GRASS_TEMPORAL_ALGEBRA=classic`` checks the classic profile with the same
    tests (the tests of *t.select* take both settings from the fixture
    ``algebra_setting``). A test that chooses the algebra itself, such as a
    comparison of both, carries ``@pytest.mark.fixed_algebra``; the classic run
    deselects it with ``-m "not fixed_algebra"``, so that it runs once. The
    testing guide ``doc/development/testing.md`` describes the settings and the
    corpus in full.

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
the ``expression=`` of each *t.rast.algebra* command, where ``-c`` chooses the
classic algebra. ``test_manual_example_runs`` plans each of them as a dry run
on the datasets of its fixture, or expects the error that the lists
``MANUAL_ERRORS`` and ``CLASSIC_MANUAL_ERRORS`` of the test name for it; an
assignment that reads a map or dataset the fixture lacks is skipped. A change of
the core that breaks an expression of the manual fails it: without ``exp`` in
``grass.temporal.algebra.parser.translate._CELL_FUNCTIONS``, the case
``C = exp(A * 1000)`` fails with "Unknown function exp()". An expression of the
manual that a change makes valid, or invalid, is changed in the manual text and
in these lists in the same commit.

The catalogs of *t.rast.algebra* keep the expressions of the original manual
and of the publication as they were printed, so that a reader can find them;
``test_original_manual_example_plans_in_the_classic_algebra`` plans those of the
original manual with the classic algebra as well, where its fixture has the
datasets.
