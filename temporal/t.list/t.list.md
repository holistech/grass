## DESCRIPTION

*t.list* lists the space time datasets and the time stamped maps that are
registered in the temporal database. It reads the temporal databases of the
accessible mapsets and changes nothing. A listing is the usual first step to
see what a project holds before *[t.info](t.info.md)* describes one dataset in
detail, or one of the tools for a single dataset type, such as
*[t.rast.list](t.rast.list.md)*, lists the maps of a dataset. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

### Selection

The option **type** chooses what is listed. It takes one or more of these
values, separated by commas; the default is `strds`:

- `strds`, `str3ds` and `stvds`: space time raster, 3D raster and vector
  datasets;
- `raster`, `raster_3d` and `vector`: the maps with a time stamp. A map is
  listed whether or not it is registered in a dataset, but it must be
  registered in the temporal database with *[t.register](t.register.md)*.

Space time datasets and maps cannot be listed together: `type=strds,raster`
stops with an error.

The option **temporaltype** chooses the temporal types: `absolute` for
datasets and maps with calendar time, `relative` for those with a number of
time units. The default is `absolute,relative`, both.

The option **where** takes an SQL condition on the columns of the listing,
such as `number_of_maps > 2` or `semantic_label IS NOT NULL`. A condition like
`name LIKE 'precip%'` lists by a pattern in the name, as the option **pattern**
of *[g.list](g.list.md)* does. A condition with a syntax error stops with an
error that starts with "Invalid where condition".

The option **mapset** chooses the mapsets whose temporal databases are read.
Without it, these are the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). It takes one or more names, separated by commas:

- `mapset=.` is the current mapset;
- `mapset=*` is every mapset of the project, whether or not it is in the
  search path;
- `mapset=name1,name2` are exactly the named mapsets, also those outside the
  search path.

Quote `*` in the shell: `mapset='*'`.

A name that is no mapset of the project stops *t.list* with the error
`Mapset <name> not found in the project.` and a return code other than 0. A
mapset that exists but has no temporal database is no error and lists
nothing, as described under the output below.

### Columns

The option **columns** chooses the columns that are printed for each dataset
or map, separated by commas. The default is `id`, except for `format=json`,
where it is `all`. The columns are, with the types they apply to:

- `id`, the name of the dataset or map with its mapset, such as
  `rain@PERMANENT`; `name` and `mapset`, the two parts of it;
- `semantic_type`, how the values of a dataset are to be understood: `sum`,
  `mean`, `min` or `max` (see *[t.create](t.create.md)*); only for space time
  datasets;
- `semantic_label`, the semantic label of a raster map, a missing value for a
  map without one; only for the type `raster`;
- `number_of_maps`, the number of maps registered in the dataset, and
  `granularity`, their time step; only for space time datasets. The
  granularity of a dataset with absolute time is a text such as `1 day`, one
  with relative time has a number of its time unit, such as `6` for 6 hours;
- `number_of_semantic_labels`, the number of semantic labels of the maps of a
  dataset; only for space time raster datasets;
- `start_time` and `end_time`, the time of the dataset or map. For a dataset,
  they enclose all its maps; for a map registered as a time instance, the end
  time is `None` (see NOTES for the output of a missing value). With relative
  time they are numbers in the unit of the dataset or map, printed without the
  unit;
- `north`, `south`, `west` and `east`, the spatial extent;
- `creator` and `creation_time`, the user who created the entry in the
  temporal database and the time of its creation;
- `type`, the type of the listed objects, one of the values of **type**;
- `all`, every column that the table of the temporal database has for the type.

A column that the listed type does not have, such as `number_of_maps` for
`type=raster`, stops with the error "Column 'number_of_maps' is not available
for the requested dataset type". With several types, `all` lists only the
columns that all of them have.

