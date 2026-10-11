## DESCRIPTION

*t.rast3d.algebra* performs temporal and spatial map algebra operations
on space time 3D raster datasets (STR3DS) by using the temporal 3D
raster algebra.

### NOTES

The module expects an **expression** as input parameter in the following
form:

`"result = expression"`

The statement structure is exact the same as of *t.rast.algebra*, see
[t.rast.algebra](t.rast.algebra.md) but allows four-dimensional
indexing: a neighbourhood modifier with four offsets is written
str3ds\[row,column,depth,time\].

By default, only temporal topological relations are evaluated.
The **-s** flag additionally activates the evaluation of the spatial
topology of the maps. It applies wherever the algebra evaluates the
topology of maps: in selections, in the hash operator, in the conditions
of if statements, in comparison operators and in the spatial operators.
Two temporally related maps are then only used together if they are also
spatially related, that is the spatial extents of the maps are
equivalent, one covers or is covered by the other, they overlap, one
lies in the other, one contains the other, or they meet (the spatial
relations *equivalent*, *cover*, *covered*, *overlap*, *in*, *contain*
and *meet*). The relations *equivalent*, *cover*, *overlap*, *in*,
*contain* and *meet* can also be named in the curly brackets of a
spatial operator, for example `{+,equal|overlap}`; the maps then need
this spatial relation in addition to the temporal one. The relation is
evaluated in three dimensions: two maps with the same depth range are not
related as *overlap*, even if they overlap in the horizontal plane.

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

## SEE ALSO

*[t.rast.algebra](t.rast.algebra.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [r.mapcalc](r.mapcalc.md),
[t.vect.algebra](t.vect.algebra.md), [t.select](t.select.md)*

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
