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

The granularity counts months and years when both times of a step (the start
and the end of an interval or of a gap) lie a whole number of months after the
earliest start of the maps, counted as a series counts its time stamps: the
earliest start plus one, two, three months, each cut to the end of a shorter
month. A monthly series from January 31, with intervals to February 28,
March 31 and April 30, has the granularity `1 month`, as has the same series
from January 1 or from January 15. The times January 31, February 28 and
March 28 are no such series: March 28 is not two months after January 31, so
the two steps count as 28 days each and the granularity is `28 days`. The
releases before GRASS 8.6 counted months only between the first days of two
months and gave the series from January 31 the granularity `1 day`. A dataset
keeps the granularity it stored until it is updated from its maps, for example
by *[t.support](t.support.md)* with **-u**.
Tools that work on the granularity (for example *t.rast.to.rast3* or the
**-g** flag of the algebra tools) use the stored granularity; the classic
algebra (**-c**) computes the granularity of the releases before GRASS 8.6.

Tools that cut a dataset into time steps, *t.rast.aggregate* with its option
**granularity** and the method `gran` of *[t.rast.list](t.rast.list.md)* with
its option **granule**, use such a step as a *granule*. Their manuals say how
the first granule is placed and how months are counted.

### Temporal topology

The temporal topology of a dataset describes how its maps lie in time to each
other. *[t.topology](t.topology.md)* reports it. The topology is *valid* if no
two maps are equal, overlap, or lie in each other. Maps that touch, where the
end of one map is the start of the next, and maps with a gap between them are
allowed, as are time instants. A *gap* is time that no map covers: it lies
before a map that starts after the latest end of the maps before it. A map
that ends inside a longer one leaves no gap behind it.
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
dataset must not contain a dot. A dataset of an earlier release whose whole
name contains a dot is found by that name: the mapsets are searched in turn,
the current one first, and in each the whole name is tried before the text
after the dot is read as a label. *t.info* prints the labels of a
dataset.

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
Temporal databases stored in other mapsets can be accessed, see
[Datasets of other mapsets](#datasets-of-other-mapsets). Datasets of other
mapsets can be read with `name@mapset`, but a tool that changes a dataset,
such as *t.register*, *t.rename* or *t.create*, works on the current mapset
only.
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

### Datasets of other mapsets

A dataset named with its mapset, `name@mapset`, is read from any mapset of the
project that has a temporal database. The mapset does not have to be in the
search path. A name without a mapset is searched by *t.rast.list*, for
example, in the current mapset first, then in the mapsets of the search path
in their order, and is not found if the dataset lies in a mapset outside the
search path. *t.select* and the algebra tools search the
current mapset and the search path, with **-c** only the current mapset. A
tool that reads the maps of a dataset of another mapset, such as
*t.rast.mapcalc*, *t.rast3d.mapcalc* and *t.rast.accdetect*, needs no entry in
the search path for it. For the other tools, add the mapset
with *[g.mapsets](g.mapsets.md)* `operation=add` only if datasets of that
mapset should be found by their name alone. A mapset that does not exist or has
no temporal database is refused with an error. The last example of the
[EXAMPLES](#examples) shows both ways.

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

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `temporalintro` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region, except the last, which creates a second mapset. The temporal
manuals use the same kind of data: series of maps for 2020 that are generated
from maps of the dataset, here the monthly air temperature and the monthly
precipitation. The values are generated, not measured. Each example uses the
result of the previous one.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=temporalintro -->

<!-- markdownlint-disable MD046 -->

### Create a dataset and register maps

The dataset `temperature_monthly` holds twelve maps of the monthly mean air
temperature in 2020, in degrees Celsius rounded to tenths. They are generated
from the elevation model `elev_state_500m`: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of elevation, and 1 degree
more for every 100 km to the south.

*[t.create](t.create.md)* creates the empty dataset and *[t.register](t.register.md)*
registers the twelve maps in it. With the flag **-i** and the options **start**
and **increment**, the maps become consecutive intervals of one month, the
first starting on 1 January 2020. The commands print nothing.

=== "Command line"

    ```sh
    g.mapset -c mapset=temporalintro
    g.region raster=elev_state_500m res=1000 -a
    for month in $(seq 12); do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=temperature_monthly title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius"
    t.register -i input=temperature_monthly \
        maps=$(g.list type=raster pattern="temperature_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="temporalintro")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    months = range(1, 13)
    tools.r_mapcalc(
        expression="\n".join(
            f"temperature_monthly_2020_{month:02d} = round((16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * elev_state_500m"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        output="temperature_monthly",
        title="Air temperature",
        description="Monthly mean air temperature 2020 in degree Celsius",
    )
    tools.t_register(
        input="temperature_monthly",
        maps=",".join(f"temperature_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

### Look at the dataset and its time

*[t.info](t.info.md)* with the flag **-g** prints the properties of the dataset.
The twelve maps cover the year 2020, and the granularity is one month.
*[t.topology](t.topology.md)* shows that the topology is valid: the maps touch
without gaps, so there are eleven `Follows` and eleven `Precedes` pairs.
*[t.rast.list](t.rast.list.md)* lists the maps with their times and the
minimum and maximum of their values. January is the coldest month with
-7.0 degrees in the coldest cell, and July the warmest with 28.4 degrees in the
warmest cell.

=== "Command line"

    ```sh
    t.info -g input=temperature_monthly | grep -E "^(start_time|end_time|granularity|number_of_maps)="
    t.topology input=temperature_monthly
    t.rast.list input=temperature_monthly columns=name,start_time,end_time,min,max
    ```

    ```text
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    granularity='1 month'
    number_of_maps=12
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly@temporalintro
     | Name: ...................... temperature_monthly
     | Mapset: .................... temporalintro
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 12
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 month
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 11
     | Precedes: .................. 11
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
    temperature_monthly_2020_01|2020-01-01 00:00:00|2020-02-01 00:00:00|-7.0|7.5
    temperature_monthly_2020_02|2020-02-01 00:00:00|2020-03-01 00:00:00|-6.1|8.4
    temperature_monthly_2020_03|2020-03-01 00:00:00|2020-04-01 00:00:00|-2.7|11.8
    temperature_monthly_2020_04|2020-04-01 00:00:00|2020-05-01 00:00:00|2.4|16.9
    temperature_monthly_2020_05|2020-05-01 00:00:00|2020-06-01 00:00:00|7.7|22.2
    temperature_monthly_2020_06|2020-06-01 00:00:00|2020-07-01 00:00:00|12.0|26.5
    temperature_monthly_2020_07|2020-07-01 00:00:00|2020-08-01 00:00:00|13.9|28.4
    temperature_monthly_2020_08|2020-08-01 00:00:00|2020-09-01 00:00:00|13.1|27.6
    temperature_monthly_2020_09|2020-09-01 00:00:00|2020-10-01 00:00:00|9.6|24.2
    temperature_monthly_2020_10|2020-10-01 00:00:00|2020-11-01 00:00:00|4.6|19.1
    temperature_monthly_2020_11|2020-11-01 00:00:00|2020-12-01 00:00:00|-0.8|13.7
    temperature_monthly_2020_12|2020-12-01 00:00:00|2021-01-01 00:00:00|-5.0|9.5
    ```

=== "Python (grass.tools)"

    ```python
    info = tools.t_info(input="temperature_monthly", flags="g").keyval
    for key in ("start_time", "end_time", "granularity", "number_of_maps"):
        print(f"{key}={info[key]}")
    print(tools.t_topology(input="temperature_monthly").stdout, end="")
    print(
        tools.t_rast_list(
            input="temperature_monthly", columns="name,start_time,end_time,min,max"
        ).text
    )
    ```

    ```text
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    granularity='1 month'
    number_of_maps=12
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly@temporalintro
     | Name: ...................... temperature_monthly
     | Mapset: .................... temporalintro
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 12
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 month
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 11
     | Precedes: .................. 11
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
    temperature_monthly_2020_01|2020-01-01 00:00:00|2020-02-01 00:00:00|-7.0|7.5
    temperature_monthly_2020_02|2020-02-01 00:00:00|2020-03-01 00:00:00|-6.1|8.4
    temperature_monthly_2020_03|2020-03-01 00:00:00|2020-04-01 00:00:00|-2.7|11.8
    temperature_monthly_2020_04|2020-04-01 00:00:00|2020-05-01 00:00:00|2.4|16.9
    temperature_monthly_2020_05|2020-05-01 00:00:00|2020-06-01 00:00:00|7.7|22.2
    temperature_monthly_2020_06|2020-06-01 00:00:00|2020-07-01 00:00:00|12.0|26.5
    temperature_monthly_2020_07|2020-07-01 00:00:00|2020-08-01 00:00:00|13.9|28.4
    temperature_monthly_2020_08|2020-08-01 00:00:00|2020-09-01 00:00:00|13.1|27.6
    temperature_monthly_2020_09|2020-09-01 00:00:00|2020-10-01 00:00:00|9.6|24.2
    temperature_monthly_2020_10|2020-10-01 00:00:00|2020-11-01 00:00:00|4.6|19.1
    temperature_monthly_2020_11|2020-11-01 00:00:00|2020-12-01 00:00:00|-0.8|13.7
    temperature_monthly_2020_12|2020-12-01 00:00:00|2021-01-01 00:00:00|-5.0|9.5
    ```

### Aggregate over a longer period

*[t.rast.aggregate](t.rast.aggregate.md)* cuts the time into granules of three
months and averages the maps of each granule. The **where** condition selects
the maps from March to November, so the granules are March to May, June to
August and September to November: spring, summer and autumn. In summer the
warmest cell has 26.5, 28.4 and 27.6 degrees in June, July and August, so its
mean is 27.5 degrees.

The figure shows the three new maps with the border of North Carolina from the
vector map `nc_state`. *[t.rast.colors](t.rast.colors.md)* gives the maps the
colour table `celsius`, so the same colour means the same temperature in all
three maps. *d.frame* makes one frame per map, *d.rast* draws the map, *d.vect*
the border and *d.text* the name; *d.legend* draws the legend in a frame of its
own.

=== "Command line"

    ```sh
    t.rast.aggregate input=temperature_monthly output=temperature_season \
        basename=temperature_season granularity="3 months" method=average \
        where="start_time >= '2020-03-01' and start_time < '2020-12-01'"
    t.rast.list input=temperature_season columns=name,start_time,end_time,min,max
    t.rast.colors input=temperature_season color=celsius
    d.mon start=cairo output=temporalintro_summer.png width=600 height=600
    row=0
    for map in "temperature_season_2020_03 spring" \
        "temperature_season_2020_06 summer" \
        "temperature_season_2020_09 autumn"; do
        set -- $map
        top=$((100 - 33 * row))
        d.frame -c frame=map_$row at=$((top - 33)),$top,0,80
        d.rast map=$1
        d.vect map=nc_state type=boundary color=black
        d.text text=$2 at=2,8 size=14 color=black
        row=$((row + 1))
    done
    d.frame -c frame=legend at=0,100,80,100
    d.legend raster=temperature_season_2020_06 range=0,30 at=10,90,10,35 \
        label_step=5 digits=0 title="deg C"
    d.mon stop=cairo
    ```

    ```text
    name|start_time|end_time|min|max
    temperature_season_2020_03|2020-03-01 00:00:00|2020-06-01 00:00:00|2.466666666666667|16.966666666666665
    temperature_season_2020_06|2020-06-01 00:00:00|2020-09-01 00:00:00|13.0|27.5
    temperature_season_2020_09|2020-09-01 00:00:00|2020-12-01 00:00:00|4.466666666666666|19.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_aggregate(
        input="temperature_monthly",
        output="temperature_season",
        basename="temperature_season",
        granularity="3 months",
        method="average",
        where="start_time >= '2020-03-01' and start_time < '2020-12-01'",
    )
    columns = "name,start_time,end_time,min,max"
    print(tools.t_rast_list(input="temperature_season", columns=columns).text)
    tools.t_rast_colors(input="temperature_season", color="celsius")
    tools.d_mon(start="cairo", output="temporalintro_summer.png", width=600, height=600)
    for row, (name, label) in enumerate(
        (
            ("temperature_season_2020_03", "spring"),
            ("temperature_season_2020_06", "summer"),
            ("temperature_season_2020_09", "autumn"),
        )
    ):
        top = 100 - 33 * row
        tools.d_frame(flags="c", frame=f"map_{row}", at=[top - 33, top, 0, 80])
        tools.d_rast(map=name)
        tools.d_vect(map="nc_state", type="boundary", color="black")
        tools.d_text(text=label, at=[2, 8], size=14, color="black")
    tools.d_frame(flags="c", frame="legend", at=[0, 100, 80, 100])
    tools.d_legend(
        raster="temperature_season_2020_06",
        range=[0, 30],
        at=[10, 90, 10, 35],
        label_step=5,
        digits=0,
        title="deg C",
    )
    tools.d_mon(stop="cairo")
    ```

    ```text
    name|start_time|end_time|min|max
    temperature_season_2020_03|2020-03-01 00:00:00|2020-06-01 00:00:00|2.466666666666667|16.966666666666665
    temperature_season_2020_06|2020-06-01 00:00:00|2020-09-01 00:00:00|13.0|27.5
    temperature_season_2020_09|2020-09-01 00:00:00|2020-12-01 00:00:00|4.466666666666666|19.0
    ```

![Generated mean air temperature of spring, summer and autumn 2020 in North Carolina](temporalintro_summer.png)

*Figure: Mean air temperature of spring, summer and autumn 2020, computed from
generated monthly maps (not measured data).*

### Sample one dataset by another

A second generated series, `precipitation_monthly`, holds the monthly
precipitation sum of 2020 in millimeters. The monthly normals of the 136
climate stations in the vector map `precip_30ynormals` are interpolated for
each month with *[v.surf.idw](v.surf.idw.md)* and multiplied by an assumed
factor for the wet year 2020. The maps are registered like the temperature
maps.

*[t.sample](t.sample.md)* takes `temperature_season` as the sampler and prints,
for each of its maps, the maps of `precipitation_monthly` in the default
relations `during`, `overlap`, `contain` and `equal`. Each season contains
three monthly maps, so each row names three maps. The columns are the sampler
map, the related maps of `precipitation_monthly`, the start and end of the
granule, its length in days (92, 92 and 91) and the distance of its start from
the first granule in days (the manual of *t.sample* describes them).

=== "Command line"

    ```sh
    month=1
    for entry in jan:1.2 feb:1.7 mar:0.9 apr:1.3 may:1.6 jun:0.9 \
        jul:1.1 aug:1.5 sep:0.8 oct:1.0 nov:1.6 dec:0.9; do
        name=$(printf %02d $month)
        v.surf.idw input=precip_30ynormals column=${entry%:*} \
            output=precipitation_normal_$name npoints=12 power=2
        r.mapcalc expression="precipitation_monthly_2020_$name = if(isnull(elev_state_500m), null(), round(${entry#*:} * precipitation_normal_$name))"
        month=$((month + 1))
    done
    t.create output=precipitation_monthly title="Precipitation" \
        description="Monthly precipitation sum 2020 in mm"
    t.register -i input=precipitation_monthly \
        maps=$(g.list type=raster pattern="precipitation_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.sample inputs=precipitation_monthly sample=temperature_season
    ```

    ```text
    temperature_season_2020_03@temporalintro|precipitation_monthly_2020_03@temporalintro,precipitation_monthly_2020_04@temporalintro,precipitation_monthly_2020_05@temporalintro|2020-03-01 00:00:00|2020-06-01 00:00:00|92.0|0.0
    temperature_season_2020_06@temporalintro|precipitation_monthly_2020_06@temporalintro,precipitation_monthly_2020_07@temporalintro,precipitation_monthly_2020_08@temporalintro|2020-06-01 00:00:00|2020-09-01 00:00:00|92.0|92.0
    temperature_season_2020_09@temporalintro|precipitation_monthly_2020_09@temporalintro,precipitation_monthly_2020_10@temporalintro,precipitation_monthly_2020_11@temporalintro|2020-09-01 00:00:00|2020-12-01 00:00:00|91.0|184.0
    ```

=== "Python (grass.tools)"

    ```python
    factors = {"jan": 1.2, "feb": 1.7, "mar": 0.9, "apr": 1.3, "may": 1.6, "jun": 0.9}
    factors |= {"jul": 1.1, "aug": 1.5, "sep": 0.8, "oct": 1.0, "nov": 1.6, "dec": 0.9}
    for month, (column, factor) in enumerate(factors.items(), start=1):
        normal = f"precipitation_normal_{month:02d}"
        tools.v_surf_idw(
            input="precip_30ynormals", column=column, output=normal, npoints=12, power=2
        )
        tools.r_mapcalc(
            expression=f"precipitation_monthly_2020_{month:02d} ="
            f" if(isnull(elev_state_500m), null(), round({factor} * {normal}))"
        )
    tools.t_create(
        output="precipitation_monthly",
        title="Precipitation",
        description="Monthly precipitation sum 2020 in mm",
    )
    tools.t_register(
        input="precipitation_monthly",
        maps=",".join(f"precipitation_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    print(tools.t_sample(inputs="precipitation_monthly", sample="temperature_season").text)
    ```

    ```text
    temperature_season_2020_03@temporalintro|precipitation_monthly_2020_03@temporalintro,precipitation_monthly_2020_04@temporalintro,precipitation_monthly_2020_05@temporalintro|2020-03-01 00:00:00|2020-06-01 00:00:00|92.0|0.0
    temperature_season_2020_06@temporalintro|precipitation_monthly_2020_06@temporalintro,precipitation_monthly_2020_07@temporalintro,precipitation_monthly_2020_08@temporalintro|2020-06-01 00:00:00|2020-09-01 00:00:00|92.0|92.0
    temperature_season_2020_09@temporalintro|precipitation_monthly_2020_09@temporalintro,precipitation_monthly_2020_10@temporalintro,precipitation_monthly_2020_11@temporalintro|2020-09-01 00:00:00|2020-12-01 00:00:00|91.0|184.0
    ```

### Compute with the temporal algebra

*[t.rast.algebra](t.rast.algebra.md)* combines the two datasets, which have the
same months. The expression marks the cells that are warm and wet in a month:
warmer than 15 degrees and with more than 100 mm of precipitation. The result
dataset `warm_wet` keeps the times of the input maps; each map holds 1 where
both conditions are true and 0 elsewhere, so its largest value is 1 from April
to October, the months with such a cell. The flag **-c** selects the classic
algebra: the second call computes the same expression with it into
`warm_wet_classic`, and the list shows the same values and times. The names of
the maps differ only in the basename.

=== "Command line"

    ```sh
    t.rast.algebra expression="warm_wet = if(temperature_monthly > 15.0 && precipitation_monthly > 100, 1, 0)" basename=warm_wet
    t.rast.list input=warm_wet columns=name,start_time,min,max
    t.rast.algebra -c expression="warm_wet_classic = if(temperature_monthly > 15.0 && precipitation_monthly > 100, 1, 0)" basename=classic
    t.rast.list input=warm_wet_classic columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_wet_00|2020-01-01 00:00:00|0.0|0.0
    warm_wet_01|2020-02-01 00:00:00|0.0|0.0
    warm_wet_02|2020-03-01 00:00:00|0.0|0.0
    warm_wet_03|2020-04-01 00:00:00|0.0|1.0
    warm_wet_04|2020-05-01 00:00:00|0.0|1.0
    warm_wet_05|2020-06-01 00:00:00|0.0|1.0
    warm_wet_06|2020-07-01 00:00:00|0.0|1.0
    warm_wet_07|2020-08-01 00:00:00|0.0|1.0
    warm_wet_08|2020-09-01 00:00:00|0.0|1.0
    warm_wet_09|2020-10-01 00:00:00|0.0|1.0
    warm_wet_10|2020-11-01 00:00:00|0.0|0.0
    warm_wet_11|2020-12-01 00:00:00|0.0|0.0
    name|start_time|min|max
    classic_00|2020-01-01 00:00:00|0.0|0.0
    classic_01|2020-02-01 00:00:00|0.0|0.0
    classic_02|2020-03-01 00:00:00|0.0|0.0
    classic_03|2020-04-01 00:00:00|0.0|1.0
    classic_04|2020-05-01 00:00:00|0.0|1.0
    classic_05|2020-06-01 00:00:00|0.0|1.0
    classic_06|2020-07-01 00:00:00|0.0|1.0
    classic_07|2020-08-01 00:00:00|0.0|1.0
    classic_08|2020-09-01 00:00:00|0.0|1.0
    classic_09|2020-10-01 00:00:00|0.0|1.0
    classic_10|2020-11-01 00:00:00|0.0|0.0
    classic_11|2020-12-01 00:00:00|0.0|0.0
    ```

=== "Python (grass.tools)"

    ```python
    condition = "temperature_monthly > 15.0 && precipitation_monthly > 100"
    tools.t_rast_algebra(
        expression=f"warm_wet = if({condition}, 1, 0)", basename="warm_wet"
    )
    print(tools.t_rast_list(input="warm_wet", columns="name,start_time,min,max").text)
    tools.t_rast_algebra(
        expression=f"warm_wet_classic = if({condition}, 1, 0)",
        basename="classic",
        flags="c",
    )
    print(
        tools.t_rast_list(input="warm_wet_classic", columns="name,start_time,min,max").text
    )
    ```

    ```text
    name|start_time|min|max
    warm_wet_00|2020-01-01 00:00:00|0.0|0.0
    warm_wet_01|2020-02-01 00:00:00|0.0|0.0
    warm_wet_02|2020-03-01 00:00:00|0.0|0.0
    warm_wet_03|2020-04-01 00:00:00|0.0|1.0
    warm_wet_04|2020-05-01 00:00:00|0.0|1.0
    warm_wet_05|2020-06-01 00:00:00|0.0|1.0
    warm_wet_06|2020-07-01 00:00:00|0.0|1.0
    warm_wet_07|2020-08-01 00:00:00|0.0|1.0
    warm_wet_08|2020-09-01 00:00:00|0.0|1.0
    warm_wet_09|2020-10-01 00:00:00|0.0|1.0
    warm_wet_10|2020-11-01 00:00:00|0.0|0.0
    warm_wet_11|2020-12-01 00:00:00|0.0|0.0
    name|start_time|min|max
    classic_00|2020-01-01 00:00:00|0.0|0.0
    classic_01|2020-02-01 00:00:00|0.0|0.0
    classic_02|2020-03-01 00:00:00|0.0|0.0
    classic_03|2020-04-01 00:00:00|0.0|1.0
    classic_04|2020-05-01 00:00:00|0.0|1.0
    classic_05|2020-06-01 00:00:00|0.0|1.0
    classic_06|2020-07-01 00:00:00|0.0|1.0
    classic_07|2020-08-01 00:00:00|0.0|1.0
    classic_08|2020-09-01 00:00:00|0.0|1.0
    classic_09|2020-10-01 00:00:00|0.0|1.0
    classic_10|2020-11-01 00:00:00|0.0|0.0
    classic_11|2020-12-01 00:00:00|0.0|0.0
    ```

### Datasets of another mapset

The example creates the mapset `temporalintro_2` and switches to it, so it is
the current mapset and `temporalintro` is not in its search path. A new
mapset takes its region from the default region of the dataset, so the region
of the first example is set again. *[t.rast.list](t.rast.list.md)* reads the
dataset `temperature_monthly` of the first example with its mapset,
`temperature_monthly@temporalintro`, and lists the maps of the first two
months. The name `temperature_monthly` alone is not found: the mapset
`temporalintro` is neither the current mapset nor in the search path. After
*g.mapsets* with `operation=add` has added it to the search path, the name
alone finds the dataset too.

=== "Command line"

    ```sh
    g.mapset -c mapset=temporalintro_2
    g.region raster=elev_state_500m res=1000 -a
    t.rast.list input=temperature_monthly@temporalintro columns=name,mapset \
        where="start_time < '2020-03-01'"
    if ! t.rast.list input=temperature_monthly columns=name,mapset 2>&1; then
        echo "t.rast.list failed"
    fi
    g.mapsets mapset=temporalintro operation=add
    t.rast.list input=temperature_monthly columns=name,mapset \
        where="start_time < '2020-03-01'"
    ```

    ```text
    name|mapset
    temperature_monthly_2020_01|temporalintro
    temperature_monthly_2020_02|temporalintro
    ERROR: Space time dataset <temperature_monthly> of type <strds> not found
    t.rast.list failed
    name|mapset
    temperature_monthly_2020_01|temporalintro
    temperature_monthly_2020_02|temporalintro
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_mapset(flags="c", mapset="temporalintro_2")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    first_months = "start_time < '2020-03-01'"
    result = tools.t_rast_list(
        input="temperature_monthly@temporalintro",
        columns="name,mapset",
        where=first_months,
    )
    print(result.text)
    try:
        tools.t_rast_list(input="temperature_monthly", columns="name,mapset")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.list failed")
    tools.g_mapsets(mapset="temporalintro", operation="add")
    result = tools.t_rast_list(
        input="temperature_monthly", columns="name,mapset", where=first_months
    )
    print(result.text)
    ```

    ```text
    name|mapset
    temperature_monthly_2020_01|temporalintro
    temperature_monthly_2020_02|temporalintro
    ERROR: Space time dataset <temperature_monthly> of type <strds> not found
    t.rast.list failed
    name|mapset
    temperature_monthly_2020_01|temporalintro
    temperature_monthly_2020_02|temporalintro
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