The value `all` shows more than the other columns: for a space time raster
dataset also `temporal_type`, `modification_time`, the extent `bottom` and
`top`, `proj`, the name of its register table, the smallest and largest
resolution of its maps (`nsres_min`, `ewres_min`, `nsres_max`, `ewres_max`),
the smallest and largest minimum and maximum of the values of its maps
(`min_min`, `min_max`, `max_min`, `max_max`), `aggregation_type`, `title`,
`description` and `command`, the history of commands. A dataset with relative
time has the column `unit`. The example "Inspect all columns of a type" lists
the names of the columns for every type and shows these values for two
datasets.

The column `type` is always the last column, in every format, even if
**columns** names it elsewhere, as in `columns=type,name`. It is added by
itself when several types are listed. It can be named for a single type as
well, but not alone: `columns=type` stops with the error "Column 'type' cannot
be requested alone".

### Order

The option **order** sorts the datasets or maps by one or more columns,
separated by commas. The default is `id`. It takes names of columns only, no
sort direction: `order=name DESC` is refused by the parser. Sorting applies
separately to the datasets of each temporal type: with the default
**temporaltype**, the datasets with absolute time are listed and sorted first,
then those with relative time, each sorted on its own. The same holds for each
mapset.

A column that the listed type does not have, such as `number_of_maps` for
`type=raster`, ends the run with the error `Invalid order <number_of_maps>:`
followed by the message of the database; the same column in **where** is
reported as `Invalid where condition`.

### Output

The option **format** chooses the form of the output:

- `plain` (the default) prints one line per dataset or map with the columns
  separated by a vertical bar `|`. A missing value is printed as `None`. The
  rows are listed in groups, one for each temporal type, mapset and (if
  several are listed) type. Each group starts with a heading, which is written
  to the standard error, not the standard output, and only if the output goes
  to the screen (not with **output**, not with `--quiet`);
- `csv` separates the columns with a comma and leaves a missing value empty.
  The line with the column names always comes first. There are no headings;
- `line` prints the values of one column in one line, separated by a comma.
  It needs exactly one type and one column; `columns=all` is not accepted;
- `json` prints a list with one object per dataset or map. The keys are the
  column names, a missing value is `null`, numbers are numbers (also the
  relative times), and times with absolute time are text.

The flag **-c** prints the column names as the first line of a `plain` listing.
The format `csv` always prints them. `line` refuses **-c**, and so does `json`,
which names the values in every object.

The option **separator** replaces the separator of the formats `plain`,
`csv` and `line`. It takes a single character or one of the names `pipe`,
`comma`, `space`, `tab` and `newline`. The format `csv` accepts only one
character, and `json` refuses the option.

The option **output** writes the listing to a file instead of the standard
output; `output=-` is the standard output. **--overwrite** lets *t.list*
replace an existing file.

## NOTES

The listing is empty if no dataset matches, for instance because **where**
matches none: `plain` and `line` print nothing, `csv` prints the line with the
column names and `json` prints an empty list `[]`. With **-c**, `plain` prints
the column names in this case, too. The column names are those of a listing
with rows, with `type` last when the type is a part of the listing. The example
"Inspect all columns of a type" uses this to list the names of all columns.

If none of the requested mapsets has a temporal database, *t.list* prints the
message "No temporal database found in the requested mapset(s). No datasets to
list." (format `plain`) or `[]` (format `json`). Other formats print nothing.
*t.list* does not create a temporal database for it. The current mapset needs
no temporal database of its own to list the datasets of other accessible
mapsets.

Datasets are listed from the mapsets of the search path or from the mapsets
named by **mapset**; the name of a dataset or map in the listing carries its
mapset, so datasets of the same name in different mapsets can be told apart.
The last example shows this.

A condition in **where** that SQL refuses is reported as an error, and
*t.list* then writes no **output** file and leaves an existing one as it was.
When **where** matches nothing, *t.list* still writes **output**: an empty file
for `plain` and `line`, the line with the column names for `csv` and `[]` for
`json`.

