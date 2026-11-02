## DESCRIPTION

*t.rast.export* writes the maps of a space time raster dataset and a
description of their times into one tar archive. The archive moves a dataset
to another project or computer: *[t.rast.import](t.rast.import.md)* reads it
back and registers the maps in a new dataset. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool for space time vector datasets is
*[t.vect.export](t.vect.export.md)*.

The option **input** names the space time raster dataset, and **output** the
archive that is written. The tool uses the name of **output** as it is and adds
no suffix, so the name should say what the archive is, such as
`temperature.tar.bz2`. An existing archive is refused unless the flag
**--overwrite** is given.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2026-03-03'`, and exports only the maps it
selects. Without **where**, all maps are exported. The maps are written in the
order of their start time; the order of maps with the same start time is not
defined. A selection without a map is not an error (see the notes).

### Export format

The option **format** chooses how each raster map is stored in the archive:

- `GTiff`, the default, writes a GeoTIFF file `name.tif` with
  *[r.out.gdal](r.out.gdal.md)* and the color table of the map as the rules
  file `name.color` with *[r.colors.out](r.colors.out.md)*;
- `AAIGrid` writes an Arc/Info ASCII Grid file `name.asc` with *r.out.gdal*
  and the rules file `name.color`;
- `pack` writes the file `name.pack` with *[r.pack](r.pack.md)*, the GRASS
  format that *r.unpack* reads. There is no `.color` file. The `.pack` file is
  a tar archive of its own that is not compressed again.

The GeoTIFF and ASCII grid files cover the current computational region, as
*r.out.gdal* does, and a `pack` file holds the whole map (see the last
example for the region).

### Options of GeoTIFF and ASCII grid files

The following options are passed on to *r.out.gdal*. They are skipped with a
warning for the `pack` format, which has no use for them.

- **type** sets the data type of the files: `Byte`, `Int16`, `UInt16`,
  `Int32`, `UInt32`, `Float32`, `Float64`, `CInt16`, `CInt32`, `CFloat32` or
  `CFloat64`. It is used for `GTiff` only and skipped with a warning for
  `AAIGrid` and `pack`. Without **type**, a map of floating point cells gets
  the type that *r.out.gdal* chooses; for a map of integer cells the tool
  chooses the type (see **nodata**).
- **nodata** sets the value that marks the cells without data in the files.
  Without **nodata**, a GeoTIFF file of an integer map without **type** gets
  the value `maximum + 1` of the map, and the smallest of the types `Byte`,
  `UInt16`, `UInt32` and `Int32` that holds the values of the map and this
  value: a map of the values 5 and NULL becomes a `Byte` file with the nodata
  value 6. For a map of integer cells with **nodata** and without **type**, the
  tool takes the smallest of the types `Byte`, `UInt16`, `Int16`, `UInt32` and
  `Int32` that holds the values of the map and the nodata value: a map of the
  values 5 and NULL with `nodata=-77` becomes an `Int16` file. **nodata** also
  applies to `AAIGrid`: it is the value of the cells without data in the header
  and in the rows of the file.
- **createopt** passes creation options to the GDAL driver, written as
  `NAME=VALUE` and separated by commas, such as `COMPRESS=DEFLATE` for
  GeoTIFF. `AAIGrid` takes **createopt** without a warning.
- **metaopt** writes metadata to the files, written as `TAG=VALUE` and
  separated by commas. It works for `GTiff` only: *r.out.gdal* writes the
  metadata of an ASCII grid into a side file that the archive does not hold,
  so *t.rast.export* skips **metaopt** with a warning for `AAIGrid` and `pack`.

### Archive and compression

The option **compression** compresses the archive: `bzip2` (the default),
`gzip`, or `no` for a plain tar archive. A tool such as `tar -tf` or the Python
module `tarfile` recognises the compression by itself.

The option **directory** names the working directory, by default the current
directory. *t.rast.export* exports the maps into a temporary subdirectory of
it, packs them there, moves the archive to the path given by **output** and
removes the subdirectory. The archive is therefore not written to
**directory**, and a relative **output** is taken from the current directory.

