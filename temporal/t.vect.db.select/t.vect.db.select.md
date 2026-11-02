## DESCRIPTION

*t.vect.db.select* prints the attribute tables of the vector maps that are
registered in a space time vector dataset. It runs
*[v.db.select](v.db.select.md)* on each map, in the order of the start times of
the maps, and puts the start and end time of the map in front of every row. Use
it to see the attributes of a whole time series at once, or to find the rows of
all maps that meet one condition. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. *[t.vect.list](t.vect.list.md)* lists the maps themselves, and
*[t.vect.univar](t.vect.univar.md)* calculates statistics of their attributes.

The option **input** names the space time vector dataset. It is searched in the
mapsets of the search path, so a dataset of another mapset can be named with or
without its mapset; the last example shows both forms. The maps are read from
their own mapsets.

### Select maps and rows

The option **t_where** selects maps of the dataset. It takes an SQL condition on
the columns of the registered maps, the columns that *t.vect.list* offers, such
as `start_time >= '2026-03-02'` or `name = 'gauges_2'`. Without **t_where**, all
maps are used. The option **where** selects rows. It takes an SQL condition on
the columns of the attribute table, such as `speed > 22`, and is applied to the
table of each selected map. Both options leave out the word `where`, and they
can be combined: a row is printed if its map meets **t_where** and the row meets
**where**.

The option **layer** (default `1`) is the layer whose table is printed. A map
that is registered in the dataset with a layer, as `name:2`, always uses that
layer, and the option **layer** applies to the maps registered without one,
unless an earlier map was registered with a layer; see the notes. The layer
example shows both.

### Select columns

The option **columns** takes the names of the table columns to print, separated
by commas, in the order in which they are given. Without **columns**, all
columns of the table are printed in the order of the table. The names are
compared without regard to case, as the database does. Besides plain names,
**columns** takes the star and SQL expressions such as `speed * 2`, which
*v.db.select* evaluates for each row.

### Output

Every row starts with two columns, `start_time` and `end_time`, the times of the
map that the row comes from; the other columns are those of the attribute table.
A map registered as a time instant has no end time: the column is empty in the
formats `plain` and `csv` and `null` in `json`. With relative time, the times
are numbers in the unit of the dataset.

The option **format** chooses the form of the output:

- `plain` (the default) prints one header line with the column names and then
  one line per row. The columns are separated by `|`.
- `csv` prints the same lines, separated by a comma. Text values are put in
  double quotes.
- `json` prints a single list that holds one object per row, with the keys
  `start_time` and `end_time` first and then the columns. Numbers stay numbers
  and text values are strings.

The option **separator** replaces the separator of the columns in `plain` and
`csv`. It takes a character or a name such as `comma`, as the example shows.
In `csv` the separator must be a single character. `json` does not take a
separator.

### Several maps

The header line is printed before the rows of the first map. When the next map
has other columns, the header is printed again before its rows, so each block of
lines has the header that belongs to it. Maps with the same columns share one
header. A map without a row that meets **where** adds no line, except a header
if its columns differ. The format `json` has no headers. Its list holds the rows
of all maps.

## NOTES

All maps are checked before the first line is printed, for their attribute
table and for the columns named in **columns**. If a map has no attribute table
in the layer used for it, or lacks such a column, the module ends with an error
that lists the maps and prints nothing. The star and SQL expressions in
**columns** are not checked; *v.db.select* evaluates them in the table of each
map. A column of **where** is not checked in advance. An error in **where** ends
the module with the message of *v.db.select*, for example "incomplete input",
and a column that the table of a later map lacks stops the module at that map,
after the lines of the earlier maps have been printed.

If **t_where** selects no map, the module prints a warning and ends
successfully: the output is empty, or `[]` for the JSON format. An error in
**t_where** ends the module with the message "Invalid t_where condition".

A separator longer than one character with the format `csv`, and any separator
with the format `json`, are refused.

A map is read with the layer it is registered with. A map that is registered
without a layer takes the layer of the last selected map before it, in the order
of the start times, that is registered with one, and the option **layer** only
if there is none. The order of registration does not matter, and a map that
**t_where** leaves out passes on nothing. The layer example
shows the case, which is easy to miss: register such maps with the layer they
need, as `name:1`, or keep them in a dataset of their own.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Print the attributes of the maps of a dataset

The dataset `gauges` has three point maps of wind speed for the days from 1 to
3 March 2026. Map `gauges_k` has three points at `(k, 1)`, `(k, 2)` and
`(k, 3)` with the speeds `10 * k + 1`, `10 * k + 2` and `10 * k + 3` and the
sites `inland`, `coast` and `ridge`. The table of each map has the columns
`cat`, `x`, `y`, `speed` and `site`.

