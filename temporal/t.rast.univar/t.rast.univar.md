## DESCRIPTION

*t.rast.univar* calculates univariate statistics of each raster map
registered in a space time raster dataset and prints one line of statistics
per map, ordered by start time. It runs *[r.univar](r.univar.md)* for every
map, so the statistics are those of *r.univar*: they are taken from the cells
of the current computational region and count only cells with a value
(non-null cells). See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. Space time 3D raster datasets have their own tool,
*[t.rast3d.univar](t.rast3d.univar.md)*, space time vector datasets
*[t.vect.univar](t.vect.univar.md)*.

The option **input** names the space time raster dataset. Each line of the
output starts with four columns that name the map:

- `id`, the name of the map with its mapset, such as
  `precipitation_monthly_2020_01@t_rast_univar`;
- `semantic_label`, the semantic label of the map, empty if it has none;
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
`third_quartile` and the 90th percentile `percentile_90`. *r.univar* finds a
percentile p in the sorted values of the n non-null cells: it takes the value
at position `n * p / 100 - 0.5` with the fractional part dropped, counting
from 0, so the percentile 0 is the minimum. The quartiles follow the same rule
with p = 25 and p = 75. The median is the middle value,
or the mean of the two middle values when n is even, so it can differ from
the 50th percentile. The option **percentile** replaces the 90th percentile by
one or more percentiles from 0 to 100, separated by commas; it requires
**-e**. Each percentile gets a column of its own, named after it, with an
underscore for a decimal point: `percentile=97.5` gives `percentile_97_5`.

Three ways select the maps of the dataset, and they can be combined:

- the option **where** takes an SQL condition on the registered maps, for
  instance on `start_time` or `name`;
- a semantic label after the name of the dataset, `input=name.label`, keeps
  only the maps with this label;
- the option **region_relation** keeps the maps that have a spatial relation
  with the current computational region: `overlaps` keeps the maps that share
  at least a part of the region, `contains` the maps that cover the whole
  region, and `is_contained` the maps that lie inside the region. A map with
  the extent of the region both contains it and is contained in it. The
  option only selects maps; it does not change the cells the statistics are
  taken from.

Without the flag **-r**, the statistics of every map are taken in the current
computational region: cells of the map outside the region are not counted,
and cells of the region outside the map are null cells. With **-r**, the
statistics of each map are taken in the region of that map, so every cell of
the map is counted, whatever the current region. This holds together with
**zones** as well; the zone map is then read in the region of each map, too.

The option **zones** names an integer (CELL) raster map whose categories
divide the region into zones. *t.rast.univar* then prints one line per map
and zone, with the columns `zone` (the category) and `label` (the category
label) after the four columns of the map. A zone without any cell in the
region gets no line. **zones** takes a single raster map, not a space time
dataset; the same zones apply to every map.

The option **granularity** gives statistics per granule instead of per map.
*t.rast.univar* runs *r.univar* once for each granule with all maps of the
granule, so the statistics are taken from the cells of these maps together,
and prints one line per granule. The granules are those of
*[t.rast.aggregate](t.rast.aggregate.md)*: in absolute time the granularity is
one number and one unit, such as `3 months`, in relative time an integer in
the unit of the dataset. The first granule starts at the start of the first
selected map, moved back to the beginning of the unit of the granularity, and
the granules follow each other without gaps up to the one that holds the last
map. A granule without a map gets no line. The selection by **where**, by a
semantic label or by **region_relation** comes first: only the selected maps
are assigned to the granules.

The option **sampling** sets which maps belong to a granule, with the temporal
relations of *t.rast.aggregate*, read from the granule. `contains`, the
default, takes the maps that lie within the granule; `related` takes every map
that shares time with the granule, so a map that crosses the border of two
granules counts in both. Several relations are separated by commas.
**sampling** requires **granularity**.

With **granularity**, `start` and `end` are those of the granule, the column
`id` lists the maps of the granule, separated by commas, and `semantic_label`
stays empty. The format `csv` puts this list in double quotes if the
separator is a comma. The format `json` has the key `maps` with the list of
the maps instead of `id`, and no `semantic_label`. With **zones**, each
granule gets one line per zone, taken from all maps of the granule.

The option **nprocs** sets the number of maps, or with **granularity** the
number of granules, that are processed at the same time. Its default is the
variable `NPROCS` of the session, if it is set with *g.gisenv*, and 0
otherwise. 0 uses all CPU cores, a negative number leaves
that many cores unused. The output is the same, in the same order, for any value.

The option **format** chooses the form of the output:

- `plain` (the default) separates the columns with a vertical bar `|`;
- `csv` separates them with a comma, or with another single character given
  in **separator**;
- `json` prints a list with one object per map, or with **zones** one per
  map and zone. The keys are the column names, except where they follow
  *r.univar*: `n` instead of `non_null_cells`, `zone_label` instead of
  `label`, the additional key `cells` for the number of all cells, and no
  `sum_abs`. With **-e**, the percentiles are the list `percentiles` of
  objects with the keys `percentile` and `value`, instead of the columns
  `percentile_90` and so on. A value that does not exist, such as the
  semantic label of a map without one, is `null`.

The option **separator** sets the separator of the formats `plain` and `csv`.
The flag **-u** leaves out the line with the column names. The format `json`
always names the values and accepts neither **separator** nor **-u**.

The option **output** writes the statistics to a file instead of the standard
output; `output=-` is the standard output. An existing file is replaced only
with **--overwrite**.

## NOTES

The current computational region decides which cells are counted, unless
**-r** is given. A map that does not reach into the region has only null
cells there; its `min`, `max` and all further statistics are `nan` in the
formats `plain` and `csv` and `null` in the format `json`. The raster mask is
respected: cells outside the mask are null cells. Region and mask are the
same for all maps, so maps with different extents can have different numbers
of non-null cells, as the example with the scenes below shows.

