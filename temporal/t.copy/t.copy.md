## DESCRIPTION

*t.copy* creates a copy of a space time dataset (STRDS, STR3DS or STVDS; see
the [introduction to temporal data processing](temporalintro.md)). The copy
has the title, the description, the temporal type and the semantic type of the
original and holds the same maps with the same time stamps. The original is
not changed. The copy is a new dataset in the temporal database of the current
mapset, whereas the original can be in another mapset of the project, named
with its mapset (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)).

The option **input** names the dataset to copy, **output** the new dataset,
and **type** their type: `strds` (the default), `str3ds` or `stvds`. A dataset
is found by its type and name. An **input** without a mapset is searched in the
mapsets of the search path; a mapset in the name (`rain@PERMANENT`) is needed
if datasets of that name exist in several mapsets or if the mapset is not in
the search path. The mapset of **output** can be left out. If it is given, it
must be the current mapset.

By default, *t.copy* copies the entries of the dataset only. The maps
themselves are not copied, so that each map belongs to the original and to the
copy. With the flag **-c** the maps of the original are copied as well. They
get the same names in the current mapset and the same time stamps, and, for
raster maps, the same semantic label; the copy then holds these new maps.
*t.copy* copies raster maps for `strds`, 3D raster maps for `str3ds` and vector
maps for `stvds`, with *g.copy*. Only maps of other mapsets are copied: a map
that is in the current mapset already is not copied, and the copy refers to it,
as it does without **-c**.

The standard flag **--overwrite** replaces an existing dataset of the name
**output**; see the notes below for what happens to its maps. Without it, an
existing **output** stops the call. It does not lift the refusal of **-c** when
a map of the current mapset has the name of a map to copy; see the notes.

*[t.rast.extract](t.rast.extract.md)*, *[t.rast3d.extract](t.rast3d.extract.md)*
and *[t.vect.extract](t.vect.extract.md)* copy a selection of the maps into a
new dataset.

## NOTES

All checks are made before the first map is copied: the name of the new
dataset, an existing dataset of that name and, with **-c**, the maps that would
be copied. A refused call leaves no copied maps behind. With **-c**, a map of
the original that has the name of a map in the current mapset stops the call
with an error such as `A raster map <rain_1> exists already in the current
mapset <t_copy_2>`. **--overwrite** does not lift this refusal: it concerns the
output dataset and the entries of the temporal database, not the maps of the
mapset. The call with **--overwrite** fails in the same way, so that repeating
a call with **-c** needs the maps removed first, as the last block of the
fourth example shows (or a call without **-c**).

The name of the new dataset must not contain a dot; *t.copy* stops with an
error before anything is copied. The mapset of **output** must be the current
mapset; a call with another mapset stops with the error that the output
dataset must be in the current mapset.

An existing **output** without **--overwrite** stops with the error that the
dataset is already in the database. With **--overwrite**, the old dataset is
replaced and its maps are unregistered from it. They stay in the mapset and in
the temporal database with their time stamps, as the second example shows.

A dataset without maps is not copied. *t.copy* warns that there is nothing to
copy, creates no new dataset and ends without an error.

If all maps of the original are in the current mapset, **-c** copies nothing.
The call stops with the error that a map is already in the temporal database;
with **--overwrite** it succeeds and the copy refers to the maps of the original.

A dataset that does not exist stops *t.copy* with an error such as `Space time
dataset <nope> of type <strds> not found`. A dataset of another type is not
found either: give **type=str3ds** or **type=stvds** for 3D raster and vector
datasets.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_copy` and sets the computational region to North
Carolina with cells of 1 km; the later examples work in this mapset and region.
*t.copy* copies entries and time stamps only, so the maps hold small constant
values. The listings name the mapset `.` so that only the temporal database of
the current mapset is read.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_copy -->

<!-- markdownlint-disable MD046 -->

### Copy a dataset and share its maps

The dataset `rain` holds three daily maps of rain in millimeters, 4, 6 and 2
in every cell, and has the semantic type `sum`. The first command copies it to
`rain_copy`. *t.list* then shows both datasets with three maps each and the same
semantic type, and *t.rast.list* lists the maps of the copy. *t.info* shows with
**-g** that the map `rain_2` belongs to both datasets.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_copy
    g.region raster=elev_state_500m res=1000 -a
    r.mapcalc expression="rain_1 = 4"
    r.mapcalc expression="rain_2 = 6"
    r.mapcalc expression="rain_3 = 2"
    t.create output=rain title="Daily rain" \
        description="Rain per day in millimeters" semantictype=sum
    t.register -i input=rain maps=rain_1,rain_2,rain_3 \
        start=2026-06-01 increment="1 day"
    t.copy input=rain output=rain_copy
    t.list type=strds mapset=. columns=name,number_of_maps,semantic_type
    t.rast.list input=rain_copy columns=name,mapset,start_time
    t.info -g type=raster input=rain_2 | grep registered_datasets
    ```

    ```text
    rain|3|sum
    rain_copy|3|sum
    name|mapset|start_time
    rain_1|t_copy|2026-06-01 00:00:00
    rain_2|t_copy|2026-06-02 00:00:00
    rain_3|t_copy|2026-06-03 00:00:00
    registered_datasets=rain@t_copy,rain_copy@t_copy
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_copy")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for name, value in (("rain_1", 4), ("rain_2", 6), ("rain_3", 2)):
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.t_create(
        output="rain",
        title="Daily rain",
        description="Rain per day in millimeters",
        semantictype="sum",
    )
    tools.t_register(
        input="rain",
        maps="rain_1,rain_2,rain_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_copy(input="rain", output="rain_copy")
    print(
        tools.t_list(
            type="strds", mapset=".", columns="name,number_of_maps,semantic_type"
        ).text
    )
    print(tools.t_rast_list(input="rain_copy", columns="name,mapset,start_time").text)
    info = tools.t_info(type="raster", input="rain_2", flags="g").keyval
    print(f"registered_datasets={info['registered_datasets']}")
    ```

    ```text
    rain|3|sum
    rain_copy|3|sum
    name|mapset|start_time
    rain_1|t_copy|2026-06-01 00:00:00
    rain_2|t_copy|2026-06-02 00:00:00
    rain_3|t_copy|2026-06-03 00:00:00
    registered_datasets=rain@t_copy,rain_copy@t_copy
    ```

