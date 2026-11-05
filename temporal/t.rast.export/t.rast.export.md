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
  value: a map of the values up to 350 and NULL becomes a `UInt16` file with
  the nodata value 351. For a map of integer cells with **nodata** and without
  **type**, the tool takes the smallest of the types `Byte`, `UInt16`, `Int16`,
  `UInt32` and `Int32` that holds the values of the map and the nodata value: a
  map of the same values with `nodata=-77` becomes an `Int16` file. **nodata** also
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

A dataset of another mapset (`input=name@mapset`) is exported like one of the
current mapset; the tool reads its maps from their own mapset.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_export` and sets the computational region
to North Carolina with cells of 1 km, then narrows it to a part of the coast
near Wilmington; the later examples work in this mapset and region.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_export -->

<!-- markdownlint-disable MD046 -->

### Export a dataset as a GeoTIFF archive

The dataset `precipitation_monthly` has twelve maps of the monthly precipitation
sum in 2020, in whole millimeters. Each map is an interval of one month. The
maps are generated, not measured: *[v.surf.idw](v.surf.idw.md)* interpolates
the monthly means of the 136 climate stations in `precip_30ynormals` (columns
`jan` to `dec`), and an assumed factor between 0.8 and 1.7 for each month turns
them into the sums of a wet year. Cells outside North Carolina are NULL.

The first block creates the dataset and then narrows the region to eight by
four cells on the coast near Wilmington. GeoTIFF and ASCII grid files cover
the current region, so the archives stay small. The second block exports the
dataset with the default format and compression: a GeoTIFF file and a color
rules file for each of the twelve maps, packed into a bzip2 compressed
archive. `tar -tf` lists 29 entries, of which the block shows the first four
and the last five. The maps come first in the order of their start time, then
the five text files. The third block shows the first three lines of `list.txt`
and all of `init.txt`. The extent in `init.txt` is that of the maps, North
Carolina, not that of the narrowed region.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_export
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
    g.region n=48000 s=44000 w=715000 e=723000 res=1000
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=precipitation_monthly output=precipitation.tar.bz2
    tar -tf precipitation.tar.bz2 | sed -n 1,4p
    tar -tf precipitation.tar.bz2 | tail -5
    tar -tf precipitation.tar.bz2 | wc -l
    ```

    ```text
    precipitation_monthly_2020_01.tif
    precipitation_monthly_2020_01.color
    precipitation_monthly_2020_02.tif
    precipitation_monthly_2020_02.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    29
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    tar -xOf precipitation.tar.bz2 list.txt | sed -n 1,3p
    tar -xOf precipitation.tar.bz2 init.txt
    ```

    ```text
    precipitation_monthly_2020_01|2020-01-01 00:00:00|2020-02-01 00:00:00|None
    precipitation_monthly_2020_02|2020-02-01 00:00:00|2020-03-01 00:00:00|None
    precipitation_monthly_2020_03|2020-03-01 00:00:00|2020-04-01 00:00:00|None
    stds_type=strds
    format=GTiff
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=12
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    ```

=== "Python (grass.tools)"

    ```python
    import tarfile

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_export")
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
    tools.g_region(n=48000, s=44000, w=715000, e=723000, res=1000)


    def read_member(archive, member):
        with tarfile.open(archive) as tar:
            return tar.extractfile(member).read().decode()
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(input="precipitation_monthly", output="precipitation.tar.bz2")
    with tarfile.open("precipitation.tar.bz2") as tar:
        names = tar.getnames()
    print("\n".join(names[:4]))
    print("\n".join(names[-5:]))
    print(len(names))
    ```

    ```text
    precipitation_monthly_2020_01.tif
    precipitation_monthly_2020_01.color
    precipitation_monthly_2020_02.tif
    precipitation_monthly_2020_02.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    29
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    list_txt = read_member("precipitation.tar.bz2", "list.txt")
    print("".join(list_txt.splitlines(True)[:3]), end="")
    print(read_member("precipitation.tar.bz2", "init.txt"), end="")
    ```

    ```text
    precipitation_monthly_2020_01|2020-01-01 00:00:00|2020-02-01 00:00:00|None
    precipitation_monthly_2020_02|2020-02-01 00:00:00|2020-03-01 00:00:00|None
    precipitation_monthly_2020_03|2020-03-01 00:00:00|2020-04-01 00:00:00|None
    stds_type=strds
    format=GTiff
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=12
    north=319000.0
    south=-16000.0
    east=963000.0
    west=124000.0
    ```

### Export the maps of a time window