In a dataset with relative time, `start` and `end` are numbers of the time
unit of the dataset, printed without the unit: a map registered from 0 to 6
hours shows `0` and `6`, as the first example shows.

*t.rast.univar* only reads, so it works on a dataset of another mapset as
well. The name with the mapset
(`input=precipitation_monthly@t_rast_univar`) selects it;
a name without a mapset is searched in the mapsets of the search path (see
*[g.mapsets](g.mapsets.md)*). The example at the end shows this.

If no map is selected, for instance because the condition in **where**
matches none, *t.rast.univar* prints nothing in the formats `plain` and
`csv`, not even the line with the column names. The format `json` prints an
empty list `[]`.

The option **zones** takes a map of type CELL; *t.rast.univar* stops with the
error "Zoning raster must be of type CELL" for a floating point map.

The format `csv` refuses a separator of more than one character, the format
`json` refuses **separator** and **-u**. **percentile** without **-e** is
refused by the parser.

**granularity** refuses the flag **-r**: the maps of a granule are computed
together in one run of *r.univar* and have no common region of their own. It
also refuses the format `plain` with the separator `,`, because the list of
maps in the column `id` could then not be told apart from the other columns;
the format `csv` quotes the list. **sampling** without **granularity** is
refused by the parser. A wrong granularity, such as `0 months`, is refused
with the message of *t.rast.aggregate*. All these refusals come before
anything is written. If no map belongs to any granule, *t.rast.univar* warns,
names the granularity and the sampling, and prints what it prints when no map
is selected.

The names of all maps of a granule go into one argument of *r.univar*. If
the system refuses so long a command line (on Linux one argument holds at
most 128 KiB, on Windows the whole command line 32,767 characters),
*t.rast.univar* stops with a message that names the start of the granule; a
smaller granularity puts fewer maps into each granule. The file of
**output** then holds at most the line with the column names.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_univar` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset,
except the last, which creates a second mapset with the same region. The
examples that show how the statistics, the selection and the regions work use
maps with small constant values, so that the results can be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_univar -->

<!-- markdownlint-disable MD046 -->

### Statistics of each map of a dataset

The dataset `precipitation_monthly` holds twelve maps of the monthly
precipitation sum in 2020, in whole millimeters. They are generated, not
measured: the monthly normals of the 136 climate stations in the vector map
`precip_30ynormals` are interpolated with *v.surf.idw* for each month and
multiplied by an assumed factor for a wet year (1.2 in January, 1.7 in
February and so on), so the pattern changes from month to month. Each map is an
interval of one month, and cells outside North Carolina are null. Whole
millimeters are integers, so the sums, the means and the standard deviations
below are the same on every system.

The first command selects the maps of the first quarter to keep the output
short. *t.rast.univar* processes two maps at the same time here (**nprocs**);
the output does not depend on it.

The second block makes the dataset `runoff` with relative time: two model steps
of 6 hours each, with the constant values 1 and 2 in every cell of the region.
Their `start` and `end` are numbers of hours, printed without the unit.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_univar
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
    t.rast.univar input=precipitation_monthly nprocs=2 \
        where="start_time < '2020-04-01'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_01@t_rast_univar||2020-01-01 00:00:00|2020-02-01 00:00:00|136502|144563|94|249|155|136.209755168422|136.209755168422|16.7726752415963|281.322634760059|12.3138575653829|18592904|18592904
    precipitation_monthly_2020_02@t_rast_univar||2020-02-01 00:00:00|2020-03-01 00:00:00|136502|144563|133|309|176|160.129097009568|160.129097009568|22.9221610385697|525.425466678125|14.3148006618686|21857942|21857942
    precipitation_monthly_2020_03@t_rast_univar||2020-03-01 00:00:00|2020-04-01 00:00:00|136502|144563|88|212|124|105.972689044849|105.972689044849|13.9251048404704|193.908544818092|13.1402769581293|14465484|14465484
    ```

    ```sh
    r.mapcalc expression="runoff_1 = 1"
    r.mapcalc expression="runoff_2 = 2"
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model step of 6 hours"
    t.register -i input=runoff maps=runoff_1,runoff_2 start=0 increment=6 unit=hours
    t.rast.univar input=runoff
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    runoff_1@t_rast_univar||0|6|281065|0|1|1|0|1|1|0|0|0|281065|281065
    runoff_2@t_rast_univar||6|12|281065|0|2|2|0|2|2|0|0|0|562130|562130
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_univar")
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
    result = tools.t_rast_univar(
        input="precipitation_monthly", nprocs=2, where="start_time < '2020-04-01'"
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_01@t_rast_univar||2020-01-01 00:00:00|2020-02-01 00:00:00|136502|144563|94|249|155|136.209755168422|136.209755168422|16.7726752415963|281.322634760059|12.3138575653829|18592904|18592904
    precipitation_monthly_2020_02@t_rast_univar||2020-02-01 00:00:00|2020-03-01 00:00:00|136502|144563|133|309|176|160.129097009568|160.129097009568|22.9221610385697|525.425466678125|14.3148006618686|21857942|21857942
    precipitation_monthly_2020_03@t_rast_univar||2020-03-01 00:00:00|2020-04-01 00:00:00|136502|144563|88|212|124|105.972689044849|105.972689044849|13.9251048404704|193.908544818092|13.1402769581293|14465484|14465484
    ```

    ```python
    tools.r_mapcalc(expression="runoff_1 = 1")
    tools.r_mapcalc(expression="runoff_2 = 2")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model step of 6 hours",
    )
    tools.t_register(
        input="runoff",
        maps="runoff_1,runoff_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    print(tools.t_rast_univar(input="runoff").text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    runoff_1@t_rast_univar||0|6|281065|0|1|1|0|1|1|0|0|0|281065|281065
    runoff_2@t_rast_univar||6|12|281065|0|2|2|0|2|2|0|0|0|562130|562130
    ```

The output reads line by line:

- Each map of the first quarter has 136502 non-null cells and 144563 null
  cells: the cells outside North Carolina have no value, and the region has
  839 by 335 = 281065 cells in all.
- January has the values 94 to 249 mm, so the range is 249 - 94 = 155. The
  mean is the sum divided by the number of non-null cells,
  18592904 / 136502 = 136.2. The variance 281.32 is the mean of the squared
  deviations from the mean, the standard deviation 16.77 its square root, and
  the coefficient of variation `100 * 16.77 / 136.2` = 12.3.
- February is the wettest of the three months in this generated series, with a
  mean of 160.1 mm and a largest value of 309 mm; March is the driest with a
  mean of 106.0 mm.
- `mean_of_abs` and `sum_abs` equal `mean` and `sum`, because no value is
  negative.
- The two maps of `runoff` hold 1 and 2 in all 281065 cells, so the sums are
  281065 and 562130, and range, variance and standard deviation are 0. The
  start and end are the hours 0 to 6 and 6 to 12.

The semantic label is empty, because the maps have none.

### Select maps by start time or semantic label

The option **where** takes an SQL condition on the registered maps. The first
command keeps the maps that start on 1 November 2020 or later.

The second command uses a dataset of satellite bands. A satellite takes the
bands of a scene at the same moment. The dataset `sentinel` holds the red band
(semantic label `S2_B4`) and the near infrared band (`S2_B8`) of two scenes as
maps with constant reflectance, registered as time instances, so their end
time is `None`. The reflectance is stored as integers scaled by 10000, as in
the Sentinel-2 products: 500 is a reflectance of 0.05. The name
`sentinel.S2_B8` selects the near infrared band; without the label, all four
maps would be processed.

=== "Command line"

    ```sh
    t.rast.univar input=precipitation_monthly where="start_time >= '2020-11-01'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_11@t_rast_univar||2020-11-01 00:00:00|2020-12-01 00:00:00|136502|144563|104|350|246|138.642320259044|138.642320259044|26.5987082312919|707.491279573396|19.1851291738295|18924954|18924954
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

    ```sh
    r.mapcalc expression="red_1 = 500"
    r.mapcalc expression="nir_1 = 3000"
    r.mapcalc expression="red_2 = 700"
    r.mapcalc expression="nir_2 = 4000"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=red_2 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    r.support map=nir_2 semantic_label=S2_B8
    t.create output=sentinel title="Reflectance" \
        description="Red and near infrared reflectance of two scenes, scaled by 10000"
    t.register input=sentinel maps=red_1,nir_1 start="2020-06-01 10:30:00"
    t.register input=sentinel maps=red_2,nir_2 start="2020-06-11 10:30:00"
    t.rast.univar input=sentinel.S2_B8
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    nir_1@t_rast_univar|S2_B8|2020-06-01 10:30:00|None|281065|0|3000|3000|0|3000|3000|0|0|0|843195000|843195000
    nir_2@t_rast_univar|S2_B8|2020-06-11 10:30:00|None|281065|0|4000|4000|0|4000|4000|0|0|0|1124260000|1124260000
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly", where="start_time >= '2020-11-01'"
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_11@t_rast_univar||2020-11-01 00:00:00|2020-12-01 00:00:00|136502|144563|104|350|246|138.642320259044|138.642320259044|26.5987082312919|707.491279573396|19.1851291738295|18924954|18924954
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

    ```python
    for name, value, label in (
        ("red_1", 500, "S2_B4"),
        ("nir_1", 3000, "S2_B8"),
        ("red_2", 700, "S2_B4"),
        ("nir_2", 4000, "S2_B8"),
    ):
        tools.r_mapcalc(expression=f"{name} = {value}")
        tools.r_support(map=name, semantic_label=label)
    tools.t_create(
        output="sentinel",
        title="Reflectance",
        description="Red and near infrared reflectance of two scenes, scaled by 10000",
    )
    tools.t_register(input="sentinel", maps="red_1,nir_1", start="2020-06-01 10:30:00")
    tools.t_register(input="sentinel", maps="red_2,nir_2", start="2020-06-11 10:30:00")
    print(tools.t_rast_univar(input="sentinel.S2_B8").text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    nir_1@t_rast_univar|S2_B8|2020-06-01 10:30:00|None|281065|0|3000|3000|0|3000|3000|0|0|0|843195000|843195000
    nir_2@t_rast_univar|S2_B8|2020-06-11 10:30:00|None|281065|0|4000|4000|0|4000|4000|0|0|0|1124260000|1124260000
    ```

The first output lists November and December. November holds the largest value
of the whole series, 350 mm, and a mean of 138.6 mm; December is dry, with a
mean of 81.2 mm. Each of the four maps of `sentinel` has a constant value, so
the near infrared map of the first scene holds 3000 in all 281065 cells, and
its sum is 3000 * 281065 = 843195000. The end time of both lines is `None`,
and the semantic label `S2_B8` is the label of the band.

### Calculate extended statistics and percentiles

The flag **-e** adds the quartiles, the median and the 90th percentile. The
non-null cells of `precipitation_monthly_2020_12` are 136502. The first
quartile is at position `136502 * 25 / 100 - 0.5` = 34125 (the value 74), the
third quartile at position 102376 (the value 84), and the 90th percentile at
position 122851.3, which becomes 122851 (the value 93). The number of cells is
even, so the median is the mean of the two middle values at the positions 68250
and 68251; both are 77.

The option **percentile** replaces the 90th percentile by the listed ones. For
December, the 10th percentile is at position 13649.7, which becomes 13649 (the
value 73), the 50th at position 68250.5, which becomes 68250 (the value 77),
and the 95th at position 129676.4, which becomes 129676 (the value 112).

With so many cells, the median and the 50th percentile are the same value. They
differ when the number of cells is even and the two middle values differ. The
third block shows this for a map of the region of 4 by 4 cells that holds the
column number of each cell: the values 1, 2, 3, 4, four times each. The 50th
percentile is at position 7.5, which becomes 7, the value 2 in the sorted list,
while the median is the mean of the values at the positions 7 and 8, 2 and 3:
2.5. The block sets the region of the first example again at the end.

