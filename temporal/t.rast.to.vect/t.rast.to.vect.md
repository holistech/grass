## DESCRIPTION

*t.rast.to.vect* converts each raster map of a space time raster dataset into
a vector map and registers the vector maps in a new space time vector dataset.
It runs *[r.to.vect](r.to.vect.md)* for every map, so the points, lines and
areas are those of *r.to.vect*; see its manual for the details of the
conversion. Each new vector map gets the start and end time of the raster map
it was computed from. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

The option **input** names the space time raster dataset, the option
**output** the new space time vector dataset. The new dataset takes the
temporal type, the semantic type, the title and the description of the input
dataset. The option **where** takes an SQL condition on the registered maps
and selects the maps to convert, for instance by their `start_time` or their
`name`; without it, all maps are converted.

The option **type** is required and sets the kind of feature:

- `point` writes one point at the centre of each cell that has a value.
- `area` writes one area for each group of cells with the same value that
  touch along an edge, with a boundary and a centroid; the areas follow the
  cell borders.
- `line` writes the lines between the centres of the cells. It needs a raster
  map of lines that are one cell wide; *r.to.vect* stops at a map that is not
  thinned and asks for *[r.thin](r.thin.md)*.

The option **column** names the column of the attribute table that stores the
value of the cell, `value` by default. Each vector map gets an attribute table
with the columns `cat`, the column named by **column** and `label`. Null cells
give no feature. Three flags change the table and the categories:

- **-t** creates the vector maps without attribute tables.
- **-v** uses the values of the raster map as categories instead of a
  sequence of numbers. The table then has no column for the value, only `cat`
  and `label`, and one row for each value. This works for integer raster maps
  only: for a map with floating point values, *r.to.vect* ignores **-v**,
  warns, and writes the values to the column named by **column**, as the
  third example shows.
- **-z** writes the values of the cells as the z coordinate of the points and
  creates no table. It works for `type=point` only: with `type=area` or
  `type=line`, *r.to.vect* fails.

Two more flags are passed to *r.to.vect*:

- **-s** smooths the corners of the areas of `type=area`.
- **-b** does not build the topology of the vector maps. Such a map has no
  topological counts, such as the number of areas, and no spatial index.

The option **nprocs** sets the number of *r.to.vect* runs at the same time,
`1` by default. More than one run at a time works only with **-t**: without
it, *t.rast.to.vect* sets **nprocs** to `1` and warns, because the attribute
tables cannot be created in parallel.

The new vector maps are named after the option **basename**, followed by an
underscore and a suffix that the option **suffix** chooses:

- `gran` (the default) takes the start time of the raster map, cut to the
  granularity of the input dataset: `2020_05` in a dataset of months. A
  dataset of a single time instance has no granularity; `gran` then takes the
  full start time, as `time` does.
- `time` takes the full start time: `2020_05_01T00_00_00`.
- `num` numbers the selected maps from 1, with five digits: `00001`.
  `num%03` gives three digits: `001`.

In a dataset with relative time, each suffix gives the number, because a
relative time has no calendar date.

A raster map can give a vector map without features, for instance when all its
cells are null. Such an empty vector map is removed and not registered, unless
the flag **-n** is given; then it is registered as well.

## NOTES

*r.to.vect* converts each map in the current computational region, so the
region decides which cells are converted and where the features end, as the
last example shows.

If **where** selects no map, *t.rast.to.vect* warns that the space time
raster dataset is empty and creates no output dataset.

An unknown **suffix** is refused before anything is written, for instance
with "Invalid suffix `<gram>`, use gran, time, num or num%NN" for
`suffix=gram`. An SQL error in **where** stops the tool with a message that
begins with "Invalid where condition". If *r.to.vect* fails for a map, for
instance for `type=line` on a map that is not thinned, as in the fourth
example, or for **-z** with `type=area` or `type=line`, or for a **column**
that is no valid SQL name, *t.rast.to.vect* stops with a message that begins
with "Error running r.to.vect" and creates no dataset.

An existing **output** dataset is replaced only with **--overwrite**; without
it, the tool stops with the message that the dataset is already in the
database. With **--overwrite**, the vector maps of the same names are
replaced as well.

