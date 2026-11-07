## DESCRIPTION

*t.create* creates a new, empty space time dataset in the temporal database
of the current mapset. A space time dataset collects time stamped maps of one
type and is the input and output of most temporal tools. *t.create* is
usually the first step of a temporal workflow: the dataset is created here,
maps are added with *[t.register](t.register.md)*, and the other tools work
on the dataset from then on. See the
[introduction to temporal data processing](temporalintro.md) for an overview.

The option **type** chooses what the dataset collects:

- `strds`, a space time raster dataset, holds raster maps (the default);
- `str3ds`, a space time 3D raster dataset, holds 3D raster maps;
- `stvds`, a space time vector dataset, holds vector maps.

The option **temporaltype** sets how the maps of the dataset are placed in
time. No tool changes it later; the only way is to replace the dataset with
**--overwrite**:

- `absolute` (the default) means calendar time: a map has a date and time,
  such as `2026-06-01 00:00:00`, as a time instance or as the start and end
  of an interval;
- `relative` means a number of time units counted from an arbitrary start,
  such as model step 3. The unit (`years`, `months`, `days`, `hours`,
  `minutes` or `seconds`) is not set by *t.create*, but by the first
  registration of maps with *t.register*: from its option **unit**, or,
  without it, from the relative time the maps carry already, such as a time
  stamp `date="5 days"` set with *r.timestamp* or the time of an earlier
  registration. If neither gives a unit, *t.register* stops with an
  error.

A dataset holds maps of its own temporal type: *t.register* refuses, for
instance, to add a map with relative time to a dataset with absolute time.

The option **semantictype** states how the values of the maps are to be
understood: `sum` for amounts, such as precipitation sums, `mean` for mean
values (the default), `min` or `max` for extremes. The temporal tools store
this label, print it with *[t.info](t.info.md)* and *[t.list](t.list.md)*,
and tools that derive a new dataset from an existing one, such as
*[t.copy](t.copy.md)* and *[t.rast.aggregate](t.rast.aggregate.md)*, take it
over. No tool computes with it; it is information for the user.
*[t.support](t.support.md)* changes it later.

The options **title** and **description** are required. The title is a short
name for the dataset, the description can say what the maps show, where they
come from and how they were made. *t.info* prints both, together with the
command history, which starts with the *t.create* command.

The option **output** names the new dataset. If a dataset of this type with
this name exists already, *t.create* stops with an error unless
**--overwrite** is given (see NOTES).

## NOTES

The name of a space time dataset follows the rules for map names: it must not
be empty, and it must not contain a space, a slash, a quotation mark, an
apostrophe, `@`, a comma, `=`, `*` or `~`. The name of a new space time
dataset of any type must not contain a dot either: in the input of the other
temporal tools, the part of a raster dataset name after a dot is a semantic
label (`input=prec.label`). *t.create* stops with an error for such a name
and creates nothing; for `output=prec.label` the error is
`<prec.label> is not a valid name for a new space time dataset: a dot is not allowed`.

A space time dataset is always created in the current mapset. The name may
carry the current mapset (`output=precipitation@PERMANENT` in the mapset
`PERMANENT`); with any other mapset *t.create* stops with the error "Space
time datasets can only be created in the current mapset".

If a dataset of the same type and name exists, *t.create* stops with an
error that points to the overwrite flag and leaves the dataset as it is. With
**--overwrite**, *t.create* warns that it overwrites the dataset and
unregisters all its maps, removes the old dataset and creates a new, empty
one with the given options. The maps of the old dataset are not removed:
they stay in the mapset and in the temporal database with their time stamps,
but no longer belong to the dataset. To remove a dataset together with its
maps, use *[t.remove](t.remove.md)* with the flags **-d** and **-f**.

