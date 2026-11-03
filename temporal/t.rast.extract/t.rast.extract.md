## DESCRIPTION

*t.rast.extract* selects maps of a space time raster dataset and registers
them in a new space time raster dataset. On the way, it can compute a new map
from each selected map with a *[r.mapcalc](r.mapcalc.md)* expression. Use it
to cut a time window out of a dataset, to drop the maps whose values do not
matter, or to derive a dataset by map algebra when the same expression applies
to every map. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.rast.mapcalc](t.rast.mapcalc.md)* computes from more than one
dataset, and *[t.rast.list](t.rast.list.md)* lists the maps of the result.

The option **input** names the space time raster dataset, the option **output**
the new one. The new dataset takes the temporal type and the semantic type of
the input dataset. The output always belongs to the current mapset. An
existing output dataset is refused unless the flag **--overwrite** is given;
then it is replaced.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2020-06-01'`, which selects the maps that start
on 1 June 2020 or later. Without **where**, all maps are selected.

### Register or compute

Without **expression**, *t.rast.extract* creates no map. It registers the
selected maps themselves in the new dataset, so a map is then part of two
datasets and the data are not duplicated.

With **expression**, the tool runs *r.mapcalc* once for each selected map and
registers the new maps, with the start and end time of the map they come from,
in the new dataset. The expression is the right side of an *r.mapcalc*
expression, without the `map =` of a full one. The name of the input dataset
stands for the selected map of each step, so `2 * temperature` doubles the
map of every step of the dataset `temperature`. Any other raster map can be
used in the expression by name. The new maps belong to the current mapset.
The expression needs the option **basename**.

The new maps are named after **basename**, followed by an underscore and a
suffix that the option **suffix** chooses. A map with a semantic label gets the
label between the base name and the suffix: `basename_label_suffix`. The new
map keeps the semantic label.

- `gran` (the default) takes the start time of the map, cut to the unit of the
  granularity of the input dataset: year and month for a granularity of three
  months, year, month and day for a granularity of one day (`2026_03_01`). A
  dataset of a single time instant has no granularity; `gran` then takes the
  full start time, as `time` does.
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
them. An expression such as `if(temperature > 6, temperature, null())`
therefore selects maps by their values as well.

The option **nprocs** sets the number of *r.mapcalc* processes that run at the
same time. The default is `1`. The result does not depend on it.

## NOTES

The expression is the right side of an *r.mapcalc* expression only. A call
with `expression="if(temperature_monthly < 0, null(), temperature_monthly)"`, for
instance, sets the negative values of a dataset `temperature_monthly` to null.

If **where** selects no map, or the input dataset has none, *t.rast.extract*
warns "Nothing found in the database for space time dataset" and makes no
output dataset; for a **where** that selects nothing, the message adds that
"Dataset is empty or where clause is too constrained or incorrect". A
condition with a syntax error stops with the error "Invalid where condition".

