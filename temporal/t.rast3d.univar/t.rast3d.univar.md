## DESCRIPTION

*t.rast3d.univar* calculates univariate statistics of each 3D raster map
registered in a space time 3D raster dataset and prints one line of statistics
per map, ordered by start time. It runs *[r3.univar](r3.univar.md)* for every
map, so the statistics are those of *r3.univar*: they are taken from the cells
(voxels) of the current 3D computational region and count only cells with a
value (non-null cells). See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time raster datasets have their own tool,
*[t.rast.univar](t.rast.univar.md)*, space time vector datasets
*[t.vect.univar](t.vect.univar.md)*. Its manual page explains the statistics
for 2D maps in the same words; this page differs in the options that
*t.rast3d.univar* does not have, in the 3D region, and in the zones.

The option **input** names the space time 3D raster dataset. Each line of the
output starts with three columns that name the map:

- `id`, the name of the map with its mapset, such as `soil_1@PERMANENT`;
- `start` and `end`, the start and end time of the map; the end of a map
  registered as a time instance is `None`.

The statistics follow:

- `non_null_cells` and `null_cells`: the number of cells with and without a
  value;
- `min`, `max` and `range`, the smallest and the largest value and their
  difference;
- `mean` and `mean_of_abs`, the mean of the values and the mean of their
  absolute values;
- `stddev` and `variance`: the variance is the sum of the squared deviations
  from the mean divided by the number of non-null cells (the population
  variance), the standard deviation is its square root;
- `coeff_var`, the coefficient of variation in percent, 100 times the
  standard deviation divided by the mean. It grows without bound when the mean
  approaches 0, and it is negative for a negative mean;
- `sum` and `sum_abs`, the sum of the values and of their absolute values.

The flag **-e** adds the extended statistics `first_quartile`, `median`,
`third_quartile` and the 90th percentile `percentile_90`. *r3.univar* finds a
percentile p in the sorted values of the n non-null cells: it takes the value
at position `n * p / 100 - 0.5` with the fractional part dropped, counting
from 0, so the percentile 0 is the minimum. The quartiles follow the same rule
with p = 25 and p = 75. The median is the middle value,
or the mean of the two middle values when n is even, so it can differ from
the 50th percentile. The option **percentile** replaces the 90th percentile by
one or more percentiles from 0 to 100, separated by commas; it requires
**-e**. Each percentile gets a column of its own, named after it, with an
underscore for a decimal point: `percentile=97.5` gives `percentile_97_5`.

Two options select the maps of the dataset, and they can be combined:

- the option **where** takes an SQL condition on the registered maps, for
  instance on `start_time` or `name`;
- the option **region_relation** keeps the maps that have a spatial relation
  with the current 3D computational region: `overlaps` keeps the maps that
  share at least a part of the region, `contains` the maps that cover the
  whole region, and `is_contained` the maps that lie inside the region. A map
  with the extent of the region both contains it and is contained in it. The
  option only selects maps; it does not change the cells the statistics are
  taken from.

The statistics of every map are taken in the current 3D computational region:
cells of the map outside the region are not counted, and cells of the region
outside the map are null cells. Unlike *t.rast.univar*, *t.rast3d.univar* has
no flag to take the statistics in the region of each map instead.

The option **zones** names a 3D raster map whose integer values divide the
region into zones. *t.rast3d.univar* then prints one line per map and zone,
with the columns `zone` (the value) and `label` (the category label of the
zone, empty in the example below, where the zone map has none) after the three
columns of the map. **zones** takes a single 3D raster map, not a space time
dataset; the same zones apply to every map.

The option **nprocs** sets the number of maps that are processed at the same
time. Its default is the variable `NPROCS` of the session, if it is set with
*g.gisenv*, and 0 otherwise. 0 uses all CPU cores, a negative number leaves
that many cores unused. The output is the same, in the same order, for any value.

The option **format** chooses the form of the output:

- `plain` (the default) separates the columns with a vertical bar `|`;
- `csv` separates them with a comma, or with another single character given
  in **separator**;
- `json` prints a list with one object per map, or with **zones** one per
  map and zone. The keys are the column names, except where they follow
  *r3.univar*: `n` instead of `non_null_cells`, `zone_label` instead of
  `label`, the additional key `cells` for the number of all cells, and no
  `sum_abs`. With **-e**, the percentiles are the list `percentiles` of
  objects with the keys `percentile` and `value`, instead of the columns
  `percentile_90` and so on. A value that does not exist is `null`. Every
  object has the key `semantic_label`, which is `null` for 3D maps; the formats
  `plain` and `csv` have no such column.

