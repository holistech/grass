## DESCRIPTION

*t.rast.import* imports a space time raster dataset archive that was
exported with [t.rast.export](t.rast.export.md).

## NOTES

Optionally a base map name can be provided to avoid that existing raster
maps are overwritten by the map names that are used in the STRDS
archive.

A map that the archive names `name@mapset`, which
*[t.rast.export](t.rast.export.md)* writes for maps of one name from several
mapsets, is imported as `name_mapset`; every character of the mapset other
than a letter, a digit or `_` becomes `_`, so `dup@my.set` is imported as
`dup_my_set`. If two maps of the archive would get one name this way, for
example `dup@other` and a map `dup_other`, the import stops before the first
map is imported; with **basename** the maps are numbered instead.
An archive that lists a map more than once, as older exports wrote it for
maps of one name from several mapsets, is refused before the first map is
imported; a new export of the dataset names the maps with their mapset.

The **directory** is used as work directory in case of import but can
also be used as a data directory when using GeoTIFF for the data
exchange.

With the **project** option an archive of an unprojected project (the
coordinate system "XY") creates an unprojected project; the maps are
imported without a coordinate system check, as the GeoTIFF files hold none.

Blank lines in "list.txt" and "init.txt" are skipped, so an archive edited
by hand may contain them. A line of "init.txt" without an equals sign stops
the import with an error; a value is everything after the first equals
sign.

## EXAMPLE

The North Carolina space time dataset contains a data package called
*lst_daily.tar.bzip2* with daily data from MODIS LST. Import it by
running:

```sh
t.rast.import input=lst_daily.tar.bzip2 output=lst_daily \
              basename=lst directory=/tmp
```

## SEE ALSO

*[t.rast.export](t.rast.export.md), [t.create](t.create.md),
[t.info](t.info.md), [r.in.gdal](r.in.gdal.md), [r.unpack](r.unpack.md),
[t.vect.import](t.vect.import.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