Space time raster datasets have the column `number_of_semantic_labels`. A
temporal database created before this column was added to the database views
lacks it there: `columns=all` and the JSON output leave it out, and
`columns=number_of_semantic_labels` ends with a message that names
*[t.upgrade](t.upgrade.md)*, which creates the views anew. When the temporal
databases of the listed mapsets differ in this, `columns=all` lists the
columns that all of them have.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_list` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.list* reads the temporal database and no map values, so the maps
hold small constant values. Most listings name the current mapset with
`mapset=.`, which restricts them to the datasets and maps made here; the last
example turns to the other mapsets.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_list -->

<!-- markdownlint-disable MD046 -->

### List the space time datasets

Three space time raster datasets are made for the examples. The dataset
`temperature` has three maps of daily mean air temperature in March 2026. The
dataset `rain` has two maps of daily precipitation sums in June 2026; its
semantic type is `sum`. The dataset `model` has relative time and two model
steps of 6 hours. The temperature maps hold two values each, one in the first
row and one in the other rows, so that their minimum and maximum differ. The
default listing prints the `id` of the datasets with absolute time, sorted by
name, and then those with relative time.

The second block adds the flag **-c**, which puts the column name `id` before
the datasets.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_list
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="temperature_1 = if(row() == 1, -2, 0)"
    r.mapcalc expression="temperature_2 = if(row() == 1, 1, 3)"
    r.mapcalc expression="temperature_3 = if(row() == 1, 4, 6)"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    r.mapcalc expression="rain_1 = 4"
    r.mapcalc expression="rain_2 = 2"
    t.create output=rain semantictype=sum title="Rain" \
        description="Daily precipitation sums"
    t.register -i input=rain maps=rain_1,rain_2 \
        start=2026-06-01 increment="1 day"
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i input=model maps=step_1,step_2 \
        start=0 increment=6 unit=hours
    t.list mapset=.
    ```

    ```text
    rain@t_list
    temperature@t_list
    model@t_list
    ```

    ```sh
    t.list -c mapset=.
    ```

    ```text
    id
    rain@t_list
    temperature@t_list
    model@t_list
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_list")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.r_mapcalc(expression="temperature_1 = if(row() == 1, -2, 0)")
    tools.r_mapcalc(expression="temperature_2 = if(row() == 1, 1, 3)")
    tools.r_mapcalc(expression="temperature_3 = if(row() == 1, 4, 6)")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.r_mapcalc(expression="rain_1 = 4")
    tools.r_mapcalc(expression="rain_2 = 2")
    tools.t_create(
        output="rain",
        semantictype="sum",
        title="Rain",
        description="Daily precipitation sums",
    )
    tools.t_register(
        input="rain",
        maps="rain_1,rain_2",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_list(mapset=".").text)
    ```

    ```text
    rain@t_list
    temperature@t_list
    model@t_list
    ```

    ```python
    print(tools.t_list(flags="c", mapset=".").text)
    ```

    ```text
    id
    rain@t_list
    temperature@t_list
    model@t_list
    ```

### Choose the types and the columns

Two more datasets are made: the space time 3D raster dataset `soil` and the
space time vector dataset `gauges`. The 3D region gets three layers of 1
unit. The vector map `gauges_1` holds two stream gauges, copied from the
sample dataset's `usgsgages`. The first block lists all three dataset types
with the columns `name` and `number_of_maps`. The `type` is added as the last
column, and the datasets are grouped by type within the temporal type.

The second block lists the space time raster datasets with more columns and
the column names. The granularity of the dataset `model` is the number 6, the
unit of its relative time (hours) is not a column. The end of `temperature` is
the end of its last map.

The third block names `type` first, but it is printed last.