The option **separator** sets the separator of the formats `plain` and `csv`.
The flag **-s** leaves out the line with the column names; it takes the place
of the flag **-u** of *t.rast.univar*. The format `json` always names the
values and accepts neither **separator** nor **-s**.

The option **output** writes the statistics to a file instead of the standard
output; `output=-` is the standard output. An existing file is replaced only
with **--overwrite**.

## NOTES

The current 3D computational region decides which cells are counted, so it
needs a vertical extent and a 3D resolution (the options **t**, **b** and
**res3** of *g.region*). A map that does not reach into the region has only
null cells there; its `min`, `max` and all further statistics are `nan` in the
formats `plain` and `csv` and `null` in the format `json`. A map that lies
above or below the region counts as outside, too. The region is the same for
all maps, so maps with different extents can have different numbers of
non-null cells, as the example with the cubes below shows.

In a dataset with relative time, `start` and `end` are numbers of the time
unit of the dataset, printed without the unit: a map registered from 0 to 6
hours shows `0` and `6`, as the first example shows.

*t.rast3d.univar* only reads, so it works on a dataset of another mapset as
well. The name with the mapset (`input=soil@PERMANENT`) selects it; a name
without a mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The last example shows this.

The 3D raster mask set with *[r3.mask](r3.mask.md)* has no effect on the
statistics: *r3.univar* does not read it and counts the cells that the mask
would exclude. To leave cells out, set them to null in the maps themselves, for
instance with *[r3.mapcalc](r3.mapcalc.md)* and `if(layers == 2, null(), soil)`,
or read the lines of the zones that are wanted (see **zones** and the example
with the layers).

If no map is selected, for instance because the condition in **where**
matches none, *t.rast3d.univar* prints nothing in the formats `plain` and
`csv`, not even the line with the column names. The format `json` prints an
empty list `[]`.

The option **zones** also takes a floating point map. *r3.univar* then rounds
each value to the nearest integer, halves away from zero, instead of
refusing the map, so the zone of the value 2.5 is 3.

The format `csv` refuses a separator of more than one character, the format
`json` refuses **separator** and **-s**. **percentile** without **-e** is
refused by the parser.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Statistics of each map of a dataset

The region has two rows, three columns and two layers of the size 1, so each
map has 12 cells. The helper map `voxel_number` numbers the cells from 1 to
12, layer by layer from the bottom and row by row within a layer, so each map
is simple to follow:

- `soil_1` holds -2, -1, 0, 1, 2, 3 in the lower layer and 4 to 9 in the upper
  layer;
- `soil_2` holds the numbers 1 to 12;
- `soil_3` holds `voxel_number + 3` for the cells 1, 2, 4, 5, 7, 8, 10 and 11,
  that is 4, 5, 7, 8, 10, 11, 13 and 14, and nothing in the eastern column, as
  if a sensor had failed there.

The maps are registered as daily intervals starting on 1 March 2026.
*t.rast3d.univar* processes two maps at the same time here (**nprocs**); the
output does not depend on it.

