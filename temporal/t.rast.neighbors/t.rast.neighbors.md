## DESCRIPTION

*t.rast.neighbors* runs *[r.neighbors](r.neighbors.md)* on each raster map of
a space time raster dataset (STRDS), so a neighborhood analysis such as a
smoothing filter, a local maximum or a local quantile is applied to every map
of the dataset. The new raster maps are registered in a new space time raster
dataset. Each new map gets the start and end time of the map it was computed
from. The new dataset takes the temporal type, the semantic type, the title and
the description of the input dataset. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

*t.rast.neighbors* passes the neighborhood options on to *r.neighbors*; what
they mean in detail is described there. The options **input** and **output**
name the input dataset and the new dataset, the option **basename** the names
of the new maps.

### Selection of the maps

- **where** takes an SQL condition on the registered maps, for instance on
  their `start_time` or their `name`; only the maps that satisfy it are
  processed. Without it, all maps are processed.
- **region_relation** selects the maps by the relation of their extent to the
  current computational region: `overlaps` takes the maps that share an area
  with the region (including those that contain the region and those that
  lie within it), `contains` the maps that contain the region and
  `is_contained` the maps that lie within the region. A map equal to the
  region contains it and is contained in it. Without the option, the extent is
  not considered. The selection uses the current region also with the flag
  **-r**.

If **where** and **region_relation** select no map, nothing is computed (see
NOTES).

### Neighborhood

- **size** is the size of the window in cells, an odd number, `3` by default.
  *r.neighbors* refuses an even size.
- **method** is the statistic computed over the cells of the window, `average`
  by default. The methods are `average`, `median`, `mode`, `minimum`,
  `maximum`, `range`, `stddev`, `sum`, `count`, `variance`, `diversity`,
  `interspersion`, `quart1`, `quart3`, `perc90` and `quantile`; see
  *r.neighbors*. Cells without a value (also those outside the region) are
  left out. At the border of the region the window therefore holds fewer
  cells: with **size** `3`, the cell in a corner is computed from four cells.
- **quantile** (0.0 to 1.0) is the quantile that **method** `quantile`
  calculates; this method needs it. For one given quantile `q` and `n` sorted
  values, the result is the linear mix of the two sorted values around the
  position `q * (n - 1)` (counted from 0). Without **method** `quantile` the
  option is ignored. It takes one value, not a list.
- **-c** uses a circular window: the cells in the corners of the square window
  are left out. In a window of 3 by 3 cells, five cells remain.
- **selection** names a raster map. Only the cells where it has a value are
  computed; every other cell of the new map keeps the value of the input map.

### Weights

By default all cells of the window count equally (**weighting_function**
`none`). The other functions give each cell a weight that depends on its
distance `d` from the center of the window, measured in cells:

- `gaussian` weighs by `exp(-d^2 / (2 * f^2)) / (2 * pi * f^2)`, with `f`
  the **weighting_factor**;
- `exponential` weighs by `exp(f * d)`, with `f` the **weighting_factor**; a
  negative factor lets the weights fall with the distance;
- `file` takes the weights from a text file named by **weight**, a matrix of
  **size** rows with **size** numbers each, separated by spaces.

The functions `gaussian` and `exponential` need **weighting_factor**, the
function `file` needs **weight**; without it, *r.neighbors* fails and
*t.rast.neighbors* stops (see NOTES). The weighted `average` divides by the
sum of the weights, so a common factor of the weights cancels; the weighted
`sum` keeps it. A weighted `median` is the value at which the cumulative
weight of the sorted values reaches half of the total weight.

### Names of the new maps

The new maps are named after **basename**, followed by an underscore and a
suffix that the option **suffix** chooses:

- `gran` (the default) takes the start time of the map, cut to the granularity
  of the input dataset: `2020_07_01` in a dataset of days. A dataset of a
  single time instance has no granularity; `gran` then takes the full start
  time, as `time` does.
- `time` takes the full start time: `2020_07_01T00_00_00`.
- `num` numbers the selected maps from 1, with five digits: `00001`.
  `num%03` gives three digits: `001`.

In a dataset with relative time, `gran` and `time` give the number as `num`
does, because a relative time has no calendar date. Maps with the same start
time get the same name with `gran` and `time`; use `num` for them (see NOTES).

### Semantic labels

The option **semantic_labels** sets the semantic label of each new map:

- `input` (the default) copies the label of the input map; a map without a
  label gives a new map without a label.
- `method` appends the name of the **method** to the label of the input map,
  as `S2_B4_maximum`; a map without a label gets the name of the method as its
  label.

The labels tell the new maps apart when several of them have the same time
and extent, as the bands of an image do.

### Result and region

- **-n** registers the new maps that have no value in any cell. By default
  such an empty map is removed and not registered, which happens for a map
  that has no value in the region.
- **-r** ignores the current region and computes each map in its own region;
  the new map has the region of its input map. By default all maps are
  computed in the current region and the new maps have it. The current region
  stays as it is.
- **-e** adds the new maps to an existing output dataset instead of failing
  because it exists: the dataset keeps its maps and also gets the new ones.
  With **-e** and an output dataset that does not exist, a new dataset is
  made. **--overwrite** is needed with **-e** only if one of the new maps
  already exists; it replaces that map and keeps the others of the dataset.
  Without **-e**, **--overwrite** replaces the whole dataset.
- **nprocs** is the number of *r.neighbors* processes that run at the same
  time, `1` by default. The maps are the same for any number.

## NOTES

If **where** and **region_relation** select no map, *t.rast.neighbors* warns
that the space time raster dataset is empty and creates no output dataset. A
syntax error in **where** stops the tool with the error "Unable to get map ids
from register table", followed by "Invalid where condition" and the message of
the database.

An existing **output** dataset is refused with "Space time raster dataset
`<name>` is already in the database" unless **-e** or **--overwrite** is
given. A raster map of the name of a new map that exists in the mapset but
is not registered in the output dataset stops the tool before anything is
written, with "Raster map `<name@mapset>` exists. To overwrite, use the
--overwrite flag."; **--overwrite** replaces it. With **-e**, a new map that
is registered in the dataset already is refused before anything is written
with "Map `<name@mapset>` is already in temporal database"; **--overwrite**
replaces it.

