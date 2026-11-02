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
STRDS may be in another mapset (`strds=levels@PERMANENT`), but the vector maps
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
after it, with dots replaced by underscores (`level_2`), in the table of the
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
'2026-02-01'` selects as expected, but an equality with a date without a time of
day finds nothing, as the stored value reads `2026-02-01 00:00:00`.

### Aggregate the raster maps of a window

With **method** other than `disabled` (the default), the tool combines the
raster maps of a window to one map with *[r.series](r.series.md)* and reads
that map. It does so only for a window with more than one raster map. A window
with a single map is treated as if **method** were `disabled`: the values of the
map go to the column named after it (or to **column**). With several maps and
without **column**, the aggregate goes to the column `<strds>_<method>`, built
from the name of the STRDS without the mapset, for example `levels_average`.
Every character outside `A-Za-z0-9_` is replaced by an underscore, and a name
that would start with a digit gets the prefix `c_`, because *v.what.rast*
cannot write such a column. If the aggregate has no value at all, the tool adds
no column. The temporary raster map is removed after it has been read.

For a window with two raster maps, here `level_2` and `level_3`, whose value
at one point is 211 and 311 (the first point of the first example), the methods
give:

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

<!-- markdownlint-disable MD046 -->

### Sample the raster maps of each interval

The dataset `levels` holds six raster maps, `level_1` to `level_6`, one for
each month from January to June 2026. The region has two rows and two columns
of size 1, and the value of `level_k` in the cell of row `r` and column `c` is
`100 * k + 10 * r + c`. The dataset `stations` holds three vector maps with the
same four points, one at the centre of each cell, with the column `height` 1 to
4: the points `cat` 1 and 2 lie in the first row, 3 and 4 in the second.
`stations_1` has the interval January, `stations_2` February and March, and
`stations_3` April.

*t.vect.what.strds* uses the default **sampling**, `start`. For each vector map
it takes the raster maps that start inside its interval: `level_1` for
`stations_1`, `level_2` and `level_3` for `stations_2`, and `level_4` for
`stations_3`. Each vector map gets one column per raster map, named after it.
The last two commands print the tables of `stations_1` and `stations_2`. The
point `cat` 3, in the second row and first column, reads 121 in `level_1`, 221
in `level_2` and 321 in `level_3`.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    for k in 1 2 3 4 5 6; do
        r.mapcalc expression="level_$k = 100 * $k + 10 * row() + col()"
    done
    t.create output=levels title="Levels" description="Six monthly maps"
    t.register -i input=levels \
        maps=level_1,level_2,level_3,level_4,level_5,level_6 \
        start=2026-01-01 increment="1 month"
    v.in.ascii input=- output=stations_1 separator=comma \
        columns="x double precision, y double precision, height integer" <<EOF
    0.5,1.5,1
    1.5,1.5,2
    0.5,0.5,3
    1.5,0.5,4
    EOF
    g.copy vector=stations_1,stations_2
    g.copy vector=stations_1,stations_3
    t.create type=stvds output=stations title="Stations" \
        description="Four points in three intervals"
    t.register type=vector input=stations maps=stations_1 \
        start=2026-01-01 end=2026-02-01
    t.register type=vector input=stations maps=stations_2 \
        start=2026-02-01 end=2026-04-01
    t.register type=vector input=stations maps=stations_3 \
        start=2026-04-01 end=2026-05-01
    t.vect.what.strds input=stations strds=levels
    v.db.select map=stations_1
    v.db.select map=stations_2
    ```

    ```text
    cat|x|y|height|level_1
    1|0.5|1.5|1|111
    2|1.5|1.5|2|112
    3|0.5|0.5|3|121
    4|1.5|0.5|4|122
    cat|x|y|height|level_2|level_3
    1|0.5|1.5|1|211|311
    2|1.5|1.5|2|212|312
    3|0.5|0.5|3|221|321
    4|1.5|0.5|4|222|322
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    for k in range(1, 7):
        tools.r_mapcalc(expression=f"level_{k} = 100 * {k} + 10 * row() + col()")
    tools.t_create(output="levels", title="Levels", description="Six monthly maps")
    tools.t_register(
        input="levels",
        maps="level_1,level_2,level_3,level_4,level_5,level_6",
        start="2026-01-01",
        increment="1 month",
        flags="i",
    )
    tools.v_in_ascii(
        input=StringIO("0.5,1.5,1\n1.5,1.5,2\n0.5,0.5,3\n1.5,0.5,4\n"),
        output="stations_1",
        separator="comma",
        columns="x double precision, y double precision, height integer",
    )
    tools.g_copy(vector="stations_1,stations_2")
    tools.g_copy(vector="stations_1,stations_3")
    tools.t_create(
        type="stvds",
        output="stations",
        title="Stations",
        description="Four points in three intervals",
    )
    for name, start, end in (
        ("stations_1", "2026-01-01", "2026-02-01"),
        ("stations_2", "2026-02-01", "2026-04-01"),
        ("stations_3", "2026-04-01", "2026-05-01"),
    ):
        tools.t_register(type="vector", input="stations", maps=name, start=start, end=end)
    tools.t_vect_what_strds(input="stations", strds="levels")
    print(tools.v_db_select(map="stations_1").text)
    print(tools.v_db_select(map="stations_2").text)
    ```

    ```text
    cat|x|y|height|level_1
    1|0.5|1.5|1|111
    2|1.5|1.5|2|112
    3|0.5|0.5|3|121
    4|1.5|0.5|4|122
    cat|x|y|height|level_2|level_3
    1|0.5|1.5|1|211|311
    2|1.5|1.5|2|212|312
    3|0.5|0.5|3|221|321
    4|1.5|0.5|4|222|322
    ```