The tool stops with an error if **expression** is given without **basename**
("You need to specify the base name of new created maps"), if the input dataset
does not exist, if the output dataset exists and **--overwrite** is not given,
and if **suffix** is not `gran`, `time`, `num` or `num%NN` ("Invalid
suffix"). A dot in the name of the output dataset is refused: "a dot
is not allowed". An **expression** that *r.mapcalc* does not accept stops with
"Error in computation process". If a new map is already in the temporal
database and **--overwrite** is not given, the tool stops before it computes
anything, with "Map ... is already in temporal database, use overwrite flag to
overwrite", and makes no dataset.

The last example shows that a dataset of another mapset works as input when an
**expression** is given. Without an **expression**, such a dataset is refused,
and the empty output dataset that the refusal leaves behind has to be removed
with *[t.remove](t.remove.md)*. Add an **expression** such as the name of the
input dataset to copy the maps instead.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_extract` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region, except the last, which creates a second mapset with the same
region. The examples that show how names and times work use maps with small
constant values, so that the results can be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_extract -->

<!-- markdownlint-disable MD046 -->

### Select maps by time

The dataset `temperature_monthly` holds twelve maps of the monthly mean air
temperature in 2020, in degrees Celsius rounded to tenths. They are generated
from the elevation model `elev_state_500m`: 16.5 degrees at sea level and the
northing 160 km, an annual cycle of plus and minus 10.5 degrees with its
maximum in July, 6.5 degrees less for every 1000 m of elevation, and 1 degree
more for every 100 km to the south. Each map is an interval of one month.

The first block extracts the summer months, June to August, into the dataset
`summer`. There is no **expression**, so no map is made: the second block lists
the raster maps of the mapset, and they are still the twelve maps of
`temperature_monthly`. The dataset `summer` lists three of them. The third
block shows what the new dataset takes from the input: the temporal type and
the semantic type, and the start and end time that follow from the maps it
holds.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_extract
    g.region raster=elev_state_500m res=1000 -a
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
    t.rast.extract input=temperature_monthly output=summer \
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'"
    t.rast.list input=summer columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    temperature_monthly_2020_06|2020-06-01 00:00:00|2020-07-01 00:00:00|12.0|26.5
    temperature_monthly_2020_07|2020-07-01 00:00:00|2020-08-01 00:00:00|13.9|28.4
    temperature_monthly_2020_08|2020-08-01 00:00:00|2020-09-01 00:00:00|13.1|27.6
    ```

    ```sh
    g.list type=raster mapset=.
    ```

    ```text
    temperature_monthly_2020_01
    temperature_monthly_2020_02
    temperature_monthly_2020_03
    temperature_monthly_2020_04
    temperature_monthly_2020_05
    temperature_monthly_2020_06
    temperature_monthly_2020_07
    temperature_monthly_2020_08
    temperature_monthly_2020_09
    temperature_monthly_2020_10
    temperature_monthly_2020_11
    temperature_monthly_2020_12
    ```

    ```sh
    t.info -g summer | grep -E "^(temporal_type|semantic_type|start_time|end_time)="
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
    tools.g_mapset(flags="c", mapset="t_rast_extract")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
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
    tools.t_rast_extract(
        input="temperature_monthly",
        output="summer",
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'",
    )
    columns = "name,start_time,end_time,min,max"
    print(tools.t_rast_list(input="summer", columns=columns).text)
    ```

    ```text
    name|start_time|end_time|min|max
    temperature_monthly_2020_06|2020-06-01 00:00:00|2020-07-01 00:00:00|12.0|26.5
    temperature_monthly_2020_07|2020-07-01 00:00:00|2020-08-01 00:00:00|13.9|28.4
    temperature_monthly_2020_08|2020-08-01 00:00:00|2020-09-01 00:00:00|13.1|27.6
    ```

    ```python
    print(tools.g_list(type="raster", mapset=".").text)
    ```

    ```text
    temperature_monthly_2020_01
    temperature_monthly_2020_02
    temperature_monthly_2020_03
    temperature_monthly_2020_04
    temperature_monthly_2020_05
    temperature_monthly_2020_06
    temperature_monthly_2020_07
    temperature_monthly_2020_08
    temperature_monthly_2020_09
    temperature_monthly_2020_10
    temperature_monthly_2020_11
    temperature_monthly_2020_12
    ```

    ```python
    info = tools.t_info(input="summer", flags="g").keyval
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

The first block converts the summer months to degrees Fahrenheit. The
expression names the input dataset `temperature_monthly`, which stands for the
map of each step, multiplies it by 1.8, adds 32 and rounds to tenths, as the
input is. The new maps are named `fahrenheit`, an underscore and the month of
the map (the granularity of `temperature_monthly` is one month), and each has
the time of its source map. **nprocs** lets two *r.mapcalc* processes run at the
same time; the result is the same as with one process. The values follow from
the ones of the previous example: the coolest cell of June, 12.0 degrees, is
53.6 degrees Fahrenheit, and the warmest cell of July, 28.4 degrees, is 83.1.

The second block shows that the expression may use any raster map. The cells of
the elevation model `elev_state_500m` that lie 600 m or higher are the
mountains; **where** selects January and February, and the new maps hold the
temperature of these cells and null elsewhere. The coldest cell of the whole
year, -7.0 degrees in January, lies there.

=== "Command line"

    ```sh
    t.rast.extract input=temperature_monthly output=temperature_fahrenheit \
        basename=fahrenheit nprocs=2 \
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'" \
        expression="round((temperature_monthly * 1.8 + 32) * 10) / 10.0"
    t.rast.list input=temperature_fahrenheit columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    fahrenheit_2020_06|2020-06-01 00:00:00|53.6|79.7
    fahrenheit_2020_07|2020-07-01 00:00:00|57.0|83.1
    fahrenheit_2020_08|2020-08-01 00:00:00|55.6|81.7
    ```

    ```sh
    t.rast.extract input=temperature_monthly output=winter_mountains \
        basename=winter_mountains where="start_time < '2020-03-01'" \
        expression="if(elev_state_500m >= 600, temperature_monthly, null())"
    t.rast.list input=winter_mountains columns=name,min,max
    ```

    ```text
    name|min|max
    winter_mountains_2020_01|-7.0|2.2
    winter_mountains_2020_02|-6.1|3.1
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="temperature_fahrenheit",
        basename="fahrenheit",
        nprocs=2,
        where="start_time >= '2020-06-01' and start_time < '2020-09-01'",
        expression="round((temperature_monthly * 1.8 + 32) * 10) / 10.0",
    )
    columns = "name,start_time,min,max"
    print(tools.t_rast_list(input="temperature_fahrenheit", columns=columns).text)
    ```

    ```text
    name|start_time|min|max
    fahrenheit_2020_06|2020-06-01 00:00:00|53.6|79.7
    fahrenheit_2020_07|2020-07-01 00:00:00|57.0|83.1
    fahrenheit_2020_08|2020-08-01 00:00:00|55.6|81.7
    ```

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="winter_mountains",
        basename="winter_mountains",
        where="start_time < '2020-03-01'",
        expression="if(elev_state_500m >= 600, temperature_monthly, null())",
    )
    print(tools.t_rast_list(input="winter_mountains", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    winter_mountains_2020_01|-7.0|2.2
    winter_mountains_2020_02|-6.1|3.1
    ```

