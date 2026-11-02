## DESCRIPTION

*t.rast.colors* creates or changes the color tables of the raster maps that are
registered in a space time raster dataset. It is a wrapper around
*[r.colors](r.colors.md)*: the tool writes the names of all registered maps to
a file and runs *r.colors* once with this file, so all maps are handled in one
run. A color table that is computed from the values of the maps, such as
`grey`, therefore stretches over the combined range of all maps of the dataset,
and all maps get the same rules. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets.

The option **input** names the space time raster dataset. Every registered map
is handled; there is no option to select maps. The source of the colors is
exactly one of the following; the flags **-r** and **-l** need none:

- **color** takes the name of a color table of *r.colors*, such as `grey` or
  `viridis`. A table that is defined for a fixed range of values, such as
  `celsius` (-80 to 80), keeps this range; a table without a fixed range is
  stretched over the range of the values of all maps.
- **rules** takes the path of a file with color rules, as *r.colors* reads
  them: one rule per line, a value and a color, such as `0 blue`. The value
  `-` reads the rules from the standard input.
- **raster** takes a raster map and copies its color table to all maps of the
  dataset, with the rules of that map.
- **raster_3d** does the same with the color table of a 3D raster map.

A table that a map has is replaced by the new one; **--overwrite** is not
needed.

The flags change how the table is made or what is done with it:

- **-n** inverts the colors: the color of the smallest value becomes that of
  the largest, and the other way round. *[r.colors.out](r.colors.out.md)*
  prints the same rules with and without the flag, so use
  *[r.what.color](r.what.color.md)* to see the inversion.
- **-g** scales the colors logarithmically, **-a** logarithmically with the
  absolute values, so a negative value gets the color of its absolute value.
  Both write a table of many rules that approximates the curve.
- **-e** equalizes the histogram: the colors are spread by the cumulative
  frequency of the values in the cells, so each cell gets about the same step
  of color, and not each interval of values.
- **-w** writes the new table only to the maps that have none. The table is
  computed from the data range of these maps only. Maps that have a table keep
  it, also a table that *r.colors* wrote in the current mapset for a map of
  another mapset.
- **-r** removes the color table of every map. A map without a table is shown
  with the default table of *r.colors* for its own range of values.
- **-l** prints the names of the color tables of **color** and stops.

## NOTES

Exactly one of **color**, **rules**, **raster**, **raster_3d**, **-r** and
**-l** is required. If none is given, *r.colors* stops with the message "At
least one of the following options is required: `<raster>`, `<raster_3d>`,
`<color>`, `<rules>`, `<-r>`, `<-l>` and `<-d>`" and *t.rast.colors* adds
"Error in r.colors call". More than one source is refused with "Options
`<color>`, `<rules>`, `<raster>` and `<raster_3d>` are mutually exclusive".

