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
- Two datasets of relative time in different units, such as hours and years,
  cannot be merged. The error begins with "Relative time units of space time
  dataset" and ends with "are different". This is found while the maps are
  registered, and the new output, which is empty or partly filled by then, is
  removed again.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Merge datasets that share a map

The dataset `early` holds the maps `m_1` to `m_3`, one per day from
2026-06-01. The dataset `late` holds `m_4` and `m_5` for the next two days and,
as a third member, `m_3`, which is registered in `early` already. Registering
a map by its name alone gives it the time it has in the temporal database.
`t.rast.list` shows that `late` starts with `m_3`.

The second block merges them into the new dataset `season`, which holds five
maps, not six: `m_3` is registered once. Its time is from 2026-06-01 to
2026-06-06, the granularity is one day, and the values range from 1 to 5. The
datasets `early` and `late` keep three maps each. The new dataset has the
title `Merged space time dataset` and the semantic type `mean`, and the map
`m_3` now belongs to all three datasets.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for n in 1 2 3 4 5; do
        r.mapcalc expression="m_$n = $n"
    done
    t.create output=early title="Early" description="Days 1 to 3"
    t.register -i input=early maps=m_1,m_2,m_3 \
        start=2026-06-01 increment="1 day"
    t.create output=late title="Late" description="Days 3 to 5"
    t.register -i input=late maps=m_4,m_5 \
        start=2026-06-04 increment="1 day"
    t.register input=late maps=m_3
    t.rast.list input=late columns=name,start_time
    ```

    ```text
    name|start_time
    m_3|2026-06-03 00:00:00
    m_4|2026-06-04 00:00:00
    m_5|2026-06-05 00:00:00
    ```

    ```sh
    t.merge inputs=early,late output=season
    t.list type=strds columns=name,number_of_maps
    t.rast.list input=season columns=name,start_time,end_time
    t.info -g input=season | grep -E "^(start_time|end_time|granularity|number_of_maps|min_min|max_max)="
    t.info input=season | grep -E "Semantic type|^ \| Merged"
    t.info type=raster input=m_3 | grep "Registered datasets"
    ```

    ```text
    early|3
    late|3
    season|5
    name|start_time|end_time
    m_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    m_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    m_3|2026-06-03 00:00:00|2026-06-04 00:00:00
    m_4|2026-06-04 00:00:00|2026-06-05 00:00:00
    m_5|2026-06-05 00:00:00|2026-06-06 00:00:00
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-06 00:00:00'
    granularity='1 day'
    min_min=1.0
    max_max=5.0
    number_of_maps=5
     | Semantic type:.............. mean
     | Merged space time dataset
     | Merged space time dataset
     | Registered datasets ........ early@PERMANENT,late@PERMANENT,season@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for n in range(1, 6):
        tools.r_mapcalc(expression=f"m_{n} = {n}")
    tools.t_create(output="early", title="Early", description="Days 1 to 3")
    tools.t_register(
        input="early",
        maps="m_1,m_2,m_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(output="late", title="Late", description="Days 3 to 5")
    tools.t_register(
        input="late",
        maps="m_4,m_5",
        start="2026-06-04",
        increment="1 day",
        flags="i",
    )
    tools.t_register(input="late", maps="m_3")
    print(tools.t_rast_list(input="late", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    m_3|2026-06-03 00:00:00
    m_4|2026-06-04 00:00:00
    m_5|2026-06-05 00:00:00
    ```

    ```python
    tools.t_merge(inputs="early,late", output="season")
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.t_rast_list(input="season", columns="name,start_time,end_time").text)
    info = tools.t_info(input="season", flags="g").keyval
    for key in (
        "start_time",
        "end_time",
        "granularity",
        "min_min",
        "max_max",
        "number_of_maps",
    ):
        print(f"{key}={info[key]}")
    for line in tools.t_info(input="season").stdout.splitlines():
        if "Semantic type" in line or line.startswith(" | Merged"):
            print(line)
    for line in tools.t_info(type="raster", input="m_3").stdout.splitlines():
        if "Registered datasets" in line:
            print(line)
    ```

    ```text
    early|3
    late|3
    season|5
    name|start_time|end_time
    m_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    m_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    m_3|2026-06-03 00:00:00|2026-06-04 00:00:00
    m_4|2026-06-04 00:00:00|2026-06-05 00:00:00
    m_5|2026-06-05 00:00:00|2026-06-06 00:00:00
    start_time='2026-06-01 00:00:00'
    end_time='2026-06-06 00:00:00'
    granularity='1 day'
    min_min=1.0
    max_max=5.0
    number_of_maps=5
     | Semantic type:.............. mean
     | Merged space time dataset
     | Merged space time dataset
     | Registered datasets ........ early@PERMANENT,late@PERMANENT,season@PERMANENT
    ```

### Add maps to an existing dataset

The output `season` exists from the previous example. A call without
**--overwrite** would be refused. With it, the maps of `extra` are added to
the five maps `season` holds. In the second call the output is also an
input, together with `early`, whose maps `season` holds already: nothing is
registered twice, and `season` keeps six maps.

=== "Command line"

    ```sh
    r.mapcalc expression="m_6 = 6"
    t.create output=extra title="Extra" description="Day 6"
    t.register -i input=extra maps=m_6 start=2026-06-06 increment="1 day"
    t.merge --overwrite inputs=extra output=season
    t.rast.list input=season columns=name,start_time
    t.merge --overwrite inputs=early,season,extra output=season
    t.info -g input=season | grep -E "^(end_time|number_of_maps)="
    ```

    ```text
    name|start_time
    m_1|2026-06-01 00:00:00
    m_2|2026-06-02 00:00:00
    m_3|2026-06-03 00:00:00
    m_4|2026-06-04 00:00:00
    m_5|2026-06-05 00:00:00
    m_6|2026-06-06 00:00:00
    end_time='2026-06-07 00:00:00'
    number_of_maps=6
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="m_6 = 6")
    tools.t_create(output="extra", title="Extra", description="Day 6")
    tools.t_register(
        input="extra", maps="m_6", start="2026-06-06", increment="1 day", flags="i"
    )
    tools.t_merge(inputs="extra", output="season", overwrite=True)
    print(tools.t_rast_list(input="season", columns="name,start_time").text)
    tools.t_merge(inputs="early,season,extra", output="season", overwrite=True)
    info = tools.t_info(input="season", flags="g").keyval
    for key in ("end_time", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time
    m_1|2026-06-01 00:00:00
    m_2|2026-06-02 00:00:00
    m_3|2026-06-03 00:00:00
    m_4|2026-06-04 00:00:00
    m_5|2026-06-05 00:00:00
    m_6|2026-06-06 00:00:00
    end_time='2026-06-07 00:00:00'
    number_of_maps=6
    ```

### Merge datasets of relative time

Two model runs have relative time in hours: `run1` covers the hours 0 to 3,
`run2` the hours 3 to 5. The merged dataset has relative time as well, the
unit `hours` and the times 0 to 5. The maps are new ones; a map has one
temporal type, so the maps of the first example cannot join a dataset of
relative time.

=== "Command line"

    ```sh
    for n in 1 2 3 4 5; do
        r.mapcalc expression="step_$n = $n"
    done
    t.create output=run1 temporaltype=relative title="Run 1" \
        description="Steps 1 to 3"
    t.register -i input=run1 maps=step_1,step_2,step_3 \
        start=0 increment=1 unit=hours
    t.create output=run2 temporaltype=relative title="Run 2" \
        description="Steps 4 and 5"
    t.register -i input=run2 maps=step_4,step_5 \
        start=3 increment=1 unit=hours
    t.merge inputs=run1,run2 output=full
    t.rast.list input=full columns=name,start_time,end_time
    t.info -g input=full | grep -E "^(temporal_type|start_time|end_time|unit|granularity|number_of_maps)="
    ```

    ```text
    name|start_time|end_time
    step_1|0|1
    step_2|1|2
    step_3|2|3
    step_4|3|4
    step_5|4|5
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
        tools.r_mapcalc(expression=f"step_{n} = {n}")
    tools.t_create(
        output="run1",
        temporaltype="relative",
        title="Run 1",
        description="Steps 1 to 3",
    )
    tools.t_register(
        input="run1",
        maps="step_1,step_2,step_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_create(
        output="run2",
        temporaltype="relative",
        title="Run 2",
        description="Steps 4 and 5",
    )
    tools.t_register(
        input="run2",
        maps="step_4,step_5",
        start=3,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_merge(inputs="run1,run2", output="full")
    print(tools.t_rast_list(input="full", columns="name,start_time,end_time").text)
    info = tools.t_info(input="full", flags="g").keyval
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
    step_1|0|1
    step_2|1|2
    step_3|2|3
    step_4|3|4
    step_5|4|5
    temporal_type=relative
    start_time='0'
    end_time='5'
    unit=hours
    granularity=1
    number_of_maps=5
    ```

### Merge vector datasets

With **type** `stvds`, *t.merge* merges space time vector datasets. The
datasets `gauges_a` and `gauges_b` each hold one point map, one for each day.
Datasets of type `str3ds` are merged the same way. The merged dataset
`gauges` has two maps and two points.

=== "Command line"

    ```sh
    for n in 1 2; do
        echo "$n.5,0.5,$n.0" | v.in.ascii input=- output=gauge_$n \
            separator=comma \
            columns="x double precision, y double precision, speed double precision"
    done
    t.create type=stvds output=gauges_a title="Gauges A" description="Day 1"
    t.register -i type=vector input=gauges_a maps=gauge_1 \
        start=2026-06-01 increment="1 day"
    t.create type=stvds output=gauges_b title="Gauges B" description="Day 2"
    t.register -i type=vector input=gauges_b maps=gauge_2 \
        start=2026-06-02 increment="1 day"
    t.merge type=stvds inputs=gauges_a,gauges_b output=gauges
    t.vect.list input=gauges columns=name,start_time
    t.info -g type=stvds input=gauges | grep -E "^(points|number_of_maps)="
    ```

    ```text
    name|start_time
    gauge_1|2026-06-01 00:00:00
    gauge_2|2026-06-02 00:00:00
    points=2
    number_of_maps=2
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    for n in range(1, 3):
        tools.v_in_ascii(
            input=StringIO(f"{n}.5,0.5,{n}.0\n"),
            output=f"gauge_{n}",
            separator="comma",
            columns="x double precision, y double precision, speed double precision",
        )
    tools.t_create(type="stvds", output="gauges_a", title="Gauges A", description="Day 1")
    tools.t_register(
        type="vector",
        input="gauges_a",
        maps="gauge_1",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(type="stvds", output="gauges_b", title="Gauges B", description="Day 2")
    tools.t_register(
        type="vector",
        input="gauges_b",
        maps="gauge_2",
        start="2026-06-02",
        increment="1 day",
        flags="i",
    )
    tools.t_merge(type="stvds", inputs="gauges_a,gauges_b", output="gauges")
    print(tools.t_vect_list(input="gauges", columns="name,start_time").text)
    info = tools.t_info(type="stvds", input="gauges", flags="g").keyval
    for key in ("points", "number_of_maps"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time
    gauge_1|2026-06-01 00:00:00
    gauge_2|2026-06-02 00:00:00
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