### Replace an existing dataset

The dataset `old` holds the map `old_1`. Copying `rain` to `old` without
**--overwrite** fails because `old` exists, so the example uses **--overwrite**.
The warning that *t.copy* prints on the standard error says that all maps of
`old` are unregistered. Afterwards the first listing shows `old` with the three
maps of `rain`, next to `rain` and `rain_copy`. The second listing still finds
`old_1` with its time stamp: the map stays in the mapset and in the temporal
database, but belongs to no dataset.

This example continues with the data of the previous one.

=== "Command line"

    ```sh
    r.mapcalc expression="old_1 = 1"
    t.create output=old title="Old" description="Replaced by a copy"
    t.register input=old maps=old_1 start=2026-01-01
    t.copy --overwrite input=rain output=old
    t.list type=strds mapset=. columns=name,number_of_maps
    t.list type=raster mapset=. columns=name,start_time
    ```

    ```text
    old|3
    rain|3
    rain_copy|3
    old_1|2026-01-01 00:00:00
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="old_1 = 1")
    tools.t_create(output="old", title="Old", description="Replaced by a copy")
    tools.t_register(input="old", maps="old_1", start="2026-01-01")
    tools.t_copy(input="rain", output="old", overwrite=True)
    print(tools.t_list(type="strds", mapset=".", columns="name,number_of_maps").text)
    print(tools.t_list(type="raster", mapset=".", columns="name,start_time").text)
    ```

    ```text
    old|3
    rain|3
    rain_copy|3
    old_1|2026-01-01 00:00:00
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    ```

### Copy a 3D raster or a vector dataset

The option **type** gives the type of the dataset, here a space time 3D raster
dataset `soil` and a space time vector dataset `gauges`. The copies hold the
maps of the originals. The 3D map holds the number of its layer, 1 to 3, in
every cell. The two gauges lie in North Carolina and have a generated
discharge in cubic meters per second, not a measurement.

=== "Command line"

    ```sh
    g.region t=3 b=0 res3=1000 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    t.create type=str3ds output=soil title="Soil" description="Soil layers"
    t.register -i type=raster_3d input=soil maps=soil_1 \
        start=2026-03-01 increment="1 day"
    t.copy type=str3ds input=soil output=soil_copy
    t.rast3d.list input=soil_copy columns=name,start_time
    v.in.ascii input=- output=gauges_1 separator=comma \
        columns="x double precision, y double precision, discharge double precision" <<EOF
    638000,220000,3.0
    780000,150000,5.0
    EOF
    t.create type=stvds output=gauges title="Gauges" description="Discharge"
    t.register -i type=vector input=gauges maps=gauges_1 \
        start=2026-03-01 increment="1 day"
    t.copy type=stvds input=gauges output=gauges_copy
    t.vect.list input=gauges_copy columns=name,start_time
    ```

    ```text
    name|start_time
    soil_1|2026-03-01 00:00:00
    name|start_time
    gauges_1|2026-03-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(t=3, b=0, res3=1000, tbres=1)
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
    tools.t_copy(type="str3ds", input="soil", output="soil_copy")
    print(tools.t_rast3d_list(input="soil_copy", columns="name,start_time").text)
    tools.v_in_ascii(
        input=StringIO("638000,220000,3.0\n780000,150000,5.0\n"),
        output="gauges_1",
        separator="comma",
        columns="x double precision, y double precision, discharge double precision",
    )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="Discharge")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_copy(type="stvds", input="gauges", output="gauges_copy")
    print(tools.t_vect_list(input="gauges_copy", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    soil_1|2026-03-01 00:00:00
    name|start_time
    gauges_1|2026-03-01 00:00:00
    ```

