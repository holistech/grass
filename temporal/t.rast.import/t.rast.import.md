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
gets `basename_01` to `basename_10` (see the last example). This is the way
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
GeoTIFF archives as well, because a GeoTIFF file made there holds none; the
examples import AAIGrid and `pack` archives there without it. An import with
**project** needs no **-o**.

The flag **-e** extends the extent of the project to the maps of a `GTiff` or
`AAIGrid` archive: it makes the default region and the current region of the
project cover the imported maps. With **project**, the flag is always on for
these formats, so the new project has the extent of the maps. The maps of a
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
from (0, 0) to (1, 1) for a project without a coordinate reference system. Use
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

The examples run in a project called `temporal_examples`, which has no
coordinate reference system; where a command names this project, use the name
of your own project.

<!-- markdownlint-disable MD046 -->

### Import an archive under new names

The dataset `temperature` has four maps of daily mean air temperature for the
days from 1 to 4 March 2026. The maps have three columns and two rows, and
their values are the column number plus the offset 0, 3, 6 and 9. The first
block creates it.

The second block writes the archive `temperature.tar.bz2` with
*[t.rast.export](t.rast.export.md)* and imports it into the same project. The
maps of the archive carry the names of the maps that exist already, so
**basename** names the new maps `imported_1` to `imported_4`. The flag **-o**
is needed in the project of the examples, which has no coordinate reference
system, because the GeoTIFF files hold none. **title** and **description** are
set, and **memory** limits the cache of *r.in.gdal* to 100 MB. The commands
print the new dataset and the minimum and the maximum of its maps, which are
those of the exported maps (the map `imported_n` holds the values from 3n - 2
to 3n), and the title and the description of the dataset from *t.info*.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="temperature_1 = col()"
    r.mapcalc expression="temperature_2 = col() + 3"
    r.mapcalc expression="temperature_3 = col() + 6"
    r.mapcalc expression="temperature_4 = col() + 9"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3,temperature_4 \
        start=2026-03-01 increment="1 day"
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=temperature output=temperature.tar.bz2
    t.rast.import -o input=temperature.tar.bz2 output=copy basename=imported \
        title="Copy of temperature" description="Imported from the archive" \
        memory=100
    t.rast.list input=copy
    t.rast.univar input=copy | cut -d"|" -f1,7,8
    t.info input=copy | grep -A3 "Title:"
    ```

    ```text
    name|mapset|start_time|end_time
    imported_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    imported_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    imported_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    imported_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    id|min|max
    imported_1@PERMANENT|1|3
    imported_2@PERMANENT|4|6
    imported_3@PERMANENT|7|9
    imported_4@PERMANENT|10|12
     | Title:
     | Copy of temperature
     | Description:
     | Imported from the archive
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for number, offset in enumerate((0, 3, 6, 9), start=1):
        tools.r_mapcalc(expression=f"temperature_{number} = col() + {offset}")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3,temperature_4",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="temperature", output="temperature.tar.bz2")
    tools.t_rast_import(
        input="temperature.tar.bz2",
        output="copy",
        basename="imported",
        title="Copy of temperature",
        description="Imported from the archive",
        memory=100,
        flags="o",
    )
    print(tools.t_rast_list(input="copy").text)
    for line in tools.t_rast_univar(input="copy").text.splitlines():
        fields = line.split("|")
        print("|".join(fields[index] for index in (0, 6, 7)))
    info = tools.t_info(input="copy").stdout.splitlines()
    first = next(index for index, line in enumerate(info) if "Title:" in line)
    print("\n".join(info[first : first + 4]))
    ```

    ```text
    name|mapset|start_time|end_time
    imported_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    imported_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    imported_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    imported_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    id|min|max
    imported_1@PERMANENT|1|3
    imported_2@PERMANENT|4|6
    imported_3@PERMANENT|7|9
    imported_4@PERMANENT|10|12
     | Title:
     | Copy of temperature
     | Description:
     | Imported from the archive
    ```

### Link the files instead of importing the cells

With **-l**, the maps are linked to the GeoTIFF files with *r.external*: the
cells stay in the files, which **directory** names and the tool leaves there.
The directory `files` has to exist. The commands list the GeoTIFF files in it,
print the type of the first map, `GDAL-link` for a linked map, and its
minimum and maximum, which are those of the exported map (1 and 3). The maps
read their cells from the files, so the files must stay where they are.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    mkdir files
    t.rast.import -l -o input=temperature.tar.bz2 output=linked \
        basename=linked directory=files
    ls files | grep tif
    r.info -e map=linked_1 | grep maptype
    r.univar -g map=linked_1 | grep -E "^(min|max)="
    ```

    ```text
    temperature_1.tif
    temperature_2.tif
    temperature_3.tif
    temperature_4.tif
    maptype=GDAL-link
    min=1
    max=3
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    Path("files").mkdir()
    tools.t_rast_import(
        input="temperature.tar.bz2",
        output="linked",
        basename="linked",
        directory="files",
        flags="lo",
    )
    print("\n".join(sorted(path.name for path in Path("files").glob("*.tif"))))
    print("maptype=" + tools.r_info(map="linked_1", flags="e").keyval["maptype"])
    for key, value in tools.r_univar(map="linked_1", flags="g").keyval.items():
        if key in ("min", "max"):
            print(f"{key}={value}")
    ```

    ```text
    temperature_1.tif
    temperature_2.tif
    temperature_3.tif
    temperature_4.tif
    maptype=GDAL-link
    min=1
    max=3
    ```