The first block prints the whole table of the three maps, nine rows. Each row
starts with the start and end time of its map. The second block prints the two
columns `cat` and `speed` only; the columns come in the order of **columns**.

=== "Command line"

    ```sh
    for k in 1 2 3; do
        v.in.ascii input=- output=gauges_$k separator=comma \
            columns="x double precision, y double precision, speed double precision, site text" <<EOF
    $k,1,$((10 * k + 1)),inland
    $k,2,$((10 * k + 2)),coast
    $k,3,$((10 * k + 3)),ridge
    EOF
    done
    t.create type=stvds output=gauges title="Wind speed" \
        description="Wind speed at three gauges"
    t.register -i type=vector input=gauges \
        maps=gauges_1,gauges_2,gauges_3 \
        start=2026-03-01 increment="1 day"
    t.vect.db.select input=gauges
    ```

    ```text
    start_time|end_time|cat|x|y|speed|site
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1|1|11|inland
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|1|2|12|coast
    2026-03-01 00:00:00|2026-03-02 00:00:00|3|1|3|13|ridge
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|2|1|21|inland
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2|2|22|coast
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|2|3|23|ridge
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|3|1|31|inland
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|3|2|32|coast
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|3|3|33|ridge
    ```

    ```sh
    t.vect.db.select input=gauges columns=speed,cat
    ```

    ```text
    start_time|end_time|speed|cat
    2026-03-01 00:00:00|2026-03-02 00:00:00|11|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|12|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|13|3
    2026-03-02 00:00:00|2026-03-03 00:00:00|21|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|22|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|23|3
    2026-03-03 00:00:00|2026-03-04 00:00:00|31|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|32|2
    2026-03-03 00:00:00|2026-03-04 00:00:00|33|3
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    sites = ("inland", "coast", "ridge")
    for k in range(1, 4):
        rows = "".join(f"{k},{i},{10 * k + i},{sites[i - 1]}\n" for i in (1, 2, 3))
        tools.v_in_ascii(
            input=StringIO(rows),
            output=f"gauges_{k}",
            separator="comma",
            columns="x double precision, y double precision, "
            "speed double precision, site text",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Wind speed",
        description="Wind speed at three gauges",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2,gauges_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_vect_db_select(input="gauges").text)
    ```

    ```text
    start_time|end_time|cat|x|y|speed|site
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1|1|11|inland
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|1|2|12|coast
    2026-03-01 00:00:00|2026-03-02 00:00:00|3|1|3|13|ridge
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|2|1|21|inland
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2|2|22|coast
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|2|3|23|ridge
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|3|1|31|inland
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|3|2|32|coast
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|3|3|33|ridge
    ```

    ```python
    print(tools.t_vect_db_select(input="gauges", columns="speed,cat").text)
    ```

    ```text
    start_time|end_time|speed|cat
    2026-03-01 00:00:00|2026-03-02 00:00:00|11|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|12|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|13|3
    2026-03-02 00:00:00|2026-03-03 00:00:00|21|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|22|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|23|3
    2026-03-03 00:00:00|2026-03-04 00:00:00|31|1
    2026-03-03 00:00:00|2026-03-04 00:00:00|32|2
    2026-03-03 00:00:00|2026-03-04 00:00:00|33|3
    ```

### Select rows and maps

The first block prints the points with a speed above 22 from every map. The
condition **where** is applied to each table: the first map has none, the
second the point with 23, the third all three. The second block selects the maps
that start on 2 March or later and prints all their rows. The third block
combines both: the point with the category 2 of the maps that start on 2 March
or later.

=== "Command line"

    ```sh
    t.vect.db.select input=gauges columns=cat,speed where="speed > 22"
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|23
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|33
    ```

    ```sh
    t.vect.db.select input=gauges columns=cat,speed \
        t_where="start_time >= '2026-03-02'"
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|22
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|23
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|33
    ```

    ```sh
    t.vect.db.select input=gauges columns=cat,speed \
        where="cat = 2" t_where="start_time >= '2026-03-02'"
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|22
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    ```

=== "Python (grass.tools)"

    ```python
    print(
        tools.t_vect_db_select(input="gauges", columns="cat,speed", where="speed > 22").text
    )
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|23
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|33
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges", columns="cat,speed", t_where="start_time >= '2026-03-02'"
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|22
    2026-03-02 00:00:00|2026-03-03 00:00:00|3|23
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    2026-03-03 00:00:00|2026-03-04 00:00:00|3|33
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges",
            columns="cat,speed",
            where="cat = 2",
            t_where="start_time >= '2026-03-02'",
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|22
    2026-03-03 00:00:00|2026-03-04 00:00:00|2|32
    ```

