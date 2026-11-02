## DESCRIPTION

*t.info* reports what the temporal database stores about a space time dataset
or about a single map: its identifier and creator, its time, its spatial extent
and metadata that depend on the type of the dataset. The report is made for
reading, or, with the flag **-g**, in shell script style with one `key=value`
pair per line. *t.info* only reads; it does not change the database. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Datasets are created with *[t.create](t.create.md)*, maps are
registered in them with *[t.register](t.register.md)*, and
*[t.list](t.list.md)* and *[t.rast.list](t.rast.list.md)* list datasets and
their maps.

*t.info* reports the values stored in the temporal database, it does not read
the maps. For all values of a map, such as its category table or its history,
use *[r.info](r.info.md)*, *[r3.info](r3.info.md)* or *[v.info](v.info.md)*.

The option **input** names the dataset or the map. A name without a mapset
refers to the current mapset; `name@mapset` selects another one. **input** is
required, except together with **-d**.

The option **type** says what **input** is: a space time dataset of type
`strds` (raster maps, the default), `str3ds` (3D raster maps) or `stvds`
(vector maps), or a single map of type `raster`, `raster_3d` or `vector`.

The flag **-g** prints the report in shell script style instead of the framed
box, as described below. The flag **-h** prints the history of a space time
dataset instead of the report. The flag **-d** prints information about the
database back end instead of a dataset. **-g** also changes the form of the
output of **-d**. **-h** takes precedence over both: with **-h**, the output is
the history, whether **-g** or **-d** is given or not.

### The report of a space time dataset

The report is a box of sections. A line shows a label, dots, and a value.

The section *Basic information* starts with the lines `Id` (name and mapset,
`temperature@PERMANENT`), `Name` and `Mapset`. `Creator` is the user who
created the dataset, `Temporal type` is `absolute` or `relative`, `Creation
time` and `Modification time` are the times at which the dataset was created
and last changed in the database, and `Semantic type` is the label given
with **semantictype** of *t.create*: `mean` unless set otherwise.

The next section is named *Absolute time* or *Relative time*, after the
temporal type. `Start time` is the earliest start and `End time` the latest
end of the registered maps; with absolute time they are dates and times, with
relative time numbers, and the line `Relative time unit` names the unit of
those numbers. `Granularity` is the step in which the time of the dataset can
be counted: `1 day` for maps that are one day long and follow each other
without gap; with relative time it is a number of the unit, in the example `6`
for maps that are 6 hours long. With maps of different lengths or gaps between
them, it is the greatest common divisor of the lengths and gaps, as in the
dataset `uneven` of the examples. How months and years count is explained in the
[introduction to temporal data processing](temporalintro.md). `Temporal type
of maps` is `interval` if all maps have a start and an end, `point` if all are
time instances, and `mixed` if both occur.

The section *Spatial extent* gives `North`, `South`, `East`, `West`, `Top` and
`Bottom` of the dataset, the bounding box of its registered maps. Top and
bottom are 0 for datasets of 2D maps.

The section *Metadata information* depends on the type:

- A space time raster dataset (`strds`) shows the `Raster register table`,
  the name of the table of its maps in the temporal database. The lines
  `North-South resolution min` and `max` and `East-west resolution min` and
  `max` give the smallest and the largest resolution among the registered
  maps. `Minimum value min` is the smallest of the minima of the maps and
  `Minimum value max` the largest of them; `Maximum value min` and `Maximum
  value max` are the smallest and the largest of the maxima. `Aggregation
  type` is the aggregation type stored with the dataset, `None` for all
  datasets of the examples. `Number of semantic labels` and `Semantic labels`
  give the number and the names, separated by commas, of the different
  semantic labels of the registered maps, `0` and `None` if there are none.
- A space time 3D raster dataset (`str3ds`) shows the `3D raster register
  table`, `Top-bottom resolution min` and `max` in addition, and the same
  resolution and value lines as `strds`, except the semantic labels.
- A space time vector dataset (`stvds`) shows the `Vector register table` and
  the number of `points`, `lines`, `boundaries`, `centroids`, `faces`,
  `kernels`, `primitives`, `nodes`, `areas`, `islands`, `holes` and `volumes`,
  added up over the registered maps.

