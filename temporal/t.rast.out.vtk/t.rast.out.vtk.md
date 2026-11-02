## DESCRIPTION

*t.rast.out.vtk* writes each raster map of a space time raster dataset into a
VTK legacy file, one file per map. The files are ASCII text; a program that
reads VTK, such as [ParaView](https://www.paraview.org), can show them one
after the other as a time series. The tool runs *[r.out.vtk](r.out.vtk.md)* for
every map. See the
[introduction to temporal data processing](temporalintro.md) for space time
datasets. The tool that writes a dataset into one archive for another GRASS
project is *[t.rast.export](t.rast.export.md)*.

The option **input** names the space time raster dataset, and **directory** the
directory that receives the files. The directory must exist; the tool does not
make it. A relative **directory** is taken from the current directory.

### Select the maps

The option **where** takes an SQL condition on the columns of the registered
maps, such as `start_time >= '2026-03-02'`, and writes only the maps it selects.
Without **where**, all maps are written. The maps are written in the order of
their start time. **where** is ignored with the flag **-g**.

The flag **-g** writes the files for equidistant steps of the granularity of
the dataset. A time step in which no map is registered, a gap, gets a file in
which every cell has the **null** value. The files of a dataset without gaps
are the same with and without **-g**. A dataset with gaps gets more files with
**-g**, one for each missing step.

### Names of the files

The files are numbered from `000000` in the order of the maps, and the number
has six digits. The file name is the number, an underscore, the name of the
dataset without its mapset and the suffix `.vtk`, such as
`000002_temperature.vtk`. The numbering starts at `000000` again for every call
and counts only the written files, so a selection with **where** is numbered
without holes. An existing file is refused unless the flag **--overwrite** is
given.

### Content of the files

*r.out.vtk* writes the cells of the current computational region, so the files
of one call have the grid of the region at the time of the call. The first four
lines of a file are `# vtk DataFile Version 3.0`, the title
`GRASS 8 Export`, the word `ASCII` and the dataset type. The following lines
give the number of points in each direction, the spacing, the origin and the
number of values; the values follow in rows after the line
`LOOKUP_TABLE default`. The name of the scalar in the line that starts with
`SCALARS` is the name of the dataset and the number of the process that ran
the tool, so it differs from call to call.

- Without **elevation** the file holds the cells as a grid of cells
  (`DATASET STRUCTURED_POINTS` and `CELL_DATA`): the grid has one point more
  than cells in each direction and starts at the south-west corner of the
  region.
- With the flag **-p** the file holds point data instead
  (`POINT_DATA`): one point at the centre of each cell, so the grid has as
  many points as the region has cells and starts at the centre of the
  south-west cell.
- The option **elevation** names a raster map that gives the height of each
  cell. The file then holds a surface (`DATASET POLYDATA`): a list of points,
  one at the centre of each cell with the value of the elevation map as height,
  the quadrilaterals between four neighbouring points, and the values of the
  dataset map at the points. The flag **-p** changes nothing for a file with **elevation**.
- The option **null** sets the value that is written for a cell without data. It
  is `-99999.99` by default. The value applies to files with and without
  **elevation**.
- The flag **-c** corrects the coordinates of the grid: the origin is moved by
  the centre of the default region of the project, which `g.region -d` shows,
  so that the coordinates of a project with large coordinate values become
  small numbers. Use **-c** for all files that are shown together, and only
  for data of one project, as the default region differs between projects.

## NOTES

The tool copies every map under a temporary name to make the scalars of all
files have the same name, and exports the copy. The copy and, with **-g**, the
map without data are removed in every case, also if the export stops with an
error.

The tool stops with "Export directory `name` not found." if **directory** does
not exist or is a file. A **where** condition with a syntax error stops the
tool with an error that contains "Invalid where condition", and no file is
written. A file that exists already stops the tool with "Unable to export
raster map" and leaves the file as it was (see the sixth example).

A dataset with relative time is written like one with absolute time, and a
dataset of another mapset is named with its mapset. The last example shows
both.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Write one VTK file per map

The dataset `temperature` has three maps of two rows and three columns. The
cell value of `temperature_1` is `10 * row + column`, so it is 11, 12, 13 in
the northern row and 21, 22, 23 in the southern one. `temperature_2` is the
same plus 100. `temperature_4` has the value 1.5 in the first column and no
data in the others. The first two maps are the days 1 and 2 of March 2026, and
the third is the day 4, so there is no map for the day 3.

The first block creates the dataset. The second block makes the directory
`vtk` and writes the files into it. The tool makes one file for each of the
three maps, numbered in the order of time. The first eight lines of the first
file are the version, the title, the format, the dataset type and the grid: 4
by 3 points around 3 by 2 cells with the spacing 1 and the origin in the
south-west corner of the region. The last two lines hold the values, row by
row, the southern row first. The line that starts with `SCALARS` is left out
because it holds the number of the process.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="temperature_1 = 10 * row() + col()"
    r.mapcalc expression="temperature_2 = 10 * row() + col() + 100"
    r.mapcalc expression="temperature_4 = if(col() == 1, 1.5, null())"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature maps=temperature_1,temperature_2 \
        start=2026-03-01 increment="1 day"
    t.register input=temperature maps=temperature_4 \
        start=2026-03-04 end=2026-03-05
    ```

    ```sh
    mkdir vtk
    t.rast.out.vtk input=temperature directory=vtk
    ls vtk
    head -n 8 vtk/000000_temperature.vtk
    tail -n 2 vtk/000000_temperature.vtk | sed 's/ *$//'
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET STRUCTURED_POINTS
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 0.000000 0.000000 0.000000
    CELL_DATA 6
    21.000000000000 22.000000000000 23.000000000000
    11.000000000000 12.000000000000 13.000000000000
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="temperature_1 = 10 * row() + col()")
    tools.r_mapcalc(expression="temperature_2 = 10 * row() + col() + 100")
    tools.r_mapcalc(expression="temperature_4 = if(col() == 1, 1.5, null())")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_register(
        input="temperature", maps="temperature_4", start="2026-03-04", end="2026-03-05"
    )
    ```

    ```python
    Path("vtk").mkdir()
    tools.t_rast_out_vtk(input="temperature", directory="vtk")
    print("\n".join(sorted(path.name for path in Path("vtk").iterdir())))
    lines = Path("vtk/000000_temperature.vtk").read_text().splitlines()
    print("\n".join(lines[:8]))
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET STRUCTURED_POINTS
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 0.000000 0.000000 0.000000
    CELL_DATA 6
    21.000000000000 22.000000000000 23.000000000000
    11.000000000000 12.000000000000 13.000000000000
    ```

### Select maps and set the value of cells without data

**where** selects the maps `temperature_2` and `temperature_4`, those that start
on or after 2 March. They are written into the new directory `selected` and
numbered `000000` and `000001`, although they are the second and third map of
the dataset. **null** sets `-9999` for the cells without data, so the last two
cells in each row of `temperature_4` hold `-9999` and the first one holds 1.5.
The values are written with twelve decimal places.

=== "Command line"

    ```sh
    mkdir selected
    t.rast.out.vtk input=temperature directory=selected \
        where="start_time >= '2026-03-02'" null=-9999
    ls selected
    tail -n 2 selected/000001_temperature.vtk | sed 's/ *$//'
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    1.500000000000 -9999.000000000000 -9999.000000000000
    1.500000000000 -9999.000000000000 -9999.000000000000
    ```

=== "Python (grass.tools)"

    ```python
    Path("selected").mkdir()
    tools.t_rast_out_vtk(
        input="temperature",
        directory="selected",
        where="start_time >= '2026-03-02'",
        null=-9999,
    )
    print("\n".join(sorted(path.name for path in Path("selected").iterdir())))
    lines = Path("selected/000001_temperature.vtk").read_text().splitlines()
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    1.500000000000 -9999.000000000000 -9999.000000000000
    1.500000000000 -9999.000000000000 -9999.000000000000
    ```

### Write a file for each time step with the granularity

The dataset has the granularity of one day, and there is no map on 3 March. The
flag **-g** writes a file for every day: four files instead of three. The file
`000002_temperature.vtk` is the gap on 3 March; all its cells have the **null**
value. The call also has a **where** condition that would select two maps, but
**-g** ignores it: all four files are written. The last two lines of the gap
file are shown.

=== "Command line"

    ```sh
    mkdir granules
    t.rast.out.vtk -g input=temperature directory=granules null=-9999 \
        where="start_time >= '2026-03-02'"
    ls granules
    tail -n 2 granules/000002_temperature.vtk | sed 's/ *$//'
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    000003_temperature.vtk
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    ```

=== "Python (grass.tools)"

    ```python
    Path("granules").mkdir()
    tools.t_rast_out_vtk(
        input="temperature",
        directory="granules",
        flags="g",
        null=-9999,
        where="start_time >= '2026-03-02'",
    )
    print("\n".join(sorted(path.name for path in Path("granules").iterdir())))
    lines = Path("granules/000002_temperature.vtk").read_text().splitlines()
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    000003_temperature.vtk
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    ```

### Draw the maps as a surface

The map `elevation` has the value `100 * row + column`: 101, 102, 103 in the
northern row and 201, 202, 203 in the southern one. With **elevation** the
files hold a surface (`DATASET POLYDATA`) instead of a grid of cells: six
points, one at the centre of each cell with the elevation as the third
coordinate, listed from the southern row, and two quadrilaterals (`POLYGONS 2
10`) between them. Each quadrilateral lists four point numbers, counted from 0.
The values follow with `POINT_DATA`. The example writes the first map only, the
one with the values 11 to 23.

The second block repeats the call with **-p** into another directory and
compares the files without the `SCALARS` line: they are the same, because **-p**
changes nothing for a surface.

=== "Command line"

    ```sh
    r.mapcalc expression="elevation = 100 * row() + col()"
    mkdir surface surface_p
    t.rast.out.vtk input=temperature directory=surface elevation=elevation \
        where="name = 'temperature_1'" null=-9999
    grep -v SCALARS surface/000000_temperature.vtk | sed 's/ *$//'
    ```

    ```text
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET POLYDATA
    POINTS 6 float
    0.500000000000 0.500000000000 201.000000000000
    1.500000000000 0.500000000000 202.000000000000
    2.500000000000 0.500000000000 203.000000000000
    0.500000000000 1.500000000000 101.000000000000
    1.500000000000 1.500000000000 102.000000000000
    2.500000000000 1.500000000000 103.000000000000
    POLYGONS 2 10
    4 0 1 4 3
    4 1 2 5 4
    POINT_DATA 6
    LOOKUP_TABLE default
    21.000000000000 22.000000000000 23.000000000000
    11.000000000000 12.000000000000 13.000000000000
    ```

    ```sh
    t.rast.out.vtk -p input=temperature directory=surface_p \
        elevation=elevation where="name = 'temperature_1'" null=-9999
    diff <(grep -v SCALARS surface/000000_temperature.vtk) \
        <(grep -v SCALARS surface_p/000000_temperature.vtk) && echo same
    ```

    ```text
    same
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="elevation = 100 * row() + col()")
    Path("surface").mkdir()
    Path("surface_p").mkdir()
    tools.t_rast_out_vtk(
        input="temperature",
        directory="surface",
        elevation="elevation",
        where="name = 'temperature_1'",
        null=-9999,
    )
    lines = Path("surface/000000_temperature.vtk").read_text().splitlines()
    surface = [line for line in lines if not line.startswith("SCALARS")]
    print("\n".join(line.rstrip() for line in surface))
    ```

    ```text
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET POLYDATA
    POINTS 6 float
    0.500000000000 0.500000000000 201.000000000000
    1.500000000000 0.500000000000 202.000000000000
    2.500000000000 0.500000000000 203.000000000000
    0.500000000000 1.500000000000 101.000000000000
    1.500000000000 1.500000000000 102.000000000000
    2.500000000000 1.500000000000 103.000000000000
    POLYGONS 2 10
    4 0 1 4 3
    4 1 2 5 4
    POINT_DATA 6
    LOOKUP_TABLE default
    21.000000000000 22.000000000000 23.000000000000
    11.000000000000 12.000000000000 13.000000000000
    ```

    ```python
    tools.t_rast_out_vtk(
        input="temperature",
        directory="surface_p",
        elevation="elevation",
        where="name = 'temperature_1'",
        null=-9999,
        flags="p",
    )
    lines = Path("surface_p/000000_temperature.vtk").read_text().splitlines()
    if [line for line in lines if not line.startswith("SCALARS")] == surface:
        print("same")
    ```

    ```text
    same
    ```

### Point data and coordinates in a large coordinate system

The region moves to the coordinates 1000 to 1003 and 2000 to 2002, as in a
project with a projected coordinate system, and the call writes the first map
four times: without flag, with **-p**, with **-c** and with both. Each call
prints the lines 5 to 8 of the first file, which hold the number of points, the
spacing, the origin and the kind of data.

Without a flag the file holds cells: 4 by 3 points and the origin in the
south-west corner, 1000 and 2000. With **-p** it holds points: 3 by 2 points
and the origin at the centre of the south-west cell, 1000.5 and 2000.5. The
default region of a new project is the square from 0 to 1, so its centre is
0.5; the values below depend on it (`g.region -d -p` shows the default region
of another project).
**-c** moves the origin by this value: 999.5 and 1999.5 for the cells, and 1000
and 2000 for the points. The last block sets the region back.

=== "Command line"

    ```sh
    g.region n=2002 s=2000 w=1000 e=1003 res=1
    mkdir plain points corrected both
    t.rast.out.vtk input=temperature directory=plain null=-9999 \
        where="name = 'temperature_1'"
    t.rast.out.vtk -p input=temperature directory=points null=-9999 \
        where="name = 'temperature_1'"
    t.rast.out.vtk -c input=temperature directory=corrected null=-9999 \
        where="name = 'temperature_1'"
    t.rast.out.vtk -p -c input=temperature directory=both null=-9999 \
        where="name = 'temperature_1'"
    for directory in plain points corrected both; do
        echo $directory
        sed -n 5,8p $directory/000000_temperature.vtk
    done
    g.region n=2 s=0 e=3 w=0 res=1
    ```

    ```text
    plain
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.000000 2000.000000 0.000000
    CELL_DATA 6
    points
    DIMENSIONS 3 2 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.500000 2000.500000 0.000000
    POINT_DATA 6
    corrected
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 999.500000 1999.500000 0.000000
    CELL_DATA 6
    both
    DIMENSIONS 3 2 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.000000 2000.000000 0.000000
    POINT_DATA 6
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=2002, s=2000, w=1000, e=1003, res=1)
    for directory, flags in (
        ("plain", ""),
        ("points", "p"),
        ("corrected", "c"),
        ("both", "pc"),
    ):
        Path(directory).mkdir()
        tools.t_rast_out_vtk(
            input="temperature",
            directory=directory,
            flags=flags,
            null=-9999,
            where="name = 'temperature_1'",
        )
        print(directory)
        lines = Path(directory, "000000_temperature.vtk").read_text().splitlines()
        print("\n".join(lines[4:8]))
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    ```

    ```text
    plain
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.000000 2000.000000 0.000000
    CELL_DATA 6
    points
    DIMENSIONS 3 2 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.500000 2000.500000 0.000000
    POINT_DATA 6
    corrected
    DIMENSIONS 4 3 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 999.500000 1999.500000 0.000000
    CELL_DATA 6
    both
    DIMENSIONS 3 2 1
    SPACING 1.000000 1.000000 0.000000
    ORIGIN 1000.000000 2000.000000 0.000000
    POINT_DATA 6
    ```

### Replace existing files

The directory `vtk` from the first example holds the files already. A second
call without **--overwrite** is refused: the message names the file, and the
tool stops with "Unable to export raster map" and a temporary name that
differs from call to call, so only the line about the file is shown. The file
is as it was. The call with **--overwrite** replaces the files.

=== "Command line"

    ```sh
    t.rast.out.vtk input=temperature directory=vtk 2>&1 | grep "exists" || true
    t.rast.out.vtk --overwrite input=temperature directory=vtk
    ls vtk
    ```

    ```text
    ERROR: option <output>: <000000_temperature.vtk> exists. To overwrite, use the --overwrite flag
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    try:
        tools.t_rast_out_vtk(input="temperature", directory="vtk")
    except ToolError as error:
        print([line for line in error.stderr.splitlines() if "exists" in line][0])
    tools.t_rast_out_vtk(input="temperature", directory="vtk", overwrite=True)
    print("\n".join(sorted(path.name for path in Path("vtk").iterdir())))
    ```

    ```text
    ERROR: option <output>: <000000_temperature.vtk> exists. To overwrite, use the --overwrite flag
    000000_temperature.vtk
    000001_temperature.vtk
    000002_temperature.vtk
    ```

### Write a dataset of another mapset with relative time

The dataset `model` has relative time and two maps in the mapset `PERMANENT`. The
example switches to the mapset `analysis`, which has the default region, so it
sets the region of the maps again. The call names the dataset with its mapset.
The files are numbered as for absolute time.

=== "Command line"

    ```sh
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=1 unit=hours
    g.mapset -c mapset=analysis
    g.region n=2 s=0 e=3 w=0 res=1
    mkdir model
    t.rast.out.vtk input=model@PERMANENT directory=model
    ls model
    ```

    ```text
    000000_model.vtk
    000001_model.vtk
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=1, unit="hours", flags="i"
    )
    tools.g_mapset(flags="c", mapset="analysis")
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    Path("model").mkdir()
    tools.t_rast_out_vtk(input="model@PERMANENT", directory="model")
    print("\n".join(sorted(path.name for path in Path("model").iterdir())))
    ```

    ```text
    000000_model.vtk
    000001_model.vtk
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.region](g.region.md), [r.out.vtk](r.out.vtk.md),
[t.create](t.create.md), [t.rast.export](t.rast.export.md),
[t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
