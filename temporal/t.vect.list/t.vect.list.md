## DESCRIPTION

*t.vect.list* lists the vector maps that are registered in a space time vector
dataset, with the metadata that the temporal database holds for each map. It
reads the temporal database; the maps themselves are not opened. The listing is
the usual step after *[t.info](t.info.md)* has shown the dataset as a whole and
before a tool such as *[t.vect.extract](t.vect.extract.md)* works on its maps.
See the [introduction to temporal data processing](temporalintro.md) for space
time datasets. The tool is the counterpart of
*[t.rast.list](t.rast.list.md)* for vector maps, with the same options,
formats and methods; the differences are the columns of the vector topology
(see below), the column `layer`, the method `cols` instead of `list`, and the
absence of the option **granule**. Space time 3D raster datasets have their
own tool, *[t.rast3d.list](t.rast3d.list.md)*, and *[t.list](t.list.md)* lists
the datasets themselves.

### Select the maps

The option **input** names the space time vector dataset. The option **where**
takes an SQL condition on the columns of the registered maps, such as
`points > 0`, `name = 'survey_1'` or `start_time >= '2026-03-02'`. Times are
compared as text, so a time with a clock part needs the whole text:
`start_time = '2026-03-02'` selects nothing, because the stored value is
`2026-03-02 00:00:00`. Use `>=` and `<` for a day, or `name` for a single map.
The function `strftime()` of SQLite selects recurring times, such as one day of
the month or one month of the year. A condition with a syntax error stops with
an error that starts with "Invalid where condition". With the methods `delta`,
`deltagaps` and `gran`, the condition selects the maps before the lengths and
distances are counted, so the distances start at 0 with the first selected map.

### Columns and order

The option **columns** chooses the columns that are printed for each map,
separated by commas. The columns are:

- `id`, the name of the map with its mapset, such as `survey_1@PERMANENT`; for
  a map that is registered with a layer, the layer follows the name after a
  colon, such as `gauge:2@PERMANENT`. `name` and `mapset` are the two parts of
  it, without the layer;
- `layer`, the layer of the map that is registered, `None` for a map that is
  registered without a layer. Several layers of one map are registered one by
  one, and each is a map of the dataset with its own time;
- `temporal_type`, `absolute` or `relative`;
- `start_time` and `end_time`, the time of the map. The end time of a map
  registered as a time instant is `None`. With relative time, they are numbers
  in the unit of the dataset, printed without the unit;
- `creator` and `creation_time`, the user who created the entry of the map in
  the temporal database and the time of its creation;
- `north`, `south`, `west` and `east`, the bounding box of the map;
- `points`, `lines`, `boundaries`, `centroids`, `faces` and `kernels`, the
  numbers of features of each type. The feature types are the ones that the
  vector topology of GRASS knows; the maps of the examples hold points, lines,
  boundaries and centroids only, so `faces` and `kernels` are 0 there;
- `primitives`, the number of all features; in the maps of the examples it is
  the sum of the numbers above;
- `nodes`, the number of nodes, which are the points where a line or a
  boundary starts or ends; `areas`, the number of areas that the boundaries
  enclose, with or without a centroid; `islands`, the number of islands;
  `holes` and `volumes`, the numbers of holes and volumes that the topology
  counts (0 for the maps of the examples);
- `interval_length` and `distance_from_begin`, the length of the time interval
  of the map and the distance of its start from the start of the first listed
  map. They exist for the methods `delta`, `deltagaps` and `gran` only (see
  below). With absolute time they are numbers of days, with relative time
  numbers of the time unit of the dataset.

The numbers of the topology come from the geometry of the map; the first
example derives them for four small maps.

The option **order** sorts the maps by one or more columns, separated by
commas; the possible columns are those of the list above up to `volumes`, so
not `interval_length` and `distance_from_begin`. The default is `start_time`.
The order is ascending, and the option takes names of columns only, no sort
direction. The option works with the methods `cols` and `comma` only.

### Methods

The option **method** chooses what is listed. The default is `cols`.

- `cols` prints one line per registered map with the columns of **columns**.
  Without **columns**, these are `name`, `layer`, `mapset`, `start_time` and
  `end_time`; with `format=line`, the column `id`. It supports all columns
  except `interval_length` and `distance_from_begin`, and **order** applies to
  it.
- `delta` prints the maps ordered by start time with the length of their
  intervals and their distance from the first map. Without **columns**, the
  columns are `id`, `name`, `layer`, `mapset`, `start_time`, `end_time`,
  `interval_length` and `distance_from_begin`. The length of a time instant is
  `None`. `delta` supports only these columns.
- `deltagaps` is `delta` with a line for every temporal gap between two maps.
  A gap line has `None` as `id`, `name`, `layer` and `mapset`; its times are
  the end of the map before and the start of the map after the gap, and its
  length is the length of the gap. Maps that follow each other directly leave
  no gap.
- `gran` samples the maps by the granularity of the dataset and prints one
  line per granule, with the columns of `delta`. There is no option to choose
  another granule. The times and the length are those of the granule, not of
  the map, so a map that is longer than the granule is listed once for each
  granule it covers. A granule without a map has `None` as `id`, `name`,
  `layer` and `mapset`. When more than one map meets a granule, the line names
  the first map of the first group that is not empty, in this order: maps that
  are equal to the granule, maps that contain it, maps that overlap it, maps
  that are overlapped by it and maps that lie inside it. The sixth example
  shows a map that is equal to a granule named before a longer map that
  contains it. The granularity of a dataset is shown by
  *[t.info](t.info.md)* with the flag **-g**.