### Select maps by their values

An expression that sets cells to null selects maps. The first block takes the
months from May to September, five maps, and keeps the cells with more than
25 degrees. Of the five, the maps of June, July and August have such cells; May
and September stay below 25 degrees everywhere, so their maps are empty. The
empty maps are not registered in `hot`, and the second block shows that they are
removed: only three maps are left in the mapset.

The third block runs the same call with the flag **-n**. The dataset `hot_all`
registers the empty maps as well, with `None` as their smallest and largest
value, and the mapset keeps all five maps.

=== "Command line"

    ```sh
    t.rast.extract input=temperature_monthly output=hot basename=hot \
        where="start_time >= '2020-05-01' and start_time < '2020-10-01'" \
        expression="if(temperature_monthly > 25, temperature_monthly, null())"
    t.rast.list input=hot columns=name,start_time,min,max
    ```

    ```text
    name|start_time|min|max
    hot_2020_06|2020-06-01 00:00:00|25.1|26.5
    hot_2020_07|2020-07-01 00:00:00|25.1|28.4
    hot_2020_08|2020-08-01 00:00:00|25.1|27.6
    ```

    ```sh
    g.list type=raster pattern="hot*" mapset=.
    ```

    ```text
    hot_2020_06
    hot_2020_07
    hot_2020_08
    ```

    ```sh
    t.rast.extract -n input=temperature_monthly output=hot_all basename=hot_all \
        where="start_time >= '2020-05-01' and start_time < '2020-10-01'" \
        expression="if(temperature_monthly > 25, temperature_monthly, null())"
    t.rast.list input=hot_all columns=name,start_time,min,max
    g.list type=raster pattern="hot_all*" mapset=.
    ```

    ```text
    name|start_time|min|max
    hot_all_2020_05|2020-05-01 00:00:00|None|None
    hot_all_2020_06|2020-06-01 00:00:00|25.1|26.5
    hot_all_2020_07|2020-07-01 00:00:00|25.1|28.4
    hot_all_2020_08|2020-08-01 00:00:00|25.1|27.6
    hot_all_2020_09|2020-09-01 00:00:00|None|None
    hot_all_2020_05
    hot_all_2020_06
    hot_all_2020_07
    hot_all_2020_08
    hot_all_2020_09
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="hot",
        basename="hot",
        where="start_time >= '2020-05-01' and start_time < '2020-10-01'",
        expression="if(temperature_monthly > 25, temperature_monthly, null())",
    )
    print(tools.t_rast_list(input="hot", columns="name,start_time,min,max").text)
    ```

    ```text
    name|start_time|min|max
    hot_2020_06|2020-06-01 00:00:00|25.1|26.5
    hot_2020_07|2020-07-01 00:00:00|25.1|28.4
    hot_2020_08|2020-08-01 00:00:00|25.1|27.6
    ```

    ```python
    print(tools.g_list(type="raster", pattern="hot*", mapset=".").text)
    ```

    ```text
    hot_2020_06
    hot_2020_07
    hot_2020_08
    ```

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="hot_all",
        basename="hot_all",
        where="start_time >= '2020-05-01' and start_time < '2020-10-01'",
        expression="if(temperature_monthly > 25, temperature_monthly, null())",
        flags="n",
    )
    print(tools.t_rast_list(input="hot_all", columns="name,start_time,min,max").text)
    print(tools.g_list(type="raster", pattern="hot_all*", mapset=".").text)
    ```

    ```text
    name|start_time|min|max
    hot_all_2020_05|2020-05-01 00:00:00|None|None
    hot_all_2020_06|2020-06-01 00:00:00|25.1|26.5
    hot_all_2020_07|2020-07-01 00:00:00|25.1|28.4
    hot_all_2020_08|2020-08-01 00:00:00|25.1|27.6
    hot_all_2020_09|2020-09-01 00:00:00|None|None
    hot_all_2020_05
    hot_all_2020_06
    hot_all_2020_07
    hot_all_2020_08
    hot_all_2020_09
    ```

### Name the new maps

The option **suffix** chooses the end of the names. Each of the first three
blocks copies the first four maps of `temperature_monthly`, January to April,
with the expression `temperature_monthly` and lists the names: `time` gives the
full start time, `num` a number of five digits and `num%03` a number of three
digits.

The dataset `gauge_pair` in the fourth block has two maps of the same day,
`gauge_a` with the value 1 and `gauge_b` with the value 2. Their names from the
default suffix would be the same. The first map in the order of start time and
map id, `gauge_a`, keeps `ten_2026_06_01`; the second one becomes
`ten_2026_06_01_2`. The values are 10 and 20.

=== "Command line"

    ```sh
    t.rast.extract input=temperature_monthly output=by_time basename=by_time \
        where="start_time < '2020-05-01'" expression="temperature_monthly" \
        suffix=time
    t.rast.list input=by_time columns=name
    ```

    ```text
    name
    by_time_2020_01_01T00_00_00
    by_time_2020_02_01T00_00_00
    by_time_2020_03_01T00_00_00
    by_time_2020_04_01T00_00_00
    ```

    ```sh
    t.rast.extract input=temperature_monthly output=by_number \
        basename=by_number where="start_time < '2020-05-01'" \
        expression="temperature_monthly" suffix=num
    t.rast.list input=by_number columns=name
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```sh
    t.rast.extract input=temperature_monthly output=by_width \
        basename=by_width where="start_time < '2020-05-01'" \
        expression="temperature_monthly" suffix=num%03
    t.rast.list input=by_width columns=name
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```sh
    r.mapcalc expression="gauge_a = 1"
    r.mapcalc expression="gauge_b = 2"
    t.create output=gauge_pair title="Two maps of one day" \
        description="Two maps with the same time"
    t.register input=gauge_pair maps=gauge_a,gauge_b start=2026-06-01 \
        end=2026-06-02
    t.rast.extract input=gauge_pair output=gauge_ten basename=ten \
        expression="gauge_pair * 10"
    t.rast.list input=gauge_ten columns=name,start_time,min order=name
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="by_time",
        basename="by_time",
        where="start_time < '2020-05-01'",
        expression="temperature_monthly",
        suffix="time",
    )
    print(tools.t_rast_list(input="by_time", columns="name").text)
    ```

    ```text
    name
    by_time_2020_01_01T00_00_00
    by_time_2020_02_01T00_00_00
    by_time_2020_03_01T00_00_00
    by_time_2020_04_01T00_00_00
    ```

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="by_number",
        basename="by_number",
        where="start_time < '2020-05-01'",
        expression="temperature_monthly",
        suffix="num",
    )
    print(tools.t_rast_list(input="by_number", columns="name").text)
    ```

    ```text
    name
    by_number_00001
    by_number_00002
    by_number_00003
    by_number_00004
    ```

    ```python
    tools.t_rast_extract(
        input="temperature_monthly",
        output="by_width",
        basename="by_width",
        where="start_time < '2020-05-01'",
        expression="temperature_monthly",
        suffix="num%03",
    )
    print(tools.t_rast_list(input="by_width", columns="name").text)
    ```

    ```text
    name
    by_width_001
    by_width_002
    by_width_003
    by_width_004
    ```

    ```python
    tools.r_mapcalc(expression="gauge_a = 1")
    tools.r_mapcalc(expression="gauge_b = 2")
    tools.t_create(
        output="gauge_pair",
        title="Two maps of one day",
        description="Two maps with the same time",
    )
    tools.t_register(
        input="gauge_pair",
        maps="gauge_a,gauge_b",
        start="2026-06-01",
        end="2026-06-02",
    )
    tools.t_rast_extract(
        input="gauge_pair",
        output="gauge_ten",
        basename="ten",
        expression="gauge_pair * 10",
    )
    result = tools.t_rast_list(
        input="gauge_ten", columns="name,start_time,min", order="name"
    )
    print(result.text)
    ```

    ```text
    name|start_time|min
    ten_2026_06_01|2026-06-01 00:00:00|10.0
    ten_2026_06_01_2|2026-06-01 00:00:00|20.0
    ```