### Store one column and read only some points

With **column**, the tool stores the values of one raster map per vector map in
the column `first`. For `stations_2` that is `level_2`, the first of its two
raster maps. **where** limits the points: only those with a `height` above 2
get a value, and the column of the points 1 and 2 stays empty.

The second part reads the points with a smaller region, the first row only
(`n=2`, `s=1`), and **t_where** limits the call to `stations_2`. The points of
the second row lie outside the region and get no value in the new column `top`;
the points of the first row read `level_2` again. The last command sets the
region back.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=levels column=first \
        where="height > 2"
    v.db.select map=stations_2 columns=cat,height,first
    ```

    ```text
    cat|height|first
    1|1|
    2|2|
    3|3|221
    4|4|222
    ```

    ```sh
    g.region n=2 s=1 e=2 w=0 res=1
    t.vect.what.strds input=stations strds=levels column=top \
        t_where="name = 'stations_2'"
    v.db.select map=stations_2 columns=cat,height,top
    g.region n=2 s=0 e=2 w=0 res=1
    ```

    ```text
    cat|height|top
    1|1|211
    2|2|212
    3|3|
    4|4|
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations", strds="levels", column="first", where="height > 2"
    )
    print(tools.v_db_select(map="stations_2", columns="cat,height,first").text)
    ```

    ```text
    cat|height|first
    1|1|
    2|2|
    3|3|221
    4|4|222
    ```

    ```python
    tools.g_region(n=2, s=1, e=2, w=0, res=1)
    tools.t_vect_what_strds(
        input="stations", strds="levels", column="top", t_where="name = 'stations_2'"
    )
    print(tools.v_db_select(map="stations_2", columns="cat,height,top").text)
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    ```

    ```text
    cat|height|top
    1|1|211
    2|2|212
    3|3|
    4|4|
    ```

### Aggregate the raster maps of an interval

The first call aggregates with **method**`=average`, but only for
`stations_2`, which **t_where** selects by name: it is the only vector map with
two raster maps in its interval. Without **column** the aggregate goes to the
column `levels_average`, the name of the dataset and the method. For the point
`cat` 1 it is the mean of 211 and 311, which is 261.

The second call uses **column**`=total` and `sum` for all three vector maps.
In `stations_2` the column holds the sum of the two maps, 211 + 311 = 522 for
the point 1. `stations_1` has one raster map in its interval, which is not
aggregated: its column holds the values of `level_1`, 111 for the point 1. The
description lists the values of the other methods.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=levels method=average \
        t_where="name = 'stations_2'"
    v.db.select map=stations_2 columns=cat,levels_average
    ```

    ```text
    cat|levels_average
    1|261
    2|262
    3|271
    4|272
    ```

    ```sh
    t.vect.what.strds input=stations strds=levels column=total method=sum
    v.db.select map=stations_2 columns=cat,total
    v.db.select map=stations_1 columns=cat,total
    ```

    ```text
    cat|total
    1|522
    2|524
    3|542
    4|544
    cat|total
    1|111
    2|112
    3|121
    4|122
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations",
        strds="levels",
        method="average",
        t_where="name = 'stations_2'",
    )
    print(tools.v_db_select(map="stations_2", columns="cat,levels_average").text)
    ```

    ```text
    cat|levels_average
    1|261
    2|262
    3|271
    4|272
    ```

    ```python
    tools.t_vect_what_strds(input="stations", strds="levels", column="total", method="sum")
    print(tools.v_db_select(map="stations_2", columns="cat,total").text)
    print(tools.v_db_select(map="stations_1", columns="cat,total").text)
    ```

    ```text
    cat|total
    1|522
    2|524
    3|542
    4|544
    cat|total
    1|111
    2|112
    3|121
    4|122
    ```

