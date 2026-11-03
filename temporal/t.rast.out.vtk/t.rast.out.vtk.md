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
`000002_temperature_monthly.vtk`. The numbering starts at `000000` again for
every call and counts only the written files, so a selection with **where** is
numbered without holes. An existing file is refused unless the flag
**--overwrite** is given.

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

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_rast_out_vtk` and sets the computational region
to North Carolina with cells of 1 km; it builds the dataset
`temperature_monthly` with the mean air temperature of each month of 2020 in
degree Celsius, generated from the elevation by a formula and not measured. A
VTK file holds every cell of the region as text, and one file of the whole
state would have more than 280,000 values. The examples
therefore write a window of three by two cells of 1 km, set with
*[g.region](g.region.md)* before each call: `n=210000 s=208000 w=600000
e=603000` in the Piedmont and `n=200000 s=198000 w=928000 e=931000` at the
Atlantic coast, where the first column holds land and the two others lie
outside the state and hold no data. The files then have six values each, and
the shown lines are the same on every system.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_rast_out_vtk -->

<!-- markdownlint-disable MD046 -->

### Write one VTK file per map

The dataset `temperature_monthly` has the twelve monthly maps of 2020. The
temperature falls by 0.65 degrees per 100 m of elevation of
`elev_state_500m`, is rounded to 0.1 degrees and is highest in July. The
window is the one in the Piedmont. The tool makes one file for each of the
twelve maps, numbered in the order of time; the example lists the number of
files and the first three names. The first eight lines of the first file are
the version, the title, the format, the dataset type and the grid: 4 by 3
points around 3 by 2 cells with the spacing 1000 and the origin in the
south-west corner of the window. The last two lines hold the values of the
January map, row by row, the southern row first. The line that starts with
`SCALARS` is left out because it holds the number of the process.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_rast_out_vtk
    g.region raster=elev_state_500m res=1000 -a
    for month in $(seq 12); do
        echo "temperature_monthly_2020_$(printf %02d $month) = round((16.5" \
            "+ 10.5 * cos(30 * ($month - 7.2)) - 0.0065 * elev_state_500m" \
            "- 0.00001 * (y() - 160000)) * 10) / 10.0"
    done | r.mapcalc file=-
    t.create output=temperature_monthly title="Air temperature" \
        description="Monthly mean air temperature 2020 in degree Celsius"
    t.register -i input=temperature_monthly \
        maps=$(g.list type=raster pattern="temperature_monthly_*" mapset=. separator=comma) \
        start=2020-01-01 increment="1 month"
    ```

    ```sh
    g.region n=210000 s=208000 w=600000 e=603000 res=1000
    mkdir vtk
    t.rast.out.vtk input=temperature_monthly directory=vtk
    ls vtk | wc -l
    ls vtk | head -n 3
    head -n 8 vtk/000000_temperature_monthly.vtk
    tail -n 2 vtk/000000_temperature_monthly.vtk | sed 's/ *$//'
    ```

    ```text
    12
    000000_temperature_monthly.vtk
    000001_temperature_monthly.vtk
    000002_temperature_monthly.vtk
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET STRUCTURED_POINTS
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600000.000000 208000.000000 0.000000
    CELL_DATA 6
    5.100000000000 5.100000000000 5.100000000000
    4.900000000000 5.100000000000 5.100000000000
    ```

