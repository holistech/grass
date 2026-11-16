## DESCRIPTION

*t.merge* registers the maps of several space time datasets in one output
dataset: the output holds the maps of all inputs, and the inputs stay as they
are. See the [introduction to temporal data processing](temporalintro.md) for
an overview. Only the registration is merged. *t.merge* copies no map and
changes no time stamp; every map keeps the time it has in the temporal
database.

The option **inputs** names the datasets to merge, separated by commas, and
**output** names the dataset that receives their maps. Both are required.
The option **type** gives the type of all datasets of the call: `strds`
(the default), `str3ds` or `stvds`. A dataset is found by its type and name,
so a name that belongs to a dataset of another type is not found.

A map that is a member of several inputs is registered once in the output.
Registering a map in the output does not unregister it from the input, so the
map then belongs to all of these datasets, which *[t.info](t.info.md)* shows
for the map under `Registered datasets`. The output takes the start and end
time, the granularity and the range of values from all registered maps (see
the first example).

### The output dataset

A new output dataset gets the temporal type of the inputs, the title and the
description `Merged space time dataset` and the semantic type `mean`.

An output that exists already is refused, unless the flag **--overwrite** is
given. With **--overwrite**, the maps of the inputs are added to the maps that
the output holds; nothing is removed from the output and the maps it holds
already are not registered again. The output may also be one of the inputs,
which adds nothing for that input.

### Temporal type

All inputs must have the same temporal type, absolute or relative. The
type of the output is that of the inputs (see the third example). With
relative time, the inputs must also share the time unit of their maps.

### Mapsets

The output belongs to the current mapset. An input name without a mapset is
looked for in the current mapset only, also if another mapset of the search
path has a dataset of that name; name such a dataset with its mapset
(`temperature@climate`). The maps of an input of another mapset are
registered in the output, in the current mapset.

## NOTES

An output in another mapset is refused with the error "Output space time
dataset `<name@mapset>` must be located in this mapset". An existing output
without **--overwrite** is refused with an error like "Unable to merge maps
into space time raster dataset `<out@PERMANENT>` please use the overwrite
flag." (raster stands for the type of the maps: raster, raster3d or vector).

Refusals and what they leave behind:

- A name that is not a dataset of the given type stops the run with the error
  "Space time dataset `<name>` of type `<strds>` not found", and no output is
  created.
- Datasets of different temporal types stop the run with the error "Space
  time datasets to merge must have the same temporal type", and no output is
  created.
- Datasets with a time zone offset and datasets without one, or such inputs
  and an existing output of the other kind, are refused before the first
  write with the error "Space time datasets to merge must all have a time
  zone offset or all have none". Datasets with different offsets, such as
  `+01:00` and `+02:00`, are refused the same way with the error "Space time
  datasets to merge must have the same time zone offset", because a dataset
  holds one offset (see *t.register*).