The input dataset can be in another mapset of the project; the name with the
mapset (`input=precipitation_heavy@t_rast_to_vect`) selects it. The new
vector maps and the new dataset are always created in the current mapset, as
the last example shows.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_to_vect` and sets the computational region
to North Carolina with cells of 1 km; the first two examples work in this
region. The later examples work in a window of 8 by 8 cells, 8 km by 8 km, in
the west of the state, so that the vector maps stay small and their features
can be counted by hand. The last example creates a second mapset. The
shapes in the examples about lines and corners are made up, with dates in
July 2026, so that the results can be checked by hand.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_to_vect -->

<!-- markdownlint-disable MD046 -->

### Convert the classes of heavy rain to areas

The dataset `precipitation_monthly` holds twelve maps of the monthly
precipitation sum in 2020 in whole millimetres. The maps are generated, not
measured: the monthly normals of the 136 climate stations in `precip_30ynormals`
are interpolated with *v.surf.idw* and multiplied by an assumed factor for each
month, so the pattern changes from month to month. Each map is an interval of
one month. The list at the end of the first block shows the largest value of
each month.

The dataset `precipitation_heavy` classifies them: a cell with 200 mm or more
gets the class `int(mm / 100)`, so 2 stands for 200 to 299 mm and 3 for 300 mm
and more. All other cells are null and give no area. The semantic type `max`
is the one that *t.info* shows for the new dataset later.

In the second block, *t.rast.to.vect* converts all twelve maps with
`type=area`. Four months have no cell of 200 mm or more: June, September,
October and December. Their vector maps are empty and *t.rast.to.vect* removes
them, so eight vector maps are registered, as *g.list* shows. The default
suffix `gran` names the maps after the month. The columns `areas` and
`centroids` of *[t.vect.list](t.vect.list.md)* differ, because `areas` counts
every closed ring of boundaries, also a ring that encloses only null cells
and carries no class, while `centroids` counts the areas that carry a class.
The third block prints the classes of the first two months, selected with
**t_where**, from the attribute tables with
*[t.vect.db.select](t.vect.db.select.md)*: one row for each area with a class,
in the default column `value`. January has one area of class 2, February five
areas of class 2 and three of class 3. The fourth block shows with
*[t.info](t.info.md)* that the new dataset `rain_areas` has the time, the
semantic type `max`, the title and the description of the input dataset. Its
counts are the sums over the eight maps, so the number of areas (46) again
exceeds the number of centroids (36) for the same reason.

In the last block, the flag **-n** keeps the four empty maps, and
**--overwrite** replaces the dataset `rain_areas` of the second block together
with its vector maps.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_to_vect
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
    for month in $(seq 12); do
        name=$(printf %02d $month)
        echo "precipitation_heavy_2020_$name = if(precipitation_monthly_2020_$name >= 200," \
            "int(precipitation_monthly_2020_$name / 100), null())"
    done | r.mapcalc file=-
    t.create output=precipitation_heavy semantictype=max title="Heavy precipitation" \
        description="Monthly precipitation of 200 mm and more in classes of 100 mm"
    t.register -i input=precipitation_heavy \
        maps=$(g.list type=raster pattern="precipitation_heavy_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    t.rast.list input=precipitation_monthly columns=name,max
    ```

    ```text
    name|max
    precipitation_monthly_2020_01|249.0
    precipitation_monthly_2020_02|309.0
    precipitation_monthly_2020_03|212.0
    precipitation_monthly_2020_04|231.0
    precipitation_monthly_2020_05|347.0
    precipitation_monthly_2020_06|163.0
    precipitation_monthly_2020_07|223.0
    precipitation_monthly_2020_08|295.0
    precipitation_monthly_2020_09|181.0
    precipitation_monthly_2020_10|160.0
    precipitation_monthly_2020_11|350.0
    precipitation_monthly_2020_12|177.0
    ```

    ```sh
    t.rast.to.vect input=precipitation_heavy output=rain_areas basename=rain_area \
        type=area
    t.vect.list input=rain_areas columns=name,start_time,areas,centroids
    g.list type=vector pattern="rain_area_*" mapset=.
    ```

    ```text
    name|start_time|areas|centroids
    rain_area_2020_01|2020-01-01 00:00:00|1|1
    rain_area_2020_02|2020-02-01 00:00:00|8|8
    rain_area_2020_03|2020-03-01 00:00:00|2|2
    rain_area_2020_04|2020-04-01 00:00:00|1|1
    rain_area_2020_05|2020-05-01 00:00:00|15|7
    rain_area_2020_07|2020-07-01 00:00:00|2|2
    rain_area_2020_08|2020-08-01 00:00:00|7|6
    rain_area_2020_11|2020-11-01 00:00:00|10|9
    rain_area_2020_01
    rain_area_2020_02
    rain_area_2020_03
    rain_area_2020_04
    rain_area_2020_05
    rain_area_2020_07
    rain_area_2020_08
    rain_area_2020_11
    ```

    ```sh
    t.vect.db.select input=rain_areas columns=value \
        t_where="start_time < '2020-03-01'"
    ```

    ```text
    start_time|end_time|value
    2020-01-01 00:00:00|2020-02-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    ```

    ```sh
    t.info type=stvds input=rain_areas
    ```

    ```text
     +-------------------- Space Time Vector Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_areas@t_rast_to_vect
     | Name: ...................... rain_areas
     | Mapset: .................... t_rast_to_vect
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-01-01 00:00:00
     | End time:................... 2020-12-01 00:00:00
     | Granularity:................ 1 month
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 318000.0
     | South:...................... 11000.0
     | East:.. .................... 930000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Vector register table:...... vector_map_register_00000000000000000000000000000000
     | Number of points ........... 0
     | Number of lines ............ 0
     | Number of boundaries ....... 54
     | Number of centroids ........ 36
     | Number of faces ............ 0
     | Number of kernels .......... 0
     | Number of primitives ....... 90
     | Number of nodes ............ 47
     | Number of areas ............ 46
     | Number of islands .......... 39
     | Number of holes ............ 0
     | Number of volumes .......... 0
     | Number of registered maps:.. 8
     |
     | Title:
     | Heavy precipitation
     | Description:
     | Monthly precipitation of 200 mm and more in classes of 100 mm
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.to.vect input="precipitation_heavy"
     |     output="rain_areas" basename="rain_area" type="area"
     | 
     +----------------------------------------------------------------------------+
    ```

    ```sh
    t.rast.to.vect -n input=precipitation_heavy output=rain_areas basename=rain_area \
        type=area --overwrite
    t.vect.list input=rain_areas columns=name,areas
    ```

    ```text
    name|areas
    rain_area_2020_01|1
    rain_area_2020_02|8
    rain_area_2020_03|2
    rain_area_2020_04|1
    rain_area_2020_05|15
    rain_area_2020_06|0
    rain_area_2020_07|2
    rain_area_2020_08|7
    rain_area_2020_09|0
    rain_area_2020_10|0
    rain_area_2020_11|10
    rain_area_2020_12|0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_to_vect")
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
    tools.r_mapcalc(
        expression="\n".join(
            f"precipitation_heavy_2020_{month:02d} ="
            f" if(precipitation_monthly_2020_{month:02d} >= 200,"
            f" int(precipitation_monthly_2020_{month:02d} / 100), null())"
            for month in months
        )
    )
    tools.t_create(
        output="precipitation_heavy",
        semantictype="max",
        title="Heavy precipitation",
        description="Monthly precipitation of 200 mm and more in classes of 100 mm",
    )
    tools.t_register(
        input="precipitation_heavy",
        maps=",".join(f"precipitation_heavy_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    print(tools.t_rast_list(input="precipitation_monthly", columns="name,max").text)
    ```

    ```text
    name|max
    precipitation_monthly_2020_01|249.0
    precipitation_monthly_2020_02|309.0
    precipitation_monthly_2020_03|212.0
    precipitation_monthly_2020_04|231.0
    precipitation_monthly_2020_05|347.0
    precipitation_monthly_2020_06|163.0
    precipitation_monthly_2020_07|223.0
    precipitation_monthly_2020_08|295.0
    precipitation_monthly_2020_09|181.0
    precipitation_monthly_2020_10|160.0
    precipitation_monthly_2020_11|350.0
    precipitation_monthly_2020_12|177.0
    ```

    ```python
    tools.t_rast_to_vect(
        input="precipitation_heavy", output="rain_areas", basename="rain_area", type="area"
    )
    columns = "name,start_time,areas,centroids"
    print(tools.t_vect_list(input="rain_areas", columns=columns).text)
    print(tools.g_list(type="vector", pattern="rain_area_*", mapset=".").text)
    ```

    ```text
    name|start_time|areas|centroids
    rain_area_2020_01|2020-01-01 00:00:00|1|1
    rain_area_2020_02|2020-02-01 00:00:00|8|8
    rain_area_2020_03|2020-03-01 00:00:00|2|2
    rain_area_2020_04|2020-04-01 00:00:00|1|1
    rain_area_2020_05|2020-05-01 00:00:00|15|7
    rain_area_2020_07|2020-07-01 00:00:00|2|2
    rain_area_2020_08|2020-08-01 00:00:00|7|6
    rain_area_2020_11|2020-11-01 00:00:00|10|9
    rain_area_2020_01
    rain_area_2020_02
    rain_area_2020_03
    rain_area_2020_04
    rain_area_2020_05
    rain_area_2020_07
    rain_area_2020_08
    rain_area_2020_11
    ```

    ```python
    print(
        tools.t_vect_db_select(
            input="rain_areas", columns="value", t_where="start_time < '2020-03-01'"
        ).text
    )
    ```

    ```text
    start_time|end_time|value
    2020-01-01 00:00:00|2020-02-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|2
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    2020-02-01 00:00:00|2020-03-01 00:00:00|3
    ```

    ```python
    print(tools.t_info(type="stvds", input="rain_areas").stdout, end="")
    ```

    ```text
     +-------------------- Space Time Vector Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_areas@t_rast_to_vect
     | Name: ...................... rain_areas
     | Mapset: .................... t_rast_to_vect
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2020-01-01 00:00:00
     | End time:................... 2020-12-01 00:00:00
     | Granularity:................ 1 month
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 318000.0
     | South:...................... 11000.0
     | East:.. .................... 930000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Vector register table:...... vector_map_register_00000000000000000000000000000000
     | Number of points ........... 0
     | Number of lines ............ 0
     | Number of boundaries ....... 54
     | Number of centroids ........ 36
     | Number of faces ............ 0
     | Number of kernels .......... 0
     | Number of primitives ....... 90
     | Number of nodes ............ 47
     | Number of areas ............ 46
     | Number of islands .......... 39
     | Number of holes ............ 0
     | Number of volumes .......... 0
     | Number of registered maps:.. 8
     |
     | Title:
     | Heavy precipitation
     | Description:
     | Monthly precipitation of 200 mm and more in classes of 100 mm
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.to.vect input="precipitation_heavy"
     |     output="rain_areas" basename="rain_area" type="area"
     | 
     +----------------------------------------------------------------------------+
    ```

    ```python
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="rain_areas",
        basename="rain_area",
        type="area",
        flags="n",
        overwrite=True,
    )
    print(tools.t_vect_list(input="rain_areas", columns="name,areas").text)
    ```

    ```text
    name|areas
    rain_area_2020_01|1
    rain_area_2020_02|8
    rain_area_2020_03|2
    rain_area_2020_04|1
    rain_area_2020_05|15
    rain_area_2020_06|0
    rain_area_2020_07|2
    rain_area_2020_08|7
    rain_area_2020_09|0
    rain_area_2020_10|0
    rain_area_2020_11|10
    rain_area_2020_12|0
    ```

