Writing a temporal tool
=======================

This page shows how a new ``t.*`` tool is built: the layout of its directory, the
steps that the tools share, the messages and their recordings, the manual and
the tests. It complements the overview of the library in :doc:`temporal_framework`
and the user documentation in the manual page *temporalintro*.

The tool in the first section is complete. The documentation tests of the
repository write it to a file, run the commands of this page against it in a new
project and compare what it prints with what the page shows. Every name of
``grass.temporal`` that the tool calls is part of the public contract of the
library, so a change of the library that breaks the example fails there. The
tool is not part of the repository: it is a model, and the tools in ``temporal/``
are the examples to copy from.

The rules for the code, the comments, the commit messages and the tests of the
whole repository are in ``AGENTS.md`` and ``doc/development/style_guide.md``;
this page names only what is specific to the temporal tools.

.. contents::
   :local:
   :depth: 1

The layout of a tool
--------------------

A tool lives in its own directory ``temporal/<name>/`` with these files:

- ``<name>.py``, the tool: a comment header, the options in ``%option`` blocks and
  the code;
- ``<name>.md`` and ``<name>.html``, the manual (see `The manual`_);
- ``Makefile``, a few lines for Autotools, which differ between tools only in
  ``PGM``;
- ``tests/``, the tests (see `The tests`_).

.. literalinclude:: ../../../../temporal/t.shift/Makefile
    :caption: The Makefile of t.shift, the model for every Python tool of the directory
    :start-after: MODULE_TOPDIR = ../../

CMake builds the tools from one list: the name of the tool belongs to
``temporal_script_modules_list`` in ``temporal/CMakeLists.txt``, and a loop at the
end of that file builds each entry. Autotools builds the subdirectories of
``SUBDIRS`` in ``temporal/Makefile``, so the name is entered there as well.

.. literalinclude:: ../../../../temporal/CMakeLists.txt
    :caption: The end of temporal/CMakeLists.txt, which builds every tool of the list
    :start-after: build_program_in_subdir(t.connect DEPENDS grass_gis grass_temporal grass_parson)

A tool starts as a comment header, then the ``%module`` block, one ``%option`` or
``%flag`` block for each option, and the code. The standard options
(``G_OPT_STRDS_INPUT``, ``G_OPT_STDS_OUTPUT``, ``G_OPT_F_INPUT`` and the others of
``lib/gis/parser_standard_options.c``) are preferred over options defined from
scratch, as for every GRASS tool. The tool at the end of the file calls
``gs.parser()``, which reads the header and fills ``options`` and ``flags``.

``main()`` imports ``grass.temporal`` as its first statement, not at the top of the
file. ``gs.parser()`` answers ``--help`` and ``--interface-description`` before
``main()`` runs, and the graphical dialogs of GRASS build themselves from the
interface description, so neither may pay the start-up cost of the library, which
loads ``sqlite3``, ``numpy`` and the C libraries. ``grass_temporal_tool_imports_test.py`` in
``python/grass/temporal/tests`` keeps this: it starts every tool of
``temporal/`` with ``--interface-description`` and ``-X importtime`` and fails when
a module of ``grass.temporal`` shows among the imports. The same test counts the
tools, so a new tool in the repository changes that number in the same commit.

After the import, a tool calls :func:`~grass.temporal.state.init`, which creates the
temporal database of the current mapset if it does not exist, and opens a
connection with :class:`~grass.temporal.db.SQLDatabaseInterfaceConnection`. A
tool closes the connection on every way out; the example does it in a
``finally`` clause. :func:`~grass.temporal.open_stds.open_old_stds` returns an
existing space time dataset of the given type. A name without a mapset is searched
first in the current mapset, then on the search path; ``name@mapset`` names a
dataset of another mapset of the project that has a temporal database. A dataset that
does not exist ends the run with a message. A tool that creates a space time dataset
asks :func:`~grass.temporal.open_stds.check_new_stds` or
:func:`~grass.temporal.open_stds.open_new_stds` before it computes anything: both
refuse a name that is not legal, a dot in the name and an existing dataset without
``--overwrite``, and :func:`~grass.temporal.open_stds.check_new_stds_name` is the part
that refuses the dot.