All types end the section with `Number of registered maps`, followed by the
`Title`, the `Description` and the `Command history`: the commands that
created the dataset and registered maps in it, each with the time at which it
ran. A dataset without maps shows `None` for the time, the extent, the
granularity, the type of the maps, the values from the maps and the number of
maps.

### The report of a map

The report of a map (`raster`, `raster_3d`, `vector`) has the same sections.
Its basic information has no modification time and no semantic type, its time
has no granularity and no type of the maps, and `End time` is `None` for a
time instance. *Metadata information* shows the values the temporal database
stored when the map was registered:

- a raster map: `Datatype`, `Number of columns`, `Number of rows`, `Number of
  cells`, the resolution, the `Minimum value`, the `Maximum value` and the
  `Semantic label`;
- a 3D raster map: the same without the semantic label, and `Number of depths`
  and `Top-Bottom resolution`;
- a vector map: `Is map 3d` and the numbers of points, lines, boundaries,
  centroids, faces, kernels, primitives, nodes, areas, islands, holes and
  volumes.

The last line, `Registered datasets`, lists the space time datasets the map is
registered in, separated by commas.

### Shell script style

With **-g**, each value of the report is printed as `key=value`, in the order
of the box. Text values are not quoted, except the times, the granularity of a
dataset with absolute time and the start and end of a dataset with relative
time, which are put between single quotes: `start_time='2026-03-01 00:00:00'`.
The keys follow the labels of the box: `id`, `name`, `mapset`, `creator`,
`temporal_type`, `creation_time`, `modification_time`, `semantic_type`,
`start_time`, `end_time`, `unit`, `granularity`, `map_time`, `north`, `south`,
`east`, `west`, `top`, `bottom`, then the register table (`raster_register`,
`raster3d_register` or `vector_register`) and the values of the type, such as
`nsres_min`, `min_min`, `number_of_semantic_labels`, `semantic_labels`,
`points` or, for maps, `datatype`, `cols`, `rows`, `number_of_cells`, `nsres`,
`min`, `max`, `depths` and `registered_datasets`. A dataset ends with
`number_of_maps`. Empty values are printed as `None`; the title, the
description and the history are not part of this form, use **-h** for them.

### The history of a space time dataset

With **-h**, *t.info* prints the title, the description and the command history
of a space time dataset instead of the report. The lines `# Title:`, `#
Description:` and `# Command history:` and the lines with the title and the
description start with `#`. The commands are those that created the dataset and
registered maps in it; before each command, a line starting with `#` gives its
time. The lines of the commands themselves do not start with `#`. Long commands
are broken into several lines, and every line of a command ends in a backslash,
also the last line of a command that is followed by another one. Only the last
line of the whole history has none. **-h** with a map prints the report of the
map; only space time datasets have a history. **-g** has no effect together
with **-h**.

### The database back end

The flag **-d** prints information about the temporal database of the current
mapset and ends; **input** and **type** are ignored. The lines are:

- `DBMI Python interface`, the name of the Python module that talks to the
  database (`sqlite3` for the default back end);
- `Temporal database string`, the connection string; with SQLite the path of
  the database file, which lies in the directory `tgis` of the mapset;
- `SQL template path`, the directory of the SQL templates of the installation;
- `tgis_version` and `tgis_db_version`, the version of the temporal framework
  and of the database layout, and `creation_time`, the time at which the
  database was created.

With **-g**, the same values are printed as `dbmi_python_interface`,
`dbmi_string`, `sql_template_path`, `tgis_version`, `tgis_db_version` and
`creation_time`, each value between single quotes. **-d** together with **-h**
asks for the history of a dataset and needs **input**.

## NOTES

A dataset or a map that is not registered in the temporal database ends the
module with the error "Dataset `<name@mapset>` of type `<type>` not found in
temporal database". The error also appears when **type** does not fit: a map
asked for with the default type `strds`, or a dataset asked for with
`type=raster`. A name without a mapset refers to the current mapset: a dataset
of another mapset is selected as `input=name@mapset`, and without the mapset
the error names the current mapset. A map of another mapset that is registered
in a dataset of the current mapset is found with `name@mapset` as well.