### Files in the archive

The archive holds the files of the maps, in the order of their start time, and
then five text files:

- `list.txt` has one line for each map, with the fields name, start time, end
  time and a fourth field that is `None` for a map without a semantic label,
  separated by `|`. Start and end time are in ISO format with absolute time
  and numbers with relative time;
- `proj.txt` is the output of *[g.proj](g.proj.md)* with `-p format=proj4`,
  the coordinate reference system of the project;
- `init.txt` has one `key=value` line for each of the following: `stds_type`,
  `format`, `temporal_type`, `semantic_type`, `relative_time_unit` (relative
  time only), `number_of_maps` and the extent `north`, `south`, `east`, `west`.
  `number_of_maps` counts the exported maps, and the extent is that of the
  exported maps, not of the region;
- `readme.txt` describes the files of the archive;
- `metadata.txt` is the output of *[t.info](t.info.md)* for the dataset.

## NOTES

The export reads the maps from the mapsets they were registered from, also
if a map of the same name exists in the current mapset. The maps of a dataset
may come from several mapsets. If maps of one name from different mapsets are
exported together, each of them is named `name@mapset` in the archive, in
`list.txt` and in its file names, for example `dup@other.tif` and
`dup@other.color`. A map whose name no other mapset of the selection shares
keeps its name, so an archive without such maps has the form of older versions.
*[t.rast.import](t.rast.import.md)* imports `dup@other` as `dup_other`.

With relative time, `list.txt` holds the numbers of the start and end, and
`init.txt` the unit as `relative_time_unit`.

A **where** condition that selects no map gives the warning "The selection
contains no map" and an archive without maps, with `number_of_maps=0` in
`init.txt`. A condition with a syntax error stops the tool with an error that
starts with "Invalid where condition".

The tool checks the directories before it makes anything. It stops with
"Directory ... not found" or "... is not writable" for **directory**, and with
"Output directory ... not found" for the directory of **output**; both must
exist and be writable. A map that can no longer be exported, for example
because it was removed, stops the tool with "Unable to export raster map
`name@mapset`"; no archive is left, and the temporary subdirectory is removed
in every case.

For a map of integer cells, a **nodata** value that no integer type holds, such
as `nan`, leaves the choice of the type to *r.out.gdal*, which refuses it for
the type it picks; the tool then stops with "Unable to export raster map".

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Export a dataset as a GeoTIFF archive

The dataset `temperature` has four maps of daily mean air temperature for the
days from 1 to 4 March 2026. The maps have three columns and two rows, and
their values are the column number plus the offset 0, 3, 6 and 9.

