## DESCRIPTION

*t.support* changes the descriptive metadata of a space time dataset and
brings the metadata that is computed from the registered maps up to date. See
the [introduction to temporal data processing](temporalintro.md) for an
overview. The maps, their time stamps and their registration stay as they
are, with one exception: with the flag **-m** a map that is gone from the
spatial database is unregistered.

The option **input** names the dataset, and **type** gives its type: `strds`
(the default), `str3ds` or `stvds`. A dataset is found by its type and name,
so a name that belongs to a dataset of another type is not found. The
dataset may have absolute or relative time.

### Descriptive metadata

Each of the following options changes one property and leaves the others as
they are. A call with only **title**, for example, keeps the description. An
empty value changes nothing.

- **title** sets the title of the dataset.
- **description** sets its description.
- **semantictype** sets the semantic type, one of `min`, `max`, `sum` and
  `mean`. It has no default: a call without it keeps the semantic type, also
  a call with **-m** or **-u**. A new dataset made by *[t.create](t.create.md)*
  has the semantic type `mean`.
- **aggr_type** sets the aggregation type of a space time raster or 3D raster
  dataset, the name of the method that produced its maps, such as `average`.
  The text is stored as it is and not checked against the known aggregation
  methods. *[t.info](t.info.md)* shows `None` until a type is set. A space
  time vector dataset has no aggregation type: *t.support* warns about
  **aggr_type** for it, ignores it and applies the other options.

*[t.info](t.info.md)* shows the title and the description in its text output
and the semantic type and the aggregation type both in its text output and with
**-g**.

### Updating the metadata computed from the maps

A dataset keeps the values that it computes from its maps: the start and end
time, the granularity, the spatial extent, the resolutions, the range of values
and the number of maps. The flags compute them again; so does a change of
**title**, **description**, **semantictype** or **aggr_type**. This also
writes the granularity anew that a release before GRASS 8.6 stored for a
monthly series from the last day of a month, `1 day`; it is `1 month` now (see
*[t.info](t.info.md)*):

- **-u** computes them again from the entries of the registered maps in the
  temporal database. It does not read the maps themselves, so a map that was
  made again without a temporal command is not seen by **-u**; use **-m** for
  it.
- **-m** reads every registered map from the spatial database again and writes
  its values (extent, resolution, range of values) into the temporal database.
  A map that is gone from the spatial database is deleted from the temporal
  database, which unregisters it from every dataset that held it. The other
  datasets that hold a map that **-m** read or removed are updated too. **-m**
  includes the work of **-u**, so the two flags are not needed together. A map
  of another mapset is read from there.

A call without **-u**, **-m** and any other option does not compute these
values again.

## NOTES

An unknown name stops the run with the error "Space time dataset `<name>` of
type `<strds>` not found". A **semantictype** other than the four values or a
**type** other than the three types is refused by the parser, which names the
legal values. A call without **input** is refused with the message that the
required parameter is not set.

The map values that **-m** reads are the ones the spatial database holds now.
For a raster dataset they are the range of values and the extent and
resolution of each map; for a vector dataset the extent. Changing a map
without **-m** or **-u** leaves the dataset as it was (see the third example).

