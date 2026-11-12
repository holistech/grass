Temporal Framework
================================

Introduction
------------

The GRASS Temporal Framework implements the temporal GIS functionality of GRASS
and provides an API to implement spatio-temporal processing modules. The framework
introduces space time datasets that represent time series of raster, 3D raster or vector maps.
This framework provides the following functionalities:

- Assign time stamp to maps and register maps in the temporal database
- Modification of time stamps
- Creation, renaming and deletion of space time datasets
- Registration and un-registration of maps in space time datasets
- Query of maps that are registered in space time datasets using SQL where statements
- Analysis of the spatio-temporal topology of space time datasets
- Sampling of space time datasets
- Computation of temporal and spatial relationships between registered maps
- Higher level functions that are shared between modules

Most of the functions described above are member functions of dedicated map layer and space time dataset classes.

The document :download:`The GRASS Temporal Framework: Object oriented code design with examples <Temporal-Framework-Code-Design.pdf>`
(GRASS 8.6) describes the design of the current code with UML figures and
examples that run against the code. This page lists the modules and shows
short examples; the guide :doc:`temporal_framework_tools` shows how to write a
new temporal tool, and the guide :doc:`temporal_framework_algebra` how to extend
the algebra core without changing what valid expressions compute. The
document of the same name that accompanies the 2017 publication of Gebbert and
Pebesma shows the state of 2017 and is linked in the references.

Temporal API
------------

The temporal framework API consists of several dedicated modules. Each module contains one or several classes
as well as function definition. The API can be roughly divided in a low level and high level part. However, several
functions from the low level module are used in module implementation as well.

Low level API
^^^^^^^^^^^^^

The low level API implements the core functionality of the temporal framework. Core functionality is
for example the database interface, the temporal database creation and initialization,
the SQL object serialization, all classes that represent table entries, datetime mathematics and many more.


:mod:`~grass.temporal.state`
""""""""""""""""""""""""""""

    The state of the temporal session and its initialization:

    - Initialization function :func:`~grass.temporal.state.init()`
    - The object that holds the state of the session
    - Several global functions to access TGIS specific variables
    - Interfaces to the TGIS C-library and PyGRASS messenger objects

:mod:`~grass.temporal.db`
"""""""""""""""""""""""""

    The connections to the temporal database:

    - Database interface connection class :class:`~grass.temporal.db.SQLDatabaseInterfaceConnection`
      to sqlite3 and postgresql database backends
    - The context manager :func:`~grass.temporal.db.connection()` that closes
      the connection it opened

:mod:`~grass.temporal.schema`
"""""""""""""""""""""""""""""

    Functions to create, check and upgrade the temporal database.

:mod:`~grass.temporal.core`
"""""""""""""""""""""""""""

    The names of the three modules above under their former module, for
    scripts and addons that use ``tgis.core``.

:mod:`~grass.temporal.rows`
"""""""""""""""""""""""""""

    Implements the SQL conversion of the rows of the temporal database:

    - Definition of the SQL serialize class :class:`~grass.temporal.rows.DictSQLSerializer`
      that converts the content of temporal
      classes into SQL SELECT, INSERT or UPDATE statements
    - Definition of :class:`~grass.temporal.rows.SQLDatabaseInterface`
      that is the base class for all temporal datatype subclasses
    - Definition of :class:`~grass.temporal.rows.Row`, whose subclasses list
      their columns and get the accessors generated

