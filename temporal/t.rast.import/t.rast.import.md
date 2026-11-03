## DESCRIPTION

*t.rast.import* imports an archive that *[t.rast.export](t.rast.export.md)*
wrote: it unpacks the archive, imports the raster maps and registers them in a
new space time raster dataset with the times of the archive. The archive moves
a dataset from another project or computer into the current project. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool for space time vector datasets is
*[t.vect.import](t.vect.import.md)*; *t.rast.import* refuses the archive of a
vector dataset.

The option **input** names the archive, and **output** the new space time
raster dataset, which is made in the current mapset. The compression of the
archive (`bzip2`, `gzip` or none) and the format of the maps in it (`GTiff`,
`AAIGrid` or `pack`) are found out from the archive. The maps of a `GTiff` or
`AAIGrid` archive are imported with *[r.in.gdal](r.in.gdal.md)*, those of a
`pack` archive with *[r.unpack](r.unpack.md)*. The temporal type, the
unit of relative time, the semantic type of the dataset, the times of the maps
and their semantic labels come from the archive, too. The options **title** and
**description** set the title and the description of the new dataset.

### Names of the maps

Without **basename**, each map keeps the name it has in the archive. The
option **basename** names the maps `basename_1`, `basename_2` and so on, with
a numerical suffix in the order of the maps in the archive. The suffix has as
many digits as the number of maps, padded with zeros: a dataset of ten maps
gets `basename_01` to `basename_10` (see the first example). This is the way
to import a dataset into the project it was exported from, where the names of
the archive are taken. A map of the same name in the current mapset is
refused (see the notes).

### Projection and new projects

The option **project** makes a new project with the coordinate reference system
of the archive in the GRASS database of the session and imports into it. The
project must not exist yet. When the import is over, the session is in the
project and mapset it was in before. The flag **-c** makes the project and
imports nothing; the archive is needed even then, because the new project takes
its coordinate reference system from it. An archive made in a project without a
coordinate reference system (the project `XY`) makes a project without one.

Without **project**, the maps are imported into the current project. The
import compares the coordinate reference system of the archive with that of the
project and refuses a difference. The flag **-o** assumes that the archive has
the coordinate reference system of the current project and skips this check.
In a project without a coordinate reference system, **-o** is needed for
GeoTIFF archives as well, because a GeoTIFF file made there holds none. An
archive of AAIGrid files holds no coordinate reference system either and
needs no **-o**, as the example with the ASCII grid shows, and neither does
the `pack` format. An import with **project** needs no **-o**.

The flag **-e** extends the extent of the project to the maps of a `GTiff` or
`AAIGrid` archive: it makes the default region and the current region of the
project cover the imported maps. With **project**, the flag is always on for
these formats. Without **project** it changes the default region of the
current project, so use it with care in a project that you share. The maps of a
`pack` archive do not change the region, with or without **-e** (see the
notes); a new project then keeps its default region.

### Files and region

The option **directory** names the directory that the archive is extracted to.
It must exist, and the extracted files stay in it. By default, the tool uses a
temporary directory. The flag **-l** links the raster maps to the GeoTIFF or
ASCII grid files with *[r.external](r.external.md)* instead of
importing the cells with *[r.in.gdal](r.in.gdal.md)*. The maps then read their
cells from the extracted files, so with **-l** choose a **directory** that you
keep. The option **memory** is the cache size in MB for raster rows (default
300) that *r.in.gdal* uses; *r.external* has none, so **-l** ignores it.

The flag **-r** sets the current computational region to the region of the
last map that was imported. Without it, the region stays as it is.

An existing dataset **output** is refused unless **--overwrite** is given.
With **--overwrite**, the dataset is made again from the archive and maps of
the same names are replaced.

## NOTES

The maps of a `pack` archive are unpacked with *[r.unpack](r.unpack.md)*,
which does not extend the region: **-e** has no effect, the region stays as it
is, and with **project** the new project keeps its default region, one cell
from (0, 0) to (1, 1). Use
**-r** to set the region from the maps of a `pack` archive, or
*[g.region](g.region.md)* afterwards. The example with the semantic labels
shows the missing extension.