The command history of the dataset records each call of *t.support*, which
*t.info* shows under `Command history`.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_support` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. The first two examples change metadata only, so their maps hold small
constant values. The last two examples use a series of monthly air temperatures
that they generate from the elevation model of the dataset. The values are made
up and are not measurements. *t.support* with **-m** changes only datasets of
the mapset in which it runs.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_support -->

<!-- markdownlint-disable MD046 -->

### Change title, description and types

The dataset `rain` holds three maps, one per day from 2026-06-01, with 10, 20
and 30 mm of rain. *t.info* shows its title and description, the semantic type
`mean` and the aggregation type `None`.

The first call of *t.support* changes all four properties at once. The second
call gives only a title, so the description, the semantic type and the
aggregation type stay.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_support
    g.region raster=elev_state_500m res=1000 -a
    for day in 1 2 3; do
        r.mapcalc expression="rain_2026_06_0$day = $day * 10"
    done
    t.create output=rain title="Old title" description="Old description"
    t.register -i input=rain \
        maps=rain_2026_06_01,rain_2026_06_02,rain_2026_06_03 \
        start=2026-06-01 increment="1 day"
    t.info input=rain | grep -E "Semantic type|Aggregation type"
    t.info input=rain | grep -A3 "Title:"
    ```

    ```text
     | Semantic type:.............. mean
     | Aggregation type:........... None
     | Title:
     | Old title
     | Description:
     | Old description
    ```

    ```sh
    t.support input=rain title="Daily rain" \
        description="Rain per day in mm" \
        semantictype=sum aggr_type=sum
    t.info input=rain | grep -E "Semantic type|Aggregation type"
    t.info input=rain | grep -A3 "Title:"
    t.support input=rain title="Rain per day"
    t.info input=rain | grep -E "Semantic type|Aggregation type"
    t.info input=rain | grep -A3 "Title:"
    ```

    ```text
     | Semantic type:.............. sum
     | Aggregation type:........... sum
     | Title:
     | Daily rain
     | Description:
     | Rain per day in mm
     | Semantic type:.............. sum
     | Aggregation type:........... sum
     | Title:
     | Rain per day
     | Description:
     | Rain per day in mm
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def show_metadata(name):
        lines = tools.t_info(input=name).stdout.splitlines()
        for line in lines:
            if "Semantic type" in line or "Aggregation type" in line:
                print(line)
        first = next(i for i, line in enumerate(lines) if "Title:" in line)
        print("\n".join(lines[first : first + 4]))


    tools.g_mapset(flags="c", mapset="t_support")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for day in range(1, 4):
        tools.r_mapcalc(expression=f"rain_2026_06_0{day} = {day} * 10")
    tools.t_create(output="rain", title="Old title", description="Old description")
    tools.t_register(
        input="rain",
        maps="rain_2026_06_01,rain_2026_06_02,rain_2026_06_03",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    show_metadata("rain")
    ```

    ```text
     | Semantic type:.............. mean
     | Aggregation type:........... None
     | Title:
     | Old title
     | Description:
     | Old description
    ```

    ```python
    tools.t_support(
        input="rain",
        title="Daily rain",
        description="Rain per day in mm",
        semantictype="sum",
        aggr_type="sum",
    )
    show_metadata("rain")
    tools.t_support(input="rain", title="Rain per day")
    show_metadata("rain")
    ```

    ```text
     | Semantic type:.............. sum
     | Aggregation type:........... sum
     | Title:
     | Daily rain
     | Description:
     | Rain per day in mm
     | Semantic type:.............. sum
     | Aggregation type:........... sum
     | Title:
     | Rain per day
     | Description:
     | Rain per day in mm
    ```

### Change the metadata of a vector dataset

The dataset `gauges` of type `stvds` holds one point map. The call changes the
title and gives an **aggr_type**, which a vector dataset does not have: the
module warns, which is not shown here, and applies the title. The output of
`t.info -g` has a line for the semantic type and none for the aggregation
type. Datasets of type `str3ds` are handled like those of type `strds`.

=== "Command line"

    ```sh
    echo "640000,220000,3.0" | v.in.ascii input=- output=gauge_1 \
        separator=comma \
        columns="x double precision, y double precision, speed double precision"
    t.create type=stvds output=gauges title="Gauges" description="Wind gauges"
    t.register -i type=vector input=gauges maps=gauge_1 \
        start=2026-06-01 increment="1 day"
    t.support type=stvds input=gauges title="Wind gauges" aggr_type=average
    t.info type=stvds input=gauges | grep -A1 "Title:"
    t.info -g type=stvds input=gauges | grep -E "^(semantic|aggregation)"
    ```

    ```text
     | Title:
     | Wind gauges
    semantic_type=mean
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.v_in_ascii(
        input=StringIO("640000,220000,3.0\n"),
        output="gauge_1",
        separator="comma",
        columns="x double precision, y double precision, speed double precision",
    )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="Wind gauges")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauge_1",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_support(type="stvds", input="gauges", title="Wind gauges", aggr_type="average")
    lines = tools.t_info(type="stvds", input="gauges").stdout.splitlines()
    first = next(i for i, line in enumerate(lines) if "Title:" in line)
    print("\n".join(lines[first : first + 2]))
    info = tools.t_info(type="stvds", input="gauges", flags="g").keyval
    for key in ("semantic_type", "aggregation_type"):
        if key in info:
            print(f"{key}={info[key]}")
    ```

    ```text
     | Title:
     | Wind gauges
    semantic_type=mean
    ```

### Read maps that were made again

The dataset `temperature_monthly` holds twelve monthly mean air temperatures of
2020 in degree Celsius, one map per month, generated from the elevation model
(about -6.5 degree per 1000 m, with a yearly cycle that peaks in July). The
dataset `temperature_summer` holds the maps of June, July and August with the
times they have in the temporal database. Then the July map is made again with a
correction of +2 degrees Celsius. Both datasets still report the range of values
from before.