### Import into a new project

With **project**, the tool makes a new project with the coordinate reference
system of the archive, imports into it and goes back to the project it was
called in. The project of the examples has none, so the new project has none
either, and **-o** is not needed. The maps keep their names, because the new
project has none of them. The new project takes the extent of the maps. The
commands switch to the new project to look at it and switch back, to the
project `temporal_examples` of these examples.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.import input=temperature.tar.bz2 output=temperature \
        project=archive_copy
    g.mapset project=archive_copy mapset=PERMANENT
    t.rast.list input=temperature
    g.region -dg | grep -E "^(n|s|e|w)="
    g.mapset project=temporal_examples mapset=PERMANENT
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    n=2
    s=0
    w=0
    e=3
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_import(
        input="temperature.tar.bz2", output="temperature", project="archive_copy"
    )
    tools.g_mapset(project="archive_copy", mapset="PERMANENT")
    print(tools.t_rast_list(input="temperature").text)
    region = tools.g_region(flags="dg").keyval
    print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))
    tools.g_mapset(project="temporal_examples", mapset="PERMANENT")
    ```

    ```text
    name|mapset|start_time|end_time
    temperature_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    temperature_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    n=2
    s=0
    w=0
    e=3
    ```

### Create a project and extend its region

The flag **-c** makes the project and imports nothing. The default region of a
new project without a coordinate reference system is one cell from (0, 0) to
(1, 1). The second import into it uses **-e**, so the default region and the
current region grow to the extent of the maps, 3 columns and 2 rows.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.import -c input=temperature.tar.bz2 output=temperature \
        project=empty_project
    g.mapset project=empty_project mapset=PERMANENT
    g.region -dg | grep -E "^(n|s|e|w)="
    t.rast.import -o -e input=temperature.tar.bz2 output=temperature
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
    e=3
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    def print_extent(flags):
        region = tools.g_region(flags=flags).keyval
        print("\n".join(f"{key}={region[key]}" for key in ("n", "s", "w", "e")))


    tools.t_rast_import(
        input="temperature.tar.bz2",
        output="temperature",
        project="empty_project",
        flags="c",
    )
    tools.g_mapset(project="empty_project", mapset="PERMANENT")
    print_extent("dg")
    tools.t_rast_import(input="temperature.tar.bz2", output="temperature", flags="oe")
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
    e=3
    ```

