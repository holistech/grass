## DESCRIPTION

*t.unregister* unregisters maps from a space time dataset or from the temporal
database. A space time dataset (STRDS, STR3DS or STVDS) is a collection of
time stamped maps; see the
[introduction to temporal data processing](temporalintro.md) for an overview.
*t.unregister* is the counterpart of *[t.register](t.register.md)*. It never
deletes a map from the mapset: only the registration and, without **input**,
the time stamp in the temporal database go away. To remove a dataset, use
*[t.remove](t.remove.md)*.

The maps are named with **maps**, a comma separated list, or with **file**, a
text file that holds one map name per line. Empty lines in the file are
skipped. A name without mapset belongs to the current mapset; a name may
carry its mapset (`rain_1@PERMANENT`). The options **maps** and **file**
exclude each other, and one of them is required; an empty **maps** counts as
missing.

The option **input** decides where the maps are unregistered from:

- with **input**, a space time dataset: the maps are unregistered from this
  dataset only. They keep their time stamps in the temporal database and stay
  registered in every other dataset that holds them. This is the way to take
  a map out of one dataset without affecting the others;
- without **input**: the maps are unregistered from the temporal database.
  Their time stamps are removed, and every dataset that held a map loses it.

Whichever way is used, each dataset that loses maps gets its number of maps,
its time and spatial extent and the other metadata computed again from the
maps that are left; *[t.info](t.info.md)* shows the new values. A dataset that
loses all its maps stays and holds zero maps.

The option **type** gives the type of all maps of the call: `raster` (the
default), `raster_3d` or `vector`. It also selects the type of **input**: a
call with `raster` maps needs a space time raster dataset, one with `raster_3d`
maps a space time 3D raster dataset, and one with `vector` maps a space time
vector dataset. A map is found by its type and name, so a name that belongs to
a map of another type is not found. A layer of a vector map is a map of its
own for the temporal database and is named `map:layer`; the name of the vector
map alone is another map.

## NOTES

All checks of the options come first. A call with both or neither of **maps**
and **file** stops with the error "maps= and file= are mutually exclusive" or
"maps= or file= must be specified", and a missing **file** with the error
`File <name> not found`. A dataset **input** that does not exist, or exists
with another type than the one **type** selects, stops the run with the error
`Space time dataset <name> of type <raster> not found`; the type in the
message is the value of **type**. In none of these cases a map has been
changed.

A map that cannot be unregistered is a warning, not an error, and the other
maps of the call are still unregistered:

- without **input**, a map that is not in the temporal database gives the
  warning `Unable to find raster map <rain_9@PERMANENT> in temporal database`
  (with the type and the full name of the map);
- with **input**, the same warning is given for such a map, and a map that is
  in the temporal database but not registered in the dataset gives
  `Map <rain_1@PERMANENT> is not registered in space time dataset
  <rain@PERMANENT>`. The map stays as it is.

The dataset types of the maps and of **input** must fit. A 3D raster map is
not found as `raster`, and a call with `type=vector` does not find a space
time raster dataset.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_unregister` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.unregister* changes registrations and time stamps only and never
touches a map of the sample dataset, so the maps of the examples hold small
constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_unregister -->

<!-- markdownlint-disable MD046 -->

### Unregister maps from one dataset

The dataset `rain` holds three daily maps of precipitation, 4, 2 and 6 mm in
every cell; `wet` holds the second and the third of them, which keep their
time stamps. *t.unregister* with **input**
`rain` takes `rain_3` out of `rain` only. *t.list* shows that `rain` has two
maps and `wet` still two, and *t.info* that the end of `rain` moved from the
fourth to the third of June, computed from `rain_1` and `rain_2`. The third
command lists the registered raster maps: the time stamps of all three are
still there.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_unregister
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="rain_1 = 4"
    r.mapcalc expression="rain_2 = 2"
    r.mapcalc expression="rain_3 = 6"
    t.create output=rain title="Rain" description="Daily precipitation in mm"
    t.register -i input=rain maps=rain_1,rain_2,rain_3 \
        start=2026-06-01 increment="1 day"
    t.create output=wet title="Wet" description="Wet days, precipitation in mm"
    t.register input=wet maps=rain_2,rain_3
    t.unregister input=rain maps=rain_3
    t.list type=strds columns=name,number_of_maps mapset=.
    t.info -g input=rain | grep -E "^(start_time|end_time|number_of_maps)="
    t.list type=raster columns=name,start_time mapset=.
    ```

    ```text
    rain|2
    wet|2
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-03 00:00:00'
    number_of_maps=2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_unregister")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for name, value in (("rain_1", 4), ("rain_2", 2), ("rain_3", 6)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.t_create(output="rain", title="Rain", description="Daily precipitation in mm")
    tools.t_register(
        input="rain",
        maps="rain_1,rain_2,rain_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(output="wet", title="Wet", description="Wet days, precipitation in mm")
    tools.t_register(input="wet", maps="rain_2,rain_3")
    tools.t_unregister(input="rain", maps="rain_3")
    print(tools.t_list(type="strds", columns="name,number_of_maps", mapset=".").text)
    info = tools.t_info(input="rain", flags="g").keyval
    for key in ("start_time", "end_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    print(tools.t_list(type="raster", columns="name,start_time", mapset=".").text)
    ```

    ```text
    rain|2
    wet|2
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-03 00:00:00'
    number_of_maps=2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    ```