### Draw the areas over the raster map

The figure shows the map of May with the boundaries of the areas that
*t.rast.to.vect* made from it. *d.rast* draws the raster map, *d.vect* the
outline of the state from the vector map `nc_state` in grey and the boundaries
of the vector map `rain_area_2020_05` in red, and *d.legend* the two classes.

=== "Command line"

    ```sh
    d.mon start=cairo output=t_rast_to_vect_areas.png width=600 height=400
    d.rast map=precipitation_heavy_2020_05
    d.vect map=nc_state fill_color=none color=gray width=1
    d.vect map=rain_area_2020_05 type=boundary color=red width=2
    d.legend raster=precipitation_heavy_2020_05 at=10,40,84,88 fontsize=14
    d.mon stop=cairo
    ```

=== "Python (grass.tools)"

    ```python
    tools.d_mon(start="cairo", output="t_rast_to_vect_areas.png", width=600, height=400)
    tools.d_rast(map="precipitation_heavy_2020_05")
    tools.d_vect(map="nc_state", fill_color="none", color="gray", width=1)
    tools.d_vect(map="rain_area_2020_05", type="boundary", color="red", width=2)
    tools.d_legend(raster="precipitation_heavy_2020_05", at=[10, 40, 84, 88], fontsize=14)
    tools.d_mon(stop="cairo")
    ```