### Set the region from the imported maps

The flag **-r** sets the current region to the region of the last map that
was imported, here 2 rows and 3 columns. The first command moves the region far
away from the maps.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    g.region n=100 s=90 w=50 e=60 res=1
    g.region -g | grep -E "^(n|s|e|w)="
    t.rast.import -o -r input=temperature.tar.bz2 output=moved basename=moved
    g.region -g | grep -E "^(n|s|e|w)="
    ```

    ```text
    n=100
    s=90
    w=50
    e=60
    n=2
    s=0
    w=0
    e=3
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.g_region(n=100, s=90, w=50, e=60, res=1)
    print_extent("g")
    tools.t_rast_import(
        input="temperature.tar.bz2",
        output="moved",
        basename="moved",
        flags="or",
    )
    print_extent("g")
    ```

    ```text
    n=100
    s=90
    w=50
    e=60
    n=2
    s=0
    w=0
    e=3
    ```

### Import a dataset with relative time and semantic labels

The dataset `sentinel` has relative time in days and four maps of 10 days
each. The maps alternate between the red band (semantic label `S2_B4`) and
the near infrared band (`S2_B8`). The archive is in the `pack` format and
needs no GDAL driver. The import goes to the new mapset `archive`; the maps
keep their names, because the mapset has none of them, and the dataset keeps
the unit, the times and the labels.

The last block imports the archive a second time with **-e** under another
**basename**. The new mapset has the region of one cell, and the region is the
same before and after, although the maps have 2 rows and 3 columns: **-e**
does nothing for a `pack` archive.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
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
    g.mapset -c mapset=archive
    t.rast.import input=sentinel.tar output=sentinel_copy
    t.rast.list input=sentinel_copy \
        columns=name,mapset,semantic_label,start_time,end_time
    t.info -g input=sentinel_copy | grep -E "^(temporal_type|unit)="
    ```

    ```text
    name|mapset|semantic_label|start_time|end_time
    red_1|archive|S2_B4|0|10
    nir_1|archive|S2_B8|10|20
    red_2|archive|S2_B4|20|30
    nir_2|archive|S2_B8|30|40
    temporal_type=relative
    unit=days
    ```

    ```sh
    g.region -g | grep -E "^(n|s|w|e)="
    t.rast.import -e input=sentinel.tar output=sentinel_extended \
        basename=extended
    g.region -g | grep -E "^(n|s|w|e)="
    g.mapset mapset=PERMANENT
    ```

    ```text
    n=1
    s=0
    w=0
    e=1
    n=1
    s=0
    w=0
    e=1
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
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
    tools.g_mapset(mapset="archive", flags="c")
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
    red_1|archive|S2_B4|0|10
    nir_1|archive|S2_B8|10|20
    red_2|archive|S2_B4|20|30
    nir_2|archive|S2_B8|30|40
    temporal_type=relative
    unit=days
    ```

    ```python
    print_extent("g")
    tools.t_rast_import(
        input="sentinel.tar",
        output="sentinel_extended",
        basename="extended",
        flags="e",
    )
    print_extent("g")
    tools.g_mapset(mapset="PERMANENT")
    ```

    ```text
    n=1
    s=0
    w=0
    e=1
    n=1
    s=0
    w=0
    e=1
    ```

### Replace a dataset with an ASCII grid archive