### Extract maps with semantic labels

The dataset `sentinel` has two scenes, on 1 and 11 June 2026, each with a red
band (`S2_B4`) and a near infrared band (`S2_B8`). The red maps hold 10 and 20,
the near infrared maps 30 and 40. The call takes the second scene and doubles
its values. The name of each new map has the semantic label between the base
name and the suffix, and the maps keep their labels. With `suffix=num`, the
maps are numbered in the order of start time and map id, so the near infrared
map `nir_2` is number 1 and the red map `red_2` is number 2. The block lists
the maps sorted by name.

=== "Command line"

    ```sh
    for scene in 1 2; do
        r.mapcalc expression="red_$scene = $scene * 10"
        r.mapcalc expression="nir_$scene = $scene * 10 + 20"
        r.support map=red_$scene semantic_label=S2_B4
        r.support map=nir_$scene semantic_label=S2_B8
    done
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared"
    t.register input=sentinel maps=red_1,nir_1 start="2026-06-01 10:30:00"
    t.register input=sentinel maps=red_2,nir_2 start="2026-06-11 10:30:00"
    t.rast.extract input=sentinel output=sentinel_twice basename=twice \
        where="start_time >= '2026-06-10'" expression="2 * sentinel" \
        suffix=num
    t.rast.list input=sentinel_twice columns=name,semantic_label,min order=name
    ```

    ```text
    name|semantic_label|min
    twice_S2_B4_00002|S2_B4|40.0
    twice_S2_B8_00001|S2_B8|80.0
    ```

