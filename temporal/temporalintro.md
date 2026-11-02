---
description: Temporal data processing in GRASS
index: temporal
---

# Temporal data processing in GRASS

The temporal framework of GRASS manages time series of maps. It adds three
types of datasets for them, the *space time datasets*:

- *Space time raster datasets* (strds) hold raster map time series. The
  tools that process strds have the name prefix *t.rast*.
- *Space time 3D raster datasets* (str3ds) hold 3D raster map time series.
  The tools that process str3ds have the name prefix *t.rast3d*.
- *Space time vector datasets* (stvds) hold vector map time series. The
  tools that process stvds have the name prefix *t.vect*.

A space time dataset is a named collection of maps of one type. It does not
contain the maps; it lists them, together with the time of each map and the
extent and the range of values that the framework has read from the map. The
tools of the framework, the temporal tools, create, change, analyze and
process these datasets. The short example at the end of this page runs the
main steps with generated data.

## Concepts

### Time of maps

Every map of a space time dataset has a time. The *temporal type* of the
dataset is either *absolute* or *relative*:

- With absolute time, the time of a map is a date and time, such as
  `2026-03-01 00:00:00`.
- With relative time, the time of a map is a number of time units counted from
  an arbitrary start, such as model step 3. The unit is `years`, `months`,
  `days`, `hours`, `minutes` or `seconds` and is the same for all maps of a
  dataset.

A dataset holds maps of its own temporal type only. A map has either a *time
instant*, a start time without an end time, or a *time interval*, from a start
time to an end time. A dataset can hold both. Absolute and relative time are
set with *[t.create](t.create.md)* and *[t.register](t.register.md)*: the
option **temporaltype** of *t.create* chooses the type of the dataset, and
*t.register* gives the maps their times and, with relative time, the unit.

### Granularity

The granularity of a dataset is the step in which its time can be counted:
`1 day` for daily maps that follow each other without a gap. For maps of
different lengths or with gaps between them, it is the greatest common divisor
of the lengths and gaps. With relative time it is a number of the unit.
*[t.info](t.info.md)* and *[t.topology](t.topology.md)* print it. A dataset
with a single map that is a time instant has no granularity.

The granularity of a space-time dataset counts months and years only if
the start and the end of every interval lie on the first day of a month.
A monthly series that starts on another day, for example on January 31
with intervals of 28, 31 and 30 days, has the granularity `1 day`; the
same series from January 1 has the granularity `1 month`. Tools that work
on the granularity (for example *t.rast.to.rast3* or the **-g** flag of
the algebra tools) then use days.

Tools that cut a dataset into time steps, *t.rast.aggregate* with its option
**granularity** and the method `gran` of *[t.rast.list](t.rast.list.md)* with
its option **granule**, use such a step as a *granule*. Their manuals say how
the first granule is placed and how months are counted.

### Temporal topology

The temporal topology of a dataset describes how its maps lie in time to each
other. *[t.topology](t.topology.md)* reports it. The topology is *valid* if no
two maps are equal, overlap, or lie in each other. Maps that touch, where the
end of one map is the start of the next, and maps with a gap between them are
allowed, as are time instants. A *gap* lies between two neighbouring maps
where the later one starts after the earlier one has ended.
*[t.snap](t.snap.md)* closes gaps, and *[t.rast.gapfill](t.rast.gapfill.md)*
fills them with interpolated maps.

The temporal relations between two time intervals A and B are `equal`,
`during` and `contains`, `starts` and `started`, `finishes` and `finished`,
`precedes` and `follows`, `overlaps` and `overlapped`. The manual of
*[t.rast.algebra](t.rast.algebra.md)* draws them and states which relation
includes which, and the manual of *t.topology* counts them for a dataset.

### Sampling

Sampling relates the maps of one dataset to the maps of another dataset, the
*sampler*. Each map of the sampler is a granule of time; for each granule, the
sampling finds the maps of the other dataset that are in a chosen temporal
relation to it, such as `during`, `contain`, `overlap` or `equal`.
*[t.sample](t.sample.md)* prints the result. The tools that combine several
datasets use the same idea, among them
*[t.rast.mapcalc](t.rast.mapcalc.md)*,
*[t.rast3d.mapcalc](t.rast3d.mapcalc.md)* and
*[t.rast.aggregate.ds](t.rast.aggregate.ds.md)*; the manual of
*t.rast3d.mapcalc* explains how the tool picks one map when more than one
map is related to a granule.