- Two datasets of relative time in different units, such as hours and years,
  cannot be merged. The error begins with "Relative time units of space time
  dataset" and ends with "are different". This is found while the maps are
  registered, and the new output, which is empty or partly filled by then, is
  removed again.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_merge` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.merge* registers maps only, so the maps hold small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_merge -->

<!-- markdownlint-disable MD046 -->

### Merge datasets that share a map

The dataset `rain_early` holds the maps `rain_1` to `rain_3`, daily rain
sums of 1 to 3 mm in every cell, one per day from 2026-06-01. The dataset
`rain_late` holds `rain_4` and `rain_5` for the next two days and, as a third
member, `rain_3`, which is registered in `rain_early` already. Registering a
map by its name alone gives it the time it has in the temporal database.
`t.rast.list` shows that `rain_late` starts with `rain_3`.

The second block merges them into the new dataset `rain_season`, which holds
five maps, not six: `rain_3` is registered once. Its time is from 2026-06-01
to 2026-06-06, the granularity is one day, and the values range from 1 to 5.
The datasets `rain_early` and `rain_late` keep three maps each. The new dataset
has the title `Merged space time dataset` and the semantic type `mean`, and
the map `rain_3` now belongs to all three datasets. The listing of the
datasets is limited to the current mapset with `mapset=.`.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_merge
    g.region raster=elev_state_500m res=1000 -a
    for n in 1 2 3 4 5; do
        r.mapcalc expression="rain_$n = $n"
    done
    t.create output=rain_early title="Early rain" \
        description="Daily rain sum in mm, days 1 to 3"
    t.register -i input=rain_early maps=rain_1,rain_2,rain_3 \
        start=2026-06-01 increment="1 day"
    t.create output=rain_late title="Late rain" \
        description="Daily rain sum in mm, days 3 to 5"
    t.register -i input=rain_late maps=rain_4,rain_5 \
        start=2026-06-04 increment="1 day"
    t.register input=rain_late maps=rain_3
    t.rast.list input=rain_late columns=name,start_time
    ```

    ```text
    name|start_time
    rain_3|2026-06-03 00:00:00
    rain_4|2026-06-04 00:00:00
    rain_5|2026-06-05 00:00:00
    ```

    ```sh
    t.merge inputs=rain_early,rain_late output=rain_season
    t.list type=strds columns=name,number_of_maps mapset=.
    t.rast.list input=rain_season columns=name,start_time,end_time
    t.info -g input=rain_season | grep -E "^(start_time|end_time|granularity|number_of_maps|min_min|max_max)="
    t.info input=rain_season | grep -E "Semantic type|^ \| Merged"
    t.info type=raster input=rain_3 | grep "Registered datasets"
    ```

    ```text
    rain_early|3
    rain_late|3
    rain_season|5
    name|start_time|end_time
    rain_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    rain_3|2026-06-03 00:00:00|2026-06-04 00:00:00
    rain_4|2026-06-04 00:00:00|2026-06-05 00:00:00
    rain_5|2026-06-05 00:00:00|2026-06-06 00:00:00
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-06 00:00:00'
    granularity='1 day'
    min_min=1.0
    max_max=5.0
    number_of_maps=5
     | Semantic type:.............. mean
     | Merged space time dataset
     | Merged space time dataset
     | Registered datasets ........ rain_early@t_merge,rain_late@t_merge,rain_season@t_merge
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_merge")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for n in range(1, 6):
        tools.r_mapcalc(expression=f"rain_{n} = {n}")
    tools.t_create(
        output="rain_early",
        title="Early rain",
        description="Daily rain sum in mm, days 1 to 3",
    )
    tools.t_register(
        input="rain_early",
        maps="rain_1,rain_2,rain_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(
        output="rain_late",
        title="Late rain",
        description="Daily rain sum in mm, days 3 to 5",
    )
    tools.t_register(
        input="rain_late",
        maps="rain_4,rain_5",
        start="2026-06-04",
        increment="1 day",
        flags="i",
    )
    tools.t_register(input="rain_late", maps="rain_3")
    print(tools.t_rast_list(input="rain_late", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    rain_3|2026-06-03 00:00:00
    rain_4|2026-06-04 00:00:00
    rain_5|2026-06-05 00:00:00
    ```

    ```python
    tools.t_merge(inputs="rain_early,rain_late", output="rain_season")
    print(tools.t_list(type="strds", columns="name,number_of_maps", mapset=".").text)
    print(tools.t_rast_list(input="rain_season", columns="name,start_time,end_time").text)
    info = tools.t_info(input="rain_season", flags="g").keyval
    for key in (
        "start_time",
        "end_time",
        "granularity",
        "min_min",
        "max_max",
        "number_of_maps",
    ):
        print(f"{key}={info[key]}")
    for line in tools.t_info(input="rain_season").stdout.splitlines():
        if "Semantic type" in line or line.startswith(" | Merged"):
            print(line)
    for line in tools.t_info(type="raster", input="rain_3").stdout.splitlines():
        if "Registered datasets" in line:
            print(line)
    ```

    ```text
    rain_early|3
    rain_late|3
    rain_season|5
    name|start_time|end_time
    rain_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    rain_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    rain_3|2026-06-03 00:00:00|2026-06-04 00:00:00
    rain_4|2026-06-04 00:00:00|2026-06-05 00:00:00
    rain_5|2026-06-05 00:00:00|2026-06-06 00:00:00
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-06 00:00:00'
    granularity='1 day'
    min_min=1.0
    max_max=5.0
    number_of_maps=5
     | Semantic type:.............. mean
     | Merged space time dataset
     | Merged space time dataset
     | Registered datasets ........ rain_early@t_merge,rain_late@t_merge,rain_season@t_merge
    ```