The second block makes the dataset `model` with relative time: two model
steps of 6 hours each, with the constant values 1 and 2. Their `start` and
`end` are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 t=2 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="voxel_number = (depth() - 1) * 6 + (row() - 1) * 3 + col()"
    r3.mapcalc expression="soil_1 = voxel_number - 3"
    r3.mapcalc expression="soil_2 = voxel_number"
    r3.mapcalc expression="soil_3 = if(col() == 3, null(), voxel_number + 3)"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in degrees Celsius"
    t.register -i type=raster_3d input=soil \
        maps=soil_1,soil_2,soil_3 start=2026-03-01 increment="1 day"
    t.rast3d.univar input=soil nprocs=2
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_1@PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00|12|0|-2|9|11|3.5|4|3.45205252953466|11.9166666666667|98.6300722724189|42|48
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    soil_3@PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00|8|4|4|14|10|9|9|3.39116499156263|11.5|37.6796110173626|72|72
    ```

    ```sh
    r3.mapcalc expression="step_1 = 1"
    r3.mapcalc expression="step_2 = 2"
    t.create type=str3ds output=model temporaltype=relative title="Model" \
        description="Model output per step of 6 hours"
    t.register -i type=raster_3d input=model maps=step_1,step_2 \
        start=0 increment=6 unit=hours
    t.rast3d.univar input=model
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    step_1@PERMANENT|0|6|12|0|1|1|0|1|1|0|0|0|12|12
    step_2@PERMANENT|6|12|12|0|2|2|0|2|2|0|0|0|24|24
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, t=2, b=0, res=1, res3=1, tbres=1)
    tools.r3_mapcalc(
        expression="voxel_number = (depth() - 1) * 6 + (row() - 1) * 3 + col()"
    )
    tools.r3_mapcalc(expression="soil_1 = voxel_number - 3")
    tools.r3_mapcalc(expression="soil_2 = voxel_number")
    tools.r3_mapcalc(expression="soil_3 = if(col() == 3, null(), voxel_number + 3)")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in degrees Celsius",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2,soil_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast3d_univar(input="soil", nprocs=2).text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_1@PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00|12|0|-2|9|11|3.5|4|3.45205252953466|11.9166666666667|98.6300722724189|42|48
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    soil_3@PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00|8|4|4|14|10|9|9|3.39116499156263|11.5|37.6796110173626|72|72
    ```

    ```python
    tools.r3_mapcalc(expression="step_1 = 1")
    tools.r3_mapcalc(expression="step_2 = 2")
    tools.t_create(
        type="str3ds",
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step of 6 hours",
    )
    tools.t_register(
        type="raster_3d",
        input="model",
        maps="step_1,step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast3d_univar(input="model").text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    step_1@PERMANENT|0|6|12|0|1|1|0|1|1|0|0|0|12|12
    step_2@PERMANENT|6|12|12|0|2|2|0|2|2|0|0|0|24|24
    ```

The output reads line by line:

- `soil_2` has twelve values, 1 to 12: the mean is 78 / 12 = 6.5, the range
  12 - 1 = 11. The squared deviations from the mean add up to 143, so the
  variance is 143 / 12 = 11.9166..., the standard deviation its square root
  3.4520..., and the coefficient of variation `100 * 3.4520 / 6.5` = 53.10...
- `soil_1` holds the same values minus 3, so range, variance and standard
  deviation are those of `soil_2`. Its values add up to 42 and give the mean
  3.5, while their absolute values add up to 48 and give `mean_of_abs` 4.
- `soil_3` has eight non-null cells and four null cells; its mean is
  72 / 8 = 9.

### Calculate extended statistics and percentiles

The flag **-e** adds the quartiles, the median and the 90th percentile. The
twelve values 1 to 12 of `soil_2` give the first quartile at position
`12 * 25 / 100 - 0.5` = 2.5, which becomes 2 (the value 3), the third quartile
at position 8.5, which becomes 8 (the value 9), and the 90th percentile at
position 10.3, which becomes 10 (the value 11). The median is the mean of the
two middle values 6 and 7.

The option **percentile** replaces the 90th percentile by the listed ones.
For `soil_2`, the 10th percentile is at position 0.7 (the value 1), the 50th
at position 5.5 (the value 6) and the 95th at position 10.9 (the value 11).
The 50th percentile 6 is not the median 6.5: the median takes the mean of the
two middle values, the percentile one value. The option **where** keeps
`soil_2` in the first command and `soil_3`, which starts on the third of
March, in the second command.

=== "Command line"

    ```sh
    t.rast3d.univar -e input=soil percentile=10,50,95 \
        where="name = 'soil_2'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78|3|6.5|9|1|6|11
    ```

    ```sh
    t.rast3d.univar -e input=soil where="start_time >= '2026-03-03'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    soil_3@PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00|8|4|4|14|10|9|9|3.39116499156263|11.5|37.6796110173626|72|72|5|9|11|13
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast3d_univar(
        input="soil",
        percentile=[10, 50, 95],
        where="name = 'soil_2'",
        flags="e",
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78|3|6.5|9|1|6|11
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="soil", where="start_time >= '2026-03-03'", flags="e"
    )
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    soil_3@PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00|8|4|4|14|10|9|9|3.39116499156263|11.5|37.6796110173626|72|72|5|9|11|13
    ```

### Statistics per zone

The 3D map `layers` holds the number of the layer: 1 in the lower and 2 in
the upper layer. With **zones**, each map gets one line per zone. For `soil_2`,
the lower layer holds 1 to 6 with the mean 3.5, the upper layer 7 to 12 with
the mean 9.5. The zone map has no category labels, so `label` is empty. With
**format** `json`, each zone is an object of its own, and the category label
has the name `zone_label`; it is the empty text here, not `null`.

=== "Command line"

    ```sh
    r3.mapcalc expression="layers = depth()"
    t.rast3d.univar input=soil zones=layers where="name = 'soil_2'"
    ```

    ```text
    id|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|1||6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|2||6|0|7|12|5|9.5|9.5|1.70782512765993|2.91666666666667|17.9771066069467|57|57
    ```

    ```sh
    t.rast3d.univar input=soil zones=layers format=json \
        where="name = 'soil_2'" | grep -E '"(zone|zone_label|mean)"'
    ```

    ```text
            "zone": 1,
            "zone_label": "",
            "mean": 3.5,
            "zone": 2,
            "zone_label": "",
            "mean": 9.5,
    ```

=== "Python (grass.tools)"

    ```python
    tools.r3_mapcalc(expression="layers = depth()")
    result = tools.t_rast3d_univar(input="soil", zones="layers", where="name = 'soil_2'")
    print(result.text)
    ```

    ```text
    id|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|1||6|0|1|6|5|3.5|3.5|1.70782512765993|2.91666666666667|48.7950036474267|21|21
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|2||6|0|7|12|5|9.5|9.5|1.70782512765993|2.91666666666667|17.9771066069467|57|57
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="soil", zones="layers", format="json", where="name = 'soil_2'"
    )
    for stats in result.json:
        print(f"zone {stats['zone']} ({stats['zone_label']!r}): mean {stats['mean']}")
    ```

    ```text
    zone 1 (''): mean 3.5
    zone 2 (''): mean 9.5
    ```

### Choose the output format

The option **separator** sets another separator, and the flag **-s** leaves
out the line with the column names, for instance to append the lines to a
table that has them already. With **format** `csv`, the columns are separated
by commas, and the option **output** writes the statistics to a file. With
**format** `json`, *t.rast3d.univar* prints a list with one object per map;
here for `soil_2` with the extended statistics and two percentiles. The key
`semantic_label` is `null`. In Python, the attribute `json` of the result
holds this list, and the example prints the mean, the median and the
percentiles from it.

=== "Command line"

    ```sh
    t.rast3d.univar -s input=soil separator=";"
    ```

    ```text
    soil_1@PERMANENT;2026-03-01 00:00:00;2026-03-02 00:00:00;12;0;-2;9;11;3.5;4;3.45205252953466;11.9166666666667;98.6300722724189;42;48
    soil_2@PERMANENT;2026-03-02 00:00:00;2026-03-03 00:00:00;12;0;1;12;11;6.5;6.5;3.45205252953466;11.9166666666667;53.1085004543794;78;78
    soil_3@PERMANENT;2026-03-03 00:00:00;2026-03-04 00:00:00;8;4;4;14;10;9;9;3.39116499156263;11.5;37.6796110173626;72;72
    ```

    ```sh
    t.rast3d.univar input=soil format=csv output=soil.csv
    cat soil.csv
    ```

    ```text
    id,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    soil_1@PERMANENT,2026-03-01 00:00:00,2026-03-02 00:00:00,12,0,-2,9,11,3.5,4,3.45205252953466,11.9166666666667,98.6300722724189,42,48
    soil_2@PERMANENT,2026-03-02 00:00:00,2026-03-03 00:00:00,12,0,1,12,11,6.5,6.5,3.45205252953466,11.9166666666667,53.1085004543794,78,78
    soil_3@PERMANENT,2026-03-03 00:00:00,2026-03-04 00:00:00,8,4,4,14,10,9,9,3.39116499156263,11.5,37.6796110173626,72,72
    ```

    ```sh
    t.rast3d.univar -e input=soil format=json percentile=50,90 \
        where="name = 'soil_2'"
    ```

    ```text
    [
        {
            "id": "soil_2@PERMANENT",
            "semantic_label": null,
            "start": "2026-03-02 00:00:00",
            "end": "2026-03-03 00:00:00",
            "n": 12,
            "null_cells": 0,
            "cells": 12,
            "min": 1,
            "max": 12,
            "range": 11,
            "mean": 6.5,
            "mean_of_abs": 6.5,
            "stddev": 3.452052529534663,
            "variance": 11.916666666666666,
            "coeff_var": 53.108500454379424,
            "sum": 78,
            "first_quartile": 3,
            "median": 6.5,
            "third_quartile": 9,
            "percentiles": [
                {
                    "percentile": 50,
                    "value": 6
                },
                {
                    "percentile": 90,
                    "value": 11
                }
            ]
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast3d_univar(input="soil", separator=";", flags="s")
    print(result.text)
    ```

    ```text
    soil_1@PERMANENT;2026-03-01 00:00:00;2026-03-02 00:00:00;12;0;-2;9;11;3.5;4;3.45205252953466;11.9166666666667;98.6300722724189;42;48
    soil_2@PERMANENT;2026-03-02 00:00:00;2026-03-03 00:00:00;12;0;1;12;11;6.5;6.5;3.45205252953466;11.9166666666667;53.1085004543794;78;78
    soil_3@PERMANENT;2026-03-03 00:00:00;2026-03-04 00:00:00;8;4;4;14;10;9;9;3.39116499156263;11.5;37.6796110173626;72;72
    ```

    ```python
    from pathlib import Path

    tools.t_rast3d_univar(input="soil", format="csv", output="soil.csv")
    print(Path("soil.csv").read_text(), end="")
    ```

    ```text
    id,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    soil_1@PERMANENT,2026-03-01 00:00:00,2026-03-02 00:00:00,12,0,-2,9,11,3.5,4,3.45205252953466,11.9166666666667,98.6300722724189,42,48
    soil_2@PERMANENT,2026-03-02 00:00:00,2026-03-03 00:00:00,12,0,1,12,11,6.5,6.5,3.45205252953466,11.9166666666667,53.1085004543794,78,78
    soil_3@PERMANENT,2026-03-03 00:00:00,2026-03-04 00:00:00,8,4,4,14,10,9,9,3.39116499156263,11.5,37.6796110173626,72,72
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="soil",
        format="json",
        percentile=[50, 90],
        where="name = 'soil_2'",
        flags="e",
    )
    for stats in result.json:
        percentiles = {item["percentile"]: item["value"] for item in stats["percentiles"]}
        print(
            f"{stats['id']}: mean {stats['mean']}, median {stats['median']},"
            f" percentiles {percentiles}"
        )
    ```

    ```text
    soil_2@PERMANENT: mean 6.5, median 6.5, percentiles {50: 6, 90: 11}
    ```

### Maps with extents of their own

The dataset `cubes` holds four maps with constant values on cubes of their
own; the current region is the cube from (0, 0, 0) to (4, 4, 4) with 64 cells:

- `cube_1` covers the cube from (-1, -1, -1) to (5, 5, 5) and so the whole
  region;
- `cube_2` lies inside the region, from (1, 1, 1) to (3, 3, 3);
- `cube_3` reaches from (2, 2, 2) to (6, 6, 6) and shares 8 cells with the
  region;
- `cube_4` lies outside, from (10, 10, 10) to (12, 12, 12).

The commands print the columns `id`, `non_null_cells`, `null_cells` and `min`
only: on the command line, *cut* keeps the first, fourth, fifth and sixth
column; in Python, the function `print_columns()` picks them from the plain
text.

1. By default, the cells are counted in the current region: `cube_1` has 64
   non-null cells there, `cube_2` and `cube_3` have 8, and `cube_4` none. As
   `cube_4` has no value in the region, its `min` is `nan`.
2. **region_relation** selects maps by their relation to the current region:
   `overlaps` keeps all but `cube_4`, `contains` only `cube_1`, which covers
   the region, and `is_contained` only `cube_2`, which lies inside it.
3. **region_relation** and **where** work together: of the maps that overlap
   the region, the condition keeps those that start on 2 July 2026 or later.
4. With **format** `json`, the statistics of `cube_4` that do not exist are
   `null`.

=== "Command line"

    ```sh
    for cube in "cube_1 -1 5 10" "cube_2 1 3 20" \
        "cube_3 2 6 30" "cube_4 10 12 40"; do
        set -- $cube
        g.region s=$2 n=$3 w=$2 e=$3 b=$2 t=$3 res=1 res3=1
        r3.mapcalc expression="$1 = $4"
    done
    t.create type=str3ds output=cubes title="Cubes" \
        description="Cubes with extents of their own"
    t.register -i type=raster_3d input=cubes \
        maps=cube_1,cube_2,cube_3,cube_4 start=2026-07-01 increment="1 day"
    g.region s=0 n=4 w=0 e=4 b=0 t=4 res=1 res3=1
    t.rast3d.univar input=cubes | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    cube_4@PERMANENT|0|64|nan
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=overlaps | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=contains | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=is_contained | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@PERMANENT|8|56|20
    ```

    ```sh
    t.rast3d.univar input=cubes region_relation=overlaps \
        where="start_time >= '2026-07-02'" | cut -d"|" -f1,4-6
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    ```

    ```sh
    t.rast3d.univar input=cubes format=json where="name = 'cube_4'" |
        grep -E '"(n|null_cells|min|mean)"'
    ```

    ```text
            "n": 0,
            "null_cells": 64,
            "min": null,
            "mean": null,
    ```

=== "Python (grass.tools)"

    ```python
    for name, low, high, value in (
        ("cube_1", -1, 5, 10),
        ("cube_2", 1, 3, 20),
        ("cube_3", 2, 6, 30),
        ("cube_4", 10, 12, 40),
    ):
        tools.g_region(s=low, n=high, w=low, e=high, b=low, t=high, res=1, res3=1)
        tools.r3_mapcalc(expression=f"{name} = {value}")
    tools.t_create(
        type="str3ds",
        output="cubes",
        title="Cubes",
        description="Cubes with extents of their own",
    )
    tools.t_register(
        type="raster_3d",
        input="cubes",
        maps="cube_1,cube_2,cube_3,cube_4",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(s=0, n=4, w=0, e=4, b=0, t=4, res=1, res3=1)


    def print_columns(result):
        for line in result.text.splitlines():
            columns = line.split("|")
            print("|".join(columns[index] for index in (0, 3, 4, 5)))


    print_columns(tools.t_rast3d_univar(input="cubes"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    cube_4@PERMANENT|0|64|nan
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="overlaps"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="contains"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_1@PERMANENT|64|0|10
    ```

    ```python
    print_columns(tools.t_rast3d_univar(input="cubes", region_relation="is_contained"))
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@PERMANENT|8|56|20
    ```

    ```python
    result = tools.t_rast3d_univar(
        input="cubes", region_relation="overlaps", where="start_time >= '2026-07-02'"
    )
    print_columns(result)
    ```

    ```text
    id|non_null_cells|null_cells|min
    cube_2@PERMANENT|8|56|20
    cube_3@PERMANENT|8|56|30
    ```

    ```python
    result = tools.t_rast3d_univar(input="cubes", format="json", where="name = 'cube_4'")
    for stats in result.json:
        print(
            f"n: {stats['n']}, null_cells: {stats['null_cells']},"
            f" min: {stats['min']}, mean: {stats['mean']}"
        )
    ```

    ```text
    n: 0, null_cells: 64, min: None, mean: None
    ```

### Use a dataset of another mapset

*t.rast3d.univar* reads a dataset of another mapset. The example creates the
mapset `analysis` and switches to it; the dataset `soil` stays in the mapset
`PERMANENT` and is named with its mapset. The region of the new mapset is set
to the one of the maps. In the second block, *g.mapsets* shows that
`PERMANENT` is in the search path of the new mapset, so the name `soil` without
a mapset finds the same dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=3 w=0 t=2 b=0 res=1 res3=1 tbres=1
    t.rast3d.univar input=soil@PERMANENT where="name = 'soil_2'"
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    ```

    ```sh
    g.mapsets -p
    t.rast3d.univar input=soil where="name = 'soil_2'"
    ```

    ```text
    analysis PERMANENT
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=2, s=0, e=3, w=0, t=2, b=0, res=1, res3=1, tbres=1)
    result = tools.t_rast3d_univar(input="soil@PERMANENT", where="name = 'soil_2'")
    print(result.text)
    ```

    ```text
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    result = tools.t_rast3d_univar(input="soil", where="name = 'soil_2'")
    print(result.text)
    ```

    ```text
    analysis PERMANENT
    id|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    soil_2@PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00|12|0|1|12|11|6.5|6.5|3.45205252953466|11.9166666666667|53.1085004543794|78|78
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.gisenv](g.gisenv.md), [g.mapsets](g.mapsets.md), [g.region](g.region.md),
[r3.mapcalc](r3.mapcalc.md), [r3.mask](r3.mask.md),
[r3.univar](r3.univar.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.univar](t.rast.univar.md), [t.register](t.register.md),
[t.vect.univar](t.vect.univar.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture  
Stefan Blumentrath (support for zones)