### Semantic labels

A raster map can carry a semantic label that names its role, such as the band
`S2_B4` of a satellite scene (set with *[r.support](r.support.md)*). Maps of
different labels may share the same time. With
*[t.rast.list](t.rast.list.md)*, *[t.rast.univar](t.rast.univar.md)* and
*[t.rast.aggregate](t.rast.aggregate.md)*, `input=name.label` selects the maps
of one label from the dataset `name`. Therefore the name of a new space time
dataset must not contain a dot. *t.info* prints the
labels of a dataset.

The *semantic type* of a dataset, set with the option **semantictype** of
*t.create*, is a different thing: it states whether the values are amounts
(`sum`), means (`mean`, the default), minima or maxima.

### Temporal algebra

The temporal algebra applies operations to whole datasets. An expression
such as `C = A + B` relates the maps of the datasets by their temporal
relations and registers the results in a new dataset. The tools are
*[t.rast.algebra](t.rast.algebra.md)*,
*[t.rast3d.algebra](t.rast3d.algebra.md)*,
*[t.vect.algebra](t.vect.algebra.md)* and *[t.select](t.select.md)*, which
selects maps without computing.

Since GRASS 8.6, the algebra computes with a new implementation. The previous
algebra stays available as the *classic algebra* because published results
rely on it: the flag **-c** of the algebra tools selects it for one call, and
the environment variable `GRASS_TEMPORAL_ALGEBRA=classic` for a whole session
or script. The manual of *t.rast.algebra* lists where the two differ.

## Temporal data management in general

Space time datasets are stored in a temporal database. A core principle
of the temporal framework is that temporal databases are mapset
specific. A new temporal database is created when a temporal command is
invoked in a mapset that does not contain any temporal databases yet.
For example, when a mapset was recently created.

A space time dataset belongs to the mapset in which it was created, and a
new dataset is always created in the current mapset. Maps of other mapsets
can be registered in a dataset of the current mapset, but the dataset itself
has to belong to the current mapset.

Registering a map in a space time dataset changes the metadata of the map,
for instance its time stamp. This matters if the user has no write access to
the maps from other mapsets. If a registered map is removed from the spatial
database in another way than with the temporal tools, the temporal database
still lists it until [t.support](t.support.md) with the flag **-m** reads the
maps again and drops the maps that are gone.

SQLite3 or PostgreSQL are supported as temporal database backends.
Temporal databases stored in other mapsets can be accessed as long as
those other mapsets are in the user's current mapset search path
(managed with [g.mapsets](g.mapsets.md)). Datasets of other mapsets can
be read with `name@mapset`, but a tool that changes a dataset, such as
*t.register*, *t.rename* or *t.create*, works on the current mapset only.
*t.remove* stops with an error for a dataset of another mapset. For a
dataset of the current mapset, the flag **-d** deletes only its maps of the
current mapset and warns for each map of another mapset.

Connection settings are performed with [t.connect](t.connect.md). By
default, a SQLite3 database is created in the current mapset to store
all space-time datasets and registered time series maps in that mapset.
[t.upgrade](t.upgrade.md) brings the temporal database of a mapset to the
version of the installed GRASS.

New space-time datasets are created in the temporal database with
[t.create](t.create.md). The name of the new dataset, the type (strds,
str3ds, stvds), the title and the description must be provided for
creation. Optionally, the temporal type (absolute, relative) and the
semantic information can be provided.

The module [t.register](t.register.md) is designed to register raster,
3D raster and vector maps in the temporal database and in the space-time
datasets. It supports different input options. Maps to register can be
provided as a comma separated string at the command line, or in an input
file. The module supports the definition of time stamps (time instances
or intervals) for each map in the input file. With
[t.unregister](t.unregister.md) maps can be unregistered from space-time
datasets and from the temporal database.

**Important**  
*Use only temporal commands like [t.register](t.register.md) to attach a
time stamp to raster, 3D raster and vector maps. The commands
r.timestamp, r3.timestamp and v.timestamp should not be used because
they only modify the metadata of the map in the spatial database, but
they do not register maps in the temporal database. However, maps with
timestamps attached by means of \*.timestamp modules can be registered
in space-time datasets using the existing timestamp.*

