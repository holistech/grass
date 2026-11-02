## DESCRIPTION

*t.vect.import* imports an archive that *[t.vect.export](t.vect.export.md)*
wrote: it unpacks the archive, imports the vector maps and registers them in a
new space time vector dataset with the times of the archive. The archive moves
a dataset from another project or computer into the current project, if that
project has a coordinate reference system (see the notes). See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool for space time raster datasets is
*[t.rast.import](t.rast.import.md)*; *t.vect.import* refuses the archive of a
raster dataset.

The option **input** names the archive, and **output** the new space time vector
dataset, which is made in the current mapset. The compression of the archive
(`bzip2`, `gzip` or none) and the format of the maps in it (`GML`, `GPKG` or
`pack`) are found out from the archive. The maps of a `GML` or `GPKG` archive
are imported with *[v.in.ogr](v.in.ogr.md)*, those of a `pack` archive with
*[v.unpack](v.unpack.md)*. The temporal type, the unit of relative time and the
times of the maps come from the archive, too. The options **title** and
**description** set the title and the description of the new dataset.

### Names of the maps

Without **basename**, each map keeps the name it has in the archive. The
option **basename** names the maps `basename_1`, `basename_2` and so on, with
a numerical suffix in the order of the maps in the archive. This is the way to
import a dataset into the project it was exported from, where the names of the
archive are taken. A map of the same name in the current mapset is refused (see
the notes).

### Projection and new projects

The option **project** makes a new project with the coordinate reference system
of the archive in the GRASS database of the session and imports into it. When
the import is over, the session is in the
project and mapset it was in before. The flag **-c** makes the project and
imports nothing; the archive is needed even then, because the new project takes
its coordinate reference system from it.

