## DESCRIPTION

*t.vect.what.strds* reads the values of the maps of a space time raster
dataset (STRDS) at the points of the maps of a space time vector dataset
(STVDS) and stores them as columns in the attribute tables of the vector maps.
Use it to attach a time series of raster values, such as temperature or
precipitation, to monitoring stations or other sample points. Each vector map
of the STVDS has a time interval, which this manual calls its window. For each
vector map, the tool collects the raster maps of the STRDS that are related to
its window in time, optionally combines them to one map, and lets
*[v.what.rast](v.what.rast.md)* write the raster values at the points into the
table. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.vect.observe.strds](t.vect.observe.strds.md)* does the sampling
into new vector maps instead of existing ones, *[t.vect.list](t.vect.list.md)*
lists the vector maps of the dataset, and *[v.db.select](v.db.select.md)* prints
their tables.

### Datasets and region

The options **input** (the STVDS) and **strds** (the STRDS) are required. Both
datasets must have the same temporal type, absolute or relative. Every vector
map of **input** must have a time interval; a map with a time instant stops the
tool. The tool changes the tables of the vector maps, so the maps must be in the
current mapset, and each registered layer must have an attribute table. The
STRDS may be in another mapset (`strds=precipitation_monthly@t_vect_what_strds`),
but the vector maps
of **input** must be in the current mapset; the seventh example shows both.
Points outside the current region get no value, as *v.what.rast* skips them;
the second example shows it.

### Select the raster maps of a window

The option **sampling** is a list of temporal relations. A raster map is taken
for a vector map if it has one of the listed relations to its window. The
default is `start`. The relations describe the raster map in terms of the
window:

- `start`: the raster map starts inside the window, at or after its start and
  before its end. Its end does not matter, so the map may end after the window,
  and a map that equals the window is taken too.
- `during`: the raster map lies within the window and is not equal to it. It may
  share the start or the end of the window.
- `overlap`: the raster map starts before the window and ends inside it, or
  starts inside the window and ends after it.
- `contain`: the raster map covers the whole window and is longer than it.
- `equal`: the raster map has the start and the end of the window.
- `follows`: the raster map starts when the window ends.
- `precedes`: the raster map ends when the window starts.

So `start` selects more than its name suggests: it takes a map that `during`
rejects because it is equal to the window or because it ends after the window,
and it takes nothing that starts before the window, however long it lasts. The
fourth example runs every relation on the same windows. If a window has no
raster map, the vector map is left as it is, without a new column. The tool
takes the maps of a window in the order of their start time.

The relations apply only to a STRDS whose maps are all intervals. If the STRDS
has time instants, or instants and intervals, **sampling** has no effect: the
tool always takes the raster maps that start inside the window, as `start`
does, even with `contain`, which no instant can satisfy. The fourth example
shows it.

### Choose the columns

Without **column**, each raster map found for a vector map gets a column named
after it, with dots replaced by underscores (`precipitation_monthly_2020_02`),
in the table of the
layer of the vector map. The column type is `INT` for an integer raster map and
`DOUBLE PRECISION` for any other. The value of a point is the value of the cell
below it.

The option **column** names one column instead, the same in every vector map.
It holds the values of one raster map for each vector map: the first map of the
window in time order, or the aggregate if **method** is given and the window has
several maps.

The option **where** is an SQL condition on the attribute table of the vector
maps. Only the points that satisfy it get a value; the column of the other points
stays empty (`NULL`). The tool tries the condition on the table of each layer
before it writes the first value, and stops if it fails.

The option **t_where** is an SQL condition on the vector maps of **input**,
using the columns of the temporal database such as `name`, `start_time` and
`end_time` (see *[t.vect.list](t.vect.list.md)*). The tool changes only the
vector maps that match. SQLite compares times as text: `start_time >=
'2020-02-01'` selects as expected, but an equality with a date without a time of
day finds nothing, as the stored value reads `2020-02-01 00:00:00`.

### Aggregate the raster maps of a window

With **method** other than `disabled` (the default), the tool combines the
raster maps of a window to one map with *[r.series](r.series.md)* and reads
that map. It does so only for a window with more than one raster map. A window
with a single map is treated as if **method** were `disabled`: the values of the
map go to the column named after it (or to **column**). With several maps and
without **column**, the aggregate goes to the column `<strds>_<method>`, built
from the name of the STRDS without the mapset, for example `precipitation_monthly_average`.
Every character outside `A-Za-z0-9_` is replaced by an underscore, and a name
that would start with a digit gets the prefix `c_`, because *v.what.rast*
cannot write such a column. If the aggregate has no value at all, the tool adds
no column. The temporary raster map is removed after it has been read.