### Add maps to an existing dataset

The output `rain_season` exists from the previous example. A call without
**--overwrite** would be refused. With it, the maps of `rain_extra` are added
to the five maps `rain_season` holds. In the second call the output is also an
input, together with `rain_early`, whose maps `rain_season` holds already:
nothing is registered twice, and `rain_season` keeps six maps.

=== "Command line"

    ```sh
    r.mapcalc expression="rain_6 = 6"
    t.create output=rain_extra title="Extra rain" \
        description="Daily rain sum in mm, day 6"
    t.register -i input=rain_extra maps=rain_6 \
        start=2026-06-06 increment="1 day"
    t.merge --overwrite inputs=rain_extra output=rain_season
    t.rast.list input=rain_season columns=name,start_time
    t.merge --overwrite inputs=rain_early,rain_season,rain_extra \
        output=rain_season
    t.info -g input=rain_season | grep -E "^(end_time|number_of_maps)="
    ```

    ```text
    name|start_time
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    rain_4|2026-06-04 00:00:00
    rain_5|2026-06-05 00:00:00
    rain_6|2026-06-06 00:00:00
    end_time='2026-06-07 00:00:00'
    number_of_maps=6
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="rain_6 = 6")
    tools.t_create(
        output="rain_extra",
        title="Extra rain",
        description="Daily rain sum in mm, day 6",
    )
    tools.t_register(
        input="rain_extra",
        maps="rain_6",
        start="2026-06-06",
        increment="1 day",
        flags="i",
    )
    tools.t_merge(inputs="rain_extra", output="rain_season", overwrite=True)
    print(tools.t_rast_list(input="rain_season", columns="name,start_time").text)
    tools.t_merge(
        inputs="rain_early,rain_season,rain_extra",
        output="rain_season",
        overwrite=True,
    )
    info = tools.t_info(input="rain_season", flags="g").keyval
    for key in ("end_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time
    rain_1|2026-06-01 00:00:00
    rain_2|2026-06-02 00:00:00
    rain_3|2026-06-03 00:00:00
    rain_4|2026-06-04 00:00:00
    rain_5|2026-06-05 00:00:00
    rain_6|2026-06-06 00:00:00
    end_time='2026-06-07 00:00:00'
    number_of_maps=6
    ```

### Merge datasets of relative time

Two model runs have relative time in hours: `run_a` covers the hours 0 to 3,
`run_b` the hours 3 to 5. The maps hold the simulated runoff of 1 to 5 mm per
model hour in every cell. The merged dataset has relative time as well, the
unit `hours` and the times 0 to 5. The maps are new ones; a map has one
temporal type, so the maps of the first example cannot join a dataset of
relative time.

=== "Command line"

    ```sh
    for n in 1 2 3 4 5; do
        r.mapcalc expression="runoff_$n = $n"
    done
    t.create output=run_a temporaltype=relative title="Run A" \
        description="Simulated runoff in mm per model hour, hours 0 to 3"
    t.register -i input=run_a maps=runoff_1,runoff_2,runoff_3 \
        start=0 increment=1 unit=hours
    t.create output=run_b temporaltype=relative title="Run B" \
        description="Simulated runoff in mm per model hour, hours 3 to 5"
    t.register -i input=run_b maps=runoff_4,runoff_5 \
        start=3 increment=1 unit=hours
    t.merge inputs=run_a,run_b output=run_full
    t.rast.list input=run_full columns=name,start_time,end_time
    t.info -g input=run_full | grep -E "^(temporal_type|start_time|end_time|unit|granularity|number_of_maps)="
    ```

    ```text
    name|start_time|end_time
    runoff_1|0|1
    runoff_2|1|2
    runoff_3|2|3
    runoff_4|3|4
    runoff_5|4|5
    temporal_type=relative
    start_time='0'
    end_time='5'
    unit=hours
    granularity=1
    number_of_maps=5
    ```

