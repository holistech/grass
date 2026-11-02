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
  of the input dataset: `2026_03_01` in a dataset of days. A dataset of a
  single time instance has no granularity; `gran` then takes the full start
  time, as `time` does.
- `time` takes the full start time: `2026_03_01T00_00_00`.
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
mapset (`input=model@PERMANENT`) selects it. The new maps and the new dataset
are always created in the current mapset, as the last example shows. Relative
time works as absolute time; the new maps have the time of the input maps.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Smooth the maps of a dataset

The dataset `ramp` has three daily maps of 3 by 3 cells. The cells of `ramp_1`
hold the numbers 1 to 9 row by row; `ramp_2` and `ramp_3` have 10 and 20 added.

With the default **method** `average` and a window of **size** 3, each cell
takes the mean of the cells around it. The cell in the center sees all nine
cells, so it keeps its value 5, 15 and 25. A cell in a corner sees only the
four cells that lie in the region: the upper left cell of `ramp_1` is
`(1 + 2 + 4 + 5) / 4 = 3`. The new maps have a smallest value of 3, 13 and 23
and a largest value of 7, 17 and 27, and the names of their days. **nprocs**
`2` computes two maps at the same time.

The second block prints the cells of the first new map. The third block shows
with *[t.info](t.info.md)* that the new dataset takes the temporal type, the
semantic type, the title and the description of `ramp`, and that it holds three
maps.

=== "Command line"

    ```sh
    g.region n=3 s=0 e=3 w=0 res=1
    for k in 0 1 2; do
        r.mapcalc expression="ramp_$((k + 1)) = double((row() - 1) * 3 + col()) + 10 * $k"
    done
    t.create output=ramp semantictype=max title="Ramps" description="Three ramps of nine cells"
    t.register -i input=ramp maps=ramp_1,ramp_2,ramp_3 \
        start=2026-03-01 increment="1 day"
    t.rast.neighbors input=ramp output=smooth basename=smooth \
        size=3 method=average nprocs=2
    t.rast.list input=smooth columns=name,start_time,end_time,min,max
    ```

    ```text
    name|start_time|end_time|min|max
    smooth_2026_03_01|2026-03-01 00:00:00|2026-03-02 00:00:00|3.0|7.0
    smooth_2026_03_02|2026-03-02 00:00:00|2026-03-03 00:00:00|13.0|17.0
    smooth_2026_03_03|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|27.0
    ```

    ```sh
    r.out.ascii -h input=smooth_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    3 3.5 4
    4.5 5 5.5
    6 6.5 7
    ```

    ```sh
    t.info input=smooth
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ smooth@PERMANENT
     | Name: ...................... smooth
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-01 00:00:00
     | End time:................... 2026-03-04 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 3.0
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
     | Minimum value min:.......... 3.0
     | Minimum value max:.......... 23.0
     | Maximum value min:.......... 7.0
     | Maximum value max:.......... 27.0
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 3
     |
     | Title:
     | Ramps
     | Description:
     | Three ramps of nine cells
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.neighbors input="ramp" output="smooth"
     |     basename="smooth" size="3" method="average" nprocs="2"
     | 
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    for k in range(3):
        tools.r_mapcalc(
            expression=f"ramp_{k + 1} = double((row() - 1) * 3 + col()) + 10 * {k}"
        )
    tools.t_create(
        output="ramp",
        semantictype="max",
        title="Ramps",
        description="Three ramps of nine cells",
    )
    tools.t_register(
        input="ramp",
        maps="ramp_1,ramp_2,ramp_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_neighbors(
        input="ramp", output="smooth", basename="smooth", size=3, method="average", nprocs=2
    )
    print(
        tools.t_rast_list(input="smooth", columns="name,start_time,end_time,min,max").text
    )
    ```

    ```text
    name|start_time|end_time|min|max
    smooth_2026_03_01|2026-03-01 00:00:00|2026-03-02 00:00:00|3.0|7.0
    smooth_2026_03_02|2026-03-02 00:00:00|2026-03-03 00:00:00|13.0|17.0
    smooth_2026_03_03|2026-03-03 00:00:00|2026-03-04 00:00:00|23.0|27.0
    ```

    ```python
    def print_cells(name):
        cells = tools.r_out_ascii(input=name, output="-", precision=2, flags="h")
        for line in cells.stdout.splitlines():
            print(line.rstrip())


    print_cells("smooth_2026_03_01")
    ```

    ```text
    3 3.5 4
    4.5 5 5.5
    6 6.5 7
    ```

    ```python
    print(tools.t_info(input="smooth").stdout, end="")
    ```

    ```text
     +-------------------- Space Time Raster Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ smooth@PERMANENT
     | Name: ...................... smooth
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-03-01 00:00:00
     | End time:................... 2026-03-04 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 3.0
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
     | Minimum value min:.......... 3.0
     | Minimum value max:.......... 23.0
     | Maximum value min:.......... 7.0
     | Maximum value max:.......... 27.0
     | Aggregation type:........... None
     | Number of semantic labels:.. 0
     | Semantic labels:............ None
     | Number of registered maps:.. 3
     |
     | Title:
     | Ramps
     | Description:
     | Three ramps of nine cells
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.neighbors input="ramp" output="smooth"
     |     basename="smooth" size="3" method="average" nprocs="2"
     | 
     +----------------------------------------------------------------------------+
    ```