=== "Command line"

    ```sh
    g.region t=3 b=0 res3=1000 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in three layers"
    t.register -i type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2026-03-01 increment="1 day"
    v.extract input=usgsgages output=gauges_1 where="cat <= 2"
    t.create type=stvds output=gauges title="Gauges" \
        description="Water level at two stream gauges"
    t.register -i type=vector input=gauges maps=gauges_1 \
        start=2026-03-01 increment="1 day"
    t.list type=strds,str3ds,stvds columns=name,number_of_maps mapset=.
    ```

    ```text
    rain|2|strds
    temperature|3|strds
    soil|2|str3ds
    gauges|1|stvds
    model|2|strds
    ```

    ```sh
    t.list -c columns=name,semantic_type,number_of_maps,granularity,start_time,end_time mapset=.
    ```

    ```text
    name|semantic_type|number_of_maps|granularity|start_time|end_time
    rain|sum|2|1 day|2026-06-01 00:00:00|2026-06-03 00:00:00
    temperature|mean|3|1 day|2026-03-01 00:00:00|2026-03-04 00:00:00
    model|mean|2|6|0|12
    ```

    ```sh
    t.list -c type=stvds columns=type,name mapset=.
    ```

    ```text
    name|type
    gauges|stvds
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(t=3, b=0, res3=1000, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in three layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.v_extract(input="usgsgages", output="gauges_1", where="cat <= 2")
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Gauges",
        description="Water level at two stream gauges",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(
        tools.t_list(
            type="strds,str3ds,stvds", columns="name,number_of_maps", mapset="."
        ).text
    )
    ```

    ```text
    rain|2|strds
    temperature|3|strds
    soil|2|str3ds
    gauges|1|stvds
    model|2|strds
    ```

    ```python
    print(
        tools.t_list(
            columns="name,semantic_type,number_of_maps,granularity,start_time,end_time",
            flags="c",
            mapset=".",
        ).text
    )
    ```

    ```text
    name|semantic_type|number_of_maps|granularity|start_time|end_time
    rain|sum|2|1 day|2026-06-01 00:00:00|2026-06-03 00:00:00
    temperature|mean|3|1 day|2026-03-01 00:00:00|2026-03-04 00:00:00
    model|mean|2|6|0|12
    ```

    ```python
    print(tools.t_list(type="stvds", columns="type,name", flags="c", mapset=".").text)
    ```

    ```text
    name|type
    gauges|stvds
    ```

### Select and sort the datasets

The first block lists the datasets that have more than two maps: only
`temperature`. The second selects by a pattern in the name: `rain`.
The third sorts by the start time, so `temperature` (March) comes before `rain`
(June). The dataset `model` follows them, because datasets with absolute time
come first and each temporal type is sorted on its own. The fourth block lists
only the datasets with relative time, and the numbers are those of its unit.

=== "Command line"

    ```sh
    t.list -c columns=name,number_of_maps where="number_of_maps > 2" mapset=.
    ```

    ```text
    name|number_of_maps
    temperature|3
    ```

    ```sh
    t.list columns=name where="name LIKE 'r%'" mapset=.
    ```

    ```text
    rain
    ```

    ```sh
    t.list columns=name,start_time order=start_time mapset=.
    ```

    ```text
    temperature|2026-03-01 00:00:00
    rain|2026-06-01 00:00:00
    model|0
    ```

    ```sh
    t.list -c temporaltype=relative columns=name,start_time,end_time,granularity mapset=.
    ```

    ```text
    name|start_time|end_time|granularity
    model|0|12|6
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_list(
        columns="name,number_of_maps",
        where="number_of_maps > 2",
        flags="c",
        mapset=".",
    )
    print(result.text)
    ```

    ```text
    name|number_of_maps
    temperature|3
    ```

    ```python
    print(tools.t_list(columns="name", where="name LIKE 'r%'", mapset=".").text)
    ```

    ```text
    rain
    ```

    ```python
    print(tools.t_list(columns="name,start_time", order="start_time", mapset=".").text)
    ```

    ```text
    temperature|2026-03-01 00:00:00
    rain|2026-06-01 00:00:00
    model|0
    ```

    ```python
    result = tools.t_list(
        temporaltype="relative",
        columns="name,start_time,end_time,granularity",
        flags="c",
        mapset=".",
    )
    print(result.text)
    ```

    ```text
    name|start_time|end_time|granularity
    model|0|12|6
    ```