**where** selects the maps of November and December, and **directory** names
the working directory `work`. The archive holds the files of two maps, and
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
    t.rast.export input=precipitation_monthly output=later.tar.bz2 directory=work \
        where="start_time >= '2020-11-01'"
    tar -tf later.tar.bz2
    tar -xOf later.tar.bz2 init.txt | grep number_of_maps
    ls -A work | wc -l
    ```

    ```text
    precipitation_monthly_2020_11.tif
    precipitation_monthly_2020_11.color
    precipitation_monthly_2020_12.tif
    precipitation_monthly_2020_12.color
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
        input="precipitation_monthly",
        output="later.tar.bz2",
        directory="work",
        where="start_time >= '2020-11-01'",
    )
    with tarfile.open("later.tar.bz2") as tar:
        print("\n".join(tar.getnames()))
    init = read_member("later.tar.bz2", "init.txt")
    print([line for line in init.splitlines() if "number_of_maps" in line][0])
    print(len(list(Path("work").iterdir())))
    ```

    ```text
    precipitation_monthly_2020_11.tif
    precipitation_monthly_2020_11.color
    precipitation_monthly_2020_12.tif
    precipitation_monthly_2020_12.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=2
    0
    ```

### Choose the compression

The loop exports the maps of the first quarter three times into the archive
`all.tar`, which **--overwrite** replaces each time. It prints the
compression, what the first two bytes of the file say about it and the number
of files in the archive. A gzip file starts with the bytes `1f8b` and a bzip2
file with `425a` (the letters `BZ`); a plain tar archive has neither. All three
hold the same 11 files, the two files of three maps and the five text files,
and `tar` reads them without being told the compression.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    for compression in no gzip bzip2; do
        t.rast.export input=precipitation_monthly output=all.tar \
            compression=$compression where="start_time < '2020-04-01'" --overwrite
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
    no: plain tar, 11 files
    gzip: gzip, 11 files
    bzip2: bzip2, 11 files
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:GTiff -->

    ```python
    for compression in ("no", "gzip", "bzip2"):
        tools.t_rast_export(
            input="precipitation_monthly",
            output="all.tar",
            compression=compression,
            where="start_time < '2020-04-01'",
            overwrite=True,
        )
        kinds = {"1f8b": "gzip", "425a": "bzip2"}
        kind = kinds.get(Path("all.tar").read_bytes()[:2].hex(), "plain tar")
        with tarfile.open("all.tar") as tar:
            print(f"{compression}: {kind}, {len(tar.getnames())} files")
    ```

    ```text
    no: plain tar, 11 files
    gzip: gzip, 11 files
    bzip2: bzip2, 11 files
    ```

### Set the data type and the nodata value

The three blocks export the map of November, whose cells hold up to 350 mm
over the whole of North Carolina and are NULL over the sea. Each block reads
the output of `gdalinfo -json` for the GeoTIFF file and prints its data type
and nodata value. The first block exports without options. The map has integer
cells, so the tool takes the largest value of the whole map plus one as the
nodata value, 351, and `UInt16` as the smallest type that holds 350 and 351; a
`Byte` holds only up to 255. The 8 by 4 cells of the region hold at most 132
mm, but the maximum of the whole map counts.

The second block adds `nodata=-77`. Neither `Byte` nor `UInt16` can hold -77,
so the tool takes `Int16`. The third block sets the type itself and passes a
creation option and a metadata tag to the GeoTIFF driver: the file is
compressed with `DEFLATE` and carries the tag `TAG=hello`; this block also
prints the compression and the tag.

=== "Command line"

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=precipitation_monthly output=november_default.tar \
        compression=no where="start_time >= '2020-11-01' and start_time < '2020-12-01'"
    tar -xf november_default.tar precipitation_monthly_2020_11.tif
    gdalinfo -json precipitation_monthly_2020_11.tif | python3 -c "import json, sys; i = json.load(sys.stdin); b = i['bands'][0]; print(b['type'], b['noDataValue'])"
    ```

    ```text
    UInt16 351
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=precipitation_monthly output=november_nodata.tar \
        compression=no where="start_time >= '2020-11-01' and start_time < '2020-12-01'" nodata=-77
    tar -xf november_nodata.tar precipitation_monthly_2020_11.tif
    gdalinfo -json precipitation_monthly_2020_11.tif | python3 -c "import json, sys; i = json.load(sys.stdin); b = i['bands'][0]; print(b['type'], b['noDataValue'])"
    ```

    ```text
    Int16 -77
    ```

    <!-- example: requires=gdal:GTiff -->

    ```sh
    t.rast.export input=precipitation_monthly output=november_options.tar \
        compression=no where="start_time >= '2020-11-01' and start_time < '2020-12-01'" \
        type=Int16 nodata=-77 createopt="COMPRESS=DEFLATE" metaopt="TAG=hello"
    tar -xf november_options.tar precipitation_monthly_2020_11.tif
    gdalinfo -json precipitation_monthly_2020_11.tif | python3 -c "import json, sys; i = json.load(sys.stdin); b = i['bands'][0]; print(b['type'], b['noDataValue'], i['metadata']['IMAGE_STRUCTURE']['COMPRESSION'], i['metadata']['']['TAG'])"
    ```

    ```text
    Int16 -77 DEFLATE hello
    ```