A new dataset has no start and end time, no spatial extent and no map count;
*t.info* prints `None` for them. They follow from the maps once maps are
registered.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_create` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.create* only creates datasets, so the one example with maps uses
small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_create -->

<!-- markdownlint-disable MD046 -->

### Create a space time raster dataset

A space time raster dataset for daily precipitation sums. The values of the
maps are amounts, so the semantic type is `sum`.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_create
    g.region raster=elev_state_500m res=1000 -a
    t.create output=precipitation type=strds temporaltype=absolute \
        semantictype=sum title="Daily precipitation" \
        description="Daily precipitation sums in millimeters"
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_create")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_create(
        output="precipitation",
        type="strds",
        temporaltype="absolute",
        semantictype="sum",
        title="Daily precipitation",
        description="Daily precipitation sums in millimeters",
    )
    ```

### Look at the new dataset

*t.info* shows what *t.create* stored. Time, extent and the number of maps
are still `None`, because the dataset holds no maps yet. In Python, the
attribute `stdout` of the result holds the text as the tool printed it.

=== "Command line"

    ```sh
    t.info input=precipitation
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ precipitation@t_create
     | Name: ...................... precipitation
     | Mapset: .................... t_create
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. sum
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. None
     | End time:................... None
     | Granularity:................ None
     | Temporal type of maps:...... None
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... None
     | South:...................... None
     | East:....................... None
     | West:....................... None
     | Top:........................ None
     | Bottom:..................... None
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. None
     | North-South resolution max:. None
     | East-west resolution min:... None
     | East-west resolution max:... None
     | Minimum value min:.......... None
     | Minimum value max:.......... None
     | Maximum value min:.......... None
     | Maximum value max:.......... None
     | Aggregation type:........... None
     | Number of semantic labels:.. None
     | Semantic labels:............ None
     | Number of registered maps:.. None
     |
     | Title:
     | Daily precipitation
     | Description:
     | Daily precipitation sums in millimeters
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="precipitation" type="strds"
     |     temporaltype="absolute" semantictype="sum" title="Daily precipitation"
     |     description="Daily precipitation sums in millimeters"
     | 
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_info(input="precipitation").stdout, end="")
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ precipitation@t_create
     | Name: ...................... precipitation
     | Mapset: .................... t_create
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. sum
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. None
     | End time:................... None
     | Granularity:................ None
     | Temporal type of maps:...... None
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... None
     | South:...................... None
     | East:....................... None
     | West:....................... None
     | Top:........................ None
     | Bottom:..................... None
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. None
     | North-South resolution max:. None
     | East-west resolution min:... None
     | East-west resolution max:... None
     | Minimum value min:.......... None
     | Minimum value max:.......... None
     | Maximum value min:.......... None
     | Maximum value max:.......... None
     | Aggregation type:........... None
     | Number of semantic labels:.. None
     | Semantic labels:............ None
     | Number of registered maps:.. None
     |
     | Title:
     | Daily precipitation
     | Description:
     | Daily precipitation sums in millimeters
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="precipitation" type="strds"
     |     temporaltype="absolute" semantictype="sum" title="Daily precipitation"
     |     description="Daily precipitation sums in millimeters"
     | 
     +----------------------------------------------------------------------------+
    ```

### Rely on the default values

Without **type**, **temporaltype** and **semantictype**, *t.create* creates a
space time raster dataset with absolute time and the semantic type `mean`.
The flag **-g** of *t.info* prints `key=value` lines; in Python, the
attribute `keyval` of the result turns them into a dictionary.

=== "Command line"

    ```sh
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature at 2 m above ground"
    t.info -g input=temperature | grep -E "^(temporal_type|semantic_type)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature at 2 m above ground",
    )
    info = tools.t_info(input="temperature", flags="g").keyval
    for key in ("temporal_type", "semantic_type"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    ```

### Create a space time 3D raster dataset

A space time 3D raster dataset for the daily minimum of the soil temperature
at several depths; the semantic type `min` marks the values as minima.

=== "Command line"

    ```sh
    t.create output=soil_temperature type=str3ds semantictype=min \
        title="Soil temperature" \
        description="Daily minimum soil temperature in 3D layers"
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(
        output="soil_temperature",
        type="str3ds",
        semantictype="min",
        title="Soil temperature",
        description="Daily minimum soil temperature in 3D layers",
    )
    ```

