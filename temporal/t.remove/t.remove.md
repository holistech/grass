## DESCRIPTION

*t.remove* removes space time datasets from the temporal database of the
current mapset. A space time dataset (STRDS, STR3DS or STVDS) is a collection
of time stamped maps; see the
[introduction to temporal data processing](temporalintro.md) for an overview.
*t.remove* is the counterpart of *[t.create](t.create.md)*. By default it
removes only the dataset and leaves its maps alone: they stay in the mapset
and, with their time stamps, in the temporal database, as *[t.list](t.list.md)*
with **type** `raster` shows.

The datasets are named with **inputs**, a comma separated list, or with
**file**, a text file that holds one name per line. Empty lines in the file
are skipped and blanks around a name are ignored. A name may carry its mapset
(`rain@PERMANENT`). The options **inputs** and **file** exclude each other,
and one of them is required.

The option **type** gives the type of all datasets of the call: `strds`
(the default), `str3ds` or `stvds`. A dataset is found by its type and name,
so the call refuses a name that belongs to a dataset of another type.

Nothing is removed without the flag **-f** (force). Without it, *t.remove*
only reports, as messages on the standard error, which datasets it would
remove and, with **-r** or **-d**, the names of their maps, and ends with
the message "Nothing removed. You must use the force flag (-f) to actually
remove them." With **-f**, the flags choose how far the removal goes:

- no further flag: the datasets are removed and their maps are left as they
  are;
- **-r** (recursive): the datasets are removed and their maps are unregistered
  from the temporal database. The maps stay in the mapset, but are no longer
  known to the temporal database and belong to no dataset;
- **-d** (delete): as **-r**, and the maps are also deleted from the mapset,
  with *g.remove*: raster maps for `strds`, 3D raster maps for `str3ds` and
  vector maps for `stvds`. **-d** alone does what **-r** and **-d** together
  do. A vector map with several layers is deleted once.

Only maps of the current mapset are deleted, because GRASS writes to the
current mapset only. For each registered map of another mapset, *t.remove*
with **-d** warns that the map is not removed, and still removes the dataset.

A map can be registered in several datasets. With **-r** or **-d**, a map is
taken out of every dataset that holds it. A dataset that is not removed and
loses maps this way gets its number of maps, time and spatial extent and the
other metadata computed again from the maps that are left; *[t.info](t.info.md)*
shows the new values.

## NOTES

All datasets of a call are opened before the first one is removed. A name that
does not exist stops the run with an error before anything has changed, so
that a call with an unknown name after valid ones removes none of them. The
same holds for a call with both or neither of **inputs** and **file**, for
which the errors are "inputs= and file= are mutually exclusive" and
"inputs= or file= must be specified". A missing **file** is reported as an
error with the file name.

Removing a dataset twice fails the second time with the error that the
dataset does not exist, because the first call removed it.

A dataset is found by its type. A call with the wrong **type** for the name,
such as the default `strds` for a space time 3D raster dataset, stops with an
error like `Space time dataset <soil> of type <strds> not found`; give
**type=str3ds**.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Remove a dataset and keep its maps