Without **input** and without **-d**, the parser stops with "Required
parameter `<input>` not set". **-d** with **-h** and without **input** stops
with "Please specify input=".

With absolute time, `Start time`, `End time` and the other times are printed
as `2026-03-01 00:00:00`. With relative time, `Start time` and `End time` are
numbers without unit; the unit is the line `Relative time unit` of the box and
the key `unit` of the shell form.

The `Semantic label` line of a map, and `semantic_label` in the shell form,
show `None` even for a map that has a semantic label, as the last but one
example shows. The dataset reports the labels of its maps correctly (`Semantic
labels`). To read the label of a map, use `t.rast.list
columns=name,semantic_label`.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Report on a space time dataset

The dataset `temperature` holds three maps of daily mean air temperature on a
region of two rows and three columns. The helper map `cell_number` numbers the
cells from 1 to 6, so the values can be followed: `temperature_1` holds -2 to
3, `temperature_2` holds 1 to 6 and `temperature_3` holds 4 to 9. The maps are
registered as daily intervals from 1 March 2026.

The report shows the extent in time of the dataset (1 to 4 March, the end of
the last interval), the granularity `1 day`, and the extent of the region. The
smallest of the minima is -2, the largest of the minima is 4, the smallest of
the maxima is 3 and the largest of the maxima is 9. The command history lists
the two commands that built the dataset.