=== "Python (grass.tools)"

    ```python
    for scene in (1, 2):
        tools.r_mapcalc(expression=f"red_{scene} = {scene * 10}")
        tools.r_mapcalc(expression=f"nir_{scene} = {scene * 10 + 20}")
        tools.r_support(map=f"red_{scene}", semantic_label="S2_B4")
        tools.r_support(map=f"nir_{scene}", semantic_label="S2_B8")
    tools.t_create(
        output="sentinel", title="Reflectance", description="Red and near infrared"
    )
    tools.t_register(input="sentinel", maps="red_1,nir_1", start="2026-06-01 10:30:00")
    tools.t_register(input="sentinel", maps="red_2,nir_2", start="2026-06-11 10:30:00")
    tools.t_rast_extract(
        input="sentinel",
        output="sentinel_twice",
        basename="twice",
        where="start_time >= '2026-06-10'",
        expression="2 * sentinel",
        suffix="num",
    )
    result = tools.t_rast_list(
        input="sentinel_twice", columns="name,semantic_label,min", order="name"
    )
    print(result.text)
    ```

    ```text
    name|semantic_label|min
    twice_S2_B4_00002|S2_B4|40.0
    twice_S2_B8_00001|S2_B8|80.0
    ```

### Extract from a dataset with relative time