=== "Command line"

    ```sh
    t.rast.univar -e input=precipitation_monthly where="start_time >= '2020-11-01'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    precipitation_monthly_2020_11@t_rast_univar||2020-11-01 00:00:00|2020-12-01 00:00:00|136502|144563|104|350|246|138.642320259044|138.642320259044|26.5987082312919|707.491279573396|19.1851291738295|18924954|18924954|123|131|141|175
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779|74|77|84|93
    ```

    ```sh
    t.rast.univar -e input=precipitation_monthly percentile=10,50,95 \
        where="name = 'precipitation_monthly_2020_12'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779|74|77|84|73|77|112
    ```

    ```sh
    g.region w=400000 e=404000 s=100000 n=104000 res=1000
    r.mapcalc expression="column_number = col()"
    t.create output=column_numbers title="Column numbers" \
        description="Column number of each cell of a small region"
    t.register input=column_numbers maps=column_number start=2020-01-01
    t.rast.univar -e input=column_numbers percentile=50
    g.region raster=elev_state_500m res=1000 -a
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_50
    column_number@t_rast_univar||2020-01-01 00:00:00|None|16|0|1|4|3|2.5|2.5|1.11803398874989|1.25|44.7213595499958|40|40|1|2.5|3|2
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly", where="start_time >= '2020-11-01'", flags="e"
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_90
    precipitation_monthly_2020_11@t_rast_univar||2020-11-01 00:00:00|2020-12-01 00:00:00|136502|144563|104|350|246|138.642320259044|138.642320259044|26.5987082312919|707.491279573396|19.1851291738295|18924954|18924954|123|131|141|175
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779|74|77|84|93
    ```

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly",
        percentile=[10, 50, 95],
        where="name = 'precipitation_monthly_2020_12'",
        flags="e",
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_10|percentile_50|percentile_95
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779|74|77|84|73|77|112
    ```

    ```python
    tools.g_region(w=400000, e=404000, s=100000, n=104000, res=1000)
    tools.r_mapcalc(expression="column_number = col()")
    tools.t_create(
        output="column_numbers",
        title="Column numbers",
        description="Column number of each cell of a small region",
    )
    tools.t_register(input="column_numbers", maps="column_number", start="2020-01-01")
    print(tools.t_rast_univar(input="column_numbers", percentile=[50], flags="e").text)
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs|first_quartile|median|third_quartile|percentile_50
    column_number@t_rast_univar||2020-01-01 00:00:00|None|16|0|1|4|3|2.5|2.5|1.11803398874989|1.25|44.7213595499958|40|40|1|2.5|3|2
    ```

### Statistics per zone

The map `regions` divides North Carolina by elevation into three zones, roughly
the natural regions: the Coastal Plain below 100 m (category 1), the Piedmont
up to 400 m (category 2) and the Mountains above (category 3). With **zones**,
each map gets one line per zone. The three zones hold 71800, 43252 and 21450
cells, which add up to the 136502 non-null cells of the map; the cells outside
North Carolina belong to no zone and are not counted. With **format** `json`,
each zone is an object of its own, and the category label has the name
`zone_label`. The values are those of the generated series for July, not
measurements.

=== "Command line"

    ```sh
    r.mapcalc expression="regions = if(elev_state_500m < 100, 1, if(elev_state_500m < 400, 2, 3))"
    r.category map=regions separator=":" rules=- <<EOF
    1:Coastal Plain
    2:Piedmont
    3:Mountains
    EOF
    t.rast.univar input=precipitation_monthly zones=regions \
        where="name = 'precipitation_monthly_2020_07'"
    ```

    ```text
    id|semantic_label|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|1|Coastal Plain|71800|0|112|223|111|155.746908077994|155.746908077994|18.893553458953|356.966362306315|12.1309332506887|11182628|11182628
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|2|Piedmont|43252|0|86|199|113|123.406732636641|123.406732636641|10.9022827751374|118.859769709058|8.83443110615212|5337588|5337588
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|3|Mountains|21450|0|83|219|136|129.840745920746|129.840745920746|16.0767767300026|258.462750026352|12.3819195707761|2785084|2785084
    ```

    ```sh
    t.rast.univar input=precipitation_monthly zones=regions format=json \
        where="name = 'precipitation_monthly_2020_07'" | grep -E '"(zone|zone_label|mean)"'
    ```

    ```text
            "zone": 1,
            "zone_label": "Coastal Plain",
            "mean": 155.74690807799442,
            "zone": 2,
            "zone_label": "Piedmont",
            "mean": 123.40673263664108,
            "zone": 3,
            "zone_label": "Mountains",
            "mean": 129.84074592074592,
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.r_mapcalc(
        expression="regions = if(elev_state_500m < 100, 1, if(elev_state_500m < 400, 2, 3))"
    )
    tools.r_category(
        map="regions",
        separator=":",
        rules=StringIO("1:Coastal Plain\n2:Piedmont\n3:Mountains\n"),
    )
    result = tools.t_rast_univar(
        input="precipitation_monthly",
        zones="regions",
        where="name = 'precipitation_monthly_2020_07'",
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|zone|label|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|1|Coastal Plain|71800|0|112|223|111|155.746908077994|155.746908077994|18.893553458953|356.966362306315|12.1309332506887|11182628|11182628
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|2|Piedmont|43252|0|86|199|113|123.406732636641|123.406732636641|10.9022827751374|118.859769709058|8.83443110615212|5337588|5337588
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|3|Mountains|21450|0|83|219|136|129.840745920746|129.840745920746|16.0767767300026|258.462750026352|12.3819195707761|2785084|2785084
    ```

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly",
        zones="regions",
        format="json",
        where="name = 'precipitation_monthly_2020_07'",
    )
    for stats in result.json:
        print(f"zone {stats['zone']} ({stats['zone_label']}): mean {stats['mean']}")
    ```

    ```text
    zone 1 (Coastal Plain): mean 155.74690807799442
    zone 2 (Piedmont): mean 123.40673263664108
    zone 3 (Mountains): mean 129.84074592074592
    ```

### Restrict the statistics with a raster mask

A raster mask restricts the statistics in the same way as for *r.univar*. With
the mask on the Mountains (category 3 of `regions`), 21450 cells of the July map
remain, and the other 259615 cells of the region count as null cells. The
statistics are those of the zone 3 line above. `r.mask -r` removes the mask
again.

=== "Command line"

    ```sh
    r.mask raster=regions maskcats=3
    t.rast.univar input=precipitation_monthly \
        where="name = 'precipitation_monthly_2020_07'"
    r.mask -r
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|21450|259615|83|219|136|129.840745920746|129.840745920746|16.0767767300026|258.462750026352|12.3819195707761|2785084|2785084
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mask(raster="regions", maskcats="3")
    result = tools.t_rast_univar(
        input="precipitation_monthly", where="name = 'precipitation_monthly_2020_07'"
    )
    print(result.text)
    tools.r_mask(flags="r")
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_07@t_rast_univar||2020-07-01 00:00:00|2020-08-01 00:00:00|21450|259615|83|219|136|129.840745920746|129.840745920746|16.0767767300026|258.462750026352|12.3819195707761|2785084|2785084
    ```

### Choose the output format

The option **separator** sets another separator, and the flag **-u** leaves
out the line with the column names, for instance to append the lines to a
table that has them already. With **format** `csv`, the columns are separated
by commas, and the option **output** writes the statistics to a file. With
**format** `json`, *t.rast.univar* prints a list with one object per map;
here for December with the extended statistics and two percentiles. In
Python, the attribute `json` of the result holds this list, and the example
prints the mean, the median and the percentiles from it.

=== "Command line"

    ```sh
    t.rast.univar -u input=precipitation_monthly separator=";" \
        where="start_time >= '2020-11-01'"
    ```

    ```text
    precipitation_monthly_2020_11@t_rast_univar;;2020-11-01 00:00:00;2020-12-01 00:00:00;136502;144563;104;350;246;138.642320259044;138.642320259044;26.5987082312919;707.491279573396;19.1851291738295;18924954;18924954
    precipitation_monthly_2020_12@t_rast_univar;;2020-12-01 00:00:00;2021-01-01 00:00:00;136502;144563;59;177;118;81.2133082299161;81.2133082299161;12.9580869230387;167.912016705026;15.9556200892028;11085779;11085779
    ```

    ```sh
    t.rast.univar input=precipitation_monthly format=csv output=precipitation.csv \
        where="start_time >= '2020-11-01'"
    cat precipitation.csv
    ```

    ```text
    id,semantic_label,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    precipitation_monthly_2020_11@t_rast_univar,,2020-11-01 00:00:00,2020-12-01 00:00:00,136502,144563,104,350,246,138.642320259044,138.642320259044,26.5987082312919,707.491279573396,19.1851291738295,18924954,18924954
    precipitation_monthly_2020_12@t_rast_univar,,2020-12-01 00:00:00,2021-01-01 00:00:00,136502,144563,59,177,118,81.2133082299161,81.2133082299161,12.9580869230387,167.912016705026,15.9556200892028,11085779,11085779
    ```

    ```sh
    t.rast.univar -e input=precipitation_monthly format=json percentile=50,90 \
        where="name = 'precipitation_monthly_2020_12'"
    ```

    ```text
    [
        {
            "id": "precipitation_monthly_2020_12@t_rast_univar",
            "semantic_label": null,
            "start": "2020-12-01 00:00:00",
            "end": "2021-01-01 00:00:00",
            "n": 136502,
            "null_cells": 144563,
            "cells": 281065,
            "min": 59,
            "max": 177,
            "range": 118,
            "mean": 81.21330822991605,
            "mean_of_abs": 81.21330822991605,
            "stddev": 12.95808692303869,
            "variance": 167.91201670502633,
            "coeff_var": 15.955620089202819,
            "sum": 11085779,
            "first_quartile": 74,
            "median": 77,
            "third_quartile": 84,
            "percentiles": [
                {
                    "percentile": 50,
                    "value": 77
                },
                {
                    "percentile": 90,
                    "value": 93
                }
            ]
        }
    ]
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly",
        separator=";",
        where="start_time >= '2020-11-01'",
        flags="u",
    )
    print(result.text)
    ```

    ```text
    precipitation_monthly_2020_11@t_rast_univar;;2020-11-01 00:00:00;2020-12-01 00:00:00;136502;144563;104;350;246;138.642320259044;138.642320259044;26.5987082312919;707.491279573396;19.1851291738295;18924954;18924954
    precipitation_monthly_2020_12@t_rast_univar;;2020-12-01 00:00:00;2021-01-01 00:00:00;136502;144563;59;177;118;81.2133082299161;81.2133082299161;12.9580869230387;167.912016705026;15.9556200892028;11085779;11085779
    ```

    ```python
    from pathlib import Path

    tools.t_rast_univar(
        input="precipitation_monthly",
        format="csv",
        output="precipitation.csv",
        where="start_time >= '2020-11-01'",
    )
    print(Path("precipitation.csv").read_text(), end="")
    ```

    ```text
    id,semantic_label,start,end,non_null_cells,null_cells,min,max,range,mean,mean_of_abs,stddev,variance,coeff_var,sum,sum_abs
    precipitation_monthly_2020_11@t_rast_univar,,2020-11-01 00:00:00,2020-12-01 00:00:00,136502,144563,104,350,246,138.642320259044,138.642320259044,26.5987082312919,707.491279573396,19.1851291738295,18924954,18924954
    precipitation_monthly_2020_12@t_rast_univar,,2020-12-01 00:00:00,2021-01-01 00:00:00,136502,144563,59,177,118,81.2133082299161,81.2133082299161,12.9580869230387,167.912016705026,15.9556200892028,11085779,11085779
    ```

    ```python
    result = tools.t_rast_univar(
        input="precipitation_monthly",
        format="json",
        percentile=[50, 90],
        where="name = 'precipitation_monthly_2020_12'",
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
    precipitation_monthly_2020_12@t_rast_univar: mean 81.21330822991605, median 77, percentiles {50: 77, 90: 93}
    ```

### Statistics per granule

With **granularity**, the four quarters of 2020 each get one line: the first
granule starts on 1 January, the start of the first map, and each quarter
holds three monthly maps, listed in the column `id`. The statistics are taken
from all cells of the three maps, so `non_null_cells` is `3 * 136502` =
409506, and the mean of a quarter is its sum divided by this number.

The second block adds the map `precipitation_storm_2020_03_15` with 50 mm in
every cell of North Carolina, from 15 March to 15 April, and registers it with
the monthly maps of the first half year in the dataset
`precipitation_storm`. The storm crosses the border of the first two
quarters. With the default sampling `contains`, neither quarter takes it, and
the means are those of the first block. With `sampling=related`, both
quarters take it, so each has four maps and `4 * 136502` = 546008 non-null
cells. The mean of the first quarter falls from 134.10 to
`(54916330 + 50 * 136502) / 546008` = 113.08, because the storm brings less
than the months: 54916330 is the sum of the first quarter in the first block.
The commands print the columns `id`, `start`, `non_null_cells` and `mean`: on
the command line, *cut* keeps the first, third, fifth and tenth column; in
Python, the function `print_columns()` picks the same fields from each line.

=== "Command line"

    ```sh
    t.rast.univar input=precipitation_monthly granularity="3 months"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar||2020-01-01 00:00:00|2020-04-01 00:00:00|409506|433689|88|309|221|134.10384707428|134.10384707428|28.7156588027523|824.589060476084|21.4130015128103|54916330|54916330
    precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar||2020-04-01 00:00:00|2020-07-01 00:00:00|409506|433689|71|347|276|129.35009743447|129.35009743447|36.1818670920443|1309.12750626636|27.9720447140555|52969641|52969641
    precipitation_monthly_2020_07@t_rast_univar,precipitation_monthly_2020_08@t_rast_univar,precipitation_monthly_2020_09@t_rast_univar||2020-07-01 00:00:00|2020-10-01 00:00:00|409506|433689|60|295|235|142.463136071266|142.463136071266|46.3127455981012|2144.87040483444|32.5085821323865|58339509|58339509
    precipitation_monthly_2020_10@t_rast_univar,precipitation_monthly_2020_11@t_rast_univar,precipitation_monthly_2020_12@t_rast_univar||2020-10-01 00:00:00|2021-01-01 00:00:00|409506|433689|55|350|295|103.768320854884|103.768320854884|30.7986830474803|948.558877459148|29.680236505466|42493750|42493750
    ```

    ```sh
    r.mapcalc expression="precipitation_storm_2020_03_15 = if(isnull(elev_state_500m), null(), 50)"
    t.create output=precipitation_storm title="Precipitation with storm" \
        description="Monthly precipitation sum and a storm in 2020 in mm"
    t.register input=precipitation_storm \
        maps=$(t.rast.list -u input=precipitation_monthly columns=name \
            where="start_time < '2020-07-01'" | paste -s -d, -)
    t.register input=precipitation_storm maps=precipitation_storm_2020_03_15 \
        start=2020-03-15 end=2020-04-15
    t.rast.univar input=precipitation_storm granularity="3 months" \
        | cut -d"|" -f1,3,5,10
    t.rast.univar input=precipitation_storm granularity="3 months" \
        sampling=related | cut -d"|" -f1,3,5,10
    ```

    ```text
    id|start|non_null_cells|mean
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar|2020-01-01 00:00:00|409506|134.10384707428
    precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar|2020-04-01 00:00:00|409506|129.35009743447
    id|start|non_null_cells|mean
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar,precipitation_storm_2020_03_15@t_rast_univar|2020-01-01 00:00:00|546008|113.07788530571
    precipitation_storm_2020_03_15@t_rast_univar,precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar|2020-04-01 00:00:00|546008|109.512573075852
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_rast_univar(input="precipitation_monthly", granularity="3 months")
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar||2020-01-01 00:00:00|2020-04-01 00:00:00|409506|433689|88|309|221|134.10384707428|134.10384707428|28.7156588027523|824.589060476084|21.4130015128103|54916330|54916330
    precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar||2020-04-01 00:00:00|2020-07-01 00:00:00|409506|433689|71|347|276|129.35009743447|129.35009743447|36.1818670920443|1309.12750626636|27.9720447140555|52969641|52969641
    precipitation_monthly_2020_07@t_rast_univar,precipitation_monthly_2020_08@t_rast_univar,precipitation_monthly_2020_09@t_rast_univar||2020-07-01 00:00:00|2020-10-01 00:00:00|409506|433689|60|295|235|142.463136071266|142.463136071266|46.3127455981012|2144.87040483444|32.5085821323865|58339509|58339509
    precipitation_monthly_2020_10@t_rast_univar,precipitation_monthly_2020_11@t_rast_univar,precipitation_monthly_2020_12@t_rast_univar||2020-10-01 00:00:00|2021-01-01 00:00:00|409506|433689|55|350|295|103.768320854884|103.768320854884|30.7986830474803|948.558877459148|29.680236505466|42493750|42493750
    ```

    ```python
    def print_columns(result):
        for line in result.text.splitlines():
            fields = line.split("|")
            print("|".join(fields[k] for k in (0, 2, 4, 9)))


    tools.r_mapcalc(
        expression="precipitation_storm_2020_03_15 ="
        " if(isnull(elev_state_500m), null(), 50)"
    )
    tools.t_create(
        output="precipitation_storm",
        title="Precipitation with storm",
        description="Monthly precipitation sum and a storm in 2020 in mm",
    )
    months = tools.t_rast_list(
        input="precipitation_monthly",
        columns="name",
        where="start_time < '2020-07-01'",
        flags="u",
    )
    tools.t_register(input="precipitation_storm", maps=",".join(months.text.split()))
    tools.t_register(
        input="precipitation_storm",
        maps="precipitation_storm_2020_03_15",
        start="2020-03-15",
        end="2020-04-15",
    )
    print_columns(tools.t_rast_univar(input="precipitation_storm", granularity="3 months"))
    print_columns(
        tools.t_rast_univar(
            input="precipitation_storm", granularity="3 months", sampling="related"
        )
    )
    ```

    ```text
    id|start|non_null_cells|mean
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar|2020-01-01 00:00:00|409506|134.10384707428
    precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar|2020-04-01 00:00:00|409506|129.35009743447
    id|start|non_null_cells|mean
    precipitation_monthly_2020_01@t_rast_univar,precipitation_monthly_2020_02@t_rast_univar,precipitation_monthly_2020_03@t_rast_univar,precipitation_storm_2020_03_15@t_rast_univar|2020-01-01 00:00:00|546008|113.07788530571
    precipitation_storm_2020_03_15@t_rast_univar,precipitation_monthly_2020_04@t_rast_univar,precipitation_monthly_2020_05@t_rast_univar,precipitation_monthly_2020_06@t_rast_univar|2020-04-01 00:00:00|546008|109.512573075852
    ```

### Maps with extents of their own

Satellite scenes rarely share one extent. The dataset `scenes` holds four
maps with constant values on extents of their own. The current region is the
square of 4 km by 4 km with 16 cells whose south-west corner is at easting
400000 and northing 100000; the extents of the scenes are given in km from this
corner:

- `scene_1` covers the square from (-1, -1) to (5, 5) and so the whole region;
- `scene_2` lies inside the region, from (1, 1) to (3, 3);
- `scene_3` reaches from (2, 2) to (6, 6) and shares 4 cells with the region;
- `scene_4` lies outside, from (10, 10) to (12, 12).

The commands print the columns `id`, `non_null_cells` and `null_cells` only:
on the command line, *cut* keeps the first, fifth and sixth column; in Python,
the function `print_cells()` reads them from the JSON output, where `n` is the
number of non-null cells.

1. By default, the cells are counted in the current region: `scene_1` has 16
   non-null cells there, `scene_2` and `scene_3` have 4, and `scene_4` none.
2. With **-r**, each map is counted in its own region: `scene_1` has 36
   cells, `scene_3` 16, and `scene_4`, outside the current region, 4.
3. **region_relation** selects maps by their relation to the current region:
   `overlaps` keeps all but `scene_4`, `contains` only `scene_1`, which covers
   the region, and `is_contained` only `scene_2`, which lies inside it.
   Combined with **-r**, the selected maps are counted in their own regions.
4. **-r** works with **zones** as well. The zone map `sides` covers all four
   scenes and holds 1 west of the easting 402000 (2 km from the corner) and 2
   east of it. In its own region, `scene_1` has 18 cells in each zone and
   `scene_2` 2; `scene_3` and `scene_4` lie east of it and get a line for zone
   2 only, because a zone without any cell in the region of a map gets no line.
   The commands print `id`, `zone` and `non_null_cells`.

=== "Command line"

    ```sh
    for scene in "scene_1 -1 5 10" "scene_2 1 3 20" \
        "scene_3 2 6 30" "scene_4 10 12 40"; do
        set -- $scene
        g.region w=$((400000 + $2 * 1000)) e=$((400000 + $3 * 1000)) \
            s=$((100000 + $2 * 1000)) n=$((100000 + $3 * 1000)) res=1000
        r.mapcalc expression="$1 = $4"
    done
    t.create output=scenes title="Scenes" \
        description="Scenes with extents of their own"
    t.register -i input=scenes maps=scene_1,scene_2,scene_3,scene_4 \
        start=2020-07-01 increment="1 day"
    g.region w=400000 e=404000 s=100000 n=104000 res=1000
    t.rast.univar input=scenes | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    scene_2@t_rast_univar|4|12
    scene_3@t_rast_univar|4|12
    scene_4@t_rast_univar|0|16
    ```

    ```sh
    t.rast.univar -r input=scenes | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|36|0
    scene_2@t_rast_univar|4|0
    scene_3@t_rast_univar|16|0
    scene_4@t_rast_univar|4|0
    ```

    ```sh
    t.rast.univar input=scenes region_relation=overlaps | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    scene_2@t_rast_univar|4|12
    scene_3@t_rast_univar|4|12
    ```

    ```sh
    t.rast.univar input=scenes region_relation=contains | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    ```

    ```sh
    t.rast.univar input=scenes region_relation=is_contained | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_2@t_rast_univar|4|12
    ```

    ```sh
    t.rast.univar -r input=scenes region_relation=overlaps | cut -d"|" -f1,5,6
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|36|0
    scene_2@t_rast_univar|4|0
    scene_3@t_rast_univar|16|0
    ```

    ```sh
    g.region w=399000 e=413000 s=99000 n=113000 res=1000
    r.mapcalc expression="sides = if(x() < 402000, 1, 2)"
    g.region w=400000 e=404000 s=100000 n=104000 res=1000
    t.rast.univar -r input=scenes zones=sides | cut -d"|" -f1,5,7
    ```

    ```text
    id|zone|non_null_cells
    scene_1@t_rast_univar|1|18
    scene_1@t_rast_univar|2|18
    scene_2@t_rast_univar|1|2
    scene_2@t_rast_univar|2|2
    scene_3@t_rast_univar|2|16
    scene_4@t_rast_univar|2|4
    ```

=== "Python (grass.tools)"

    ```python
    for name, low, high, value in (
        ("scene_1", -1, 5, 10),
        ("scene_2", 1, 3, 20),
        ("scene_3", 2, 6, 30),
        ("scene_4", 10, 12, 40),
    ):
        tools.g_region(
            w=400000 + low * 1000,
            e=400000 + high * 1000,
            s=100000 + low * 1000,
            n=100000 + high * 1000,
            res=1000,
        )
        tools.r_mapcalc(expression=f"{name} = {value}")
    tools.t_create(
        output="scenes",
        title="Scenes",
        description="Scenes with extents of their own",
    )
    tools.t_register(
        input="scenes",
        maps="scene_1,scene_2,scene_3,scene_4",
        start="2020-07-01",
        increment="1 day",
        flags="i",
    )
    tools.g_region(w=400000, e=404000, s=100000, n=104000, res=1000)


    def print_cells(result):
        print("id|non_null_cells|null_cells")
        for stats in result.json:
            print(f"{stats['id']}|{stats['n']}|{stats['null_cells']}")


    print_cells(tools.t_rast_univar(input="scenes", format="json"))
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    scene_2@t_rast_univar|4|12
    scene_3@t_rast_univar|4|12
    scene_4@t_rast_univar|0|16
    ```

    ```python
    print_cells(tools.t_rast_univar(input="scenes", format="json", flags="r"))
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|36|0
    scene_2@t_rast_univar|4|0
    scene_3@t_rast_univar|16|0
    scene_4@t_rast_univar|4|0
    ```

    ```python
    result = tools.t_rast_univar(input="scenes", format="json", region_relation="overlaps")
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    scene_2@t_rast_univar|4|12
    scene_3@t_rast_univar|4|12
    ```

    ```python
    result = tools.t_rast_univar(input="scenes", format="json", region_relation="contains")
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|16|0
    ```

    ```python
    result = tools.t_rast_univar(
        input="scenes", format="json", region_relation="is_contained"
    )
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_2@t_rast_univar|4|12
    ```

    ```python
    result = tools.t_rast_univar(
        input="scenes", format="json", region_relation="overlaps", flags="r"
    )
    print_cells(result)
    ```

    ```text
    id|non_null_cells|null_cells
    scene_1@t_rast_univar|36|0
    scene_2@t_rast_univar|4|0
    scene_3@t_rast_univar|16|0
    ```

    ```python
    tools.g_region(w=399000, e=413000, s=99000, n=113000, res=1000)
    tools.r_mapcalc(expression="sides = if(x() < 402000, 1, 2)")
    tools.g_region(w=400000, e=404000, s=100000, n=104000, res=1000)
    result = tools.t_rast_univar(input="scenes", zones="sides", format="json", flags="r")
    print("id|zone|non_null_cells")
    for stats in result.json:
        print(f"{stats['id']}|{stats['zone']}|{stats['n']}")
    ```

    ```text
    id|zone|non_null_cells
    scene_1@t_rast_univar|1|18
    scene_1@t_rast_univar|2|18
    scene_2@t_rast_univar|1|2
    scene_2@t_rast_univar|2|2
    scene_3@t_rast_univar|2|16
    scene_4@t_rast_univar|2|4
    ```

### Use a dataset of another mapset

*t.rast.univar* reads a dataset of another mapset. The new mapset
`t_rast_univar_2` has no dataset of its own. A new mapset starts with the
default region of the dataset, cells of 500 m, so the example sets the region
of the first example again. *g.mapsets* adds the mapset `t_rast_univar` to the
search path, and the input `precipitation_monthly@t_rast_univar` names the
dataset of the first example with its mapset. In the second block,
*g.mapsets* shows the search path, now with `t_rast_univar`, so the name
`precipitation_monthly` without a mapset finds the same dataset. The mapset is
added only for the second block, which names the dataset without its mapset; the
first block works without it (see
[Datasets of other mapsets](temporalintro.md#datasets-of-other-mapsets)).

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_univar_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_rast_univar operation=add
    t.rast.univar input=precipitation_monthly@t_rast_univar \
        where="name = 'precipitation_monthly_2020_12'"
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

    ```sh
    g.mapsets -p
    t.rast.univar input=precipitation_monthly \
        where="name = 'precipitation_monthly_2020_12'"
    ```

    ```text
    t_rast_univar_2 PERMANENT t_rast_univar
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(flags="c", mapset="t_rast_univar_2")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_rast_univar", operation="add")
    result = tools.t_rast_univar(
        input="precipitation_monthly@t_rast_univar",
        where="name = 'precipitation_monthly_2020_12'",
    )
    print(result.text)
    ```

    ```text
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

    ```python
    print(tools.g_mapsets(flags="p").text)
    result = tools.t_rast_univar(
        input="precipitation_monthly", where="name = 'precipitation_monthly_2020_12'"
    )
    print(result.text)
    ```

    ```text
    t_rast_univar_2 PERMANENT t_rast_univar
    id|semantic_label|start|end|non_null_cells|null_cells|min|max|range|mean|mean_of_abs|stddev|variance|coeff_var|sum|sum_abs
    precipitation_monthly_2020_12@t_rast_univar||2020-12-01 00:00:00|2021-01-01 00:00:00|136502|144563|59|177|118|81.2133082299161|81.2133082299161|12.9580869230387|167.912016705026|15.9556200892028|11085779|11085779
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.gisenv](g.gisenv.md), [g.mapsets](g.mapsets.md), [g.region](g.region.md),
[r.mask](r.mask.md), [r.univar](r.univar.md),
[t.create](t.create.md), [t.info](t.info.md),
[t.rast3d.univar](t.rast3d.univar.md), [t.register](t.register.md),
[t.vect.univar](t.vect.univar.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture  
Stefan Blumentrath (support for zones, parallel processing, and spatial
relations)
