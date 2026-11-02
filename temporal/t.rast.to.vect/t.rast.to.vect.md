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
  granularity of the input dataset: `2026_07_01` in a dataset of days. A
  dataset of a single time instance has no granularity; `gran` then takes the
  full start time, as `time` does.
- `time` takes the full start time: `2026_07_01T00_00_00`.
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
mapset (`input=cover@PERMANENT`) selects it. The new vector maps and the new
dataset are always created in the current mapset, as the last example shows.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Convert the maps of a dataset to areas

The dataset `cover` holds the land cover classes of a region of 8 by 8 cells
on three days in July. On the first day, the western half of the region has
class 1 and the eastern half class 2. On the second day, the classes 1 to 4
are the four quadrants of 16 cells each: 1 in the north-west, 2 in the
north-east, 3 in the south-west and 4 in the south-east. On the third day, the
map has no values.

With `type=area`, the first map gives 2 areas and the second 4. The third map
gives no feature: its vector map is empty and *t.rast.to.vect* removes it, so
two vector maps are registered, as *g.list* shows. The default suffix `gran`
names the maps after the day. The second block prints the values from the
attribute tables with *[t.vect.db.select](t.vect.db.select.md)*: one row for
each area, in the default column `value`. The third block shows with
*[t.info](t.info.md)* that the new dataset `parcels` has the time, the
semantic type `max`, the title and the description of the input dataset, and
2 + 4 = 6 areas.

In the fourth block, the flag **-n** keeps the empty map of the third day, and
**--overwrite** replaces the dataset `parcels` of the first block together
with its vector maps.