### Choose the output format

Five blocks show the formats. The first prints the dataset times as `csv`, the
second the number of maps as `plain` with the separator `;`. The third puts the
names in one line (`line`). The fourth prints `json` for `temperature` and
`model`: the times of the dataset with absolute time are text, those of
`model` are numbers. The fifth writes `csv` to the file `datasets.csv`
instead of the standard output and shows the file.

=== "Command line"

    ```sh
    t.list format=csv columns=name,start_time,end_time mapset=.
    ```

    ```text
    name,start_time,end_time
    rain,2026-06-01 00:00:00,2026-06-03 00:00:00
    temperature,2026-03-01 00:00:00,2026-03-04 00:00:00
    model,0,12
    ```

    ```sh
    t.list -c columns=name,number_of_maps separator=";" mapset=.
    ```

    ```text
    name;number_of_maps
    rain;2
    temperature;3
    model;2
    ```

    ```sh
    t.list format=line columns=name mapset=.
    ```

    ```text
    rain,temperature,model
    ```

    ```sh
    t.list format=json columns=name,number_of_maps,start_time,granularity \
        where="name IN ('temperature', 'model')" mapset=.
    ```

    ```text
    [
        {
            "name": "temperature",
            "number_of_maps": 3,
            "start_time": "2026-03-01 00:00:00",
            "granularity": "1 day"
        },
        {
            "name": "model",
            "number_of_maps": 2,
            "start_time": 0,
            "granularity": 6
        }
    ]
    ```

    ```sh
    t.list format=csv columns=name,number_of_maps output=datasets.csv mapset=.
    cat datasets.csv
    ```

    ```text
    name,number_of_maps
    rain,2
    temperature,3
    model,2
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_list(format="csv", columns="name,start_time,end_time", mapset=".").text)
    ```

    ```text
    name,start_time,end_time
    rain,2026-06-01 00:00:00,2026-06-03 00:00:00
    temperature,2026-03-01 00:00:00,2026-03-04 00:00:00
    model,0,12
    ```

    ```python
    result = tools.t_list(
        columns="name,number_of_maps", separator=";", flags="c", mapset="."
    )
    print(result.text)
    ```

    ```text
    name;number_of_maps
    rain;2
    temperature;3
    model;2
    ```

    ```python
    print(tools.t_list(format="line", columns="name", mapset=".").text)
    ```

    ```text
    rain,temperature,model
    ```

    ```python
    import json

    result = tools.t_list(
        format="json",
        columns="name,number_of_maps,start_time,granularity",
        where="name IN ('temperature', 'model')",
        mapset=".",
    )
    print(json.dumps(result.json, indent=4))
    ```

    ```text
    [
        {
            "name": "temperature",
            "number_of_maps": 3,
            "start_time": "2026-03-01 00:00:00",
            "granularity": "1 day"
        },
        {
            "name": "model",
            "number_of_maps": 2,
            "start_time": 0,
            "granularity": 6
        }
    ]
    ```

    ```python
    from pathlib import Path

    tools.t_list(
        format="csv", columns="name,number_of_maps", output="datasets.csv", mapset="."
    )
    print(Path("datasets.csv").read_text(), end="")
    ```

    ```text
    name,number_of_maps
    rain,2
    temperature,3
    model,2
    ```

### Inspect all columns of a type

With `columns=all`, the flag **-c** and a condition that no dataset meets, the
listing consists of the column names of the type alone. The first block does it
for every type; the columns of the temporal database differ by type.