The example tool
^^^^^^^^^^^^^^^^

``t.example.count`` counts the maps of a space time raster dataset that lie in a time
range. A map lies in the range when its start is not before **start** and its end,
or its start for a time instant, is not after **end**. The maps named in the
file of **exclude** are left out. The tool reads and writes nothing but a number.

.. code-block:: python
    :caption: t.example.count.py
    :name: example-tool-file

    #!/usr/bin/env python3

    # %module
    # % description: Counts the maps of a space time raster dataset in a time range.
    # % keyword: temporal
    # % keyword: statistics
    # % keyword: time
    # %end

    # %option G_OPT_STRDS_INPUT
    # %end

    # %option
    # % key: start
    # % type: string
    # % description: Start of the range, absolute time such as 2020-01-02
    # % required: no
    # %end

    # %option
    # % key: end
    # % type: string
    # % description: End of the range, absolute time such as 2020-01-04
    # % required: no
    # %end

    # %option G_OPT_F_INPUT
    # % key: exclude
    # % description: Name of a file that lists maps to leave out, one name per line
    # % required: no
    # %end

    import grass.script as gs


    def selected_maps(stds, start, end, excluded, dbif):
        """Return the registered maps that lie in the range and are not excluded"""
        selected = []
        for map_ in stds.get_registered_maps_as_objects(dbif=dbif) or []:
            map_start, map_end = map_.get_temporal_extent_as_tuple()
            if map_.get_name() in excluded:
                continue
            if start is not None and map_start < start:
                continue
            if end is not None and (map_end or map_start) > end:
                continue
            selected.append(map_)
        return selected


    def main():
        # Imported here, not at module level: gs.parser() answers --help and
        # --interface-description before main() runs, and these need no temporal code.
        import grass.temporal as tgis

        tgis.init()
        dbif = tgis.SQLDatabaseInterfaceConnection()
        dbif.connect()
        try:
            stds = tgis.open_old_stds(options["input"], "strds", dbif)
            if not stds.is_time_absolute():
                gs.fatal(
                    _("Space time dataset <{}> has relative time").format(stds.get_id())
                )
            try:
                limits = [
                    tgis.option_to_datetime(options[key], key) if options[key] else None
                    for key in ("start", "end")
                ]
                excluded = (
                    set(tgis.names_from_file(options["exclude"]))
                    if options["exclude"]
                    else set()
                )
            except ValueError as error:
                gs.fatal(str(error))
            print(len(selected_maps(stds, *limits, excluded, dbif)))
        finally:
            dbif.close()


    if __name__ == "__main__":
        options, flags = gs.parser()
        main()

``options`` is a module variable that ``gs.parser()`` fills in the guard at the
end of the file, which is why ``main()`` reads it without a parameter. The tools
of ``temporal/`` declare ``global tgis`` in ``main()`` when helper functions of
the file need the library, as ``shift_by_list`` in *t.shift* does; the helper of
this example does not, so it does not. The two ``option_to_datetime`` calls and the call of ``names_from_file`` are the
pattern of `The shared steps`_: a helper checks one option and raises
``ValueError`` with a translated text, and the tool decides how the run ends. A
result that is data, here the number, goes to the standard output with ``print()``;
messages for the user go through ``gs.message()``, ``gs.warning()`` and ``gs.fatal()``.

To try the tool without installing it, save the listing as ``t.example.count.py`` in a
folder, open a GRASS session in a project and run the tool with ``python3`` in
that folder. ``--help`` prints its interface; the tool needs no entry in the
Makefiles for this. The first block makes a dataset of four daily maps, as
four points in time, and a file that names two of them. The next ones count.

