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

The flag **-e** extends the region to the imported maps: it grows the current
region until it covers them (see the example "Extend the region to the
imported maps"). In the mapset `PERMANENT` it also extends the default region
of the project, so use it with care in a project that you share. The maps of a
`pack` archive extend the region as well as those of a `GML` or `GPKG`
archive.

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

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_import`, sets the computational region to
North Carolina with cells of 1 km, generates a dataset of three monthly
vector maps and imports the archive that *[t.vect.export](t.vect.export.md)*
wrote from it; the later examples work in this mapset and with this archive.
The example with several layers creates a second mapset with the same region.
The new projects of the examples are made in the GRASS database of the
session, next to the dataset, and the dataset itself stays as it is. Where a
command names the project `nc_spm_08_grass7`, use the name of the project you
opened.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_import -->

<!-- markdownlint-disable MD046 -->

### Import an archive under new names

The dataset `stations_monthly` has three vector maps for January to March 2020.
Each map is a copy of the 136 climate stations of the dataset, with the column
`precipitation`, which holds the normal of the month in millimetres, rounded to
a whole number. The maps are copies in the current mapset, so the dataset stays
as it is. Each map is an interval of one month. The first block creates the
dataset.

The second block writes the archive `stations.tar` with
*[t.vect.export](t.vect.export.md)* and imports it into the same project. The
maps of the archive carry the names of the maps that exist already, so
**basename** names the new maps `imported_1` to `imported_3`. The archive is
extracted to the existing directory `work`, which keeps the pack files.
**title** and **description** are set; *t.info* prints them. The map
`imported_2` has the stations of `stations_monthly_2020_02`; the commands print
the first three of them.

The third block imports the archive again under the same names. **--overwrite**
replaces the dataset and its maps.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_import
    g.region raster=elev_state_500m res=1000 -a
    for entry in 01:jan 02:feb 03:mar; do
        v.extract --quiet input=precip_30ynormals \
            output=stations_monthly_2020_${entry%:*}
        v.db.addcolumn --quiet map=stations_monthly_2020_${entry%:*} \
            columns="precipitation integer"
        v.db.update --quiet map=stations_monthly_2020_${entry%:*} \
            column=precipitation query_column="round(${entry#*:})"
    done
    t.create type=stvds output=stations_monthly title="Precipitation" \
        description="Monthly precipitation normal in mm at the climate stations"
    t.register -i type=vector input=stations_monthly \
        maps=$(g.list type=vector pattern="stations_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    ```

    ```sh
    t.vect.export input=stations_monthly output=stations.tar format=pack \
        compression=no
    mkdir work
    t.vect.import input=stations.tar output=copy basename=imported \
        directory=work title="Copy of stations" \
        description="Imported from the archive"
    t.vect.list input=copy columns=name,layer,start_time,end_time
    v.db.select map=imported_2 columns=cat,station,precipitation \
        where="cat <= 3"
    t.info type=stvds input=copy | grep -A3 "Title:"
    ls work | grep pack
    ```

    ```text
    name|layer|start_time|end_time
    imported_1|1|2020-01-01 00:00:00|2020-02-01 00:00:00
    imported_2|1|2020-02-01 00:00:00|2020-03-01 00:00:00
    imported_3|1|2020-03-01 00:00:00|2020-04-01 00:00:00
    cat|station|precipitation
    1|310090|92
    2|310184|155
    3|310241|88
     | Title:
     | Copy of stations
     | Description:
     | Imported from the archive
    stations_monthly_2020_01.pack
    stations_monthly_2020_02.pack
    stations_monthly_2020_03.pack
    ```

    ```sh
    t.vect.import --overwrite input=stations.tar output=copy basename=imported \
        directory=work
    t.vect.list input=copy columns=name,start_time
    ```

    ```text
    name|start_time
    imported_1|2020-01-01 00:00:00
    imported_2|2020-02-01 00:00:00
    imported_3|2020-03-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_vect_import")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for month, column in enumerate(("jan", "feb", "mar"), start=1):
        name = f"stations_monthly_2020_{month:02d}"
        tools.v_extract(input="precip_30ynormals", output=name)
        tools.v_db_addcolumn(map=name, columns="precipitation integer")
        tools.v_db_update(map=name, column="precipitation", query_column=f"round({column})")
    tools.t_create(
        type="stvds",
        output="stations_monthly",
        title="Precipitation",
        description="Monthly precipitation normal in mm at the climate stations",
    )
    tools.t_register(
        type="vector",
        input="stations_monthly",
        maps=",".join(f"stations_monthly_2020_{month:02d}" for month in (1, 2, 3)),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

    ```python
    tools.t_vect_export(
        input="stations_monthly", output="stations.tar", format="pack", compression="no"
    )
    Path("work").mkdir()
    tools.t_vect_import(
        input="stations.tar",
        output="copy",
        basename="imported",
        directory="work",
        title="Copy of stations",
        description="Imported from the archive",
    )
    print(tools.t_vect_list(input="copy", columns="name,layer,start_time,end_time").text)
    print(
        tools.v_db_select(
            map="imported_2", columns="cat,station,precipitation", where="cat <= 3"
        ).text
    )
    info = tools.t_info(type="stvds", input="copy").stdout.splitlines()
    first = next(index for index, line in enumerate(info) if "Title:" in line)
    print("\n".join(info[first : first + 4]))
    print("\n".join(sorted(path.name for path in Path("work").glob("*.pack"))))
    ```

    ```text
    name|layer|start_time|end_time
    imported_1|1|2020-01-01 00:00:00|2020-02-01 00:00:00
    imported_2|1|2020-02-01 00:00:00|2020-03-01 00:00:00
    imported_3|1|2020-03-01 00:00:00|2020-04-01 00:00:00
    cat|station|precipitation
    1|310090|92
    2|310184|155
    3|310241|88
     | Title:
     | Copy of stations
     | Description:
     | Imported from the archive
    stations_monthly_2020_01.pack
    stations_monthly_2020_02.pack
    stations_monthly_2020_03.pack
    ```

    ```python
    tools.t_vect_import(
        input="stations.tar",
        output="copy",
        basename="imported",
        directory="work",
        overwrite=True,
    )
    print(tools.t_vect_list(input="copy", columns="name,start_time").text)
    ```

    ```text
    name|start_time
    imported_1|2020-01-01 00:00:00
    imported_2|2020-02-01 00:00:00
    imported_3|2020-03-01 00:00:00
    ```

### Choose the format of the archive

*[t.vect.export](t.vect.export.md)* writes the maps as GML (the default),
GeoPackage (`GPKG`) or `pack` files. The archives here are compressed with
`gzip` and `bzip2`; the import finds the compression and the format itself.
The first block imports a GML archive, with the names `gml_1` to `gml_3`. The
directory `gml_files` keeps the GML files that *v.in.ogr* read. The table of
`gml_1` has the columns of the GML file besides those of the stations: the
commands print the three that the import adds or renames, `cat`, the new key
column, `gml_id`, the feature id, and `cat_`, the field `cat` of the archive,
which *v.in.ogr* renamed because it made a new key column `cat`. The second
block imports a GeoPackage archive and prints the precipitation of the first
three stations of `gpkg_2`, which are those of `stations_monthly_2020_02`.

=== "Command line"

    <!-- example: requires=gdal:GML -->

    ```sh
    t.vect.export input=stations_monthly output=stations_gml.tar.gz format=GML \
        compression=gzip
    mkdir gml_files
    t.vect.import input=stations_gml.tar.gz output=gml_copy basename=gml \
        directory=gml_files
    t.vect.list input=gml_copy columns=name,layer,start_time
    db.columns table=gml_1 | grep -E "^(cat|gml_id|cat_)$"
    ls gml_files | grep xml
    ```

    ```text
    name|layer|start_time
    gml_1|None|2020-01-01 00:00:00
    gml_2|None|2020-02-01 00:00:00
    gml_3|None|2020-03-01 00:00:00
    cat
    gml_id
    cat_
    stations_monthly_2020_01.xml
    stations_monthly_2020_02.xml
    stations_monthly_2020_03.xml
    ```

    <!-- example: requires=gdal:GPKG -->

    ```sh
    t.vect.export input=stations_monthly output=stations_gpkg.tar.bz2 \
        format=GPKG compression=bzip2
    mkdir gpkg_files
    t.vect.import input=stations_gpkg.tar.bz2 output=gpkg_copy basename=gpkg \
        directory=gpkg_files
    t.vect.list input=gpkg_copy columns=name,layer,start_time
    v.db.select map=gpkg_2 columns=station,precipitation where="cat_ <= 3"
    ```

    ```text
    name|layer|start_time
    gpkg_1|None|2020-01-01 00:00:00
    gpkg_2|None|2020-02-01 00:00:00
    gpkg_3|None|2020-03-01 00:00:00
    station|precipitation
    310090|92
    310184|155
    310241|88
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GML -->

    ```python
    tools.t_vect_export(
        input="stations_monthly",
        output="stations_gml.tar.gz",
        format="GML",
        compression="gzip",
    )
    Path("gml_files").mkdir()
    tools.t_vect_import(
        input="stations_gml.tar.gz",
        output="gml_copy",
        basename="gml",
        directory="gml_files",
    )
    print(tools.t_vect_list(input="gml_copy", columns="name,layer,start_time").text)
    columns = tools.db_columns(table="gml_1").text.splitlines()
    print("\n".join(name for name in columns if name in ("cat", "gml_id", "cat_")))
    print("\n".join(sorted(path.name for path in Path("gml_files").glob("*.xml"))))
    ```

    ```text
    name|layer|start_time
    gml_1|None|2020-01-01 00:00:00
    gml_2|None|2020-02-01 00:00:00
    gml_3|None|2020-03-01 00:00:00
    cat
    gml_id
    cat_
    stations_monthly_2020_01.xml
    stations_monthly_2020_02.xml
    stations_monthly_2020_03.xml
    ```

    <!-- example: requires=gdal:GPKG -->

    ```python
    tools.t_vect_export(
        input="stations_monthly",
        output="stations_gpkg.tar.bz2",
        format="GPKG",
        compression="bzip2",
    )
    Path("gpkg_files").mkdir()
    tools.t_vect_import(
        input="stations_gpkg.tar.bz2",
        output="gpkg_copy",
        basename="gpkg",
        directory="gpkg_files",
    )
    print(tools.t_vect_list(input="gpkg_copy", columns="name,layer,start_time").text)
    print(
        tools.v_db_select(
            map="gpkg_2", columns="station,precipitation", where="cat_ <= 3"
        ).text
    )
    ```

    ```text
    name|layer|start_time
    gpkg_1|None|2020-01-01 00:00:00
    gpkg_2|None|2020-02-01 00:00:00
    gpkg_3|None|2020-03-01 00:00:00
    station|precipitation
    310090|92
    310184|155
    310241|88
    ```

### Import into a new project

With **project**, the tool makes a new project with the coordinate reference
system of the archive, imports into it and goes back to the project it was
called in. The new project is made in the GRASS database of the session, so it
lies next to the project `nc_spm_08_grass7`. The maps keep their names, because
the new project has none of them. The first block imports the `pack` archive.
It switches to the new project to look at it and back to the mapset of these
examples. The commands print the dataset and the bounds of the first map,
which are those of the stations in the project of the examples. The second
block does the same for the GML archive of the previous example.

=== "Command line"

    ```sh
    t.vect.import input=stations.tar output=stations project=archive_copy \
        directory=work
    g.mapset project=archive_copy mapset=PERMANENT
    t.vect.list input=stations columns=name,start_time
    v.info format=shell map=stations_monthly_2020_01 | grep -E "^(north|south|east|west)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    g.mapset project=nc_spm_08_grass7 mapset=t_vect_import
    v.info format=shell map=stations_monthly_2020_01 | grep -E "^(north|south|east|west)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    ```

    ```text
    name|start_time
    stations_monthly_2020_01|2020-01-01 00:00:00
    stations_monthly_2020_02|2020-02-01 00:00:00
    stations_monthly_2020_03|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    north=306222
    south=27607
    east=917005
    west=151769
    ```

    <!-- example: requires=gdal:GML -->

    ```sh
    t.vect.import input=stations_gml.tar.gz output=stations project=archive_gml \
        directory=gml_files
    g.mapset project=archive_gml mapset=PERMANENT
    t.vect.list input=stations columns=name,layer,start_time
    g.mapset project=nc_spm_08_grass7 mapset=t_vect_import
    ```

    ```text
    name|layer|start_time
    stations_monthly_2020_01|None|2020-01-01 00:00:00
    stations_monthly_2020_02|None|2020-02-01 00:00:00
    stations_monthly_2020_03|None|2020-03-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    def print_bounds(name):
        info = tools.v_info(map=name, format="shell").keyval
        keys = ("north", "south", "east", "west")
        print("\n".join(f"{key}={info[key]:.0f}" for key in keys))


    tools.t_vect_import(
        input="stations.tar", output="stations", project="archive_copy", directory="work"
    )
    tools.g_mapset(project="archive_copy", mapset="PERMANENT")
    print(tools.t_vect_list(input="stations", columns="name,start_time").text)
    print_bounds("stations_monthly_2020_01")
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_vect_import")
    print_bounds("stations_monthly_2020_01")
    ```

    ```text
    name|start_time
    stations_monthly_2020_01|2020-01-01 00:00:00
    stations_monthly_2020_02|2020-02-01 00:00:00
    stations_monthly_2020_03|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    north=306222
    south=27607
    east=917005
    west=151769
    ```

    <!-- example: requires=gdal:GML -->

    ```python
    tools.t_vect_import(
        input="stations_gml.tar.gz",
        output="stations",
        project="archive_gml",
        directory="gml_files",
    )
    tools.g_mapset(project="archive_gml", mapset="PERMANENT")
    print(tools.t_vect_list(input="stations", columns="name,layer,start_time").text)
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_vect_import")
    ```

    ```text
    name|layer|start_time
    stations_monthly_2020_01|None|2020-01-01 00:00:00
    stations_monthly_2020_02|None|2020-02-01 00:00:00
    stations_monthly_2020_03|None|2020-03-01 00:00:00
    ```

### Create a project without importing

The flag **-c** makes the project and imports nothing. The commands switch to
the new project and show that it has no vector map and no dataset, and that
its default region is one cell.

=== "Command line"

    ```sh
    t.vect.import -c input=stations.tar output=stations project=empty_project \
        directory=work
    g.mapset project=empty_project mapset=PERMANENT
    g.list type=vector | wc -l
    t.list type=stvds | wc -l
    g.region -dg | grep -E "^(n|s|e|w)="
    g.mapset project=nc_spm_08_grass7 mapset=t_vect_import
    ```

    ```text
    0
    0
    n=1
    s=0
    w=0
    e=1
    ```

=== "Python (grass.tools)"

    ```python
    def print_extent(flags):
        region = tools.g_region(flags=flags).keyval
        print("\n".join(f"{key}={region[key]:.0f}" for key in ("n", "s", "w", "e")))


    tools.t_vect_import(
        input="stations.tar",
        output="stations",
        project="empty_project",
        directory="work",
        flags="c",
    )
    tools.g_mapset(project="empty_project", mapset="PERMANENT")
    for result in (tools.g_list(type="vector"), tools.t_list(type="stvds")):
        print(len(result.text.splitlines()) if result else 0)
    print_extent("dg")
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_vect_import")
    ```

    ```text
    0
    0
    n=1
    s=0
    w=0
    e=1
    ```

### Extend the region to the imported maps

The flag **-e** grows the current region until it covers the imported maps. The
first command moves the region to a small window; the import then grows it to
the extent of the stations, in cells of 1 km, from the north and west edges
of the stations. The maps of a `pack` archive extend the region as well as
those of a GML or GeoPackage archive.

=== "Command line"

    ```sh
    g.region n=250000 s=240000 w=500000 e=510000 res=1000
    g.region -g | grep -E "^(n|s|e|w)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    t.vect.import -e input=stations.tar output=extended basename=extended \
        directory=work
    g.region -g | grep -E "^(n|s|e|w)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    g.region raster=elev_state_500m res=1000 -a
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=306222
    s=27222
    w=151769
    e=917769
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=250000, s=240000, w=500000, e=510000, res=1000)
    print_extent("g")
    tools.t_vect_import(
        input="stations.tar",
        output="extended",
        basename="extended",
        directory="work",
        flags="e",
    )
    print_extent("g")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=306222
    s=27222
    w=151769
    e=917769
    ```

### Import into a project with another coordinate reference system

The archive `stations.tar` has the coordinate reference system of the dataset,
EPSG:3358. The project `utm` made here has EPSG:32632. The first block imports
the archive into it without **-o**, the second with **-o** and under other
names. Neither import is refused, and neither reprojects: the maps keep their
coordinates, and the bounds of `stations_monthly_2020_01` are those printed in
the example with the new project. Both warn that the projections differ; **-o**
only leaves out the warning that re-projection is not supported.

The project `flat` is made with `grass -c XY` and has no coordinate reference
system. The `pack` archive
cannot be imported into it: the next block prints that the error mentions the
missing "PROJ_INFO" file. The GML archive of the second example can (the
block needs the GML driver).

=== "Command line"

    ```sh
    g.proj -c project=utm epsg=32632
    g.mapset project=utm mapset=PERMANENT
    t.vect.import input=stations.tar output=stations directory=work
    t.vect.list input=stations columns=name,start_time
    v.info format=shell map=stations_monthly_2020_01 | grep -E "^(north|south|east|west)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    t.vect.import -o input=stations.tar output=again basename=again \
        directory=work
    t.vect.list input=again columns=name,start_time
    v.info format=shell map=again_1 | grep -E "^(north|south|east|west)=" | awk -F= '{printf "%s=%.0f\n", $1, $2}'
    g.mapset project=nc_spm_08_grass7 mapset=t_vect_import
    ```

    ```text
    name|start_time
    stations_monthly_2020_01|2020-01-01 00:00:00
    stations_monthly_2020_02|2020-02-01 00:00:00
    stations_monthly_2020_03|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    name|start_time
    again_1|2020-01-01 00:00:00
    again_2|2020-02-01 00:00:00
    again_3|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    ```

    ```sh
    grass -c XY "$(g.gisenv get=GISDBASE)/flat" --exec true
    g.mapset project=flat mapset=PERMANENT
    mkdir flat_files
    if ! t.vect.import input=stations.tar output=stations directory=flat_files \
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
    t.vect.import input=stations_gml.tar.gz output=flat_stations \
        directory=flat_gml_files
    t.vect.list input=flat_stations columns=name,layer,start_time
    g.mapset project=nc_spm_08_grass7 mapset=t_vect_import
    ```

    ```text
    name|layer|start_time
    stations_monthly_2020_01|None|2020-01-01 00:00:00
    stations_monthly_2020_02|None|2020-02-01 00:00:00
    stations_monthly_2020_03|None|2020-03-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_proj(flags="c", project="utm", epsg=32632)
    tools.g_mapset(project="utm", mapset="PERMANENT")
    tools.t_vect_import(input="stations.tar", output="stations", directory="work")
    print(tools.t_vect_list(input="stations", columns="name,start_time").text)
    print_bounds("stations_monthly_2020_01")
    tools.t_vect_import(
        input="stations.tar",
        output="again",
        basename="again",
        directory="work",
        flags="o",
    )
    print(tools.t_vect_list(input="again", columns="name,start_time").text)
    print_bounds("again_1")
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_vect_import")
    ```

    ```text
    name|start_time
    stations_monthly_2020_01|2020-01-01 00:00:00
    stations_monthly_2020_02|2020-02-01 00:00:00
    stations_monthly_2020_03|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    name|start_time
    again_1|2020-01-01 00:00:00
    again_2|2020-02-01 00:00:00
    again_3|2020-03-01 00:00:00
    north=306222
    south=27607
    east=917005
    west=151769
    ```

    ```python
    import subprocess

    from grass.tools import ToolError

    gisdbase = tools.g_gisenv(get="GISDBASE").stdout.strip()
    subprocess.run(["grass", "-c", "XY", f"{gisdbase}/flat", "--exec", "true"], check=True)
    tools.g_mapset(project="flat", mapset="PERMANENT")
    Path("flat_files").mkdir()
    try:
        tools.t_vect_import(input="stations.tar", output="stations", directory="flat_files")
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
        input="stations_gml.tar.gz", output="flat_stations", directory="flat_gml_files"
    )
    print(tools.t_vect_list(input="flat_stations", columns="name,layer,start_time").text)
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_vect_import")
    ```

    ```text
    name|layer|start_time
    stations_monthly_2020_01|None|2020-01-01 00:00:00
    stations_monthly_2020_02|None|2020-02-01 00:00:00
    stations_monthly_2020_03|None|2020-03-01 00:00:00
    ```

### Import a map with several layers

The map `layered` has the stations of `stations_monthly_2020_01` in two layers
with the same categories. Layer 2 has its own table, `layered_2`, in which the
precipitation is 100 mm higher. The dataset `layered` registers layer 2 of the
map as `layered:2`.

A `pack` archive holds the whole map, so the import into the new mapset
`t_vect_import_2` has both layers, and the dataset registers layer 2 as before.
The values of layer 2 of the first three stations are 211, 282 and 200 mm.
The GML archive holds the registered layer as the only layer of the map: the
imported map `lgml_1` has layer 1, and its table has the values of layer 2.

=== "Command line"

    ```sh
    v.category --quiet input=stations_monthly_2020_01 output=layered \
        option=transfer layer=1,2
    db.copy from_table=layered to_table=layered_2
    v.db.connect --quiet map=layered table=layered_2 layer=2 key=cat
    db.execute sql="UPDATE layered_2 SET precipitation = precipitation + 100"
    t.create type=stvds output=layered title="Layers" \
        description="A map with two layers"
    t.register type=vector input=layered maps=layered:2 \
        start=2020-01-01 end=2020-02-01
    t.vect.export input=layered output=layered.tar format=pack compression=no
    mkdir layer_files
    g.mapset -c mapset=t_vect_import_2
    g.region raster=elev_state_500m res=1000 -a
    t.vect.import input=layered.tar output=layered_copy directory=layer_files
    t.vect.list input=layered_copy columns=name,layer,mapset
    v.category input=layered@t_vect_import_2 option=layers
    v.db.select map=layered@t_vect_import_2 layer=2 \
        columns=cat,station,precipitation where="cat <= 3"
    g.mapset mapset=t_vect_import
    ```

    ```text
    name|layer|mapset
    layered|2|t_vect_import_2
    1
    2
    cat|station|precipitation
    1|310090|211
    2|310184|282
    3|310241|200
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
    v.db.select map=lgml_1 columns=station,precipitation where="cat_ <= 3"
    ```

    ```text
    name|layer
    lgml_1|None
    1
    station|precipitation
    310090|211
    310184|282
    310241|200
    ```

=== "Python (grass.tools)"

    ```python
    tools.v_category(
        input="stations_monthly_2020_01", output="layered", option="transfer", layer="1,2"
    )
    tools.db_copy(from_table="layered", to_table="layered_2")
    tools.v_db_connect(map="layered", table="layered_2", layer=2, key="cat")
    tools.db_execute(sql="UPDATE layered_2 SET precipitation = precipitation + 100")
    tools.t_create(
        type="stvds", output="layered", title="Layers", description="A map with two layers"
    )
    tools.t_register(
        type="vector",
        input="layered",
        maps="layered:2",
        start="2020-01-01",
        end="2020-02-01",
    )
    tools.t_vect_export(
        input="layered", output="layered.tar", format="pack", compression="no"
    )
    Path("layer_files").mkdir()
    tools.g_mapset(mapset="t_vect_import_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_vect_import(input="layered.tar", output="layered_copy", directory="layer_files")
    print(tools.t_vect_list(input="layered_copy", columns="name,layer,mapset").text)
    print(tools.v_category(input="layered@t_vect_import_2", option="layers").text)
    print(
        tools.v_db_select(
            map="layered@t_vect_import_2",
            layer=2,
            columns="cat,station,precipitation",
            where="cat <= 3",
        ).text
    )
    tools.g_mapset(mapset="t_vect_import")
    ```

    ```text
    name|layer|mapset
    layered|2|t_vect_import_2
    1
    2
    cat|station|precipitation
    1|310090|211
    2|310184|282
    3|310241|200
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
    print(
        tools.v_db_select(
            map="lgml_1", columns="station,precipitation", where="cat_ <= 3"
        ).text
    )
    ```

    ```text
    name|layer
    lgml_1|None
    1
    station|precipitation
    310090|211
    310184|282
    310241|200
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.import](t.rast.import.md), [t.vect.export](t.vect.export.md),
[v.in.ogr](v.in.ogr.md), [v.pack](v.pack.md), [v.unpack](v.unpack.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
