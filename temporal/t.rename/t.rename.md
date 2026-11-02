## DESCRIPTION

*t.rename* gives a space time dataset (STRDS, STR3DS or STVDS) a new name in
the temporal database of the current mapset. The maps registered in the
dataset stay as they are and are registered in the dataset under its new name.
A space time dataset is a collection of time stamped maps; see the
[introduction to temporal data processing](temporalintro.md) for an overview.
The dataset keeps its maps, its time extent, its title, description and
semantic type. To change these, use
*[t.support](t.support.md)*; to create a dataset, use
*[t.create](t.create.md)*.

The option **input** is the name of the dataset to rename and **output** is
its new name. Both may carry a mapset (`rain@PERMANENT`); without one, the
current mapset is used. The option **type** gives the type of the dataset:
`strds` (the default), `str3ds` or `stvds`. A dataset is found by its type and
name, so the call refuses a name that belongs to a dataset of another type.
Datasets with absolute and with relative time are renamed the same way.

A dataset can only be renamed in the mapset it belongs to, and only to a name
in that mapset, because GRASS writes to the current mapset only.

The new name must not be in use for a dataset of the same type. With the
flag **--overwrite**, *t.rename* first removes the dataset that has the new
name and then renames. The maps of the removed dataset stay in the mapset and
in the temporal database, but belong to no dataset unless they are registered
in another one.

*t.rename* appends its own call to the command history of the dataset, with
the old name as **input**; *[t.info](t.info.md)* with the flag **-h** shows
it.

## NOTES

A name that does not exist stops the run with an error such as
`Space time raster dataset <nope@PERMANENT> not found`, and so does a name that
belongs to a dataset of another type: the call with the default **type**
`strds` for a space time 3D raster dataset fails; give **type=str3ds**. A
**type** other than `strds`, `str3ds` and `stvds` is refused by the parser.

A new name that is already in use, without **--overwrite**, ends with an error
that says the name is in use and asks for the overwrite flag. Neither dataset
changes.

The new name must not contain a dot; *t.rename* stops with an error and keeps
the old name, for every type of dataset.

If the new name carries another mapset than the current one, the error says
that the mapset of the new identifier differs from the current mapset. For a
dataset of another mapset as **input**, the error says that the mapset of the
database does not match the current mapset. In both cases the datasets stay
as they were.

Renaming a dataset to its own name, with or without the mapset, does nothing
and does not change its command history.

If the current mapset and another mapset of the search path both hold a
dataset of the name given as **input**, the one of the current mapset is
renamed and the other keeps its name and its maps.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Rename a dataset

