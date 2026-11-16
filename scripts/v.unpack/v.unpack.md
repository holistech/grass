## DESCRIPTION

*v.unpack* allows unpacking vector maps packed by *[v.pack](v.pack.md)*.

## NOTES

Name of the vector map is determined by default from pack file
internals. Optionally the name can be given by **output** parameter.

The coordinate reference system (CRS) of the pack file must match the one of
the current project; the name of the CRS is not compared. If it does not, the
module stops with an error. The flag **-o** assumes that both are the same:
the module warns and uses the CRS of the current project. A project without a
CRS (an XY project) has none to match, so a pack file of a project with a CRS
is unpacked there with **-o** only.

## EXAMPLE

Pack up vector map *random_point* into *random_point.pack* file.

```sh
v.pack input=random_point
```

the vector map can be afterwards unpacked by

```sh
v.unpack input=random_point.pack
```

## SEE ALSO

*[v.pack](v.pack.md), [v.in.ogr](v.in.ogr.md), [r.pack](r.pack.md)*

## AUTHOR

Luca Delucchi, Fondazione E. Mach (Italy), based on the *r.unpack* code