=== "Python (grass.tools)"

    ```python
    from pathlib import Path

    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_rast_out_vtk")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    months = range(1, 13)
    tools.r_mapcalc(
        expression="\n".join(
            f"temperature_monthly_2020_{month:02d} = round((16.5"
            f" + 10.5 * cos(30 * ({month} - 7.2)) - 0.0065 * elev_state_500m"
            " - 0.00001 * (y() - 160000)) * 10) / 10.0"
            for month in months
        )
    )
    tools.t_create(
        output="temperature_monthly",
        title="Air temperature",
        description="Monthly mean air temperature 2020 in degree Celsius",
    )
    tools.t_register(
        input="temperature_monthly",
        maps=",".join(f"temperature_monthly_2020_{month:02d}" for month in months),
        start="2020-01-01",
        increment="1 month",
        flags="i",
    )
    ```

    ```python
    tools.g_region(n=210000, s=208000, w=600000, e=603000, res=1000)
    Path("vtk").mkdir()
    tools.t_rast_out_vtk(input="temperature_monthly", directory="vtk")
    names = sorted(path.name for path in Path("vtk").iterdir())
    print(len(names))
    print("\n".join(names[:3]))
    lines = Path("vtk/000000_temperature_monthly.vtk").read_text().splitlines()
    print("\n".join(lines[:8]))
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    12
    000000_temperature_monthly.vtk
    000001_temperature_monthly.vtk
    000002_temperature_monthly.vtk
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET STRUCTURED_POINTS
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600000.000000 208000.000000 0.000000
    CELL_DATA 6
    5.100000000000 5.100000000000 5.100000000000
    4.900000000000 5.100000000000 5.100000000000
    ```

### Select maps and set the value of cells without data

**where** selects the maps of November and December, those that start on or
after 1 November. They are written into the new directory `selected` and
numbered `000000` and `000001`, although they are the eleventh and twelfth map
of the dataset. The window is the one at the coast. **null** sets `-9999` for
the cells without data, so the last two cells in each row hold `-9999` and the
first one holds the temperature of the land cell in December, 7.6 degrees. The
values are written with twelve decimal places.

=== "Command line"

    ```sh
    g.region n=200000 s=198000 w=928000 e=931000 res=1000
    mkdir selected
    t.rast.out.vtk input=temperature_monthly directory=selected \
        where="start_time >= '2020-11-01'" null=-9999
    ls selected
    tail -n 2 selected/000001_temperature_monthly.vtk | sed 's/ *$//'
    ```

    ```text
    000000_temperature_monthly.vtk
    000001_temperature_monthly.vtk
    7.600000000000 -9999.000000000000 -9999.000000000000
    7.600000000000 -9999.000000000000 -9999.000000000000
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=200000, s=198000, w=928000, e=931000, res=1000)
    Path("selected").mkdir()
    tools.t_rast_out_vtk(
        input="temperature_monthly",
        directory="selected",
        where="start_time >= '2020-11-01'",
        null=-9999,
    )
    print("\n".join(sorted(path.name for path in Path("selected").iterdir())))
    lines = Path("selected/000001_temperature_monthly.vtk").read_text().splitlines()
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    000000_temperature_monthly.vtk
    000001_temperature_monthly.vtk
    7.600000000000 -9999.000000000000 -9999.000000000000
    7.600000000000 -9999.000000000000 -9999.000000000000
    ```

### Write a file for each time step with the granularity

The dataset `temperature_gaps` holds the maps of January, February and April
2020 and takes their times from the maps, as `t.register` does for maps that
have a time already. It has the granularity of one month, and there is no map
for March. The flag **-g** writes a file for every month: four files instead
of three. The file `000002_temperature_gaps.vtk` is the gap of March; all its
cells have the **null** value. The call also has a **where** condition that
would select two maps, but **-g** ignores it: all four files are written. The
last two lines of the gap file are shown.