The second block lists some of the further columns of the datasets
`temperature` and `model` with the format `json`, whose default columns are
`all`. The extent in the third dimension is 0 for these raster maps. The
smallest value of the dataset `temperature` is -2, in `temperature_1`, so
`min_min` is -2, its largest minimum is that of `temperature_3`, 4: `min_max`.
The largest maximum is the 6 of `temperature_3`, the smallest one the 0 of
`temperature_1`. The key `unit` exists only for the dataset with relative time.

=== "Command line"

    ```sh
    for kind in strds str3ds stvds raster raster_3d vector; do
        t.list type=$kind columns=all -c where="name = 'none'" mapset=.
    done
    ```

    ```text
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|raster_register|number_of_maps|nsres_min|ewres_min|nsres_max|ewres_max|min_min|min_max|max_min|max_max|aggregation_type|number_of_semantic_labels|title|description|command
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|raster3d_register|number_of_maps|nsres_min|ewres_min|nsres_max|ewres_max|tbres_min|tbres_max|min_min|min_max|max_min|max_max|aggregation_type|title|description|command
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|vector_register|number_of_maps|title|description|command|points|lines|boundaries|centroids|faces|kernels|primitives|nodes|areas|islands|holes|volumes
    id|mapset|name|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|datatype|cols|rows|nsres|ewres|min|max|number_of_cells|semantic_label|registered_stds
    id|mapset|name|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|datatype|cols|rows|depths|nsres|ewres|tbres|min|max|number_of_cells|registered_stds
    id|mapset|name|layer|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|is_3d|points|lines|boundaries|centroids|faces|kernels|primitives|nodes|areas|islands|holes|volumes|registered_stds
    ```

    ```sh
    t.list format=json where="name IN ('temperature', 'model')" mapset=. |
        grep -E '"(name|temporal_type|unit|bottom|top|nsres_min|min_min|min_max|max_min|max_max)"'
    ```

    ```text
            "name": "temperature",
            "temporal_type": "absolute",
            "bottom": 0.0,
            "top": 0.0,
            "nsres_min": 1000.0,
            "min_min": -2.0,
            "min_max": 4.0,
            "max_min": 0.0,
            "max_max": 6.0,
            "name": "model",
            "temporal_type": "relative",
            "unit": "hours",
            "bottom": 0.0,
            "top": 0.0,
            "nsres_min": 1000.0,
            "min_min": 1.0,
            "min_max": 2.0,
            "max_min": 1.0,
            "max_max": 2.0,
    ```

=== "Python (grass.tools)"

    ```python
    for kind in ("strds", "str3ds", "stvds", "raster", "raster_3d", "vector"):
        result = tools.t_list(
            type=kind, columns="all", flags="c", where="name = 'none'", mapset="."
        )
        print(result.text)
    ```

    ```text
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|raster_register|number_of_maps|nsres_min|ewres_min|nsres_max|ewres_max|min_min|min_max|max_min|max_max|aggregation_type|number_of_semantic_labels|title|description|command
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|raster3d_register|number_of_maps|nsres_min|ewres_min|nsres_max|ewres_max|tbres_min|tbres_max|min_min|min_max|max_min|max_max|aggregation_type|title|description|command
    id|name|mapset|temporal_type|semantic_type|creation_time|modification_time|creator|start_time|end_time|granularity|north|south|east|west|bottom|top|proj|vector_register|number_of_maps|title|description|command|points|lines|boundaries|centroids|faces|kernels|primitives|nodes|areas|islands|holes|volumes
    id|mapset|name|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|datatype|cols|rows|nsres|ewres|min|max|number_of_cells|semantic_label|registered_stds
    id|mapset|name|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|datatype|cols|rows|depths|nsres|ewres|tbres|min|max|number_of_cells|registered_stds
    id|mapset|name|layer|temporal_type|creation_time|creator|start_time|end_time|north|south|east|west|bottom|top|proj|is_3d|points|lines|boundaries|centroids|faces|kernels|primitives|nodes|areas|islands|holes|volumes|registered_stds
    ```

    ```python
    keys = (
        "name",
        "temporal_type",
        "unit",
        "bottom",
        "top",
        "nsres_min",
        "min_min",
        "min_max",
        "max_min",
        "max_max",
    )
    result = tools.t_list(
        format="json", where="name IN ('temperature', 'model')", mapset="."
    )
    for row in result.json:
        print({key: row[key] for key in keys if key in row})
    ```

    ```text
    {'name': 'temperature', 'temporal_type': 'absolute', 'bottom': 0.0, 'top': 0.0, 'nsres_min': 1000.0, 'min_min': -2.0, 'min_max': 4.0, 'max_min': 0.0, 'max_max': 6.0}
    {'name': 'model', 'temporal_type': 'relative', 'unit': 'hours', 'bottom': 0.0, 'top': 0.0, 'nsres_min': 1000.0, 'min_min': 1.0, 'min_max': 2.0, 'max_min': 1.0, 'max_max': 2.0}
    ```