The archive in the format `AAIGrid` holds the maps as Arc/Info ASCII Grid
files, which carry no coordinate reference system; the import needs no
**-o** for them in the project of the examples. Importing the same archive
again under the same names needs **--overwrite**, which replaces the dataset
and its maps. The commands list the dataset after the second import. The last
block links the ASCII grid files with **-l**; like the GeoTIFF files in the
second example, they stay in the directory `ascii_files`.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    t.rast.export input=temperature output=temperature.tar.gz \
        format=AAIGrid compression=gzip
    t.rast.import input=temperature.tar.gz output=ascii basename=ascii
    t.rast.import --overwrite input=temperature.tar.gz output=ascii \
        basename=ascii
    t.rast.list input=ascii
    ```

    ```text
    name|mapset|start_time|end_time
    ascii_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    ascii_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    ascii_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    ascii_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    mkdir ascii_files
    t.rast.import -l input=temperature.tar.gz output=ascii_linked \
        basename=linked_ascii directory=ascii_files
    ls ascii_files | grep asc
    r.info -e map=linked_ascii_1 | grep maptype
    ```

    ```text
    temperature_1.asc
    temperature_2.asc
    temperature_3.asc
    temperature_4.asc
    maptype=GDAL-link
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    tools.t_rast_export(
        input="temperature",
        output="temperature.tar.gz",
        format="AAIGrid",
        compression="gzip",
    )
    tools.t_rast_import(input="temperature.tar.gz", output="ascii", basename="ascii")
    tools.t_rast_import(
        input="temperature.tar.gz", output="ascii", basename="ascii", overwrite=True
    )
    print(tools.t_rast_list(input="ascii").text)
    ```

    ```text
    name|mapset|start_time|end_time
    ascii_1|PERMANENT|2026-03-01 00:00:00|2026-03-02 00:00:00
    ascii_2|PERMANENT|2026-03-02 00:00:00|2026-03-03 00:00:00
    ascii_3|PERMANENT|2026-03-03 00:00:00|2026-03-04 00:00:00
    ascii_4|PERMANENT|2026-03-04 00:00:00|2026-03-05 00:00:00
    ```

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    Path("ascii_files").mkdir()
    tools.t_rast_import(
        input="temperature.tar.gz",
        output="ascii_linked",
        basename="linked_ascii",
        directory="ascii_files",
        flags="l",
    )
    print("\n".join(sorted(path.name for path in Path("ascii_files").glob("*.asc"))))
    print("maptype=" + tools.r_info(map="linked_ascii_1", flags="e").keyval["maptype"])
    ```

    ```text
    temperature_1.asc
    temperature_2.asc
    temperature_3.asc
    temperature_4.asc
    maptype=GDAL-link
    ```

### Numbers of the new maps

The dataset `long` has ten maps. With **basename**, the suffix has two digits
because there are ten maps, so the new maps are `part_01` to `part_10`. With
fewer than ten maps, as in the first example, the suffix is a single digit.

=== "Command line"

    ```sh
    for number in 1 2 3 4 5 6 7 8 9 10; do
        r.mapcalc expression="long_$number = $number"
    done
    t.create output=long title="Ten maps" description="Ten constant maps"
    t.register -i input=long \
        maps=long_1,long_2,long_3,long_4,long_5,long_6,long_7,long_8,long_9,long_10 \
        start=2026-04-01 increment="1 day"
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=long output=long.tar
    t.rast.import -o input=long.tar output=part_set basename=part
    t.rast.list input=part_set columns=name
    ```

    ```text
    name
    part_01
    part_02
    part_03
    part_04
    part_05
    part_06
    part_07
    part_08
    part_09
    part_10
    ```

=== "Python (grass.tools)"

    ```python
    names = [f"long_{number}" for number in range(1, 11)]
    for number, name in enumerate(names, start=1):
        tools.r_mapcalc(expression=f"{name} = {number}")
    tools.t_create(output="long", title="Ten maps", description="Ten constant maps")
    tools.t_register(
        input="long",
        maps=",".join(names),
        start="2026-04-01",
        increment="1 day",
        flags="i",
    )
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="long", output="long.tar")
    tools.t_rast_import(input="long.tar", output="part_set", basename="part", flags="o")
    print(tools.t_rast_list(input="part_set", columns="name").text)
    ```

    ```text
    name
    part_01
    part_02
    part_03
    part_04
    part_05
    part_06
    part_07
    part_08
    part_09
    part_10
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