=== "Command line"

    ```sh
    t.create output=temperature_gaps title="Air temperature with a gap" \
        description="Monthly mean air temperature 2020 without March"
    t.register input=temperature_gaps \
        maps=temperature_monthly_2020_01,temperature_monthly_2020_02,temperature_monthly_2020_04
    g.region n=210000 s=208000 w=600000 e=603000 res=1000
    mkdir granules
    t.rast.out.vtk -g input=temperature_gaps directory=granules null=-9999 \
        where="start_time >= '2020-02-01'"
    ls granules
    tail -n 2 granules/000002_temperature_gaps.vtk | sed 's/ *$//'
    ```

    ```text
    000000_temperature_gaps.vtk
    000001_temperature_gaps.vtk
    000002_temperature_gaps.vtk
    000003_temperature_gaps.vtk
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_create(
        output="temperature_gaps",
        title="Air temperature with a gap",
        description="Monthly mean air temperature 2020 without March",
    )
    tools.t_register(
        input="temperature_gaps",
        maps="temperature_monthly_2020_01,temperature_monthly_2020_02,"
        "temperature_monthly_2020_04",
    )
    tools.g_region(n=210000, s=208000, w=600000, e=603000, res=1000)
    Path("granules").mkdir()
    tools.t_rast_out_vtk(
        input="temperature_gaps",
        directory="granules",
        flags="g",
        null=-9999,
        where="start_time >= '2020-02-01'",
    )
    print("\n".join(sorted(path.name for path in Path("granules").iterdir())))
    lines = Path("granules/000002_temperature_gaps.vtk").read_text().splitlines()
    print("\n".join(line.rstrip() for line in lines[-2:]))
    ```

    ```text
    000000_temperature_gaps.vtk
    000001_temperature_gaps.vtk
    000002_temperature_gaps.vtk
    000003_temperature_gaps.vtk
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    -9999.000000000000 -9999.000000000000 -9999.000000000000
    ```

### Draw the maps as a surface

With **elevation** the files hold a surface (`DATASET POLYDATA`) instead of a
grid of cells: six points, one at the centre of each cell with the elevation
of `elev_state_500m` in meters as the third coordinate, listed from the
southern row, and two quadrilaterals (`POLYGONS 2 10`) between them. Each
quadrilateral lists four point numbers, counted from 0. The values follow with
`POINT_DATA`. The example writes the January map only.

The second block repeats the call with **-p** into another directory and
compares the files without the `SCALARS` line: they are the same, because **-p**
changes nothing for a surface.

=== "Command line"

    ```sh
    g.region n=210000 s=208000 w=600000 e=603000 res=1000
    mkdir surface surface_p
    t.rast.out.vtk input=temperature_monthly directory=surface \
        elevation=elev_state_500m \
        where="name = 'temperature_monthly_2020_01'" null=-9999
    grep -v SCALARS surface/000000_temperature_monthly.vtk | sed 's/ *$//'
    ```

    ```text
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET POLYDATA
    POINTS 6 float
    600500.000000000000 208500.000000000000 66.440725843200
    601500.000000000000 208500.000000000000 73.203652627200
    602500.000000000000 208500.000000000000 65.847543590400
    600500.000000000000 209500.000000000000 94.675374580800
    601500.000000000000 209500.000000000000 78.346650316800
    602500.000000000000 209500.000000000000 75.891428100000
    POLYGONS 2 10
    4 0 1 4 3
    4 1 2 5 4
    POINT_DATA 6
    LOOKUP_TABLE default
    5.100000000000 5.100000000000 5.100000000000
    4.900000000000 5.100000000000 5.100000000000
    ```

    ```sh
    t.rast.out.vtk -p input=temperature_monthly directory=surface_p \
        elevation=elev_state_500m \
        where="name = 'temperature_monthly_2020_01'" null=-9999
    diff <(grep -v SCALARS surface/000000_temperature_monthly.vtk) \
        <(grep -v SCALARS surface_p/000000_temperature_monthly.vtk) && echo same
    ```

    ```text
    same
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(n=210000, s=208000, w=600000, e=603000, res=1000)
    Path("surface").mkdir()
    Path("surface_p").mkdir()
    tools.t_rast_out_vtk(
        input="temperature_monthly",
        directory="surface",
        elevation="elev_state_500m",
        where="name = 'temperature_monthly_2020_01'",
        null=-9999,
    )
    lines = Path("surface/000000_temperature_monthly.vtk").read_text().splitlines()
    surface = [line for line in lines if not line.startswith("SCALARS")]
    print("\n".join(line.rstrip() for line in surface))
    ```

    ```text
    # vtk DataFile Version 3.0
    GRASS 8 Export
    ASCII
    DATASET POLYDATA
    POINTS 6 float
    600500.000000000000 208500.000000000000 66.440725843200
    601500.000000000000 208500.000000000000 73.203652627200
    602500.000000000000 208500.000000000000 65.847543590400
    600500.000000000000 209500.000000000000 94.675374580800
    601500.000000000000 209500.000000000000 78.346650316800
    602500.000000000000 209500.000000000000 75.891428100000
    POLYGONS 2 10
    4 0 1 4 3
    4 1 2 5 4
    POINT_DATA 6
    LOOKUP_TABLE default
    5.100000000000 5.100000000000 5.100000000000
    4.900000000000 5.100000000000 5.100000000000
    ```

    ```python
    tools.t_rast_out_vtk(
        input="temperature_monthly",
        directory="surface_p",
        elevation="elev_state_500m",
        where="name = 'temperature_monthly_2020_01'",
        null=-9999,
        flags="p",
    )
    path = Path("surface_p/000000_temperature_monthly.vtk")
    lines = path.read_text().splitlines()
    if [line for line in lines if not line.startswith("SCALARS")] == surface:
        print("same")
    ```

    ```text
    same
    ```