### Unregister maps from the temporal database

Without **input**, the maps leave the temporal database and every dataset that
holds them. Here `rain_2` and `rain_3` are unregistered. `rain` keeps only
`rain_1`, `wet` loses both its maps and stays as an empty dataset, and only
`rain_1` has a time stamp left. The maps themselves are still in the mapset,
as *g.list* shows.

=== "Command line"

    ```sh
    t.unregister maps=rain_2,rain_3
    t.list type=strds columns=name,number_of_maps mapset=.
    t.list type=raster columns=name,start_time mapset=.
    g.list type=raster pattern="rain_*"
    ```

    ```text
    rain|1
    wet|0
    rain_1|2026-06-01 00:00:00
    rain_1
    rain_2
    rain_3
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_unregister(maps="rain_2,rain_3")
    print(tools.t_list(type="strds", columns="name,number_of_maps", mapset=".").text)
    print(tools.t_list(type="raster", columns="name,start_time", mapset=".").text)
    print(tools.g_list(type="raster", pattern="rain_*").text)
    ```

    ```text
    rain|1
    wet|0
    rain_1|2026-06-01 00:00:00
    rain_1
    rain_2
    rain_3
    ```

### Take the map names from a file

The file `dry.txt` names two of the three maps of the new dataset `dry`, which
holds the precipitation of dry days, 0 mm in every cell, with an empty line
between the names. First, **file** is combined with **input**:
the two maps leave `dry`, which keeps one map, but all three maps keep their
time stamps. Then the same file without **input** removes the time stamps of
the two maps.

=== "Command line"

    ```sh
    for name in dry_1 dry_2 dry_3; do
        r.mapcalc expression="$name = 0"
    done
    t.create output=dry title="Dry" description="Dry days, precipitation in mm"
    t.register -i input=dry maps=dry_1,dry_2,dry_3 \
        start=2026-07-01 increment="1 day"
    printf "dry_1\n\ndry_2\n" > dry.txt
    t.unregister input=dry file=dry.txt
    t.list type=strds columns=name,number_of_maps where="name = 'dry'" mapset=.
    t.list type=raster columns=name where="name like 'dry_%'" mapset=.
    ```

    ```text
    dry|1
    dry_1
    dry_2
    dry_3
    ```

    ```sh
    t.unregister file=dry.txt
    t.list type=raster columns=name where="name like 'dry_%'" mapset=.
    ```

    ```text
    dry_3
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for name in ("dry_1", "dry_2", "dry_3"):
        tools.r_mapcalc(expression=f"{name} = 0")
    tools.t_create(output="dry", title="Dry", description="Dry days, precipitation in mm")
    tools.t_register(
        input="dry",
        maps="dry_1,dry_2,dry_3",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    Path("dry.txt").write_text("dry_1\n\ndry_2\n")
    tools.t_unregister(input="dry", file="dry.txt")
    print(
        tools.t_list(
            type="strds",
            columns="name,number_of_maps",
            where="name = 'dry'",
            mapset=".",
        ).text
    )
    print(
        tools.t_list(
            type="raster", columns="name", where="name like 'dry_%'", mapset="."
        ).text
    )
    ```

    ```text
    dry|1
    dry_1
    dry_2
    dry_3
    ```

    ```python
    tools.t_unregister(file="dry.txt")
    print(
        tools.t_list(
            type="raster", columns="name", where="name like 'dry_%'", mapset="."
        ).text
    )
    ```

    ```text
    dry_3
    ```

