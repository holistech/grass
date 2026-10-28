## DESCRIPTION

*t.vect.import* imports a space time vector dataset archive that was
exported with [t.vect.export](t.vect.export.md). The archive may hold the
maps as GRASS pack files, as GML or as GeoPackage (GPKG) files; the maps of
the last two are imported with *[v.in.ogr](v.in.ogr.md)*.

## NOTES

Optionally a base map name can be provided to avoid that existing vector
maps are overwritten by the map names that are used in the STRDS
archive.
With a base name, the layers of one vector map share the new name and
stay in one map.

A map that the archive names `name@mapset`, which
*[t.vect.export](t.vect.export.md)* writes for maps of one name from several
mapsets, is imported as `name_mapset`; every character of the mapset other
than a letter, a digit or `_` becomes `_`, so `dup@my.set` is imported as
`dup_my_set`. If two maps of the archive would get one name this way, for
example `dup@other` and a map `dup_other`, the import stops before the first
map is imported; with **basename** the maps are numbered instead.
An archive that lists a map more than once, as older exports wrote it for
maps of one name from several mapsets, is refused before the first map is
imported; a new export of the dataset names the maps with their mapset.

The **directory** is used as work directory in case of import but can
also be used as a data directory when using GML for the data exchange.

With the **-e** flag the region is extended to the extent of the imported
maps, for GML and GPKG archives by *[v.in.ogr](v.in.ogr.md)* and for pack
archives by the module itself after *[v.unpack](v.unpack.md)*.

Blank lines in "list.txt" and "init.txt" are skipped, so an archive edited
by hand may contain them. A line of "init.txt" without an equals sign stops
the import with an error; a value is everything after the first equals
sign.

## EXAMPLE

In this example, five vector maps are created and registered in a single
space time vector dataset named *random_locations*. Each vector map
represents random locations within the boundary of the state taken at 1
month intervals. The space time dataset is then exported and
re-imported.

```sh
db.connect -d

for i in `seq 1 5` ; do
    v.random output=map_$i n=500 restrict=boundary_state@PERMANENT
    echo map_$i >> map_list.txt
done

t.create type=stvds temporaltype=absolute \
         output=random_locations \
         title="Random locations" \
         description="Vector test dataset with random locations"

t.register -i type=vector input=random_locations \
           file=map_list.txt start="2012-01-01" increment="1 months"

t.vect.list random_locations

t.vect.export input=random_locations output=random_locations.tar.gz \
              compression=gzip

t.vect.import input=random_locations.tar.gz output=new_random_locations \
              basename=new_map directory=/tmp

t.vect.list new_random_locations
id|name|layer|mapset|start_time|end_time
new_map_1@user1|new_map_1|None|user1|2012-01-01 00:00:00|2012-02-01 00:00:00
new_map_2@user1|new_map_2|None|user1|2012-02-01 00:00:00|2012-03-01 00:00:00
new_map_3@user1|new_map_3|None|user1|2012-03-01 00:00:00|2012-04-01 00:00:00
new_map_4@user1|new_map_4|None|user1|2012-04-01 00:00:00|2012-05-01 00:00:00
new_map_5@user1|new_map_5|None|user1|2012-05-01 00:00:00|2012-06-01 00:00:00
```

## SEE ALSO

*[t.vect.export](t.vect.export.md), [t.create](t.create.md),
[t.info](t.info.md), [v.in.ogr](v.in.ogr.md), [v.pack](v.pack.md),
[t.rast.import](t.rast.import.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