### Choose the raster maps by their relation to the interval

The loop runs every value of **sampling** on four vector maps with the same
points and these windows (all in 2026): `a` from 15 February to 15 April, `b`
from 10 to 20 March, `c` from 1 March to 1 April and `d` from 1 March to 10
April. The raster maps are the monthly maps `level_1` to `level_6`, so
`level_3` lasts from 1 March to 1 April, `level_2` from 1 February to 1 March
and `level_4` from 1 April to 1 May. For each relation the loop makes a dataset
`windows_<relation>` with four copies of a template map, runs the tool, and
prints the raster columns of each copy.

Compare the rows of a window in the output:

- `start`: `level_3` and `level_4` for `a` and `d`, because both start inside
  these windows, though `level_4` ends after them; `level_3` alone for `c`,
  which it equals; nothing for `b`, because `level_3` starts before it.
- `during`: `level_3` for `a` and for `d`, which shares its start with
  `level_3`; nothing for `c`, which equals `level_3`.
- `overlap`: `level_2` and `level_4` for `a`, `level_4` for `d`.
- `contain`: `level_3` for `b`, which lies inside it.
- `equal`: `level_3` for `c`.
- `follows`: `level_4` for `c`, which ends when `level_4` starts.
- `precedes`: `level_2` for `c` and `d`, which start when `level_2` ends.

The last block uses a dataset `readings` of two time instants, 5 and 25 March,
and a window from 1 March to 1 April. No instant can contain a window, but with
**sampling**`=contain` the tool writes both columns: a STRDS with time instants
is always sampled as with `start`.

=== "Command line"

    ```sh
    v.in.ascii input=- output=window separator=comma \
        columns="x double precision, y double precision, height integer" <<EOF
    0.5,1.5,1
    1.5,1.5,2
    0.5,0.5,3
    1.5,0.5,4
    EOF
    for s in start during overlap contain equal follows precedes; do
        t.create type=stvds output=windows_$s title="Windows" \
            description="Sampling $s"
        for w in a b c d; do
            g.copy vector=window,${s}_$w
        done
        t.register type=vector input=windows_$s maps=${s}_a \
            start=2026-02-15 end=2026-04-15
        t.register type=vector input=windows_$s maps=${s}_b \
            start=2026-03-10 end=2026-03-20
        t.register type=vector input=windows_$s maps=${s}_c \
            start=2026-03-01 end=2026-04-01
        t.register type=vector input=windows_$s maps=${s}_d \
            start=2026-03-01 end=2026-04-10
        t.vect.what.strds input=windows_$s strds=levels sampling=$s
        for w in a b c d; do
            c=$(db.columns table=${s}_$w | awk '/^level_/' | paste -sd, -)
            echo "${s}_$w: ${c:--}"
        done
    done
    ```

    ```text
    start_a: level_3,level_4
    start_b: -
    start_c: level_3
    start_d: level_3,level_4
    during_a: level_3
    during_b: -
    during_c: -
    during_d: level_3
    overlap_a: level_2,level_4
    overlap_b: -
    overlap_c: -
    overlap_d: level_4
    contain_a: -
    contain_b: level_3
    contain_c: -
    contain_d: -
    equal_a: -
    equal_b: -
    equal_c: level_3
    equal_d: -
    follows_a: -
    follows_b: -
    follows_c: level_4
    follows_d: -
    precedes_a: -
    precedes_b: -
    precedes_c: level_2
    precedes_d: level_2
    ```

    ```sh
    for k in 1 2; do
        r.mapcalc expression="reading_$k = 100 * $k + 10 * row() + col()"
    done
    t.create output=readings title="Readings" description="Two instants"
    t.register input=readings maps=reading_1 start=2026-03-05
    t.register input=readings maps=reading_2 start=2026-03-25
    g.copy vector=window,instant_window
    t.create type=stvds output=instant_windows title="Windows" \
        description="One window"
    t.register type=vector input=instant_windows maps=instant_window \
        start=2026-03-01 end=2026-04-01
    t.vect.what.strds input=instant_windows strds=readings sampling=contain
    db.columns table=instant_window | awk '/^reading_/' | paste -sd, -
    ```

    ```text
    reading_1,reading_2
    ```