The tool compares the coordinate reference system of the archive with that of
the project, but unlike *t.rast.import* it never stops at a difference: it
warns `Projection information does not match. Proceeding...`, with and without
**-o**, and imports the maps without reprojecting them. They keep their
coordinates (see the example "Import into a project with another coordinate
reference system"). Without **-o**, the tool gives a second warning, that
re-projection is not supported and that it ignores the projection information
of the archive. The flag **-o** assumes that the archive has the coordinate
reference system of the current project and leaves out only this second
warning.

The flag **-e** extends the extent of the project to the imported maps: it
makes the default region and the current region of the project cover them. With
**project**, the flag is always on, so the new project has the extent of the
maps. This holds for all formats of the archive, `pack` as well.

### Files and layers

The option **directory** names the directory that the archive is extracted to.
It is required and must exist, and the extracted files stay in it. For a `GML`
archive these are the files that *v.in.ogr* reads (see the example with the
archive formats).

A vector map of a `GML` archive has one layer, which is layer 1 of the imported
map. A `pack` archive holds the whole map with all its layers, and
the dataset registers the layer that the exported dataset registered (see the
last example).

An existing dataset **output** is refused unless **--overwrite** is given.
With **--overwrite**, the dataset is made again from the archive and maps of
the same names are replaced.

## NOTES

The attribute table of a `pack` archive comes back as it was. A `GML` archive
adds the columns of the GML file: *v.in.ogr* reads the feature id as the field
`gml_id`, makes a new key column `cat` and renames the field `cat` of the
archive to `cat_`. The example with the archive formats shows the columns.

A map that the archive names `name@mapset`, which
*[t.vect.export](t.vect.export.md)* writes for maps of one name from several
mapsets, is imported as `name_mapset`; every character of the mapset other than
a letter, a digit or an underscore becomes an underscore, so `dup@my.set` is
imported as `dup_my_set`. If two maps of the archive would get one name this
way, for example `dup@other` and a map `dup_other`, the import stops before the
first map is imported; with **basename** the maps are numbered instead. An
archive that lists a map more than once, as older exports wrote it for maps of
one name from several mapsets, is refused before the first map is imported; a
new export of the dataset names the maps with their mapset.

A `pack` archive cannot be imported into a project without a coordinate
reference system, the project `XY`: the project has no "PROJ_INFO" file, and
*v.unpack* stops with a Python error, with and without **-o**; no dataset is
made. The import works if the target has a coordinate reference system, if the
dataset is exported as `GML` or `GPKG`, or with **project**, which makes a
project from the archive. The last block of the example with another
coordinate reference system shows the error and the GML way.

The dataset and the maps are made in the current mapset. A map of the same
name in another mapset is no clash, as the last example shows.

The tool checks the archive and the names before it imports the first map,
so a refusal does not leave part of the maps behind:

- `Space time stvds dataset ... is already in the database` for an existing
  dataset;
- `... exists. To overwrite, use the --overwrite flag` for an existing map of
  the current mapset;
- `Extraction directory ... not found` for a missing **directory**;
- `The archive file is of wrong space time dataset type` for an archive of
  raster maps;
- `Number of maps mismatch in init and list file.` if `number_of_maps` in
  "init.txt" differs from the number of maps in "list.txt".

Blank lines in "list.txt" and "init.txt" are skipped, so an archive edited
by hand may contain them. A line of "init.txt" without an equals sign stops
the import with an error; a value is everything after the first equals
sign.

## EXAMPLES

The examples run in a project called `temporal_examples` with the coordinate
reference system EPSG:3358; where a command names this project, use the name of
your own project.

<!-- example-project: crs=EPSG:3358 -->

<!-- markdownlint-disable MD046 -->

### Import an archive under new names

The dataset `gauges` has two point maps of wind speed for the days from 1 to 2
March 2026. Map `gauges_k` has the two points `(k, 1)` and `(k, 2)` with the
speeds `10 * k + 1` and `10 * k + 2`. The first block creates it.

The second block writes the archive `gauges.tar` with
*[t.vect.export](t.vect.export.md)* and imports it into the same project. The
maps of the archive carry the names of the maps that exist already, so
**basename** names the new maps `imported_1` and `imported_2`. The archive is
extracted to the existing directory `work`, which keeps the pack files.
**title** and **description** are set; *t.info* prints them. The map
`imported_2` has the points of `gauges_2`.

The third block imports the archive again under the same names. **--overwrite**
replaces the dataset and its maps.

=== "Command line"

    ```sh
    for k in 1 2; do
        v.in.ascii --quiet input=- output=gauges_$k separator=comma \
            columns="x double precision, y double precision, speed double precision" <<EOF
    $k,1,$((10 * k + 1))
    $k,2,$((10 * k + 2))
    EOF
    done
    t.create type=stvds output=gauges title="Wind speed" \
        description="Wind speed at two gauges"
    t.register -i type=vector input=gauges maps=gauges_1,gauges_2 \
        start=2026-03-01 increment="1 day"
    ```

    ```sh
    t.vect.export input=gauges output=gauges.tar format=pack compression=no
    mkdir work
    t.vect.import input=gauges.tar output=copy basename=imported \
        directory=work title="Copy of gauges" \
        description="Imported from the archive"
    t.vect.list input=copy columns=name,layer,start_time,end_time
    v.db.select map=imported_2
    t.info type=stvds input=copy | grep -A3 "Title:"
    ls work | grep pack
    ```

    ```text
    name|layer|start_time|end_time
    imported_1|1|2026-03-01 00:00:00|2026-03-02 00:00:00
    imported_2|1|2026-03-02 00:00:00|2026-03-03 00:00:00
    cat|x|y|speed
    1|2|1|21
    2|2|2|22
     | Title:
     | Copy of gauges
     | Description:
     | Imported from the archive
    gauges_1.pack
    gauges_2.pack
    ```

    ```sh
    t.vect.import --overwrite input=gauges.tar output=copy basename=imported \
        directory=work
    t.vect.list input=copy columns=name,start_time
    ```

    ```text
    name|start_time
    imported_1|2026-03-01 00:00:00
    imported_2|2026-03-02 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    from grass.tools import Tools

    tools = Tools()
    for k in (1, 2):
        tools.v_in_ascii(
            input=StringIO(f"{k},1,{10 * k + 1}\n{k},2,{10 * k + 2}\n"),
            output=f"gauges_{k}",
            separator="comma",
            columns="x double precision, y double precision, speed double precision",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Wind speed",
        description="Wind speed at two gauges",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    ```

    ```python
    from pathlib import Path

    tools.t_vect_export(
        input="gauges", output="gauges.tar", format="pack", compression="no"
    )
    Path("work").mkdir()
    tools.t_vect_import(
        input="gauges.tar",
        output="copy",
        basename="imported",
        directory="work",
        title="Copy of gauges",
        description="Imported from the archive",
    )
    print(tools.t_vect_list(input="copy", columns="name,layer,start_time,end_time").text)
    print(tools.v_db_select(map="imported_2").text)
    info = tools.t_info(type="stvds", input="copy").stdout.splitlines()
    first = next(index for index, line in enumerate(info) if "Title:" in line)
    print("\n".join(info[first : first + 4]))
    print("\n".join(sorted(path.name for path in Path("work").glob("*.pack"))))
    ```

    ```text
    name|layer|start_time|end_time
    imported_1|1|2026-03-01 00:00:00|2026-03-02 00:00:00
    imported_2|1|2026-03-02 00:00:00|2026-03-03 00:00:00
    cat|x|y|speed
    1|2|1|21
    2|2|2|22
     | Title:
     | Copy of gauges
     | Description:
     | Imported from the archive
    gauges_1.pack
    gauges_2.pack
    ```

    ```python
    tools.t_vect_import(
        input="gauges.tar",
        output="copy",
        basename="imported",
        directory="work",
        overwrite=True,
    )
    print(tools.t_vect_list(input="copy", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    imported_1|2026-03-01 00:00:00
    imported_2|2026-03-02 00:00:00
    ```

### Choose the format of the archive

*[t.vect.export](t.vect.export.md)* writes the maps as GML (the default),
GeoPackage (`GPKG`) or `pack` files. The archives here are compressed with
`gzip` and `bzip2`; the import finds the compression and the format itself.
The first block imports a GML archive, with the names `gml_1` and `gml_2`. The
directory `gml_files` keeps the GML files that *v.in.ogr* read. The table of
`gml_1` has the columns of the GML file besides `x`, `y` and `speed`: `gml_id`,
the feature id, and `cat_`, the field `cat` of the archive, which *v.in.ogr*
renamed because it made a new key column `cat`. The second block imports a
GeoPackage archive and prints the speeds of the points of `gpkg_2`, which are
those of `gauges_2`.

=== "Command line"

    <!-- example: requires=gdal:GML -->

    ```sh
    t.vect.export input=gauges output=gauges_gml.tar.gz format=GML \
        compression=gzip
    mkdir gml_files
    t.vect.import input=gauges_gml.tar.gz output=gml_copy basename=gml \
        directory=gml_files
    t.vect.list input=gml_copy columns=name,layer,start_time
    db.columns table=gml_1
    ls gml_files | grep xml
    ```

    ```text
    name|layer|start_time
    gml_1|None|2026-03-01 00:00:00
    gml_2|None|2026-03-02 00:00:00
    cat
    gml_id
    cat_
    x
    y
    speed
    gauges_1.xml
    gauges_2.xml
    ```

    <!-- example: requires=gdal:GPKG -->

    ```sh
    t.vect.export input=gauges output=gauges_gpkg.tar.bz2 format=GPKG \
        compression=bzip2
    mkdir gpkg_files
    t.vect.import input=gauges_gpkg.tar.bz2 output=gpkg_copy basename=gpkg \
        directory=gpkg_files
    t.vect.list input=gpkg_copy columns=name,layer,start_time
    v.db.select map=gpkg_2 columns=speed
    ```

    ```text
    name|layer|start_time
    gpkg_1|None|2026-03-01 00:00:00
    gpkg_2|None|2026-03-02 00:00:00
    speed
    21
    22
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GML -->

    ```python
    tools.t_vect_export(
        input="gauges",
        output="gauges_gml.tar.gz",
        format="GML",
        compression="gzip",
    )
    Path("gml_files").mkdir()
    tools.t_vect_import(
        input="gauges_gml.tar.gz",
        output="gml_copy",
        basename="gml",
        directory="gml_files",
    )
    print(tools.t_vect_list(input="gml_copy", columns="name,layer,start_time").text)
    print(tools.db_columns(table="gml_1").text)
    print("\n".join(sorted(path.name for path in Path("gml_files").glob("*.xml"))))
    ```

    ```text
    name|layer|start_time
    gml_1|None|2026-03-01 00:00:00
    gml_2|None|2026-03-02 00:00:00
    cat
    gml_id
    cat_
    x
    y
    speed
    gauges_1.xml
    gauges_2.xml
    ```

    <!-- example: requires=gdal:GPKG -->

    ```python
    tools.t_vect_export(
        input="gauges",
        output="gauges_gpkg.tar.bz2",
        format="GPKG",
        compression="bzip2",
    )
    Path("gpkg_files").mkdir()
    tools.t_vect_import(
        input="gauges_gpkg.tar.bz2",
        output="gpkg_copy",
        basename="gpkg",
        directory="gpkg_files",
    )
    print(tools.t_vect_list(input="gpkg_copy", columns="name,layer,start_time").text)
    print(tools.v_db_select(map="gpkg_2", columns="speed").text)
    ```

    ```text
    name|layer|start_time
    gpkg_1|None|2026-03-01 00:00:00
    gpkg_2|None|2026-03-02 00:00:00
    speed
    21
    22
    ```

### Import into a new project

With **project**, the tool makes a new project with the coordinate reference
system of the archive, imports into it and goes back to the project it was
called in. The maps keep their names, because the new project has none of
them. The new project takes the extent of the maps, for a GML archive as well
as for a `pack` archive: the default region of a new project is a single cell
from (0, 0) to (1, 1), and the points lie between (1, 1) and (2, 2), so the
region grows to the corners (0, 0) and (2, 2).

The first block imports the `pack` archive. It switches to the new project to
look at it and back to the project `temporal_examples` of these examples. The
last two commands print the projection and the ellipsoid of the new project and
of the project of the examples, which are the same. The second block does the
same for the GML archive of the previous example and prints the region of its
new project.

=== "Command line"

    ```sh
    t.vect.import input=gauges.tar output=gauges project=archive_copy \
        directory=work
    g.mapset project=archive_copy mapset=PERMANENT
    t.vect.list input=gauges columns=name,start_time
    g.region -dg | grep -E "^(n|s|e|w)="
    g.proj -g | grep -E "^(proj|ellps)="
    g.mapset project=temporal_examples mapset=PERMANENT
    g.proj -g | grep -E "^(proj|ellps)="
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    n=2
    s=0
    w=0
    e=2
    ellps=grs80
    proj=lcc
    ellps=grs80
    proj=lcc
    ```

    <!-- example: requires=gdal:GML -->

    ```sh
    t.vect.import input=gauges_gml.tar.gz output=gauges project=archive_gml \
        directory=gml_files
    g.mapset project=archive_gml mapset=PERMANENT
    g.region -dg | grep -E "^(n|s|e|w)="
    g.mapset project=temporal_examples mapset=PERMANENT
    ```

    ```text
    n=2
    s=0
    w=0
    e=2
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_import(
        input="gauges.tar", output="gauges", project="archive_copy", directory="work"
    )
    tools.g_mapset(project="archive_copy", mapset="PERMANENT")
    print(tools.t_vect_list(input="gauges", columns="name,start_time").text)
    region = tools.g_region(flags="dg").keyval
    print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))
    projection = tools.g_proj(flags="g").keyval
    print("\n".join(f"{key}={projection[key]}" for key in ("ellps", "proj")))
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    projection = tools.g_proj(flags="g").keyval
    print("\n".join(f"{key}={projection[key]}" for key in ("ellps", "proj")))
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    n=2
    s=0
    w=0
    e=2
    ellps=grs80
    proj=lcc
    ellps=grs80
    proj=lcc
    ```

    <!-- example: requires=gdal:GML -->

    ```python
    tools.t_vect_import(
        input="gauges_gml.tar.gz",
        output="gauges",
        project="archive_gml",
        directory="gml_files",
    )
    tools.g_mapset(project="archive_gml", mapset="PERMANENT")
    region = tools.g_region(flags="dg").keyval
    print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    ```

    ```text
    n=2
    s=0
    w=0
    e=2
    ```

### Create a project and extend its region

The flag **-c** makes the project and imports nothing: the region of the new
project is its default one, a single cell from (0, 0) to (1, 1). The second
import goes into that project with **-e**, so the default region and the current
region grow to the extent of the maps. The flag works for a `pack` archive as it
does for GML and GPKG.

=== "Command line"

    ```sh
    t.vect.import -c input=gauges.tar output=gauges project=empty_project \
        directory=work
    g.mapset project=empty_project mapset=PERMANENT
    g.region -dg | grep -E "^(n|s|e|w)="
    t.vect.import -e input=gauges.tar output=gauges directory=work
    g.region -dg | grep -E "^(n|s|e|w)="
    g.mapset project=temporal_examples mapset=PERMANENT
    ```

    ```text
    n=1
    s=0
    w=0
    e=1
    n=2
    s=0
    w=0
    e=2
    ```

=== "Python (grass.tools)"

    ```python
    def print_extent(flags):
        region = tools.g_region(flags=flags).keyval
        print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))


    tools.t_vect_import(
        input="gauges.tar",
        output="gauges",
        project="empty_project",
        directory="work",
        flags="c",
    )
    tools.g_mapset(project="empty_project", mapset="PERMANENT")
    print_extent("dg")
    tools.t_vect_import(input="gauges.tar", output="gauges", directory="work", flags="e")
    print_extent("dg")
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    ```

    ```text
    n=1
    s=0
    w=0
    e=1
    n=2
    s=0
    w=0
    e=2
    ```

### Import into a project with another coordinate reference system

The archive `gauges.tar` has the coordinate reference system EPSG:3358. The
project `utm` made here has EPSG:32632. The first block imports the archive
into it without **-o**, the second with **-o** and under other names. Neither
import is refused, and neither reprojects: the maps keep their coordinates, and
the points of `gauges_1` still lie at x = 1 and y = 1 and 2. Both warn that the
projections differ; **-o** only leaves out the warning that re-projection is
not supported.

The project `flat` is made with `grass -c XY` and has no coordinate reference
system. The `pack` archive
cannot be imported into it: the next block prints that the error mentions the
missing "PROJ_INFO" file. The GML archive of the second example can (the
block needs the GML driver).

=== "Command line"

    ```sh
    g.proj -c project=utm epsg=32632
    g.mapset project=utm mapset=PERMANENT
    t.vect.import input=gauges.tar output=gauges directory=work
    t.vect.list input=gauges columns=name,start_time
    v.info format=shell map=gauges_1 | grep -E "^(north|south|east|west)="
    t.vect.import -o input=gauges.tar output=again basename=again \
        directory=work
    t.vect.list input=again columns=name,start_time
    v.info format=shell map=again_1 | grep -E "^(north|south|east|west)="
    g.mapset project=temporal_examples mapset=PERMANENT
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    north=2
    south=1
    east=1
    west=1
    name|start_time
    again_1|2026-03-01 00:00:00
    again_2|2026-03-02 00:00:00
    north=2
    south=1
    east=1
    west=1
    ```

    ```sh
    grass -c XY "$(g.gisenv get=GISDBASE)/flat" --exec true
    g.mapset project=flat mapset=PERMANENT
    mkdir flat_files
    if ! t.vect.import input=gauges.tar output=gauges directory=flat_files \
        2> flat_error.txt; then
        grep -q PROJ_INFO flat_error.txt && echo "PROJ_INFO is missing"
    fi
    ```

    ```text
    PROJ_INFO is missing
    ```

    <!-- example: requires=gdal:GML -->

    ```sh
    mkdir flat_gml_files
    t.vect.import input=gauges_gml.tar.gz output=flat_gauges \
        directory=flat_gml_files
    t.vect.list input=flat_gauges columns=name,start_time
    g.mapset project=temporal_examples mapset=PERMANENT
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    def print_bounds(name):
        info = tools.v_info(map=name, format="shell").keyval
        keys = ("north", "south", "east", "west")
        print("\n".join(f"{key}={info[key]}" for key in keys))


    tools.g_proj(flags="c", project="utm", epsg=32632)
    tools.g_mapset(project="utm", mapset="PERMANENT")
    tools.t_vect_import(input="gauges.tar", output="gauges", directory="work")
    print(tools.t_vect_list(input="gauges", columns="name,start_time").text)
    print_bounds("gauges_1")
    tools.t_vect_import(
        input="gauges.tar",
        output="again",
        basename="again",
        directory="work",
        flags="o",
    )
    print(tools.t_vect_list(input="again", columns="name,start_time").text)
    print_bounds("again_1")
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    north=2
    south=1
    east=1
    west=1
    name|start_time
    again_1|2026-03-01 00:00:00
    again_2|2026-03-02 00:00:00
    north=2
    south=1
    east=1
    west=1
    ```

    ```python
    import subprocess

    from grass.tools import ToolError

    gisdbase = tools.g_gisenv(get="GISDBASE").stdout.strip()
    subprocess.run(["grass", "-c", "XY", f"{gisdbase}/flat", "--exec", "true"], check=True)
    tools.g_mapset(project="flat", mapset="PERMANENT")
    Path("flat_files").mkdir()
    try:
        tools.t_vect_import(input="gauges.tar", output="gauges", directory="flat_files")
    except ToolError as error:
        if "PROJ_INFO" in str(error):
            print("PROJ_INFO is missing")
    ```

    ```text
    PROJ_INFO is missing
    ```

    <!-- example: requires=gdal:GML -->

    ```python
    Path("flat_gml_files").mkdir()
    tools.t_vect_import(
        input="gauges_gml.tar.gz", output="flat_gauges", directory="flat_gml_files"
    )
    print(tools.t_vect_list(input="flat_gauges", columns="name,start_time").text)
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    ```

    ```text
    name|start_time
    gauges_1|2026-03-01 00:00:00
    gauges_2|2026-03-02 00:00:00
    ```

### Import a map with several layers

The map `layered` has the points of `gauges_1` in two layers with the same
categories 1 and 2. Layer 2 has its own table, `layered_2`, in which the speeds
are 100 higher. The dataset `layered` registers layer 2 of the map as
`layered:2`.

A `pack` archive holds the whole map, so the import into the new mapset
`layers` has both layers, and the dataset registers layer 2 as before. The
speeds of layer 2 are 111 and 112. The GML archive holds the registered layer
as the only layer of the map: the imported map `lgml_1` has layer 1, and its
table has the speeds of layer 2.

=== "Command line"

    ```sh
    v.category --quiet input=gauges_1 output=layered option=transfer \
        layer=1,2
    db.copy from_table=layered to_table=layered_2
    v.db.connect --quiet map=layered table=layered_2 layer=2 key=cat
    db.execute sql="UPDATE layered_2 SET speed = speed + 100"
    t.create type=stvds output=layered title="Layers" \
        description="A map with two layers"
    t.register type=vector input=layered maps=layered:2 \
        start=2026-03-01 end=2026-03-02
    t.vect.export input=layered output=layered.tar format=pack compression=no
    mkdir layer_files
    g.mapset -c mapset=layers
    t.vect.import input=layered.tar output=layered_copy directory=layer_files
    t.vect.list input=layered_copy columns=name,layer,mapset
    v.category input=layered@layers option=layers
    v.db.select map=layered@layers layer=2 columns=speed
    g.mapset mapset=PERMANENT
    ```

    ```text
    name|layer|mapset
    layered|2|layers
    1
    2
    speed
    111
    112
    ```

    <!-- example: requires=gdal:GML -->

    ```sh
    t.vect.export input=layered output=layered_gml.tar format=GML \
        compression=no
    mkdir layer_gml_files
    t.vect.import input=layered_gml.tar output=layered_gml basename=lgml \
        directory=layer_gml_files
    t.vect.list input=layered_gml columns=name,layer
    v.category input=lgml_1 option=layers
    v.db.select map=lgml_1 columns=speed
    ```

    ```text
    name|layer
    lgml_1|None
    1
    speed
    111
    112
    ```

=== "Python (grass.tools)"

    ```python
    tools.v_category(input="gauges_1", output="layered", option="transfer", layer="1,2")
    tools.db_copy(from_table="layered", to_table="layered_2")
    tools.v_db_connect(map="layered", table="layered_2", layer=2, key="cat")
    tools.db_execute(sql="UPDATE layered_2 SET speed = speed + 100")
    tools.t_create(
        type="stvds", output="layered", title="Layers", description="A map with two layers"
    )
    tools.t_register(
        type="vector",
        input="layered",
        maps="layered:2",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_vect_export(
        input="layered", output="layered.tar", format="pack", compression="no"
    )
    Path("layer_files").mkdir()
    tools.g_mapset(mapset="layers", flags="c")
    tools.t_vect_import(input="layered.tar", output="layered_copy", directory="layer_files")
    print(tools.t_vect_list(input="layered_copy", columns="name,layer,mapset").text)
    print(tools.v_category(input="layered@layers", option="layers").text)
    print(tools.v_db_select(map="layered@layers", layer=2, columns="speed").text)
    tools.g_mapset(mapset="PERMANENT")
    ```

    ```text
    name|layer|mapset
    layered|2|layers
    1
    2
    speed
    111
    112
    ```

    <!-- example: requires=gdal:GML -->

    ```python
    tools.t_vect_export(
        input="layered", output="layered_gml.tar", format="GML", compression="no"
    )
    Path("layer_gml_files").mkdir()
    tools.t_vect_import(
        input="layered_gml.tar",
        output="layered_gml",
        basename="lgml",
        directory="layer_gml_files",
    )
    print(tools.t_vect_list(input="layered_gml", columns="name,layer").text)
    print(tools.v_category(input="lgml_1", option="layers").text)
    print(tools.v_db_select(map="lgml_1", columns="speed").text)
    ```

    ```text
    name|layer
    lgml_1|None
    1
    speed
    111
    112
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.import](t.rast.import.md), [t.vect.export](t.vect.export.md),
[v.in.ogr](v.in.ogr.md), [v.pack](v.pack.md), [v.unpack](v.unpack.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