A map that the archive names `name@mapset`, which
*[t.rast.export](t.rast.export.md)* writes for maps of one name from several
mapsets, is imported as `name_mapset`; every character of the mapset other
than a letter, a digit or an underscore becomes an underscore, so
`dup@my.set` is imported as `dup_my_set`. If two maps of the archive would get
one name this way, for example `dup@other` and a map `dup_other`, the import
stops before the first map is imported; with **basename** the maps are
numbered instead.
An archive that lists a map more than once, as older exports wrote it for
maps of one name from several mapsets, is refused before the first map is
imported; a new export of the dataset names the maps with their mapset.

The name of the new dataset may not contain a dot. The tool checks this before
it makes anything, so a refused name leaves no new project behind.

The dataset and the maps are made in the current mapset. A map of the same
name in another mapset is no clash, as the example with the semantic labels
shows. In a dataset with relative time, the unit of the archive is kept.

The tool checks the archive and the names before it imports the first map,
so a refusal does not leave part of the maps behind:

- `Space time strds dataset ... is already in the database. Use the overwrite
  flag.` for an existing dataset;
- `... exists. To overwrite, use the --overwrite flag` for an existing map of
  the current mapset;
- `Space time raster dataset archive ... not found` and `Extraction directory
  ... not found` for a missing archive or **directory**;
- `The archive file is of wrong space time dataset type` for an archive of
  vector maps;
- `Number of maps mismatch in init and list file.` if `number_of_maps` in
  "init.txt" differs from the number of maps in "list.txt";
- `Unable to create location ...` for a **project** that exists.

An archive whose coordinate reference system differs from that of the project
is refused with `Projection information does not match. Aborting.`. A GeoTIFF
archive in a project without a coordinate reference system is refused with
`Unable to import/link raster map ...`. **-o** cures both, if the coordinate
reference systems are the same.