=== "Python (grass.tools)"

    ```python
    windows = {
        "a": ("2026-02-15", "2026-04-15"),
        "b": ("2026-03-10", "2026-03-20"),
        "c": ("2026-03-01", "2026-04-01"),
        "d": ("2026-03-01", "2026-04-10"),
    }
    tools.v_in_ascii(
        input=StringIO("0.5,1.5,1\n1.5,1.5,2\n0.5,0.5,3\n1.5,0.5,4\n"),
        output="window",
        separator="comma",
        columns="x double precision, y double precision, height integer",
    )
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
            tools.g_copy(vector=f"window,{name}")
            tools.t_register(type="vector", input=dataset, maps=name, start=start, end=end)
        tools.t_vect_what_strds(input=dataset, strds="levels", sampling=sampling)
        for letter in windows:
            name = f"{sampling}_{letter}"
            columns = tools.db_columns(table=name).text.split()
            raster_columns = [column for column in columns if column.startswith("level_")]
            print(f"{name}: {','.join(raster_columns) or '-'}")
    ```

    ```text
    start_a: level_3,level_4
    start_b: -
    start_c: level_3
    start_d: level_3,level_4
    during_a: level_3
    during_b: -
    during_c: -
    during_d: level_3
    overlap_a: level_2,level_4
    overlap_b: -
    overlap_c: -
    overlap_d: level_4
    contain_a: -
    contain_b: level_3
    contain_c: -
    contain_d: -
    equal_a: -
    equal_b: -
    equal_c: level_3
    equal_d: -
    follows_a: -
    follows_b: -
    follows_c: level_4
    follows_d: -
    precedes_a: -
    precedes_b: -
    precedes_c: level_2
    precedes_d: level_2
    ```

    ```python
    for k in (1, 2):
        tools.r_mapcalc(expression=f"reading_{k} = 100 * {k} + 10 * row() + col()")
    tools.t_create(output="readings", title="Readings", description="Two instants")
    tools.t_register(input="readings", maps="reading_1", start="2026-03-05")
    tools.t_register(input="readings", maps="reading_2", start="2026-03-25")
    tools.g_copy(vector="window,instant_window")
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
    tools.t_vect_what_strds(input="instant_windows", strds="readings", sampling="contain")
    columns = tools.db_columns(table="instant_window").text.split()
    print(",".join(column for column in columns if column.startswith("reading_")))
    ```

    ```text
    reading_1,reading_2
    ```

### Select vector maps by time and write the values again

**t_where** restricts the tool to the vector maps whose temporal metadata
match. Here it takes the maps that start on or after 1 February, so
`stations_2` and `stations_3` get the column `late` and `stations_1` does not.
The loop prints the columns named `late`, with `-` where there is none.

The second call repeats the first one with **--overwrite**. The columns exist
now, and the flag lets the tool write them again instead of stopping. The call
changes what is read: **method**`=maximum` takes the larger of the two maps of
`stations_2`, `level_3`, and **where** limits the new values to the points
with a `height` of at most 2. The points 1 and 2 of `stations_2` read 311 and
312 from `level_3`; the points 3 and 4 keep the values 221 and 222 of the first
call.