### Choose the statistic and the window

The three blocks use the first map `ramp_1` only (**where**), so each result
is a dataset of one map. The cells of `ramp_1` are 1 2 3 / 4 5 6 / 7 8 9.

1. **method** `maximum` gives the largest value of the window: 5 in the upper
   left corner (of 1, 2, 4 and 5) and 9 in the center.
2. **method** `quantile` with **quantile** `0.25` takes the position
   `0.25 * (n - 1)` in the sorted values. In the corner there are `n = 4`
   values 1, 2, 4 and 5; the position 0.75 gives `1 + 0.75 * (2 - 1) = 1.75`.
   In the center there are nine values and the position is 2, the third value,
   3.
3. With **-c**, the window is circular. The center sees the five cells 2, 4, 5,
   6 and 8, and **method** `sum` gives 25; the upper left corner sees the
   three cells 1, 2 and 4, which give 7.

=== "Command line"

    ```sh
    t.rast.neighbors input=ramp output=maxima basename=maximum \
        method=maximum where="name = 'ramp_1'"
    r.out.ascii -h input=maximum_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    5 6 6
    8 9 9
    8 9 9
    ```

    ```sh
    t.rast.neighbors input=ramp output=quartiles basename=quartile \
        method=quantile quantile=0.25 where="name = 'ramp_1'"
    r.out.ascii -h input=quartile_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    1.75 2.25 2.75
    2.5 3 3.5
    4.75 5.25 5.75
    ```

    ```sh
    t.rast.neighbors -c input=ramp output=circular basename=circular \
        method=sum where="name = 'ramp_1'"
    r.out.ascii -h input=circular_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    7 11 11
    17 25 23
    19 29 23
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_neighbors(
        input="ramp",
        output="maxima",
        basename="maximum",
        method="maximum",
        where="name = 'ramp_1'",
    )
    print_cells("maximum_2026_03_01")
    ```

    ```text
    5 6 6
    8 9 9
    8 9 9
    ```

    ```python
    tools.t_rast_neighbors(
        input="ramp",
        output="quartiles",
        basename="quartile",
        method="quantile",
        quantile=0.25,
        where="name = 'ramp_1'",
    )
    print_cells("quartile_2026_03_01")
    ```

    ```text
    1.75 2.25 2.75
    2.5 3 3.5
    4.75 5.25 5.75
    ```

    ```python
    tools.t_rast_neighbors(
        input="ramp",
        output="circular",
        basename="circular",
        method="sum",
        where="name = 'ramp_1'",
        flags="c",
    )
    print_cells("circular_2026_03_01")
    ```

    ```text
    7 11 11
    17 25 23
    19 29 23
    ```