An unknown name in **color** is refused by the parser ("Value
`<nosuchtable>` out of range for parameter `<color>`"), and the maps keep their
tables. A missing file in **rules** stops with "Unable to load rules file"
and the path; an unknown map in **raster** stops with "Error in r.colors
call".

A dataset without maps is left alone, without a message.

Datasets with absolute and with relative time are handled in the same way;
the last example uses relative time.

For a dataset of another mapset (`input=model@PERMANENT`), *r.colors* writes the
tables to the current mapset, where they take precedence over the tables of
the maps for as long as this mapset is the current one. The maps in their own
mapset are not changed, as the last example shows.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Give all maps one color table

The dataset `temperature` holds three daily maps on a region of 2 rows and 3
columns. The helper map `cell_number` counts the cells from 1 to 6. The
values of `temperature_1` are 1 to 6, those of `temperature_2` are 10 to 60,
and those of `temperature_3` are 21 to 121 in steps of 20, so the combined
range of the dataset is 1 to 121 and all 18 values are different.

With **color** `grey`, all maps get a table from black at 1 to white at 121,
not one for the range of each map: the first block prints the table of
`temperature_1` and of `temperature_3`. The lines `nv` and `default` are
the colors of null cells and of values outside the table. A table with a fixed
range keeps it: `celsius` runs from -80 to 80, so the second block prints
only the rules for -80 and 80 of the table of `temperature_1`.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="cell_number = 3 * (row() - 1) + col()"
    r.mapcalc expression="temperature_1 = cell_number"
    r.mapcalc expression="temperature_2 = cell_number * 10"
    r.mapcalc expression="temperature_3 = cell_number * 20 + 1"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    ```

    ```sh
    t.rast.colors input=temperature color=grey
    r.colors.out map=temperature_1
    r.colors.out map=temperature_3
    ```

    ```text
    1 0:0:0
    121 255:255:255
    nv 255:255:255
    default 255:255:255
    1 0:0:0
    121 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```sh
    t.rast.colors input=temperature color=celsius
    r.colors.out map=temperature_1 | grep -E "^(-80|80) "
    ```

    ```text
    -80 0:0:40
    80 155:10:155
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="cell_number = 3 * (row() - 1) + col()")
    tools.r_mapcalc(expression="temperature_1 = cell_number")
    tools.r_mapcalc(expression="temperature_2 = cell_number * 10")
    tools.r_mapcalc(expression="temperature_3 = cell_number * 20 + 1")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    ```

    ```python
    tools.t_rast_colors(input="temperature", color="grey")
    print(tools.r_colors_out(map="temperature_1").text)
    print(tools.r_colors_out(map="temperature_3").text)
    ```

    ```text
    1 0:0:0
    121 255:255:255
    nv 255:255:255
    default 255:255:255
    1 0:0:0
    121 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```python
    tools.t_rast_colors(input="temperature", color="celsius")
    for line in tools.r_colors_out(map="temperature_1").text.splitlines():
        if line.split()[0] in ("-80", "80"):
            print(line)
    ```

    ```text
    -80 0:0:40
    80 155:10:155
    ```

### Define the colors by rules and invert them

The rules `1 red` and `121 blue` give a table from red at the smallest to blue
at the largest value of the dataset. The first block reads them from the
standard input (`rules=-`; in Python a `StringIO` object does this) and prints
the table of `temperature_1`; the second block asks *r.what.color* for the
colors of the values 1 and 121.

With **-n**, the table has the same two rules, as the third block shows, but
the colors of the values are the other way round: 1 is blue and 121 red.

=== "Command line"

    ```sh
    t.rast.colors input=temperature rules=- <<EOF
    1 red
    121 blue
    EOF
    r.colors.out map=temperature_1
    ```

    ```text
    1 255:0:0
    121 0:0:255
    nv 255:255:255
    default 255:255:255
    ```

    ```sh
    r.what.color input=temperature_1 value=1,121 format="%d:%d:%d"
    ```

    ```text
    1: 255:0:0
    121: 0:0:255
    ```

    ```sh
    t.rast.colors -n input=temperature rules=- <<EOF
    1 red
    121 blue
    EOF
    r.colors.out map=temperature_1
    r.what.color input=temperature_1 value=1,121 format="%d:%d:%d"
    ```

    ```text
    1 255:0:0
    121 0:0:255
    nv 255:255:255
    default 255:255:255
    1: 0:0:255
    121: 255:0:0
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.t_rast_colors(input="temperature", rules=StringIO("1 red\n121 blue\n"))
    print(tools.r_colors_out(map="temperature_1").text)
    ```

    ```text
    1 255:0:0
    121 0:0:255
    nv 255:255:255
    default 255:255:255
    ```

    ```python
    print(tools.r_what_color(input="temperature_1", value=[1, 121], format="%d:%d:%d").text)
    ```

    ```text
    1: 255:0:0
    121: 0:0:255
    ```

    ```python
    tools.t_rast_colors(input="temperature", rules=StringIO("1 red\n121 blue\n"), flags="n")
    print(tools.r_colors_out(map="temperature_1").text)
    print(tools.r_what_color(input="temperature_1", value=[1, 121], format="%d:%d:%d").text)
    ```

    ```text
    1 255:0:0
    121 0:0:255
    nv 255:255:255
    default 255:255:255
    1: 0:0:255
    121: 255:0:0
    ```

### Scale the colors

The rules `1 red` and `121 blue` are used again. The colors of the values 1, 6,
11 and 121 are printed by *r.what.color* with the linear table, with **-g** and
with **-a**. The linear table puts 11 at 10 / 120 of the way from red to blue,
a red of 234 and a blue of 21. With the logarithmic scale 11 lies at
`ln(11) / ln(121)` = 0.5 of the way, near the middle: 129 and 126. **-g** and
**-a** give the same colors for positive values. With **-a**, the value -11
has the color of 11, within the steps of the table: 128:0:127 against
129:0:126, as the third block shows.

With **-e** and `color=grey`, the colors are spread by the frequency of the
cells. All 18 cells of the dataset have different values, so each value is one
step of 256 / 18 = 14.2 in grey: the smallest values 1, 2 and 3 get the greys
7, 21 and 35. The first three rules of `temperature_1` are printed.

=== "Command line"

    ```sh
    t.rast.colors input=temperature rules=- <<EOF
    1 red
    121 blue
    EOF
    r.what.color input=temperature_1 value=1,6,11,121 format="%d:%d:%d"
    ```

    ```text
    1: 255:0:0
    6: 245:0:10
    11: 234:0:21
    121: 0:0:255
    ```

    ```sh
    t.rast.colors -g input=temperature rules=- <<EOF
    1 red
    121 blue
    EOF
    r.what.color input=temperature_1 value=1,6,11,121 format="%d:%d:%d"
    ```

    ```text
    1: 255:0:0
    6: 161:0:94
    11: 129:0:126
    121: 0:0:255
    ```

    ```sh
    t.rast.colors -a input=temperature rules=- <<EOF
    1 red
    121 blue
    EOF
    r.what.color input=temperature_1 value=-11,11 format="%d:%d:%d"
    ```

    ```text
    -11: 128:0:127
    11: 129:0:126
    ```

    ```sh
    t.rast.colors -e input=temperature color=grey
    r.colors.out map=temperature_1 | sed -n 1,3p
    ```

    ```text
    1 7:7:7
    2 21:21:21
    3 35:35:35
    ```

=== "Python (grass.tools)"

    ```python
    rules = "1 red\n121 blue\n"
    tools.t_rast_colors(input="temperature", rules=StringIO(rules))
    print(
        tools.r_what_color(
            input="temperature_1", value=[1, 6, 11, 121], format="%d:%d:%d"
        ).text
    )
    ```

    ```text
    1: 255:0:0
    6: 245:0:10
    11: 234:0:21
    121: 0:0:255
    ```

    ```python
    tools.t_rast_colors(input="temperature", rules=StringIO(rules), flags="g")
    print(
        tools.r_what_color(
            input="temperature_1", value=[1, 6, 11, 121], format="%d:%d:%d"
        ).text
    )
    ```

    ```text
    1: 255:0:0
    6: 161:0:94
    11: 129:0:126
    121: 0:0:255
    ```

    ```python
    tools.t_rast_colors(input="temperature", rules=StringIO(rules), flags="a")
    print(
        tools.r_what_color(input="temperature_1", value=[-11, 11], format="%d:%d:%d").text
    )
    ```

    ```text
    -11: 128:0:127
    11: 129:0:126
    ```

    ```python
    tools.t_rast_colors(input="temperature", color="grey", flags="e")
    print("\n".join(tools.r_colors_out(map="temperature_1").text.splitlines()[:3]))
    ```

    ```text
    1 7:7:7
    2 21:21:21
    3 35:35:35
    ```

### Copy the color table of another map

The color table of a map becomes the table of all maps of the dataset, with
the rules of that map, and not with the range of the dataset. The 2D map
`reference` has the rules `1 red` and `5 yellow`; **raster** copies them. The
3D map `volume` has the rules `0 yellow` and `10 green`; **raster_3d** copies
them. The 3D map needs a region with a vertical extent, which the first
command of the second block sets.

=== "Command line"

    ```sh
    r.mapcalc expression="reference = 7"
    r.colors map=reference rules=- <<EOF
    1 red
    5 yellow
    EOF
    t.rast.colors input=temperature raster=reference
    r.colors.out map=temperature_1
    ```

    ```text
    1 255:0:0
    5 255:255:0
    nv 255:255:255
    default 255:255:255
    ```

    ```sh
    g.region n=2 s=0 e=3 w=0 t=1 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="volume = 5.0"
    r3.colors map=volume rules=- <<EOF
    0 yellow
    10 green
    EOF
    t.rast.colors input=temperature raster_3d=volume
    r.colors.out map=temperature_1
    ```

    ```text
    0 255:255:0
    10 0:255:0
    nv 255:255:255
    default 255:255:255
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="reference = 7")
    tools.r_colors(map="reference", rules=StringIO("1 red\n5 yellow\n"))
    tools.t_rast_colors(input="temperature", raster="reference")
    print(tools.r_colors_out(map="temperature_1").text)
    ```

    ```text
    1 255:0:0
    5 255:255:0
    nv 255:255:255
    default 255:255:255
    ```

    ```python
    tools.g_region(n=2, s=0, e=3, w=0, t=1, b=0, res=1, res3=1, tbres=1)
    tools.r3_mapcalc(expression="volume = 5.0")
    tools.r3_colors(map="volume", rules=StringIO("0 yellow\n10 green\n"))
    tools.t_rast_colors(input="temperature", raster_3d="volume")
    print(tools.r_colors_out(map="temperature_1").text)
    ```

    ```text
    0 255:255:0
    10 0:255:0
    nv 255:255:255
    default 255:255:255
    ```

### Keep the tables that exist

The new map `temperature_4` has the values 30 to 180 and no color table. It is
registered in the dataset, which now has four maps; the other three have the
table of the previous example. With **-w**, only `temperature_4` gets the
table `grey`, and it is computed from its own range, 30 to 180, and not from
the range of the dataset. The first block prints the table of
`temperature_4`; the second shows that `temperature_1` keeps the rules of the
previous example.

=== "Command line"

    ```sh
    r.mapcalc expression="temperature_4 = cell_number * 30"
    t.register input=temperature maps=temperature_4 start=2026-03-04 \
        end=2026-03-05
    t.rast.colors -w input=temperature color=grey
    r.colors.out map=temperature_4
    ```

    ```text
    30 0:0:0
    180 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```sh
    r.colors.out map=temperature_1
    ```

    ```text
    0 255:255:0
    10 0:255:0
    nv 255:255:255
    default 255:255:255
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="temperature_4 = cell_number * 30")
    tools.t_register(
        input="temperature",
        maps="temperature_4",
        start="2026-03-04",
        end="2026-03-05",
    )
    tools.t_rast_colors(input="temperature", color="grey", flags="w")
    print(tools.r_colors_out(map="temperature_4").text)
    ```

    ```text
    30 0:0:0
    180 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```python
    print(tools.r_colors_out(map="temperature_1").text)
    ```

    ```text
    0 255:255:0
    10 0:255:0
    nv 255:255:255
    default 255:255:255
    ```

### List the color tables and remove the tables

**-l** prints the names of all color tables that **color** accepts, one per
line; the first block selects two of them. **-r** removes the color table of
every map of the dataset. A map without a table is shown with the default
table of *r.colors* for the range of the map itself: the second block prints
the rules for 1 and 6 of `temperature_1`, the smallest and the largest value
of this map, and not the range 1 to 121 of the dataset.

=== "Command line"

    ```sh
    t.rast.colors -l input=temperature | grep -x -E "grey|viridis"
    ```

    ```text
    grey
    viridis
    ```

    ```sh
    t.rast.colors -r input=temperature
    r.colors.out map=temperature_1 | grep -E "^(1|6) "
    ```

    ```text
    1 68:1:84
    6 253:231:37
    ```

=== "Python (grass.tools)"

    ```python
    for line in tools.t_rast_colors(input="temperature", flags="l").text.splitlines():
        if line in ("grey", "viridis"):
            print(line)
    ```

    ```text
    grey
    viridis
    ```

    ```python
    tools.t_rast_colors(input="temperature", flags="r")
    for line in tools.r_colors_out(map="temperature_1").text.splitlines():
        if line.split()[0] in ("1", "6"):
            print(line)
    ```

    ```text
    1 68:1:84
    6 253:231:37
    ```

### Color a dataset of another mapset

The dataset `model` has relative time and lies in the mapset `PERMANENT`. The
example creates the mapset `analysis`, switches to it and colors `model`; the
dataset is named with its mapset. The tables are written to `analysis`: the
first block prints the table of `step_1@PERMANENT` in `analysis`, the grey
table for the range 1 to 6 of the dataset; the second block prints the rules
for 1 and 3 after switching back to `PERMANENT`, where the map has the
default table for its own range, 1 to 3. The maps in `PERMANENT` are not changed.

=== "Command line"

    ```sh
    r.mapcalc expression="step_1 = col()"
    r.mapcalc expression="step_2 = col() * 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=1 unit=hours
    g.mapset -c mapset=analysis
    t.rast.colors input=model@PERMANENT color=grey
    r.colors.out map=step_1@PERMANENT
    ```

    ```text
    1 0:0:0
    6 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```sh
    g.mapset mapset=PERMANENT
    r.colors.out map=step_1 | grep -E "^(1|3) "
    ```

    ```text
    1 68:1:84
    3 253:231:37
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="step_1 = col()")
    tools.r_mapcalc(expression="step_2 = col() * 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=1, unit="hours", flags="i"
    )
    tools.g_mapset(mapset="analysis", flags="c")
    tools.t_rast_colors(input="model@PERMANENT", color="grey")
    print(tools.r_colors_out(map="step_1@PERMANENT").text)
    ```

    ```text
    1 0:0:0
    6 255:255:255
    nv 255:255:255
    default 255:255:255
    ```

    ```python
    tools.g_mapset(mapset="PERMANENT")
    for line in tools.r_colors_out(map="step_1").text.splitlines():
        if line.split()[0] in ("1", "3"):
            print(line)
    ```

    ```text
    1 68:1:84
    3 253:231:37
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.region](g.region.md), [r.colors](r.colors.md),
[r.colors.out](r.colors.out.md), [r.mapcalc](r.mapcalc.md),
[r.what.color](r.what.color.md), [r3.colors](r3.colors.md),
[r3.mapcalc](r3.mapcalc.md), [t.create](t.create.md),
[t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