=== "Command line"

    ```sh
    t.vect.what.strds input=stations strds=levels column=late \
        t_where="start_time >= '2026-02-01'"
    for m in stations_1 stations_2 stations_3; do
        c=$(db.columns table=$m | awk '/^late$/')
        echo "$m: ${c:--}"
    done
    t.vect.what.strds --overwrite input=stations strds=levels column=late \
        method=maximum where="height <= 2" t_where="start_time >= '2026-02-01'"
    v.db.select map=stations_2 columns=cat,height,late
    ```

    ```text
    stations_1: -
    stations_2: late
    stations_3: late
    cat|height|late
    1|1|311
    2|2|312
    3|3|221
    4|4|222
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_what_strds(
        input="stations",
        strds="levels",
        column="late",
        t_where="start_time >= '2026-02-01'",
    )
    for name in ("stations_1", "stations_2", "stations_3"):
        columns = tools.db_columns(table=name).text.split()
        print(f"{name}: {'late' if 'late' in columns else '-'}")
    tools.t_vect_what_strds(
        input="stations",
        strds="levels",
        column="late",
        method="maximum",
        where="height <= 2",
        t_where="start_time >= '2026-02-01'",
        overwrite=True,
    )
    print(tools.v_db_select(map="stations_2", columns="cat,height,late").text)
    ```

    ```text
    stations_1: -
    stations_2: late
    stations_3: late
    cat|height|late
    1|1|311
    2|2|312
    3|3|221
    4|4|222
    ```

### Relative time

The dataset `steps` has three raster maps for the hours 0 to 1, 1 to 2 and 2 to
3, and `probes` two vector maps with the intervals 0 to 2 and 2 to 3, both in
hours. Both datasets have relative time. `probe_1` has `step_1` and `step_2` in
its interval, so **method**`=average` stores their mean, 111 and 211 for the
first point, 161, in the column `steps_average`. `probe_2` has only `step_3`,
which is stored under its own name, 311 for the first point.

The last block shows that the tool does not look at the unit. The vector map
`probe_days` has the interval 0 to 2 days, while `steps` counts hours. The
tool compares the numbers: it takes `step_1` and `step_2`, which start at 0 and
1, but not `step_3`, which starts at 2, although 2 days are 48 hours and cover
all three maps. Use the same unit in both datasets.

=== "Command line"

    ```sh
    for k in 1 2 3; do
        r.mapcalc expression="step_$k = 100 * $k + 10 * row() + col()"
    done
    t.create output=steps temporaltype=relative title="Steps" \
        description="Three hourly maps"
    t.register -i input=steps maps=step_1,step_2,step_3 \
        start=0 increment=1 unit=hours
    g.copy vector=window,probe_1
    g.copy vector=window,probe_2
    t.create type=stvds temporaltype=relative output=probes title="Probes" \
        description="Two intervals"
    t.register type=vector input=probes maps=probe_1 start=0 end=2 unit=hours
    t.register type=vector input=probes maps=probe_2 start=2 end=3 unit=hours
    t.vect.what.strds input=probes strds=steps method=average
    v.db.select map=probe_1
    v.db.select map=probe_2
    ```

    ```text
    cat|x|y|height|steps_average
    1|0.5|1.5|1|161
    2|1.5|1.5|2|162
    3|0.5|0.5|3|171
    4|1.5|0.5|4|172
    cat|x|y|height|step_3
    1|0.5|1.5|1|311
    2|1.5|1.5|2|312
    3|0.5|0.5|3|321
    4|1.5|0.5|4|322
    ```

    ```sh
    g.copy vector=window,probe_days
    t.create type=stvds temporaltype=relative output=probes_days \
        title="Probes in days" description="One interval in days"
    t.register type=vector input=probes_days maps=probe_days \
        start=0 end=2 unit=days
    t.vect.what.strds input=probes_days strds=steps
    db.columns table=probe_days | awk '/^step_/' | paste -sd, -
    ```

    ```text
    step_1,step_2
    ```