=== "Python (grass.tools)"

    ```python
    import json
    import subprocess


    def gdal_info(archive, member):
        with tarfile.open(archive) as tar:
            tar.extract(member, filter="data")
        result = subprocess.run(
            ["gdalinfo", "-json", member], capture_output=True, text=True, check=True
        )
        return json.loads(result.stdout)
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    november = "start_time >= '2020-11-01' and start_time < '2020-12-01'"
    tools.t_rast_export(
        input="precipitation_monthly",
        output="november_default.tar",
        compression="no",
        where=november,
    )
    info = gdal_info("november_default.tar", "precipitation_monthly_2020_11.tif")
    band = info["bands"][0]
    print(band["type"], band["noDataValue"])
    ```

    ```text
    UInt16 351
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(
        input="precipitation_monthly",
        output="november_nodata.tar",
        compression="no",
        where=november,
        nodata=-77,
    )
    info = gdal_info("november_nodata.tar", "precipitation_monthly_2020_11.tif")
    band = info["bands"][0]
    print(band["type"], band["noDataValue"])
    ```

    ```text
    Int16 -77
    ```

    <!-- example: requires=gdal:GTiff -->

    ```python
    tools.t_rast_export(
        input="precipitation_monthly",
        output="november_options.tar",
        compression="no",
        where=november,
        type="Int16",
        nodata=-77,
        createopt="COMPRESS=DEFLATE",
        metaopt="TAG=hello",
    )
    info = gdal_info("november_options.tar", "precipitation_monthly_2020_11.tif")
    band = info["bands"][0]
    metadata = info["metadata"]
    print(
        band["type"],
        band["noDataValue"],
        metadata["IMAGE_STRUCTURE"]["COMPRESSION"],
        metadata[""]["TAG"],
    )
    ```

    ```text
    Int16 -77 DEFLATE hello
    ```

### Export as an ASCII grid or in the GRASS pack format

With `format=AAIGrid`, the map of November is written as an Arc/Info ASCII Grid
file. `nodata=-77` is the value of the NULL cells in the header and in the
four rows of the file: the sea cells are -77, the land cells on the coast hold
132 mm.