### Weight the cells of the window

The three blocks smooth `ramp_1` with weights. The cells of `ramp_1` are
1 2 3 / 4 5 6 / 7 8 9; without weights the center is 5 and the upper left
corner 3.

1. **weighting_function** `gaussian` with **weighting_factor** `1`. The
   weight falls with the distance from the center, so the cell itself counts
   more than in the plain average: the corner is 2.51, nearer to its own value
   1 than the plain 3. Cells at the same distance on opposite sides have the
   same weight, so the center stays 5.
2. **weighting_function** `exponential` with **weighting_factor** `-1`
   weights by `exp(-d)`, which falls faster with the distance than the
   Gaussian weights of the first block: the corner is 2.24.
3. **weighting_function** `file` with **weight** takes the matrix of a text
   file. The matrix 1 1 1 / 1 1 1 / 0 0 0 gives the row below the center the
   weight 0, so the center is the mean of the six cells above and beside it,
   `(1 + 2 + 3 + 4 + 5 + 6) / 6 = 3.5`.

=== "Command line"

    ```sh
    t.rast.neighbors input=ramp output=gauss basename=gauss \
        weighting_function=gaussian weighting_factor=1 where="name = 'ramp_1'"
    r.out.ascii -h input=gauss_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    2.51 3.13 3.76
    4.38 5 5.62
    6.24 6.87 7.49
    ```

    ```sh
    t.rast.neighbors input=ramp output=expo basename=expo \
        weighting_function=exponential weighting_factor=-1 where="name = 'ramp_1'"
    r.out.ascii -h input=expo_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    2.24 2.99 3.62
    4.33 5 5.67
    6.38 7.01 7.76
    ```

    ```sh
    cat > weights.txt <<EOF
    1 1 1
    1 1 1
    0 0 0
    EOF
    t.rast.neighbors input=ramp output=above basename=above \
        weighting_function=file weight=weights.txt where="name = 'ramp_1'"
    r.out.ascii -h input=above_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    1.5 2 2.5
    3 3.5 4
    6 6.5 7
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_neighbors(
        input="ramp",
        output="gauss",
        basename="gauss",
        weighting_function="gaussian",
        weighting_factor=1,
        where="name = 'ramp_1'",
    )
    print_cells("gauss_2026_03_01")
    ```

    ```text
    2.51 3.13 3.76
    4.38 5 5.62
    6.24 6.87 7.49
    ```

    ```python
    tools.t_rast_neighbors(
        input="ramp",
        output="expo",
        basename="expo",
        weighting_function="exponential",
        weighting_factor=-1,
        where="name = 'ramp_1'",
    )
    print_cells("expo_2026_03_01")
    ```

    ```text
    2.24 2.99 3.62
    4.33 5 5.67
    6.38 7.01 7.76
    ```

    ```python
    from pathlib import Path

    Path("weights.txt").write_text("1 1 1\n1 1 1\n0 0 0\n")
    tools.t_rast_neighbors(
        input="ramp",
        output="above",
        basename="above",
        weighting_function="file",
        weight="weights.txt",
        where="name = 'ramp_1'",
    )
    print_cells("above_2026_03_01")
    ```

    ```text
    1.5 2 2.5
    3 3.5 4
    6 6.5 7
    ```

### Compute only some cells

The raster map `centre` has a value only in the center cell. With
**selection** `centre`, only the center cell is computed; **method**
`maximum` gives 9 there. All other cells keep the values of `ramp_1`.

=== "Command line"

    ```sh
    r.mapcalc expression="centre = if(row() == 2 && col() == 2, 1, null())"
    t.rast.neighbors input=ramp output=picked basename=picked \
        method=maximum selection=centre where="name = 'ramp_1'"
    r.out.ascii -h input=picked_2026_03_01 output=- precision=2 | sed 's/ *$//'
    ```

    ```text
    1 2 3
    4 9 6
    7 8 9
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="centre = if(row() == 2 && col() == 2, 1, null())")
    tools.t_rast_neighbors(
        input="ramp",
        output="picked",
        basename="picked",
        method="maximum",
        selection="centre",
        where="name = 'ramp_1'",
    )
    print_cells("picked_2026_03_01")
    ```

    ```text
    1 2 3
    4 9 6
    7 8 9
    ```