The module [t.remove](t.remove.md) will remove the space-time datasets
from the temporal database and optionally all registered maps. It will
take care of multiple map registration, hence if maps are registered in
several space-time datasets in the current mapset. Use
[t.support](t.support.md) to modify the metadata of space time datasets
or to update the metadata that is derived from registered maps. This
module also checks for removed and modified maps and updates the
space-time datasets accordingly. Rename a space-time dataset with
[t.rename](t.rename.md). [t.copy](t.copy.md) copies a dataset,
[t.merge](t.merge.md) registers the maps of several datasets in one, and
[t.shift](t.shift.md) and [t.snap](t.snap.md) change the times of the maps.

To print information about space-time datasets or registered maps, the
module [t.info](t.info.md) can be used. [t.list](t.list.md) will list
all space-time datasets and registered maps in the temporal database.

The module [t.topology](t.topology.md) was designed to compute and check
the temporal topology of space-time datasets. Moreover, the module
[t.sample](t.sample.md) samples input space-time dataset(s) with a
sample space-time dataset and prints the result to standard output.
Different sampling methods are supported and can be combined.

List of general management modules:

- [t.connect](t.connect.md)
- [t.copy](t.copy.md)
- [t.create](t.create.md)
- [t.info](t.info.md)
- [t.list](t.list.md)
- [t.merge](t.merge.md)
- [t.register](t.register.md)
- [t.remove](t.remove.md)
- [t.rename](t.rename.md)
- [t.sample](t.sample.md)
- [t.shift](t.shift.md)
- [t.snap](t.snap.md)
- [t.support](t.support.md)
- [t.topology](t.topology.md)
- [t.unregister](t.unregister.md)
- [t.upgrade](t.upgrade.md)

## Modules to visualize space-time datasets and temporal data

- [g.gui.animation](g.gui.animation.md)
- [g.gui.timeline](g.gui.timeline.md)
- [g.gui.mapswipe](g.gui.mapswipe.md)
- [g.gui.tplot](g.gui.tplot.md)

## Modules to process space-time raster datasets

The focus of the temporal GIS framework is the processing and analysis
of raster time series. Hence, the majority of the temporal modules are
designed to process space-time raster datasets (strds). However, there
are several modules to process space-time 3D raster datasets and
space-time vector datasets as well.

### Querying and map calculation

Maps registered in a space-time raster dataset can be listed using
[t.rast.list](t.rast.list.md). This module supports several methods to
list maps and uses SQL queries to determine how these maps are selected
and sorted. Subsets of space-time raster datasets can be extracted with
[t.rast.extract](t.rast.extract.md) that allows performing additional
mapcalc operations on the selected raster maps.

Several modules in the temporal framework have a *where* option. This
option allows performing different selections of maps registered in the
temporal database and in space-time datasets. The columns that can be
used to perform these selections are: *id, name, creator, mapset,
temporal_type, creation_time, start_time, end_time, north, south, west,
east, nsres, ewres, cols, rows, number_of_cells, min and max*. Note that
for vector time series, i.e. stvds, some of the columns that can be
queried to list/select vector maps differ from those for space-time
raster datasets (check with `t.vect.list --help`).

- [t.rast.extract](t.rast.extract.md)
- [t.rast.gapfill](t.rast.gapfill.md)
- [t.rast.mapcalc](t.rast.mapcalc.md)
- [t.rast.algebra](t.rast.algebra.md)
- [t.rast.colors](t.rast.colors.md)
- [t.rast.neighbors](t.rast.neighbors.md)
- [t.rast.contour](t.rast.contour.md)
- [t.rast.what](t.rast.what.md)

Similar to the *where* option, selected modules like
[t.rast.univar](t.rast.univar.md) support a *region_relation* option to
limit computations to maps of the space time raster dataset that have a
given spatial relation to the current computational region. Supported
spatial relations are:

- "overlaps": process only maps that spatially overlap ("intersect")
  with the current computational region
- "is_contained": process only maps that are fully within the current
  computational region
- "contains": process only maps that contain (fully cover) the current
  computational region

Space time raster datasets may contain raster maps with varying spatial
extent like for example series of scenes of satellite images. For such
cases the *region_relation* option can be useful.