### Point data and coordinates of the project

The coordinates of the window are large, as in every project with a
projected coordinate system. The call writes the January map four times:
without flag, with **-p**, with **-c** and with both. Each call prints the
lines 5 to 8 of the first file, which hold the number of points, the spacing,
the origin and the kind of data.

Without a flag the file holds cells: 4 by 3 points and the origin in the
south-west corner of the window, 600000 and 208000. With **-p** it holds
points: 3 by 2 points and the origin at the centre of the south-west cell,
600500 and 208500. The first command prints the default region of the project
(`g.region -d -u -g`; **-u** leaves the current region as it is). Its centre
is 527500 and 165000, the mean of the west and east and of the south and north
values. **-c** moves the origin by this value: 72500 and 43000 for the cells,
and 73000 and 43500 for the points. The values depend on the default region
of the project, which is the same in the sample dataset and its full version.

=== "Command line"

    ```sh
    g.region -d -u -g | grep -E "^[nswe]="
    mkdir plain points corrected both
    t.rast.out.vtk input=temperature_monthly directory=plain null=-9999 \
        where="name = 'temperature_monthly_2020_01'"
    t.rast.out.vtk -p input=temperature_monthly directory=points null=-9999 \
        where="name = 'temperature_monthly_2020_01'"
    t.rast.out.vtk -c input=temperature_monthly directory=corrected null=-9999 \
        where="name = 'temperature_monthly_2020_01'"
    t.rast.out.vtk -p -c input=temperature_monthly directory=both null=-9999 \
        where="name = 'temperature_monthly_2020_01'"
    for directory in plain points corrected both; do
        echo $directory
        sed -n 5,8p $directory/000000_temperature_monthly.vtk
    done
    ```

    ```text
    n=320000
    s=10000
    w=120000
    e=935000
    plain
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600000.000000 208000.000000 0.000000
    CELL_DATA 6
    points
    DIMENSIONS 3 2 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600500.000000 208500.000000 0.000000
    POINT_DATA 6
    corrected
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 72500.000000 43000.000000 0.000000
    CELL_DATA 6
    both
    DIMENSIONS 3 2 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 73000.000000 43500.000000 0.000000
    POINT_DATA 6
    ```