A call with **-u** does not change that, because **-u** works on the entries of
the temporal database, and these still hold the old values of the July map. A
call with **-m** reads the July map from the spatial database. The largest value
of `temperature_monthly` and of `temperature_summer` rises from 28.4 to 30.4
degree, and the smallest values stay, because the coldest map of each dataset is
not the one of July. Only
`temperature_monthly` was named in the call, but `temperature_summer` holds the
July map and follows.

=== "Command line"

    ```sh
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
    t.create output=temperature_summer title="Summer air temperature" \
        description="Monthly mean air temperature June to August 2020"
    t.register input=temperature_summer \
        maps=temperature_monthly_2020_06,temperature_monthly_2020_07,temperature_monthly_2020_08
    r.mapcalc --overwrite \
        expression="temperature_monthly_2020_07 = round((temperature_monthly_2020_07 + 2) * 10) / 10.0"
    t.support -u input=temperature_monthly
    t.info -g input=temperature_monthly | grep -E "^(min_min|max_max)="
    t.info -g input=temperature_summer | grep -E "^(min_min|max_max)="
    t.support -m input=temperature_monthly
    t.info -g input=temperature_monthly | grep -E "^(min_min|max_max)="
    t.info -g input=temperature_summer | grep -E "^(min_min|max_max)="
    ```

    ```text
    min_min=-7.0
    max_max=28.4
    min_min=12.0
    max_max=28.4
    min_min=-7.0
    max_max=30.4
    min_min=12.0
    max_max=30.4
    ```

=== "Python (grass.tools)"

    ```python
    def show_range(name):
        info = tools.t_info(input=name, flags="g").keyval
        for key in ("min_min", "max_max"):
            print(f"{key}={info[key]}")


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
    tools.t_create(
        output="temperature_summer",
        title="Summer air temperature",
        description="Monthly mean air temperature June to August 2020",
    )
    tools.t_register(
        input="temperature_summer",
        maps="temperature_monthly_2020_06,temperature_monthly_2020_07,temperature_monthly_2020_08",
    )
    tools.r_mapcalc(
        expression="temperature_monthly_2020_07 = round((temperature_monthly_2020_07 + 2) * 10) / 10.0",
        overwrite=True,
    )
    tools.t_support(input="temperature_monthly", flags="u")
    show_range("temperature_monthly")
    show_range("temperature_summer")
    tools.t_support(input="temperature_monthly", flags="m")
    show_range("temperature_monthly")
    show_range("temperature_summer")
    ```

    ```text
    min_min=-7.0
    max_max=28.4
    min_min=12.0
    max_max=28.4
    min_min=-7.0
    max_max=30.4
    min_min=12.0
    max_max=30.4
    ```

### Unregister maps that are gone

The map of August is removed from the spatial database with *g.remove*, which
leaves it registered in `temperature_monthly` and `temperature_summer`. The call
with **-m** finds that it is gone, deletes it from the temporal database and
updates both datasets: `temperature_monthly` keeps eleven maps and
`temperature_summer` keeps two. The dataset `temperature_summer` was not named
in the call.

=== "Command line"

    ```sh
    g.remove -f type=raster name=temperature_monthly_2020_08
    t.support -m input=temperature_monthly
    t.list type=strds mapset=. columns=name,number_of_maps
    t.rast.list input=temperature_summer columns=name,start_time
    ```

    ```text
    rain|3
    temperature_monthly|11
    temperature_summer|2
    name|start_time
    temperature_monthly_2020_06|2020-06-01 00:00:00
    temperature_monthly_2020_07|2020-07-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_remove(type="raster", name="temperature_monthly_2020_08", flags="f")
    tools.t_support(input="temperature_monthly", flags="m")
    print(tools.t_list(type="strds", mapset=".", columns="name,number_of_maps").text)
    print(tools.t_rast_list(input="temperature_summer", columns="name,start_time").text)
    ```

    ```text
    rain|3
    temperature_monthly|11
    temperature_summer|2
    name|start_time
    temperature_monthly_2020_06|2020-06-01 00:00:00
    temperature_monthly_2020_07|2020-07-01 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.remove](g.remove.md), [t.create](t.create.md), [t.info](t.info.md),
[t.register](t.register.md), [t.unregister](t.unregister.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