:mod:`~grass.temporal.base`
"""""""""""""""""""""""""""

    Implements basic dataset information:

    - Contains the classes :class:`~grass.temporal.base.BaseRow` and
      :class:`~grass.temporal.base.RegisterRow` for all datasets [#allds]_
      that contain basic information (id, name, mapset, creator, ...)

:mod:`~grass.temporal.spatial_extent`
"""""""""""""""""""""""""""""""""""""

    Implements 2d and 3d spatial extents of all datasets:

    - Implements class :class:`~grass.temporal.spatial_extent.SpatialExtent`
      that is the base class for all dataset specific spatial extent classes
      It provides spatial topological logic and operations for 2D and 3D extents
    - Implements spatial extent classes for all datasets [#allds]_

:mod:`~grass.temporal.temporal_extent`
""""""""""""""""""""""""""""""""""""""

    Implements the temporal extent of all datasets for relative and absolute time:

    - Implements class :class:`~grass.temporal.temporal_extent.TemporalExtent`
      that is the base class for all dataset specific temporal extent classes
      It provides temporal topological logic and operations
    - Implements temporal extent classes for relative time and absolute time for
      all datasets [#allds]_

:mod:`~grass.temporal.metadata`
"""""""""""""""""""""""""""""""

    Implements the metadata of all datasets [#allds]_ in the class :class:`~grass.temporal.metadata.MetadataRow`, which has the columns of the type of the dataset.

:mod:`~grass.temporal.c_libraries_interface`
""""""""""""""""""""""""""""""""""""""""""""

    The RPC C-library interface for exit safe and fast access to raster, vector and 3D raster information.

:mod:`~grass.temporal.temporal_granularity`
"""""""""""""""""""""""""""""""""""""""""""

    The computation of the temporal granularity for a list
    of :class:`~grass.temporal.abstract_dataset.AbstractDataset`
    objects for absolute and relative is implemented here.

:mod:`~grass.temporal.datetime_math`
""""""""""""""""""""""""""""""""""""

    This module contains functions to parse, convert and process datetime objects
    in the temporal framework.

The classic implementation of the spatio-temporal algebra for space time raster,
3D raster and vector datasets, the reference of the algebra core, is the package
:mod:`~grass.temporal.classic`. It stays unchanged because publications cite it:

- :mod:`~grass.temporal.classic.temporal_algebra`, the lexer and parser of the
  temporal expressions, the base of the other parsers
- :mod:`~grass.temporal.classic.temporal_operator`, the lexer and parser of the
  operators in curly braces, such as ``{+,during}``
- :mod:`~grass.temporal.classic.temporal_raster_base_algebra`, what the raster
  and 3D raster algebra share
- :mod:`~grass.temporal.classic.temporal_raster_algebra`, the algebra of space
  time raster datasets
- :mod:`~grass.temporal.classic.temporal_raster3d_algebra`, the algebra of
  space time 3D raster datasets
- :mod:`~grass.temporal.classic.temporal_vector_algebra`, the algebra of space
  time vector datasets
- :mod:`~grass.temporal.classic.granularity`, the granularity of a map list as
  the classic algebra computes it

The package ``grass.temporal.ply`` is an embedded copy of the PLY lexer and
parser generator that the classic algebra builds on. It is not documented here.

High level API
^^^^^^^^^^^^^^

The high level API utilizes the low level API. Its classes and functions are usually used to implement
temporal processing algorithms and temporal GRASS modules.

:mod:`~grass.temporal.abstract_dataset`
"""""""""""""""""""""""""""""""""""""""

    - Implements the base class for all datasets [#allds]_ :class:`~grass.temporal.abstract_dataset.AbstractDataset`.
    - Implements the select, insert and update functionality as well as
      convenient functions to access the base, extent and metadata information

:mod:`~grass.temporal.abstract_map_dataset`
"""""""""""""""""""""""""""""""""""""""""""

    - Implements the base class :class:`~grass.temporal.abstract_map_dataset.AbstractMapDataset`
      for all map layer specific classes
    - Provides the interface to all map layer specific information in the temporal database

:mod:`~grass.temporal.abstract_space_time_dataset`
""""""""""""""""""""""""""""""""""""""""""""""""""

    - Implements the base class :class:`~grass.temporal.abstract_space_time_dataset.AbstractSpaceTimeDataset`
      for all Space Time Datasets classes
    - Contains the creation and deletion functionality, the map registration and un-registration,
      access methods to map layer objects and so on
    - Provides the interface to all Space Time Dataset specific information in the temporal database

:mod:`~grass.temporal.stds_map_register`
""""""""""""""""""""""""""""""""""""""""

    - Implements the class :class:`~grass.temporal.stds_map_register.StdsMapRegister`
      that holds the table of registered maps of a Space Time Dataset: creating, renaming and dropping
      the table, the registration and un-registration of a map, the selection of the registered maps
      and the update of the extent and the metadata of the dataset

:mod:`~grass.temporal.stds_time_edit`
"""""""""""""""""""""""""""""""""""""

    - Shifts and snaps the time of the maps of a Space Time Dataset, in memory
      (:func:`~grass.temporal.stds_time_edit.shift_map_list`,
      :func:`~grass.temporal.stds_time_edit.snap_map_list`) or in the temporal database
      (:func:`~grass.temporal.stds_time_edit.shift`, :func:`~grass.temporal.stds_time_edit.snap`)

:mod:`~grass.temporal.granule_sampling`
"""""""""""""""""""""""""""""""""""""""

    - Splits the maps of a Space Time Dataset into granules of a granularity
      (:func:`~grass.temporal.granule_sampling.registered_maps_by_granularity`,
      :func:`~grass.temporal.granule_sampling.resample_maplist_by_granularity`)

:mod:`~grass.temporal.datasets`
"""""""""""""""""""""""""""""""

    The two generic classes ``MapDataset`` and ``StdsDataset``. They read the
    names of the tables, the prefix of the C interface and the map register
    from the kind of the dataset, so the six classes below only state their
    kind and what is specific to them.

:mod:`~grass.temporal.space_time_datasets`
""""""""""""""""""""""""""""""""""""""""""

    This module contains all classes that represent specific datasets [#allds]_.
    A module developer uses these map layer and Space Time Dataset object
    representations to perform spatio-temporal tasks.

:mod:`~grass.temporal.topology`
"""""""""""""""""""""""""""""""

    The links a dataset keeps to the datasets it is spatially and temporally related to
    (class :class:`~grass.temporal.topology.TopologyLinks`, with the tables of the relations and their inverses)
    and the logic to compute the spatio-temporal topology for a single list or two lists of :class:`~grass.temporal.abstract_dataset.AbstractDataset` objects.
    The class :class:`~grass.temporal.topology.SpatioTemporalTopologyBuilder`
    provides a convenient interface for topology computation.

:mod:`~grass.temporal.gui_support`
""""""""""""""""""""""""""""""""""

    Helper functions to support the listing of space time datasets in the automatically generated GUI.


Shared Module functionality
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Functionality that is shared between different temporal GRASS modules, such as
map listing, space time dataset creation, map registration and un-registration,
aggregation, extraction, map calculation, statistics as well as import and export of
space time datasets.

:mod:`~grass.temporal.aggregation`
""""""""""""""""""""""""""""""""""

    Aggregation of a list of raster maps with *r.series* into one new map that
    is registered in a Space Time Raster Dataset. Used in *t.vect.what.strds*.

:mod:`~grass.temporal.aggregation_core`
"""""""""""""""""""""""""""""""""""""""

    Aggregation of a raster series onto a target series with the algebra core:
    the target is a regular grid of granules or the time stamps of a sampler
    dataset. Used in *t.rast.aggregate* and *t.rast.aggregate.ds*.

:mod:`~grass.temporal.extract`
""""""""""""""""""""""""""""""

    Extraction of subsets from Space Time Datasets including
    map algebra and vector selection statements.
    Used in *t.rast.extract*, *t.rast3d.extract* and *t.vect.extract*.

:mod:`~grass.temporal.kinds`
""""""""""""""""""""""""""""

    The six dataset types (raster, 3D raster, vector maps and their space
    time datasets) with their names, aliases and tables in the temporal
    database. The entry functions below look a type up here.

:mod:`~grass.temporal.factory`
""""""""""""""""""""""""""""""

    Factory functions to create datasets of all types [#allds]_.

:mod:`~grass.temporal.open_stds`
""""""""""""""""""""""""""""""""

    Convenient functions to open existing Space Time Datasets or
    to create new ones. Used in almost all temporal modules.

:mod:`~grass.temporal.list_stds`
""""""""""""""""""""""""""""""""

    Convenient functions to list datasets of all types [#allds]_
    registered in the temporal database.

:mod:`~grass.temporal.batches`
""""""""""""""""""""""""""""""""

    Runs the mapcalc and extraction jobs of the datasets in child processes, a batch at a time.
    Used in the extraction and the map calculation of space time datasets.

:mod:`~grass.temporal.mapcalc`
""""""""""""""""""""""""""""""

    Simple temporal algebra for Space Time Raster and 3d Raster
    datasets. Used in *t.rast.mapcalc* and *t.rast3d.mapcalc*

:mod:`~grass.temporal.register`
"""""""""""""""""""""""""""""""

    Convenient functions to register a single or multiple map layers in the temporal database and
    Space Time Datasets. Used in several modules, most important *t.register*.

:mod:`~grass.temporal.sampling`
"""""""""""""""""""""""""""""""

    Sampling of space time datasets with a sampler space time dataset: for
    each map of the sampler it returns the maps that are related to it.
    Used in *t.vect.observe.strds*.

:mod:`~grass.temporal.related_maps`
"""""""""""""""""""""""""""""""""""

    The sampling of the maps by granules with the rules of the classic
    algebra, on the algebra core. Used in :mod:`~grass.temporal.mapcalc` and
    *t.sample*.

:mod:`~grass.temporal.series_limits`
""""""""""""""""""""""""""""""""""""

    The number of files that *r.series* has to open, counted before it runs,
    to decide whether its flag ``-z`` is needed. Used in the aggregation and
    in the reductions of the algebra core.

:mod:`~grass.temporal.tool_steps`
"""""""""""""""""""""""""""""""""

    Steps that several tools share: opening the new map for each input map,
    registering the computed maps, removing empty maps, and walking the cycles
    of *t.rast.accumulate* and *t.rast.accdetect*.

:mod:`~grass.temporal.stds_export`
""""""""""""""""""""""""""""""""""

    Functions to export Space Time Datasets, used in *t.rast.export* and *t.vect.export*.

:mod:`~grass.temporal.stds_import`
""""""""""""""""""""""""""""""""""

    Functions to import Space Time Datasets, used in *t.rast.import* and *t.vect.import*.

:mod:`~grass.temporal.univar_statistics`
""""""""""""""""""""""""""""""""""""""""

    Simple statistical analysis functions for Space Time Datasets, used in *t.rast.univar*, *t.rast3d.univar*
    and *t.vect.univar*.


.. [#allds] Raster Map Layer, 3d Raster Map Layer, Vector Map Layer, Space time Raster Datasets (STRDS),
              Space Time 3d Raster Datasets (STR3DS) and Space Time Vector Datasets (STVDS)


Here the full list of all temporal modules:

.. toctree::
   :maxdepth: 2

   grass.temporal


Guides
------

Each guide has a complete example that runs in the documentation tests of the
repository:

.. toctree::
   :maxdepth: 1

   temporal_framework_tools
   temporal_framework_algebra


Examples
--------

Each example runs on its own in a new project in the documentation tests of
the repository. The text before an example names what it needs: the first one
needs a temporal database without the dataset it creates, the next two need
the space time raster dataset ``test@PERMANENT`` with registered maps, and the
dataset names of the algebra example are named there. The tests create
``test``, ``A`` and ``B``, each with three registered maps, before every example
except the first.

Creation of a space time dataset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example shows how to create a space time dataset. The code is generic and works
for different space time datasets (raster, 3D raster and vector):

.. code-block:: python

    # Let us import the temporal framework and
    # the script framework
    import grass.temporal as tgis
    import grass.script as gs

    # The id of the new space time dataset
    stds_id = "test@PERMANENT"
    # The title of the new space time dataset
    title = "This is a test dataset"
    # The description of the space time dataset
    description = "The description"
    # The type of the space time dataset (strds, str3ds or stvds)
    stds_type = "strds"
    # The temporal type of the space time dataset (absolute or relative)
    temporal_type = "absolute"
    # Whether an existing dataset of this id may be replaced
    overwrite = False

    # Make sure the temporal database exists
    # and set the temporal GIS environment
    tgis.init()

    # We use the dataset factory to create a new space time dataset instance of a specific type
    stds = tgis.dataset_factory(stds_type, stds_id)

    # We need a database connection to insert the content of the space time dataset
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    # First we check if the dataset is already in the database
    if stds.is_in_db(dbif=dbif) and not overwrite:
        dbif.close()
        gs.fatal(
            "Space time {} dataset <{}> is already in the database. "
            "Use the overwrite flag.".format(
                stds.get_new_map_instance(None).get_type(), stds_id
            )
        )

    # We delete the existing dataset and create a new one in case we are allowed to overwrite it
    if stds.is_in_db(dbif=dbif) and overwrite:
        gs.warning(
            "Overwrite space time {} dataset <{}> and unregister all maps.".format(
                stds.get_new_map_instance(None).get_type(), stds_id
            )
        )
        stds.delete(dbif=dbif)
        stds = stds.get_new_instance(stds_id)

    # We set the initial values. This function also creates the command history.
    stds.set_initial_values(
        temporal_type=temporal_type,
        semantic_type="mean",
        title=title,
        description=description,
    )

    # Now we can insert the new space time dataset in the database
    stds.insert(dbif=dbif)

    # Close the database connection
    dbif.close()


Howto start example
^^^^^^^^^^^^^^^^^^^

This simple example shows how to open a space time raster dataset
to access its registered maps. It needs a space time raster dataset
``test@PERMANENT`` in the temporal database, such as the one the previous
example creates, with maps registered by *t.register*.

.. code-block:: python

    # Let us import the temporal framework and
    # the script framework
    import grass.temporal as tgis
    import grass.script as gs

    # Make sure the temporal database exists
    # and set the temporal GIS environment
    tgis.init()

    # We create the temporal database interface for fast processing
    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    # The id of a space time raster dataset is built from its name and its mapset
    stds_id = "test@PERMANENT"

    # We create a space time raster dataset object
    strds = tgis.SpaceTimeRasterDataset(stds_id)

    # Check if the space time raster dataset is in the temporal database
    if strds.is_in_db(dbif=dbif) is False:
        dbif.close()
        gs.fatal(
            "Space time {} dataset <{}> not found".format(
                strds.get_new_map_instance(None).get_type(), stds_id
            )
        )

    # Fill the object with the content from the temporal database
    strds.select(dbif=dbif)

    # Print information about the space time raster dataset to stdout
    strds.print_info()

    # Get all maps that are registered in the strds and print
    # information about the maps to stdout
    maps = strds.get_registered_maps_as_objects(dbif=dbif)

    # We iterate over the temporal sorted map list
    for raster_map in maps:
        # We fill the map object with the content
        # from the temporal database. We use the existing
        # database connection, otherwise a new connection
        # will be established for each map object
        # which slows the processing down
        raster_map.select(dbif=dbif)
        raster_map.print_info()

    # Close the database connection
    dbif.close()


Snapping the time stamps
^^^^^^^^^^^^^^^^^^^^^^^^

This example snaps the time stamps of the maps of ``test@PERMANENT`` in the
temporal database so that the end of a map is the start of the next one.
Like the previous example it needs the dataset to exist.

.. code-block:: python

    import grass.script as gs
    import grass.temporal as tgis

    stds_id = "test@PERMANENT"
    stds_type = "strds"

    # Make sure the temporal database exists
    tgis.init()

    dbif = tgis.SQLDatabaseInterfaceConnection()
    dbif.connect()

    stds = tgis.dataset_factory(stds_type, stds_id)

    if stds.is_in_db(dbif) is False:
        dbif.close()
        gs.fatal(
            "Space time dataset <{}> not found in temporal database".format(stds_id)
        )

    stds.select(dbif=dbif)

    stds.snap(dbif=dbif)

    stds.update_command_string(dbif=dbif)
    dbif.close()


Algebra core
------------

The package :mod:`~grass.temporal.algebra` offers the operations of the
temporal algebra as Python functions on series of maps: ``source``,
``source_map``, ``select``, ``pairs``, ``gather``, ``apply``, ``choose``,
``where``, ``merge``, ``cell_offset``, ``buffer``, ``lift``, ``retime``,
``neighbour``, ``timevar``, ``granules``, ``plan`` and ``materialize``.
Every decision that the algebra syntax takes implicitly is an explicit
parameter, with a documented default where one is sensible; how several
related maps are combined must always be named (``reduce`` of ``gather``).
Raster, 3D raster and vector maps are supported; see the docstring of the
package for an example.
``source``, ``source_map`` and ``materialize`` need a GRASS session with an
initialised temporal database (``tgis.init()``); ``plan`` needs one only when
a result map has the name of a map that the series reads, to look up the
current mapset; the other functions need none.

The modules of the package:

- :mod:`~grass.temporal.algebra.series`: the series of slots, the values of
  the algebra, with the extent and the space of a slot
- :mod:`~grass.temporal.algebra.content`: the content of a slot as an
  immutable expression tree
- :mod:`~grass.temporal.algebra.maptypes`: what the core needs to know about
  a map type
- :mod:`~grass.temporal.algebra.adapters`: the map objects that stand for
  the slots of a series
- :mod:`~grass.temporal.algebra.sources`: reading space time datasets and
  single maps as series
- :mod:`~grass.temporal.algebra.relations`: the temporal and spatial relations
  between the slots of two series
- :mod:`~grass.temporal.algebra.operations`: the operations, pure functions
  on series
- :mod:`~grass.temporal.algebra.reducers`: how ``gather`` combines the related
  slots of a target slot
- :mod:`~grass.temporal.algebra.time_functions`: operations on the time
  stamps of a series
- :mod:`~grass.temporal.algebra.backends`: the turning of the content of a
  slot into module calls
- :mod:`~grass.temporal.algebra.materialize`: planning a series as module
  calls and map names, and running the plan with registration of the maps

The syntax of :program:`t.rast.algebra` is translated onto these functions
by :func:`grass.temporal.algebra.parser.evaluate`, which also gives the
process chain of a dry run. The package
:mod:`~grass.temporal.algebra.parser` holds the syntax:

- :mod:`~grass.temporal.algebra.parser.lexer`,
  :mod:`~grass.temporal.algebra.parser.grammar` and
  :mod:`~grass.temporal.algebra.parser.operators`: the tokens, the grammar
  and the operators in braces such as ``{+,during}``
- :mod:`~grass.temporal.algebra.parser.ast`: the nodes of the syntax tree
- :mod:`~grass.temporal.algebra.parser.translate` and
  :mod:`~grass.temporal.algebra.parser.shared`: the translation of the tree
  onto the core operations and what the translators share
- :mod:`~grass.temporal.algebra.parser.granularity`: the sampling of space
  time datasets with a common granularity
- :mod:`~grass.temporal.algebra.parser.facade`: the public parser classes

The example evaluates an expression as a dry run. It needs a session, an
initialised temporal database (``tgis.init()``) and the space time datasets
``A`` and ``B`` that the expression names; without them ``evaluate`` raises
an error:

.. code-block:: python

    import grass.temporal as tgis
    from grass.temporal.algebra.parser import evaluate

    tgis.init()
    chain = evaluate("C = A {+,during} B", dry_run=True)
    print(chain)


Testing package
---------------

The package :mod:`~grass.temporal.testing` holds the helpers of the tests of
the library and of the tools. It is part of the installed package so that the
tests of the tools can use it; code outside the tests does not need it. It
does not import pytest at module level; only :mod:`~grass.temporal.testing.postgresql`
imports it inside the function that skips a test. Its modules:

- :mod:`~grass.temporal.testing.session`: creating and tearing down the GRASS
  sessions of the tests
- :mod:`~grass.temporal.testing.data`: building dates, maps and space time
  datasets as input
- :mod:`~grass.temporal.testing.readback`: reading registered maps and
  *t.info* output back for comparison
- :mod:`~grass.temporal.testing.io_cache`: caches of two slow calls that give
  the same answer in a test
- :mod:`~grass.temporal.testing.postgresql`: running tests against a
  PostgreSQL server and comparing the backends
- :mod:`~grass.temporal.testing.versions`: turning a current temporal
  database into one of an older version
- :mod:`~grass.temporal.testing.database_image`: the image of the temporal
  database, what the library writes and reads back
- :mod:`~grass.temporal.testing.recordings`: recorded results of the extent,
  granularity, date and topology functions
- :mod:`~grass.temporal.testing.contract_trace`: tracing which public
  functions an example script calls
- :mod:`~grass.temporal.testing.nc_dataset`: finding the North Carolina
  sample dataset and seeing whether a run changed it
- :mod:`~grass.temporal.testing.manual_examples` and
  :mod:`~grass.temporal.testing.manual_coverage`: reading the examples of a
  manual, running them, and checking that a manual shows every option
- :mod:`~grass.temporal.testing.outcomes`: running an expression on the
  algebra core and describing the maps it made
- :mod:`~grass.temporal.testing.algebra_cases`: algebra cases with expected
  values derived by hand
- :mod:`~grass.temporal.testing.expressions_data`: the datasets that the
  algebra tests run expressions on

The testing guide ``doc/development/testing.md`` of the repository describes
how the tests use them.


References
----------

* Gebbert, S., Pebesma, E., 2014. *A temporal GIS for field based environmental modeling*.
  Environmental Modelling & Software, 53, 1-12.
  `doi:10.1016/j.envsoft.2013.11.001 <https://doi.org/10.1016/j.envsoft.2013.11.001>`_
* Gebbert, S., Pebesma, E., 2017. *The GRASS GIS temporal framework*.
  International Journal of Geographical Information Science, 31(7), 1273-1292.
  `doi:10.1080/13658816.2017.1306862 <https://doi.org/10.1080/13658816.2017.1306862>`_
* `TGRASS related articles in the GRASS Wiki <https://grasswiki.osgeo.org/wiki/Temporal_data_processing>`_
* :download:`The GRASS Temporal Framework: Object oriented code design with examples <Temporal-Framework-Code-Design.pdf>`:
  the current description of the code (GRASS 8.6)
* Supplementary material of Gebbert and Pebesma (2017), as published and
  showing the state of the code in 2017:
  :download:`The GRASS GIS Temporal Framework: Object oriented code design with examples <Temporal-Framework-API-Description.pdf>`

:Authors: Soeren Gebbert
