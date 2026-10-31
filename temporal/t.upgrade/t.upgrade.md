## DESCRIPTION

The *t.upgrade* module upgrades the temporal database in the current
mapset from version 2 (default in GRASS 7) to 3 (default in GRASS 8).
The version 3 introduces a semantic label support, see
*[i.band.library](i.band.library.md)* for details.

On a temporal database that already has the current version, *t.upgrade*
drops all views of the database and creates them again in one transaction,
and reports that the database is up-to-date and that its views were created
anew. A database created before a view gained a column, such as
`number_of_semantic_labels` of the space time raster datasets (see
*[t.list](t.list.md)*), gets the views of the installed version this way. The
tables and the rows stay as they are, and a second run changes nothing.

## EXAMPLE

```sh
t.upgrade
```

## SEE ALSO

*[t.info](t.info.md), [t.list](t.list.md)*

## AUTHORS

Martin Landa and Markus Neteler