### Choose the output format

All blocks print the point with the category 1 of each map and the columns `cat`
and `site`. The first block uses `csv`: the separator is a comma and the text
values are in double quotes. The second block sets **separator** to a semicolon
for `csv`. The third block shows `plain` with the separator `comma`, which
differs from `csv` by the missing quotes. The fourth block uses `json`: a list
with one object for each row, the times first.

=== "Command line"

    ```sh
    t.vect.db.select input=gauges columns=cat,site where="cat = 1" format=csv
    ```

    ```text
    start_time,end_time,cat,site
    2026-03-01 00:00:00,2026-03-02 00:00:00,1,"inland"
    2026-03-02 00:00:00,2026-03-03 00:00:00,1,"inland"
    2026-03-03 00:00:00,2026-03-04 00:00:00,1,"inland"
    ```

    ```sh
    t.vect.db.select input=gauges columns=cat,site where="cat = 1" \
        format=csv separator=";"
    ```

    ```text
    start_time;end_time;cat;site
    2026-03-01 00:00:00;2026-03-02 00:00:00;1;"inland"
    2026-03-02 00:00:00;2026-03-03 00:00:00;1;"inland"
    2026-03-03 00:00:00;2026-03-04 00:00:00;1;"inland"
    ```

    ```sh
    t.vect.db.select input=gauges columns=cat,site where="cat = 1" \
        separator=comma
    ```

    ```text
    start_time,end_time,cat,site
    2026-03-01 00:00:00,2026-03-02 00:00:00,1,inland
    2026-03-02 00:00:00,2026-03-03 00:00:00,1,inland
    2026-03-03 00:00:00,2026-03-04 00:00:00,1,inland
    ```

    ```sh
    t.vect.db.select input=gauges columns=cat,site where="cat = 1" format=json
    ```

    ```text
    [
        {
            "start_time": "2026-03-01 00:00:00",
            "end_time": "2026-03-02 00:00:00",
            "cat": 1,
            "site": "inland"
        },
        {
            "start_time": "2026-03-02 00:00:00",
            "end_time": "2026-03-03 00:00:00",
            "cat": 1,
            "site": "inland"
        },
        {
            "start_time": "2026-03-03 00:00:00",
            "end_time": "2026-03-04 00:00:00",
            "cat": 1,
            "site": "inland"
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges", columns="cat,site", where="cat = 1", format="csv"
        ).text
    )
    ```

    ```text
    start_time,end_time,cat,site
    2026-03-01 00:00:00,2026-03-02 00:00:00,1,"inland"
    2026-03-02 00:00:00,2026-03-03 00:00:00,1,"inland"
    2026-03-03 00:00:00,2026-03-04 00:00:00,1,"inland"
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges",
            columns="cat,site",
            where="cat = 1",
            format="csv",
            separator=";",
        ).text
    )
    ```

    ```text
    start_time;end_time;cat;site
    2026-03-01 00:00:00;2026-03-02 00:00:00;1;"inland"
    2026-03-02 00:00:00;2026-03-03 00:00:00;1;"inland"
    2026-03-03 00:00:00;2026-03-04 00:00:00;1;"inland"
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges", columns="cat,site", where="cat = 1", separator="comma"
        ).text
    )
    ```

    ```text
    start_time,end_time,cat,site
    2026-03-01 00:00:00,2026-03-02 00:00:00,1,inland
    2026-03-02 00:00:00,2026-03-03 00:00:00,1,inland
    2026-03-03 00:00:00,2026-03-04 00:00:00,1,inland
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges", columns="cat,site", where="cat = 1", format="json"
        ).text
    )
    ```

    ```text
    [
        {
            "start_time": "2026-03-01 00:00:00",
            "end_time": "2026-03-02 00:00:00",
            "cat": 1,
            "site": "inland"
        },
        {
            "start_time": "2026-03-02 00:00:00",
            "end_time": "2026-03-03 00:00:00",
            "cat": 1,
            "site": "inland"
        },
        {
            "start_time": "2026-03-03 00:00:00",
            "end_time": "2026-03-04 00:00:00",
            "cat": 1,
            "site": "inland"
        }
    ]
    ```

### Time instants and relative time