### Create a space time vector dataset with relative time

Model results counted in steps rather than in calendar time get a dataset
with relative time. Here, the points of a vector map hold the maximum wind
speed of each step. The time unit of the dataset stays unset (`None`) until
the first maps are registered.

=== "Command line"

    ```sh
    t.create output=wind_gauges type=stvds temporaltype=relative \
        semantictype=max title="Simulated wind gauges" \
        description="Maximum wind speed per model step at the gauge points"
    t.info -g type=stvds input=wind_gauges | grep -E "^(temporal_type|unit)="
    ```

    ```text
    temporal_type=relative
    unit=None
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(
        output="wind_gauges",
        type="stvds",
        temporaltype="relative",
        semantictype="max",
        title="Simulated wind gauges",
        description="Maximum wind speed per model step at the gauge points",
    )
    info = tools.t_info(type="stvds", input="wind_gauges", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=relative
    unit=None
    ```

### List the datasets of all types

*t.list* lists the datasets made in the examples above, with their semantic
types; the column `type` comes last.

=== "Command line"

    ```sh
    t.list -c type=strds,str3ds,stvds columns=name,semantic_type
    ```

    ```text
    name|semantic_type|type
    precipitation|sum|strds
    temperature|mean|strds
    soil_temperature|min|str3ds
    wind_gauges|max|stvds
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_list(
        type="strds,str3ds,stvds", columns="name,semantic_type", flags="c"
    )
    print(result.text)
    ```

    ```text
    name|semantic_type|type
    precipitation|sum|strds
    temperature|mean|strds
    soil_temperature|min|str3ds
    wind_gauges|max|stvds
    ```

### Replace a dataset with --overwrite

Two raster maps of North Carolina, with 4.5 and 0.5 millimeters of rain in
every cell, are registered as daily intervals in the dataset
`precipitation` of the first example. *t.create* with **--overwrite** then
replaces the dataset with a new, empty one. The maps are no longer part of
it, but they stay in the temporal database with their time stamps, as
*t.list* with **type** `raster` shows.

=== "Command line"

    ```sh
    r.mapcalc expression="rain_june_1 = 4.5"
    r.mapcalc expression="rain_june_2 = 0.5"
    t.register -i input=precipitation maps=rain_june_1,rain_june_2 \
        start=2026-06-01 increment="1 day"
    t.rast.list input=precipitation
    ```

    ```text
    name|mapset|start_time|end_time
    rain_june_1|t_create|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_june_2|t_create|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

    ```sh
    t.create --overwrite output=precipitation semantictype=sum \
        title="Daily precipitation" \
        description="Daily precipitation sums in millimeters, second run"
    t.info -g input=precipitation | grep number_of_maps
    t.list -c type=raster columns=name,start_time,end_time
    ```

    ```text
    number_of_maps=None
    name|start_time|end_time
    rain_june_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_june_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="rain_june_1 = 4.5")
    tools.r_mapcalc(expression="rain_june_2 = 0.5")
    tools.t_register(
        input="precipitation",
        maps="rain_june_1,rain_june_2",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast_list(input="precipitation").text)
    ```

    ```text
    name|mapset|start_time|end_time
    rain_june_1|t_create|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_june_2|t_create|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

    ```python
    tools.t_create(
        output="precipitation",
        semantictype="sum",
        title="Daily precipitation",
        description="Daily precipitation sums in millimeters, second run",
        overwrite=True,
    )
    info = tools.t_info(input="precipitation", flags="g").keyval
    print(f"number_of_maps={info['number_of_maps']}")
    result = tools.t_list(type="raster", columns="name,start_time,end_time", flags="c")
    print(result.text)
    ```

    ```text
    number_of_maps=None
    name|start_time|end_time
    rain_june_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_june_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.info](t.info.md), [t.list](t.list.md), [t.register](t.register.md),
[t.remove](t.remove.md), [t.support](t.support.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