Blank lines in "list.txt" and "init.txt" are skipped, so an archive edited
by hand may contain them. A line of "init.txt" without an equals sign stops
the import with an error; a value is everything after the first equals
sign.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_import`, sets the computational region to
North Carolina with cells of 1 km, generates a dataset of twelve monthly
precipitation maps and imports the archive that
*[t.rast.export](t.rast.export.md)* wrote from it; the later examples work in
this mapset and with this archive. The example with the semantic labels
creates a second mapset with the same region. The new projects of two
examples are made in the GRASS database of the session, next to the dataset,
and the dataset itself stays as it is. Where a command names the project
`nc_spm_08_grass7`, use the name of the project you opened.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_import -->

<!-- markdownlint-disable MD046 -->

### Import an archive under new names

The dataset `precipitation_monthly` holds twelve maps of the monthly
precipitation sum in 2020, in millimetres. They are generated, not measured:
the monthly normals of the 136 climate stations of the dataset are
interpolated with *[v.surf.idw](v.surf.idw.md)* and multiplied by an assumed
factor for a wet year, which is different for every month. Each map is an
interval of one month. The first block creates the dataset.

The second block writes the archive `precipitation.tar.bz2` with
*[t.rast.export](t.rast.export.md)* and imports it into the same project. The
maps of the archive carry the names of the maps that exist already, so
**basename** names the new maps `imported_01` to `imported_12`: the suffix has
two digits because there are twelve maps, and a dataset of fewer than ten maps
gets a single digit. The archive holds GeoTIFF files with the coordinate
reference system of the project, so the import needs no **-o**. **title** and
**description** are set, and **memory** limits the cache of *r.in.gdal* to
100 MB. The commands print the new dataset with the minimum and the maximum of
each map, the range of both datasets, which is the same, and the title and the
description of the new dataset from *t.info*.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_import
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
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=precipitation_monthly output=precipitation.tar.bz2
    t.rast.import input=precipitation.tar.bz2 output=precipitation_copy \
        basename=imported title="Copy of precipitation" \
        description="Imported from the archive" memory=100
    t.rast.list input=precipitation_copy columns=name,start_time,end_time,min,max
    for name in precipitation_monthly precipitation_copy; do
        t.info -g input=$name | grep -E "^(min_min|max_max)="
    done
    t.info input=precipitation_copy | grep -A3 "Title:"
    ```

    ```text
    name|start_time|end_time|min|max
    imported_01|2020-01-01 00:00:00|2020-02-01 00:00:00|94.0|249.0
    imported_02|2020-02-01 00:00:00|2020-03-01 00:00:00|133.0|309.0
    imported_03|2020-03-01 00:00:00|2020-04-01 00:00:00|88.0|212.0
    imported_04|2020-04-01 00:00:00|2020-05-01 00:00:00|92.0|231.0
    imported_05|2020-05-01 00:00:00|2020-06-01 00:00:00|133.0|347.0
    imported_06|2020-06-01 00:00:00|2020-07-01 00:00:00|71.0|163.0
    imported_07|2020-07-01 00:00:00|2020-08-01 00:00:00|83.0|223.0
    imported_08|2020-08-01 00:00:00|2020-09-01 00:00:00|119.0|295.0
    imported_09|2020-09-01 00:00:00|2020-10-01 00:00:00|60.0|181.0
    imported_10|2020-10-01 00:00:00|2020-11-01 00:00:00|55.0|160.0
    imported_11|2020-11-01 00:00:00|2020-12-01 00:00:00|104.0|350.0
    imported_12|2020-12-01 00:00:00|2021-01-01 00:00:00|59.0|177.0
    min_min=55.0
    max_max=350.0
    min_min=55.0
    max_max=350.0
     | Title:
     | Copy of precipitation
     | Description:
     | Imported from the archive
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_import")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
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
        maps=",".join(f"precipitation_monthly_2020_{month:02d}" for month in range(1, 13)),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="precipitation_monthly", output="precipitation.tar.bz2")
    tools.t_rast_import(
        input="precipitation.tar.bz2",
        output="precipitation_copy",
        basename="imported",
        title="Copy of precipitation",
        description="Imported from the archive",
        memory=100,
    )
    columns = "name,start_time,end_time,min,max"
    print(tools.t_rast_list(input="precipitation_copy", columns=columns).text)
    for name in ("precipitation_monthly", "precipitation_copy"):
        info = tools.t_info(input=name, flags="g").keyval
        print("\n".join(f"{key}={info[key]}" for key in ("min_min", "max_max")))
    info = tools.t_info(input="precipitation_copy").stdout.splitlines()
    first = next(index for index, line in enumerate(info) if "Title:" in line)
    print("\n".join(info[first : first + 4]))
    ```

    ```text
    name|start_time|end_time|min|max
    imported_01|2020-01-01 00:00:00|2020-02-01 00:00:00|94.0|249.0
    imported_02|2020-02-01 00:00:00|2020-03-01 00:00:00|133.0|309.0
    imported_03|2020-03-01 00:00:00|2020-04-01 00:00:00|88.0|212.0
    imported_04|2020-04-01 00:00:00|2020-05-01 00:00:00|92.0|231.0
    imported_05|2020-05-01 00:00:00|2020-06-01 00:00:00|133.0|347.0
    imported_06|2020-06-01 00:00:00|2020-07-01 00:00:00|71.0|163.0
    imported_07|2020-07-01 00:00:00|2020-08-01 00:00:00|83.0|223.0
    imported_08|2020-08-01 00:00:00|2020-09-01 00:00:00|119.0|295.0
    imported_09|2020-09-01 00:00:00|2020-10-01 00:00:00|60.0|181.0
    imported_10|2020-10-01 00:00:00|2020-11-01 00:00:00|55.0|160.0
    imported_11|2020-11-01 00:00:00|2020-12-01 00:00:00|104.0|350.0
    imported_12|2020-12-01 00:00:00|2021-01-01 00:00:00|59.0|177.0
    min_min=55.0
    max_max=350.0
    min_min=55.0
    max_max=350.0
     | Title:
     | Copy of precipitation
     | Description:
     | Imported from the archive
    ```