- `comma` is the old name of `cols` with `format=line`: it prints the values
  of the chosen column in one line, the ids without **columns**. Prefer the
  option **format**.

### Output

The option **format** chooses the form of the output:

- `plain` (the default) prints one line per map with the columns separated by
  a vertical bar `|`, and the column names as the first line;
- `line` prints the values of one column in one line, separated by commas. It
  takes one column only; the default column is `id`, so the line is a list of
  maps that other tools accept as input;
- `csv` prints comma separated values, with the column names as the first
  line. Text is enclosed in double quotes and numbers are not. A missing value
  (`None`) is an empty text;
- `json` prints an object with the key `data`, a list with one object per
  map, and the key `metadata` with the list `column_names`. A missing value is
  `null`, numbers are numbers, and times with absolute time and layers are
  text;
- `yaml` prints the same structure as YAML. It needs the PyYAML package.

The flag **-u** suppresses the line with the column names in the formats
`plain` and `csv`. The formats `json` and `yaml` always name the columns and
refuse **-u**.

The option **separator** replaces the separator of the formats `plain`, `csv`
and `line`. It is a single character or a name such as `pipe`, `comma` or
`tab`. The format `csv` accepts one character only, and `json` and `yaml`
refuse **separator**. The option **output** writes the listing to a file
instead of the standard output.

## NOTES

A column name that is not in the list above is refused by the parser, which
names the column.

If no map is listed, the result depends on the method and the format. The
methods `cols` and `comma` stop with the error "Nothing found in the database
for space time dataset `<name@mapset>` (type: stvds)", followed by "Dataset is
empty" for a dataset without maps and by "Dataset is empty or where clause is
too constrained or incorrect" when **where** selects nothing. With the format
`json`, `data` is an empty list. The methods `delta` and `deltagaps` print the
line with the column names only, both for a dataset without maps and when
**where** selects nothing. The method `gran` does the same when **where**
selects nothing in a dataset that has a granularity, but stops for a dataset
without maps with the error "Nothing found in the database for space time
dataset `<name@mapset>` (type: stvds)", followed by "Dataset is empty". A
dataset with a single map that is a time instant has no granularity, and `gran`
stops for it with the error "Wrong granularity: "None"", whatever **where**
selects, as the last block of the sixth example shows. Use `delta` for such a
dataset.

With relative time, the times are numbers of the time unit of the dataset,
printed without the unit, as the model in the fifth example shows. The method
`gran` works with relative time as well; the granularity of the dataset is the
granule.

The option **output** takes the name of a file. The name `-` is not the
standard output here: it writes a file with this name, as the last block of
the third example shows. To print the listing, leave out **output**; to keep it
in a file, give a file name other than `-`.

*t.vect.list* only reads, so it works on a dataset of another mapset as well.
The name with the mapset (`input=survey@PERMANENT`) selects it; a name without
a mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The last example shows this.

Combinations that cannot work are refused with a message that names the
options. **order** is refused with `delta`, `deltagaps` and `gran`. These
three methods list only the columns of `delta`, so a column of the temporal
database is refused with them, and `interval_length` and `distance_from_begin`
are refused with `cols` and `comma`. More than one column is refused with
`format=line`, **-u** and **separator** with `json` and `yaml`, and a separator
of more than one character with `csv`.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### List the maps of a dataset

The dataset `survey` has four vector maps on the days from 1 to 4 March 2026.
The first map has three points at (1, 1), (2, 3) and (5, 2). The second map has
two lines: one from (0, 0) to (4, 0) and one from (0, 1) to (0, 3). The third
map is a square from (0, 0) to (2, 2): one boundary that closes on itself, and
a centroid in the middle. The fourth map is a square from (0, 0) to (4, 4) with
a centroid at (3, 3) and a smaller ring from (1, 1) to (2, 2) inside, which has
no centroid. A space time vector dataset has the type `stvds`, and its maps are
registered with the type `vector`.

The first block lists the maps with the default columns. The second block adds
the flag **-u**, which suppresses the line with the column names, and names the
default method `cols`. The third block counts the features of each type and the
nodes. The points, lines, boundaries and centroids are the ones that were
written in the input, and each is a primitive, so the first map has 3
primitives and the second 2. A line has two nodes, if its ends lie apart, so
the second map has 4 nodes; a closed boundary has the node where it starts and
ends, so the third map has 1 node and the fourth map, with two rings, 2. The
fourth block counts the areas and islands: each ring bounds an island, so the
third map has 1 area and 1 island, and the fourth map, with an outer and an
inner ring, has 2 islands and 2 areas. The numbers of `holes`, `faces`,
`kernels` and `volumes` are 0 for all of them. The fifth block lists the extent
of the fourth map: its bounding box is the outer square.