The dataset `readings` has two maps that are registered as time instants, for 1
and 2 March 2026. Each has one point with the column `depth`. The end time is
empty: the first block shows the two separators `||` next to each other in the plain
format, and the second block shows `null` in `json`. The dataset `cycles` has
two maps of relative time in days, from 0 to 1 and from 1 to 2. Its times are
numbers.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.in.ascii input=- output=reading_$k separator=comma \
            columns="x double precision, y double precision, depth double precision" <<EOF
    $k,1,$((5 * k))
    EOF
        v.in.ascii input=- output=cycle_$k separator=comma \
            columns="x double precision, y double precision, depth double precision" <<EOF
    $k,1,$((7 * k))
    EOF
    done
    t.create type=stvds output=readings title="Readings" \
        description="Depth readings as time instants"
    t.register type=vector input=readings maps=reading_1,reading_2 \
        start=2026-03-01 increment="1 day"
    t.create type=stvds temporaltype=relative output=cycles title="Cycles" \
        description="Depth per cycle"
    t.register -i type=vector input=cycles maps=cycle_1,cycle_2 \
        start=0 increment=1 unit=days
    t.vect.db.select input=readings columns=cat,depth
    ```

    ```text
    start_time|end_time|cat|depth
    2026-03-01 00:00:00||1|5
    2026-03-02 00:00:00||1|10
    ```

    ```sh
    t.vect.db.select input=readings columns=cat,depth where="depth > 5" format=json
    ```

    ```text
    [
        {
            "start_time": "2026-03-02 00:00:00",
            "end_time": null,
            "cat": 1,
            "depth": 10
        }
    ]
    ```

    ```sh
    t.vect.db.select input=cycles columns=cat,depth
    ```

    ```text
    start_time|end_time|cat|depth
    0|1|1|7
    1|2|1|14
    ```

=== "Python (grass.tools)"

    ```python
    for k in (1, 2):
        tools.v_in_ascii(
            input=StringIO(f"{k},1,{5 * k}\n"),
            output=f"reading_{k}",
            separator="comma",
            columns="x double precision, y double precision, depth double precision",
        )
        tools.v_in_ascii(
            input=StringIO(f"{k},1,{7 * k}\n"),
            output=f"cycle_{k}",
            separator="comma",
            columns="x double precision, y double precision, depth double precision",
        )
    tools.t_create(
        type="stvds",
        output="readings",
        title="Readings",
        description="Depth readings as time instants",
    )
    tools.t_register(
        type="vector",
        input="readings",
        maps="reading_1,reading_2",
        start="2026-03-01",
        increment="1 day",
    )
    tools.t_create(
        type="stvds",
        temporaltype="relative",
        output="cycles",
        title="Cycles",
        description="Depth per cycle",
    )
    tools.t_register(
        type="vector",
        input="cycles",
        maps="cycle_1,cycle_2",
        start=0,
        increment=1,
        unit="days",
        flags="i",
    )
    print(tools.t_vect_db_select(input="readings", columns="cat,depth").text)
    ```

    ```text
    start_time|end_time|cat|depth
    2026-03-01 00:00:00||1|5
    2026-03-02 00:00:00||1|10
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="readings", columns="cat,depth", where="depth > 5", format="json"
        ).text
    )
    ```

    ```text
    [
        {
            "start_time": "2026-03-02 00:00:00",
            "end_time": null,
            "cat": 1,
            "depth": 10
        }
    ]
    ```

    ```python
    print(tools.t_vect_db_select(input="cycles", columns="cat,depth").text)
    ```

    ```text
    start_time|end_time|cat|depth
    0|1|1|7
    1|2|1|14
    ```

### Choose the layer

The dataset `plots` has two maps for 1 and 2 March 2026. Each has two points
with the categories 1 and 2 in layer 1 and in layer 2. The table of layer 1 has
the column `count` with the values 1 and 2, the table of layer 2 the values 101
and 102. The maps are registered without a layer, so the first block prints
layer 1 and the second block, with **layer** set to 2, prints layer 2.

The dataset `both` registers the two layers of `plots_1` as `plots_1:1` and
`plots_1:2`. The third block prints both, and a **layer** option does not change
this: the registered layer wins.

The dataset `mixed` shows the case that the notes warn about. It registers
`plots_1:2` for 1 March and `plots_2` without a layer for 2 March. The fourth
block prints layer 2 for both maps: the second map takes the layer of the
first and shows 101 and 102, not the values 1 and 2 of its layer 1.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.edit map=plots_$k tool=create
        v.edit map=plots_$k tool=add input=- <<EOF
    VERTI:
    P 1 2
     $k 1
     1 1
     2 1
    P 1 2
     $k 2
     1 2
     2 2
    EOF
        v.db.addtable map=plots_$k columns="count integer"
        v.db.addtable map=plots_$k layer=2 table=plots_${k}_b columns="count integer"
        db.execute input=- <<EOF
    UPDATE plots_$k SET count = cat;
    UPDATE plots_${k}_b SET count = 100 + cat;
    EOF
    done
    t.create type=stvds output=plots title="Plots" \
        description="Two layers per map"
    t.register -i type=vector input=plots maps=plots_1,plots_2 \
        start=2026-03-01 increment="1 day"
    t.vect.db.select input=plots
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2
    ```

    ```sh
    t.vect.db.select input=plots layer=2
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

    ```sh
    t.create type=stvds output=both title="Both layers" \
        description="Two layers of one map"
    t.register type=vector input=both maps=plots_1:1,plots_1:2 \
        start=2026-03-01 end=2026-03-02
    t.vect.db.select input=both layer=2
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    ```

    ```sh
    t.create type=stvds output=mixed title="Mixed layers" \
        description="A map with a layer, then one without"
    t.register type=vector input=mixed maps=plots_1:2 \
        start=2026-03-01 end=2026-03-02
    t.register type=vector input=mixed maps=plots_2 \
        start=2026-03-02 end=2026-03-03
    t.vect.db.select input=mixed
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