### List time stamped maps and semantic labels

With `type=raster`, *t.list* lists the maps with a time stamp in the temporal
database, no matter if they are in a dataset. The map `lonely` is registered
with *[t.register](t.register.md)* without a dataset, as a time instance. The
first block lists it with the maps of `rain`, sorted by start time. A map with
a time instance has no end time, which `plain` prints as `None`.

Two further maps carry the semantic labels `S2_B4` and `S2_B8` and form the
dataset `sentinel`. The second block lists the maps with a label, sorted by the
label. The third block shows the number of maps and of labels of the dataset.
The fourth lists the 3D raster and vector maps; their type is added.

=== "Command line"

    ```sh
    r.mapcalc expression="lonely = 7"
    t.register maps=lonely start=2026-07-15
    t.list type=raster columns=name,start_time,end_time \
        where="name LIKE 'rain%' OR name = 'lonely'" order=start_time mapset=.
    ```

    ```text
    rain_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    lonely|2026-07-15 00:00:00|None
    ```

    ```sh
    r.mapcalc expression="red_1 = 0.05"
    r.mapcalc expression="nir_1 = 0.30"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared"
    t.register input=sentinel maps=red_1,nir_1 start="2026-06-01 10:30:00"
    t.list type=raster columns=name,semantic_label,start_time \
        where="semantic_label IS NOT NULL" order=semantic_label mapset=.
    ```

    ```text
    red_1|S2_B4|2026-06-01 10:30:00
    nir_1|S2_B8|2026-06-01 10:30:00
    ```

    ```sh
    t.list -c columns=name,number_of_maps,number_of_semantic_labels \
        where="name = 'sentinel'" mapset=.
    ```

    ```text
    name|number_of_maps|number_of_semantic_labels
    sentinel|2|2
    ```

    ```sh
    t.list type=raster_3d,vector columns=name mapset=.
    ```

    ```text
    soil_1|raster_3d
    soil_2|raster_3d
    gauges_1|vector
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="lonely = 7")
    tools.t_register(maps="lonely", start="2026-07-15")
    result = tools.t_list(
        type="raster",
        columns="name,start_time,end_time",
        where="name LIKE 'rain%' OR name = 'lonely'",
        order="start_time",
        mapset=".",
    )
    print(result.text)
    ```

    ```text
    rain_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    lonely|2026-07-15 00:00:00|None
    ```

    ```python
    tools.r_mapcalc(expression="red_1 = 0.05")
    tools.r_mapcalc(expression="nir_1 = 0.30")
    tools.r_support(map="red_1", semantic_label="S2_B4")
    tools.r_support(map="nir_1", semantic_label="S2_B8")
    tools.t_create(
        output="sentinel",
        title="Reflectance",
        description="Red and near infrared",
    )
    tools.t_register(input="sentinel", maps="red_1,nir_1", start="2026-06-01 10:30:00")
    result = tools.t_list(
        type="raster",
        columns="name,semantic_label,start_time",
        where="semantic_label IS NOT NULL",
        order="semantic_label",
        mapset=".",
    )
    print(result.text)
    ```

    ```text
    red_1|S2_B4|2026-06-01 10:30:00
    nir_1|S2_B8|2026-06-01 10:30:00
    ```

    ```python
    result = tools.t_list(
        columns="name,number_of_maps,number_of_semantic_labels",
        where="name = 'sentinel'",
        flags="c",
        mapset=".",
    )
    print(result.text)
    ```

    ```text
    name|number_of_maps|number_of_semantic_labels
    sentinel|2|2
    ```

    ```python
    print(tools.t_list(type="raster_3d,vector", columns="name", mapset=".").text)
    ```

    ```text
    soil_1|raster_3d
    soil_2|raster_3d
    gauges_1|vector
    ```