With `format=pack`, the map is one `.pack` file and there is no `.color` file.
*r.pack* has no use for the options **type**, **nodata**, **createopt** and
**metaopt**, so the tool skips them with a warning.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    t.rast.export input=precipitation_monthly output=november_ascii.tar \
        compression=no where="start_time >= '2020-11-01' and start_time < '2020-12-01'" format=AAIGrid nodata=-77
    tar -tf november_ascii.tar
    tar -xOf november_ascii.tar precipitation_monthly_2020_11.asc
    ```

    ```text
    precipitation_monthly_2020_11.asc
    precipitation_monthly_2020_11.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ncols        8
    nrows        4
    xllcorner    715000.000000000000
    yllcorner    44000.000000000000
    cellsize     1000.000000000000
    NODATA_value -77
    132 132 132 -77 -77 -77 -77 -77 
    132 132 -77 -77 -77 -77 -77 -77 
    132 132 -77 -77 -77 -77 -77 -77 
    132 -77 -77 -77 -77 -77 -77 -77 
    ```

    ```sh
    t.rast.export input=precipitation_monthly output=november_pack.tar \
        compression=no where="start_time >= '2020-11-01' and start_time < '2020-12-01'" format=pack
    tar -tf november_pack.tar
    ```

    ```text
    precipitation_monthly_2020_11.pack
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
        input="precipitation_monthly",
        output="november_ascii.tar",
        compression="no",
        where=november,
        format="AAIGrid",
        nodata=-77,
    )
    with tarfile.open("november_ascii.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("november_ascii.tar", "precipitation_monthly_2020_11.asc"), end="")
    ```

    ```text
    precipitation_monthly_2020_11.asc
    precipitation_monthly_2020_11.color
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ncols        8
    nrows        4
    xllcorner    715000.000000000000
    yllcorner    44000.000000000000
    cellsize     1000.000000000000
    NODATA_value -77
    132 132 132 -77 -77 -77 -77 -77 
    132 132 -77 -77 -77 -77 -77 -77 
    132 132 -77 -77 -77 -77 -77 -77 
    132 -77 -77 -77 -77 -77 -77 -77 
    ```

    ```python
    tools.t_rast_export(
        input="precipitation_monthly",
        output="november_pack.tar",
        compression="no",
        where=november,
        format="pack",
    )
    with tarfile.open("november_pack.tar") as tar:
        print("\n".join(tar.getnames()))
    ```

    ```text
    precipitation_monthly_2020_11.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

### Export with a smaller region

GeoTIFF and ASCII grid files cover the current region, a `pack` file the
whole map. The first block narrows the region to the first four columns and
exports the map of November in all three formats. The GeoTIFF file is 4 by 4
cells (its `size` is `[4, 4]`), the ASCII grid has four columns, and the
packed map still has its 839 columns and 335 rows. `init.txt` still gives the
extent of the maps, east 963000 and west 124000. The last command resets the
region.

=== "Command line"

    <!-- example: requires=gdal:AAIGrid -->

    ```sh
    g.region n=48000 s=44000 w=715000 e=719000 res=1000
    t.rast.export input=precipitation_monthly output=cut_tif.tar compression=no \
        where="start_time >= '2020-11-01' and start_time < '2020-12-01'"
    t.rast.export input=precipitation_monthly output=cut_asc.tar compression=no \
        where="start_time >= '2020-11-01' and start_time < '2020-12-01'" format=AAIGrid
    t.rast.export input=precipitation_monthly output=cut_pack.tar compression=no \
        where="start_time >= '2020-11-01' and start_time < '2020-12-01'" format=pack
    tar -xf cut_tif.tar precipitation_monthly_2020_11.tif
    gdalinfo -json precipitation_monthly_2020_11.tif | python3 -c "import json, sys; i = json.load(sys.stdin); b = i['bands'][0]; print(i['size'], b['type'], b['noDataValue'])"
    tar -xOf cut_asc.tar precipitation_monthly_2020_11.asc | sed -n 1,2p
    tar -xOf cut_pack.tar precipitation_monthly_2020_11.pack | tar -xOf - precipitation_monthly_2020_11/cellhd | grep -E "^(cols|rows)"
    tar -xOf cut_tif.tar init.txt | grep -E "^(east|west)="
    g.region n=48000 s=44000 w=715000 e=723000 res=1000
    ```

    ```text
    [4, 4] UInt16 351
    ncols        4
    nrows        4
    cols:       839
    rows:       335
    east=963000.0
    west=124000.0
    ```

=== "Python (grass.tools)"

    <!-- example: requires=gdal:AAIGrid -->

    ```python
    tools.g_region(n=48000, s=44000, w=715000, e=719000, res=1000)
    for output, file_format in (
        ("cut_tif.tar", "GTiff"),
        ("cut_asc.tar", "AAIGrid"),
        ("cut_pack.tar", "pack"),
    ):
        tools.t_rast_export(
            input="precipitation_monthly",
            output=output,
            compression="no",
            where=november,
            format=file_format,
        )
    info = gdal_info("cut_tif.tar", "precipitation_monthly_2020_11.tif")
    band = info["bands"][0]
    print(info["size"], band["type"], band["noDataValue"])
    ascii_grid = read_member("cut_asc.tar", "precipitation_monthly_2020_11.asc")
    print("".join(ascii_grid.splitlines(True)[:2]), end="")
    with tarfile.open("cut_pack.tar") as outer:
        with tarfile.open(
            fileobj=outer.extractfile("precipitation_monthly_2020_11.pack"), mode="r:"
        ) as inner:
            header = inner.extractfile("precipitation_monthly_2020_11/cellhd").read()
    header = header.decode()
    print("\n".join(line for line in header.splitlines() if line[:4] in ("cols", "rows")))
    init = read_member("cut_tif.tar", "init.txt")
    print("\n".join(line for line in init.splitlines() if line[:4] in ("east", "west")))
    tools.g_region(n=48000, s=44000, w=715000, e=723000, res=1000)
    ```

    ```text
    [4, 4] UInt16 351
    ncols        4
    nrows        4
    cols:       839
    rows:       335
    east=963000.0
    west=124000.0
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