### Copy a dataset of another mapset

The example creates the mapset `t_copy_2`, sets the region again and adds the
mapset `t_copy` to the search path with *g.mapsets*, so that *t.copy* finds the
dataset `rain` without naming the mapset: a name without a mapset is searched
in the current mapset and then in the search path (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)). The
later commands name `rain@t_copy` and would work without it. The first command
copies the dataset to `rain_linked` without **-c**: the maps of the copy are
still the maps of `t_copy`, as the column `mapset` shows. The second command
copies the dataset with **-c** to `rain_own`: the copy holds new maps with the
same names in the mapset `t_copy_2`, and the maps of `rain` in `t_copy` are as
they were. *g.list* shows the new maps in `t_copy_2`. The third command repeats
the call with **--overwrite**: it fails, because the maps `rain_1` to `rain_3`
exist in `t_copy_2` now. After *g.remove* has removed them, the call with
**--overwrite** replaces `rain_own` and copies the maps again.

This example continues with the data of the first one.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_copy_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_copy operation=add
    t.copy input=rain output=rain_linked
    t.rast.list input=rain_linked columns=name,mapset
    ```

    ```text
    name|mapset
    rain_1|t_copy
    rain_2|t_copy
    rain_3|t_copy
    ```

    ```sh
    t.copy -c input=rain@t_copy output=rain_own
    t.rast.list input=rain_own columns=name,mapset
    g.list type=raster mapset=t_copy_2
    t.rast.list input=rain@t_copy columns=name,mapset
    ```

    ```text
    name|mapset
    rain_1|t_copy_2
    rain_2|t_copy_2
    rain_3|t_copy_2
    rain_1
    rain_2
    rain_3
    name|mapset
    rain_1|t_copy
    rain_2|t_copy
    rain_3|t_copy
    ```

    ```sh
    if ! t.copy -c --overwrite input=rain@t_copy output=rain_own 2>&1; then
        echo "t.copy failed"
    fi
    g.remove -f type=raster name=rain_1,rain_2,rain_3
    t.copy -c --overwrite input=rain@t_copy output=rain_own
    t.rast.list input=rain_own columns=name,mapset
    ```

    ```text
    Copying raster maps to the current mapset...
    ERROR: A raster map <rain_1> exists already in the current mapset
           <t_copy_2>.
    t.copy failed
    name|mapset
    rain_1|t_copy_2
    rain_2|t_copy_2
    rain_3|t_copy_2
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(flags="c", mapset="t_copy_2")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_copy", operation="add")
    tools.t_copy(input="rain", output="rain_linked")
    print(tools.t_rast_list(input="rain_linked", columns="name,mapset").text)
    ```

    ```text
    name|mapset
    rain_1|t_copy
    rain_2|t_copy
    rain_3|t_copy
    ```

    ```python
    tools.t_copy(input="rain@t_copy", output="rain_own", flags="c")
    print(tools.t_rast_list(input="rain_own", columns="name,mapset").text)
    print(tools.g_list(type="raster", mapset="t_copy_2").text)
    print(tools.t_rast_list(input="rain@t_copy", columns="name,mapset").text)
    ```

    ```text
    name|mapset
    rain_1|t_copy_2
    rain_2|t_copy_2
    rain_3|t_copy_2
    rain_1
    rain_2
    rain_3
    name|mapset
    rain_1|t_copy
    rain_2|t_copy
    rain_3|t_copy
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_copy(input="rain@t_copy", output="rain_own", flags="c", overwrite=True)
    except ToolError as error:
        print(error.stderr.strip())
        print("t.copy failed")
    tools.g_remove(flags="f", type="raster", name="rain_1,rain_2,rain_3")
    tools.t_copy(input="rain@t_copy", output="rain_own", flags="c", overwrite=True)
    print(tools.t_rast_list(input="rain_own", columns="name,mapset").text)
    ```

    ```text
    Copying raster maps to the current mapset...
    ERROR: A raster map <rain_1> exists already in the current mapset
           <t_copy_2>.
    t.copy failed
    name|mapset
    rain_1|t_copy_2
    rain_2|t_copy_2
    rain_3|t_copy_2
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.copy](g.copy.md), [g.list](g.list.md), [g.mapset](g.mapset.md),
[g.mapsets](g.mapsets.md), [g.region](g.region.md),
[g.remove](g.remove.md),
[t.create](t.create.md), [t.info](t.info.md), [t.list](t.list.md),
[t.rast.extract](t.rast.extract.md), [t.rast.list](t.rast.list.md),
[t.rast3d.extract](t.rast3d.extract.md), [t.rast3d.list](t.rast3d.list.md),
[t.register](t.register.md), [t.remove](t.remove.md),
[t.vect.extract](t.vect.extract.md), [t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Markus Metz, [mundialis](https://www.mundialis.de)