*r.neighbors* can fail, for instance with an even **size**, with
**weighting_function** `gaussian` and no **weighting_factor**, or with
**weighting_function** `file` and no **weight**. *t.rast.neighbors* then stops
with the message "Error running r.neighbors" and creates no dataset. The method
`quantile` without **quantile** stops the tool at the start with "The method
`<quantile>` requires input in the 'quantile' option."; a list of quantiles is
refused by the parser. An unknown **suffix** is refused before anything is
written, for instance with "Invalid suffix `<gram>`, use gran, time, num or
num%NN" for `suffix=gram`.

Two maps with the same start time, such as the bands of a scene, get the
same name with the suffixes `gran` and `time`, and the run fails. The tool
does not check this before it starts, so the outcome depends on the options.
With **nprocs** `1` and without **--overwrite**, *r.neighbors* writes the
first map, fails on the second with "`<name>` exists", and the tool stops; the
first map stays as a raster map that belongs to no dataset, and no dataset is
created. With **nprocs** above 1 or with **--overwrite**, the maps overwrite
each other and the tool usually ends with a database error ("UNIQUE
constraint failed") and an empty output dataset that stays behind; with
**nprocs** above 1 the outcome varies from run to run. Use **suffix** `num`
for such maps, as the fifth example shows.

The input dataset can be in another mapset of the project; the name with the
mapset (`input=model@t_rast_neighbors`) selects it. The new maps and the new dataset
are always created in the current mapset, as the last example shows. Relative
time works as absolute time; the new maps have the time of the input maps.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_neighbors`, sets the computational region
to North Carolina with cells of 1 km, builds the dataset `precipitation_daily`
and then narrows the region to a window of 5 by 5 cells, so that the cells of
the results can be checked by hand; the later examples work in this mapset and
change the region as they need. The last example creates a second mapset. The
examples that show how maps are selected use small constant maps, so that the
results can be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_neighbors -->

<!-- markdownlint-disable MD046 -->

### Smooth the maps of a dataset

The dataset `precipitation_daily` holds 31 maps of the daily precipitation sum
in July 2020, in whole millimetres. They are generated, not measured: the July
normal of the climate stations of `precip_30ynormals` (the column `jul`),
interpolated with *v.surf.idw* and multiplied by an assumed factor of 1.1 for a
wet July, is spread over the days with the weight `max(0, sin(45 * day))`. It
rains on the days 1 to 3, 9 to 11, 17 to 19 and 25 to 27, with the weights
0.71, 1 and 0.71. Each map is an interval of one day.

The computational region is then narrowed to a window of 5 by 5 cells of 1 km
in the mountains of the west, so that the cells can be checked by hand. With
the default **method** `average` and a window of **size** 3, each cell takes
the mean of the cells around it. The second block prints the cells of the map
of 2 July and then the cells of the new map. The cell in the center, in the
third row and the third column, sees all nine cells: the sum of 15, 15, 14,
16, 15, 15, 16, 16 and 16 is 138, and `138 / 9` is 15.33. A cell in a corner
sees only the four cells that lie in the region: the upper left cell is
`(15 + 15 + 16 + 15) / 4`, that is 15.25. The list shows the first three new
maps with the names of their days and their smallest and largest value; on
1 and 3 July, with the weight 0.71, the rain is 10 to 12 mm. **nprocs** `2`
computes two maps at the same time.

The third block shows with *[t.info](t.info.md)* that the new dataset takes the
temporal type, the semantic type, the title and the description of
`precipitation_daily`, that it holds 31 maps and that its extent is the
window.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_neighbors
    g.region raster=elev_state_500m res=1000 -a
    v.surf.idw input=precip_30ynormals column=jul \
        output=precipitation_normal_07 npoints=12 power=2
    r.mapcalc expression="precipitation_monthly_2020_07 = if(isnull(elev_state_500m), null(), round(1.1 * precipitation_normal_07))"
    for day in $(seq 31); do
        echo "precipitation_daily_2020_07_$(printf %02d $day) =" \
            "round(precipitation_monthly_2020_07 * max(0, sin(45 * $day)) / 9.65685)"
    done | r.mapcalc file=-
    t.create output=precipitation_daily title="Precipitation" \
        description="Daily precipitation sum July 2020 in mm"
    t.register -i input=precipitation_daily \
        maps=$(g.list type=raster pattern="precipitation_daily_*" mapset=. separator=comma) \
        start=2020-07-01 increment="1 day"
    g.region w=366000 e=371000 s=270000 n=275000 res=1000
    t.rast.neighbors input=precipitation_daily output=rain_smooth \
        basename=rain_smooth size=3 method=average nprocs=2
    t.rast.list input=rain_smooth columns=name,start_time,end_time,min,max \
        where="start_time < '2020-07-04'"
    ```

    ```text
    name|start_time|end_time|min|max
    rain_smooth_2020_07_01|2020-07-01 00:00:00|2020-07-02 00:00:00|10.0|12.0
    rain_smooth_2020_07_02|2020-07-02 00:00:00|2020-07-03 00:00:00|14.0|16.5
    rain_smooth_2020_07_03|2020-07-03 00:00:00|2020-07-04 00:00:00|10.0|12.0
    ```

    ```sh
    r.out.ascii -h input=precipitation_daily_2020_07_02 output=- precision=2 | sed 's/ *$//'
    r.out.ascii -h input=rain_smooth_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15 15 14 14 14
    16 15 15 14 14
    16 16 15 15 15
    16 16 16 16 15
    17 17 16 16 15
    15.25 15 14.5 14.17 14
    15.5 15.22 14.78 14.44 14.33
    15.83 15.67 15.33 15 14.83
    16.33 16.11 15.89 15.44 15.33
    16.5 16.33 16.17 15.67 15.5
    ```

    ```sh
    t.info input=rain_smooth
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_smooth@t_rast_neighbors
     | Name: ...................... rain_smooth
     | Mapset: .................... t_rast_neighbors
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-07-01 00:00:00
     | End time:................... 2020-08-01 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 275000.0
     | South:...................... 270000.0
     | East:.. .................... 371000.0
     | West:....................... 366000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1000.0
     | North-South resolution max:. 1000.0
     | East-west resolution min:... 1000.0
     | East-west resolution max:... 1000.0
     | Minimum value min:.......... 0.0
     | Minimum value max:.......... 14.0
     | Maximum value min:.......... 0.0
     | Maximum value max:.......... 16.5
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 31
     |
     | Title:
     | Precipitation
     | Description:
     | Daily precipitation sum July 2020 in mm
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.neighbors input="precipitation_daily"
     |     output="rain_smooth" basename="rain_smooth" size="3" method="average"
     |     nprocs="2"
     | 
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_neighbors")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.v_surf_idw(
        input="precip_30ynormals",
        column="jul",
        output="precipitation_normal_07",
        npoints=12,
        power=2,
    )
    tools.r_mapcalc(
        expression="precipitation_monthly_2020_07 = if(isnull(elev_state_500m),"
        " null(), round(1.1 * precipitation_normal_07))"
    )
    days = range(1, 32)
    tools.r_mapcalc(
        expression="\n".join(
            f"precipitation_daily_2020_07_{day:02d} ="
            f" round(precipitation_monthly_2020_07 * max(0, sin(45 * {day})) / 9.65685)"
            for day in days
        )
    )
    tools.t_create(
        output="precipitation_daily",
        title="Precipitation",
        description="Daily precipitation sum July 2020 in mm",
    )
    tools.t_register(
        input="precipitation_daily",
        maps=",".join(f"precipitation_daily_2020_07_{day:02d}" for day in days),
        start="2020-07-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(w=366000, e=371000, s=270000, n=275000, res=1000)
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_smooth",
        basename="rain_smooth",
        size=3,
        method="average",
        nprocs=2,
    )
    columns = "name,start_time,end_time,min,max"
    print(
        tools.t_rast_list(
            input="rain_smooth", columns=columns, where="start_time < '2020-07-04'"
        ).text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    rain_smooth_2020_07_01|2020-07-01 00:00:00|2020-07-02 00:00:00|10.0|12.0
    rain_smooth_2020_07_02|2020-07-02 00:00:00|2020-07-03 00:00:00|14.0|16.5
    rain_smooth_2020_07_03|2020-07-03 00:00:00|2020-07-04 00:00:00|10.0|12.0
    ```

    ```python
    def print_cells(name):
        cells = tools.r_out_ascii(input=name, output="-", precision=2, flags="h")
        for line in cells.stdout.splitlines():
            print(line.rstrip())


    print_cells("precipitation_daily_2020_07_02")
    print_cells("rain_smooth_2020_07_02")
    ```

    ```text
    15 15 14 14 14
    16 15 15 14 14
    16 16 15 15 15
    16 16 16 16 15
    17 17 16 16 15
    15.25 15 14.5 14.17 14
    15.5 15.22 14.78 14.44 14.33
    15.83 15.67 15.33 15 14.83
    16.33 16.11 15.89 15.44 15.33
    16.5 16.33 16.17 15.67 15.5
    ```

    ```python
    print(tools.t_info(input="rain_smooth").stdout, end="")
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_smooth@t_rast_neighbors
     | Name: ...................... rain_smooth
     | Mapset: .................... t_rast_neighbors
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-07-01 00:00:00
     | End time:................... 2020-08-01 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 275000.0
     | South:...................... 270000.0
     | East:.. .................... 371000.0
     | West:....................... 366000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Raster register table:...... raster_map_register_00000000000000000000000000000000
     | North-South resolution min:. 1000.0
     | North-South resolution max:. 1000.0
     | East-west resolution min:... 1000.0
     | East-west resolution max:... 1000.0
     | Minimum value min:.......... 0.0
     | Minimum value max:.......... 14.0
     | Maximum value min:.......... 0.0
     | Maximum value max:.......... 16.5
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 31
     |
     | Title:
     | Precipitation
     | Description:
     | Daily precipitation sum July 2020 in mm
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.neighbors input="precipitation_daily"
     |     output="rain_smooth" basename="rain_smooth" size="3" method="average"
     |     nprocs="2"
     | 
     +----------------------------------------------------------------------------+
    ```

### Choose the statistic and the window

The three blocks use the map of 2 July only (**where**), so each result is a
dataset of one map. The cells of that map are the input of the first example:
the first row is 15 15 14 14 14, the third row 16 16 15 15 15.

1. **method** `maximum` gives the largest value of the window: 16 in the upper
   left corner (of 15, 15, 16 and 15) and 16 in the center.
2. **method** `quantile` with **quantile** `0.25` takes the position
   `0.25 * (n - 1)` in the sorted values. In the center there are nine values
   and the position is 2, the third value, 15. At the right edge of the third
   row there are six values, 14, 14, 15, 15, 15 and 16; the position 1.25 gives
   `14 + 0.25 * (15 - 14) = 14.25`.
3. With **-c**, the window is circular. The center sees the five cells 15 above,
   16 left, 15 itself, 15 right and 16 below, and **method** `sum` gives 77; the
   upper left corner sees the three cells 15, 15 and 16, which give 46.

=== "Command line"

    ```sh
    t.rast.neighbors input=precipitation_daily output=rain_maximum \
        basename=rain_maximum method=maximum \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_maximum_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    16 16 15 15 14
    16 16 16 15 15
    16 16 16 16 16
    17 17 17 16 16
    17 17 17 16 16
    ```

    ```sh
    t.rast.neighbors input=precipitation_daily output=rain_quartile \
        basename=rain_quartile method=quantile quantile=0.25 \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_quartile_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15 15 14 14 14
    15 15 14 14 14
    16 15 15 15 14.25
    16 16 16 15 15
    16 16 16 15.25 15
    ```

    ```sh
    t.rast.neighbors -c input=precipitation_daily output=rain_circular \
        basename=rain_circular method=sum \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_circular_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    46 59 58 56 42
    62 77 73 72 57
    64 78 77 75 59
    65 81 79 78 61
    50 66 65 63 46
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_maximum",
        basename="rain_maximum",
        method="maximum",
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_maximum_2020_07_02")
    ```

    ```text
    16 16 15 15 14
    16 16 16 15 15
    16 16 16 16 16
    17 17 17 16 16
    17 17 17 16 16
    ```

    ```python
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_quartile",
        basename="rain_quartile",
        method="quantile",
        quantile=0.25,
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_quartile_2020_07_02")
    ```

    ```text
    15 15 14 14 14
    15 15 14 14 14
    16 15 15 15 14.25
    16 16 16 15 15
    16 16 16 15.25 15
    ```

    ```python
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_circular",
        basename="rain_circular",
        method="sum",
        where="name = 'precipitation_daily_2020_07_02'",
        flags="c",
    )
    print_cells("rain_circular_2020_07_02")
    ```

    ```text
    46 59 58 56 42
    62 77 73 72 57
    64 78 77 75 59
    65 81 79 78 61
    50 66 65 63 46
    ```

### Weight the cells of the window

The three blocks smooth the map of 2 July with weights. Without weights the
center is 15.33 and the lower left corner 16.5, the mean of 17, 17, 16 and 16.

1. **weighting_function** `gaussian` with **weighting_factor** `1`. The
   weight falls with the distance from the center, so the cell itself counts
   more than in the plain average: the lower left corner is 16.62, nearer to
   its own value 17 than the plain 16.5.
2. **weighting_function** `exponential` with **weighting_factor** `-1`
   weights by `exp(-d)`, which falls faster with the distance than the
   Gaussian weights of the first block: the corner is 16.69.
3. **weighting_function** `file` with **weight** takes the matrix of a text
   file. The matrix 1 1 1 / 1 1 1 / 0 0 0 gives the row below the center the
   weight 0, so the center is the mean of the six cells above and beside it,
   `(15 + 15 + 14 + 16 + 15 + 15) / 6 = 15`.

=== "Command line"

    ```sh
    t.rast.neighbors input=precipitation_daily output=rain_gauss \
        basename=rain_gauss weighting_function=gaussian weighting_factor=1 \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_gauss_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15.24 14.93 14.44 14.1 14
    15.56 15.25 14.75 14.4 14.27
    15.9 15.68 15.32 15 14.83
    16.27 16.12 15.88 15.53 15.27
    16.62 16.45 16.17 15.73 15.38
    ```

    ```sh
    t.rast.neighbors input=precipitation_daily output=rain_expo \
        basename=rain_expo weighting_function=exponential weighting_factor=-1 \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_expo_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15.19 14.95 14.38 14.09 14
    15.62 15.21 14.79 14.35 14.24
    15.91 15.72 15.28 15 14.86
    16.24 16.11 15.89 15.57 15.24
    16.69 16.53 16.14 15.76 15.31
    ```

    ```sh
    cat > weights.txt <<EOF
    1 1 1
    1 1 1
    0 0 0
    EOF
    t.rast.neighbors input=precipitation_daily output=rain_above \
        basename=rain_above weighting_function=file weight=weights.txt \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_above_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15 14.67 14.33 14 14
    15.25 15 14.5 14.17 14
    15.75 15.5 15 14.67 14.5
    16 15.83 15.67 15.33 15.25
    16.5 16.33 16.17 15.67 15.5
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_gauss",
        basename="rain_gauss",
        weighting_function="gaussian",
        weighting_factor=1,
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_gauss_2020_07_02")
    ```

    ```text
    15.24 14.93 14.44 14.1 14
    15.56 15.25 14.75 14.4 14.27
    15.9 15.68 15.32 15 14.83
    16.27 16.12 15.88 15.53 15.27
    16.62 16.45 16.17 15.73 15.38
    ```

    ```python
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_expo",
        basename="rain_expo",
        weighting_function="exponential",
        weighting_factor=-1,
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_expo_2020_07_02")
    ```

    ```text
    15.19 14.95 14.38 14.09 14
    15.62 15.21 14.79 14.35 14.24
    15.91 15.72 15.28 15 14.86
    16.24 16.11 15.89 15.57 15.24
    16.69 16.53 16.14 15.76 15.31
    ```

    ```python
    from pathlib import Path

    Path("weights.txt").write_text("1 1 1\n1 1 1\n0 0 0\n")
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_above",
        basename="rain_above",
        weighting_function="file",
        weight="weights.txt",
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_above_2020_07_02")
    ```

    ```text
    15 14.67 14.33 14 14
    15.25 15 14.5 14.17 14
    15.75 15.5 15 14.67 14.5
    16 15.83 15.67 15.33 15.25
    16.5 16.33 16.17 15.67 15.5
    ```

### Compute only some cells

The raster map `centre` has a value only in the center cell of the window.
With **selection** `centre`, only the center cell is computed; **method**
`maximum` gives 16 there. All other cells keep the values of the map of 2 July,
for instance 15 in the first row.

=== "Command line"

    ```sh
    r.mapcalc expression="centre = if(row() == 3 && col() == 3, 1, null())"
    t.rast.neighbors input=precipitation_daily output=rain_picked \
        basename=rain_picked method=maximum selection=centre \
        where="name = 'precipitation_daily_2020_07_02'"
    r.out.ascii -h input=rain_picked_2020_07_02 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    15 15 14 14 14
    16 15 15 14 14
    16 16 16 15 15
    16 16 16 16 15
    17 17 16 16 15
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="centre = if(row() == 3 && col() == 3, 1, null())")
    tools.t_rast_neighbors(
        input="precipitation_daily",
        output="rain_picked",
        basename="rain_picked",
        method="maximum",
        selection="centre",
        where="name = 'precipitation_daily_2020_07_02'",
    )
    print_cells("rain_picked_2020_07_02")
    ```

    ```text
    15 15 14 14 14
    16 15 15 14 14
    16 16 16 15 15
    16 16 16 16 15
    17 17 16 16 15
    ```

### Layers with semantic labels

The dataset `layers` has two maps with the same start time, 2 July 2020,
10:30: `layer_elevation` with the semantic label `elevation` holds the
elevation in whole metres and `layer_rain` with `precipitation` the rain of
2 July from the first example. Equal start times give equal names with the
default **suffix** `gran`, so the first block, which smooths both maps, uses
**suffix** `num%03`. The new maps keep the labels of their input maps
(**semantic_labels** `input`, the default). The numbering of maps with the same
start time is not fixed, so the listing is ordered by label.

The second block computes the maximum of both layers with **semantic_labels**
`method`: the labels get the name of the method, `elevation_maximum`. The third
block selects one layer by its label and gives the new map the full start time
as its name (**suffix** `time`).

The fourth block shows what happens without **suffix** `num`, with the default
`gran` and with `time`, and with the default **nprocs** `1`: both new maps
would get the same name, for instance `failed_2020_07_02T10_30_00`, and the
tool stops at the second map and prints that the map exists. The block shows
only the line with the message. The list of datasets of the mapset has neither
of the datasets `failed` and `failed_time`, but the first map of each run stays
behind as a raster map.

=== "Command line"

    ```sh
    r.mapcalc expression="layer_elevation = round(elev_state_500m)"
    r.mapcalc expression="layer_rain = precipitation_daily_2020_07_02"
    r.support map=layer_elevation semantic_label=elevation
    r.support map=layer_rain semantic_label=precipitation
    t.create output=layers title="Layers" description="Elevation and precipitation"
    t.register input=layers maps=layer_elevation,layer_rain start="2020-07-02 10:30:00"
    t.rast.neighbors input=layers output=smoothed basename=smoothed suffix=num%03
    t.rast.list input=smoothed columns=semantic_label,min,max order=semantic_label
    ```

    ```text
    semantic_label|min|max
    elevation|1051.0|1201.0
    precipitation|14.0|16.5
    ```

    ```sh
    t.rast.neighbors input=layers output=maxima_layers basename=maximum_layer \
        suffix=num method=maximum semantic_labels=method
    t.rast.list input=maxima_layers columns=semantic_label,min,max \
        order=semantic_label
    ```

    ```text
    semantic_label|min|max
    elevation_maximum|1096.0|1291.0
    precipitation_maximum|14.0|17.0
    ```

    ```sh
    t.rast.neighbors input=layers output=rain_only basename=rain \
        suffix=time method=maximum semantic_labels=method \
        where="semantic_label = 'precipitation'"
    t.rast.list input=rain_only columns=name,semantic_label,min,max
    ```

    ```text
    name|semantic_label|min|max
    rain_2020_07_02T10_30_00|precipitation_maximum|14.0|17.0
    ```

    ```sh
    (t.rast.neighbors input=layers output=failed basename=failed 2>&1 || true) \
        | grep exists
    (t.rast.neighbors input=layers output=failed_time basename=failed_time \
        suffix=time 2>&1 || true) | grep exists
    t.list type=strds columns=name format=line mapset=.
    g.list type=raster pattern="failed*" mapset=.
    ```

    ```text
    ERROR: option <output>: <failed_2020_07_02T10_30_00> exists. To overwrite, use the --overwrite flag
    ERROR: option <output>: <failed_time_2020_07_02T10_30_00> exists. To overwrite, use the --overwrite flag
    layers,maxima_layers,precipitation_daily,rain_above,rain_circular,rain_expo,rain_gauss,rain_maximum,rain_only,rain_picked,rain_quartile,rain_smooth,smoothed
    failed_2020_07_02T10_30_00
    failed_time_2020_07_02T10_30_00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="layer_elevation = round(elev_state_500m)")
    tools.r_mapcalc(expression="layer_rain = precipitation_daily_2020_07_02")
    tools.r_support(map="layer_elevation", semantic_label="elevation")
    tools.r_support(map="layer_rain", semantic_label="precipitation")
    tools.t_create(
        output="layers", title="Layers", description="Elevation and precipitation"
    )
    tools.t_register(
        input="layers", maps="layer_elevation,layer_rain", start="2020-07-02 10:30:00"
    )
    tools.t_rast_neighbors(
        input="layers", output="smoothed", basename="smoothed", suffix="num%03"
    )
    print(
        tools.t_rast_list(
            input="smoothed", columns="semantic_label,min,max", order="semantic_label"
        ).text
    )
    ```

    ```text
    semantic_label|min|max
    elevation|1051.0|1201.0
    precipitation|14.0|16.5
    ```

    ```python
    tools.t_rast_neighbors(
        input="layers",
        output="maxima_layers",
        basename="maximum_layer",
        suffix="num",
        method="maximum",
        semantic_labels="method",
    )
    print(
        tools.t_rast_list(
            input="maxima_layers", columns="semantic_label,min,max", order="semantic_label"
        ).text
    )
    ```

    ```text
    semantic_label|min|max
    elevation_maximum|1096.0|1291.0
    precipitation_maximum|14.0|17.0
    ```

    ```python
    tools.t_rast_neighbors(
        input="layers",
        output="rain_only",
        basename="rain",
        suffix="time",
        method="maximum",
        semantic_labels="method",
        where="semantic_label = 'precipitation'",
    )
    print(tools.t_rast_list(input="rain_only", columns="name,semantic_label,min,max").text)
    ```

    ```text
    name|semantic_label|min|max
    rain_2020_07_02T10_30_00|precipitation_maximum|14.0|17.0
    ```

    ```python
    from grass.tools import ToolError

    for output, suffix in (("failed", "gran"), ("failed_time", "time")):
        try:
            tools.t_rast_neighbors(
                input="layers", output=output, basename=output, suffix=suffix
            )
        except ToolError as error:
            for line in error.stderr.splitlines():
                if "exists" in line:
                    print(line)
    print(tools.t_list(type="strds", columns="name", format="line", mapset=".").text)
    print(tools.g_list(type="raster", pattern="failed*", mapset=".").text)
    ```

    ```text
    ERROR: option <output>: <failed_2020_07_02T10_30_00> exists. To overwrite, use the --overwrite flag
    ERROR: option <output>: <failed_time_2020_07_02T10_30_00> exists. To overwrite, use the --overwrite flag
    layers,maxima_layers,precipitation_daily,rain_above,rain_circular,rain_expo,rain_gauss,rain_maximum,rain_only,rain_picked,rain_quartile,rain_smooth,smoothed
    failed_2020_07_02T10_30_00
    failed_time_2020_07_02T10_30_00
    ```

### Select the maps to process

The dataset `scenes` has four daily maps from 1 May 2026, each with an extent of
its own and a constant value of 10, 20, 30 and 40. They are generated for the
example. The current region has 4 by 4 cells of 1 km. `scene_around` (6 by 6
cells) contains the region, `scene_inside` (2 by 2 cells) lies within it,
`scene_shifted` (4 by 4 cells) overlaps it and `scene_remote` (2 by 2 cells)
is far away.

The first block selects the maps from the second day on with **where**. The new
map of `scene_remote` has no value in the region, so it is empty and not
registered: two maps remain, with the 4 by 4 cells of the current region. The
second block adds **-n**, which registers the empty map as well; its smallest
and largest value are `None`.

The third block selects by **region_relation**: `overlaps` takes the first
three maps, `contains` takes `scene_around` and `is_contained` takes
`scene_inside`.

=== "Command line"

    ```sh
    for scene in "scene_around -1 5 10" "scene_inside 1 3 20" \
        "scene_shifted 2 6 30" "scene_remote 10 12 40"; do
        set -- $scene
        g.region w=$((640000 + 1000 * $2)) e=$((640000 + 1000 * $3)) \
            s=$((220000 + 1000 * $2)) n=$((220000 + 1000 * $3)) res=1000
        r.mapcalc expression="$1 = $4"
    done
    g.region w=640000 e=644000 s=220000 n=224000 res=1000
    t.create output=scenes title="Scenes" \
        description="Scenes with extents of their own"
    t.register -i input=scenes \
        maps=scene_around,scene_inside,scene_shifted,scene_remote \
        start=2026-05-01 increment="1 day"
    t.rast.neighbors input=scenes output=late basename=late \
        where="start_time >= '2026-05-02'"
    t.rast.list input=late columns=name,rows,cols,min,max
    ```

    ```text
    name|rows|cols|min|max
    late_2026_05_02|4|4|20.0|20.0
    late_2026_05_03|4|4|30.0|30.0
    ```

    ```sh
    t.rast.neighbors -n input=scenes output=late_all basename=late_all \
        where="start_time >= '2026-05-02'"
    t.rast.list input=late_all columns=name,min,max
    ```

    ```text
    name|min|max
    late_all_2026_05_02|20.0|20.0
    late_all_2026_05_03|30.0|30.0
    late_all_2026_05_04|None|None
    ```

    ```sh
    for relation in overlaps contains is_contained; do
        t.rast.neighbors input=scenes output=rel_$relation \
            basename=rel_$relation region_relation=$relation
        echo "$relation:"
        t.rast.list -u input=rel_$relation columns=name
    done
    ```

    ```text
    overlaps:
    rel_overlaps_2026_05_01
    rel_overlaps_2026_05_02
    rel_overlaps_2026_05_03
    contains:
    rel_contains_2026_05_01
    is_contained:
    rel_is_contained_2026_05_02
    ```

=== "Python (grass.tools)"

    ```python
    for name, low, high, value in (
        ("scene_around", -1, 5, 10),
        ("scene_inside", 1, 3, 20),
        ("scene_shifted", 2, 6, 30),
        ("scene_remote", 10, 12, 40),
    ):
        tools.g_region(
            w=640000 + 1000 * low,
            e=640000 + 1000 * high,
            s=220000 + 1000 * low,
            n=220000 + 1000 * high,
            res=1000,
        )
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.g_region(w=640000, e=644000, s=220000, n=224000, res=1000)
    tools.t_create(
        output="scenes", title="Scenes", description="Scenes with extents of their own"
    )
    tools.t_register(
        input="scenes",
        maps="scene_around,scene_inside,scene_shifted,scene_remote",
        start="2026-05-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_neighbors(
        input="scenes",
        output="late",
        basename="late",
        where="start_time >= '2026-05-02'",
    )
    print(tools.t_rast_list(input="late", columns="name,rows,cols,min,max").text)
    ```

    ```text
    name|rows|cols|min|max
    late_2026_05_02|4|4|20.0|20.0
    late_2026_05_03|4|4|30.0|30.0
    ```

    ```python
    tools.t_rast_neighbors(
        input="scenes",
        output="late_all",
        basename="late_all",
        where="start_time >= '2026-05-02'",
        flags="n",
    )
    print(tools.t_rast_list(input="late_all", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    late_all_2026_05_02|20.0|20.0
    late_all_2026_05_03|30.0|30.0
    late_all_2026_05_04|None|None
    ```

    ```python
    for relation in ("overlaps", "contains", "is_contained"):
        tools.t_rast_neighbors(
            input="scenes",
            output=f"rel_{relation}",
            basename=f"rel_{relation}",
            region_relation=relation,
        )
        print(f"{relation}:")
        print(tools.t_rast_list(input=f"rel_{relation}", columns="name", flags="u").text)
    ```

    ```text
    overlaps:
    rel_overlaps_2026_05_01
    rel_overlaps_2026_05_02
    rel_overlaps_2026_05_03
    contains:
    rel_contains_2026_05_01
    is_contained:
    rel_is_contained_2026_05_02
    ```

### Use the region of each map and extend a dataset

The first block computes each map in its own region (**-r**) for the maps that
**region_relation** `overlaps` selects, still with the current region of 4 by
4 cells. The new maps have 6 by 6, 2 by 2 and 4 by 4 cells, the sizes of
`scene_around`, `scene_inside` and `scene_shifted`. The current region keeps
its 4 rows and 4 columns.

In the second block, the first run makes a dataset `part` from the first two
days. The run with **-e** adds the maps of the third day (the fourth day is
empty and not registered) to it: `part` has three maps. A second run with
**-e** and **--overwrite** makes the maps of the second and third day again;
**--overwrite** is needed because they exist, and the map of the first day
stays.

=== "Command line"

    ```sh
    t.rast.neighbors -r input=scenes output=own basename=own \
        region_relation=overlaps
    t.rast.list input=own columns=name,rows,cols
    g.region -g | grep -E "^(rows|cols)="
    ```

    ```text
    name|rows|cols
    own_2026_05_01|6|6
    own_2026_05_02|2|2
    own_2026_05_03|4|4
    rows=4
    cols=4
    ```

    ```sh
    t.rast.neighbors input=scenes output=part basename=part \
        where="start_time < '2026-05-03'"
    t.rast.neighbors -e input=scenes output=part basename=part \
        where="start_time >= '2026-05-03'"
    t.rast.list input=part columns=name,min,max
    t.rast.neighbors -e input=scenes output=part basename=part \
        where="start_time >= '2026-05-02' and start_time < '2026-05-04'" \
        --overwrite
    t.rast.list input=part columns=name,min,max
    ```

    ```text
    name|min|max
    part_2026_05_01|10.0|10.0
    part_2026_05_02|20.0|20.0
    part_2026_05_03|30.0|30.0
    name|min|max
    part_2026_05_01|10.0|10.0
    part_2026_05_02|20.0|20.0
    part_2026_05_03|30.0|30.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_neighbors(
        input="scenes",
        output="own",
        basename="own",
        region_relation="overlaps",
        flags="r",
    )
    print(tools.t_rast_list(input="own", columns="name,rows,cols").text)
    region = tools.g_region(flags="g").keyval
    print(f"rows={region['rows']}")
    print(f"cols={region['cols']}")
    ```

    ```text
    name|rows|cols
    own_2026_05_01|6|6
    own_2026_05_02|2|2
    own_2026_05_03|4|4
    rows=4
    cols=4
    ```

    ```python
    tools.t_rast_neighbors(
        input="scenes",
        output="part",
        basename="part",
        where="start_time < '2026-05-03'",
    )
    tools.t_rast_neighbors(
        input="scenes",
        output="part",
        basename="part",
        where="start_time >= '2026-05-03'",
        flags="e",
    )
    print(tools.t_rast_list(input="part", columns="name,min,max").text)
    tools.t_rast_neighbors(
        input="scenes",
        output="part",
        basename="part",
        where="start_time >= '2026-05-02' and start_time < '2026-05-04'",
        flags="e",
        overwrite=True,
    )
    print(tools.t_rast_list(input="part", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    part_2026_05_01|10.0|10.0
    part_2026_05_02|20.0|20.0
    part_2026_05_03|30.0|30.0
    name|min|max
    part_2026_05_01|10.0|10.0
    part_2026_05_02|20.0|20.0
    part_2026_05_03|30.0|30.0
    ```

### Draw a map before and after the filter

The dataset `rain_noisy` has two maps of 40 by 40 cells, the rain of 2 and
3 July in a window in the mountains of the west with a checkerboard of plus and
minus 3 mm added. The noise is assumed; it makes the effect of the filter
visible. The figure shows `rain_noisy_2020_07_02` on the left and its 3 by 3
average on the right. The same color table is used for both maps, so the colors
mean the same values. The average smooths away most of the checkerboard, as
every window inside the region holds five cells of one sign and four of the
other, so that a flat field keeps a remainder of 3 / 9 mm; at the edge of the
region the window holds fewer cells, 2 and 2 in a corner and 3 and 3 at an edge,
and the noise cancels. The average leaves the trend of the rain; the range of
the values shrinks from 9 to 20 mm in `rain_noisy_2020_07_02` to 11.9 to 17.3
mm in the first new map, whose smallest value `107 / 9` and largest value
`156 / 9` are sums of nine cells. The white cell in the upper left corner of
the left map has no value in the input; the average fills it from its
neighbors.

=== "Command line"

    ```sh
    g.region w=350000 e=390000 s=250000 n=290000 res=1000
    for day in 02 03; do
        r.mapcalc expression="rain_noisy_2020_07_$day = precipitation_daily_2020_07_$day + if((row() + col()) % 2 == 0, 3.0, -3.0)"
    done
    t.create output=rain_noisy title="Noisy precipitation" \
        description="Daily precipitation with checkerboard noise in mm"
    t.register -i input=rain_noisy maps=rain_noisy_2020_07_02,rain_noisy_2020_07_03 \
        start=2020-07-02 increment="1 day"
    t.rast.neighbors input=rain_noisy output=rain_denoised basename=rain_denoised size=3
    t.rast.list input=rain_noisy columns=name,min,max
    t.rast.list input=rain_denoised columns=name,min,max
    ```

    ```text
    name|min|max
    rain_noisy_2020_07_02|9.0|20.0
    rain_noisy_2020_07_03|6.0|15.0
    name|min|max
    rain_denoised_2020_07_02|11.88888888888889|17.333333333333332
    rain_denoised_2020_07_03|8.666666666666666|13.0
    ```

    ```sh
    r.colors map=rain_noisy_2020_07_02,rain_denoised_2020_07_02 rules=- <<EOF
    9 68:1:84
    11.75 59:82:139
    14.5 33:145:140
    17.25 94:201:98
    20 253:231:37
    EOF
    d.mon start=cairo output=t_rast_neighbors_average.png width=800 height=400
    d.frame -c frame=before at=0,100,0,50
    d.rast map=rain_noisy_2020_07_02
    d.text text="Before" color=white size=6 at=3,92
    d.frame -c frame=after at=0,100,50,100
    d.rast map=rain_denoised_2020_07_02
    d.text text="After" color=white size=6 at=3,92
    d.mon stop=cairo
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(w=350000, e=390000, s=250000, n=290000, res=1000)
    for day in ("02", "03"):
        tools.r_mapcalc(
            expression=f"rain_noisy_2020_07_{day} = precipitation_daily_2020_07_{day}"
            " + if((row() + col()) % 2 == 0, 3.0, -3.0)"
        )
    tools.t_create(
        output="rain_noisy",
        title="Noisy precipitation",
        description="Daily precipitation with checkerboard noise in mm",
    )
    tools.t_register(
        input="rain_noisy",
        maps="rain_noisy_2020_07_02,rain_noisy_2020_07_03",
        start="2020-07-02",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_neighbors(
        input="rain_noisy", output="rain_denoised", basename="rain_denoised", size=3
    )
    print(tools.t_rast_list(input="rain_noisy", columns="name,min,max").text)
    print(tools.t_rast_list(input="rain_denoised", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    rain_noisy_2020_07_02|9.0|20.0
    rain_noisy_2020_07_03|6.0|15.0
    name|min|max
    rain_denoised_2020_07_02|11.88888888888889|17.333333333333332
    rain_denoised_2020_07_03|8.666666666666666|13.0
    ```

    ```python
    from io import StringIO

    colors = "9 68:1:84\n11.75 59:82:139\n14.5 33:145:140\n17.25 94:201:98\n20 253:231:37\n"
    tools.r_colors(
        map="rain_noisy_2020_07_02,rain_denoised_2020_07_02", rules=StringIO(colors)
    )
    tools.d_mon(start="cairo", output="t_rast_neighbors_average.png", width=800, height=400)
    tools.d_frame(flags="c", frame="before", at=[0, 100, 0, 50])
    tools.d_rast(map="rain_noisy_2020_07_02")
    tools.d_text(text="Before", color="white", size=6, at=[3, 92])
    tools.d_frame(flags="c", frame="after", at=[0, 100, 50, 100])
    tools.d_rast(map="rain_denoised_2020_07_02")
    tools.d_text(text="After", color="white", size=6, at=[3, 92])
    tools.d_mon(stop="cairo")
    ```

![Daily precipitation with assumed checkerboard noise before and after the average](t_rast_neighbors_average.png)

*Figure: The map `rain_noisy_2020_07_02` (left), the rain of 2 July with assumed
checkerboard noise, and its average in a window of 3 by 3 cells (right),
`rain_denoised_2020_07_02`, in the same color table.*

### Relative time and a dataset of another mapset

The dataset `model` has two maps with relative time, `rain_forecast_0h` with the
rain of 2 July and `rain_forecast_6h` with the rain of 3 July, registered at 0
and 6 hours; the region is the window of 5 by 5 cells again. The new maps have
the same times. With the default **suffix** `gran` they are numbered,
`m1_00001` and `m1_00002`, and so they are with **suffix** `time`; **suffix**
`num%03` gives three digits.

The second block creates the mapset `t_rast_neighbors_2`, sets the region to
North Carolina again and adds the first mapset to the search path with
*[g.mapsets](g.mapsets.md)*. The input name `model@t_rast_neighbors` selects
the dataset of the other mapset; the new maps and the new dataset are created in
`t_rast_neighbors_2`, as their ids show.

=== "Command line"

    ```sh
    g.region w=366000 e=371000 s=270000 n=275000 res=1000
    r.mapcalc expression="rain_forecast_0h = precipitation_daily_2020_07_02"
    r.mapcalc expression="rain_forecast_6h = precipitation_daily_2020_07_03"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output every six hours"
    t.register -i input=model maps=rain_forecast_0h,rain_forecast_6h \
        start=0 increment=6 unit=hours
    t.rast.neighbors input=model output=m1 basename=m1
    t.rast.list input=m1 columns=name,start_time,end_time,min,max
    t.rast.neighbors input=model output=m2 basename=m2 suffix=time
    t.rast.list input=m2 columns=name,start_time
    t.rast.neighbors input=model output=m3 basename=m3 suffix=num%03
    t.rast.list input=m3 columns=name,start_time
    ```

    ```text
    name|start_time|end_time|min|max
    m1_00001|0|6|14.0|16.5
    m1_00002|6|12|10.0|12.0
    name|start_time
    m2_00001|0
    m2_00002|6
    name|start_time
    m3_001|0
    m3_002|6
    ```

    ```sh
    g.mapset -c mapset=t_rast_neighbors_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_rast_neighbors operation=add
    t.rast.neighbors input=model@t_rast_neighbors output=m4 basename=m4
    t.rast.list input=m4 columns=id,mapset,start_time
    ```

    ```text
    id|mapset|start_time
    m4_00001@t_rast_neighbors_2|t_rast_neighbors_2|0
    m4_00002@t_rast_neighbors_2|t_rast_neighbors_2|6
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(w=366000, e=371000, s=270000, n=275000, res=1000)
    tools.r_mapcalc(expression="rain_forecast_0h = precipitation_daily_2020_07_02")
    tools.r_mapcalc(expression="rain_forecast_6h = precipitation_daily_2020_07_03")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output every six hours",
    )
    tools.t_register(
        input="model",
        maps="rain_forecast_0h,rain_forecast_6h",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    tools.t_rast_neighbors(input="model", output="m1", basename="m1")
    print(tools.t_rast_list(input="m1", columns="name,start_time,end_time,min,max").text)
    tools.t_rast_neighbors(input="model", output="m2", basename="m2", suffix="time")
    print(tools.t_rast_list(input="m2", columns="name,start_time").text)
    tools.t_rast_neighbors(input="model", output="m3", basename="m3", suffix="num%03")
    print(tools.t_rast_list(input="m3", columns="name,start_time").text)
    ```

    ```text
    name|start_time|end_time|min|max
    m1_00001|0|6|14.0|16.5
    m1_00002|6|12|10.0|12.0
    name|start_time
    m2_00001|0
    m2_00002|6
    name|start_time
    m3_001|0
    m3_002|6
    ```

    ```python
    tools.g_mapset(mapset="t_rast_neighbors_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_rast_neighbors", operation="add")
    tools.t_rast_neighbors(input="model@t_rast_neighbors", output="m4", basename="m4")
    print(tools.t_rast_list(input="m4", columns="id,mapset,start_time").text)
    ```

    ```text
    id|mapset|start_time
    m4_00001@t_rast_neighbors_2|t_rast_neighbors_2|0
    m4_00002@t_rast_neighbors_2|t_rast_neighbors_2|6
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[d.frame](d.frame.md), [d.rast](d.rast.md), [d.text](d.text.md),
[g.list](g.list.md), [g.mapset](g.mapset.md), [g.mapsets](g.mapsets.md),
[g.region](g.region.md), [r.colors](r.colors.md), [r.mapcalc](r.mapcalc.md),
[r.neighbors](r.neighbors.md), [r.out.ascii](r.out.ascii.md),
[r.support](r.support.md), [t.create](t.create.md), [t.info](t.info.md),
[t.list](t.list.md), [t.rast.aggregate](t.rast.aggregate.md),
[t.rast.extract](t.rast.extract.md), [t.rast.list](t.rast.list.md),
[t.register](t.register.md), [temporal data processing](temporalintro.md),
[v.surf.idw](v.surf.idw.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