### Bands with semantic labels

The dataset `bands` has two maps with the same start time: `red_1` with the
semantic label `S2_B4` holds 1 to 9 and `nir_1` with `S2_B8` holds 11 to 19.
Equal start times give equal names with the default **suffix** `gran`, so the
first block, which smooths both maps, uses **suffix** `num%03`. The new maps
keep the labels of their input maps (**semantic_labels** `input`, the
default). The numbering of maps with the same start time is not fixed, so the
listing is ordered by label.

The second block computes the maximum of both bands with **semantic_labels**
`method`: the labels get the name of the method, `S2_B4_maximum`. The third
block selects one band by its label and gives the new map the full start time
as its name (**suffix** `time`).

The fourth block shows what happens without **suffix** `num`, with the default
`gran` and with `time`, and with the default **nprocs** `1`: both new maps
would get the same name, for instance `failed_2026_06_01T10_30_00`, and the
tool stops at the second map and prints that the map exists. The block shows
only the line with the message. The list of datasets has neither of the
datasets `failed` and `failed_time`, but the first map of each run stays behind
as a raster map.

=== "Command line"

    ```sh
    r.mapcalc expression="red_1 = double((row() - 1) * 3 + col())"
    r.mapcalc expression="nir_1 = double((row() - 1) * 3 + col()) + 10"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    t.create output=bands title="Bands" description="Red and near infrared"
    t.register input=bands maps=red_1,nir_1 start="2026-06-01 10:30:00"
    t.rast.neighbors input=bands output=smoothed basename=smoothed suffix=num%03
    t.rast.list input=smoothed columns=semantic_label,min,max order=semantic_label
    ```

    ```text
    semantic_label|min|max
    S2_B4|3.0|7.0
    S2_B8|13.0|17.0
    ```

    ```sh
    t.rast.neighbors input=bands output=maxima_bands basename=maximum_band \
        suffix=num method=maximum semantic_labels=method
    t.rast.list input=maxima_bands columns=semantic_label,min,max \
        order=semantic_label
    ```

    ```text
    semantic_label|min|max
    S2_B4_maximum|5.0|9.0
    S2_B8_maximum|15.0|19.0
    ```

    ```sh
    t.rast.neighbors input=bands output=red_only basename=red \
        suffix=time method=maximum semantic_labels=method \
        where="semantic_label = 'S2_B4'"
    t.rast.list input=red_only columns=name,semantic_label,min,max
    ```

    ```text
    name|semantic_label|min|max
    red_2026_06_01T10_30_00|S2_B4_maximum|5.0|9.0
    ```

    ```sh
    (t.rast.neighbors input=bands output=failed basename=failed 2>&1 || true) \
        | grep exists
    (t.rast.neighbors input=bands output=failed_time basename=failed_time \
        suffix=time 2>&1 || true) | grep exists
    t.list type=strds columns=name format=line
    g.list type=raster pattern="failed*"
    ```

    ```text
    ERROR: option <output>: <failed_2026_06_01T10_30_00> exists. To overwrite, use the --overwrite flag
    ERROR: option <output>: <failed_time_2026_06_01T10_30_00> exists. To overwrite, use the --overwrite flag
    above,bands,circular,expo,gauss,maxima,maxima_bands,picked,quartiles,ramp,red_only,smooth,smoothed
    failed_2026_06_01T10_30_00
    failed_time_2026_06_01T10_30_00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="red_1 = double((row() - 1) * 3 + col())")
    tools.r_mapcalc(expression="nir_1 = double((row() - 1) * 3 + col()) + 10")
    tools.r_support(map="red_1", semantic_label="S2_B4")
    tools.r_support(map="nir_1", semantic_label="S2_B8")
    tools.t_create(output="bands", title="Bands", description="Red and near infrared")
    tools.t_register(input="bands", maps="red_1,nir_1", start="2026-06-01 10:30:00")
    tools.t_rast_neighbors(
        input="bands", output="smoothed", basename="smoothed", suffix="num%03"
    )
    print(
        tools.t_rast_list(
            input="smoothed", columns="semantic_label,min,max", order="semantic_label"
        ).text
    )
    ```

    ```text
    semantic_label|min|max
    S2_B4|3.0|7.0
    S2_B8|13.0|17.0
    ```

    ```python
    tools.t_rast_neighbors(
        input="bands",
        output="maxima_bands",
        basename="maximum_band",
        suffix="num",
        method="maximum",
        semantic_labels="method",
    )
    print(
        tools.t_rast_list(
            input="maxima_bands", columns="semantic_label,min,max", order="semantic_label"
        ).text
    )
    ```

    ```text
    semantic_label|min|max
    S2_B4_maximum|5.0|9.0
    S2_B8_maximum|15.0|19.0
    ```

    ```python
    tools.t_rast_neighbors(
        input="bands",
        output="red_only",
        basename="red",
        suffix="time",
        method="maximum",
        semantic_labels="method",
        where="semantic_label = 'S2_B4'",
    )
    print(tools.t_rast_list(input="red_only", columns="name,semantic_label,min,max").text)
    ```

    ```text
    name|semantic_label|min|max
    red_2026_06_01T10_30_00|S2_B4_maximum|5.0|9.0
    ```

    ```python
    from grass.tools import ToolError

    for output, suffix in (("failed", "gran"), ("failed_time", "time")):
        try:
            tools.t_rast_neighbors(
                input="bands", output=output, basename=output, suffix=suffix
            )
        except ToolError as error:
            for line in error.stderr.splitlines():
                if "exists" in line:
                    print(line)
    print(tools.t_list(type="strds", columns="name", format="line").text)
    print(tools.g_list(type="raster", pattern="failed*").text)
    ```

    ```text
    ERROR: option <output>: <failed_2026_06_01T10_30_00> exists. To overwrite, use the --overwrite flag
    ERROR: option <output>: <failed_time_2026_06_01T10_30_00> exists. To overwrite, use the --overwrite flag
    above,bands,circular,expo,gauss,maxima,maxima_bands,picked,quartiles,ramp,red_only,smooth,smoothed
    failed_2026_06_01T10_30_00
    failed_time_2026_06_01T10_30_00
    ```

