## DESCRIPTION

*t.rast3d.extract* is used to extract a subset of a space time 3D raster
dataset and to store that subset in a different space time 3D raster
dataset. It has exactly the same functionality as
[t.rast.extract](t.rast.extract.md). The only difference is the that
this module works on STR3DS and 3D raster maps.

Please refer to [t.rast.extract](t.rast.extract.md) for documentation
and examples.

Two different maps of one time (for example two maps of January 2001)
get the same name from the **suffix**. The first of them, in the order of
start time and map id, keeps the name; the second and every further map get
the number `_2`, `_3` and so on after it. A number that another new map has
as its name is skipped.

## SEE ALSO

*[t.rast.extract](t.rast.extract.md), [t.create](t.create.md),
[t.info](t.info.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