The Python tab prints `result.stdout` unchanged; `result.text` would remove
the blank at the start of the first line.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="cell_number = 3 * (row() - 1) + col()"
    r.mapcalc expression="temperature_1 = cell_number - 3"
    r.mapcalc expression="temperature_2 = cell_number"
    r.mapcalc expression="temperature_3 = cell_number + 3"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature in degrees Celsius"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    t.info input=temperature
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature@PERMANENT
     | Name: ...................... temperature
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-01 00:00:00
     | End time:................... 2026-03-04 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1.0
     | North-South resolution max:. 1.0
     | East-west resolution min:... 1.0
     | East-west resolution max:... 1.0
     | Minimum value min:.......... -2.0
     | Minimum value max:.......... 4.0
     | Maximum value min:.......... 3.0
     | Maximum value max:.......... 9.0
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 3
     |
     | Title:
     | Air temperature
     | Description:
     | Daily mean air temperature in degrees Celsius
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="temperature" title="Air temperature"
     |     description="Daily mean air temperature in degrees Celsius"
     | # 2026-11-01 12:00:00 
     | t.register -i input="temperature"
     |     maps="temperature_1,temperature_2,temperature_3" start="2026-03-01"
     |     increment="1 day"
     | 
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="cell_number = 3 * (row() - 1) + col()")
    tools.r_mapcalc(expression="temperature_1 = cell_number - 3")
    tools.r_mapcalc(expression="temperature_2 = cell_number")
    tools.r_mapcalc(expression="temperature_3 = cell_number + 3")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature in degrees Celsius",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    result = tools.t_info(input="temperature")
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature@PERMANENT
     | Name: ...................... temperature
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-01 00:00:00
     | End time:................... 2026-03-04 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1.0
     | North-South resolution max:. 1.0
     | East-west resolution min:... 1.0
     | East-west resolution max:... 1.0
     | Minimum value min:.......... -2.0
     | Minimum value max:.......... 4.0
     | Maximum value min:.......... 3.0
     | Maximum value max:.......... 9.0
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 3
     |
     | Title:
     | Air temperature
     | Description:
     | Daily mean air temperature in degrees Celsius
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="temperature" title="Air temperature"
     |     description="Daily mean air temperature in degrees Celsius"
     | # 2026-11-01 12:00:00 
     | t.register -i input="temperature"
     |     maps="temperature_1,temperature_2,temperature_3" start="2026-03-01"
     |     increment="1 day"
     | 
     +----------------------------------------------------------------------------+
    ```

### Report on a map

**type** selects a map instead of a dataset. The map `temperature_2` holds the
values 1 to 6 and covers 2 March 2026; the report shows the extent of the
region, the data type `CELL`, the six cells in three columns and two rows, the
smallest and the largest value, and the dataset it is registered in,
`temperature`. Its time is the interval of 2 March 2026.

=== "Command line"

    ```sh
    t.info type=raster input=temperature_2
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_2@PERMANENT
     | Name: ...................... temperature_2
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-02 00:00:00
     | End time:................... 2026-03-03 00:00:00
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 3
     | Number of rows:............. 2
     | Number of cells:............ 6
     | North-South resolution:..... 1.0
     | East-west resolution:....... 1.0
     | Minimum value:.............. 1.0
     | Maximum value:.............. 6.0
     | Semantic label:............. None
     | Registered datasets ........ temperature@PERMANENT
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_info(type="raster", input="temperature_2")
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_2@PERMANENT
     | Name: ...................... temperature_2
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-02 00:00:00
     | End time:................... 2026-03-03 00:00:00
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 3
     | Number of rows:............. 2
     | Number of cells:............ 6
     | North-South resolution:..... 1.0
     | East-west resolution:....... 1.0
     | Minimum value:.............. 1.0
     | Maximum value:.............. 6.0
     | Semantic label:............. None
     | Registered datasets ........ temperature@PERMANENT
     +----------------------------------------------------------------------------+
    ```

### Print the report in shell script style

With **-g**, the same values are printed as `key=value`. The first command
reports the dataset, the second the map. In the Python tab, `.keyval` splits
the lines into a dictionary of keys and values: numbers are converted to
numbers, strings keep their quotes, so printing the pairs gives the lines of
the Command line tab again. The helper `print_keys()` is used in the following
examples as well; with a set of keys, it prints only these.

=== "Command line"

    ```sh
    t.info -g input=temperature
    ```

    ```text
    id=temperature@PERMANENT
    name=temperature
    mapset=PERMANENT
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    modification_time='2026-11-01 12:00:00'
    semantic_type=mean
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    map_time=interval
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    top=0.0
    bottom=0.0
    raster_register=raster_map_register_00000000000000000000000000000000
    nsres_min=1.0
    nsres_max=1.0
    ewres_min=1.0
    ewres_max=1.0
    min_min=-2.0
    min_max=4.0
    max_min=3.0
    max_max=9.0
    aggregation_type=None
    number_of_semantic_labels=0
    semantic_labels=None
    number_of_maps=3
    ```

    ```sh
    t.info -g type=raster input=temperature_2
    ```

    ```text
    id=temperature_2@PERMANENT
    name=temperature_2
    mapset=PERMANENT
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    start_time='2026-03-02 00:00:00'
    end_time='2026-03-03 00:00:00'
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    top=0.0
    bottom=0.0
    datatype=CELL
    cols=3
    rows=2
    number_of_cells=6
    nsres=1.0
    ewres=1.0
    min=1.0
    max=6.0
    semantic_label=None
    registered_datasets=temperature@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    def print_keys(result, keys=None):
        for key, value in result.keyval.items():
            if keys is None or key in keys:
                print(f"{key}={value}")


    print_keys(tools.t_info(input="temperature", flags="g"))
    ```

    ```text
    id=temperature@PERMANENT
    name=temperature
    mapset=PERMANENT
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    modification_time='2026-11-01 12:00:00'
    semantic_type=mean
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    map_time=interval
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    top=0.0
    bottom=0.0
    raster_register=raster_map_register_00000000000000000000000000000000
    nsres_min=1.0
    nsres_max=1.0
    ewres_min=1.0
    ewres_max=1.0
    min_min=-2.0
    min_max=4.0
    max_min=3.0
    max_max=9.0
    aggregation_type=None
    number_of_semantic_labels=0
    semantic_labels=None
    number_of_maps=3
    ```

    ```python
    print_keys(tools.t_info(type="raster", input="temperature_2", flags="g"))
    ```

    ```text
    id=temperature_2@PERMANENT
    name=temperature_2
    mapset=PERMANENT
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    start_time='2026-03-02 00:00:00'
    end_time='2026-03-03 00:00:00'
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    top=0.0
    bottom=0.0
    datatype=CELL
    cols=3
    rows=2
    number_of_cells=6
    nsres=1.0
    ewres=1.0
    min=1.0
    max=6.0
    semantic_label=None
    registered_datasets=temperature@PERMANENT
    ```

### Print the history of a dataset

**-h** replaces the report by the title, the description and the commands that
built the dataset. A line with the time of the command precedes each command.
The second command shows that **-h** has no effect on a map:
it prints the report of the map, of which the command selects two lines, the
header and the id.

=== "Command line"

    ```sh
    t.info -h input=temperature
    ```

    ```text
    # Title:
    # Air temperature
    # Description:
    # Daily mean air temperature in degrees Celsius
    # Command history:
    # 2026-11-01 12:00:00
    t.create output="temperature" title="Air temperature" \
    description="Daily mean air temperature in degrees Celsius" \
    # 2026-11-01 12:00:00
    t.register -i input="temperature" \
    maps="temperature_1,temperature_2,temperature_3" start="2026-03-01" \
    increment="1 day"
    ```

    ```sh
    t.info -h type=raster input=temperature_2 | grep -E "Raster Dataset|Id:"
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     | Id: ........................ temperature_2@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_info(input="temperature", flags="h").text)
    ```

    ```text
    # Title:
    # Air temperature
    # Description:
    # Daily mean air temperature in degrees Celsius
    # Command history:
    # 2026-11-01 12:00:00
    t.create output="temperature" title="Air temperature" \
    description="Daily mean air temperature in degrees Celsius" \
    # 2026-11-01 12:00:00
    t.register -i input="temperature" \
    maps="temperature_1,temperature_2,temperature_3" start="2026-03-01" \
    increment="1 day"
    ```

    ```python
    result = tools.t_info(type="raster", input="temperature_2", flags="h")
    for line in result.stdout.splitlines():
        if "Raster Dataset" in line or "Id:" in line:
            print(line)
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     | Id: ........................ temperature_2@PERMANENT
    ```

### Datasets with relative time, mixed time and no maps

The dataset `model` has relative time: two model steps of 6 hours, registered
with the unit `hours`. `Start time` and `End time` are the numbers 0 and 12,
the granularity is 6, and the unit has a line of its own (`unit` in the shell
form).

The dataset `mixed` holds the map `early` as an interval of one day and the
map `late` as a time instance four days later. The two maps lie in different
parts of the region and have the resolutions 1 and 2. The map time of the
dataset is `mixed`, its end is the start of the time instance, its extent is
the bounding box of both maps, and the resolution lines give the smallest and
the largest resolution. The region is set back afterwards.

The dataset `uneven` has three maps of 4, 6 and 4 days, with a gap of 4 days
before the last one. Its granularity is the greatest common divisor, 2 days.

The dataset `nothing` has no maps. Its time, extent, values and number of maps
are `None`, as the last command shows. The shell form quotes the times and
the granularity, so they are `'None'`.

=== "Command line"

    ```sh
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i input=model maps=step_1,step_2 start=0 increment=6 unit=hours
    t.info -g input=model | grep -E "^(temporal_type|start_time|end_time|unit|granularity)="
    ```

    ```text
    temporal_type=relative
    start_time='0'
    end_time='12'
    unit=hours
    granularity=6
    ```

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    r.mapcalc expression="early = 1"
    g.region n=6 s=4 e=8 w=4 res=2
    r.mapcalc expression="late = 2"
    t.create output=mixed title="Mixed" description="An interval and a time instance"
    t.register input=mixed maps=early start=2026-03-01 end=2026-03-02
    t.register input=mixed maps=late start=2026-03-05
    t.info -g input=mixed | grep -E "^(start_time|end_time|map_time|north|south|east|west|nsres_min|nsres_max)="
    g.region n=2 s=0 e=3 w=0 res=1
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    map_time=mixed
    north=6.0
    south=0.0
    east=8.0
    west=0.0
    nsres_min=1.0
    nsres_max=2.0
    ```

    ```sh
    r.mapcalc expression="long_1 = 1"
    r.mapcalc expression="long_2 = 2"
    r.mapcalc expression="long_3 = 3"
    t.create output=uneven title="Uneven" \
        description="Maps of 4, 6 and 4 days with a gap"
    t.register input=uneven maps=long_1 start=2026-03-01 end=2026-03-05
    t.register input=uneven maps=long_2 start=2026-03-05 end=2026-03-11
    t.register input=uneven maps=long_3 start=2026-03-15 end=2026-03-19
    t.info -g input=uneven | grep "^granularity="
    ```

    ```text
    granularity='2 days'
    ```

    ```sh
    t.create output=nothing title="Nothing" description="A dataset without maps"
    t.info -g input=nothing | grep -E "^(start_time|end_time|granularity|map_time|north|min_min|number_of_maps)="
    ```

    ```text
    start_time='None'
    end_time='None'
    granularity='None'
    map_time=None
    north=None
    min_min=None
    number_of_maps=None
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print_keys(
        tools.t_info(input="model", flags="g"),
        {"temporal_type", "start_time", "end_time", "unit", "granularity"},
    )
    ```

    ```text
    temporal_type=relative
    start_time='0'
    end_time='12'
    unit=hours
    granularity=6
    ```

    ```python
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.r_mapcalc(expression="early = 1")
    tools.g_region(n=6, s=4, e=8, w=4, res=2)
    tools.r_mapcalc(expression="late = 2")
    tools.t_create(
        output="mixed", title="Mixed", description="An interval and a time instance"
    )
    tools.t_register(input="mixed", maps="early", start="2026-03-01", end="2026-03-02")
    tools.t_register(input="mixed", maps="late", start="2026-03-05")
    print_keys(
        tools.t_info(input="mixed", flags="g"),
        {
            "start_time",
            "end_time",
            "map_time",
            "north",
            "south",
            "east",
            "west",
            "nsres_min",
            "nsres_max",
        },
    )
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    map_time=mixed
    north=6.0
    south=0.0
    east=8.0
    west=0.0
    nsres_min=1.0
    nsres_max=2.0
    ```

    ```python
    for number in (1, 2, 3):
        tools.r_mapcalc(expression=f"long_{number} = {number}")
    tools.t_create(
        output="uneven", title="Uneven", description="Maps of 4, 6 and 4 days with a gap"
    )
    for name, start, end in (
        ("long_1", "2026-03-01", "2026-03-05"),
        ("long_2", "2026-03-05", "2026-03-11"),
        ("long_3", "2026-03-15", "2026-03-19"),
    ):
        tools.t_register(input="uneven", maps=name, start=start, end=end)
    print_keys(tools.t_info(input="uneven", flags="g"), {"granularity"})
    ```

    ```text
    granularity='2 days'
    ```

    ```python
    tools.t_create(output="nothing", title="Nothing", description="A dataset without maps")
    print_keys(
        tools.t_info(input="nothing", flags="g"),
        {
            "start_time",
            "end_time",
            "granularity",
            "map_time",
            "north",
            "min_min",
            "number_of_maps",
        },
    )
    ```

    ```text
    start_time='None'
    end_time='None'
    granularity='None'
    map_time=None
    north=None
    min_min=None
    number_of_maps=None
    ```

