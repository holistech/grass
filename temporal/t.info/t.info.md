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
`temperature_monthly@t_info`), `Name` and `Mapset`. `Creator` is the user who
created the dataset, `Temporal type` is `absolute` or `relative`, `Creation
time` and `Modification time` are the times at which the dataset was created
and last changed in the database, and `Semantic type` is the label given
with **semantictype** of *t.create*: `mean` unless set otherwise.

The next section is named *Absolute time* or *Relative time*, after the
temporal type. `Start time` is the earliest start and `End time` the latest
end of the registered maps; with absolute time they are dates and times, with
relative time numbers, and the line `Relative time unit` names the unit of
those numbers. `Granularity` is the step in which the time of the dataset can
be counted: `1 month` for maps that are one month long and follow each other
without gap; with relative time it is a number of the unit, in the example `6`
for maps that are 6 hours long. With maps of different lengths or gaps between
them, it is the greatest common divisor of the lengths and gaps, as in the
dataset `uneven` of the examples. A step of whole months from the first map
counts as a month, also when it is cut to the end of a shorter month: maps
from January 31 to February 28, March 31 and April 30 have the granularity
`1 month`. How months and years count is explained in the
[introduction to temporal data processing](temporalintro.md). The granularity
is stored with the dataset. A dataset that a release before GRASS 8.6 created
may show `1 day` for such a series until its metadata is updated from the
maps, for example by *[t.support](t.support.md)* with **-u**. `Temporal type
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
are broken into several lines, and every line of a command ends in a backslash
except the last line of the command, so a command can be copied into a shell
as it is. **-h** with a map prints the report of the map; only space time
datasets have a history. **-g** has no effect together with **-h**.

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
`type=raster`. The name of a dataset without a mapset is searched in the
current mapset first, then in the search path. A dataset of a mapset outside the
search path is selected as `input=name@mapset`, and without the mapset the error
names the current mapset. The name of a map without a mapset refers to the
current mapset; a map of another mapset that is registered in a dataset of the
current mapset is found with `name@mapset`.

The name is taken as it is: a dot belongs to the name, so a dataset of an
earlier release whose name contains a dot is shown like any other.

Without **input** and without **-d**, the parser stops with "Required
parameter `<input>` not set". **-d** with **-h** and without **input** stops
with "Please specify input=".

With absolute time, `Start time`, `End time` and the other times are printed
as `2026-03-01 00:00:00`. With relative time, `Start time` and `End time` are
numbers without unit; the unit is the line `Relative time unit` of the box and
the key `unit` of the shell form.

The `Semantic label` line of a raster map, and `semantic_label` in the shell
form, give the semantic label of the map, and `None` for a map without one. The
dataset counts and lists the labels of its maps (`Number of semantic labels`,
`Semantic labels`).

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_info`, sets the computational region to North
Carolina with cells of 1 km and generates the space time dataset
`temperature_monthly`: twelve maps of the monthly mean air temperature of
2020 in degrees Celsius, computed from the elevation model `elev_state_500m`,
not measured. The later examples work in this mapset and region. *t.info* only
reads the temporal database, so the datasets that show the special cases (relative
time, mixed time, no maps, semantic labels) hold small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_info -->

<!-- markdownlint-disable MD046 -->

### Report on a space time dataset

The dataset `temperature_monthly` holds the twelve monthly maps of 2020. The
temperature falls by 6.5 degrees per 1000 m of elevation and by 1 degree per
100 km to the north, and follows a yearly cycle with the maximum in July. The
maps are registered as monthly intervals from 1 January 2020. A file lists
their names, so that the command history shows the file instead of the twelve
names.

The report shows the extent in time of the dataset (1 January 2020 to 1
January 2021, the end of the last interval), the granularity `1 month` and the
extent of the region, 839 columns by 335 rows of 1000 m. The smallest of the
minima is -7.0 degrees (January, in the mountains), the largest of the minima
is 13.9 (July), the smallest of the maxima is 7.5 (January) and the largest of
the maxima is 28.4 (July). The command history lists the two commands that
built the dataset.