=== "Python (grass.tools)"

    ```python
    default_region = tools.g_region(flags="dug").keyval
    for key in ("n", "s", "w", "e"):
        print(f"{key}={default_region[key]}")
    for directory, flags in (
        ("plain", ""),
        ("points", "p"),
        ("corrected", "c"),
        ("both", "pc"),
    ):
        Path(directory).mkdir()
        tools.t_rast_out_vtk(
            input="temperature_monthly",
            directory=directory,
            flags=flags,
            null=-9999,
            where="name = 'temperature_monthly_2020_01'",
        )
        print(directory)
        path = Path(directory, "000000_temperature_monthly.vtk")
        print("\n".join(path.read_text().splitlines()[4:8]))
    ```

    ```text
    n=320000
    s=10000
    w=120000
    e=935000
    plain
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600000.000000 208000.000000 0.000000
    CELL_DATA 6
    points
    DIMENSIONS 3 2 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 600500.000000 208500.000000 0.000000
    POINT_DATA 6
    corrected
    DIMENSIONS 4 3 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 72500.000000 43000.000000 0.000000
    CELL_DATA 6
    both
    DIMENSIONS 3 2 1
    SPACING 1000.000000 1000.000000 0.000000
    ORIGIN 73000.000000 43500.000000 0.000000
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
    t.rast.out.vtk input=temperature_monthly directory=vtk 2>&1 | grep "exists" || true
    t.rast.out.vtk --overwrite input=temperature_monthly directory=vtk
    ls vtk | wc -l
    ```

    ```text
    ERROR: option <output>: <000000_temperature_monthly.vtk> exists. To overwrite, use the --overwrite flag
    12
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import ToolError

    try:
        tools.t_rast_out_vtk(input="temperature_monthly", directory="vtk")
    except ToolError as error:
        print([line for line in error.stderr.splitlines() if "exists" in line][0])
    tools.t_rast_out_vtk(input="temperature_monthly", directory="vtk", overwrite=True)
    print(len(list(Path("vtk").iterdir())))
    ```

    ```text
    ERROR: option <output>: <000000_temperature_monthly.vtk> exists. To overwrite, use the --overwrite flag
    12
    ```

### Write a dataset of another mapset with relative time

The dataset `runoff` has relative time and two maps with the constant values 1
and 2 in the mapset `t_rast_out_vtk`: the simulated runoff in millimeters in
model hours 0 to 1 and 1 to 2. The example switches to the mapset
`t_rast_out_vtk_2`, which starts with the default region of the sample
dataset, so it sets the region again. The mapset `t_rast_out_vtk` is added to
the search path, and the call names the dataset with its mapset. The files are
numbered as for absolute time.

=== "Command line"

    ```sh
    for step in 1 2; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2 start=0 increment=1 unit=hours
    g.mapset -c mapset=t_rast_out_vtk_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapsets mapset=t_rast_out_vtk operation=add
    g.region n=210000 s=208000 w=600000 e=603000 res=1000
    mkdir model
    t.rast.out.vtk input=runoff@t_rast_out_vtk directory=model
    ls model
    ```

    ```text
    000000_runoff.vtk
    000001_runoff.vtk
    ```

=== "Python (grass.tools)"

    ```python
    for step in (1, 2):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    tools.t_register(
        input="runoff",
        maps="runoff_1,runoff_2",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.g_mapset(flags="c", mapset="t_rast_out_vtk_2")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapsets(mapset="t_rast_out_vtk", operation="add")
    tools.g_region(n=210000, s=208000, w=600000, e=603000, res=1000)
    Path("model").mkdir()
    tools.t_rast_out_vtk(input="runoff@t_rast_out_vtk", directory="model")
    print("\n".join(sorted(path.name for path in Path("model").iterdir())))
    ```

    ```text
    000000_runoff.vtk
    000001_runoff.vtk
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.mapset](g.mapset.md), [g.mapsets](g.mapsets.md),
[g.region](g.region.md), [r.out.vtk](r.out.vtk.md),
[t.create](t.create.md), [t.rast.export](t.rast.export.md),
[t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