![Areas of the classes of heavy rain in May 2020 (generated data)](t_rast_to_vect_areas.png)

*Figure: The areas of the classes of heavy rain in May 2020 (generated data),
outlined by the boundaries of the vector map `rain_area_2020_05`.*

### Convert the cells to points

With `type=point`, each cell with a value becomes a point at the centre of
the cell. The example sets the region to the window of 8 by 8 cells. The
condition in **where** selects the map of February, which has 64 cells with
values and so gives 64 points. **column** names the column that holds the class
of each cell, `class` instead of `value`. The second block groups the table by
the class: 32 cells in each class. The third block prints the first two rows
of the table, with the columns `cat`, `class` and `label`.

The flag **-v** takes the class of each cell as the category of the point
instead of a sequence of numbers. The fourth block shows the table of that
map: only the categories 2 and 3, one for each class, and no column for the
value.

The flag **-z** writes the class as the z coordinate of the points and makes
no table. *v.out.ascii* prints the first three points, the cells of the top
row, with class 2 as z coordinate, and the z coordinates of all points, 2 and
3. *v.info* shows that the map has no attribute table.

The last block shows the limit of **-v**. The dataset `precipitation_cm` holds
the map of February in centimetres, with floating point values. With **-v**,
*t.rast.to.vect* warns that the raster is not CELL and that the flag is
ignored; the table has the column `value` with the values of the cells, as
without the flag, not one category for each value.