The first block creates the dataset. The second exports it with the default
format and compression: a GeoTIFF file and a color rules file for each map,
packed into a bzip2 compressed archive. `tar -tf` lists the files. The maps
come first in the order of their start time, then the five text files. The
third block shows what `list.txt` and `init.txt` say about the dataset. The
extent in `init.txt` is that of the maps, and `proj.txt` shows that the project
of the examples has no coordinate reference system.

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
    tar -tf temperature.tar.bz2
    ```

    ```text
    temperature_1.tif
    temperature_1.color
    temperature_2.tif
    temperature_2.color
    temperature_3.tif
    temperature_3.color
    temperature_4.tif
    temperature_4.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    tar -xOf temperature.tar.bz2 list.txt
    tar -xOf temperature.tar.bz2 init.txt
    tar -xOf temperature.tar.bz2 proj.txt
    ```

    ```text
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00|None
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00|None
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00|None
    temperature_4|2026-03-04 00:00:00|2026-03-05 00:00:00|None
    stds_type=strds
    format=GTiff
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=4
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    XY location (unprojected)
    ```

=== "Python (grass.tools)"

    ```python
    import tarfile

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


    def read_member(archive, member):
        with tarfile.open(archive) as tar:
            return tar.extractfile(member).read().decode()
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="temperature", output="temperature.tar.bz2")
    with tarfile.open("temperature.tar.bz2") as tar:
        print("\n".join(tar.getnames()))
    ```

    ```text
    temperature_1.tif
    temperature_1.color
    temperature_2.tif
    temperature_2.color
    temperature_3.tif
    temperature_3.color
    temperature_4.tif
    temperature_4.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    for member in ("list.txt", "init.txt", "proj.txt"):
        print(read_member("temperature.tar.bz2", member), end="")
    ```

    ```text
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00|None
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00|None
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00|None
    temperature_4|2026-03-04 00:00:00|2026-03-05 00:00:00|None
    stds_type=strds
    format=GTiff
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=4
    north=2.0
    south=0.0
    east=3.0
    west=0.0
    XY location (unprojected)
    ```

### Export the maps of a time window

**where** selects the maps of 3 and 4 March, and **directory** names the
working directory `work`. The archive holds the files of two maps, and
`number_of_maps` in `init.txt` counts two. The tool exports and packs in a
temporary subdirectory of `work` and removes it, so the last command finds
`work` empty: the archive is in the current directory, where **output** puts
it.

=== "Command line"

    ```sh
    mkdir work
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=temperature output=later.tar.bz2 directory=work \
        where="start_time >= '2026-03-03'"
    tar -tf later.tar.bz2
    tar -xOf later.tar.bz2 init.txt | grep number_of_maps
    ls -A work | wc -l
    ```

    ```text
    temperature_3.tif
    temperature_3.color
    temperature_4.tif
    temperature_4.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=2
    0
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    Path("work").mkdir()
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(
        input="temperature",
        output="later.tar.bz2",
        directory="work",
        where="start_time >= '2026-03-03'",
    )
    with tarfile.open("later.tar.bz2") as tar:
        print("\n".join(tar.getnames()))
    init = read_member("later.tar.bz2", "init.txt")
    print([line for line in init.splitlines() if "number_of_maps" in line][0])
    print(len(list(Path("work").iterdir())))
    ```

    ```text
    temperature_3.tif
    temperature_3.color
    temperature_4.tif
    temperature_4.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=2
    0
    ```

### Choose the compression

The loop exports the dataset three times into the archive `all.tar`, which
**--overwrite** replaces each time. It prints the compression, what the first
two bytes of the file say about it and the number of files in the archive. A
gzip file starts with the bytes `1f8b` and a bzip2 file with `425a` (the
letters `BZ`); a plain tar archive has neither. All three hold the same 13
files, and `tar` reads them without being told the compression.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    for compression in no gzip bzip2; do
        t.rast.export input=temperature output=all.tar \
            compression=$compression --overwrite
        magic=$(od -An -tx1 -N2 all.tar | tr -d ' ')
        case $magic in
            1f8b) kind=gzip ;;
            425a) kind=bzip2 ;;
            *) kind="plain tar" ;;
        esac
        echo "$compression: $kind, $(tar -tf all.tar | wc -l) files"
    done
    ```

    ```text
    no: plain tar, 13 files
    gzip: gzip, 13 files
    bzip2: bzip2, 13 files
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    for compression in ("no", "gzip", "bzip2"):
        tools.t_rast_export(
            input="temperature",
            output="all.tar",
            compression=compression,
            overwrite=True,
        )
        kinds = {"1f8b": "gzip", "425a": "bzip2"}
        kind = kinds.get(Path("all.tar").read_bytes()[:2].hex(), "plain tar")
        with tarfile.open("all.tar") as tar:
            print(f"{compression}: {kind}, {len(tar.getnames())} files")
    ```

    ```text
    no: plain tar, 13 files
    gzip: gzip, 13 files
    bzip2: bzip2, 13 files
    ```

### Set the data type and the nodata value

The dataset `land` has two maps of the value 5 and 8 in the third column and
NULL in the other two. The first block exports it without options and reads
the data type and the nodata value of the first GeoTIFF file with
*gdalinfo*. The maps are integer maps, so the tool takes `maximum + 1` as the
nodata value, 6, and `Byte` as the smallest type that holds 5 and 6.

The second block adds `nodata=-77`. A `Byte` cannot hold -77, so the tool
takes `Int16`. The third block sets the type itself and passes a creation
option and a metadata tag to the GeoTIFF driver: the file is compressed with
`DEFLATE` and carries the tag `TAG=hello`.