=== "Command line"

    ```sh
    g.region n=8 s=0 e=8 w=0 res=1
    r.mapcalc expression="cover_1 = if(col() <= 4, 1, 2)"
    r.mapcalc expression="cover_2 = 1 + if(col() > 4, 1, 0) + if(row() > 4, 2, 0)"
    r.mapcalc expression="cover_3 = null()"
    t.create output=cover semantictype=max title="Land cover" \
        description="Land cover classes"
    t.register -i input=cover maps=cover_1,cover_2,cover_3 \
        start=2026-07-01 increment="1 day"
    t.rast.to.vect input=cover output=parcels basename=parcel type=area
    t.vect.list input=parcels columns=name,start_time,end_time,areas
    g.list type=vector pattern="parcel_*"
    ```

    ```text
    name|start_time|end_time|areas
    parcel_2026_07_01|2026-07-01 00:00:00|2026-07-02 00:00:00|2
    parcel_2026_07_02|2026-07-02 00:00:00|2026-07-03 00:00:00|4
    parcel_2026_07_01
    parcel_2026_07_02
    ```

    ```sh
    t.vect.db.select input=parcels columns=value
    ```

    ```text
    start_time|end_time|value
    2026-07-01 00:00:00|2026-07-02 00:00:00|1
    2026-07-01 00:00:00|2026-07-02 00:00:00|2
    2026-07-02 00:00:00|2026-07-03 00:00:00|1
    2026-07-02 00:00:00|2026-07-03 00:00:00|2
    2026-07-02 00:00:00|2026-07-03 00:00:00|3
    2026-07-02 00:00:00|2026-07-03 00:00:00|4
    ```

    ```sh
    t.info type=stvds input=parcels
    ```

    ```text
     +-------------------- Space Time Vector Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ parcels@PERMANENT
     | Name: ...................... parcels
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-07-01 00:00:00
     | End time:................... 2026-07-03 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 8.0
     | South:...................... 0.0
     | East:.. .................... 8.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Vector register table:...... vector_map_register_00000000000000000000000000000000
     | Number of points ........... 0
     | Number of lines ............ 0
     | Number of boundaries ....... 11
     | Number of centroids ........ 6
     | Number of faces ............ 0
     | Number of kernels .......... 0
     | Number of primitives ....... 17
     | Number of nodes ............ 7
     | Number of areas ............ 6
     | Number of islands .......... 2
     | Number of holes ............ 0
     | Number of volumes .......... 0
     | Number of registered maps:.. 2
     |
     | Title:
     | Land cover
     | Description:
     | Land cover classes
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.to.vect input="cover" output="parcels"
     |     basename="parcel" type="area"
     | 
     +----------------------------------------------------------------------------+
    ```

    ```sh
    t.rast.to.vect -n input=cover output=parcels basename=parcel type=area \
        --overwrite
    t.vect.list input=parcels columns=name,areas
    ```

    ```text
    name|areas
    parcel_2026_07_01|2
    parcel_2026_07_02|4
    parcel_2026_07_03|0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=8, s=0, e=8, w=0, res=1)
    tools.r_mapcalc(expression="cover_1 = if(col() <= 4, 1, 2)")
    tools.r_mapcalc(expression="cover_2 = 1 + if(col() > 4, 1, 0) + if(row() > 4, 2, 0)")
    tools.r_mapcalc(expression="cover_3 = null()")
    tools.t_create(
        output="cover",
        semantictype="max",
        title="Land cover",
        description="Land cover classes",
    )
    tools.t_register(
        input="cover",
        maps="cover_1,cover_2,cover_3",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_to_vect(input="cover", output="parcels", basename="parcel", type="area")
    result = tools.t_vect_list(input="parcels", columns="name,start_time,end_time,areas")
    print(result.text)
    print(tools.g_list(type="vector", pattern="parcel_*").text)
    ```

    ```text
    name|start_time|end_time|areas
    parcel_2026_07_01|2026-07-01 00:00:00|2026-07-02 00:00:00|2
    parcel_2026_07_02|2026-07-02 00:00:00|2026-07-03 00:00:00|4
    parcel_2026_07_01
    parcel_2026_07_02
    ```

    ```python
    print(tools.t_vect_db_select(input="parcels", columns="value").text)
    ```

    ```text
    start_time|end_time|value
    2026-07-01 00:00:00|2026-07-02 00:00:00|1
    2026-07-01 00:00:00|2026-07-02 00:00:00|2
    2026-07-02 00:00:00|2026-07-03 00:00:00|1
    2026-07-02 00:00:00|2026-07-03 00:00:00|2
    2026-07-02 00:00:00|2026-07-03 00:00:00|3
    2026-07-02 00:00:00|2026-07-03 00:00:00|4
    ```

    ```python
    print(tools.t_info(type="stvds", input="parcels").stdout, end="")
    ```

    ```text
     +-------------------- Space Time Vector Dataset -----------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ parcels@PERMANENT
     | Name: ...................... parcels
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. max
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-07-01 00:00:00
     | End time:................... 2026-07-03 00:00:00
     | Granularity:................ 1 day
     | Temporal type of maps:...... interval
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 8.0
     | South:...................... 0.0
     | East:.. .................... 8.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Vector register table:...... vector_map_register_00000000000000000000000000000000
     | Number of points ........... 0
     | Number of lines ............ 0
     | Number of boundaries ....... 11
     | Number of centroids ........ 6
     | Number of faces ............ 0
     | Number of kernels .......... 0
     | Number of primitives ....... 17
     | Number of nodes ............ 7
     | Number of areas ............ 6
     | Number of islands .......... 2
     | Number of holes ............ 0
     | Number of volumes .......... 0
     | Number of registered maps:.. 2
     |
     | Title:
     | Land cover
     | Description:
     | Land cover classes
     | Command history:
     | # 2026-11-01 12:00:00 
     | t.rast.to.vect input="cover" output="parcels"
     |     basename="parcel" type="area"
     | 
     +----------------------------------------------------------------------------+
    ```

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="parcels",
        basename="parcel",
        type="area",
        flags="n",
        overwrite=True,
    )
    print(tools.t_vect_list(input="parcels", columns="name,areas").text)
    ```

    ```text
    name|areas
    parcel_2026_07_01|2
    parcel_2026_07_02|4
    parcel_2026_07_03|0
    ```

### Draw the areas over the raster map

The figure shows the map of the second day with the boundaries of the areas
that *t.rast.to.vect* made from it. *d.rast* draws the raster map, *d.vect*
the boundaries of the vector map and *d.legend* the four classes.

=== "Command line"

    ```sh
    d.mon start=cairo output=t_rast_to_vect_areas.png width=600 height=400
    d.rast map=cover_2
    d.vect map=parcel_2026_07_02 type=boundary color=white width=3
    d.legend raster=cover_2 at=10,90,84,88 fontsize=14
    d.mon stop=cairo
    ```

=== "Python (grass.tools)"

    ```python
    tools.d_mon(start="cairo", output="t_rast_to_vect_areas.png", width=600, height=400)
    tools.d_rast(map="cover_2")
    tools.d_vect(map="parcel_2026_07_02", type="boundary", color="white", width=3)
    tools.d_legend(raster="cover_2", at=[10, 90, 84, 88], fontsize=14)
    tools.d_mon(stop="cairo")
    ```

![Areas of the land cover classes](t_rast_to_vect_areas.png)

*Figure: The four areas of the land cover map `cover_2`, outlined by the
boundaries of the vector map `parcel_2026_07_02`.*

### Convert the cells to points

With `type=point`, each cell with a value becomes a point at the centre of
the cell. The condition in **where** selects the first map, which has 64 cells
with values and so gives 64 points. **column** names the column that holds
the class of each cell, `class` instead of `value`. The second block groups
the table by the class: 32 cells in each half of the map. The third block
prints the first two rows of the table, with the columns `cat`, `class` and
`label`.

The flag **-v** takes the class of each cell as the category of the point
instead of a sequence of numbers. The fourth block shows the table of that
map: only the categories 1 and 2, one for each class, and no column for the
value.

The flag **-z** writes the class as the z coordinate of the points and makes
no table. The fifth block converts the second map, whose classes are 1 to 4.
*v.out.ascii* prints the first three points, the cells of the top row, with
class 1 as z coordinate, and the z coordinates of all points, 1 to 4.
*v.info* shows that the map has no attribute table.

The last block shows the limit of **-v**. The dataset `ratio` holds the map
`ratio_1` with the floating point values 0.5 and 1. With **-v**,
*t.rast.to.vect* warns that the raster is not CELL and that the flag is
ignored; the table has the column `value` with the values of the cells, as
without the flag, not one category for each value.

=== "Command line"

    ```sh
    t.rast.to.vect input=cover output=cells basename=cell type=point \
        column=class where="start_time < '2026-07-02'"
    t.vect.list input=cells columns=name,points
    ```

    ```text
    name|points
    cell_2026_07_01|64
    ```

    ```sh
    db.select sql="SELECT class, count(*) AS cells FROM cell_2026_07_01 GROUP BY class"
    ```

    ```text
    class|cells
    1|32
    2|32
    ```

    ```sh
    v.db.select map=cell_2026_07_01 where="cat <= 2"
    ```

    ```text
    cat|class|label
    1|1|
    2|1|
    ```

    ```sh
    t.rast.to.vect -v input=cover output=classes basename=class type=point \
        where="start_time < '2026-07-02'"
    v.db.select map=class_2026_07_01
    ```

    ```text
    cat|label
    1|
    2|
    ```

    ```sh
    t.rast.to.vect -z input=cover output=heights basename=height type=point \
        where="name = 'cover_2'"
    v.out.ascii input=height_2026_07_02 format=point separator=space layer=-1 \
        | head -n 3
    v.out.ascii input=height_2026_07_02 format=point separator=space layer=-1 \
        | cut -d" " -f3 | sort -u | paste -sd,
    v.info -e map=height_2026_07_02 | grep num_dblinks
    ```

    ```text
    0.5 7.5 1
    1.5 7.5 1
    2.5 7.5 1
    1,2,3,4
    num_dblinks=0
    ```

    ```sh
    r.mapcalc expression="ratio_1 = cover_1 / 2.0"
    t.create output=ratio title="Ratio" description="Half of the class"
    t.register -i input=ratio maps=ratio_1 start=2026-07-01 increment="1 day"
    t.rast.to.vect -v input=ratio output=ratios basename=ratio type=point
    v.db.select map=ratio_2026_07_01 where="cat <= 2"
    ```

    ```text
    cat|value
    1|0.5
    2|0.5
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="cells",
        basename="cell",
        type="point",
        column="class",
        where="start_time < '2026-07-02'",
    )
    print(tools.t_vect_list(input="cells", columns="name,points").text)
    ```

    ```text
    name|points
    cell_2026_07_01|64
    ```

    ```python
    print(
        tools.db_select(
            sql="SELECT class, count(*) AS cells FROM cell_2026_07_01 GROUP BY class"
        ).text
    )
    ```

    ```text
    class|cells
    1|32
    2|32
    ```

    ```python
    print(tools.v_db_select(map="cell_2026_07_01", where="cat <= 2").text)
    ```

    ```text
    cat|class|label
    1|1|
    2|1|
    ```

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="classes",
        basename="class",
        type="point",
        where="start_time < '2026-07-02'",
        flags="v",
    )
    print(tools.v_db_select(map="class_2026_07_01").text)
    ```

    ```text
    cat|label
    1|
    2|
    ```

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="heights",
        basename="height",
        type="point",
        where="name = 'cover_2'",
        flags="z",
    )
    result = tools.v_out_ascii(
        input="height_2026_07_02", format="point", separator="space", layer=-1
    )
    points = result.text.splitlines()
    print("\n".join(points[:3]))
    print(",".join(sorted({point.split()[2] for point in points})))
    info = tools.v_info(map="height_2026_07_02", flags="e").keyval
    print(f"num_dblinks={info['num_dblinks']}")
    ```

    ```text
    0.5 7.5 1
    1.5 7.5 1
    2.5 7.5 1
    1,2,3,4
    num_dblinks=0
    ```

    ```python
    tools.r_mapcalc(expression="ratio_1 = cover_1 / 2.0")
    tools.t_create(output="ratio", title="Ratio", description="Half of the class")
    tools.t_register(
        input="ratio",
        maps="ratio_1",
        start="2026-07-01",
        increment="1 day",
        flags="i",
    )
    tools.t_rast_to_vect(
        input="ratio", output="ratios", basename="ratio", type="point", flags="v"
    )
    print(tools.v_db_select(map="ratio_2026_07_01", where="cat <= 2").text)
    ```

    ```text
    cat|value
    1|0.5
    2|0.5
    ```

### Convert thin lines to lines

With `type=line`, *r.to.vect* needs lines that are one cell wide. The
dataset `roads` has two maps: the diagonal from the north-west to the
south-east cell on the first day, and the fourth row on the second day. Each
map gives one line with two nodes, one at the centre of its first and one at
the centre of its last cell. The bounding box of the first line runs from 0.5
to 7.5 in both directions, the second line lies at y = 4.5.

The second block shows what happens with a map that is not thinned. The
first map of `cover` fills the whole region, so *r.to.vect* finds no thin
lines in it; *t.rast.to.vect* ends with the message of *r.to.vect* and creates
no dataset `thick`.

=== "Command line"

    ```sh
    r.mapcalc expression="road_1 = if(row() == col(), 1, null())"
    r.mapcalc expression="road_2 = if(row() == 4, 1, null())"
    t.create output=roads title="Roads" description="Two roads"
    t.register -i input=roads maps=road_1,road_2 \
        start=2026-07-01 increment="1 day"
    t.rast.to.vect input=roads output=tracks basename=track type=line
    t.vect.list input=tracks columns=name,lines,nodes,west,east,south,north
    ```

    ```text
    name|lines|nodes|west|east|south|north
    track_2026_07_01|1|2|0.5|7.5|0.5|7.5
    track_2026_07_02|1|2|0.5|7.5|4.5|4.5
    ```

    ```sh
    t.rast.to.vect input=cover output=thick basename=thick type=line \
        --quiet 2>&1 || echo "t.rast.to.vect failed"
    ```

    ```text
    r.to.vect input=cover_1@PERMANENT type=line column=value output=thick_2026_07_01@PERMANENT --q
    ERROR: Raster map is not thinned properly.
           Please run r.thin.
    ERROR: Error running r.to.vect: Module run `r.to.vect
           input=cover_1@PERMANENT type=line column=value
           output=thick_2026_07_01@PERMANENT --q` ended with an error.
           The subprocess ended with a non-zero return code: 1. See errors
           above the traceback or in the error output.
    t.rast.to.vect failed
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="road_1 = if(row() == col(), 1, null())")
    tools.r_mapcalc(expression="road_2 = if(row() == 4, 1, null())")
    tools.t_create(output="roads", title="Roads", description="Two roads")
    tools.t_register(
        input="roads",
        maps="road_1,road_2",
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
    track_2026_07_01|1|2|0.5|7.5|0.5|7.5
    track_2026_07_02|1|2|0.5|7.5|4.5|4.5
    ```

    ```python
    from grass.tools import ToolError

    try:
        tools.t_rast_to_vect(
            input="cover", output="thick", basename="thick", type="line", quiet=True
        )
    except ToolError as error:
        print(error.stderr.strip())
        print("t.rast.to.vect failed")
    ```

    ```text
    r.to.vect input=cover_1@PERMANENT type=line column=value output=thick_2026_07_01@PERMANENT --q
    ERROR: Raster map is not thinned properly.
           Please run r.thin.
    ERROR: Error running r.to.vect: Module run `r.to.vect
           input=cover_1@PERMANENT type=line column=value
           output=thick_2026_07_01@PERMANENT --q` ended with an error.
           The subprocess ended with a non-zero return code: 1. See errors
           above the traceback or in the error output.
    t.rast.to.vect failed
    ```

### Smooth the corners and skip the topology

The map `stairs_1` is a triangle in the south-west of the region: the cells
with `row() >= col()`. Its outline is a staircase. The first block converts it
to an area twice, without and with the flag **-s**. *v.out.ascii* starts the
boundary of each area with `B` and the number of its points: 19 points for
the staircase, 22 for the smoothed outline, because **-s** cuts the corners.

The flag **-b** builds no topology. The second block converts the map with
**-b**: the topological counts of the map, such as the number of areas, are
not known, and *t.vect.list* shows `None` for them. *ls* lists the files of
the vector maps: the map made with **-b** has none of the topology files
`topo`, `sidx` and `cidx`.

=== "Command line"

    ```sh
    r.mapcalc expression="stairs_1 = if(row() >= col(), 1, null())"
    t.create output=stairs title="Stairs" description="A staircase"
    t.register -i input=stairs maps=stairs_1 \
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

    tools.r_mapcalc(expression="stairs_1 = if(row() >= col(), 1, null())")
    tools.t_create(output="stairs", title="Stairs", description="A staircase")
    tools.t_register(
        input="stairs",
        maps="stairs_1",
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
The condition in **where** selects the first two days, and the numbers count
the selected maps from 1:

1. `time` takes the full start time of each raster map.
2. `num%03` numbers the maps with three digits.
3. In a dataset with relative time, the suffix is always a number. The
   dataset `model` holds the first two maps of `cover` as the steps 1 and 2
   of a model run, six hours apart; the default suffix `gran` numbers the
   maps, and the new dataset has relative time as well.

The last block uses the flag **-t**: the vector maps get no attribute table,
and **nprocs** can run several *r.to.vect* processes at the same time; here
three, one for each map. *v.info* shows that the map of the first day is
linked to no attribute table.

=== "Command line"

    ```sh
    t.rast.to.vect input=cover output=timed basename=timed type=area \
        suffix=time where="start_time < '2026-07-03'"
    t.vect.list input=timed columns=name
    t.rast.to.vect input=cover output=numbered basename=zone type=area \
        suffix=num%03 where="start_time < '2026-07-03'"
    t.vect.list input=numbered columns=name
    ```

    ```text
    name
    timed_2026_07_01T00_00_00
    timed_2026_07_02T00_00_00
    name
    zone_001
    zone_002
    ```

    ```sh
    r.mapcalc expression="step_1 = cover_1"
    r.mapcalc expression="step_2 = cover_2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=6 unit=hours
    t.rast.to.vect input=model output=steps basename=step type=area
    t.vect.list input=steps columns=name,start_time,end_time,areas
    ```

    ```text
    name|start_time|end_time|areas
    step_00001|0|6|2
    step_00002|6|12|4
    ```

    ```sh
    t.rast.to.vect -t input=cover output=quick basename=quick type=point \
        nprocs=3
    t.vect.list input=quick columns=name,points
    v.info -e map=quick_2026_07_01 | grep num_dblinks
    ```

    ```text
    name|points
    quick_2026_07_01|64
    quick_2026_07_02|64
    num_dblinks=0
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="timed",
        basename="timed",
        type="area",
        suffix="time",
        where="start_time < '2026-07-03'",
    )
    print(tools.t_vect_list(input="timed", columns="name").text)
    tools.t_rast_to_vect(
        input="cover",
        output="numbered",
        basename="zone",
        type="area",
        suffix="num%03",
        where="start_time < '2026-07-03'",
    )
    print(tools.t_vect_list(input="numbered", columns="name").text)
    ```

    ```text
    name
    timed_2026_07_01T00_00_00
    timed_2026_07_02T00_00_00
    name
    zone_001
    zone_002
    ```

    ```python
    tools.r_mapcalc(expression="step_1 = cover_1")
    tools.r_mapcalc(expression="step_2 = cover_2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model",
        maps="step_1,step_2",
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
    step_00001|0|6|2
    step_00002|6|12|4
    ```

    ```python
    tools.t_rast_to_vect(
        input="cover",
        output="quick",
        basename="quick",
        type="point",
        nprocs=3,
        flags="t",
    )
    print(tools.t_vect_list(input="quick", columns="name,points").text)
    info = tools.v_info(map="quick_2026_07_01", flags="e").keyval
    print(f"num_dblinks={info['num_dblinks']}")
    ```

    ```text
    name|points
    quick_2026_07_01|64
    quick_2026_07_02|64
    num_dblinks=0
    ```

### Use a dataset of another mapset

The example creates the mapset `analysis` and switches to it. The dataset
`cover` stays in the mapset `PERMANENT` and is named with its mapset; the new
dataset `west` and its vector maps are created in `analysis`, as the column
`id` shows.

The region of the new mapset is set to the western half of the maps, so
*r.to.vect* converts only the cells of the western half: the east edge of the
vector maps lies at x = 4. The first map has one area, class 1; the second
has two, the classes 1 and 3.

=== "Command line"

    ```sh
    g.mapset -c mapset=analysis
    g.region n=8 s=0 e=4 w=0 res=1
    t.rast.to.vect input=cover@PERMANENT output=west basename=west type=area
    t.vect.list input=west columns=id,areas,east
    ```

    ```text
    id|areas|east
    west_2026_07_01@analysis|1|4.0
    west_2026_07_02@analysis|2|4.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_mapset(mapset="analysis", flags="c")
    tools.g_region(n=8, s=0, e=4, w=0, res=1)
    tools.t_rast_to_vect(
        input="cover@PERMANENT", output="west", basename="west", type="area"
    )
    print(tools.t_vect_list(input="west", columns="id,areas,east").text)
    ```

    ```text
    id|areas|east
    west_2026_07_01@analysis|1|4.0
    west_2026_07_02@analysis|2|4.0
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