=== "Python (grass.tools)"

    ```python
    for n in range(1, 6):
        tools.r_mapcalc(expression=f"runoff_{n} = {n}")
    tools.t_create(
        output="run_a",
        temporaltype="relative",
        title="Run A",
        description="Simulated runoff in mm per model hour, hours 0 to 3",
    )
    tools.t_register(
        input="run_a",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_create(
        output="run_b",
        temporaltype="relative",
        title="Run B",
        description="Simulated runoff in mm per model hour, hours 3 to 5",
    )
    tools.t_register(
        input="run_b",
        maps="runoff_4,runoff_5",
        start=3,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_merge(inputs="run_a,run_b", output="run_full")
    print(tools.t_rast_list(input="run_full", columns="name,start_time,end_time").text)
    info = tools.t_info(input="run_full", flags="g").keyval
    for key in (
        "temporal_type",
        "start_time",
        "end_time",
        "unit",
        "granularity",
        "number_of_maps",
    ):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time
    runoff_1|0|1
    runoff_2|1|2
    runoff_3|2|3
    runoff_4|3|4
    runoff_5|4|5
    temporal_type=relative
    start_time='0'
    end_time='5'
    unit=hours
    granularity=1
    number_of_maps=5
    ```

### Merge vector datasets

With **type** `stvds`, *t.merge* merges space time vector datasets. The
datasets `creek_a` and `creek_b` each hold one point map, a gauge of the
Crabtree Creek near Raleigh copied from `usgsgages`, one for each day.
Datasets of type `str3ds` are merged the same way. The merged dataset
`creek_gauges` has two maps and two points.

=== "Command line"

    ```sh
    v.extract input=usgsgages output=creek_gauge_1 where="cat = 149"
    v.extract input=usgsgages output=creek_gauge_2 where="cat = 150"
    t.create type=stvds output=creek_a title="Creek A" \
        description="Gauge of day 1"
    t.register -i type=vector input=creek_a maps=creek_gauge_1 \
        start=2026-06-01 increment="1 day"
    t.create type=stvds output=creek_b title="Creek B" \
        description="Gauge of day 2"
    t.register -i type=vector input=creek_b maps=creek_gauge_2 \
        start=2026-06-02 increment="1 day"
    t.merge type=stvds inputs=creek_a,creek_b output=creek_gauges
    t.vect.list input=creek_gauges columns=name,start_time
    t.info -g type=stvds input=creek_gauges | grep -E "^(points|number_of_maps)="
    ```

    ```text
    name|start_time
    creek_gauge_1|2026-06-01 00:00:00
    creek_gauge_2|2026-06-02 00:00:00
    points=2
    number_of_maps=2
    ```

=== "Python (grass.tools)"

    ```python
    for n, cat in ((1, 149), (2, 150)):
        tools.v_extract(input="usgsgages", output=f"creek_gauge_{n}", where=f"cat = {cat}")
    tools.t_create(
        type="stvds", output="creek_a", title="Creek A", description="Gauge of day 1"
    )
    tools.t_register(
        type="vector",
        input="creek_a",
        maps="creek_gauge_1",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(
        type="stvds", output="creek_b", title="Creek B", description="Gauge of day 2"
    )
    tools.t_register(
        type="vector",
        input="creek_b",
        maps="creek_gauge_2",
        start="2026-06-02",
        increment="1 day",
        flags="i",
    )
    tools.t_merge(type="stvds", inputs="creek_a,creek_b", output="creek_gauges")
    print(tools.t_vect_list(input="creek_gauges", columns="name,start_time").text)
    info = tools.t_info(type="stvds", input="creek_gauges", flags="g").keyval
    for key in ("points", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time
    creek_gauge_1|2026-06-01 00:00:00
    creek_gauge_2|2026-06-02 00:00:00
    points=2
    number_of_maps=2
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapsets](g.mapsets.md), [t.copy](t.copy.md), [t.create](t.create.md),
[t.info](t.info.md), [t.register](t.register.md), [t.remove](t.remove.md),
[t.support](t.support.md), [t.unregister](t.unregister.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