The Python tab prints `result.stdout` unchanged; `result.text` would remove
the blank at the start of the first line.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_info
    g.region raster=elev_state_500m res=1000 -a
    for month in $(seq 12); do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=temperature_monthly title="Air temperature" \
        description="Monthly mean air temperature 2020 in degrees Celsius"
    g.list type=raster pattern="temperature_monthly_*" mapset=. > maps.txt
    t.register -i input=temperature_monthly file=maps.txt \
        start=2020-01-01 increment="1 month"
    t.info input=temperature_monthly
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly@t_info
     | Name: ...................... temperature_monthly
     | Mapset: .................... t_info
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-01-01 00:00:00
     | End time:................... 2021-01-01 00:00:00
     | Granularity:................ 1 month
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:....................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1000.0
     | North-South resolution max:. 1000.0
     | East-west resolution min:... 1000.0
     | East-west resolution max:... 1000.0
     | Minimum value min:.......... -7.0
     | Minimum value max:.......... 13.9
     | Maximum value min:.......... 7.5
     | Maximum value max:.......... 28.4
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 12
     |
     | Title:
     | Air temperature
     | Description:
     | Monthly mean air temperature 2020 in degrees Celsius
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="temperature_monthly"
     |     title="Air temperature"
     |     description="Monthly mean air temperature 2020 in degrees Celsius"
     | # 2026-11-01 12:00:00 
     | t.register -i input="temperature_monthly"
     |     file="maps.txt" start="2020-01-01" increment="1 month"
     | 
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_info")
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
        description="Monthly mean air temperature 2020 in degrees Celsius",
    )
    Path("maps.txt").write_text(
        "".join(f"temperature_monthly_2020_{month:02d}\n" for month in months)
    )
    tools.t_register(
        input="temperature_monthly",
        file="maps.txt",
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    result = tools.t_info(input="temperature_monthly")
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly@t_info
     | Name: ...................... temperature_monthly
     | Mapset: .................... t_info
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-01-01 00:00:00
     | End time:................... 2021-01-01 00:00:00
     | Granularity:................ 1 month
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:....................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1000.0
     | North-South resolution max:. 1000.0
     | East-west resolution min:... 1000.0
     | East-west resolution max:... 1000.0
     | Minimum value min:.......... -7.0
     | Minimum value max:.......... 13.9
     | Maximum value min:.......... 7.5
     | Maximum value max:.......... 28.4
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 12
     |
     | Title:
     | Air temperature
     | Description:
     | Monthly mean air temperature 2020 in degrees Celsius
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.create output="temperature_monthly"
     |     title="Air temperature"
     |     description="Monthly mean air temperature 2020 in degrees Celsius"
     | # 2026-11-01 12:00:00 
     | t.register -i input="temperature_monthly"
     |     file="maps.txt" start="2020-01-01" increment="1 month"
     | 
     +----------------------------------------------------------------------------+
    ```

### Report on a map

**type** selects a map instead of a dataset. The map `temperature_monthly_2020_07`
covers July 2020, from 1 July to 1 August. The report shows the extent of the
region, the data type `DCELL`, the 839 columns and 335 rows (281065 cells), the
smallest and the largest value of July, 13.9 and 28.4 degrees, and the dataset
the map is registered in, `temperature_monthly`.

=== "Command line"

    ```sh
    t.info type=raster input=temperature_monthly_2020_07
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly_2020_07@t_info
     | Name: ...................... temperature_monthly_2020_07
     | Mapset: .................... t_info
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-07-01 00:00:00
     | End time:................... 2020-08-01 00:00:00
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:....................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... DCELL
     | Number of columns:.......... 839
     | Number of rows:............. 335
     | Number of cells:............ 281065
     | North-South resolution:..... 1000.0
     | East-west resolution:....... 1000.0
     | Minimum value:.............. 13.9
     | Maximum value:.............. 28.4
     | Semantic label:............. None
     | Registered datasets ........ temperature_monthly@t_info
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_info(type="raster", input="temperature_monthly_2020_07")
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ temperature_monthly_2020_07@t_info
     | Name: ...................... temperature_monthly_2020_07
     | Mapset: .................... t_info
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-07-01 00:00:00
     | End time:................... 2020-08-01 00:00:00
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:....................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... DCELL
     | Number of columns:.......... 839
     | Number of rows:............. 335
     | Number of cells:............ 281065
     | North-South resolution:..... 1000.0
     | East-west resolution:....... 1000.0
     | Minimum value:.............. 13.9
     | Maximum value:.............. 28.4
     | Semantic label:............. None
     | Registered datasets ........ temperature_monthly@t_info
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
    t.info -g input=temperature_monthly
    ```

    ```text
    id=temperature_monthly@t_info
    name=temperature_monthly
    mapset=t_info
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    modification_time='2026-11-01 12:00:00'
    semantic_type=mean
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    granularity='1 month'
    map_time=interval
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    top=0.0
    bottom=0.0
    raster_register=raster_map_register_00000000000000000000000000000000
    nsres_min=1000.0
    nsres_max=1000.0
    ewres_min=1000.0
    ewres_max=1000.0
    min_min=-7.0
    min_max=13.9
    max_min=7.5
    max_max=28.4
    aggregation_type=None
    number_of_semantic_labels=0
    semantic_labels=None
    number_of_maps=12
    ```

    ```sh
    t.info -g type=raster input=temperature_monthly_2020_07
    ```

    ```text
    id=temperature_monthly_2020_07@t_info
    name=temperature_monthly_2020_07
    mapset=t_info
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    start_time='2020-07-01 00:00:00'
    end_time='2020-08-01 00:00:00'
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    top=0.0
    bottom=0.0
    datatype=DCELL
    cols=839
    rows=335
    number_of_cells=281065
    nsres=1000.0
    ewres=1000.0
    min=13.9
    max=28.4
    semantic_label=None
    registered_datasets=temperature_monthly@t_info
    ```

=== "Python (grass.tools)"

    ```python
    def print_keys(result, keys=None):
        for key, value in result.keyval.items():
            if keys is None or key in keys:
                print(f"{key}={value}")


    print_keys(tools.t_info(input="temperature_monthly", flags="g"))
    ```

    ```text
    id=temperature_monthly@t_info
    name=temperature_monthly
    mapset=t_info
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    modification_time='2026-11-01 12:00:00'
    semantic_type=mean
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    granularity='1 month'
    map_time=interval
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    top=0.0
    bottom=0.0
    raster_register=raster_map_register_00000000000000000000000000000000
    nsres_min=1000.0
    nsres_max=1000.0
    ewres_min=1000.0
    ewres_max=1000.0
    min_min=-7.0
    min_max=13.9
    max_min=7.5
    max_max=28.4
    aggregation_type=None
    number_of_semantic_labels=0
    semantic_labels=None
    number_of_maps=12
    ```

    ```python
    print_keys(tools.t_info(type="raster", input="temperature_monthly_2020_07", flags="g"))
    ```

    ```text
    id=temperature_monthly_2020_07@t_info
    name=temperature_monthly_2020_07
    mapset=t_info
    creator=user
    temporal_type=absolute
    creation_time='2026-11-01 12:00:00'
    start_time='2020-07-01 00:00:00'
    end_time='2020-08-01 00:00:00'
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    top=0.0
    bottom=0.0
    datatype=DCELL
    cols=839
    rows=335
    number_of_cells=281065
    nsres=1000.0
    ewres=1000.0
    min=13.9
    max=28.4
    semantic_label=None
    registered_datasets=temperature_monthly@t_info
    ```

### Print the history of a dataset

**-h** replaces the report by the title, the description and the commands that
built the dataset. A line with the time of the command precedes each command.
The second command shows that **-h** has no effect on a map:
it prints the report of the map, of which the command selects two lines, the
header and the id.

=== "Command line"

    ```sh
    t.info -h input=temperature_monthly
    ```

    ```text
    # Title:
    # Air temperature
    # Description:
    # Monthly mean air temperature 2020 in degrees Celsius
    # Command history:
    # 2026-11-01 12:00:00
    t.create output="temperature_monthly" \
    title="Air temperature" \
    description="Monthly mean air temperature 2020 in degrees Celsius"
    # 2026-11-01 12:00:00
    t.register -i input="temperature_monthly" \
    file="maps.txt" start="2020-01-01" increment="1 month"
    ```

    ```sh
    t.info -h type=raster input=temperature_monthly_2020_07 | grep -E "Raster Dataset|Id:"
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     | Id: ........................ temperature_monthly_2020_07@t_info
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_info(input="temperature_monthly", flags="h").text)
    ```

    ```text
    # Title:
    # Air temperature
    # Description:
    # Monthly mean air temperature 2020 in degrees Celsius
    # Command history:
    # 2026-11-01 12:00:00
    t.create output="temperature_monthly" \
    title="Air temperature" \
    description="Monthly mean air temperature 2020 in degrees Celsius"
    # 2026-11-01 12:00:00
    t.register -i input="temperature_monthly" \
    file="maps.txt" start="2020-01-01" increment="1 month"
    ```

    ```python
    result = tools.t_info(type="raster", input="temperature_monthly_2020_07", flags="h")
    for line in result.stdout.splitlines():
        if "Raster Dataset" in line or "Id:" in line:
            print(line)
    ```

    ```text
     +-------------------- Raster Dataset ----------------------------------------+
     | Id: ........................ temperature_monthly_2020_07@t_info
    ```

### Datasets with relative time, mixed time and no maps

The dataset `model` has relative time: two model steps of 6 hours, registered
with the unit `hours`. `Start time` and `End time` are the numbers 0 and 12,
the granularity is 6, and the unit has a line of its own (`unit` in the shell
form).

The dataset `mixed` holds the map `early` as an interval of one day and the
map `late` as a time instance four days later. The two maps cover squares of
100 km in different parts of North Carolina and have the resolutions 1000 m and
2000 m. The map time of the dataset is `mixed`, its end is the start of the
time instance, its extent is the bounding box of both maps, and the resolution
lines give the smallest and the largest resolution. The region is set back
afterwards.

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
    g.region n=100000 s=0 e=300000 w=200000 res=1000
    r.mapcalc expression="early = 1"
    g.region n=250000 s=150000 e=500000 w=400000 res=2000
    r.mapcalc expression="late = 2"
    t.create output=mixed title="Mixed" description="An interval and a time instance"
    t.register input=mixed maps=early start=2026-03-01 end=2026-03-02
    t.register input=mixed maps=late start=2026-03-05
    t.info -g input=mixed | grep -E "^(start_time|end_time|map_time|north|south|east|west|nsres_min|nsres_max)="
    g.region raster=elev_state_500m res=1000 -a
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    map_time=mixed
    north=250000.0
    south=0.0
    east=500000.0
    west=200000.0
    nsres_min=1000.0
    nsres_max=2000.0
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
    tools.g_region(n=100000, s=0, e=300000, w=200000, res=1000)
    tools.r_mapcalc(expression="early = 1")
    tools.g_region(n=250000, s=150000, e=500000, w=400000, res=2000)
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
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-05 00:00:00'
    map_time=mixed
    north=250000.0
    south=0.0
    east=500000.0
    west=200000.0
    nsres_min=1000.0
    nsres_max=2000.0
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

**type** names the kind of the dataset. The 3D raster dataset
`temperature_profile` holds twelve maps of the monthly mean air temperature in
three layers of 1000 m, from the sea level to 3000 m; the temperature falls by
6.5 degrees per 1000 m, as in `temperature_monthly`. The report shows the top
and bottom of the region (3000 and 0) and the top-bottom resolution (1000).

The vector dataset `stations_monthly` holds twelve copies of the 136 climate
stations `precip_30ynormals` of the sample dataset, one for each month of
2020, so that the point counts can be followed: the report counts the points
and the primitives over all twelve maps, 12 times 136 is 1632.

The commands that follow select a few lines of the report of a 3D raster map
(839 columns, 335 rows and 3 depths) and of a vector map (136 points), **-g**
with the types `raster_3d` and `vector`. The region keeps the 3D settings of
this example in the examples that follow, which work on 2D maps only.

=== "Command line"

    ```sh
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    for month in $(seq 12); do
        echo "temperature_profile_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * z()" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r3.mapcalc file=-
    t.create type=str3ds output=temperature_profile title="Air temperature" \
        description="Monthly mean air temperature 2020 in degrees Celsius, 0 to 3000 m"
    t.register -i type=raster_3d input=temperature_profile \
        maps=$(g.list type=raster_3d pattern="temperature_profile_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.info -g type=str3ds input=temperature_profile | grep -E "^(top|bottom|tbres_min|tbres_max|number_of_maps)="
    t.info -g type=raster_3d input=temperature_profile_2020_07 | grep -E "^(depths|tbres|cols|rows)="
    ```

    ```text
    top=3000.0
    bottom=0.0
    tbres_min=1000.0
    tbres_max=1000.0
    number_of_maps=12
    cols=839
    rows=335
    depths=3
    tbres=1000.0
    ```

    ```sh
    for month in $(seq -w 12); do
        v.extract input=precip_30ynormals output=stations_monthly_2020_$month
    done
    t.create type=stvds output=stations_monthly title="Climate stations" \
        description="Copies of the climate stations, one for each month of 2020"
    t.register -i type=vector input=stations_monthly \
        maps=$(g.list type=vector pattern="stations_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.info -g type=stvds input=stations_monthly | grep -E "^(points|lines|primitives|number_of_maps)="
    t.info -g type=vector input=stations_monthly_2020_07 | grep -E "^(is_3d|points|primitives)="
    ```

    ```text
    points=1632
    lines=0
    primitives=1632
    number_of_maps=12
    is_3d=0
    points=136
    primitives=136
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
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
        description="Monthly mean air temperature 2020 in degrees Celsius, 0 to 3000 m",
    )
    tools.t_register(
        type="raster_3d",
        input="temperature_profile",
        maps=",".join(f"temperature_profile_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    print_keys(
        tools.t_info(type="str3ds", input="temperature_profile", flags="g"),
        {"top", "bottom", "tbres_min", "tbres_max", "number_of_maps"},
    )
    print_keys(
        tools.t_info(type="raster_3d", input="temperature_profile_2020_07", flags="g"),
        {"depths", "tbres", "cols", "rows"},
    )
    ```

    ```text
    top=3000.0
    bottom=0.0
    tbres_min=1000.0
    tbres_max=1000.0
    number_of_maps=12
    cols=839
    rows=335
    depths=3
    tbres=1000.0
    ```

    ```python
    for month in months:
        tools.v_extract(
            input="precip_30ynormals", output=f"stations_monthly_2020_{month:02d}"
        )
    tools.t_create(
        type="stvds",
        output="stations_monthly",
        title="Climate stations",
        description="Copies of the climate stations, one for each month of 2020",
    )
    tools.t_register(
        type="vector",
        input="stations_monthly",
        maps=",".join(f"stations_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    print_keys(
        tools.t_info(type="stvds", input="stations_monthly", flags="g"),
        {"points", "lines", "primitives", "number_of_maps"},
    )
    print_keys(
        tools.t_info(type="vector", input="stations_monthly_2020_07", flags="g"),
        {"is_3d", "points", "primitives"},
    )
    ```

    ```text
    points=1632
    lines=0
    primitives=1632
    number_of_maps=12
    is_3d=0
    points=136
    primitives=136
    ```

### Semantic labels

The dataset `sentinel` holds the red band (semantic label `S2_B4`) and the near
infrared band (`S2_B8`) of two scenes, registered as time instances. The
reflectances are constants over the region. The
report of the dataset counts the two labels and names them. The second block
shows the map `nir_1`: it is a time instance, so its end is `None`, and
its semantic label is `S2_B8`, which *t.rast.list* gives as well.

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
    semantic_label=S2_B8
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
    semantic_label=S2_B8
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
     | Temporal database string:... /home/user/grassdata/nc_spm_08_grass7/t_info/tgis/sqlite.db
     | tgis_version .......... 2
     | tgis_db_version .......... 3
    ```

    ```sh
    t.info -dg | grep -v -E "^(sql_template_path|creation_time)="
    ```

    ```text
    dbmi_python_interface='sqlite3'
    dbmi_string='/home/user/grassdata/nc_spm_08_grass7/t_info/tgis/sqlite.db'
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
     | Temporal database string:... /home/user/grassdata/nc_spm_08_grass7/t_info/tgis/sqlite.db
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
    dbmi_string='/home/user/grassdata/nc_spm_08_grass7/t_info/tgis/sqlite.db'
    tgis_version='2'
    tgis_db_version='3'
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[r.info](r.info.md), [r3.info](r3.info.md),
[t.create](t.create.md), [t.list](t.list.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[v.info](v.info.md),
[changes in GRASS 8.6](temporalchanges.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
