## DESCRIPTION

*t.rast3d.extract* selects maps of a space time 3D raster dataset and
registers them in a new space time 3D raster dataset. On the way, it can
compute a new 3D raster map from each selected map with an
*[r3.mapcalc](r3.mapcalc.md)* expression. Use it to cut a time window out of a
dataset, to drop the maps whose values do not matter, or to derive a dataset by
map algebra when the same expression applies to every map. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast3d.mapcalc](t.rast3d.mapcalc.md)* computes from more than one
dataset, and *[t.rast3d.list](t.rast3d.list.md)* lists the maps of the result.
The tool works like *[t.rast.extract](t.rast.extract.md)*, on space time 3D
raster datasets (STR3DS) and 3D raster maps instead of space time raster
datasets and raster maps.

The option **input** names the space time 3D raster dataset, the option
**output** the new one. The new dataset takes the temporal type and the
semantic type of the input dataset. The output always belongs to the current
mapset. An existing output dataset is refused unless the flag **--overwrite**
is given; then it is replaced.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2020-06-01'`, which selects the maps that start
on 1 June 2020 or later. Without **where**, all maps are selected.

### Register or compute

Without **expression**, *t.rast3d.extract* creates no map. It registers the
selected maps themselves in the new dataset, so a map is then part of two
datasets and the data are not duplicated.

With **expression**, the tool runs *r3.mapcalc* once for each selected map and
registers the new maps, with the start and end time of the map they come from,
in the new dataset. The expression is the right side of an *r3.mapcalc*
expression, without the `map =` of a full one. The name of the input dataset
stands for the selected map of each step, so `2 * temperature_profile` doubles
the map of every step of the dataset `temperature_profile`. Any other 3D raster
map can be used in the expression by name. The new maps belong to the current
mapset. The expression needs the option **basename**.

The new maps are named after **basename**, followed by an underscore and a
suffix that the option **suffix** chooses.

- `gran` (the default) takes the start time of the map, cut to the unit of the
  granularity of the input dataset: year and month for a granularity of three
  months, year, month and day for a granularity of one day (`2026_03_01`). A
  monthly series from the last day of a month (January 31, February 28) has
  the granularity of one month and gets year and month (`2026_01`). A dataset
  of a single time instant has no granularity; `gran` then takes the full
  start time, as `time` does.
- `time` takes the full start time: `2026_03_01T00_00_00`.
- `num` numbers the selected maps from 1 in the order of their start time and
  map id, with five digits (`00001`); the number counts also the maps that come
  out empty. `num%03` gives three digits (`001`).
- With relative time, a start time is a number without a calendar date. Every
  suffix then gives the number, as `num` does.

Two different maps of one time, such as two maps of January 2001, get the same
name from the suffix. The first of them, in the order of start time and map id,
keeps the name; the second and every further map get the number `_2`, `_3` and
so on after it. A number that another new map has as its name is skipped.

A new map that has no valid cell, that is, no minimum and no maximum, is
empty. By default it is not registered in the new dataset and the map is
removed after the run. The flag **-n** registers the empty maps and keeps
them. An expression such as `if(temperature_profile > 20, temperature_profile,
null())` therefore selects
maps by their values as well.

The option **nprocs** sets the number of *r3.mapcalc* processes that run at the
same time. The default is `1`. The result does not depend on it.

## NOTES

If **where** selects no map, or the input dataset has none, *t.rast3d.extract*
warns "Nothing found in the database for space time dataset" and makes no
output dataset; for a **where** that selects nothing, the message adds that
"Dataset is empty or where clause is too constrained or incorrect". A condition
with a syntax error stops with the error "Invalid where condition".