=== "Python (grass.tools)"

    ```python
    for k in range(1, 4):
        tools.r_mapcalc(expression=f"step_{k} = 100 * {k} + 10 * row() + col()")
    tools.t_create(
        output="steps",
        temporaltype="relative",
        title="Steps",
        description="Three hourly maps",
    )
    tools.t_register(
        input="steps",
        maps="step_1,step_2,step_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.g_copy(vector="window,probe_1")
    tools.g_copy(vector="window,probe_2")
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="probes",
        title="Probes",
        description="Two intervals",
    )
    tools.t_register(
        type="vector", input="probes", maps="probe_1", start=0, end=2, unit="hours"
    )
    tools.t_register(
        type="vector", input="probes", maps="probe_2", start=2, end=3, unit="hours"
    )
    tools.t_vect_what_strds(input="probes", strds="steps", method="average")
    print(tools.v_db_select(map="probe_1").text)
    print(tools.v_db_select(map="probe_2").text)
    ```

    ```text
    cat|x|y|height|steps_average
    1|0.5|1.5|1|161
    2|1.5|1.5|2|162
    3|0.5|0.5|3|171
    4|1.5|0.5|4|172
    cat|x|y|height|step_3
    1|0.5|1.5|1|311
    2|1.5|1.5|2|312
    3|0.5|0.5|3|321
    4|1.5|0.5|4|322
    ```

    ```python
    tools.g_copy(vector="window,probe_days")
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="probes_days",
        title="Probes in days",
        description="One interval in days",
    )
    tools.t_register(
        type="vector",
        input="probes_days",
        maps="probe_days",
        start=0,
        end=2,
        unit="days",
    )
    tools.t_vect_what_strds(input="probes_days", strds="steps")
    columns = tools.db_columns(table="probe_days").text.split()
    print(",".join(column for column in columns if column.startswith("step_")))
    ```

    ```text
    step_1,step_2
    ```

### Datasets of another mapset

The example creates the mapset `analysis` and switches to it, where the region
is its own and is set again. The dataset `levels` stays in `PERMANENT`, and
**strds**`=levels@PERMANENT` names it with its mapset. The vector map `remote`
and its dataset belong to `analysis`, so the tool writes the columns `level_2`
and `level_3` into the table of `remote` in the current mapset. The second
block asks for the dataset `stations` in `PERMANENT` as **input**. The tool
refuses it before it writes anything, because it would have to change the
tables of vector maps of another mapset, and the block prints the message.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=2 w=0 res=1
    g.copy vector=window@PERMANENT,remote
    t.create type=stvds output=remote_ds title="Remote" \
        description="One interval in the new mapset"
    t.register type=vector input=remote_ds maps=remote \
        start=2026-02-01 end=2026-04-01
    t.vect.what.strds input=remote_ds strds=levels@PERMANENT
    v.db.select map=remote
    ```

    ```text
    cat|x|y|height|level_2|level_3
    1|0.5|1.5|1|211|311
    2|1.5|1.5|2|212|312
    3|0.5|0.5|3|221|321
    4|1.5|0.5|4|222|322
    ```

    ```sh
    if ! t.vect.what.strds input=stations@PERMANENT strds=levels@PERMANENT \
        column=other 2>&1; then
        echo "t.vect.what.strds failed"
    fi
    ```

    ```text
    ERROR: Vector map <stations_1@PERMANENT> is not in the current mapset, so
           its table cannot be written
           Vector map <stations_2@PERMANENT> is not in the current mapset, so
           its table cannot be written
           Vector map <stations_3@PERMANENT> is not in the current mapset, so
           its table cannot be written
    t.vect.what.strds failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.g_copy(vector="window@PERMANENT,remote")
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
        start="2026-02-01",
        end="2026-04-01",
    )
    tools.t_vect_what_strds(input="remote_ds", strds="levels@PERMANENT")
    print(tools.v_db_select(map="remote").text)
    ```

    ```text
    cat|x|y|height|level_2|level_3
    1|0.5|1.5|1|211|311
    2|1.5|1.5|2|212|312
    3|0.5|0.5|3|221|321
    4|1.5|0.5|4|222|322
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_vect_what_strds(
            input="stations@PERMANENT", strds="levels@PERMANENT", column="other"
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.what.strds failed")
    ```

    ```text
    ERROR: Vector map <stations_1@PERMANENT> is not in the current mapset, so
           its table cannot be written
           Vector map <stations_2@PERMANENT> is not in the current mapset, so
           its table cannot be written
           Vector map <stations_3@PERMANENT> is not in the current mapset, so
           its table cannot be written
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