### Link the files instead of importing the cells

With **-l**, the maps are linked to the GeoTIFF files with *r.external*: the
cells stay in the files, which **directory** names and the tool leaves there.
The directory `files` has to exist. The commands count the GeoTIFF files in
it, print the type of the first map, `GDAL-link` for a linked map, and the
range of the linked dataset, which is that of the exported maps. The maps read their
cells from the files, so the files must stay where they are.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    mkdir files
    t.rast.import -l input=precipitation.tar.bz2 output=linked \
        basename=linked directory=files
    ls files | grep -c tif
    r.info -e map=linked_01 | grep maptype
    t.info -g input=linked | grep -E "^(min_min|max_max)="
    ```

    ```text
    12
    maptype=GDAL-link
    min_min=55.0
    max_max=350.0
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    Path("files").mkdir()
    tools.t_rast_import(
        input="precipitation.tar.bz2",
        output="linked",
        basename="linked",
        directory="files",
        flags="l",
    )
    print(len(list(Path("files").glob("*.tif"))))
    print("maptype=" + tools.r_info(map="linked_01", flags="e").keyval["maptype"])
    info = tools.t_info(input="linked", flags="g").keyval
    print("\n".join(f"{key}={info[key]}" for key in ("min_min", "max_max")))
    ```

    ```text
    12
    maptype=GDAL-link
    min_min=55.0
    max_max=350.0
    ```

### Import into a new project

With **project**, the tool makes a new project with the coordinate reference
system of the archive, imports into it and goes back to the project it was
called in. The new project is made in the GRASS database of the session, so it
lies next to the project `nc_spm_08_grass7`; it must not exist yet. The maps
keep their names, because the new project has none of them, and **-o** is not
needed. The commands switch to the new project to look at the
dataset in it, and switch back to the mapset of these examples.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.import input=precipitation.tar.bz2 output=precipitation \
        project=archive_copy
    g.mapset project=archive_copy mapset=PERMANENT
    t.info -g input=precipitation | grep -E "^(start_time|end_time|number_of_maps)="
    g.mapset project=nc_spm_08_grass7 mapset=t_rast_import
    ```

    ```text
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    number_of_maps=12
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    def print_extent(flags):
        region = tools.g_region(flags=flags).keyval
        print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))


    tools.t_rast_import(
        input="precipitation.tar.bz2", output="precipitation", project="archive_copy"
    )
    tools.g_mapset(project="archive_copy", mapset="PERMANENT")
    info = tools.t_info(input="precipitation", flags="g").keyval
    keys = ("start_time", "end_time", "number_of_maps")
    print("\n".join(f"{key}={info[key]}" for key in keys))
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_rast_import")
    ```

    ```text
    start_time='2020-01-01 00:00:00'
    end_time='2021-01-01 00:00:00'
    number_of_maps=12
    ```

### Create a project without importing

