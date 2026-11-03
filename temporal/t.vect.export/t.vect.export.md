## DESCRIPTION

*t.vect.export* writes the maps of a space time vector dataset and a
description of their times into one tar archive. The archive moves a dataset
to another project or computer: *[t.vect.import](t.vect.import.md)* reads it
back and registers the maps in a new dataset. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool for space time raster datasets is
*[t.rast.export](t.rast.export.md)*.

The option **input** names the space time vector dataset, and **output** the
archive that is written. The tool uses the name of **output** as it is and adds
no suffix, so the name should say what the archive is, such as
`discharge.tar.bz2`. An existing archive is refused unless the flag
**--overwrite** is given.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2026-03-02'`, and exports only the maps it
selects. Without **where**, all maps are exported. The maps are written in the
order of their start time. A selection without a map is not an error (see the
notes).

### Export format

The option **format** chooses how each vector map is stored in the archive:

- `GML`, the default, writes the files `name.xml` and `name.xsd` with
  *[v.out.ogr](v.out.ogr.md)*;
- `GPKG` writes a GeoPackage file `name.gpkg` with *v.out.ogr*;
- `pack` writes the file `name.pack` with *[v.pack](v.pack.md)*, the GRASS
  format that *v.unpack* reads. The `.pack` file is a tar archive of its own
  that is not compressed again.

*v.out.ogr* writes one layer per file, *v.pack* all layers of a map (see the
notes).

### Archive and compression

The option **compression** compresses the archive: `bzip2` (the default),
`gzip`, or `no` for a plain tar archive. A tool such as `tar -tf` or the Python
module `tarfile` recognises the compression by itself.

The option **directory** names the working directory, by default `/tmp`.
*t.vect.export* exports the maps into a temporary subdirectory of it, packs
them there, moves the archive to the path given by **output** and removes the
subdirectory. The archive is therefore not written to **directory**, and a
relative **output** is taken from the current directory.

### Files in the archive

The archive holds the files of the maps, in the order of their start time, and
then five text files:

- `list.txt` has one line for each map, with the fields name, start time and
  end time, separated by `|`. The start and end time are in ISO format with
  absolute time and numbers with relative time. A map that is a time instance
  has the end time of its start time. In the pack format the name is
  `name:layer`, with one line for each registered layer of a vector map;
- `proj.txt` is the output of *[g.proj](g.proj.md)* with `-p format=proj4`,
  the coordinate reference system of the project;
- `init.txt` has one `key=value` line for each of the following: `stds_type`,
  `format`, `temporal_type`, `semantic_type`, `relative_time_unit` (relative
  time only), `number_of_maps` and the extent `north`, `south`, `east`, `west`.
  `number_of_maps` counts the exported maps, and the extent is that of the
  exported maps, not of the region. A selection without a map (see the notes)
  writes the extent of the whole dataset instead;
- `readme.txt` describes the files of the archive;
- `metadata.txt` is the output of *[t.info](t.info.md)* for the dataset.

## NOTES

The export reads the maps from the mapsets they were registered from, also
if a map of the same name exists in the current mapset. The maps of a dataset
may come from several mapsets. If maps of one name from different mapsets are
exported together, each of them is named `name@mapset` in the archive, in its
file names and in `list.txt`, where the pack format writes `name:layer@mapset`.
A map whose name no other mapset of the selection shares keeps its name, so an
archive without such maps has the form of older versions. The last example
shows this. *[t.vect.import](t.vect.import.md)* imports `dup@t_vect_export_2` as
`dup_t_vect_export_2`.