### Select the maps to process

The dataset `scenes` has four daily maps, each with an extent of its own and
constant values 10, 20, 30 and 40. The current region reaches from 0 to 4 in
both directions. `scene_1` (from -1 to 5) contains the region, `scene_2`
(1 to 3) lies within it, `scene_3` (2 to 6) overlaps it and `scene_4` (10 to
12) is far away.

The first block selects the maps from the second day on with **where**. The new
map of `scene_4` has no value in the region, so it is empty and not registered:
two maps remain, with the 4 by 4 cells of the current region. The second block
adds **-n**, which registers the empty map as well; its smallest and largest
value are `None`.

The third block selects by **region_relation**: `overlaps` takes the first
three maps, `contains` takes `scene_1` and `is_contained` takes `scene_2`.

=== "Command line"

    ```sh
    for scene in "scene_1 -1 5 10" "scene_2 1 3 20" \
        "scene_3 2 6 30" "scene_4 10 12 40"; do
        set -- $scene
        g.region s=$2 n=$3 w=$2 e=$3 res=1
        r.mapcalc expression="$1 = $4"
    done
    g.region s=0 n=4 w=0 e=4 res=1
    t.create output=scenes title="Scenes" \
        description="Scenes with extents of their own"
    t.register -i input=scenes maps=scene_1,scene_2,scene_3,scene_4 \
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
        ("scene_1", -1, 5, 10),
        ("scene_2", 1, 3, 20),
        ("scene_3", 2, 6, 30),
        ("scene_4", 10, 12, 40),
    ):
        tools.g_region(s=low, n=high, w=low, e=high, res=1)
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.g_region(s=0, n=4, w=0, e=4, res=1)
    tools.t_create(
        output="scenes", title="Scenes", description="Scenes with extents of their own"
    )
    tools.t_register(
        input="scenes",
        maps="scene_1,scene_2,scene_3,scene_4",
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
**region_relation** `overlaps` selects, still with the current region from
0 to 4. The new maps have 6 by 6, 2 by 2 and 4 by 4 cells, the sizes of
`scene_1`, `scene_2` and `scene_3`. The current region keeps its 4 rows and
4 columns.

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

The dataset `noisy` has two maps of 12 by 12 cells. In the cells of `noisy_1`,
the column number is the trend and a checkerboard of plus and minus 3 is the
noise. The figure shows `noisy_1` on the left and its 3 by 3 average on the
right. The same color table is used for both maps, so the colors mean the
same values. The average smooths away most of the checkerboard and leaves
the trend from left to right; the range of the values shrinks from -2 to 15
in `noisy_1` to 1.5 to 11.5 in the first new map.

=== "Command line"

    ```sh
    g.region n=12 s=0 e=12 w=0 res=1
    r.mapcalc expression="noisy_1 = double(col()) + if((row() + col()) % 2 == 0, 3, -3)"
    r.mapcalc expression="noisy_2 = double(col()) + 2 + if((row() + col()) % 2 == 0, 3, -3)"
    t.create output=noisy title="Noisy" description="Ramp with checkerboard noise"
    t.register -i input=noisy maps=noisy_1,noisy_2 \
        start=2026-04-01 increment="1 day"
    t.rast.neighbors input=noisy output=denoised basename=denoised size=3
    t.rast.list input=noisy columns=name,min,max
    t.rast.list input=denoised columns=name,min,max
    ```

    ```text
    name|min|max
    noisy_1|-2.0|15.0
    noisy_2|0.0|17.0
    name|min|max
    denoised_2026_04_01|1.5|11.5
    denoised_2026_04_02|3.5|13.5
    ```

    ```sh
    r.colors map=noisy_1,denoised_2026_04_01 rules=- <<EOF
    -2 68:1:84
    2.25 59:82:139
    6.5 33:145:140
    10.75 94:201:98
    15 253:231:37
    EOF
    d.mon start=cairo output=t_rast_neighbors_average.png width=800 height=400
    d.frame -c frame=before at=0,100,0,50
    d.rast map=noisy_1
    d.text text="Before" color=white size=6 at=3,92
    d.frame -c frame=after at=0,100,50,100
    d.rast map=denoised_2026_04_01
    d.text text="After" color=white size=6 at=3,92
    d.mon stop=cairo
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=12, s=0, e=12, w=0, res=1)
    for name, shift in (("noisy_1", 0), ("noisy_2", 2)):
        tools.r_mapcalc(
            expression=f"{name} = double(col()) + {shift} + "
            "if((row() + col()) % 2 == 0, 3, -3)"
        )
    tools.t_create(
        output="noisy", title="Noisy", description="Ramp with checkerboard noise"
    )
    tools.t_register(
        input="noisy",
        maps="noisy_1,noisy_2",
        start="2026-04-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_neighbors(input="noisy", output="denoised", basename="denoised", size=3)
    print(tools.t_rast_list(input="noisy", columns="name,min,max").text)
    print(tools.t_rast_list(input="denoised", columns="name,min,max").text)
    ```

    ```text
    name|min|max
    noisy_1|-2.0|15.0
    noisy_2|0.0|17.0
    name|min|max
    denoised_2026_04_01|1.5|11.5
    denoised_2026_04_02|3.5|13.5
    ```

    ```python
    from io import StringIO

    colors = "-2 68:1:84\n2.25 59:82:139\n6.5 33:145:140\n10.75 94:201:98\n15 253:231:37\n"
    tools.r_colors(map="noisy_1,denoised_2026_04_01", rules=StringIO(colors))
    tools.d_mon(start="cairo", output="t_rast_neighbors_average.png", width=800, height=400)
    tools.d_frame(flags="c", frame="before", at=[0, 100, 0, 50])
    tools.d_rast(map="noisy_1")
    tools.d_text(text="Before", color="white", size=6, at=[3, 92])
    tools.d_frame(flags="c", frame="after", at=[0, 100, 50, 100])
    tools.d_rast(map="denoised_2026_04_01")
    tools.d_text(text="After", color="white", size=6, at=[3, 92])
    tools.d_mon(stop="cairo")
    ```

![A map with checkerboard noise before and after the average](t_rast_neighbors_average.png)

*Figure: The map `noisy_1` (left) and its average in a window of 3 by 3 cells
(right), `denoised_2026_04_01`, in the same color table.*

### Relative time and a dataset of another mapset

The dataset `model` has two maps with relative time, the ramp `step_1` with
the numbers 1 to 9 and `step_2` with 10 added, registered at 0 and 6 hours.
The new maps have the same times. With the default **suffix** `gran` they are
numbered, `m1_00001` and `m1_00002`, and so they are with **suffix** `time`;
**suffix** `num%03` gives three digits.

After `g.mapset`, the current mapset is `analysis`. The input name
`model@PERMANENT` selects the dataset of the other mapset; the new maps and
the new dataset are created in `analysis`, as their ids show.

=== "Command line"

    ```sh
    g.region n=3 s=0 e=3 w=0 res=1
    r.mapcalc expression="step_1 = double((row() - 1) * 3 + col())"
    r.mapcalc expression="step_2 = double((row() - 1) * 3 + col()) + 10"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output every six hours"
    t.register -i input=model maps=step_1,step_2 start=0 increment=6 unit=hours
    t.rast.neighbors input=model output=m1 basename=m1
    t.rast.list input=m1 columns=name,start_time,end_time,min,max
    t.rast.neighbors input=model output=m2 basename=m2 suffix=time
    t.rast.list input=m2 columns=name,start_time
    t.rast.neighbors input=model output=m3 basename=m3 suffix=num%03
    t.rast.list input=m3 columns=name,start_time
    ```

    ```text
    name|start_time|end_time|min|max
    m1_00001|0|6|3.0|7.0
    m1_00002|6|12|13.0|17.0
    name|start_time
    m2_00001|0
    m2_00002|6
    name|start_time
    m3_001|0
    m3_002|6
    ```

    ```sh
    g.mapset -c mapset=analysis
    t.rast.neighbors input=model@PERMANENT output=m4 basename=m4
    t.rast.list input=m4 columns=id,mapset,start_time
    ```

    ```text
    id|mapset|start_time
    m4_00001@analysis|analysis|0
    m4_00002@analysis|analysis|6
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=3, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="step_1 = double((row() - 1) * 3 + col())")
    tools.r_mapcalc(expression="step_2 = double((row() - 1) * 3 + col()) + 10")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output every six hours",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=6, unit="hours", flags="i"
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
    m1_00001|0|6|3.0|7.0
    m1_00002|6|12|13.0|17.0
    name|start_time
    m2_00001|0
    m2_00002|6
    name|start_time
    m3_001|0
    m3_002|6
    ```

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.t_rast_neighbors(input="model@PERMANENT", output="m4", basename="m4")
    print(tools.t_rast_list(input="m4", columns="id,mapset,start_time").text)
    ```

    ```text
    id|mapset|start_time
    m4_00001@analysis|analysis|0
    m4_00002@analysis|analysis|6
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[d.frame](d.frame.md), [d.rast](d.rast.md), [d.text](d.text.md),
[g.mapset](g.mapset.md), [g.region](g.region.md), [r.colors](r.colors.md),
[r.neighbors](r.neighbors.md), [r.out.ascii](r.out.ascii.md),
[r.support](r.support.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.aggregate](t.rast.aggregate.md), [t.rast.extract](t.rast.extract.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