Moreover, there is [v.what.strds](v.what.strds.md), that uploads
space-time raster dataset values at positions of vector points, to the
attribute table of the vector map. [t.rast.what](t.rast.what.md) samples
the maps of a dataset at point locations and prints the values.

### Aggregation and accumulation analysis

The temporal framework supports the aggregation of space-time raster
datasets. It provides three modules to perform aggregation using
different approaches. To aggregate a space-time raster dataset using a
temporal granularity like 4 months, 7 days and so on, use
[t.rast.aggregate](t.rast.aggregate.md). The module
[t.rast.aggregate.ds](t.rast.aggregate.ds.md) allows aggregating a
space-time raster dataset using the time intervals of the maps of
another space-time dataset (raster, 3D raster and vector). A simple
interface to [r.series](r.series.md) is the module
[t.rast.series](t.rast.series.md) that processes the whole input
space-time raster dataset or a subset of it.

- [t.rast.aggregate](t.rast.aggregate.md)
- [t.rast.aggregate.ds](t.rast.aggregate.ds.md)
- [t.rast.series](t.rast.series.md)
- [t.rast.accumulate](t.rast.accumulate.md)
- [t.rast.accdetect](t.rast.accdetect.md)

### Export/import conversion

Space-time raster datasets can be exported with
[t.rast.export](t.rast.export.md) as a compressed tar archive. Such
archives can be then imported using [t.rast.import](t.rast.import.md).

The module [t.rast.to.rast3](t.rast.to.rast3.md) converts space-time
raster datasets into space-time voxel cubes. All 3D raster modules can
be used to process such voxel cubes. This conversion allows the export
of space-time raster datasets as netCDF files that include time as one
dimension. [t.rast.to.vect](t.rast.to.vect.md) converts each map of a
dataset into a vector map and registers them in a space time vector dataset.

- [t.rast.export](t.rast.export.md)
- [t.rast.import](t.rast.import.md)
- [t.rast.out.vtk](t.rast.out.vtk.md)
- [t.rast.to.rast3](t.rast.to.rast3.md)
- [t.rast.to.vect](t.rast.to.vect.md)
- [r3.out.netcdf](r3.out.netcdf.md)

### Statistics and gap filling

- [t.rast.univar](t.rast.univar.md)
- [t.rast.gapfill](t.rast.gapfill.md)

## Modules to manage, process and analyze STR3DS and STVDS

Several space-time vector dataset modules were developed to allow the
handling of vector time series data.

- [t.vect.algebra](t.vect.algebra.md)
- [t.vect.db.select](t.vect.db.select.md)
- [t.vect.export](t.vect.export.md)
- [t.vect.extract](t.vect.extract.md)
- [t.vect.import](t.vect.import.md)
- [t.vect.list](t.vect.list.md)
- [t.vect.observe.strds](t.vect.observe.strds.md)
- [t.vect.univar](t.vect.univar.md)
- [t.vect.what.strds](t.vect.what.strds.md)

The space-time 3D raster dataset modules are doing exactly the same as
their raster pendants, but with 3D raster map layers:

- [t.rast3d.algebra](t.rast3d.algebra.md)
- [t.rast3d.list](t.rast3d.list.md)
- [t.rast3d.extract](t.rast3d.extract.md)
- [t.rast3d.mapcalc](t.rast3d.mapcalc.md)
- [t.rast3d.univar](t.rast3d.univar.md)

[t.select](t.select.md) selects maps of datasets of all three types
without computing.

## EXAMPLES

The examples use one small dataset of four daily air temperature maps that
they build step by step. The region has 2 by 3 cells, and the map
`temperature_n` has the value `column + 3 * (n - 1)` in each cell, so that the
values of the four maps are 1 to 3, 4 to 6, 7 to 9 and 10 to 12. Each example
uses the result of the previous one.

<!-- markdownlint-disable MD046 -->

### Create a dataset and register maps