The tool stops with an error if **expression** is given without **basename**
("You need to specify the base name of new created maps"), if the input dataset
does not exist, if the output dataset exists and **--overwrite** is not given,
and if **suffix** is not `gran`, `time`, `num` or `num%NN` ("Invalid
suffix"). A dot in the name of the output dataset is refused: "a dot is not
allowed". An **expression** that *r3.mapcalc* does not accept stops with
"Error in computation process". If a new map is already in the temporal
database and **--overwrite** is not given, the tool stops before it computes
anything, with "Map ... is already in temporal database, use overwrite flag to
overwrite", and makes no dataset.

A dataset of another mapset works as input. With an **expression** the new
maps belong to the current mapset. Without one the new dataset registers the
maps of the input, which stay in their mapset: the tool inserts them into the
temporal database of the current mapset, as *[t.copy](t.copy.md)* does without
**-c**. The last example shows both.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast3d_extract` and sets the computational region
to North Carolina with cells of 1 km, in the plane and in the vertical (the
option **res3**), and three layers of 1000 m from 0 to 3000 m; the later
examples work in this mapset and region, except the last, which creates a
second mapset with the same region. The examples about names, relative time and
other mapsets use 3D maps with small constant values, so that the results can
be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast3d_extract -->

<!-- markdownlint-disable MD046 -->

### Select maps by time

The dataset `temperature_profile` has twelve 3D raster maps of the monthly mean
air temperature in 2020, in degrees Celsius rounded to tenths. They are
generated from the height `z()` of the cell: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its maximum
in July, 6.5 degrees less for every 1000 m of height, and 1 degree more for
every 100 km to the south. Each map is an interval of one month.

The first block creates the maps and the dataset. The second block extracts the
summer months, June to August, into the dataset `summer`. There is no
**expression**, so no map is made: the third block lists the 3D raster maps of
the mapset, and they are still the twelve maps of `temperature_profile`. The
dataset `summer` lists three of them. The fourth block shows what the new
dataset takes from the input: the temporal type and the semantic type, and the
start and end time that follow from the maps it holds.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_extract
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    for month in $(seq 12); do
        echo "temperature_profile_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * z()" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r3.mapcalc file=-
    t.create type=str3ds output=temperature_profile title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius, 0 to 3000 m"
    t.register -i type=raster_3d input=temperature_profile \
        maps=$(g.list type=raster_3d pattern="temperature_profile_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    ```

    ```sh
    t.rast3d.extract input=temperature_profile output=summer \
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'"
    t.rast3d.list input=summer
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_profile_2020_06|t_rast3d_extract|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_extract|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_extract|2020-08-01 00:00:00|2020-09-01 00:00:00
    ```

    ```sh
    g.list type=raster_3d mapset=.
    ```

    ```text
    temperature_profile_2020_01
    temperature_profile_2020_02
    temperature_profile_2020_03
    temperature_profile_2020_04
    temperature_profile_2020_05
    temperature_profile_2020_06
    temperature_profile_2020_07
    temperature_profile_2020_08
    temperature_profile_2020_09
    temperature_profile_2020_10
    temperature_profile_2020_11
    temperature_profile_2020_12
    ```

    ```sh
    t.info -g type=str3ds input=summer | grep -E "^(temporal_type|semantic_type|start_time|end_time)="
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2020-06-01 00:00:00'
    end_time='2020-09-01 00:00:00'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast3d_extract")
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    months = range(1, 13)
    tools.r3_mapcalc(
        expression="\n".join(
            f"temperature_profile_2020_{month:02d} = round((16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * z()"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        type="str3ds",
        output="temperature_profile",
        title="Air temperature",
        description="Monthly mean air temperature 2020 in degree Celsius, 0 to 3000 m",
    )
    tools.t_register(
        type="raster_3d",
        input="temperature_profile",
        maps=",".join(f"temperature_profile_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="summer",
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'",
    )
    print(tools.t_rast3d_list(input="summer").text)
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_profile_2020_06|t_rast3d_extract|2020-06-01 00:00:00|2020-07-01 00:00:00
    temperature_profile_2020_07|t_rast3d_extract|2020-07-01 00:00:00|2020-08-01 00:00:00
    temperature_profile_2020_08|t_rast3d_extract|2020-08-01 00:00:00|2020-09-01 00:00:00
    ```

    ```python
    print(tools.g_list(type="raster_3d", mapset=".").text)
    ```

    ```text
    temperature_profile_2020_01
    temperature_profile_2020_02
    temperature_profile_2020_03
    temperature_profile_2020_04
    temperature_profile_2020_05
    temperature_profile_2020_06
    temperature_profile_2020_07
    temperature_profile_2020_08
    temperature_profile_2020_09
    temperature_profile_2020_10
    temperature_profile_2020_11
    temperature_profile_2020_12
    ```

    ```python
    info = tools.t_info(type="str3ds", input="summer", flags="g").keyval
    for key in ("temporal_type", "semantic_type", "start_time", "end_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    temporal_type=absolute
    semantic_type=mean
    start_time='2020-06-01 00:00:00'
    end_time='2020-09-01 00:00:00'
    ```

### Compute new maps from the selected maps

The first block converts the maps of the first quarter to degrees Fahrenheit.
The expression names the dataset, which stands for the map of each step. The new
maps are named `fahrenheit`, an underscore and the month of the map (the
granularity of `temperature_profile` is one month), and each has the time of its
source map. The result is rounded to tenths, so that the values are the same on
every system. **nprocs** lets two *r3.mapcalc* processes run at the same time;
the result is the same as with one process.

The second block shows that the expression may use any 3D raster map. The map
`correction` is 1.5 everywhere, as a correction of a sensor that reads 1.5
degrees too low; **where** selects the first two months, and the new maps hold
the values of their source maps plus 1.5.

=== "Command line"

    ```sh
    t.rast3d.extract input=temperature_profile output=fahrenheit \
        basename=fahrenheit where="start_time < '2020-04-01'" \
        expression="round((temperature_profile * 1.8 + 32) * 10) / 10.0" nprocs=2
    t.rast3d.list input=fahrenheit columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    fahrenheit_2020_01|2020-01-01 00:00:00|10.8|40.3
    fahrenheit_2020_02|2020-02-01 00:00:00|12.4|41.7
    fahrenheit_2020_03|2020-03-01 00:00:00|18.5|47.8
    ```

    ```sh
    r3.mapcalc expression="correction = 1.5"
    t.rast3d.extract input=temperature_profile output=corrected \
        basename=corrected where="start_time < '2020-03-01'" \
        expression="round((temperature_profile + correction) * 10) / 10.0"
    t.rast3d.list input=corrected columns=name,min,max
    ```

    ```text
    name|min|max
    corrected_2020_01|-10.3|6.1
    corrected_2020_02|-9.4|6.9
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="fahrenheit",
        basename="fahrenheit",
        where="start_time < '2020-04-01'",
        expression="round((temperature_profile * 1.8 + 32) * 10) / 10.0",
        nprocs=2,
    )
    print(tools.t_rast3d_list(input="fahrenheit", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    fahrenheit_2020_01|2020-01-01 00:00:00|10.8|40.3
    fahrenheit_2020_02|2020-02-01 00:00:00|12.4|41.7
    fahrenheit_2020_03|2020-03-01 00:00:00|18.5|47.8
    ```

    ```python
    tools.r3_mapcalc(expression="correction = 1.5")
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="corrected",
        basename="corrected",
        where="start_time < '2020-03-01'",
        expression="round((temperature_profile + correction) * 10) / 10.0",
    )
    print(tools.t_rast3d_list(input="corrected", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    corrected_2020_01|-10.3|6.1
    corrected_2020_02|-9.4|6.9
    ```

### Select maps by their values

An expression that sets cells to null selects maps. The first block takes the
maps from August to October, three maps, and keeps the values above 20 degrees.
The maps of August and September have cells above 20 degrees; the map of
October has none (its largest value is 16.1), so it is empty. The empty map is
not registered in `warm`, and the second block shows that it is removed: only
two maps are left in the mapset.

The third block runs the same call with the flag **-n**. The dataset `warm_all`
registers the empty map as well, with `None` as its smallest and largest value,
and the mapset keeps all three maps.

=== "Command line"

    ```sh
    t.rast3d.extract input=temperature_profile output=warm basename=warm \
        where="start_time >= '2020-08-01' and start_time < '2020-11-01'" \
        expression="if(temperature_profile > 20, temperature_profile, null())"
    t.rast3d.list input=warm columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    warm_2020_08|2020-08-01 00:00:00|21.3|24.6
    warm_2020_09|2020-09-01 00:00:00|20.1|21.2
    ```

    ```sh
    g.list type=raster_3d pattern="warm*" mapset=.
    ```

    ```text
    warm_2020_08
    warm_2020_09
    ```

    ```sh
    t.rast3d.extract -n input=temperature_profile output=warm_all \
        basename=warm_all \
        where="start_time >= '2020-08-01' and start_time < '2020-11-01'" \
        expression="if(temperature_profile > 20, temperature_profile, null())"
    t.rast3d.list input=warm_all columns=name,start_time,min,max
    g.list type=raster_3d pattern="warm_all*" mapset=.
    ```

    ```text
    name|start_time|min|max
    warm_all_2020_08|2020-08-01 00:00:00|21.3|24.6
    warm_all_2020_09|2020-09-01 00:00:00|20.1|21.2
    warm_all_2020_10|2020-10-01 00:00:00|None|None
    warm_all_2020_08
    warm_all_2020_09
    warm_all_2020_10
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="warm",
        basename="warm",
        where="start_time >= '2020-08-01' and start_time < '2020-11-01'",
        expression="if(temperature_profile > 20, temperature_profile, null())",
    )
    print(tools.t_rast3d_list(input="warm", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    warm_2020_08|2020-08-01 00:00:00|21.3|24.6
    warm_2020_09|2020-09-01 00:00:00|20.1|21.2
    ```

    ```python
    print(tools.g_list(type="raster_3d", pattern="warm*", mapset=".").text)
    ```

    ```text
    warm_2020_08
    warm_2020_09
    ```

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="warm_all",
        basename="warm_all",
        where="start_time >= '2020-08-01' and start_time < '2020-11-01'",
        expression="if(temperature_profile > 20, temperature_profile, null())",
        flags="n",
    )
    columns = "name,start_time,min,max"
    print(tools.t_rast3d_list(input="warm_all", columns=columns).text)
    print(tools.g_list(type="raster_3d", pattern="warm_all*", mapset=".").text)
    ```

    ```text
    name|start_time|min|max
    warm_all_2020_08|2020-08-01 00:00:00|21.3|24.6
    warm_all_2020_09|2020-09-01 00:00:00|20.1|21.2
    warm_all_2020_10|2020-10-01 00:00:00|None|None
    warm_all_2020_08
    warm_all_2020_09
    warm_all_2020_10
    ```

### Name the new maps

The option **suffix** chooses the end of the names. Each of the first three
blocks copies the maps of the first quarter of `temperature_profile` with the
expression `temperature_profile` and lists the names: `time` gives the full
start time, `num` a number of five digits and `num%03` a number of three digits.

The dataset `soundings` in the fourth block has two maps of the same day,
`sounding_a` with the value 1 and `sounding_b` with the value 2. Their names
from the default suffix would be the same. The first map in the order of start
time and map id, `sounding_a`, keeps `ten_2026_06_01`; the second one becomes
`ten_2026_06_01_2`. The values are 10 and 20.

=== "Command line"

    ```sh
    t.rast3d.extract input=temperature_profile output=by_time basename=by_time \
        where="start_time < '2020-04-01'" expression="temperature_profile" \
        suffix=time
    t.rast3d.list input=by_time columns=name
    ```

    ```text
    name
    by_time_2020_01_01T00_00_00
    by_time_2020_02_01T00_00_00
    by_time_2020_03_01T00_00_00
    ```

    ```sh
    t.rast3d.extract input=temperature_profile output=by_number \
        basename=by_number where="start_time < '2020-04-01'" \
        expression="temperature_profile" suffix=num
    t.rast3d.list input=by_number columns=name
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    ```

    ```sh
    t.rast3d.extract input=temperature_profile output=by_width \
        basename=by_width where="start_time < '2020-04-01'" \
        expression="temperature_profile" suffix=num%03
    t.rast3d.list input=by_width columns=name
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    ```

    ```sh
    r3.mapcalc expression="sounding_a = 1"
    r3.mapcalc expression="sounding_b = 2"
    t.create type=str3ds output=soundings title="Two soundings of one day" \
        description="Two maps with the same time"
    t.register type=raster_3d input=soundings maps=sounding_a,sounding_b \
        start=2026-06-01 end=2026-06-02
    t.rast3d.extract input=soundings output=soundings_ten basename=ten \
        expression="soundings * 10"
    t.rast3d.list input=soundings_ten columns=name,start_time,min order=name
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="by_time",
        basename="by_time",
        where="start_time < '2020-04-01'",
        expression="temperature_profile",
        suffix="time",
    )
    print(tools.t_rast3d_list(input="by_time", columns="name").text)
    ```

    ```text
    name
    by_time_2020_01_01T00_00_00
    by_time_2020_02_01T00_00_00
    by_time_2020_03_01T00_00_00
    ```

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="by_number",
        basename="by_number",
        where="start_time < '2020-04-01'",
        expression="temperature_profile",
        suffix="num",
    )
    print(tools.t_rast3d_list(input="by_number", columns="name").text)
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    ```

    ```python
    tools.t_rast3d_extract(
        input="temperature_profile",
        output="by_width",
        basename="by_width",
        where="start_time < '2020-04-01'",
        expression="temperature_profile",
        suffix="num%03",
    )
    print(tools.t_rast3d_list(input="by_width", columns="name").text)
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    ```

    ```python
    tools.r3_mapcalc(expression="sounding_a = 1")
    tools.r3_mapcalc(expression="sounding_b = 2")
    tools.t_create(
        type="str3ds",
        output="soundings",
        title="Two soundings of one day",
        description="Two maps with the same time",
    )
    tools.t_register(
        type="raster_3d",
        input="soundings",
        maps="sounding_a,sounding_b",
        start="2026-06-01",
        end="2026-06-02",
    )
    tools.t_rast3d_extract(
        input="soundings",
        output="soundings_ten",
        basename="ten",
        expression="soundings * 10",
    )
    result = tools.t_rast3d_list(
        input="soundings_ten", columns="name,start_time,min", order="name"
    )
    print(result.text)
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

### Extract from a dataset with relative time

The dataset `model` has two maps of six hours each, from 0 to 6 and from 6 to
12 hours, with the values 1 and 2. In a dataset with relative time a start time
is a number, so the names of the new maps carry the number of the map instead of
a date. The first block keeps the values above 1. The number counts all selected
maps, also the empty one: the first map is empty and left out, so the remaining
map is `m_00002`. The new dataset has the times and the unit of the input. The
second block takes `time` as the suffix; with relative time it gives the number
as well.

=== "Command line"

    ```sh
    r3.mapcalc expression="model_hour_0 = 1"
    r3.mapcalc expression="model_hour_6 = 2"
    t.create type=str3ds output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i type=raster_3d input=model maps=model_hour_0,model_hour_6 \
        start=0 increment=6 unit=hours
    t.rast3d.extract input=model output=model_high basename=m \
        expression="if(model > 1, model, null())"
    t.rast3d.list input=model_high columns=name,start_time,end_time,min
    t.info -g type=str3ds input=model_high | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|start_time|end_time|min
    m_00002|6|12|2.0
    temporal_type=relative
    unit=hours
    ```

    ```sh
    t.rast3d.extract input=model output=model_time basename=t \
        expression="model" suffix=time
    t.rast3d.list input=model_time columns=name
    ```

    ```text
    name
    t_00001
    t_00002
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="model_hour_0 = 1")
    tools.r3_mapcalc(expression="model_hour_6 = 2")
    tools.t_create(
        type="str3ds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        type="raster_3d",
        input="model",
        maps="model_hour_0,model_hour_6",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    tools.t_rast3d_extract(
        input="model",
        output="model_high",
        basename="m",
        expression="if(model > 1, model, null())",
    )
    columns = "name,start_time,end_time,min"
    print(tools.t_rast3d_list(input="model_high", columns=columns).text)
    info = tools.t_info(type="str3ds", input="model_high", flags="g").keyval
    for key in ("temporal_type", "unit"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time|min
    m_00002|6|12|2.0
    temporal_type=relative
    unit=hours
    ```

    ```python
    tools.t_rast3d_extract(
        input="model",
        output="model_time",
        basename="t",
        expression="model",
        suffix="time",
    )
    print(tools.t_rast3d_list(input="model_time", columns="name").text)
    ```

    ```text
    name
    t_00001
    t_00002
    ```

### Extract from a dataset of another mapset

The dataset `model` stays in the mapset `t_rast3d_extract`. The first block
creates the mapset `t_rast3d_extract_2`, sets the same region, and extracts
with an expression from `model@t_rast3d_extract`, which the name with its
mapset selects. The name `model` in the expression stands for the maps of the
dataset, though it has no mapset, and the output dataset `model_copy` and its
maps `copy_00001` and `copy_00002` belong to `t_rast3d_extract_2`. The `id`
column shows the mapset.

The second block extracts without an expression. The new dataset
`model_shared` belongs to `t_rast3d_extract_2` and registers the maps of
`model@t_rast3d_extract` themselves. The `id` column shows that they stay in
`t_rast3d_extract`, and `g.list` shows that `t_rast3d_extract_2` holds only the
two copies of the first block.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast3d_extract_2
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    t.rast3d.extract input=model@t_rast3d_extract output=model_copy \
        basename=copy expression="model" suffix=num
    t.rast3d.list input=model_copy columns=id,start_time,min
    ```

    ```text
    id|start_time|min
    copy_00001@t_rast3d_extract_2|0|1.0
    copy_00002@t_rast3d_extract_2|6|2.0
    ```

    ```sh
    t.rast3d.extract input=model@t_rast3d_extract output=model_shared
    t.rast3d.list input=model_shared columns=id,start_time,min
    g.list type=raster_3d mapset=.
    ```

    ```text
    id|start_time|min
    model_hour_0@t_rast3d_extract|0|1.0
    model_hour_6@t_rast3d_extract|6|2.0
    copy_00001
    copy_00002
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast3d_extract_2", flags="c")
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    tools.t_rast3d_extract(
        input="model@t_rast3d_extract",
        output="model_copy",
        basename="copy",
        expression="model",
        suffix="num",
    )
    print(tools.t_rast3d_list(input="model_copy", columns="id,start_time,min").text)
    ```

    ```text
    id|start_time|min
    copy_00001@t_rast3d_extract_2|0|1.0
    copy_00002@t_rast3d_extract_2|6|2.0
    ```

    ```python
    tools.t_rast3d_extract(input="model@t_rast3d_extract", output="model_shared")
    print(
        tools.t_rast3d_list(input="model_shared", columns="id,start_time,min").text
    )
    print(tools.g_list(type="raster_3d", mapset=".").text)
    ```

    ```text
    id|start_time|min
    model_hour_0@t_rast3d_extract|0|1.0
    model_hour_6@t_rast3d_extract|6|2.0
    copy_00001
    copy_00002
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [r3.mapcalc](r3.mapcalc.md),
[t.copy](t.copy.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.extract](t.rast.extract.md), [t.rast3d.list](t.rast3d.list.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