For a window with two raster maps whose values at one point are 211 and 311,
the methods give:

- `average` 261, `median` 261, `mode` 211 (the first of the sorted values with
  the highest count), `minimum` 211, `maximum` 311, `sum` 522;
- `count` 2 and `diversity` 2 (the number of maps and the number of different
  values), `range` 100 (maximum minus minimum);
- `variance` 2500 and `stddev` 50: population values, the sum of the squared
  deviations divided by the number of maps, not by that number minus 1;
- `min_raster` 0 and `max_raster` 1: the position of the map with the smallest
  or largest value in the time-ordered list, counted from 0;
- `slope` 100, `offset` 211 and `detcoeff` 1: slope, intercept and coefficient of
  determination of the regression of the values over their position 0, 1 in
  the list;
- `quart1` 236, `quart3` 286 and `perc90` 301: quantiles interpolated between
  the sorted values by the rule of Hyndman and Fan, type 7, at position
  `q * (n - 1)`;
- `quantile` 211: the tool has no option for the quantile, so this is the
  smallest value;
- `skewness` 0 and `kurtosis` -2: the skewness and the excess kurtosis of the
  two values.

## NOTES

Before the first value is written, the module checks the target columns of
all vector maps and layers. If one of them already exists, a layer to be
written has no attribute table, a vector map belongs to another mapset, or the
same layer of one map is registered under two ids (for example `c` and `c:1`)
and both would write the **column** option's column, the module stops with an
error and changes nothing. Without **column** the same layer under two ids is
refused only if both intervals reach one raster map, as they would write its
column twice, and is otherwise allowed; two different layers of
one map (`c:1` and `c:2`) are allowed with **column**, as each has its own
table. With the **--overwrite** flag,
the existing columns are kept and their values are written again, so a second
run does not add a second column; the fifth example shows it. An existing
column keeps its type: values
of a floating-point raster map written into an integer column lose their
fractional part, and *v.what.rast* warns about it. To get a column of the new
type, drop the column with *v.db.dropcolumn* first. A column name that
differs from an existing column only in upper and lower case (`K` for `k`)
is refused, with and without **--overwrite**, before anything is written.