The flag **-c** makes the project and imports nothing. The commands switch to
the new project and show that it has no raster map and no dataset, and that
its default region is one cell.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.import -c input=precipitation.tar.bz2 output=precipitation \
        project=empty_project
    g.mapset project=empty_project mapset=PERMANENT
    g.list type=raster | wc -l
    t.list type=strds | wc -l
    g.region -dg | grep -E "^(n|s|e|w)="
    g.mapset project=nc_spm_08_grass7 mapset=t_rast_import
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

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_import(
        input="precipitation.tar.bz2",
        output="precipitation",
        project="empty_project",
        flags="c",
    )
    tools.g_mapset(project="empty_project", mapset="PERMANENT")
    for result in (tools.g_list(type="raster"), tools.t_list(type="strds")):
        print(len(result.text.splitlines()) if result else 0)
    print_extent("dg")
    tools.g_mapset(project="nc_spm_08_grass7", mapset="t_rast_import")
    ```

    ```text
    0
    0
    n=1
    s=0
    w=0
    e=1
    ```

### Set the region from the imported maps

The flag **-r** sets the current region to the region of the last map that
was imported, here the whole of North Carolina in cells of 1 km. The first
command moves the region to a small window. The import also sets **-o**,
which skips the check of the coordinate reference system; this archive passes
the check anyway, so the flag changes nothing here.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    g.region n=250000 s=240000 w=500000 e=510000 res=1000
    g.region -g | grep -E "^(n|s|e|w)="
    t.rast.import -o -r input=precipitation.tar.bz2 output=moved basename=moved
    g.region -g | grep -E "^(n|s|e|w)="
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=319000
    s=-16000
    w=124000
    e=963000
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.g_region(n=250000, s=240000, w=500000, e=510000, res=1000)
    print_extent("g")
    tools.t_rast_import(
        input="precipitation.tar.bz2",
        output="moved",
        basename="moved",
        flags="or",
    )
    print_extent("g")
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=319000
    s=-16000
    w=124000
    e=963000
    ```

### Replace a dataset with an ASCII grid archive