Two space time raster datasets hold five maps in all: `rain` has three daily
maps, `snow` two. *t.list* shows both datasets and, with **type** `raster`,
all five maps with their time stamps. After `t.remove -f inputs=rain`, the
second command lists three results: first the datasets, where only `snow` is
left, then the registered maps, where all five are still found, and last the
maps named `rain_*` in the mapset, found with *g.list*.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for name in rain_1 rain_2 rain_3 snow_1 snow_2; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=rain title="Rain" description="Daily rain"
    t.register -i input=rain maps=rain_1,rain_2,rain_3 \
        start=2026-06-01 increment="1 day"
    t.create output=snow title="Snow" description="Daily snow"
    t.register -i input=snow maps=snow_1,snow_2 \
        start=2026-06-01 increment="1 day"
    t.list type=strds columns=name,number_of_maps
    t.list type=raster columns=name,start_time
    ```

    ```text
    rain|3
    snow|2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1|2026-06-01 00:00:00
    snow_2|2026-06-02 00:00:00
    ```

    ```sh
    t.remove -f inputs=rain
    t.list type=strds columns=name,number_of_maps
    t.list type=raster columns=name,start_time
    g.list type=raster pattern="rain_*"
    ```

    ```text
    snow|2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1|2026-06-01 00:00:00
    snow_2|2026-06-02 00:00:00
    rain_1
    rain_2
    rain_3
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for name in ("rain_1", "rain_2", "rain_3", "snow_1", "snow_2"):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="rain", title="Rain", description="Daily rain")
    tools.t_register(
        input="rain",
        maps="rain_1,rain_2,rain_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(output="snow", title="Snow", description="Daily snow")
    tools.t_register(
        input="snow",
        maps="snow_1,snow_2",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.t_list(type="raster", columns="name,start_time").text)
    ```

    ```text
    rain|3
    snow|2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1|2026-06-01 00:00:00
    snow_2|2026-06-02 00:00:00
    ```

    ```python
    tools.t_remove(inputs="rain", flags="f")
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.t_list(type="raster", columns="name,start_time").text)
    print(tools.g_list(type="raster", pattern="rain_*").text)
    ```

    ```text
    snow|2
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1|2026-06-01 00:00:00
    snow_2|2026-06-02 00:00:00
    rain_1
    rain_2
    rain_3
    ```

### Look before removing

Without **-f**, *t.remove* removes nothing, whatever the other flags are. It
names the dataset and, with **-d**, the maps it would delete in messages on
the standard error, which are not shown here. The result is the same as before:
the first line shows that the dataset `snow` still holds two maps, and the
others list the maps of the mapset.

=== "Command line"

    ```sh
    t.remove -d inputs=snow
    t.list type=strds columns=name,number_of_maps
    g.list type=raster pattern="snow_*"
    ```

    ```text
    snow|2
    snow_1
    snow_2
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_remove(inputs="snow", flags="d")
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.g_list(type="raster", pattern="snow_*").text)
    ```

    ```text
    snow|2
    snow_1
    snow_2
    ```

### Unregister the maps with -r

*t.remove* with **-r** and **-f** removes `snow` and unregisters its maps.
They disappear from the list of raster maps of the temporal database, which
shows only the three maps of `rain`, removed without **-r** above. They stay
in the mapset: the last two lines come from *g.list*.

=== "Command line"

    ```sh
    t.remove -rf inputs=snow
    t.list type=raster columns=name,start_time
    g.list type=raster pattern="snow_*"
    ```

    ```text
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1
    snow_2
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_remove(inputs="snow", flags="rf")
    print(tools.t_list(type="raster", columns="name,start_time").text)
    print(tools.g_list(type="raster", pattern="snow_*").text)
    ```

    ```text
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    snow_1
    snow_2
    ```

### Delete the maps with -d and take names from a file

Two new datasets are named in a file, one name per line, with an empty line
between the names, and removed together with their maps. Afterwards *t.list*
shows that only the maps of `rain` are still registered, and *g.list* that the
mapset holds only the maps of `rain` and `snow`.

=== "Command line"

    ```sh
    for name in wet_1 wet_2 dry_1 dry_2; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=wet title="Wet" description="Wet days"
    t.register -i input=wet maps=wet_1,wet_2 start=2026-07-01 increment="1 day"
    t.create output=dry title="Dry" description="Dry days"
    t.register -i input=dry maps=dry_1,dry_2 start=2026-07-01 increment="1 day"
    printf "wet\n\ndry\n" > datasets.txt
    t.remove -df file=datasets.txt
    ```

    ```sh
    t.list type=raster columns=name
    ```

    ```text
    rain_1
    rain_2
    rain_3
    ```

    ```sh
    g.list type=raster
    ```

    ```text
    rain_1
    rain_2
    rain_3
    snow_1
    snow_2
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for name in ("wet_1", "wet_2", "dry_1", "dry_2"):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="wet", title="Wet", description="Wet days")
    tools.t_register(
        input="wet",
        maps="wet_1,wet_2",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(output="dry", title="Dry", description="Dry days")
    tools.t_register(
        input="dry",
        maps="dry_1,dry_2",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    Path("datasets.txt").write_text("wet\n\ndry\n")
    tools.t_remove(file="datasets.txt", flags="df")
    ```

    ```python
    print(tools.t_list(type="raster", columns="name").text)
    ```

    ```text
    rain_1
    rain_2
    rain_3
    ```

    ```python
    print(tools.g_list(type="raster").text)
    ```

    ```text
    rain_1
    rain_2
    rain_3
    snow_1
    snow_2
    ```

### Maps that belong to two datasets

The map `shared_2` is registered in `first` and in `second`. Removing `first`
with **-r** unregisters its maps from `second` too. `second` stays, and
*t.info* shows that it has only one map left, `shared_3`, with its start and
end time computed from that map.

=== "Command line"

    ```sh
    for name in shared_1 shared_2 shared_3; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=first title="First" description="Maps 1 and 2"
    t.register -i input=first maps=shared_1,shared_2 \
        start=2026-08-01 increment="1 day"
    t.create output=second title="Second" description="Maps 2 and 3"
    t.register -i input=second maps=shared_2,shared_3 \
        start=2026-08-02 increment="1 day"
    t.remove -rf inputs=first
    t.info -g input=second | grep -E "^(number_of_maps|start_time|end_time)="
    t.rast.list input=second
    ```

    ```text
    start_time='2026-08-03 00:00:00'
    end_time='2026-08-04 00:00:00'
    number_of_maps=1
    name|mapset|start_time|end_time
    shared_3|PERMANENT|2026-08-03 00:00:00|2026-08-04 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    for name in ("shared_1", "shared_2", "shared_3"):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="first", title="First", description="Maps 1 and 2")
    tools.t_register(
        input="first",
        maps="shared_1,shared_2",
        start="2026-08-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(output="second", title="Second", description="Maps 2 and 3")
    tools.t_register(
        input="second",
        maps="shared_2,shared_3",
        start="2026-08-02",
        increment="1 day",
        flags="i",
    )
    tools.t_remove(inputs="first", flags="rf")
    info = tools.t_info(input="second", flags="g").keyval
    for key in ("start_time", "end_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    print(tools.t_rast_list(input="second").text)
    ```

    ```text
    start_time='2026-08-03 00:00:00'
    end_time='2026-08-04 00:00:00'
    number_of_maps=1
    name|mapset|start_time|end_time
    shared_3|PERMANENT|2026-08-03 00:00:00|2026-08-04 00:00:00
    ```

### Remove datasets of other types

With **type**, *t.remove* works on space time 3D raster datasets and on space
time vector datasets. **-d** then deletes 3D raster maps or vector maps. Here,
a dataset of each type is created and removed with its maps. A copy of
each map, registered in no dataset, shows that *g.list* lists the maps before
the removal and only the copies after it.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 t=3 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    t.create type=str3ds output=soil title="Soil" description="Soil layers"
    t.register -i type=raster_3d input=soil maps=soil_1 \
        start=2026-03-01 increment="1 day"
    v.in.ascii input=- output=gauges_1 separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    0.5,0.5,3.0
    2.5,1.5,5.0
    EOF
    t.create type=stvds output=gauges title="Gauges" description="Wind speed"
    t.register -i type=vector input=gauges maps=gauges_1 \
        start=2026-03-01 increment="1 day"
    g.copy raster_3d=soil_1,soil_copy
    g.copy vector=gauges_1,gauges_copy
    g.list type=raster_3d
    ```

    ```text
    soil_1
    soil_copy
    ```

    ```sh
    g.list type=vector
    ```

    ```text
    gauges_1
    gauges_copy
    ```

    ```sh
    t.remove -df type=str3ds inputs=soil
    t.remove -df type=stvds inputs=gauges
    g.list type=raster_3d
    ```

    ```text
    soil_copy
    ```

    ```sh
    g.list type=vector
    ```

    ```text
    gauges_copy
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(n=2, s=0, e=2, w=0, t=3, b=0, res=1, res3=1, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.t_create(type="str3ds", output="soil", title="Soil", description="Soil layers")
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.v_in_ascii(
        input=StringIO("0.5,0.5,3.0\n2.5,1.5,5.0\n"),
        output="gauges_1",
        separator="comma",
        columns="x double precision, y double precision, speed double precision",
    )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="Wind speed")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.g_copy(raster_3d="soil_1,soil_copy")
    tools.g_copy(vector="gauges_1,gauges_copy")
    print(tools.g_list(type="raster_3d").text)
    ```

    ```text
    soil_1
    soil_copy
    ```

    ```python
    print(tools.g_list(type="vector").text)
    ```

    ```text
    gauges_1
    gauges_copy
    ```

    ```python
    tools.t_remove(type="str3ds", inputs="soil", flags="df")
    tools.t_remove(type="stvds", inputs="gauges", flags="df")
    print(tools.g_list(type="raster_3d").text)
    ```

    ```text
    soil_copy
    ```

    ```python
    print(tools.g_list(type="vector").text)
    ```

    ```text
    gauges_copy
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.remove](g.remove.md), [t.create](t.create.md), [t.info](t.info.md),
[t.list](t.list.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