=== "Python (grass.tools)"

    ```python
    features = "VERTI:\nP 1 2\n {k} 1\n 1 1\n 2 1\nP 1 2\n {k} 2\n 1 2\n 2 2\n"
    for k in (1, 2):
        tools.v_edit(map=f"plots_{k}", tool="create")
        tools.v_edit(map=f"plots_{k}", tool="add", input=StringIO(features.format(k=k)))
        tools.v_db_addtable(map=f"plots_{k}", columns="count integer")
        tools.v_db_addtable(
            map=f"plots_{k}", layer=2, table=f"plots_{k}_b", columns="count integer"
        )
        sql = f"UPDATE plots_{k} SET count = cat;\n"
        sql += f"UPDATE plots_{k}_b SET count = 100 + cat;\n"
        tools.db_execute(input=StringIO(sql))
    tools.t_create(
        type="stvds", output="plots", title="Plots", description="Two layers per map"
    )
    tools.t_register(
        type="vector",
        input="plots",
        maps="plots_1,plots_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_vect_db_select(input="plots").text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|1
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|2
    ```

    ```python
    print(tools.t_vect_db_select(input="plots", layer=2).text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="both",
        title="Both layers",
        description="Two layers of one map",
    )
    tools.t_register(
        type="vector",
        input="both",
        maps="plots_1:1,plots_1:2",
        start="2026-03-01",
        end="2026-03-02",
    )
    print(tools.t_vect_db_select(input="both", layer=2).text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|1
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|2
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="mixed",
        title="Mixed layers",
        description="A map with a layer, then one without",
    )
    tools.t_register(
        type="vector",
        input="mixed",
        maps="plots_1:2",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_register(
        type="vector",
        input="mixed",
        maps="plots_2",
        start="2026-03-02",
        end="2026-03-03",
    )
    print(tools.t_vect_db_select(input="mixed").text)
    ```

    ```text
    start_time|end_time|cat|count
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|101
    2026-03-01 00:00:00|2026-03-02 00:00:00|2|102
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|101
    2026-03-02 00:00:00|2026-03-03 00:00:00|2|102
    ```

### Print from a dataset of another mapset

The dataset `gauges` stays in the mapset `PERMANENT`. The first block creates
the mapset `other`, switches to it and prints the dataset by its name alone,
which is found in the search path. The second block names the mapset. Both
print the same rows.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    t.vect.db.select input=gauges columns=cat,speed where="cat = 1"
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|11
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    ```

    ```sh
    t.vect.db.select input=gauges@PERMANENT columns=cat,speed where="cat = 1"
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|11
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="other", flags="c")
    print(tools.t_vect_db_select(input="gauges", columns="cat,speed", where="cat = 1").text)
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|11
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="gauges@PERMANENT", columns="cat,speed", where="cat = 1"
        ).text
    )
    ```

    ```text
    start_time|end_time|cat|speed
    2026-03-01 00:00:00|2026-03-02 00:00:00|1|11
    2026-03-02 00:00:00|2026-03-03 00:00:00|1|21
    2026-03-03 00:00:00|2026-03-04 00:00:00|1|31
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.create](t.create.md), [t.info](t.info.md),
[t.vect.list](t.vect.list.md), [t.vect.univar](t.vect.univar.md),
[v.db.select](v.db.select.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