*[t.create](t.create.md)* creates the empty dataset `temperature` and
*[t.register](t.register.md)* registers the four maps in it. With the flag
**-i** and the options **start** and **increment**, the maps become
consecutive intervals of one day, the first starting on 1 March 2026. The
commands print nothing.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for i in 1 2 3 4; do
        r.mapcalc expression="temperature_$i = col() + 3 * ($i - 1)"
    done
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3,temperature_4 \
        start=2026-03-01 increment="1 day"
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for step in range(4):
        tools.r_mapcalc(expression=f"temperature_{step + 1} = col() + {3 * step}")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3,temperature_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    ```

### Look at the dataset and its time

*[t.info](t.info.md)* with the flag **-g** prints the properties of the dataset.
The four maps cover 1 to 5 March, and the granularity is one day.
*[t.topology](t.topology.md)* shows that the topology is valid: the maps touch
without gaps, so there are three `Follows` and three `Precedes` pairs.
*[t.rast.list](t.rast.list.md)* lists the maps with their times and the
minimum and maximum of their values.

=== "Command line"

    ```sh
    t.info -g input=temperature | grep -E "^(start_time|end_time|granularity|number_of_maps)="
    t.topology input=temperature
    t.rast.list input=temperature columns=name,start_time,end_time,min,max
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    granularity='1 day'
    number_of_maps=4
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature@PERMANENT
     | Name: ...................... temperature
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 3
     | Precedes: .................. 3
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    name|start_time|end_time|min|max
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|3.0
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|6.0
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00|7.0|9.0
    temperature_4|2026-03-04 00:00:00|2026-03-05 00:00:00|10.0|12.0
    ```

=== "Python (grass.tools)"

    ```python
    info = tools.t_info(input="temperature", flags="g").keyval
    for key in ("start_time", "end_time", "granularity", "number_of_maps"):
        print(f"{key}={info[key]}")
    print(tools.t_topology(input="temperature").stdout, end="")
    print(
        tools.t_rast_list(
            input="temperature", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    granularity='1 day'
    number_of_maps=4
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature@PERMANENT
     | Name: ...................... temperature
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 3
     | Precedes: .................. 3
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    name|start_time|end_time|min|max
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00|1.0|3.0
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00|4.0|6.0
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00|7.0|9.0
    temperature_4|2026-03-04 00:00:00|2026-03-05 00:00:00|10.0|12.0
    ```

### Aggregate over a longer period

*[t.rast.aggregate](t.rast.aggregate.md)* cuts the time into granules of two
days and averages the maps of each granule. The two new maps cover 1 to 3 March
and 3 to 5 March. Here the input maps differ from each other by a constant, so the
minimum and the maximum of a new map are the means of the minima and of the
maxima of its input maps: for the first, (1 + 4) / 2 = 2.5 and (3 + 6) / 2 =
4.5.

=== "Command line"

    ```sh
    t.rast.aggregate input=temperature output=two_days basename=two_days \
        granularity="2 days" method=average
    t.rast.list input=two_days columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    two_days_2026_03_01|2026-03-01 00:00:00|2026-03-03 00:00:00|2.5|4.5
    two_days_2026_03_03|2026-03-03 00:00:00|2026-03-05 00:00:00|8.5|10.5
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_aggregate(
        input="temperature",
        output="two_days",
        basename="two_days",
        granularity="2 days",
        method="average",
    )
    print(
        tools.t_rast_list(input="two_days", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    two_days_2026_03_01|2026-03-01 00:00:00|2026-03-03 00:00:00|2.5|4.5
    two_days_2026_03_03|2026-03-03 00:00:00|2026-03-05 00:00:00|8.5|10.5
    ```

### Sample one dataset by another

*[t.sample](t.sample.md)* takes `two_days` as the sampler and prints, for each
of its maps, the maps of `temperature` in the default relations `during`,
`overlap`, `contain` and `equal`. Each daily map lies in one granule of two
days, so each row names two maps. The columns are the sampler map, the related
maps of `temperature`, the start and end of the granule, its length in days and
the distance of its start from the first granule in days (the manual of
*t.sample* describes them).

=== "Command line"

    ```sh
    t.sample inputs=temperature sample=two_days
    ```

    ```text
    two_days_2026_03_01@PERMANENT|temperature_1@PERMANENT,temperature_2@PERMANENT|2026-03-01 00:00:00|2026-03-03 00:00:00|2.0|0.0
    two_days_2026_03_03@PERMANENT|temperature_3@PERMANENT,temperature_4@PERMANENT|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_sample(inputs="temperature", sample="two_days").text)
    ```

    ```text
    two_days_2026_03_01@PERMANENT|temperature_1@PERMANENT,temperature_2@PERMANENT|2026-03-01 00:00:00|2026-03-03 00:00:00|2.0|0.0
    two_days_2026_03_03@PERMANENT|temperature_3@PERMANENT,temperature_4@PERMANENT|2026-03-03 00:00:00|2026-03-05 00:00:00|2.0|2.0
    ```

### Compute with the temporal algebra

*[t.rast.algebra](t.rast.algebra.md)* adds 10 to every map of `temperature`
and registers the results in the new dataset `warm`, which keeps the times of
the input maps. The minima and maxima are those of the input plus 10. The flag
**-c** selects the classic algebra: the second call computes the same
expression with it into `warm_classic`, and the list shows the same values and
times. The names of the maps differ only in the basename.

=== "Command line"

    ```sh
    t.rast.algebra expression="warm = temperature + 10" basename=warm
    t.rast.list input=warm columns=name,start_time,min,max
    t.rast.algebra -c expression="warm_classic = temperature + 10" \
        basename=classic
    t.rast.list input=warm_classic columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_0|2026-03-01 00:00:00|11.0|13.0
    warm_1|2026-03-02 00:00:00|14.0|16.0
    warm_2|2026-03-03 00:00:00|17.0|19.0
    warm_3|2026-03-04 00:00:00|20.0|22.0
    name|start_time|min|max
    classic_0|2026-03-01 00:00:00|11.0|13.0
    classic_1|2026-03-02 00:00:00|14.0|16.0
    classic_2|2026-03-03 00:00:00|17.0|19.0
    classic_3|2026-03-04 00:00:00|20.0|22.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_algebra(expression="warm = temperature + 10", basename="warm")
    print(tools.t_rast_list(input="warm", columns="name,start_time,min,max").text)
    tools.t_rast_algebra(
        expression="warm_classic = temperature + 10", basename="classic", flags="c"
    )
    print(tools.t_rast_list(input="warm_classic", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_0|2026-03-01 00:00:00|11.0|13.0
    warm_1|2026-03-02 00:00:00|14.0|16.0
    warm_2|2026-03-03 00:00:00|17.0|19.0
    warm_3|2026-03-04 00:00:00|20.0|22.0
    name|start_time|min|max
    classic_0|2026-03-01 00:00:00|11.0|13.0
    classic_1|2026-03-02 00:00:00|14.0|16.0
    classic_2|2026-03-03 00:00:00|17.0|19.0
    classic_3|2026-03-04 00:00:00|20.0|22.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

- Gebbert, S., Pebesma, E. 2014. *TGRASS: A temporal GIS for field based
  environmental modeling*. Environmental Modelling & Software 53, 1-12
  ([DOI](https://doi.org/10.1016/j.envsoft.2013.11.001)) - [preprint
  PDF](https://ifgi.uni-muenster.de/~epebe_01/tgrass.pdf)
- Gebbert, S., Pebesma, E. 2017. *The GRASS GIS temporal framework*.
  International Journal of Geographical Information Science 31,
  1273-1292 ([DOI](https://doi.org/10.1080/13658816.2017.1306862))
- Gebbert, S., Leppelt, T., Pebesma, E., 2019. *A topology based
  spatio-temporal map algebra for big data analysis*. Data 4, 86.
  ([DOI](https://doi.org/10.3390/data4020086))
- [Temporal data
  processing](https://grasswiki.osgeo.org/wiki/Temporal_data_processing)
  (Wiki)
- Vaclav Petras, Anna Petrasova, Helena Mitasova, Markus Neteler,
  **FOSS4G 2014 workshop**:  
  [Spatio-temporal data handling and visualization in GRASS
  GIS](https://ncsu-geoforall-lab.github.io/grass-temporal-workshop/)
- [GEOSTAT 2012 GRASS
  Course](https://www.geostat-course.org/Topic_Gebbert)

<!-- -->

- [Introduction into raster data processing](rasterintro.md)
- [Introduction into 3D raster data (voxel)
  processing](raster3dintro.md)
- [Introduction into vector data processing](vectorintro.md)
- [Introduction into image processing](imageryintro.md)
- [Database management](databaseintro.md)
- [Projections and spatial transformations](projectionintro.md)