.. code-block:: text
    :name: example-commands-setup

    r.mapcalc expression="temp_1 = 1"
    r.mapcalc expression="temp_2 = 2"
    r.mapcalc expression="temp_3 = 3"
    r.mapcalc expression="temp_4 = 4"
    t.create type=strds temporaltype=absolute output=temperature title="Temperature" description="Four days"
    t.register input=temperature maps=temp_1,temp_2,temp_3,temp_4 start=2020-01-01 increment="1 days"

.. code-block:: text
    :caption: excluded.txt
    :name: example-data-excluded

    temp_2

    temp_3

All maps of the dataset:

.. code-block:: text
    :name: example-commands-all

    python3 t.example.count.py input=temperature

.. code-block:: text
    :name: example-output-all

    4

The maps from the second to the third day:

.. code-block:: text
    :name: example-commands-range

    python3 t.example.count.py input=temperature start=2020-01-02 end=2020-01-03

.. code-block:: text
    :name: example-output-range

    2

All maps except those of the file, which may have empty lines:

.. code-block:: text
    :name: example-commands-excluded

    python3 t.example.count.py input=temperature exclude=excluded.txt

.. code-block:: text
    :name: example-output-excluded

    2

The shared steps
----------------

Tools that compute a result for each map, or in cycles, or that read a file of
names do the same steps. They are functions in
:mod:`~grass.temporal.tool_steps` and in :mod:`~grass.temporal.datetime_math`, so
that the tools differ only where they have to. Opening the output dataset and
running the modules stay with the tool: the tools differ there, and their
messages are translated per tool.

:func:`~grass.temporal.tool_steps.open_new_map_for`
    Opens the new map that a tool computes from an input map: it is named
    ``<basename>_<suffix>`` in the current mapset and gets the temporal extent
    of the input map. It is not inserted into the temporal database, and the tool
    checks whether a map of that name exists in the GRASS database.

:func:`~grass.temporal.tool_steps.open_result_map`
    The same with the whole name given by the tool; a tool whose naming does not
    follow ``basename`` and ``suffix`` uses it.

:func:`~grass.temporal.tool_steps.maps_to_register`
    Tells beforehand which computed maps
    :func:`~grass.temporal.tool_steps.register_new_maps` would register, so that a
    result without a map leaves no output dataset behind.

:func:`~grass.temporal.tool_steps.register_new_maps`
    Inserts the computed maps into the temporal database and registers them in the
    output dataset, except the empty ones unless the tool keeps them, and
    updates the extent and the metadata of the dataset. It returns the empty maps.

:func:`~grass.temporal.tool_steps.remove_maps`
    Removes maps of the GRASS database with one call of ``g.remove``, for the empty
    maps that ``register_new_maps`` returns.

:func:`~grass.temporal.tool_steps.register_in_new_stds`
    Inserts the output dataset anew, with the temporal type, the semantic type,
    the title and the description of the input dataset, replaces an existing one
    with ``--overwrite``, and registers the maps.

:func:`~grass.temporal.tool_steps.dataset_cycles`
    Yields the start and the end of each cycle of the tools that work in cycles
    (``t.rast.accumulate``, ``t.rast.accdetect``).

:func:`~grass.temporal.tool_steps.first_related_map_id`
    Finds the map of another dataset that a map selects through its temporal
    relations, for the threshold maps of the tools that work in cycles.

:func:`~grass.temporal.tool_steps.mapcalc_name`
    The text that names a map in an ``r.mapcalc`` expression: the plain name for
    a map of the current mapset, ``"name@mapset"`` in double quotes for another
    mapset.

:func:`~grass.temporal.tool_steps.names_from_file`
    The names that a file lists, one per line, without empty lines.

:func:`~grass.temporal.datetime_math.option_to_datetime`
    Converts the value of an option to a ``datetime``.

The helpers do not end the run themselves. A helper that refuses an option or a
state raises ``ValueError`` with the translated text, and the tool calls
``gs.fatal()`` with it, so that the text, the exit and the place of the message stay in
the tool. This is the example of the tool above:

