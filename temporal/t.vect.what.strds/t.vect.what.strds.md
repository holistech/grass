## DESCRIPTION

The module *t.vect.what.strds* samples a space time raster dataset
(STRDS) at the spatio-temporal locations of a space time vector dataset
(STVDS).

## NOTES

Without **column**, each sampled raster map gets a column named after it,
with dots replaced by underscores. If the maps of an interval are
aggregated with **method**, the aggregate is stored in a column named
`<strds>_<method>`, for example `tempmean_monthly_average`: the name of the
raster dataset without the mapset, every character outside `A-Za-z0-9_`
replaced by an underscore. A name that would start with a digit gets the
prefix `c_`, because *v.what.rast* cannot write such a column.

Before the first value is written, the module checks the target columns of
all vector maps and layers. If one of them already exists, a layer to be
written has no attribute table, or a vector map belongs to another mapset, the
module stops with an error and changes nothing. With the **--overwrite** flag,
the existing columns are kept and their values are written again, so a second
run does not add a second column. An existing column keeps its type: values
of a floating-point raster map written into an integer column lose their
fractional part, and *v.what.rast* warns about it. To get a column of the new
type, drop the column with *v.db.dropcolumn* first.

## EXAMPLE

The example is based on the space time vector dataset
"precip_stations@climate_2009_2012" created in the
[t.vect.observe.strds](t.vect.observe.strds.md) example. In the example
below, the module fills the new column "new_temp" with values extracted
from the "tempmean_monthly" space time raster dataset:

```sh
t.vect.what.strds input=precip_stations@climate_2009_2012 \
                  strds=tempmean_monthly@climate_2009_2012 \
                  column=new_temp method=average
```

## SEE ALSO

*[r.univar](r.univar.md), [v.univar](v.univar.md),
[v.what.rast](v.what.rast.md), [v.what.rast3](v.what.rast3.md),
[v.what.strds](v.what.strds.md), [v.what.vect](v.what.vect.md),
[t.create](t.create.md), [t.info](t.info.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