### List the datasets of other mapsets

The example creates the mapset `t_list_2` with the dataset `wind` and switches
to it. The first block lists the space time raster datasets of the current
mapset (`mapset=.`), the second those of the mapset `t_list`, which is not in
the search path of the new mapset but can be named all the same.

The third block sets the search path to the current mapset alone with
*[g.mapsets](g.mapsets.md)*. A listing without **mapset** then shows only
`wind`, but `mapset=t_list` still lists the datasets of `t_list`. The fourth
block adds `t_list` to the search path, so that the listing without **mapset**
shows the datasets of both mapsets. The last block lists every mapset of the
project with `mapset='*'`, whether or not it is in the search path, and puts
`PERMANENT` back into the search path.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_list_2
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="wind_1 = 5"
    t.create output=wind title="Wind" description="Wind speed"
    t.register -i input=wind maps=wind_1 start=2026-03-01 increment="1 day"
    t.list mapset=.
    ```

    ```text
    wind@t_list_2
    ```

    ```sh
    t.list mapset=t_list
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```sh
    g.mapsets operation=set mapset=t_list_2
    t.list
    ```

    ```text
    wind@t_list_2
    ```

    ```sh
    t.list mapset=t_list
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```sh
    g.mapsets operation=add mapset=t_list
    t.list
    ```

    ```text
    wind@t_list_2
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```sh
    t.list mapset='*'
    g.mapsets operation=set mapset=t_list_2,PERMANENT
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    wind@t_list_2
    model@t_list
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_list_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.r_mapcalc(expression="wind_1 = 5")
    tools.t_create(output="wind", title="Wind", description="Wind speed")
    tools.t_register(
        input="wind",
        maps="wind_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_list(mapset=".").text)
    ```

    ```text
    wind@t_list_2
    ```

    ```python
    print(tools.t_list(mapset="t_list").text)
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```python
    tools.g_mapsets(operation="set", mapset="t_list_2")
    print(tools.t_list().text)
    ```

    ```text
    wind@t_list_2
    ```

    ```python
    print(tools.t_list(mapset="t_list").text)
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```python
    tools.g_mapsets(operation="add", mapset="t_list")
    print(tools.t_list().text)
    ```

    ```text
    wind@t_list_2
    rain@t_list
    sentinel@t_list
    temperature@t_list
    model@t_list
    ```

    ```python
    print(tools.t_list(mapset="*").text)
    tools.g_mapsets(operation="set", mapset="t_list_2,PERMANENT")
    ```

    ```text
    rain@t_list
    sentinel@t_list
    temperature@t_list
    wind@t_list_2
    model@t_list
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapsets](g.mapsets.md), [t.create](t.create.md),
[t.info](t.info.md), [t.rast.list](t.rast.list.md), [t.rast3d.list](t.rast3d.list.md),
[t.upgrade](t.upgrade.md), [t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