The GML and GPKG formats hold one layer per map. A selection that contains
several layers of one vector map is refused before anything is written; use
`format=pack` for such a map, or select one layer with **where**. The same
holds for a map that the selection names several times with the same layer,
for example registered as `name` and as `name:1`; select it once with
**where**. The fifth example shows the refusal.

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
because it was removed, stops the tool with "Unable to export vector map
`<name@mapset>` as GML with v.out.ogr" (`GPKG` for the format GPKG; the pack
format ends the message with "with v.pack" instead); no archive is left, and
the temporary subdirectory is removed in every case.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_vect_export` and sets the computational region
to North Carolina with cells of 1 km; the later examples work in this mapset
and region. The last example adds a second mapset, `t_vect_export_2`.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_vect_export -->

<!-- markdownlint-disable MD046 -->

### Export a dataset as a GML archive

The dataset `discharge` has three maps of an assumed discharge at two of the
five gauges of Crabtree Creek in Raleigh, which *[v.extract](v.extract.md)*
copies from `usgsgages` (the gauges with the categories 149 and 153). The
values are generated, not measured: the gauge 149 has the discharge 1, 2 and 3
cubic meters per second on the days from 1 to 3 March 2026, the gauge 153 the
discharge 3, 4 and 5 cubic meters per second. The maps are time instances,
since **-i** is not given to *t.register*.

The first block creates the dataset. The second exports it with the default
format and compression: the files `name.xml` and `name.xsd` of each map, packed
into a bzip2 compressed archive. `tar -tf` lists the files. The maps come first
in the order of their start time, then the five text files. The third block
shows what `list.txt` and `init.txt` say about the dataset: a time instance has
its start time as end time, and the extent in `init.txt` is that of the two
gauges. The last block reads the discharge of the first map from its GML file.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_vect_export
    g.region raster=elev_state_500m res=1000 -a
    for k in 1 2 3; do
        map=discharge_2026_03_0$k
        v.extract input=usgsgages output=$map where="cat IN (149, 153)"
        v.db.addcolumn map=$map columns="discharge double precision"
        v.db.update map=$map column=discharge value=$k where="cat = 149"
        v.db.update map=$map column=discharge value=$((k + 2)) where="cat = 153"
    done
    t.create type=stvds output=discharge title="Discharge" \
        description="Assumed discharge in m3/s at two gauges"
    t.register type=vector input=discharge \
        maps=discharge_2026_03_01,discharge_2026_03_02,discharge_2026_03_03 \
        start=2026-03-01 increment="1 day"
    ```

    ```sh
    t.vect.export input=discharge output=discharge.tar.bz2
    tar -tf discharge.tar.bz2
    ```

    ```text
    discharge_2026_03_01.xml
    discharge_2026_03_01.xsd
    discharge_2026_03_02.xml
    discharge_2026_03_02.xsd
    discharge_2026_03_03.xml
    discharge_2026_03_03.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

    ```sh
    tar -xOf discharge.tar.bz2 list.txt
    tar -xOf discharge.tar.bz2 init.txt
    ```

    ```text
    discharge_2026_03_01|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03|2026-03-03 00:00:00|2026-03-03 00:00:00
    stds_type=stvds
    format=GML
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=3
    north=232516.08607477113
    south=228759.85307477112
    east=644719.42889786
    west=634516.9978978601
    ```

    ```sh
    tar -xOf discharge.tar.bz2 discharge_2026_03_01.xml | grep -o "<ogr:discharge>[^<]*"
    ```

    ```text
    <ogr:discharge>1
    <ogr:discharge>3
    ```

=== "Python (grass.tools)"

    ```python
    import re
    import tarfile

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_vect_export")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for k in (1, 2, 3):
        map_name = f"discharge_2026_03_0{k}"
        tools.v_extract(input="usgsgages", output=map_name, where="cat IN (149, 153)")
        tools.v_db_addcolumn(map=map_name, columns="discharge double precision")
        tools.v_db_update(map=map_name, column="discharge", value=k, where="cat = 149")
        tools.v_db_update(map=map_name, column="discharge", value=k + 2, where="cat = 153")
    tools.t_create(
        type="stvds",
        output="discharge",
        title="Discharge",
        description="Assumed discharge in m3/s at two gauges",
    )
    tools.t_register(
        type="vector",
        input="discharge",
        maps="discharge_2026_03_01,discharge_2026_03_02,discharge_2026_03_03",
        start="2026-03-01",
        increment="1 day",
    )


    def read_member(archive, member):
        with tarfile.open(archive) as tar:
            return tar.extractfile(member).read().decode()
    ```

    ```python
    tools.t_vect_export(input="discharge", output="discharge.tar.bz2")
    with tarfile.open("discharge.tar.bz2") as tar:
        print("\n".join(tar.getnames()))
    ```

    ```text
    discharge_2026_03_01.xml
    discharge_2026_03_01.xsd
    discharge_2026_03_02.xml
    discharge_2026_03_02.xsd
    discharge_2026_03_03.xml
    discharge_2026_03_03.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    ```

    ```python
    for member in ("list.txt", "init.txt"):
        print(read_member("discharge.tar.bz2", member), end="")
    ```

    ```text
    discharge_2026_03_01|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03|2026-03-03 00:00:00|2026-03-03 00:00:00
    stds_type=stvds
    format=GML
    temporal_type=absolute
    semantic_type=mean
    number_of_maps=3
    north=232516.08607477113
    south=228759.85307477112
    east=644719.42889786
    west=634516.9978978601
    ```

    ```python
    gml = read_member("discharge.tar.bz2", "discharge_2026_03_01.xml")
    print("\n".join(re.findall("<ogr:discharge>[^<]*", gml)))
    ```

    ```text
    <ogr:discharge>1
    <ogr:discharge>3
    ```

### Choose the export format

The first block exports `discharge` in the pack format: one `.pack` file for
each map. `list.txt` names the maps `name:layer`, here with the layer 1 that
*v.extract* kept, and `init.txt` names the format. The second block exports the
GeoPackage format with **compression=gzip**, which writes one `.gpkg` file for
each map and a `list.txt` with plain map names.

=== "Command line"

    ```sh
    t.vect.export input=discharge output=discharge_pack.tar format=pack compression=no
    tar -tf discharge_pack.tar
    tar -xOf discharge_pack.tar list.txt
    tar -xOf discharge_pack.tar init.txt | grep format
    ```

    ```text
    discharge_2026_03_01.pack
    discharge_2026_03_02.pack
    discharge_2026_03_03.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    discharge_2026_03_01:1|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02:1|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03:1|2026-03-03 00:00:00|2026-03-03 00:00:00
    format=pack
    ```

    <!-- example: requires=gdal:GPKG -->

    ```sh
    t.vect.export input=discharge output=discharge_gpkg.tar.gz format=GPKG compression=gzip
    tar -tf discharge_gpkg.tar.gz
    tar -xOf discharge_gpkg.tar.gz list.txt
    tar -xOf discharge_gpkg.tar.gz init.txt | grep format
    ```

    ```text
    discharge_2026_03_01.gpkg
    discharge_2026_03_02.gpkg
    discharge_2026_03_03.gpkg
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    discharge_2026_03_01|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03|2026-03-03 00:00:00|2026-03-03 00:00:00
    format=GPKG
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_vect_export(
        input="discharge", output="discharge_pack.tar", format="pack", compression="no"
    )
    with tarfile.open("discharge_pack.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("discharge_pack.tar", "list.txt"), end="")
    init = read_member("discharge_pack.tar", "init.txt")
    print("\n".join(line for line in init.splitlines() if line.startswith("format")))
    ```

    ```text
    discharge_2026_03_01.pack
    discharge_2026_03_02.pack
    discharge_2026_03_03.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    discharge_2026_03_01:1|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02:1|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03:1|2026-03-03 00:00:00|2026-03-03 00:00:00
    format=pack
    ```

    <!-- example: requires=gdal:GPKG -->

    ```python
    tools.t_vect_export(
        input="discharge",
        output="discharge_gpkg.tar.gz",
        format="GPKG",
        compression="gzip",
    )
    with tarfile.open("discharge_gpkg.tar.gz") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("discharge_gpkg.tar.gz", "list.txt"), end="")
    init = read_member("discharge_gpkg.tar.gz", "init.txt")
    print("\n".join(line for line in init.splitlines() if line.startswith("format")))
    ```

    ```text
    discharge_2026_03_01.gpkg
    discharge_2026_03_02.gpkg
    discharge_2026_03_03.gpkg
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    discharge_2026_03_01|2026-03-01 00:00:00|2026-03-01 00:00:00
    discharge_2026_03_02|2026-03-02 00:00:00|2026-03-02 00:00:00
    discharge_2026_03_03|2026-03-03 00:00:00|2026-03-03 00:00:00
    format=GPKG
    ```

### Choose the compression

Each block exports `discharge` with one value of **compression** and prints the
first two bytes of the archive as hexadecimal numbers: `1f8b` for gzip and
`425a` ("BZ") for bzip2. A plain tar archive has no such mark; its first bytes
are the start of the first file name, `2e2f` for the characters "./". `tar -tf`
and `tarfile` read all three the same way.

=== "Command line"

    ```sh
    for method in no gzip bzip2; do
        t.vect.export input=discharge output=discharge_$method.tar compression=$method
        od -An -tx1 -N2 discharge_$method.tar | tr -d ' '
        tar -tf discharge_$method.tar | sed -n 1p
    done
    ```

    ```text
    2e2f
    discharge_2026_03_01.xml
    1f8b
    discharge_2026_03_01.xml
    425a
    discharge_2026_03_01.xml
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    for method in ("no", "gzip", "bzip2"):
        archive = f"discharge_{method}.tar"
        tools.t_vect_export(input="discharge", output=archive, compression=method)
        print(Path(archive).read_bytes()[:2].hex())
        with tarfile.open(archive) as tar:
            print(tar.getnames()[0])
    ```

    ```text
    2e2f
    discharge_2026_03_01.xml
    1f8b
    discharge_2026_03_01.xml
    425a
    discharge_2026_03_01.xml
    ```

### Export the maps of a time window

**where** selects the maps of 2 and 3 March, and **directory** names the
working directory `work`. The archive holds the files of two maps, and
`number_of_maps` in `init.txt` counts two. The tool exports and packs in a
temporary subdirectory of `work` and removes it, so the last command finds
`work` empty: the archive is in the current directory, where **output** puts
it.

A condition that selects no map still writes an archive. The second block asks
for the maps after 2030: the tool warns "The selection contains no map" and the
archive holds only the five text files, with `number_of_maps=0`.

=== "Command line"

    ```sh
    mkdir work
    t.vect.export input=discharge output=later.tar compression=no \
        where="start_time >= '2026-03-02'" directory=work
    tar -tf later.tar
    tar -xOf later.tar init.txt | grep number_of_maps
    ls work
    ```

    ```text
    discharge_2026_03_02.xml
    discharge_2026_03_02.xsd
    discharge_2026_03_03.xml
    discharge_2026_03_03.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=2
    ```

    ```sh
    t.vect.export input=discharge output=none.tar compression=no \
        where="start_time > '2030-01-01'" 2>&1
    tar -tf none.tar
    tar -xOf none.tar init.txt | grep number_of_maps
    ```

    ```text
    WARNING: The selection contains no map of <discharge>; the archive holds no
             map.
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=0
    ```

=== "Python (grass.tools)"

    ```python
    Path("work").mkdir()
    tools.t_vect_export(
        input="discharge",
        output="later.tar",
        compression="no",
        where="start_time >= '2026-03-02'",
        directory="work",
    )
    with tarfile.open("later.tar") as tar:
        print("\n".join(tar.getnames()))
    init = read_member("later.tar", "init.txt")
    print("\n".join(line for line in init.splitlines() if "number_of_maps" in line))
    print(list(Path("work").iterdir()))
    ```

    ```text
    discharge_2026_03_02.xml
    discharge_2026_03_02.xsd
    discharge_2026_03_03.xml
    discharge_2026_03_03.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=2
    []
    ```

    ```python
    warning_tools = Tools(capture_stderr=True, consistent_return_value=True)
    result = warning_tools.t_vect_export(
        input="discharge",
        output="none.tar",
        compression="no",
        where="start_time > '2030-01-01'",
    )
    print(result.stderr.strip())
    with tarfile.open("none.tar") as tar:
        print("\n".join(tar.getnames()))
    init = read_member("none.tar", "init.txt")
    print("\n".join(line for line in init.splitlines() if "number_of_maps" in line))
    ```

    ```text
    WARNING: The selection contains no map of <discharge>; the archive holds no
             map.
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    number_of_maps=0
    ```

### A map with several layers

The map `gauge` has the two gauges 149 and 153 as points, and *v.category*
gives them a category in layer 2 as well as in layer 1. The dataset `gauges`
registers the layers as the maps `gauge:1` and `gauge:2`, in March and April
2026. *t.vect.list* shows the two registered maps.

The GML and GPKG formats hold one layer per map, so the first export is refused
before anything is written: no archive exists afterwards. The pack format holds
all layers; the map is packed once and `list.txt` has a line for each layer.
The last block selects layer 2 with **where** and exports it as GML.

=== "Command line"

    ```sh
    v.extract input=usgsgages output=gauge_one where="cat IN (149, 153)"
    v.category input=gauge_one output=gauge option=add layer=2 type=point
    t.create type=stvds output=gauges title="Gauges" \
        description="Gauges in two layers"
    t.register type=vector input=gauges maps=gauge:1,gauge:2 \
        start=2026-03-01 increment="1 month"
    t.vect.list input=gauges columns=name,layer,start_time
    ```

    ```text
    name|layer|start_time
    gauge|1|2026-03-01 00:00:00
    gauge|2|2026-04-01 00:00:00
    ```

    ```sh
    if ! t.vect.export input=gauges output=gauges.tar compression=no 2>&1; then
        echo "t.vect.export failed"
    fi
    ls gauges.tar || echo "no archive"
    ```

    ```text
    ERROR: Vector map <gauge> is selected with the layers 1, 2; the GML format
    holds one layer per map, use format=pack
    t.vect.export failed
    no archive
    ```

    ```sh
    t.vect.export input=gauges output=gauges_pack.tar compression=no format=pack
    tar -tf gauges_pack.tar
    tar -xOf gauges_pack.tar list.txt
    ```

    ```text
    gauge.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    gauge:1|2026-03-01 00:00:00|2026-03-01 00:00:00
    gauge:2|2026-04-01 00:00:00|2026-04-01 00:00:00
    ```

    ```sh
    t.vect.export input=gauges output=gauges_two.tar compression=no \
        where="layer = 2"
    tar -tf gauges_two.tar
    tar -xOf gauges_two.tar list.txt
    ```

    ```text
    gauge.xml
    gauge.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    gauge|2026-04-01 00:00:00|2026-04-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    tools.v_extract(input="usgsgages", output="gauge_one", where="cat IN (149, 153)")
    tools.v_category(input="gauge_one", output="gauge", option="add", layer=2, type="point")
    tools.t_create(
        type="stvds", output="gauges", title="Gauges", description="Gauges in two layers"
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauge:1,gauge:2",
        start="2026-03-01",
        increment="1 month",
    )
    print(tools.t_vect_list(input="gauges", columns="name,layer,start_time").text)
    ```

    ```text
    name|layer|start_time
    gauge|1|2026-03-01 00:00:00
    gauge|2|2026-04-01 00:00:00
    ```

    ```python
    try:
        tools.t_vect_export(input="gauges", output="gauges.tar", compression="no")
    except ToolError as error:
        print(error.stderr.strip())
        print("t.vect.export failed")
    print(Path("gauges.tar").exists())
    ```

    ```text
    ERROR: Vector map <gauge> is selected with the layers 1, 2; the GML format
    holds one layer per map, use format=pack
    t.vect.export failed
    False
    ```

    ```python
    tools.t_vect_export(
        input="gauges", output="gauges_pack.tar", compression="no", format="pack"
    )
    with tarfile.open("gauges_pack.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("gauges_pack.tar", "list.txt"), end="")
    ```

    ```text
    gauge.pack
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    gauge:1|2026-03-01 00:00:00|2026-03-01 00:00:00
    gauge:2|2026-04-01 00:00:00|2026-04-01 00:00:00
    ```

    ```python
    tools.t_vect_export(
        input="gauges", output="gauges_two.tar", compression="no", where="layer = 2"
    )
    with tarfile.open("gauges_two.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("gauges_two.tar", "list.txt"), end="")
    ```

    ```text
    gauge.xml
    gauge.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    gauge|2026-04-01 00:00:00|2026-04-01 00:00:00
    ```

### Maps of the same name from several mapsets

The map `dup` exists in the mapsets `t_vect_export` and `t_vect_export_2`, with
one gauge each (the categories 149 and 153), and `t_vect_export_2` also holds
the map `solo` (the gauge 151). The first block creates the second mapset, sets
the region there again and returns to `t_vect_export`. The dataset `pair`
registers `dup@t_vect_export` for 1 March and `dup@t_vect_export_2` and
`solo@t_vect_export_2` for 2 March; the block adds `t_vect_export_2` to the
search path with *g.mapsets* first.
The archive names the two maps of the name `dup` with their mapsets, in the file
names and in `list.txt`; `solo` keeps its name, since no other mapset of the
selection has a map of that name. In the pack format `list.txt` writes
`name:layer@mapset`.

=== "Command line"

    ```sh
    v.extract input=usgsgages output=dup where="cat = 149"
    g.mapset -c mapset=t_vect_export_2
    g.region raster=elev_state_500m res=1000 -a
    v.extract input=usgsgages output=dup where="cat = 153"
    v.extract input=usgsgages output=solo where="cat = 151"
    g.mapset mapset=t_vect_export
    g.mapsets mapset=t_vect_export_2 operation=add
    t.create type=stvds output=pair title="Pair" description="Same name twice"
    t.register type=vector input=pair maps=dup@t_vect_export \
        start=2026-03-01 end=2026-03-02
    t.register type=vector input=pair maps=dup@t_vect_export_2,solo@t_vect_export_2 \
        start=2026-03-02 end=2026-03-03
    t.vect.list input=pair columns=name,mapset,start_time
    ```

    ```text
    name|mapset|start_time
    dup|t_vect_export|2026-03-01 00:00:00
    dup|t_vect_export_2|2026-03-02 00:00:00
    solo|t_vect_export_2|2026-03-02 00:00:00
    ```

    ```sh
    t.vect.export input=pair output=pair.tar compression=no
    tar -tf pair.tar
    tar -xOf pair.tar list.txt
    ```

    ```text
    dup@t_vect_export.xml
    dup@t_vect_export.xsd
    dup@t_vect_export_2.xml
    dup@t_vect_export_2.xsd
    solo.xml
    solo.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    dup@t_vect_export|2026-03-01 00:00:00|2026-03-02 00:00:00
    dup@t_vect_export_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    solo|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```sh
    t.vect.export input=pair output=pair_pack.tar compression=no format=pack
    tar -xOf pair_pack.tar list.txt
    ```

    ```text
    dup:1@t_vect_export|2026-03-01 00:00:00|2026-03-02 00:00:00
    dup:1@t_vect_export_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    solo:1|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.v_extract(input="usgsgages", output="dup", where="cat = 149")
    tools.g_mapset(mapset="t_vect_export_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.v_extract(input="usgsgages", output="dup", where="cat = 153")
    tools.v_extract(input="usgsgages", output="solo", where="cat = 151")
    tools.g_mapset(mapset="t_vect_export")
    tools.g_mapsets(mapset="t_vect_export_2", operation="add")
    tools.t_create(type="stvds", output="pair", title="Pair", description="Same name twice")
    tools.t_register(
        type="vector",
        input="pair",
        maps="dup@t_vect_export",
        start="2026-03-01",
        end="2026-03-02",
    )
    tools.t_register(
        type="vector",
        input="pair",
        maps="dup@t_vect_export_2,solo@t_vect_export_2",
        start="2026-03-02",
        end="2026-03-03",
    )
    print(tools.t_vect_list(input="pair", columns="name,mapset,start_time").text)
    ```

    ```text
    name|mapset|start_time
    dup|t_vect_export|2026-03-01 00:00:00
    dup|t_vect_export_2|2026-03-02 00:00:00
    solo|t_vect_export_2|2026-03-02 00:00:00
    ```

    ```python
    tools.t_vect_export(input="pair", output="pair.tar", compression="no")
    with tarfile.open("pair.tar") as tar:
        print("\n".join(tar.getnames()))
    print(read_member("pair.tar", "list.txt"), end="")
    ```

    ```text
    dup@t_vect_export.xml
    dup@t_vect_export.xsd
    dup@t_vect_export_2.xml
    dup@t_vect_export_2.xsd
    solo.xml
    solo.xsd
    list.txt
    proj.txt
    init.txt
    readme.txt
    metadata.txt
    dup@t_vect_export|2026-03-01 00:00:00|2026-03-02 00:00:00
    dup@t_vect_export_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    solo|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

    ```python
    tools.t_vect_export(
        input="pair", output="pair_pack.tar", compression="no", format="pack"
    )
    print(read_member("pair_pack.tar", "list.txt"), end="")
    ```

    ```text
    dup:1@t_vect_export|2026-03-01 00:00:00|2026-03-02 00:00:00
    dup:1@t_vect_export_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    solo:1|2026-03-02 00:00:00|2026-03-03 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.proj](g.proj.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.export](t.rast.export.md), [t.vect.import](t.vect.import.md),
[v.extract](v.extract.md), [v.out.ogr](v.out.ogr.md), [v.pack](v.pack.md),
[v.unpack](v.unpack.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