.. literalinclude:: ../../temporal/tool_steps.py
    :caption: The helper that reads a file of names
    :pyobject: names_from_file

``names_from_file``, ``option_to_datetime``, ``open_result_map`` and
``dataset_cycles`` follow this rule. ``open_new_map_for`` is the exception: a
registered map of the same name without ``--overwrite`` ends the run through the
message interface of the library, as ``open_new_map_dataset`` does, whose message and
exit are fixed. The other steps check no option, so they raise no ``ValueError``.

Messages
--------

A message that a user can read is a translatable text, the argument of ``_()``,
with ``str.format()`` for the values: ``gs.fatal(_("Map <{}> not found.").format(name))``.
An f-string is for texts that nobody translates. Named placeholders
(``{name}``) are preferred when a text has more than one value, because a
translator may need to reorder them. Use ``gs.fatal()`` to end the run,
``gs.warning()`` for a result that is right but may surprise, and
``gs.message()`` for information. ``print()`` is for data that a user pipes
elsewhere, never for a message.

A translator works on the text in ``_()``, and a changed text loses the translation.
Two recordings in ``python/grass/temporal/tests/data`` keep the texts:

- ``tool_message_texts.json`` holds the text of every ``_()`` call of the tools in
  ``temporal/t.*/t.*.py``. ``grass_temporal_tool_messages_test.py`` fails for a
  recorded text that is no longer in a tool or in a module of the library. To
  record a new tool, run that file as a script,
  ``python3 python/grass/temporal/tests/grass_temporal_tool_messages_test.py``: it
  writes the texts of all tools and keeps the recorded texts that moved into the
  library. Commit the recording with the tool.
- ``message_ids.json`` holds the texts that the library and the tools had when the
  library was reorganised, and ``grass_temporal_message_ids_test.py`` fails for
  one of them that disappeared. A new tool does not enter it. A text is removed from
  it only on purpose, in the commit that removes the message, and that commit
  says so.

Old texts stay for this reason: a text that a release translated is a text that the
next release keeps, unless a change of behaviour makes it wrong. The texts of the
helpers of the steps above are in the top level modules of the library, which the
first recording covers as well.

The manual
----------

Each tool has a manual, ``<name>.md``, in the Markdown of MkDocs, and ``<name>.html``,
which the build installs for the HTML manual of the installation. The manual is a
test as well: ``temporal/tests`` runs its examples and compares the output.

- **Structure.** ``## DESCRIPTION``, ``## NOTES``, ``## EXAMPLES``, ``## SEE ALSO`` and
  ``## AUTHORS``; ``AGENTS.md`` requires DESCRIPTION, SEE ALSO and AUTHORS. DESCRIPTION says what the tool does and what it is used for,
  links the introduction *temporalintro* and the related tools, and then explains every
  option and flag with its effect, its default and how it works together with
  the others, grouped by purpose and not in the order of the parser. A tool with a
  table as output explains each column. NOTES holds the limits and the traps: an
  empty selection or dataset, a dataset of another mapset, absolute and
  relative time, ``--overwrite``, the region and the mask, and the messages that
  a user can meet, word for word when a test checks them.
- **Examples.** Each task is a ``###`` heading under ``## EXAMPLES`` with three to
  ten examples in the whole manual; every option appears at least once.
  The heading names what the reader wants to do, not the option. An example has
  the two tabs ``=== "Command line"`` (blocks in ``sh``) and
  ``=== "Python (grass.tools)"`` (blocks in ``python``), and each block of code
  is followed by the output that it prints, in a block of the language ``text``.
  The text before the tabs says what the example shows and which values to expect;
  the values are chosen so that a reader can verify them.
- **Both tabs print the same.** Where both show the same thing, they print the
  same text, so ``print(tools.<tool>(...).text)`` in the second tab for the whole
  output of the first. The Python block calls the tool itself, so that the reader
  sees the call with its options.