### Datasets of 3D raster and vector maps

**type** names the kind of the dataset. The 3D raster dataset `soil` holds two
maps of three layers, each layer one unit high; the report shows the top and
bottom of the region and the top-bottom resolution. The vector dataset
`gauges` holds two maps with two and three points; the report counts the points
and the primitives over both maps. The commands that follow select a few lines
of the report of a 3D raster map and of a vector map, **-g** with the types
`raster_3d` and `vector`. The region is set back afterwards.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 t=3 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in three layers"
    t.register -i type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2026-03-01 increment="1 day"
    g.region n=2 s=0 e=3 w=0 res=1
    t.info -g type=str3ds input=soil | grep -E "^(top|bottom|tbres_min|tbres_max|number_of_maps)="
    t.info -g type=raster_3d input=soil_1 | grep -E "^(depths|tbres|cols|rows)="
    ```

    ```text
    top=3.0
    bottom=0.0
    tbres_min=1.0
    tbres_max=1.0
    number_of_maps=2
    cols=2
    rows=2
    depths=3
    tbres=1.0
    ```

    ```sh
    v.in.ascii input=- output=gauges_1 separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    0.5,0.5,3.0
    2.5,1.5,5.0
    EOF
    v.in.ascii input=- output=gauges_2 separator=comma \
        columns="x double precision, y double precision, speed double precision" <<EOF
    1.0,1.0,2.0
    2.0,2.0,4.0
    0.5,1.5,1.0
    EOF
    t.create type=stvds output=gauges title="Gauges" \
        description="Wind speed at gauges"
    t.register -i type=vector input=gauges maps=gauges_1,gauges_2 \
        start=2026-03-01 increment="1 day"
    t.info -g type=stvds input=gauges | grep -E "^(points|lines|primitives|number_of_maps)="
    t.info -g type=vector input=gauges_2 | grep -E "^(is_3d|points|primitives)="
    ```

    ```text
    points=5
    lines=0
    primitives=5
    number_of_maps=2
    is_3d=0
    points=3
    primitives=3
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(n=2, s=0, e=2, w=0, t=3, b=0, res=1, res3=1, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in three layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    print_keys(
        tools.t_info(type="str3ds", input="soil", flags="g"),
        {"top", "bottom", "tbres_min", "tbres_max", "number_of_maps"},
    )
    print_keys(
        tools.t_info(type="raster_3d", input="soil_1", flags="g"),
        {"depths", "tbres", "cols", "rows"},
    )
    ```

    ```text
    top=3.0
    bottom=0.0
    tbres_min=1.0
    tbres_max=1.0
    number_of_maps=2
    cols=2
    rows=2
    depths=3
    tbres=1.0
    ```

    ```python
    columns = "x double precision, y double precision, speed double precision"
    tools.v_in_ascii(
        input=StringIO("0.5,0.5,3.0\n2.5,1.5,5.0\n"),
        output="gauges_1",
        separator="comma",
        columns=columns,
    )
    tools.v_in_ascii(
        input=StringIO("1.0,1.0,2.0\n2.0,2.0,4.0\n0.5,1.5,1.0\n"),
        output="gauges_2",
        separator="comma",
        columns=columns,
    )
    tools.t_create(
        type="stvds", output="gauges", title="Gauges", description="Wind speed at gauges"
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print_keys(
        tools.t_info(type="stvds", input="gauges", flags="g"),
        {"points", "lines", "primitives", "number_of_maps"},
    )
    print_keys(
        tools.t_info(type="vector", input="gauges_2", flags="g"),
        {"is_3d", "points", "primitives"},
    )
    ```

    ```text
    points=5
    lines=0
    primitives=5
    number_of_maps=2
    is_3d=0
    points=3
    primitives=3
    ```

### Semantic labels

The dataset `sentinel` holds the red band (semantic label `S2_B4`) and the near
infrared band (`S2_B8`) of two scenes, registered as time instances. The
report of the dataset counts the two labels and names them. The second block
shows what the notes say: the map `nir_1` is a time instance, so its end is
`None`, and the report gives `None` for its semantic label, although it has
one, while *t.rast.list* gives it.

=== "Command line"

    ```sh
    r.mapcalc expression="red_1 = 0.05"
    r.mapcalc expression="nir_1 = 0.30"
    r.mapcalc expression="red_2 = 0.07"
    r.mapcalc expression="nir_2 = 0.40"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=red_2 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    r.support map=nir_2 semantic_label=S2_B8
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared reflectance of two scenes"
    t.register input=sentinel maps=red_1,nir_1 start="2026-06-01 10:30:00"
    t.register input=sentinel maps=red_2,nir_2 start="2026-06-11 10:30:00"
    t.info -g input=sentinel | grep -E "^(map_time|number_of_semantic_labels|semantic_labels|number_of_maps)="
    ```

    ```text
    map_time=point
    number_of_semantic_labels=2
    semantic_labels=S2_B4,S2_B8
    number_of_maps=4
    ```

    ```sh
    t.info -g type=raster input=nir_1 | grep -E "^(start_time|end_time|semantic_label)="
    t.rast.list input=sentinel columns=name,semantic_label where="name = 'nir_1'"
    ```

    ```text
    start_time='2026-06-01 10:30:00'
    end_time='None'
    semantic_label=None
    name|semantic_label
    nir_1|S2_B8
    ```

=== "Python (grass.tools)"

    ```python
    for name, value, label in (
        ("red_1", 0.05, "S2_B4"),
        ("nir_1", 0.30, "S2_B8"),
        ("red_2", 0.07, "S2_B4"),
        ("nir_2", 0.40, "S2_B8"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value:.2f}")
        tools.r_support(map=name, semantic_label=label)
    tools.t_create(
        output="sentinel",
        title="Reflectance",
        description="Red and near infrared reflectance of two scenes",
    )
    tools.t_register(input="sentinel", maps="red_1,nir_1", start="2026-06-01 10:30:00")
    tools.t_register(input="sentinel", maps="red_2,nir_2", start="2026-06-11 10:30:00")
    print_keys(
        tools.t_info(input="sentinel", flags="g"),
        {"map_time", "number_of_semantic_labels", "semantic_labels", "number_of_maps"},
    )
    ```

    ```text
    map_time=point
    number_of_semantic_labels=2
    semantic_labels=S2_B4,S2_B8
    number_of_maps=4
    ```

    ```python
    print_keys(
        tools.t_info(type="raster", input="nir_1", flags="g"),
        {"start_time", "end_time", "semantic_label"},
    )
    result = tools.t_rast_list(
        input="sentinel", columns="name,semantic_label", where="name = 'nir_1'"
    )
    print(result.text)
    ```

    ```text
    start_time='2026-06-01 10:30:00'
    end_time='None'
    semantic_label=None
    name|semantic_label
    nir_1|S2_B8
    ```

### Information about the database back end

**-d** needs no dataset. The report names the Python interface and the
connection string of the temporal database, which is the file `sqlite.db` in
the directory `tgis` of the mapset. The commands select these and the two
version lines; the SQL template path and the creation time of the database
differ from installation to installation and are left out. With **-g**, the
same values are `key='value'` lines.

=== "Command line"

    ```sh
    t.info -d | grep -E "interface|database string|version"
    ```

    ```text
     | DBMI Python interface:...... sqlite3
     | Temporal database string:... /home/user/grassdata/temporal_examples/PERMANENT/tgis/sqlite.db
     | tgis_version .......... 2
     | tgis_db_version .......... 3
    ```

    ```sh
    t.info -dg | grep -v -E "^(sql_template_path|creation_time)="
    ```

    ```text
    dbmi_python_interface='sqlite3'
    dbmi_string='/home/user/grassdata/temporal_examples/PERMANENT/tgis/sqlite.db'
    tgis_version='2'
    tgis_db_version='3'
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_info(flags="d")
    for line in result.stdout.splitlines():
        if any(word in line for word in ("interface", "database string", "version")):
            print(line)
    ```

    ```text
     | DBMI Python interface:...... sqlite3
     | Temporal database string:... /home/user/grassdata/temporal_examples/PERMANENT/tgis/sqlite.db
     | tgis_version .......... 2
     | tgis_db_version .......... 3
    ```

    ```python
    result = tools.t_info(flags="dg")
    for key, value in result.keyval.items():
        if key not in {"sql_template_path", "creation_time"}:
            print(f"{key}={value}")
    ```

    ```text
    dbmi_python_interface='sqlite3'
    dbmi_string='/home/user/grassdata/temporal_examples/PERMANENT/tgis/sqlite.db'
    tgis_version='2'
    tgis_db_version='3'
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[r.info](r.info.md), [r3.info](r3.info.md),
[t.create](t.create.md), [t.list](t.list.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[v.info](v.info.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