The tool stops with an error if a required option is missing, if **method** or
**sampling** has a value outside the lists above, if a dataset does not exist,
if the two datasets differ in their temporal type ("Input and aggregation
dataset must have the same temporal type"), if a map of the STVDS has a time
instant ("All registered maps of the space time vector dataset must have time
intervals"), and if the STVDS is empty or **t_where** selects no map ("is
empty"). A **where** or **t_where** with a syntax error is reported as a
message (`Invalid where condition <...> for vector map <...>` and `Invalid
t_where condition <...>`), not as a traceback.

Relative time works as absolute time does; the sixth example shows it. The
relations of **sampling** then compare the start and end numbers of the maps.
The tool neither converts nor checks the units: use the same unit in both
datasets. With a STRDS in hours and a vector map from 0 to 2 days, the tool
compares 0 to 2 with the hours and takes the maps of the first two hours only,
not those of 48 hours; the last block of the sixth example shows it.

With `method=quantile` the tool gives the smallest value, as it has no option
for the quantile that *r.series* would need.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_what_strds` and sets the computational
region to North Carolina with cells of 1 km; the later examples work in this
mapset and region. The raster series are generated, they are not measurements:
the points are real climate stations and stream gauges of the dataset, but the
values at them come from a formula or from an assumed factor and say nothing
about the precipitation there. The tool writes into the tables of the vector
maps, so the examples copy the points into the mapset first. The last block of the
fourth example and the sixth example use maps with small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_what_strds -->

<!-- markdownlint-disable MD046 -->

### Sample the raster maps of each interval

The dataset `precipitation_monthly` holds twelve raster maps with the monthly
precipitation sum of 2020 in millimeters, one for each month. Each map is
generated: the monthly normals of the 136 climate stations of the dataset,
interpolated with *[v.surf.idw](v.surf.idw.md)* and multiplied by an assumed
factor for each month.

The vector maps hold the first four climate stations, copied from
`precip_30ynormals` with *[v.extract](v.extract.md)*, with the columns of the
original table. The dataset `stations` holds three copies: `stations_jan` has
the interval January, `stations_feb_mar` February and March, and
`stations_apr` April. The template `station_points` stays without time.

*t.vect.what.strds* uses the default **sampling**, `start`. For each vector map
it takes the raster maps that start inside its interval: the map of January for
`stations_jan`, the maps of February and March for `stations_feb_mar`, and the
map of April for `stations_apr`. Each vector map gets one column per raster
map, named after it. The last two commands print the tables of `stations_jan`
and `stations_feb_mar`.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_what_strds
    g.region raster=elev_state_500m res=1000 -a
    month=1
    for entry in jan:1.2 feb:1.7 mar:0.9 apr:1.3 may:1.6 jun:0.9 \
        jul:1.1 aug:1.5 sep:0.8 oct:1.0 nov:1.6 dec:0.9; do
        name=$(printf %02d $month)
        v.surf.idw input=precip_30ynormals column=${entry%:*} \
            output=precipitation_normal_$name npoints=12 power=2
        r.mapcalc expression="precipitation_monthly_2020_$name = if(isnull(elev_state_500m), null(), round(${entry#*:} * precipitation_normal_$name))"
        month=$((month + 1))
    done
    t.create output=precipitation_monthly title="Precipitation" \
        description="Monthly precipitation sum 2020 in mm"
    t.register -i input=precipitation_monthly \
        maps=$(g.list type=raster pattern="precipitation_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    ```

    ```sh
    v.extract input=precip_30ynormals output=station_points where="cat <= 4"
    g.copy vector=station_points,stations_jan
    g.copy vector=station_points,stations_feb_mar
    g.copy vector=station_points,stations_apr
    t.create type=stvds output=stations title="Stations" \
        description="Four climate stations in three intervals"
    t.register type=vector input=stations maps=stations_jan \
        start=2020-01-01 end=2020-02-01
    t.register type=vector input=stations maps=stations_feb_mar \
        start=2020-02-01 end=2020-04-01
    t.register type=vector input=stations maps=stations_apr \
        start=2020-04-01 end=2020-05-01
    t.vect.what.strds input=stations strds=precipitation_monthly
    v.db.select map=stations_jan columns=cat,station,precipitation_monthly_2020_01
    v.db.select map=stations_feb_mar \
        columns=cat,station,precipitation_monthly_2020_02,precipitation_monthly_2020_03
    ```

    ```text
    cat|station|precipitation_monthly_2020_01
    1|310090|133
    2|310184|219
    3|310241|120
    4|310286|135
    cat|station|precipitation_monthly_2020_02|precipitation_monthly_2020_03
    1|310090|157|110
    2|310184|263|159
    3|310241|149|102
    4|310286|160|98
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_vect_what_strds")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    months = range(1, 13)
    factors = {"jan": 1.2, "feb": 1.7, "mar": 0.9, "apr": 1.3, "may": 1.6, "jun": 0.9}
    factors |= {"jul": 1.1, "aug": 1.5, "sep": 0.8, "oct": 1.0, "nov": 1.6, "dec": 0.9}
    for month, (column, factor) in enumerate(factors.items(), start=1):
        normal = f"precipitation_normal_{month:02d}"
        tools.v_surf_idw(
            input="precip_30ynormals", column=column, output=normal, npoints=12, power=2
        )
        tools.r_mapcalc(
            expression=f"precipitation_monthly_2020_{month:02d} ="
            f" if(isnull(elev_state_500m), null(), round({factor} * {normal}))"
        )
    tools.t_create(
        output="precipitation_monthly",
        title="Precipitation",
        description="Monthly precipitation sum 2020 in mm",
    )
    tools.t_register(
        input="precipitation_monthly",
        maps=",".join(f"precipitation_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

    ```python
    tools.v_extract(input="precip_30ynormals", output="station_points", where="cat <= 4")
    for name in ("stations_jan", "stations_feb_mar", "stations_apr"):
        tools.g_copy(vector=f"station_points,{name}")
    tools.t_create(
        type="stvds",
        output="stations",
        title="Stations",
        description="Four climate stations in three intervals",
    )
    for name, start, end in (
        ("stations_jan", "2020-01-01", "2020-02-01"),
        ("stations_feb_mar", "2020-02-01", "2020-04-01"),
        ("stations_apr", "2020-04-01", "2020-05-01"),
    ):
        tools.t_register(type="vector", input="stations", maps=name, start=start, end=end)
    tools.t_vect_what_strds(input="stations", strds="precipitation_monthly")
    print(
        tools.v_db_select(
            map="stations_jan", columns="cat,station,precipitation_monthly_2020_01"
        ).text
    )
    print(
        tools.v_db_select(
            map="stations_feb_mar",
            columns="cat,station,precipitation_monthly_2020_02,precipitation_monthly_2020_03",
        ).text
    )
    ```

    ```text
    cat|station|precipitation_monthly_2020_01
    1|310090|133
    2|310184|219
    3|310241|120
    4|310286|135
    cat|station|precipitation_monthly_2020_02|precipitation_monthly_2020_03
    1|310090|157|110
    2|310184|263|159
    3|310241|149|102
    4|310286|160|98
    ```

### Store one column and read only some points

With **column**, the tool stores the values of one raster map per vector map in
the column `first`. For `stations_feb_mar` that is the map of February, the
first of its two raster maps. **where** limits the points: only those with a
`cat` above 2 get a value, and the column of the points 1 and 2 stays empty.

The second part reads the points with a smaller region, which ends at the
northing 200 km (`n=200000`), and **t_where** limits the call to
`stations_feb_mar`. The stations 3 and 4 lie north of it and get no value in
the new column `south`; the stations 1 and 2 read the map of February again. The
last command sets the region back.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=precipitation_monthly column=first \
        where="cat > 2"
    v.db.select map=stations_feb_mar columns=cat,station,first
    ```

    ```text
    cat|station|first
    1|310090|
    2|310184|
    3|310241|149
    4|310286|160
    ```

    ```sh
    g.region n=200000
    t.vect.what.strds input=stations strds=precipitation_monthly column=south \
        t_where="name = 'stations_feb_mar'"
    v.db.select map=stations_feb_mar columns=cat,station,south
    g.region raster=elev_state_500m res=1000 -a
    ```

    ```text
    cat|station|south
    1|310090|157
    2|310184|263
    3|310241|
    4|310286|
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations",
        strds="precipitation_monthly",
        column="first",
        where="cat > 2",
    )
    print(tools.v_db_select(map="stations_feb_mar", columns="cat,station,first").text)
    ```

    ```text
    cat|station|first
    1|310090|
    2|310184|
    3|310241|149
    4|310286|160
    ```

    ```python
    tools.g_region(n=200000)
    tools.t_vect_what_strds(
        input="stations",
        strds="precipitation_monthly",
        column="south",
        t_where="name = 'stations_feb_mar'",
    )
    print(tools.v_db_select(map="stations_feb_mar", columns="cat,station,south").text)
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    ```

    ```text
    cat|station|south
    1|310090|157
    2|310184|263
    3|310241|
    4|310286|
    ```

### Aggregate the raster maps of an interval

The first call aggregates with **method**`=average`, but only for
`stations_feb_mar`, which **t_where** selects by name: it is the only vector map
with two raster maps in its interval. Without **column** the aggregate goes to
the column `precipitation_monthly_average`, the name of the dataset and the
method. The mean of two whole numbers can have a fraction, so the column has
the type `DOUBLE PRECISION`: for the station 1 it is the mean of 157 and 110,
which is 133.5.

The second call uses **column**`=total` and `sum` for all three vector maps.
In `stations_feb_mar` the column holds the sum of the two maps, 157 + 110 = 267
for the station 1. `stations_jan` has one raster map in its interval, which is
not aggregated: its column holds the values of the map of January, 133 for the
station 1. The description lists the values of the other methods.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=precipitation_monthly method=average \
        t_where="name = 'stations_feb_mar'"
    v.db.select map=stations_feb_mar columns=cat,station,precipitation_monthly_average
    ```

    ```text
    cat|station|precipitation_monthly_average
    1|310090|133.5
    2|310184|211
    3|310241|125.5
    4|310286|129
    ```

    ```sh
    t.vect.what.strds input=stations strds=precipitation_monthly column=total \
        method=sum
    v.db.select map=stations_feb_mar columns=cat,station,total
    v.db.select map=stations_jan columns=cat,station,total
    ```

    ```text
    cat|station|total
    1|310090|267
    2|310184|422
    3|310241|251
    4|310286|258
    cat|station|total
    1|310090|133
    2|310184|219
    3|310241|120
    4|310286|135
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations",
        strds="precipitation_monthly",
        method="average",
        t_where="name = 'stations_feb_mar'",
    )
    print(
        tools.v_db_select(
            map="stations_feb_mar", columns="cat,station,precipitation_monthly_average"
        ).text
    )
    ```

    ```text
    cat|station|precipitation_monthly_average
    1|310090|133.5
    2|310184|211
    3|310241|125.5
    4|310286|129
    ```

    ```python
    tools.t_vect_what_strds(
        input="stations", strds="precipitation_monthly", column="total", method="sum"
    )
    print(tools.v_db_select(map="stations_feb_mar", columns="cat,station,total").text)
    print(tools.v_db_select(map="stations_jan", columns="cat,station,total").text)
    ```

    ```text
    cat|station|total
    1|310090|267
    2|310184|422
    3|310241|251
    4|310286|258
    cat|station|total
    1|310090|133
    2|310184|219
    3|310241|120
    4|310286|135
    ```

### Choose the raster maps by their relation to the interval

The loop runs every value of **sampling** on four vector maps with the same
points and these windows (all in 2020): `a` from 15 February to 15 April, `b`
from 10 to 20 March, `c` from 1 March to 1 April and `d` from 1 March to 10
April. The raster maps are the monthly maps of `precipitation_monthly`, so the
map of March lasts from 1 March to 1 April, the map of February from 1 February
to 1 March and the map of April from 1 April to 1 May. For each relation the
loop makes a dataset `windows_<relation>` with four copies of the template
`station_points`, runs the tool, and prints the months of the raster columns of
each copy: `03` stands for the column `precipitation_monthly_2020_03`.

Compare the rows of a window in the output:

- `start`: March and April for `a` and `d`, because both start inside these
  windows, though April ends after them; March alone for `c`, which it equals;
  nothing for `b`, because March starts before it.
- `during`: March for `a` and for `d`, which shares its start with March;
  nothing for `c`, which equals March.
- `overlap`: February and April for `a`, April for `d`.
- `contain`: March for `b`, which lies inside it.
- `equal`: March for `c`.
- `follows`: April for `c`, which ends when April starts.
- `precedes`: February for `c` and `d`, which start when February ends.

The last block uses a dataset `moisture` of two time instants, 5 and 25 March
2026, with constant maps, and a window from 1 March to 1 April 2026. No instant
can contain a window, but with **sampling**`=contain` the tool writes both
columns: a STRDS with time instants is always sampled as with `start`.

=== "Command line"

    ```sh
    for s in start during overlap contain equal follows precedes; do
        t.create type=stvds output=windows_$s title="Windows" \
            description="Sampling $s"
        for w in a b c d; do
            g.copy vector=station_points,${s}_$w
        done
        t.register type=vector input=windows_$s maps=${s}_a \
            start=2020-02-15 end=2020-04-15
        t.register type=vector input=windows_$s maps=${s}_b \
            start=2020-03-10 end=2020-03-20
        t.register type=vector input=windows_$s maps=${s}_c \
            start=2020-03-01 end=2020-04-01
        t.register type=vector input=windows_$s maps=${s}_d \
            start=2020-03-01 end=2020-04-10
        t.vect.what.strds input=windows_$s strds=precipitation_monthly sampling=$s
        for w in a b c d; do
            c=$(db.columns table=${s}_$w | awk -F_ '/^precipitation_monthly_/ {print $NF}' | paste -sd, -)
            echo "${s}_$w: ${c:--}"
        done
    done
    ```

    ```text
    start_a: 03,04
    start_b: -
    start_c: 03
    start_d: 03,04
    during_a: 03
    during_b: -
    during_c: -
    during_d: 03
    overlap_a: 02,04
    overlap_b: -
    overlap_c: -
    overlap_d: 04
    contain_a: -
    contain_b: 03
    contain_c: -
    contain_d: -
    equal_a: -
    equal_b: -
    equal_c: 03
    equal_d: -
    follows_a: -
    follows_b: -
    follows_c: 04
    follows_d: -
    precedes_a: -
    precedes_b: -
    precedes_c: 02
    precedes_d: 02
    ```

    ```sh
    for k in 1 2; do
        r.mapcalc expression="moisture_$k = 100 * $k + 11"
    done
    t.create output=moisture title="Moisture" description="Two instants"
    t.register input=moisture maps=moisture_1 start=2026-03-05
    t.register input=moisture maps=moisture_2 start=2026-03-25
    g.copy vector=station_points,instant_window
    t.create type=stvds output=instant_windows title="Windows" \
        description="One window"
    t.register type=vector input=instant_windows maps=instant_window \
        start=2026-03-01 end=2026-04-01
    t.vect.what.strds input=instant_windows strds=moisture sampling=contain
    db.columns table=instant_window | awk '/^moisture_/' | paste -sd, -
    ```

    ```text
    moisture_1,moisture_2
    ```

=== "Python (grass.tools)"

    ```python
    windows = {
        "a": ("2020-02-15", "2020-04-15"),
        "b": ("2020-03-10", "2020-03-20"),
        "c": ("2020-03-01", "2020-04-01"),
        "d": ("2020-03-01", "2020-04-10"),
    }
    for sampling in (
        "start",
        "during",
        "overlap",
        "contain",
        "equal",
        "follows",
        "precedes",
    ):
        dataset = f"windows_{sampling}"
        tools.t_create(
            type="stvds",
            output=dataset,
            title="Windows",
            description=f"Sampling {sampling}",
        )
        for letter, (start, end) in windows.items():
            name = f"{sampling}_{letter}"
            tools.g_copy(vector=f"station_points,{name}")
            tools.t_register(type="vector", input=dataset, maps=name, start=start, end=end)
        tools.t_vect_what_strds(
            input=dataset, strds="precipitation_monthly", sampling=sampling
        )
        for letter in windows:
            name = f"{sampling}_{letter}"
            columns = tools.db_columns(table=name).text.split()
            months = [
                column.rsplit("_", 1)[1]
                for column in columns
                if column.startswith("precipitation_monthly_")
            ]
            print(f"{name}: {','.join(months) or '-'}")
    ```

    ```text
    start_a: 03,04
    start_b: -
    start_c: 03
    start_d: 03,04
    during_a: 03
    during_b: -
    during_c: -
    during_d: 03
    overlap_a: 02,04
    overlap_b: -
    overlap_c: -
    overlap_d: 04
    contain_a: -
    contain_b: 03
    contain_c: -
    contain_d: -
    equal_a: -
    equal_b: -
    equal_c: 03
    equal_d: -
    follows_a: -
    follows_b: -
    follows_c: 04
    follows_d: -
    precedes_a: -
    precedes_b: -
    precedes_c: 02
    precedes_d: 02
    ```

    ```python
    for k in (1, 2):
        tools.r_mapcalc(expression=f"moisture_{k} = 100 * {k} + 11")
    tools.t_create(output="moisture", title="Moisture", description="Two instants")
    tools.t_register(input="moisture", maps="moisture_1", start="2026-03-05")
    tools.t_register(input="moisture", maps="moisture_2", start="2026-03-25")
    tools.g_copy(vector="station_points,instant_window")
    tools.t_create(
        type="stvds",
        output="instant_windows",
        title="Windows",
        description="One window",
    )
    tools.t_register(
        type="vector",
        input="instant_windows",
        maps="instant_window",
        start="2026-03-01",
        end="2026-04-01",
    )
    tools.t_vect_what_strds(input="instant_windows", strds="moisture", sampling="contain")
    columns = tools.db_columns(table="instant_window").text.split()
    print(",".join(column for column in columns if column.startswith("moisture_")))
    ```

    ```text
    moisture_1,moisture_2
    ```

### Select vector maps by time and write the values again

**t_where** restricts the tool to the vector maps whose temporal metadata
match. Here it takes the maps that start on or after 1 February, so
`stations_feb_mar` and `stations_apr` get the column `late` and `stations_jan`
does not. The loop prints the columns named `late`, with `-` where there is
none.

The second call repeats the first one with **--overwrite**. The columns exist
now, and the flag lets the tool write them again instead of stopping. The call
changes what is read: **method**`=minimum` takes the smaller of the two maps of
`stations_feb_mar`, the map of March, and **where** limits the new values to
the points with a `cat` of at most 2. The stations 1 and 2 read 110 and 159
from the map of March; the stations 3 and 4 keep the values 149 and 160 of the
first call, which are the values of the map of February.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=precipitation_monthly column=late \
        t_where="start_time >= '2020-02-01'"
    for m in stations_jan stations_feb_mar stations_apr; do
        c=$(db.columns table=$m | awk '/^late$/')
        echo "$m: ${c:--}"
    done
    t.vect.what.strds --overwrite input=stations strds=precipitation_monthly \
        column=late method=minimum where="cat <= 2" \
        t_where="start_time >= '2020-02-01'"
    v.db.select map=stations_feb_mar columns=cat,station,late
    ```

    ```text
    stations_jan: -
    stations_feb_mar: late
    stations_apr: late
    cat|station|late
    1|310090|110
    2|310184|159
    3|310241|149
    4|310286|160
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations",
        strds="precipitation_monthly",
        column="late",
        t_where="start_time >= '2020-02-01'",
    )
    for name in ("stations_jan", "stations_feb_mar", "stations_apr"):
        columns = tools.db_columns(table=name).text.split()
        print(f"{name}: {'late' if 'late' in columns else '-'}")
    tools.t_vect_what_strds(
        input="stations",
        strds="precipitation_monthly",
        column="late",
        method="minimum",
        where="cat <= 2",
        t_where="start_time >= '2020-02-01'",
        overwrite=True,
    )
    print(tools.v_db_select(map="stations_feb_mar", columns="cat,station,late").text)
    ```

    ```text
    stations_jan: -
    stations_feb_mar: late
    stations_apr: late
    cat|station|late
    1|310090|110
    2|310184|159
    3|310241|149
    4|310286|160
    ```

### Relative time

The dataset `flow` has three raster maps with constant values for the hours 0
to 1, 1 to 2 and 2 to 3: `flow_1` is 111, `flow_2` 211 and `flow_3` 311. The
dataset `gauge_runs` holds two vector maps with the intervals 0 to 2 and 2 to 3,
both in hours. Their points are two gauges of the Crabtree Creek, copied from
`usgsgages`. Both datasets have relative time. `gauge_run_1` has `flow_1` and
`flow_2` in its interval, so **method**`=average` stores their mean, 161, in the
column `flow_average`. `gauge_run_2` has only `flow_3`, which is stored under
its own name, 311.

The last block shows that the tool does not look at the unit. The vector map
`gauge_run_days` has the interval 0 to 2 days, while `flow` counts hours. The
tool compares the numbers: it takes `flow_1` and `flow_2`, which start at 0 and
1, but not `flow_3`, which starts at 2, although 2 days are 48 hours and cover
all three maps. Use the same unit in both datasets.

=== "Command line"

    ```sh
    for k in 1 2 3; do
        r.mapcalc expression="flow_$k = 100 * $k + 11"
    done
    t.create output=flow temporaltype=relative title="Flow" \
        description="Three hourly maps with constant values"
    t.register -i input=flow maps=flow_1,flow_2,flow_3 \
        start=0 increment=1 unit=hours
    v.extract input=usgsgages output=gauge_run_1 \
        where="SITE_NAME LIKE 'Crabtree Creek%' AND cat <= 150"
    g.copy vector=gauge_run_1,gauge_run_2
    t.create type=stvds temporaltype=relative output=gauge_runs title="Gauge runs" \
        description="Two intervals"
    t.register type=vector input=gauge_runs maps=gauge_run_1 start=0 end=2 unit=hours
    t.register type=vector input=gauge_runs maps=gauge_run_2 start=2 end=3 unit=hours
    t.vect.what.strds input=gauge_runs strds=flow method=average
    v.db.select map=gauge_run_1 columns=cat,SITE_ID,flow_average
    v.db.select map=gauge_run_2 columns=cat,SITE_ID,flow_3
    ```

    ```text
    cat|SITE_ID|flow_average
    149|0208726005|161
    150|02087275|161
    cat|SITE_ID|flow_3
    149|0208726005|311
    150|02087275|311
    ```

    ```sh
    v.extract input=usgsgages output=gauge_run_days \
        where="SITE_NAME LIKE 'Crabtree Creek%' AND cat <= 150"
    t.create type=stvds temporaltype=relative output=gauge_runs_days \
        title="Gauge runs in days" description="One interval in days"
    t.register type=vector input=gauge_runs_days maps=gauge_run_days \
        start=0 end=2 unit=days
    t.vect.what.strds input=gauge_runs_days strds=flow
    db.columns table=gauge_run_days | awk '/^flow_/' | paste -sd, -
    ```

    ```text
    flow_1,flow_2
    ```

=== "Python (grass.tools)"

    ```python
    for k in range(1, 4):
        tools.r_mapcalc(expression=f"flow_{k} = 100 * {k} + 11")
    tools.t_create(
        output="flow",
        temporaltype="relative",
        title="Flow",
        description="Three hourly maps with constant values",
    )
    tools.t_register(
        input="flow",
        maps="flow_1,flow_2,flow_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.v_extract(
        input="usgsgages",
        output="gauge_run_1",
        where="SITE_NAME LIKE 'Crabtree Creek%' AND cat <= 150",
    )
    tools.g_copy(vector="gauge_run_1,gauge_run_2")
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="gauge_runs",
        title="Gauge runs",
        description="Two intervals",
    )
    tools.t_register(
        type="vector", input="gauge_runs", maps="gauge_run_1", start=0, end=2, unit="hours"
    )
    tools.t_register(
        type="vector", input="gauge_runs", maps="gauge_run_2", start=2, end=3, unit="hours"
    )
    tools.t_vect_what_strds(input="gauge_runs", strds="flow", method="average")
    print(tools.v_db_select(map="gauge_run_1", columns="cat,SITE_ID,flow_average").text)
    print(tools.v_db_select(map="gauge_run_2", columns="cat,SITE_ID,flow_3").text)
    ```

    ```text
    cat|SITE_ID|flow_average
    149|0208726005|161
    150|02087275|161
    cat|SITE_ID|flow_3
    149|0208726005|311
    150|02087275|311
    ```

    ```python
    tools.v_extract(
        input="usgsgages",
        output="gauge_run_days",
        where="SITE_NAME LIKE 'Crabtree Creek%' AND cat <= 150",
    )
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="gauge_runs_days",
        title="Gauge runs in days",
        description="One interval in days",
    )
    tools.t_register(
        type="vector",
        input="gauge_runs_days",
        maps="gauge_run_days",
        start=0,
        end=2,
        unit="days",
    )
    tools.t_vect_what_strds(input="gauge_runs_days", strds="flow")
    columns = tools.db_columns(table="gauge_run_days").text.split()
    print(",".join(column for column in columns if column.startswith("flow_")))
    ```

    ```text
    flow_1,flow_2
    ```

### Datasets of another mapset

The example creates the mapset `t_vect_what_strds_2` and switches to it, where
the region is its own and is set again. The dataset `precipitation_monthly`
stays in `t_vect_what_strds`, and
**strds**`=precipitation_monthly@t_vect_what_strds` names it with its mapset,
which does not have to be in the search path. The vector map `remote` and its
dataset belong to `t_vect_what_strds_2`, so the tool writes the columns for
February and March into the table of `remote` in the current mapset. The second
block asks for the dataset `stations` in `t_vect_what_strds` as **input**. The
tool refuses it before it writes anything, because it would have to change the
tables of vector maps of another mapset, and the block prints the message.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_what_strds_2
    g.region raster=elev_state_500m res=1000 -a
    g.copy vector=station_points@t_vect_what_strds,remote
    t.create type=stvds output=remote_ds title="Remote" \
        description="One interval in the new mapset"
    t.register type=vector input=remote_ds maps=remote \
        start=2020-02-01 end=2020-04-01
    t.vect.what.strds input=remote_ds strds=precipitation_monthly@t_vect_what_strds
    v.db.select map=remote \
        columns=cat,station,precipitation_monthly_2020_02,precipitation_monthly_2020_03
    ```

    ```text
    cat|station|precipitation_monthly_2020_02|precipitation_monthly_2020_03
    1|310090|157|110
    2|310184|263|159
    3|310241|149|102
    4|310286|160|98
    ```

    ```sh
    if ! t.vect.what.strds input=stations@t_vect_what_strds \
        strds=precipitation_monthly@t_vect_what_strds column=other 2>&1; then
        echo "t.vect.what.strds failed"
    fi
    ```

    ```text
    ERROR: Vector map <stations_jan@t_vect_what_strds> is not in the current
           mapset, so its table cannot be written
           Vector map <stations_feb_mar@t_vect_what_strds> is not in the
           current mapset, so its table cannot be written
           Vector map <stations_apr@t_vect_what_strds> is not in the current
           mapset, so its table cannot be written
    t.vect.what.strds failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_vect_what_strds_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_copy(vector="station_points@t_vect_what_strds,remote")
    tools.t_create(
        type="stvds",
        output="remote_ds",
        title="Remote",
        description="One interval in the new mapset",
    )
    tools.t_register(
        type="vector",
        input="remote_ds",
        maps="remote",
        start="2020-02-01",
        end="2020-04-01",
    )
    tools.t_vect_what_strds(
        input="remote_ds", strds="precipitation_monthly@t_vect_what_strds"
    )
    print(
        tools.v_db_select(
            map="remote",
            columns="cat,station,precipitation_monthly_2020_02,precipitation_monthly_2020_03",
        ).text
    )
    ```

    ```text
    cat|station|precipitation_monthly_2020_02|precipitation_monthly_2020_03
    1|310090|157|110
    2|310184|263|159
    3|310241|149|102
    4|310286|160|98
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_vect_what_strds(
            input="stations@t_vect_what_strds",
            strds="precipitation_monthly@t_vect_what_strds",
            column="other",
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.what.strds failed")
    ```

    ```text
    ERROR: Vector map <stations_jan@t_vect_what_strds> is not in the current
           mapset, so its table cannot be written
           Vector map <stations_feb_mar@t_vect_what_strds> is not in the
           current mapset, so its table cannot be written
           Vector map <stations_apr@t_vect_what_strds> is not in the current
           mapset, so its table cannot be written
    t.vect.what.strds failed
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[r.series](r.series.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.aggregate](t.rast.aggregate.md),
[t.vect.db.select](t.vect.db.select.md), [t.vect.list](t.vect.list.md),
[t.vect.observe.strds](t.vect.observe.strds.md),
[v.db.select](v.db.select.md), [v.what.rast](v.what.rast.md),
[v.what.rast3](v.what.rast3.md), [v.what.strds](v.what.strds.md),
[v.what.vect](v.what.vect.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