Two space time raster datasets hold five maps in all: `rain` has three daily
maps, `snow` two. After `t.rename input=rain output=precipitation`, the
dataset `precipitation` holds the three maps of `rain` and the dataset `rain`
no longer exists. The first output lists the datasets and shows the keys `id`,
`name` and `number_of_maps` of the renamed dataset. The second output shows the
title and the description, which are unchanged, then the last line of the
command history, which is the call of *t.rename*, and last the map `rain_1`,
which is now registered in `precipitation`.

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
    t.rename input=rain output=precipitation
    t.list type=strds columns=name,number_of_maps
    t.info -g input=precipitation | grep -E "^(id|name|number_of_maps)="
    ```

    ```text
    precipitation|3
    snow|2
    id=precipitation@PERMANENT
    name=precipitation
    number_of_maps=3
    ```

    ```sh
    t.info -h input=precipitation | sed -n 1,4p
    t.info -h input=precipitation | tail -n 1
    t.info -g type=raster input=rain_1 | grep -E "^(id|registered_datasets)="
    ```

    ```text
    # Title:
    # Rain
    # Description:
    # Daily rain
    t.rename input="rain" output="precipitation"
    id=rain_1@PERMANENT
    registered_datasets=precipitation@PERMANENT
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
    tools.t_rename(input="rain", output="precipitation")
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    info = tools.t_info(input="precipitation", flags="g").keyval
    for key in ("id", "name", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    precipitation|3
    snow|2
    id=precipitation@PERMANENT
    name=precipitation
    number_of_maps=3
    ```

    ```python
    history = tools.t_info(input="precipitation", flags="h").text.splitlines()
    print("\n".join(history[:4]))
    print(history[-1])
    info = tools.t_info(type="raster", input="rain_1", flags="g").keyval
    for key in ("id", "registered_datasets"):
        if key in info:
            print(f"{key}={info[key]}")
    ```

    ```text
    # Title:
    # Rain
    # Description:
    # Daily rain
    t.rename input="rain" output="precipitation"
    id=rain_1@PERMANENT
    registered_datasets=precipitation@PERMANENT
    ```

### Replace a dataset with --overwrite

The dataset `snow` is renamed to `precipitation`, the name of the dataset from
the previous example. Without **--overwrite**, the call stops with an error
and nothing changes. With it, the old `precipitation` is removed first, and
`snow` takes its name. Afterwards only one dataset is left, with the two maps
of `snow`. The five maps of the mapset are still known to the temporal
database. The map `rain_1`, which was in the removed dataset, is registered in
no dataset: its `registered_datasets` line is missing, while `snow_1` is
registered in `precipitation`.

=== "Command line"

    ```sh
    t.rename --overwrite input=snow output=precipitation
    t.list type=strds columns=name,number_of_maps
    t.rast.list input=precipitation
    t.list type=raster columns=name
    ```

    ```text
    precipitation|2
    name|mapset|start_time|end_time
    snow_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00
    snow_2|PERMANENT|2026-06-02 00:00:00|2026-06-03 00:00:00
    rain_1
    rain_2
    rain_3
    snow_1
    snow_2
    ```

    ```sh
    for name in rain_1 snow_1; do
        t.info -g type=raster input=$name | grep -E "^(id|registered_datasets)="
    done
    ```

    ```text
    id=rain_1@PERMANENT
    id=snow_1@PERMANENT
    registered_datasets=precipitation@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rename(input="snow", output="precipitation", overwrite=True)
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.t_rast_list(input="precipitation").text)
    print(tools.t_list(type="raster", columns="name").text)
    ```

    ```text
    precipitation|2
    name|mapset|start_time|end_time
    snow_1|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00
    snow_2|PERMANENT|2026-06-02 00:00:00|2026-06-03 00:00:00
    rain_1
    rain_2
    rain_3
    snow_1
    snow_2
    ```

    ```python
    for name in ("rain_1", "snow_1"):
        info = tools.t_info(type="raster", input=name, flags="g").keyval
        for key in ("id", "registered_datasets"):
            if key in info:
                print(f"{key}={info[key]}")
    ```

    ```text
    id=rain_1@PERMANENT
    id=snow_1@PERMANENT
    registered_datasets=precipitation@PERMANENT
    ```

### Rename datasets of other types

With **type**, *t.rename* renames space time 3D raster datasets and space time
vector datasets. Here, `soil` becomes `layers` and `gauges` becomes `wind`.
The names of the vector dataset carry the mapset `PERMANENT`, the current
mapset, which gives the same result as the names without it. *t.list* shows the
new names with their number of maps, and *t.info* shows that each map is
registered in the renamed dataset.

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
    t.rename type=str3ds input=soil output=layers
    t.rename type=stvds input=gauges@PERMANENT output=wind@PERMANENT
    t.list type=str3ds columns=name,number_of_maps
    t.list type=stvds columns=name,number_of_maps
    t.info -g type=raster_3d input=soil_1 | grep "^registered_datasets="
    t.info -g type=vector input=gauges_1 | grep "^registered_datasets="
    ```

    ```text
    layers|1
    wind|1
    registered_datasets=layers@PERMANENT
    registered_datasets=wind@PERMANENT
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
    tools.t_rename(type="str3ds", input="soil", output="layers")
    tools.t_rename(type="stvds", input="gauges@PERMANENT", output="wind@PERMANENT")
    print(tools.t_list(type="str3ds", columns="name,number_of_maps").text)
    print(tools.t_list(type="stvds", columns="name,number_of_maps").text)
    for map_type, name in (("raster_3d", "soil_1"), ("vector", "gauges_1")):
        info = tools.t_info(type=map_type, input=name, flags="g").keyval
        print(f"registered_datasets={info['registered_datasets']}")
    ```

    ```text
    layers|1
    wind|1
    registered_datasets=layers@PERMANENT
    registered_datasets=wind@PERMANENT
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.create](t.create.md), [t.info](t.info.md), [t.register](t.register.md),
[t.remove](t.remove.md), [t.support](t.support.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