=== "Command line"

    ```sh
    r.mapcalc expression="land_1 = if(col() == 3, 5, null())"
    r.mapcalc expression="land_2 = if(col() == 3, 8, null())"
    t.create output=land title="Land use" description="Land use classes"
    t.register -i input=land maps=land_1,land_2 \
        start=2026-03-01 increment="1 day"
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=land output=land_default.tar compression=no
    tar -xf land_default.tar land_1.tif
    gdalinfo land_1.tif | grep -E "Type=|NoData"
    ```

    ```text
    Band 1 Block=3x2 Type=Byte, ColorInterp=Gray
      NoData Value=6
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=land output=land_nodata.tar compression=no nodata=-77
    tar -xf land_nodata.tar land_1.tif
    gdalinfo land_1.tif | grep -E "Type=|NoData"
    ```

    ```text
    Band 1 Block=3x2 Type=Int16, ColorInterp=Gray
      NoData Value=-77
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=land output=land_options.tar compression=no \
        type=Int16 nodata=-77 createopt="COMPRESS=DEFLATE" metaopt="TAG=hello"
    tar -xf land_options.tar land_1.tif
    gdalinfo land_1.tif | grep -E "Type=|NoData|COMPRESSION|TAG=hello"
    ```

    ```text
      TAG=hello
      COMPRESSION=DEFLATE
    Band 1 Block=3x2 Type=Int16, ColorInterp=Gray
      NoData Value=-77
    ```

=== "Python (grass.tools)"

    ```python
    import re
    import subprocess

    tools.r_mapcalc(expression="land_1 = if(col() == 3, 5, null())")
    tools.r_mapcalc(expression="land_2 = if(col() == 3, 8, null())")
    tools.t_create(output="land", title="Land use", description="Land use classes")
    tools.t_register(
        input="land",
        maps="land_1,land_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )


    def print_gdalinfo(archive, member, pattern):
        with tarfile.open(archive) as tar:
            tar.extract(member, filter="data")
        info = subprocess.run(
            ["gdalinfo", member], capture_output=True, text=True, check=True
        ).stdout
        print("\n".join(line for line in info.splitlines() if re.search(pattern, line)))
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="land", output="land_default.tar", compression="no")
    print_gdalinfo("land_default.tar", "land_1.tif", "Type=|NoData")
    ```

    ```text
    Band 1 Block=3x2 Type=Byte, ColorInterp=Gray
      NoData Value=6
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(
        input="land", output="land_nodata.tar", compression="no", nodata=-77
    )
    print_gdalinfo("land_nodata.tar", "land_1.tif", "Type=|NoData")
    ```

    ```text
    Band 1 Block=3x2 Type=Int16, ColorInterp=Gray
      NoData Value=-77
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(
        input="land",
        output="land_options.tar",
        compression="no",
        type="Int16",
        nodata=-77,
        createopt="COMPRESS=DEFLATE",
        metaopt="TAG=hello",
    )
    print_gdalinfo("land_options.tar", "land_1.tif", "Type=|NoData|COMPRESSION|TAG=hello")
    ```

    ```text
      TAG=hello
      COMPRESSION=DEFLATE
    Band 1 Block=3x2 Type=Int16, ColorInterp=Gray
      NoData Value=-77
    ```

### Export as an ASCII grid or in the GRASS pack format

With `format=AAIGrid`, the maps of `land` are written as Arc/Info ASCII Grid
files. `nodata=-77` is the value of the NULL cells in the header and in the
two rows of the file: the first two columns are -77, the third is 5.