The dataset `model` has two maps of six hours each, from 0 to 6 and from 6 to
12 hours, with the values 1 and 2. In a dataset with relative time a start
time is a number, so the names of the new maps carry the number of the map
instead of a date. The first block keeps the values above 1. The number counts
all selected maps, also the empty one: the first map is empty and left out, so
the remaining map is `m_00002`. The new dataset has the times and the unit of
the input. The second block takes `time` as the suffix; with relative time it
gives the number as well.

=== "Command line"

    ```sh
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=6 \
        unit=hours
    t.rast.extract input=model output=model_high basename=m \
        expression="if(model > 1, model, null())"
    t.rast.list input=model_high columns=name,start_time,end_time,min
    t.info -g model_high | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|start_time|end_time|min
    m_00002|6|12|2.0
    temporal_type=relative
    unit=hours
    ```

    ```sh
    t.rast.extract input=model output=model_time basename=t \
        expression="model" suffix=time
    t.rast.list input=model_time columns=name
    ```

    ```text
    name
    t_00001
    t_00002
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=6, unit="hours", flags="i"
    )
    tools.t_rast_extract(
        input="model",
        output="model_high",
        basename="m",
        expression="if(model > 1, model, null())",
    )
    columns = "name,start_time,end_time,min"
    print(tools.t_rast_list(input="model_high", columns=columns).text)
    info = tools.t_info(input="model_high", flags="g").keyval
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
    tools.t_rast_extract(
        input="model",
        output="model_time",
        basename="t",
        expression="model",
        suffix="time",
    )
    print(tools.t_rast_list(input="model_time", columns="name").text)
    ```

    ```text
    name
    t_00001
    t_00002
    ```

### Extract from a dataset of another mapset

The dataset `model` stays in the mapset `t_rast_extract`. The first block
creates the mapset `t_rast_extract_2`, sets the same region, adds the first
mapset to the search path so that its datasets can be read, and extracts with
an expression. The name `model` in the expression stands for the maps of the
dataset, though it has no mapset, and the output dataset `model_copy` and its
maps `copy_00001` and `copy_00002` belong to `t_rast_extract_2`. The `id`
column shows the mapset.

The second block shows what happens without an expression. The call is
refused, so the block prints `refused`. The refusal leaves the empty dataset
`model_copy_empty` behind. `number_of_maps=None` shows that it has no maps,
and *t.remove* removes it.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_extract_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_rast_extract operation=add
    t.rast.extract input=model@t_rast_extract output=model_copy basename=copy \
        expression="model" suffix=num
    t.rast.list input=model_copy columns=id,start_time,min
    ```

    ```text
    id|start_time|min
    copy_00001@t_rast_extract_2|0|1.0
    copy_00002@t_rast_extract_2|6|2.0
    ```

    ```sh
    if t.rast.extract input=model@t_rast_extract output=model_copy_empty \
        2>/dev/null; then echo extracted; else echo refused; fi
    t.info -g model_copy_empty | grep -E "^(id|number_of_maps)="
    t.remove -f type=strds inputs=model_copy_empty
    ```

    ```text
    refused
    id=model_copy_empty@t_rast_extract_2
    number_of_maps=None
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.g_mapset(mapset="t_rast_extract_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_rast_extract", operation="add")
    tools.t_rast_extract(
        input="model@t_rast_extract",
        output="model_copy",
        basename="copy",
        expression="model",
        suffix="num",
    )
    print(tools.t_rast_list(input="model_copy", columns="id,start_time,min").text)
    ```

    ```text
    id|start_time|min
    copy_00001@t_rast_extract_2|0|1.0
    copy_00002@t_rast_extract_2|6|2.0
    ```

    ```python
    try:
        tools.t_rast_extract(input="model@t_rast_extract", output="model_copy_empty")
    except ToolError:
        print("refused")
    else:
        print("extracted")
    info = tools.t_info(input="model_copy_empty", flags="g").keyval
    for key in ("id", "number_of_maps"):
        print(f"{key}={info[key]}")
    tools.t_remove(type="strds", inputs="model_copy_empty", flags="f")
    ```

    ```text
    refused
    id=model_copy_empty@t_rast_extract_2
    number_of_maps=None
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapset](g.mapset.md), [r.mapcalc](r.mapcalc.md),
[r.support](r.support.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.list](t.rast.list.md), [t.rast.mapcalc](t.rast.mapcalc.md),
[t.register](t.register.md), [t.remove](t.remove.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