=== "Command line"

    ```sh
    v.in.ascii -n input=- output=survey_1 format=point separator=comma <<EOF
    1,1
    2,3
    5,2
    EOF
    v.in.ascii input=- output=survey_2 format=standard <<EOF
    VERTI:
    L 2 1
     0 0
     4 0
     1 1
    L 2 1
     0 1
     0 3
     2 1
    EOF
    v.in.ascii input=- output=survey_3 format=standard <<EOF
    VERTI:
    B 5
     0 0
     2 0
     2 2
     0 2
     0 0
    C 1 1
     1 1
     1 1
    EOF
    v.in.ascii input=- output=survey_4 format=standard <<EOF
    VERTI:
    B 5
     0 0
     4 0
     4 4
     0 4
     0 0
    B 5
     1 1
     1 2
     2 2
     2 1
     1 1
    C 1 1
     3 3
     1 1
    EOF
    t.create type=stvds output=survey title="Survey" \
        description="Four maps with different features"
    t.register -i type=vector input=survey \
        maps=survey_1,survey_2,survey_3,survey_4 \
        start=2026-03-01 increment="1 day"
    t.vect.list input=survey
    ```

    ```text
    name|layer|mapset|start_time|end_time
    survey_1|None|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    survey_2|None|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    survey_3|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    survey_4|None|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.vect.list -u input=survey method=cols
    ```

    ```text
    survey_1|None|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    survey_2|None|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    survey_3|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    survey_4|None|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```sh
    t.vect.list input=survey \
        columns=name,points,lines,boundaries,centroids,primitives,nodes
    ```

    ```text
    name|points|lines|boundaries|centroids|primitives|nodes
    survey_1|3|0|0|0|3|0
    survey_2|0|2|0|0|2|4
    survey_3|0|0|1|1|2|1
    survey_4|0|0|2|1|3|2
    ```

    ```sh
    t.vect.list input=survey columns=name,areas,islands,holes,faces,kernels,volumes
    ```

    ```text
    name|areas|islands|holes|faces|kernels|volumes
    survey_1|0|0|0|0|0|0
    survey_2|0|0|0|0|0|0
    survey_3|1|1|0|0|0|0
    survey_4|2|2|0|0|0|0
    ```

    ```sh
    t.vect.list input=survey where="name = 'survey_4'" \
        columns=id,temporal_type,north,south,west,east
    ```

    ```text
    id|temporal_type|north|south|west|east
    survey_4@PERMANENT|absolute|4.0|0.0|0.0|4.0
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    tools.v_in_ascii(
        input=StringIO("1,1\n2,3\n5,2\n"),
        output="survey_1",
        format="point",
        separator="comma",
        flags="n",
    )
    lines = "VERTI:\nL 2 1\n 0 0\n 4 0\n 1 1\nL 2 1\n 0 1\n 0 3\n 2 1\n"
    tools.v_in_ascii(input=StringIO(lines), output="survey_2", format="standard")
    square = "VERTI:\nB 5\n 0 0\n 2 0\n 2 2\n 0 2\n 0 0\nC 1 1\n 1 1\n 1 1\n"
    tools.v_in_ascii(input=StringIO(square), output="survey_3", format="standard")
    rings = (
        "VERTI:\nB 5\n 0 0\n 4 0\n 4 4\n 0 4\n 0 0\n"
        "B 5\n 1 1\n 1 2\n 2 2\n 2 1\n 1 1\n"
        "C 1 1\n 3 3\n 1 1\n"
    )
    tools.v_in_ascii(input=StringIO(rings), output="survey_4", format="standard")
    tools.t_create(
        type="stvds",
        output="survey",
        title="Survey",
        description="Four maps with different features",
    )
    tools.t_register(
        type="vector",
        input="survey",
        maps="survey_1,survey_2,survey_3,survey_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_vect_list(input="survey").text)
    ```

    ```text
    name|layer|mapset|start_time|end_time
    survey_1|None|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    survey_2|None|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    survey_3|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    survey_4|None|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    print(tools.t_vect_list(input="survey", method="cols", flags="u").text)
    ```

    ```text
    survey_1|None|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    survey_2|None|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    survey_3|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    survey_4|None|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    ```python
    result = tools.t_vect_list(
        input="survey",
        columns="name,points,lines,boundaries,centroids,primitives,nodes",
    )
    print(result.text)
    ```

    ```text
    name|points|lines|boundaries|centroids|primitives|nodes
    survey_1|3|0|0|0|3|0
    survey_2|0|2|0|0|2|4
    survey_3|0|0|1|1|2|1
    survey_4|0|0|2|1|3|2
    ```

    ```python
    result = tools.t_vect_list(
        input="survey", columns="name,areas,islands,holes,faces,kernels,volumes"
    )
    print(result.text)
    ```

    ```text
    name|areas|islands|holes|faces|kernels|volumes
    survey_1|0|0|0|0|0|0
    survey_2|0|0|0|0|0|0
    survey_3|1|1|0|0|0|0
    survey_4|2|2|0|0|0|0
    ```

    ```python
    result = tools.t_vect_list(
        input="survey",
        where="name = 'survey_4'",
        columns="id,temporal_type,north,south,west,east",
    )
    print(result.text)
    ```

    ```text
    id|temporal_type|north|south|west|east
    survey_4@PERMANENT|absolute|4.0|0.0|0.0|4.0
    ```

### Select and sort the maps

The maps of `survey` are sorted by start time. The option **order** sorts by
other columns; the first block sorts by the number of primitives and then by
name, so the two maps with 2 primitives come first, `survey_2` before
`survey_3`, and the two maps with 3 primitives follow.

The option **where** selects the maps. The second block selects the maps with
areas, which are the third and the fourth. The third block selects the maps
that start from 2 March on and before 4 March, so the second and the third map.
The fourth block combines a condition on the number of nodes with **order**;
the first map has no node and drops out.
The fifth block uses `strftime()` to select the maps that start on the 1st or
the 4th day of the month, a recurring selection that works the same way for one
month of every year.

The last block shows a trap: a time compared with `=` must be the whole text
`2026-03-02 00:00:00`, and the short form selects no map. The format `json`
shows the empty result, `data` is an empty list; the formats `plain` and
`line` stop with an error here.

=== "Command line"

    ```sh
    t.vect.list input=survey columns=name,primitives order=primitives,name
    ```

    ```text
    name|primitives
    survey_2|2
    survey_3|2
    survey_1|3
    survey_4|3
    ```

    ```sh
    t.vect.list input=survey columns=name,areas where="areas > 0"
    ```

    ```text
    name|areas
    survey_3|1
    survey_4|2
    ```

    ```sh
    t.vect.list input=survey columns=name,start_time \
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'"
    ```

    ```text
    name|start_time
    survey_2|2026-03-02 00:00:00
    survey_3|2026-03-03 00:00:00
    ```

    ```sh
    t.vect.list input=survey columns=name,nodes order=nodes,name \
        where="nodes > 0"
    ```

    ```text
    name|nodes
    survey_3|1
    survey_4|2
    survey_2|4
    ```

    ```sh
    t.vect.list input=survey columns=name,start_time \
        where="strftime('%d', start_time) in ('01', '04')"
    ```

    ```text
    name|start_time
    survey_1|2026-03-01 00:00:00
    survey_4|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.list input=survey columns=name format=json \
        where="start_time = '2026-03-02'"
    echo
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_vect_list(
        input="survey", columns="name,primitives", order="primitives,name"
    )
    print(result.text)
    ```

    ```text
    name|primitives
    survey_2|2
    survey_3|2
    survey_1|3
    survey_4|3
    ```

    ```python
    result = tools.t_vect_list(input="survey", columns="name,areas", where="areas > 0")
    print(result.text)
    ```

    ```text
    name|areas
    survey_3|1
    survey_4|2
    ```

    ```python
    result = tools.t_vect_list(
        input="survey",
        columns="name,start_time",
        where="start_time >= '2026-03-02' and start_time < '2026-03-04'",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    survey_2|2026-03-02 00:00:00
    survey_3|2026-03-03 00:00:00
    ```

    ```python
    result = tools.t_vect_list(
        input="survey", columns="name,nodes", order="nodes,name", where="nodes > 0"
    )
    print(result.text)
    ```

    ```text
    name|nodes
    survey_3|1
    survey_4|2
    survey_2|4
    ```

    ```python
    result = tools.t_vect_list(
        input="survey",
        columns="name,start_time",
        where="strftime('%d', start_time) in ('01', '04')",
    )
    print(result.text)
    ```

    ```text
    name|start_time
    survey_1|2026-03-01 00:00:00
    survey_4|2026-03-04 00:00:00
    ```

    ```python
    result = tools.t_vect_list(
        input="survey",
        columns="name",
        format="json",
        where="start_time = '2026-03-02'",
    )
    print(result.text)
    ```

    ```text
    {"data": [], "metadata": {"column_names": ["name"]}}
    ```

### Choose the output format

All blocks list the dataset `survey`. The first block prints the maps as a list
of ids in one line, the form that other tools accept as input; the second
block does the same with the old method name `comma`; the third block prints
the names only, with another separator. The fourth and fifth block print CSV
with and without the line of column names; text is quoted and numbers are not.
The sixth block replaces the separator of the plain format. The seventh block
prints JSON, which the Python tab reads from `result.json` and prints name and
number of points of each map. The eighth block writes the listing to a file and
prints the file. The ninth block shows that `output=-` writes a file named `-`.

=== "Command line"

    ```sh
    t.vect.list input=survey format=line
    ```

    ```text
    survey_1@PERMANENT,survey_2@PERMANENT,survey_3@PERMANENT,survey_4@PERMANENT
    ```

    ```sh
    t.vect.list input=survey method=comma
    ```

    ```text
    survey_1@PERMANENT,survey_2@PERMANENT,survey_3@PERMANENT,survey_4@PERMANENT
    ```

    ```sh
    t.vect.list input=survey format=line columns=name separator=" | "
    ```

    ```text
    survey_1 | survey_2 | survey_3 | survey_4
    ```

    ```sh
    t.vect.list input=survey format=csv columns=name,points,lines
    ```

    ```text
    "name","points","lines"
    "survey_1",3,0
    "survey_2",0,2
    "survey_3",0,0
    "survey_4",0,0
    ```

    ```sh
    t.vect.list -u input=survey format=csv columns=name,points,lines
    ```

    ```text
    "survey_1",3,0
    "survey_2",0,2
    "survey_3",0,0
    "survey_4",0,0
    ```

    ```sh
    t.vect.list input=survey columns=name,points,lines separator=";"
    ```

    ```text
    name;points;lines
    survey_1;3;0
    survey_2;0;2
    survey_3;0;0
    survey_4;0;0
    ```

    ```sh
    t.vect.list input=survey columns=name,points format=json
    echo
    ```

    ```text
    {"data": [{"name": "survey_1", "points": 3}, {"name": "survey_2", "points": 0}, {"name": "survey_3", "points": 0}, {"name": "survey_4", "points": 0}], "metadata": {"column_names": ["name", "points"]}}
    ```

    ```sh
    t.vect.list input=survey columns=name,points output=points.txt
    cat points.txt
    ```

    ```text
    name|points
    survey_1|3
    survey_2|0
    survey_3|0
    survey_4|0
    ```

    ```sh
    t.vect.list input=survey columns=name output=-
    cat ./-
    ```

    ```text
    name
    survey_1
    survey_2
    survey_3
    survey_4
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    print(tools.t_vect_list(input="survey", format="line").text)
    ```

    ```text
    survey_1@PERMANENT,survey_2@PERMANENT,survey_3@PERMANENT,survey_4@PERMANENT
    ```

    ```python
    print(tools.t_vect_list(input="survey", method="comma").text)
    ```

    ```text
    survey_1@PERMANENT,survey_2@PERMANENT,survey_3@PERMANENT,survey_4@PERMANENT
    ```

    ```python
    result = tools.t_vect_list(
        input="survey", format="line", columns="name", separator=" | "
    )
    print(result.text)
    ```

    ```text
    survey_1 | survey_2 | survey_3 | survey_4
    ```

    ```python
    result = tools.t_vect_list(input="survey", format="csv", columns="name,points,lines")
    print(result.text)
    ```

    ```text
    "name","points","lines"
    "survey_1",3,0
    "survey_2",0,2
    "survey_3",0,0
    "survey_4",0,0
    ```

    ```python
    result = tools.t_vect_list(
        input="survey", format="csv", columns="name,points,lines", flags="u"
    )
    print(result.text)
    ```

    ```text
    "survey_1",3,0
    "survey_2",0,2
    "survey_3",0,0
    "survey_4",0,0
    ```

    ```python
    result = tools.t_vect_list(input="survey", columns="name,points,lines", separator=";")
    print(result.text)
    ```

    ```text
    name;points;lines
    survey_1;3;0
    survey_2;0;2
    survey_3;0;0
    survey_4;0;0
    ```

    ```python
    result = tools.t_vect_list(input="survey", columns="name,points", format="json")
    for item in result.json["data"]:
        print(item["name"], item["points"])
    ```

    ```text
    survey_1 3
    survey_2 0
    survey_3 0
    survey_4 0
    ```

    ```python
    tools.t_vect_list(input="survey", columns="name,points", output="points.txt")
    print(Path("points.txt").read_text(), end="")
    ```

    ```text
    name|points
    survey_1|3
    survey_2|0
    survey_3|0
    survey_4|0
    ```

    ```python
    tools.t_vect_list(input="survey", columns="name", output="-")
    print(Path("-").read_text(), end="")
    ```

    ```text
    name
    survey_1
    survey_2
    survey_3
    survey_4
    ```

### Maps with layers

The map `gauge` has three points, which have a category in each of the layers 1,
2 and 3. A layer of a map is registered by its own, as `gauge:3`, and is a map
of the dataset with its own time. The dataset `layered` holds the layer 3 of
`gauge` on 1 March, its layer 1 on 2 March, and the map `plain_1`, which has no
layer, on 3 March; the order in time differs from the order of the layers.

The first block lists the maps: the column `layer` holds the layer or `None`.
The second block lists the ids, which carry the layer after a colon, with the
names and layers. The third block selects one layer with **where**, and the
fourth block sorts by layer. The fifth block prints JSON, which holds the layer
as text, and `null` for the map without one.

=== "Command line"

    ```sh
    v.in.ascii input=- output=gauge_import format=point separator=comma \
        columns="x double precision, y double precision, cat integer" \
        x=1 y=2 z=0 cat=3 <<EOF
    1,1,1
    3,4,2
    2,2,3
    EOF
    v.category input=gauge_import output=gauge option=transfer layer=1,2,3
    v.in.ascii -n input=- output=plain_1 format=point separator=comma <<EOF
    1,1
    EOF
    t.create type=stvds output=layered title="Layers" \
        description="Layers of one map in the order of time"
    t.register type=vector input=layered maps=gauge:3 \
        start=2026-03-01 end=2026-03-02
    t.register type=vector input=layered maps=gauge:1 \
        start=2026-03-02 end=2026-03-03
    t.register type=vector input=layered maps=plain_1 \
        start=2026-03-03 end=2026-03-04
    t.vect.list input=layered
    ```

    ```text
    name|layer|mapset|start_time|end_time
    gauge|3|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    gauge|1|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    plain_1|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```sh
    t.vect.list input=layered columns=id,name,layer
    ```

    ```text
    id|name|layer
    gauge:3@PERMANENT|gauge|3
    gauge:1@PERMANENT|gauge|1
    plain_1@PERMANENT|plain_1|None
    ```

    ```sh
    t.vect.list input=layered columns=id,layer where="layer = 3"
    ```

    ```text
    id|layer
    gauge:3@PERMANENT|3
    ```

    ```sh
    t.vect.list input=layered columns=name,layer order=layer
    ```

    ```text
    name|layer
    plain_1|None
    gauge|1
    gauge|3
    ```

    ```sh
    t.vect.list input=layered columns=name,layer format=json
    echo
    ```

    ```text
    {"data": [{"name": "gauge", "layer": "3"}, {"name": "gauge", "layer": "1"}, {"name": "plain_1", "layer": null}], "metadata": {"column_names": ["name", "layer"]}}
    ```

=== "Python (grass.tools)"

    ```python
    tools.v_in_ascii(
        input=StringIO("1,1,1\n3,4,2\n2,2,3\n"),
        output="gauge_import",
        format="point",
        separator="comma",
        columns="x double precision, y double precision, cat integer",
        x=1,
        y=2,
        z=0,
        cat=3,
    )
    tools.v_category(input="gauge_import", output="gauge", option="transfer", layer="1,2,3")
    tools.v_in_ascii(
        input=StringIO("1,1\n"),
        output="plain_1",
        format="point",
        separator="comma",
        flags="n",
    )
    tools.t_create(
        type="stvds",
        output="layered",
        title="Layers",
        description="Layers of one map in the order of time",
    )
    for map_id, start, end in (
        ("gauge:3", "2026-03-01", "2026-03-02"),
        ("gauge:1", "2026-03-02", "2026-03-03"),
        ("plain_1", "2026-03-03", "2026-03-04"),
    ):
        tools.t_register(type="vector", input="layered", maps=map_id, start=start, end=end)
    print(tools.t_vect_list(input="layered").text)
    ```

    ```text
    name|layer|mapset|start_time|end_time
    gauge|3|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    gauge|1|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    plain_1|None|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    ```

    ```python
    result = tools.t_vect_list(input="layered", columns="id,name,layer")
    print(result.text)
    ```

    ```text
    id|name|layer
    gauge:3@PERMANENT|gauge|3
    gauge:1@PERMANENT|gauge|1
    plain_1@PERMANENT|plain_1|None
    ```

    ```python
    result = tools.t_vect_list(input="layered", columns="id,layer", where="layer = 3")
    print(result.text)
    ```

    ```text
    id|layer
    gauge:3@PERMANENT|3
    ```

    ```python
    result = tools.t_vect_list(input="layered", columns="name,layer", order="layer")
    print(result.text)
    ```

    ```text
    name|layer
    plain_1|None
    gauge|1
    gauge|3
    ```

    ```python
    result = tools.t_vect_list(input="layered", columns="name,layer", format="json")
    print(result.text)
    ```

    ```text
    {"data": [{"name": "gauge", "layer": "3"}, {"name": "gauge", "layer": "1"}, {"name": "plain_1", "layer": null}], "metadata": {"column_names": ["name", "layer"]}}
    ```

### Intervals, distances and gaps

The dataset `fires` has two daily maps, registered with a start and an end:
`fire_1` for 1 June 2026 and `fire_3` for 3 June, so 2 June is a gap. The
method `delta` prints the length of each map and its distance from the first
map in days; it skips the gap. The method `deltagaps` adds a line for the gap
with `None` as `id`, `name`, `layer` and `mapset`, and its length. The CSV form
of this table shows `None` as an empty text. The fourth block selects the map
`fire_3` with **where**: the distance counts from the first selected map, so it
is 0.

The dataset `model` has relative time: three model steps of 6 hours. Its times,
lengths and distances are numbers of hours, printed without the unit.

The dataset `sightings` has two maps that are time instants, registered with a
start only. The length of an instant is `None`, and so is its end time.

The dataset `coast` has relative time with the unit years and three time
instants: 1997, 1998 and 2003. The method `deltagaps` lists a gap line between
two instants, from the first year to the next one, with the distance in years
as its length: 1, then 5.

=== "Command line"

    ```sh
    for name in fire_1 fire_3 step_1 step_2 step_3 sighting_1 sighting_2 \
            coast_1997 coast_1998 coast_2003; do
        v.in.ascii -n input=- output=$name format=point separator=comma <<EOF
    1,1
    EOF
    done
    t.create type=stvds output=fires title="Fires" \
        description="Daily fires with a gap"
    t.register type=vector input=fires maps=fire_1 \
        start=2026-06-01 end=2026-06-02
    t.register type=vector input=fires maps=fire_3 \
        start=2026-06-03 end=2026-06-04
    t.vect.list input=fires method=delta
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    fire_1@PERMANENT|fire_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    fire_3@PERMANENT|fire_3|None|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.vect.list input=fires method=deltagaps
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    fire_1@PERMANENT|fire_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    fire_3@PERMANENT|fire_3|None|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```sh
    t.vect.list input=fires method=deltagaps format=csv columns=id,interval_length
    ```

    ```text
    "id","interval_length"
    "fire_1@PERMANENT",1.0
    "",1.0
    "fire_3@PERMANENT",1.0
    ```

    ```sh
    t.vect.list input=fires method=delta where="name = 'fire_3'" columns=name,distance_from_begin
    ```

    ```text
    name|distance_from_begin
    fire_3|0.0
    ```

    ```sh
    t.create type=stvds output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i type=vector input=model maps=step_1,step_2,step_3 \
        start=0 increment=6 unit=hours
    t.vect.list input=model method=delta
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|None|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|None|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|None|PERMANENT|12|18|6|12
    ```

    ```sh
    t.create type=stvds output=sightings title="Sightings" \
        description="Two sightings as time instants"
    t.register type=vector input=sightings maps=sighting_1 start=2026-06-01
    t.register type=vector input=sightings maps=sighting_2 start=2026-06-03
    t.vect.list input=sightings method=delta
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    sighting_1@PERMANENT|sighting_1|None|PERMANENT|2026-06-01 00:00:00|None|None|0.0
    sighting_2@PERMANENT|sighting_2|None|PERMANENT|2026-06-03 00:00:00|None|None|2.0
    ```

    ```sh
    t.create type=stvds output=coast temporaltype=relative title="Coast" \
        description="Coast lines at three instants"
    for year in 1997 1998 2003; do
        t.register type=vector input=coast maps=coast_$year \
            start=$year unit=years
    done
    t.vect.list input=coast method=deltagaps
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    coast_1997@PERMANENT|coast_1997|None|PERMANENT|1997|None|None|0
    None|None|None|None|1997|1998|1|0
    coast_1998@PERMANENT|coast_1998|None|PERMANENT|1998|None|None|1
    None|None|None|None|1998|2003|5|1
    coast_2003@PERMANENT|coast_2003|None|PERMANENT|2003|None|None|6
    ```

=== "Python (grass.tools)"

    ```python
    for name in (
        "fire_1",
        "fire_3",
        "step_1",
        "step_2",
        "step_3",
        "sighting_1",
        "sighting_2",
        "coast_1997",
        "coast_1998",
        "coast_2003",
    ):
        tools.v_in_ascii(
            input=StringIO("1,1\n"),
            output=name,
            format="point",
            separator="comma",
            flags="n",
        )
    tools.t_create(
        type="stvds",
        output="fires",
        title="Fires",
        description="Daily fires with a gap",
    )
    tools.t_register(
        type="vector", input="fires", maps="fire_1", start="2026-06-01", end="2026-06-02"
    )
    tools.t_register(
        type="vector", input="fires", maps="fire_3", start="2026-06-03", end="2026-06-04"
    )
    print(tools.t_vect_list(input="fires", method="delta").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    fire_1@PERMANENT|fire_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    fire_3@PERMANENT|fire_3|None|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    print(tools.t_vect_list(input="fires", method="deltagaps").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    fire_1@PERMANENT|fire_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    None|None|None|None|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    fire_3@PERMANENT|fire_3|None|PERMANENT|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    ```

    ```python
    result = tools.t_vect_list(
        input="fires", method="deltagaps", format="csv", columns="id,interval_length"
    )
    print(result.text)
    ```

    ```text
    "id","interval_length"
    "fire_1@PERMANENT",1.0
    "",1.0
    "fire_3@PERMANENT",1.0
    ```

    ```python
    result = tools.t_vect_list(
        input="fires",
        method="delta",
        where="name = 'fire_3'",
        columns="name,distance_from_begin",
    )
    print(result.text)
    ```

    ```text
    name|distance_from_begin
    fire_3|0.0
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        type="vector",
        input="model",
        maps="step_1,step_2,step_3",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_vect_list(input="model", method="delta").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|None|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|None|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|None|PERMANENT|12|18|6|12
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="sightings",
        title="Sightings",
        description="Two sightings as time instants",
    )
    tools.t_register(
        type="vector", input="sightings", maps="sighting_1", start="2026-06-01"
    )
    tools.t_register(
        type="vector", input="sightings", maps="sighting_2", start="2026-06-03"
    )
    print(tools.t_vect_list(input="sightings", method="delta").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    sighting_1@PERMANENT|sighting_1|None|PERMANENT|2026-06-01 00:00:00|None|None|0.0
    sighting_2@PERMANENT|sighting_2|None|PERMANENT|2026-06-03 00:00:00|None|None|2.0
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="coast",
        temporaltype="relative",
        title="Coast",
        description="Coast lines at three instants",
    )
    for year in (1997, 1998, 2003):
        tools.t_register(
            type="vector", input="coast", maps=f"coast_{year}", start=year, unit="years"
        )
    print(tools.t_vect_list(input="coast", method="deltagaps").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    coast_1997@PERMANENT|coast_1997|None|PERMANENT|1997|None|None|0
    None|None|None|None|1997|1998|1|0
    coast_1998@PERMANENT|coast_1998|None|PERMANENT|1998|None|None|1
    None|None|None|None|1998|2003|5|1
    coast_2003@PERMANENT|coast_2003|None|PERMANENT|2003|None|None|6
    ```

### Sample the maps by the granularity

The dataset `wells` has two maps: `well_1` from 1 to 3 June 2026, which is two
days long, and `well_2` for 4 June, which is one day long. 3 June is a gap. The
first block shows the granularity of the dataset, 1 day, which is the granule
of the method `gran`. The second block prints one line per day: `well_1` is
listed for both of its days, the day of the gap has `None` as `id`, `name`,
`layer` and `mapset`, and `well_2` follows. The third block samples the
relative dataset `model` of the previous example: its granularity is 6 hours.
The dataset `nest` has the map `nest_a` from 1 to 3 July and the map `nest_b`
from 2 to 3 July. Its granularity is 1 day. The first granule is covered by
`nest_a` only, and the second one by both maps: `nest_b` is equal to it and
`nest_a` contains it, so the line names `nest_b`, although `nest_a` starts
first.

The last block creates the dataset `lone` with a single map that is a time
instant. Such a dataset has no granularity, so `gran` stops with an error. The
shell block prints the message instead of failing.

=== "Command line"

    ```sh
    for name in well_1 well_2 lone_1 nest_a nest_b; do
        v.in.ascii -n input=- output=$name format=point separator=comma <<EOF
    1,1
    EOF
    done
    t.create type=stvds output=wells title="Wells" \
        description="One map of two days and one of one day"
    t.register type=vector input=wells maps=well_1 \
        start=2026-06-01 end=2026-06-03
    t.register type=vector input=wells maps=well_2 \
        start=2026-06-04 end=2026-06-05
    t.info -g type=stvds input=wells | grep granularity
    ```

    ```text
    granularity='1 day'
    ```

    ```sh
    t.vect.list input=wells method=gran
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    well_1@PERMANENT|well_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    well_1@PERMANENT|well_1|None|PERMANENT|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    None|None|None|None|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    well_2@PERMANENT|well_2|None|PERMANENT|2026-06-04 00:00:00|2026-06-05 00:00:00|1.0|3.0
    ```

    ```sh
    t.vect.list input=model method=gran
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|None|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|None|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|None|PERMANENT|12|18|6|12
    ```

    ```sh
    t.create type=stvds output=nest title="Nest" \
        description="A map that contains another one"
    t.register type=vector input=nest maps=nest_a \
        start=2026-07-01 end=2026-07-03
    t.register type=vector input=nest maps=nest_b \
        start=2026-07-02 end=2026-07-03
    t.vect.list input=nest method=gran columns=name,start_time
    ```

    ```text
    name|start_time
    nest_a|2026-07-01 00:00:00
    nest_b|2026-07-02 00:00:00
    ```

    ```sh
    t.create type=stvds output=lone title="Lone" \
        description="A single time instant"
    t.register type=vector input=lone maps=lone_1 start=2026-06-01
    if ! t.vect.list input=lone method=gran 2>&1; then
        echo "t.vect.list failed"
    fi
    ```

    ```text
    ERROR: Wrong granularity: "None"
    t.vect.list failed
    ```

=== "Python (grass.tools)"

    ```python
    for name in ("well_1", "well_2", "lone_1", "nest_a", "nest_b"):
        tools.v_in_ascii(
            input=StringIO("1,1\n"),
            output=name,
            format="point",
            separator="comma",
            flags="n",
        )
    tools.t_create(
        type="stvds",
        output="wells",
        title="Wells",
        description="One map of two days and one of one day",
    )
    tools.t_register(
        type="vector", input="wells", maps="well_1", start="2026-06-01", end="2026-06-03"
    )
    tools.t_register(
        type="vector", input="wells", maps="well_2", start="2026-06-04", end="2026-06-05"
    )
    info = tools.t_info(type="stvds", input="wells", flags="g").keyval
    print(f"granularity={info['granularity']}")
    ```

    ```text
    granularity='1 day'
    ```

    ```python
    print(tools.t_vect_list(input="wells", method="gran").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    well_1@PERMANENT|well_1|None|PERMANENT|2026-06-01 00:00:00|2026-06-02 00:00:00|1.0|0.0
    well_1@PERMANENT|well_1|None|PERMANENT|2026-06-02 00:00:00|2026-06-03 00:00:00|1.0|1.0
    None|None|None|None|2026-06-03 00:00:00|2026-06-04 00:00:00|1.0|2.0
    well_2@PERMANENT|well_2|None|PERMANENT|2026-06-04 00:00:00|2026-06-05 00:00:00|1.0|3.0
    ```

    ```python
    print(tools.t_vect_list(input="model", method="gran").text)
    ```

    ```text
    id|name|layer|mapset|start_time|end_time|interval_length|distance_from_begin
    step_1@PERMANENT|step_1|None|PERMANENT|0|6|6|0
    step_2@PERMANENT|step_2|None|PERMANENT|6|12|6|6
    step_3@PERMANENT|step_3|None|PERMANENT|12|18|6|12
    ```

    ```python
    tools.t_create(
        type="stvds",
        output="nest",
        title="Nest",
        description="A map that contains another one",
    )
    tools.t_register(
        type="vector", input="nest", maps="nest_a", start="2026-07-01", end="2026-07-03"
    )
    tools.t_register(
        type="vector", input="nest", maps="nest_b", start="2026-07-02", end="2026-07-03"
    )
    result = tools.t_vect_list(input="nest", method="gran", columns="name,start_time")
    print(result.text)
    ```

    ```text
    name|start_time
    nest_a|2026-07-01 00:00:00
    nest_b|2026-07-02 00:00:00
    ```

    ```python
    from grass.tools import ToolError

    tools.t_create(
        type="stvds",
        output="lone",
        title="Lone",
        description="A single time instant",
    )
    tools.t_register(type="vector", input="lone", maps="lone_1", start="2026-06-01")
    try:
        tools.t_vect_list(input="lone", method="gran")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.list failed")
    ```

    ```text
    ERROR: Wrong granularity: "None"
    t.vect.list failed
    ```

### Use a dataset of another mapset

*t.vect.list* reads a dataset of another mapset. The example creates the mapset
`other` and switches to it; the dataset `survey` stays in the mapset
`PERMANENT` and is named with its mapset. In the second block, *g.mapsets*
shows that `PERMANENT` is in the search path of the new mapset, so the name
`survey` without a mapset finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=other
    t.vect.list input=survey@PERMANENT columns=id,start_time
    ```

    ```text
    id|start_time
    survey_1@PERMANENT|2026-03-01 00:00:00
    survey_2@PERMANENT|2026-03-02 00:00:00
    survey_3@PERMANENT|2026-03-03 00:00:00
    survey_4@PERMANENT|2026-03-04 00:00:00
    ```

    ```sh
    g.mapsets -p
    t.vect.list input=survey columns=id,start_time
    ```

    ```text
    other PERMANENT
    id|start_time
    survey_1@PERMANENT|2026-03-01 00:00:00
    survey_2@PERMANENT|2026-03-02 00:00:00
    survey_3@PERMANENT|2026-03-03 00:00:00
    survey_4@PERMANENT|2026-03-04 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="other", flags="c")
    result = tools.t_vect_list(input="survey@PERMANENT", columns="id,start_time")
    print(result.text)
    ```

    ```text
    id|start_time
    survey_1@PERMANENT|2026-03-01 00:00:00
    survey_2@PERMANENT|2026-03-02 00:00:00
    survey_3@PERMANENT|2026-03-03 00:00:00
    survey_4@PERMANENT|2026-03-04 00:00:00
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    print(tools.t_vect_list(input="survey", columns="id,start_time").text)
    ```

    ```text
    other PERMANENT
    id|start_time
    survey_1@PERMANENT|2026-03-01 00:00:00
    survey_2@PERMANENT|2026-03-02 00:00:00
    survey_3@PERMANENT|2026-03-03 00:00:00
    survey_4@PERMANENT|2026-03-04 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.list](g.list.md), [g.mapsets](g.mapsets.md), [t.create](t.create.md),
[t.info](t.info.md), [t.list](t.list.md), [t.rast.list](t.rast.list.md),
[t.rast3d.list](t.rast3d.list.md), [t.register](t.register.md),
[t.vect.extract](t.vect.extract.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert
