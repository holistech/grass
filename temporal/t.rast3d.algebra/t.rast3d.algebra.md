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

*t.rast3d.algebra* computes with the classic algebra, which the section
"Core and classic algebra" in the NOTES of
[t.rast.algebra](t.rast.algebra.md) describes. The rules given there for
the new algebra do not apply to it yet: for example, conditions on
temporal variables are evaluated from left to right, and `if` without else
gives 0 where a condition on map values is false.

Since GRASS 8.6, two corrections of the temporal algebra apply to
*t.rast3d.algebra* as to *t.rast.algebra*, *t.select* and
*t.vect.algebra*. First, `if({R}, condition, conclusion)` reads
"condition R conclusion": `if({contains}, start_doy(A) > 0, B)` gives the
maps of B that lie within a map of A, where earlier versions gave the maps
of B that contain a map of A. Second, with a temporal relation beyond
`equal`, the else part of a condition on temporal variables also takes the
maps that no condition map is related to. Figure A3 of Gebbert, Leppelt
and Pebesma (2019) needs both: A has maps from day 1 to 3, 3 to 5 and 5
to 7 of January 2001, B has daily maps from day 1 to 10, and this
expression gives the first two maps of A and the maps of B from day 5 on,
as the figure shows:

```sh
C = if({equal|contains}, start_date(A) <= "2001-01-03", A, B)
```

Results that rely on the previous reading direction or else rule need the
GRASS version they were computed with. The section "Core and classic
algebra" in the NOTES of [t.rast.algebra](t.rast.algebra.md) describes
both corrections.

## REFERENCES

[PLY(Python-Lex-Yacc)](https://www.dabeaz.com/ply/)

Gebbert, S., Leppelt, T., Pebesma, E., 2019. A topology based
spatio-temporal map algebra for big data analysis. Data 4, 86.
<https://doi.org/10.3390/data4020086>

## SEE ALSO

*[t.rast.algebra](t.rast.algebra.md),
[t.rast3d.mapcalc](t.rast3d.mapcalc.md), [r.mapcalc](r.mapcalc.md),
[t.vect.algebra](t.vect.algebra.md), [t.select](t.select.md)*

## AUTHORS

Thomas Leppelt, Sören Gebbert, Thünen Institute of Climate-Smart
Agriculture