=== "Command line"

    ```sh
    g.region n=158000 s=150000 e=233000 w=225000 res=1000
    t.rast.to.vect input=precipitation_heavy output=cells basename=cell type=point \
        column=class where="name = 'precipitation_heavy_2020_02'"
    t.vect.list input=cells columns=name,points
    ```

    ```text
    name|points
    cell_2020_02|64
    ```

    ```sh
    db.select sql="SELECT class, count(*) AS cells FROM cell_2020_02 GROUP BY class"
    ```

    ```text
    class|cells
    2|32
    3|32
    ```

    ```sh
    v.db.select map=cell_2020_02 where="cat <= 2"
    ```

    ```text
    cat|class|label
    1|2|
    2|2|
    ```

    ```sh
    t.rast.to.vect -v input=precipitation_heavy output=classes basename=class \
        type=point where="name = 'precipitation_heavy_2020_02'"
    v.db.select map=class_2020_02
    ```

    ```text
    cat|label
    2|
    3|
    ```

    ```sh
    t.rast.to.vect -z input=precipitation_heavy output=heights basename=height \
        type=point where="name = 'precipitation_heavy_2020_02'"
    v.out.ascii input=height_2020_02 format=point separator=space layer=-1 \
        | head -n 3
    v.out.ascii input=height_2020_02 format=point separator=space layer=-1 \
        | cut -d" " -f3 | sort -u | paste -sd,
    v.info -e map=height_2020_02 | grep num_dblinks
    ```

    ```text
    225500 157500 2
    226500 157500 2
    227500 157500 2
    2,3
    num_dblinks=0
    ```

    ```sh
    r.mapcalc expression="precipitation_cm_2020_02 = precipitation_monthly_2020_02 / 10.0"
    t.create output=precipitation_cm title="Precipitation" \
        description="Precipitation sum February 2020 in cm"
    t.register -i input=precipitation_cm maps=precipitation_cm_2020_02 \
        start=2020-02-01 increment="1 month"
    t.rast.to.vect -v input=precipitation_cm output=cm_points basename=cm type=point
    v.db.select map=cm_2020_02 where="cat <= 2"
    ```

    ```text
    cat|value
    1|29.1
    2|29.2
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=158000, s=150000, e=233000, w=225000, res=1000)
    february = "name = 'precipitation_heavy_2020_02'"
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="cells",
        basename="cell",
        type="point",
        column="class",
        where=february,
    )
    print(tools.t_vect_list(input="cells", columns="name,points").text)
    ```

    ```text
    name|points
    cell_2020_02|64
    ```

    ```python
    print(
        tools.db_select(
            sql="SELECT class, count(*) AS cells FROM cell_2020_02 GROUP BY class"
        ).text
    )
    ```

    ```text
    class|cells
    2|32
    3|32
    ```

    ```python
    print(tools.v_db_select(map="cell_2020_02", where="cat <= 2").text)
    ```

    ```text
    cat|class|label
    1|2|
    2|2|
    ```

    ```python
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="classes",
        basename="class",
        type="point",
        where=february,
        flags="v",
    )
    print(tools.v_db_select(map="class_2020_02").text)
    ```

    ```text
    cat|label
    2|
    3|
    ```

    ```python
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="heights",
        basename="height",
        type="point",
        where=february,
        flags="z",
    )
    result = tools.v_out_ascii(
        input="height_2020_02", format="point", separator="space", layer=-1
    )
    points = result.text.splitlines()
    print("\n".join(points[:3]))
    print(",".join(sorted({point.split()[2] for point in points})))
    info = tools.v_info(map="height_2020_02", flags="e").keyval
    print(f"num_dblinks={info['num_dblinks']}")
    ```

    ```text
    225500 157500 2
    226500 157500 2
    227500 157500 2
    2,3
    num_dblinks=0
    ```

    ```python
    tools.r_mapcalc(
        expression="precipitation_cm_2020_02 = precipitation_monthly_2020_02 / 10.0"
    )
    tools.t_create(
        output="precipitation_cm",
        title="Precipitation",
        description="Precipitation sum February 2020 in cm",
    )
    tools.t_register(
        input="precipitation_cm",
        maps="precipitation_cm_2020_02",
        start="2020-02-01",
        increment="1 month",
        flags="i",
    )
    tools.t_rast_to_vect(
        input="precipitation_cm", output="cm_points", basename="cm", type="point", flags="v"
    )
    print(tools.v_db_select(map="cm_2020_02", where="cat <= 2").text)
    ```

    ```text
    cat|value
    1|29.1
    2|29.2
    ```

### Convert thin lines to lines

With `type=line`, *r.to.vect* needs lines that are one cell wide. The dataset
`roads` has two maps in the window: the diagonal from the north-west to the
south-east cell on the first day, and the fourth row on the second day. Each
map gives one line with two nodes, one at the centre of its first and one at
the centre of its last cell. The bounding box of the first line runs from 225500
to 232500 in x and from 150500 to 157500 in y, the second line lies at
y = 154500.

The second block shows what happens with a map that is not thinned. The map of
February fills the whole window, so *r.to.vect* finds no thin lines in it;
*t.rast.to.vect* ends with the message of *r.to.vect* and creates no dataset
`thick`.

=== "Command line"

    ```sh
    r.mapcalc expression="road_diagonal = if(row() == col(), 1, null())"
    r.mapcalc expression="road_fourth_row = if(row() == 4, 1, null())"
    t.create output=roads title="Roads" description="Two roads"
    t.register -i input=roads maps=road_diagonal,road_fourth_row \
        start=2026-07-01 increment="1 day"
    t.rast.to.vect input=roads output=tracks basename=track type=line
    t.vect.list input=tracks columns=name,lines,nodes,west,east,south,north
    ```

    ```text
    name|lines|nodes|west|east|south|north
    track_2026_07_01|1|2|225500.0|232500.0|150500.0|157500.0
    track_2026_07_02|1|2|225500.0|232500.0|154500.0|154500.0
    ```

    ```sh
    t.rast.to.vect input=precipitation_heavy output=thick basename=thick type=line \
        where="name = 'precipitation_heavy_2020_02'" --quiet 2>&1 \
        || echo "t.rast.to.vect failed"
    ```

    ```text
    r.to.vect input=precipitation_heavy_2020_02@t_rast_to_vect type=line column=value output=thick_2020_02@t_rast_to_vect --q
    ERROR: Raster map is not thinned properly.
           Please run r.thin.
    ERROR: Error running r.to.vect: Module run `r.to.vect
           input=precipitation_heavy_2020_02@t_rast_to_vect type=line
           column=value output=thick_2020_02@t_rast_to_vect --q` ended with an
           error.
           The subprocess ended with a non-zero return code: 1. See errors
           above the traceback or in the error output.
    t.rast.to.vect failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="road_diagonal = if(row() == col(), 1, null())")
    tools.r_mapcalc(expression="road_fourth_row = if(row() == 4, 1, null())")
    tools.t_create(output="roads", title="Roads", description="Two roads")
    tools.t_register(
        input="roads",
        maps="road_diagonal,road_fourth_row",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_to_vect(input="roads", output="tracks", basename="track", type="line")
    result = tools.t_vect_list(
        input="tracks", columns="name,lines,nodes,west,east,south,north"
    )
    print(result.text)
    ```

    ```text
    name|lines|nodes|west|east|south|north
    track_2026_07_01|1|2|225500.0|232500.0|150500.0|157500.0
    track_2026_07_02|1|2|225500.0|232500.0|154500.0|154500.0
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_rast_to_vect(
            input="precipitation_heavy",
            output="thick",
            basename="thick",
            type="line",
            where=february,
            quiet=True,
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.to.vect failed")
    ```

    ```text
    r.to.vect input=precipitation_heavy_2020_02@t_rast_to_vect type=line column=value output=thick_2020_02@t_rast_to_vect --q
    ERROR: Raster map is not thinned properly.
           Please run r.thin.
    ERROR: Error running r.to.vect: Module run `r.to.vect
           input=precipitation_heavy_2020_02@t_rast_to_vect type=line
           column=value output=thick_2020_02@t_rast_to_vect --q` ended with an
           error.
           The subprocess ended with a non-zero return code: 1. See errors
           above the traceback or in the error output.
    t.rast.to.vect failed
    ```

### Smooth the corners and skip the topology

The map `stairs_triangle` is a triangle in the south-west of the window: the
cells with `row() >= col()`. Its outline is a staircase. The first block converts
it to an area twice, without and with the flag **-s**. *v.out.ascii* starts the
boundary of each area with `B` and the number of its points: 19 points for
the staircase, 22 for the smoothed outline, because **-s** cuts the corners.

The flag **-b** builds no topology. The second block converts the map with
**-b**: the topological counts of the map, such as the number of areas, are
not known, and *t.vect.list* shows `None` for them. *ls* lists the files of
the vector maps: the map made with **-b** has none of the topology files
`topo`, `sidx` and `cidx`.

=== "Command line"

    ```sh
    r.mapcalc expression="stairs_triangle = if(row() >= col(), 1, null())"
    t.create output=stairs title="Stairs" description="A staircase"
    t.register -i input=stairs maps=stairs_triangle \
        start=2026-07-01 increment="1 day"
    t.rast.to.vect input=stairs output=sharp basename=sharp type=area
    t.rast.to.vect -s input=stairs output=smooth basename=smooth type=area
    v.out.ascii input=sharp_2026_07_01 format=standard layer=-1 | grep "^B"
    v.out.ascii input=smooth_2026_07_01 format=standard layer=-1 | grep "^B"
    ```

    ```text
    B  19
    B  22
    ```

    ```sh
    t.rast.to.vect -b input=stairs output=flat basename=flat type=area
    t.vect.list input=flat columns=name,areas
    ls -m "$(g.findfile -n element=vector file=flat_2026_07_01 | sed -n 's/^file=//p')"
    ls -m "$(g.findfile -n element=vector file=sharp_2026_07_01 | sed -n 's/^file=//p')"
    ```

    ```text
    name|areas
    flat_2026_07_01|None
    coor, dbln, head, hist, timestamp_1
    cidx, coor, dbln, head, hist, sidx, timestamp_1, topo
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    tools.r_mapcalc(expression="stairs_triangle = if(row() >= col(), 1, null())")
    tools.t_create(output="stairs", title="Stairs", description="A staircase")
    tools.t_register(
        input="stairs",
        maps="stairs_triangle",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_to_vect(input="stairs", output="sharp", basename="sharp", type="area")
    tools.t_rast_to_vect(
        input="stairs", output="smooth", basename="smooth", type="area", flags="s"
    )
    for name in ("sharp_2026_07_01", "smooth_2026_07_01"):
        result = tools.v_out_ascii(input=name, format="standard", layer=-1)
        print([line for line in result.text.splitlines() if line.startswith("B")][0])
    ```

    ```text
    B  19
    B  22
    ```

    ```python
    tools.t_rast_to_vect(
        input="stairs", output="flat", basename="flat", type="area", flags="b"
    )
    print(tools.t_vect_list(input="flat", columns="name,areas").text)
    for name in ("flat_2026_07_01", "sharp_2026_07_01"):
        path = tools.g_findfile(element="vector", file=name, flags="n").keyval["file"]
        print(", ".join(sorted(item.name for item in Path(path).iterdir())))
    ```

    ```text
    name|areas
    flat_2026_07_01|None
    coor, dbln, head, hist, timestamp_1
    cidx, coor, dbln, head, hist, sidx, timestamp_1, topo
    ```

### Choose the names of the new maps and convert in parallel

The option **suffix** chooses how the new maps are named after **basename**.
The condition in **where** selects the first two months, and the numbers count
the selected maps from 1:

1. `time` takes the full start time of each raster map.
2. `num%03` numbers the maps with three digits.
3. In a dataset with relative time, the suffix is always a number. The
   dataset `model` holds the maps of January and February as the steps 1 and 2
   of a model run, six hours apart; the default suffix `gran` numbers the
   maps, and the new dataset has relative time as well.

The last block uses the flag **-t**: the vector maps get no attribute table,
and **nprocs** can run several *r.to.vect* processes at the same time; here
three, one for each of the months January to March. The map of January and
that of February have a value in all 64 cells of the window and give 64
points. In March, 25 cells are below 200 mm and null, so the map gives 39
points. *v.info* shows that the map of January is linked to no attribute table.

=== "Command line"

    ```sh
    t.rast.to.vect input=precipitation_heavy output=timed basename=timed type=area \
        suffix=time where="start_time < '2020-03-01'"
    t.vect.list input=timed columns=name
    t.rast.to.vect input=precipitation_heavy output=numbered basename=zone type=area \
        suffix=num%03 where="start_time < '2020-03-01'"
    t.vect.list input=numbered columns=name
    ```

    ```text
    name
    timed_2020_01_01T00_00_00
    timed_2020_02_01T00_00_00
    name
    zone_001
    zone_002
    ```

    ```sh
    r.mapcalc expression="model_step_1 = precipitation_heavy_2020_01"
    r.mapcalc expression="model_step_2 = precipitation_heavy_2020_02"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=model_step_1,model_step_2 start=0 increment=6 \
        unit=hours
    t.rast.to.vect input=model output=steps basename=step type=area
    t.vect.list input=steps columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    step_00001|0|6|1
    step_00002|6|12|2
    ```

    ```sh
    t.rast.to.vect -t input=precipitation_heavy output=quick basename=quick \
        type=point nprocs=3 where="start_time < '2020-04-01'"
    t.vect.list input=quick columns=name,points
    v.info -e map=quick_2020_01 | grep num_dblinks
    ```

    ```text
    name|points
    quick_2020_01|64
    quick_2020_02|64
    quick_2020_03|39
    num_dblinks=0
    ```

=== "Python (grass.tools)"

    ```python
    first_months = "start_time < '2020-03-01'"
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="timed",
        basename="timed",
        type="area",
        suffix="time",
        where=first_months,
    )
    print(tools.t_vect_list(input="timed", columns="name").text)
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="numbered",
        basename="zone",
        type="area",
        suffix="num%03",
        where=first_months,
    )
    print(tools.t_vect_list(input="numbered", columns="name").text)
    ```

    ```text
    name
    timed_2020_01_01T00_00_00
    timed_2020_02_01T00_00_00
    name
    zone_001
    zone_002
    ```

    ```python
    tools.r_mapcalc(expression="model_step_1 = precipitation_heavy_2020_01")
    tools.r_mapcalc(expression="model_step_2 = precipitation_heavy_2020_02")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model",
        maps="model_step_1,model_step_2",
        start=0,
        increment=6,
        unit="hours",
        flags="i",
    )
    tools.t_rast_to_vect(input="model", output="steps", basename="step", type="area")
    result = tools.t_vect_list(input="steps", columns="name,start_time,end_time,areas")
    print(result.text)
    ```

    ```text
    name|start_time|end_time|areas
    step_00001|0|6|1
    step_00002|6|12|2
    ```

    ```python
    tools.t_rast_to_vect(
        input="precipitation_heavy",
        output="quick",
        basename="quick",
        type="point",
        nprocs=3,
        where="start_time < '2020-04-01'",
        flags="t",
    )
    print(tools.t_vect_list(input="quick", columns="name,points").text)
    info = tools.v_info(map="quick_2020_01", flags="e").keyval
    print(f"num_dblinks={info['num_dblinks']}")
    ```

    ```text
    name|points
    quick_2020_01|64
    quick_2020_02|64
    quick_2020_03|39
    num_dblinks=0
    ```

### Use a dataset of another mapset

The example creates the mapset `t_rast_to_vect_2`, sets the region of North
Carolina as in the first example and adds the mapset `t_rast_to_vect` to the
search path with *g.mapsets*, so that it can read the dataset. The dataset
`precipitation_heavy` stays in the mapset `t_rast_to_vect` and is named with its
mapset; the new dataset `west` and its vector maps are created in
`t_rast_to_vect_2`, as the column `id` shows.

The region of the new mapset is then set to the western half of the window, so
*r.to.vect* converts only the cells of the western half: the east edge of the
vector maps lies at x = 229000. The map of January has one area, class 2; the map
of February has two, the classes 2 and 3.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_to_vect_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_rast_to_vect operation=add
    g.region n=158000 s=150000 e=229000 w=225000 res=1000
    t.rast.to.vect input=precipitation_heavy@t_rast_to_vect output=west basename=west \
        type=area where="start_time < '2020-03-01'"
    t.vect.list input=west columns=id,areas,east
    ```

    ```text
    id|areas|east
    west_2020_01@t_rast_to_vect_2|1|229000.0
    west_2020_02@t_rast_to_vect_2|2|229000.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="t_rast_to_vect_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_rast_to_vect", operation="add")
    tools.g_region(n=158000, s=150000, e=229000, w=225000, res=1000)
    tools.t_rast_to_vect(
        input="precipitation_heavy@t_rast_to_vect",
        output="west",
        basename="west",
        type="area",
        where="start_time < '2020-03-01'",
    )
    print(tools.t_vect_list(input="west", columns="id,areas,east").text)
    ```

    ```text
    id|areas|east
    west_2020_01@t_rast_to_vect_2|1|229000.0
    west_2020_02@t_rast_to_vect_2|2|229000.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[d.legend](d.legend.md), [d.rast](d.rast.md), [d.vect](d.vect.md),
[db.select](db.select.md), [g.findfile](g.findfile.md), [g.list](g.list.md),
[g.mapset](g.mapset.md), [g.region](g.region.md), [r.thin](r.thin.md),
[r.to.vect](r.to.vect.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.contour](t.rast.contour.md), [t.register](t.register.md),
[t.vect.db.select](t.vect.db.select.md), [t.vect.list](t.vect.list.md),
[v.db.select](v.db.select.md), [v.info](v.info.md),
[v.out.ascii](v.out.ascii.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Geoinformatikbüro Dassau