With `format=pack`, each map is one `.pack` file and there are no `.color`
files. *r.pack* has no use for the options **type**, **nodata**, **createopt**
and **metaopt**, so the tool skips them with a warning.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    t.rast.export input=land output=land_ascii.tar compression=no \
        format=AAIGrid nodata=-77
    tar -tf land_ascii.tar
    tar -xOf land_ascii.tar land_1.asc
    ```

    ```text
    land_1.asc
    land_1.color
    land_2.asc
    land_2.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ncols        3
    nrows        2
    xllcorner    0.000000000000
    yllcorner    0.000000000000
    cellsize     1.000000000000
    NODATA_value -77
    -77 -77 5 
    -77 -77 5 
    ```

    ```sh
    t.rast.export input=land output=land_pack.tar compression=no format=pack
    tar -tf land_pack.tar
    ```

    ```text
    land_1.pack
    land_2.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    tools.t_rast_export(
        input="land",
        output="land_ascii.tar",
        compression="no",
        format="AAIGrid",
        nodata=-77,
    )
    with tarfile.open("land_ascii.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("land_ascii.tar", "land_1.asc"), end="")
    ```

    ```text
    land_1.asc
    land_1.color
    land_2.asc
    land_2.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ncols        3
    nrows        2
    xllcorner    0.000000000000
    yllcorner    0.000000000000
    cellsize     1.000000000000
    NODATA_value -77
    -77 -77 5 
    -77 -77 5 
    ```

    ```python
    tools.t_rast_export(
        input="land", output="land_pack.tar", compression="no", format="pack"
    )
    with tarfile.open("land_pack.tar") as tar:
        print("\n".join(tar.getnames()))
    ```

    ```text
    land_1.pack
    land_2.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

### Export with a smaller region

GeoTIFF and ASCII grid files cover the current region, a `pack` file the
whole map. The first block narrows the region to the first two columns and
exports `land` in all three formats. The GeoTIFF file is 2 by 2 cells, the
ASCII grid has two columns, and the packed map still has its three columns
and two rows. `init.txt` still gives the extent of the maps, east 3.0. The
last command resets the region.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    g.region n=2 s=0 e=2 w=0 res=1
    t.rast.export input=land output=cut_tif.tar compression=no
    t.rast.export input=land output=cut_asc.tar compression=no format=AAIGrid
    t.rast.export input=land output=cut_pack.tar compression=no format=pack
    tar -xf cut_tif.tar land_1.tif
    gdalinfo land_1.tif | grep "Size is"
    tar -xOf cut_asc.tar land_1.asc | head -2
    tar -xOf cut_pack.tar land_1.pack | tar -xOf - land_1/cellhd | grep -E "^(cols|rows)"
    tar -xOf cut_tif.tar init.txt | grep -E "^(east|west)="
    g.region n=2 s=0 e=3 w=0 res=1
    ```

    ```text
    Size is 2, 2
    ncols        2
    nrows        2
    cols:       3
    rows:       2
    east=3.0
    west=0.0
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    tools.g_region(n=2, s=0, e=2, w=0, res=1)
    tools.t_rast_export(input="land", output="cut_tif.tar", compression="no")
    tools.t_rast_export(
        input="land", output="cut_asc.tar", compression="no", format="AAIGrid"
    )
    tools.t_rast_export(
        input="land", output="cut_pack.tar", compression="no", format="pack"
    )
    print_gdalinfo("cut_tif.tar", "land_1.tif", "Size is")
    print("".join(read_member("cut_asc.tar", "land_1.asc").splitlines(True)[:2]), end="")
    with tarfile.open("cut_pack.tar") as outer:
        with tarfile.open(fileobj=outer.extractfile("land_1.pack"), mode="r:") as inner:
            header = inner.extractfile("land_1/cellhd").read().decode()
    print("\n".join(line for line in header.splitlines() if line[:4] in ("cols", "rows")))
    init = read_member("cut_tif.tar", "init.txt")
    print("\n".join(line for line in init.splitlines() if line[:4] in ("east", "west")))
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    ```

    ```text
    Size is 2, 2
    ncols        2
    nrows        2
    cols:       3
    rows:       2
    east=3.0
    west=0.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.proj](g.proj.md), [r.colors.out](r.colors.out.md),
[r.out.gdal](r.out.gdal.md), [r.pack](r.pack.md),
[t.create](t.create.md), [t.info](t.info.md),
[t.rast.import](t.rast.import.md), [t.vect.export](t.vect.export.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