The archive in the format `AAIGrid` holds the maps as Arc/Info ASCII Grid
files, which carry no coordinate reference system; the import needs no **-o**
for them. Importing the same archive
again under the same names needs **--overwrite**, which replaces the dataset
and its maps. The commands list the number of maps of the dataset after the
second import. The last block links the ASCII grid files with **-l**; like the
GeoTIFF files in the second example, they stay in the directory `ascii_files`.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    t.rast.export input=precipitation_monthly output=precipitation.tar.gz \
        format=AAIGrid compression=gzip
    t.rast.import input=precipitation.tar.gz output=ascii basename=ascii
    t.rast.import --overwrite input=precipitation.tar.gz output=ascii \
        basename=ascii
    t.info -g input=ascii | grep -E "^(number_of_maps|min_min|max_max)="
    ```

    ```text
    min_min=55.0
    max_max=350.0
    number_of_maps=12
    ```

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    mkdir ascii_files
    t.rast.import -l input=precipitation.tar.gz output=ascii_linked \
        basename=linked_ascii directory=ascii_files
    ls ascii_files | grep -c asc
    r.info -e map=linked_ascii_01 | grep maptype
    ```

    ```text
    12
    maptype=GDAL-link
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    tools.t_rast_export(
        input="precipitation_monthly",
        output="precipitation.tar.gz",
        format="AAIGrid",
        compression="gzip",
    )
    tools.t_rast_import(input="precipitation.tar.gz", output="ascii", basename="ascii")
    tools.t_rast_import(
        input="precipitation.tar.gz", output="ascii", basename="ascii", overwrite=True
    )
    info = tools.t_info(input="ascii", flags="g").keyval
    keys = ("number_of_maps", "min_min", "max_max")
    print("\n".join(f"{key}={info[key]}" for key in keys))
    ```

    ```text
    number_of_maps=12
    min_min=55.0
    max_max=350.0
    ```

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    Path("ascii_files").mkdir()
    tools.t_rast_import(
        input="precipitation.tar.gz",
        output="ascii_linked",
        basename="linked_ascii",
        directory="ascii_files",
        flags="l",
    )
    print(len(list(Path("ascii_files").glob("*.asc"))))
    print("maptype=" + tools.r_info(map="linked_ascii_01", flags="e").keyval["maptype"])
    ```

    ```text
    12
    maptype=GDAL-link
    ```

### Import a dataset with relative time and semantic labels

The dataset `sentinel` has relative time in days and four maps of 10 days
each. The maps alternate between the red band (semantic label `S2_B4`) and
the near infrared band (`S2_B8`). The archive is in the `pack` format and
needs no GDAL driver. The import goes to the new mapset `t_rast_import_2`; the
maps keep their names, because the mapset has none of them, although the maps
of the same names exist in the first mapset. The dataset keeps the unit, the
times and the labels.

The last block moves the region to a small window and imports the archive a
second time with **-e** under another **basename**. The region is the same
before and after, although the maps cover the whole of North Carolina: **-e**
does nothing for a `pack` archive.

=== "Command line"

    ```sh
    r.mapcalc expression="red_1 = 0.05"
    r.mapcalc expression="nir_1 = 0.30"
    r.mapcalc expression="red_2 = 0.07"
    r.mapcalc expression="nir_2 = 0.40"
    r.support map=red_1 semantic_label=S2_B4
    r.support map=nir_1 semantic_label=S2_B8
    r.support map=red_2 semantic_label=S2_B4
    r.support map=nir_2 semantic_label=S2_B8
    t.create output=sentinel temporaltype=relative title="Reflectance" \
        description="Alternating red and near infrared reflectance"
    t.register -i input=sentinel maps=red_1,nir_1,red_2,nir_2 \
        start=0 increment=10 unit=days
    t.rast.export input=sentinel output=sentinel.tar format=pack compression=no
    g.mapset -c mapset=t_rast_import_2
    g.region raster=elev_state_500m res=1000 -a
    t.rast.import input=sentinel.tar output=sentinel_copy
    t.rast.list input=sentinel_copy \
        columns=name,mapset,semantic_label,start_time,end_time
    t.info -g input=sentinel_copy | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|mapset|semantic_label|start_time|end_time
    red_1|t_rast_import_2|S2_B4|0|10
    nir_1|t_rast_import_2|S2_B8|10|20
    red_2|t_rast_import_2|S2_B4|20|30
    nir_2|t_rast_import_2|S2_B8|30|40
    temporal_type=relative
    unit=days
    ```

    ```sh
    g.region n=250000 s=240000 w=500000 e=510000 res=1000
    g.region -g | grep -E "^(n|s|w|e)="
    t.rast.import -e input=sentinel.tar output=sentinel_extended \
        basename=extended
    g.region -g | grep -E "^(n|s|w|e)="
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=250000
    s=240000
    w=500000
    e=510000
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
        temporaltype="relative",
        title="Reflectance",
        description="Alternating red and near infrared reflectance",
    )
    tools.t_register(
        input="sentinel",
        maps="red_1,nir_1,red_2,nir_2",
        start=0,
        increment=10,
        unit="days",
        flags="i",
    )
    tools.t_rast_export(
        input="sentinel", output="sentinel.tar", format="pack", compression="no"
    )
    tools.g_mapset(mapset="t_rast_import_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.t_rast_import(input="sentinel.tar", output="sentinel_copy")
    print(
        tools.t_rast_list(
            input="sentinel_copy",
            columns="name,mapset,semantic_label,start_time,end_time",
        ).text
    )
    info = tools.t_info(input="sentinel_copy", flags="g").keyval
    print("\n".join(f"{key}={info[key]}" for key in ("temporal_type", "unit")))
    ```

    ```text
    name|mapset|semantic_label|start_time|end_time
    red_1|t_rast_import_2|S2_B4|0|10
    nir_1|t_rast_import_2|S2_B8|10|20
    red_2|t_rast_import_2|S2_B4|20|30
    nir_2|t_rast_import_2|S2_B8|30|40
    temporal_type=relative
    unit=days
    ```

    ```python
    tools.g_region(n=250000, s=240000, w=500000, e=510000, res=1000)
    print_extent("g")
    tools.t_rast_import(
        input="sentinel.tar",
        output="sentinel_extended",
        basename="extended",
        flags="e",
    )
    print_extent("g")
    ```

    ```text
    n=250000
    s=240000
    w=500000
    e=510000
    n=250000
    s=240000
    w=500000
    e=510000
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [r.external](r.external.md),
[r.in.gdal](r.in.gdal.md), [r.unpack](r.unpack.md),
[t.create](t.create.md), [t.info](t.info.md), [t.rast.export](t.rast.export.md),
[t.vect.import](t.vect.import.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