- **Shown output.** It is inserted by running the example, never typed. What differs
  from run to run (the database path, the user, the creation and modification
  times, the hexadecimal part of the name of a register table) is replaced by fixed
  text before the comparison. An output may not hold a time, a process number, a
  progress bar or the absolute path of the working directory, and no value that
  differs between platforms.
- **Data.** A manual of a tool for the maps of a dataset runs in the North Carolina
  sample dataset, with a comment ``<!-- example-project: dataset=nc_spm_08_grass7
  mapset=<tool_with_underscores> -->`` under ``## EXAMPLES``. The first example
  creates that mapset and sets the region; the examples read only the maps that
  the module ``grass.temporal.testing.nc_dataset`` lists in ``USED_DATA`` and
  copy a map before they change its table, because a test fails when a file of
  the dataset changed. Other manuals run in a project of their own.
- **Control comments.** An HTML comment before a block steers the test and is
  invisible to the reader: ``<!-- example: not-run reason="..." -->``, or
  ``<!-- example: requires=postgresql -->``, ``requires=old-database`` and
  ``requires=gdal:<driver>``, which skip the block where the requirement is
  missing. A catalog of expressions without a Python tab is allowed only for the
  manuals of the algebras and of *t.select* (``CATALOG_MANUALS``).
- **Form.** English, plain ASCII, tools in italics, options and flags in bold,
  values and commands in backticks. A list item has its content indented by four
  spaces per level, as MkDocs reads it. A pair of
  ``<!-- markdownlint-disable MD046 -->`` and ``<!-- markdownlint-enable MD046 -->``
  encloses the examples.
- **The HTML file** is written by ``python3 utils/grass_md2html.py temporal/<name>/<name>.md``
  and never by hand; ``--check`` exits with 1 when it differs from the manual.
  The generator refuses Markdown outside the subset that the manuals use.
- **The acceptance list.** The name of the tool is entered in ``REVIEWED_MANUALS`` in
  ``temporal/tests/temporal_manual_examples_test.py``. From then on the test runs
  the examples of both tabs, checks that the examples show every option of the tool
  (``NOT_SHOWN`` in ``grass.temporal.testing.manual_coverage`` lists the exceptions
  and is empty), and compares ``.md`` and ``.html``. Each tab is one test whose time
  limit grows by five seconds for each block, at least the 300 seconds that the
  configuration of pytest gives every test.

Commit the ``.md`` and the ``.html`` file together.

The tests
---------

The tests of a tool are pytest tests in ``temporal/<name>/tests/``, in files named
``<name_with_underscores>_test.py``, such as ``t_shift_test.py``. They use the fixtures
of ``temporal/conftest.py`` (``tools`` for a project of its own with a one-cell region,
``prefix`` for names that do not collide, ``two_mapsets`` for a tool that crosses
mapsets, ``algebra_setting`` for the tools of the algebra) and the helpers of
``grass.temporal.testing``, which build datasets and read the result back as values.
The conventions that apply to every test of GRASS (the session fixture, ``env``
for ``grass.script``, ``grass.tools``, the layout of the files) are in
``doc/development/testing.md``, which also lists the helpers; they are not repeated
here.

What a tool needs in addition:

- A test for each option and flag, and for every refusal that the tool makes. A
  test of a refusal shows that nothing was written: the tool stops before the first
  map or dataset changes.
- Expected values that are computed by hand and commented, never copied from a
  run. A value that deviates from the expectation is a finding, not a reason to
  adapt the expectation.
- A fixture that builds the dataset in a few lines, as this one does for
  *t.shift*:

.. literalinclude:: ../../../../temporal/t.shift/tests/t_shift_test.py
    :caption: A fixture of the tests of t.shift
    :pyobject: mixed

The manual and the messages are tests as well, as the sections above describe. A tool
is ready when ``python3 -m pytest temporal/tests temporal/<name>/tests`` passes with
and without ``GRASS_TEMPORAL_ALGEBRA=classic``.