### Datasets of relative time

Maps of a dataset with relative time are unregistered in the same way. The
dataset `runoff` holds three maps of simulated runoff in mm, 1, 2 and 3 mm in
every cell, of one model hour each, from hour 0 to hour 3. After the first map
has left it, the dataset starts at hour 1.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2,runoff_3 \
        start=0 increment=1 unit=hours
    t.unregister input=runoff maps=runoff_1
    t.rast.list input=runoff
    t.info -g input=runoff | grep -E "^(start_time|end_time|number_of_maps)="
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_2|t_unregister|1|2
    runoff_3|t_unregister|2|3
    start_time='1'
    end_time='3'
    number_of_maps=2
    ```

=== "Python (grass.tools)"

    ```python
    for step in (1, 2, 3):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    tools.t_register(
        input="runoff",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_unregister(input="runoff", maps="runoff_1")
    print(tools.t_rast_list(input="runoff").text)
    info = tools.t_info(input="runoff", flags="g").keyval
    for key in ("start_time", "end_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|mapset|start_time|end_time
    runoff_2|t_unregister|1|2
    runoff_3|t_unregister|2|3
    start_time='1'
    end_time='3'
    number_of_maps=2
    ```

### Unregister 3D raster maps and vector maps

With **type**, the maps are 3D raster maps or vector maps, and **input** is a
space time 3D raster dataset or a space time vector dataset. The 3D raster map
`soil_1` (soil temperature in degrees Celsius, 3 layers of 1 km) leaves its
dataset `soil` and keeps its time stamp. The vector map `gauges_1`, two wind
gauges with the speed in m/s, is unregistered from the temporal database, so
that it is no longer registered in `gauges` and has no time stamp.

=== "Command line"

    ```sh
    g.region raster=elev_state_500m res=1000 -a
    g.region t=3 b=0 res3=1000 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" description="Soil layers"
    t.register -i type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2026-03-01 increment="1 day"
    v.in.ascii input=- output=gauges_1 separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    400000,100000,3.0
    700000,200000,5.0
    EOF
    g.copy vector=gauges_1,gauges_2
    t.create type=stvds output=gauges title="Gauges" description="Wind speed"
    t.register -i type=vector input=gauges maps=gauges_1,gauges_2 \
        start=2026-03-01 increment="1 day"
    t.unregister type=raster_3d input=soil maps=soil_1
    t.unregister type=vector maps=gauges_1
    t.list type=str3ds columns=name,number_of_maps mapset=.
    t.list type=raster_3d columns=name,start_time mapset=.
    t.list type=stvds columns=name,number_of_maps mapset=.
    t.list type=vector columns=name,start_time mapset=.
    g.list type=vector pattern="gauges_*"
    ```

    ```text
    soil|1
    soil_1|2026-03-01 00:00:00
    soil_2|2026-03-02 00:00:00
    gauges|1
    gauges_2|2026-03-02 00:00:00
    gauges_1
    gauges_2
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_region(t=3, b=0, res3=1000, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(type="str3ds", output="soil", title="Soil", description="Soil layers")
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.v_in_ascii(
        input=StringIO("400000,100000,3.0\n700000,200000,5.0\n"),
        output="gauges_1",
        separator="comma",
        columns="x double precision, y double precision, speed double precision",
    )
    tools.g_copy(vector="gauges_1,gauges_2")
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="Wind speed")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_unregister(type="raster_3d", input="soil", maps="soil_1")
    tools.t_unregister(type="vector", maps="gauges_1")
    print(tools.t_list(type="str3ds", columns="name,number_of_maps", mapset=".").text)
    print(tools.t_list(type="raster_3d", columns="name,start_time", mapset=".").text)
    print(tools.t_list(type="stvds", columns="name,number_of_maps", mapset=".").text)
    print(tools.t_list(type="vector", columns="name,start_time", mapset=".").text)
    print(tools.g_list(type="vector", pattern="gauges_*").text)
    ```

    ```text
    soil|1
    soil_1|2026-03-01 00:00:00
    soil_2|2026-03-02 00:00:00
    gauges|1
    gauges_2|2026-03-02 00:00:00
    gauges_1
    gauges_2
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.create](t.create.md), [t.info](t.info.md), [t.list](t.list.md),
[t.register](t.register.md), [t.remove](t.remove.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
