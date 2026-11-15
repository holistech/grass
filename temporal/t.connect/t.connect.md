## DESCRIPTION

*t.connect* prints or sets the connection to the temporal database of the
current mapset. The temporal database stores the space time datasets and the
registered maps of the mapset; see the
[introduction to temporal data processing](temporalintro.md) for the concepts
and *[t.info](t.info.md)* and *[t.list](t.list.md)* for what the database
holds. Like *[db.connect](db.connect.md)* for the attribute tables of vector
maps, *t.connect* only handles the connection parameters: the driver and the
database. It does not read or create the temporal database.

A connection has two parts. The **driver** is the database back end: `sqlite`
(the default) or `pg` for PostgreSQL. The **database** is the name of the
database for that driver: for `sqlite` the path of a file, for `pg` a
connection string such as `dbname=grass_test host=localhost`. The default
connection is the driver `sqlite` with the database
`$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db`: a file in the directory
`tgis` of the current mapset, apart from the SQLite files that hold the
attribute tables of vector maps. The variables `$GISDBASE`, `$LOCATION_NAME`
and `$MAPSET` are replaced by the values of the session when the temporal
database is opened, so the same setting works in every mapset.

*t.connect* does one of four things: it prints the connection (**-p** or
**-g**), checks it (**-c**), resets it to the default (**-d**), or sets the
**driver** and **database** that are given. The first three are chosen with a
flag; without any flag, *t.connect* sets the connection.

### Printing the connection

The flag **-p** prints the connection of the current mapset and ends. The
option **format** chooses the form of the output:

- `plain` (the default) prints the lines `driver:sqlite` and
  `database:<database>`;
- `shell` prints the lines `driver=sqlite` and `database=<database>`, which a
  shell script can read;
- `json` prints a JSON array with one object per mapset, with the keys
  `mapset`, `driver` and `database`.

The **format** option needs **-p**. A mapset that has no connection yet, as a
new mapset has until a connection is set, prints empty values in `plain` and
`shell` and `null` in `json`.

Without **mapset**, `json` reports the mapsets of the current search path, in
the order of the path. The option **mapset** changes that. It takes a list of
mapset names, with two special values: `.` is the current mapset and `*` is
every mapset of the project, whether on the search path or not. The mapsets
are printed in the order of the list; `*` stands for the mapsets in no defined
order. The option **mapset** needs **-p** and **format=json**, because
`plain` and `shell` print the connection of one mapset. A mapset that does
not exist is reported with a warning and with `null` for driver and
database.

The flag **-g** is the old way to ask for `format=shell`. It prints like **-p**
with `format=shell`, but is deprecated and will be removed in a future release;
use **-p format=shell**. **-g** cannot be combined with `format=json`.

With **-p**, the options **driver** and **database** are ignored: nothing is
set.

### Checking and resetting the connection

The flag **-c** checks whether the connection of the current mapset is set. If
neither driver nor database is set, **-c** sets the default connection and
reports it in a message. If both are set, **-c** keeps them and prints nothing.
If only one of the two is set, **-c** stops with the error `Default TGIS driver
is not set` or `Default TGIS database is not set` and changes nothing; the
pair must be repaired by setting both.

The flag **-d** sets the default connection in any case, overwriting a
connection that exists, and reports it in a message. It takes precedence over
**driver** and **database**.

**-p** and **-g** cannot be combined with **-c** or **-d**.

### Setting the connection

Without a flag, *t.connect* stores the options **driver** and **database** as
the connection of the current mapset. Each has a default (see above), and an
option that is not given is set to its default, as in *db.connect*: a call with
only **database** sets the driver to `sqlite`, a call with only **driver** sets
the database to the default file of the mapset, and a call without any option
sets both. To change one value and keep the other, give both. A **database**
that consists only of spaces is refused with `Option <database> must not be
empty.`, and the connection stays as it was.

## NOTES

Setting the connection stores the values in the `VAR` file of the mapset. The
connection is not tested, and no connection to the database is made. *t.connect*
does not create the temporal database either: the first run of a tool that
creates a space time dataset (*[t.create](t.create.md)*) creates it.

Every mapset has a connection of its own, and one that is set in a mapset does
not change the connection of another. A PostgreSQL connection has to be set
explicitly in every mapset that is to store temporal information in it.

With tens of thousands of maps to register, or when several processes write
to the temporal database at the same time, consider a PostgreSQL connection
instead of SQLite.

The values are stored with at most 4094 characters; a longer value is cut
without a message when it is read back.

Errors that the examples do not show:

- `The -p flag is required when using the format option.` for `format=shell`
  or `format=json` without **-p**;
- `Option <mapset> requires <-p>` and `The mapset option requires
  format=json.` for **mapset** without **-p** or without `format=json`;
- `The -g flag cannot be used with format=json.`;
- `Options <-p> and <-c> are mutually exclusive`, and the same for **-p** with
  **-d** and for **-g** with **-c** or **-d**.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). *t.connect*
changes the connection of the current mapset, so the first example creates the
mapset `t_connect` and every example runs in it or in `t_connect_2`; the
mapset `PERMANENT` of the dataset keeps its connection. *t.connect* handles
connections only and reads no map, so the examples need no data besides the
computational region, which they set to North Carolina with cells of 1 km.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_connect -->

<!-- markdownlint-disable MD046 -->

### Print the connection

A new mapset has no connection yet: **-p** prints empty values. **-c** finds
nothing set, sets the default connection and reports it in a message, which is
not part of the standard output. After that, **-p** prints the connection in
the form `plain`, and `format=shell` in the form `shell`. The deprecated flag
**-g** prints the same as `-p format=shell`. A second **-c** keeps the
connection and prints nothing.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_connect
    g.region raster=elev_state_500m res=1000 -a
    t.connect -p
    ```

    ```text
    driver:
    database:
    ```

    ```sh
    t.connect -c
    t.connect -p
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

    ```sh
    t.connect -c
    ```

    ```sh
    t.connect -p format=shell
    ```

    ```text
    driver=sqlite
    database=$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

    ```sh
    t.connect -g
    ```

    ```text
    driver=sqlite
    database=$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_connect")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:
    database:
    ```

    ```python
    tools.t_connect(flags="c")
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

    ```python
    tools.t_connect(flags="c")
    ```

    ```python
    print(tools.t_connect(flags="p", format="shell").text)
    ```

    ```text
    driver=sqlite
    database=$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

    ```python
    print(tools.t_connect(flags="g").text)
    ```

    ```text
    driver=sqlite
    database=$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

### Print and check the connection of several mapsets

The JSON form lists the mapsets on the search path. In the sample dataset
that includes `PERMANENT`, which has a connection of its own that is not the
subject here, so the first call selects the current mapset with `.`. JSON
escapes the slashes in the path with a backslash. The example creates a second
mapset `t_connect_2`, which has no connection yet and is not on the search path
of `t_connect`. The option **mapset** selects mapsets by name: `t_connect_2`
and `.` (the current mapset) are printed in this order, and `t_connect_2` has
`null` for driver and database. Then **-c** is run in `t_connect_2`: it finds
nothing set and sets the default connection, so the same call now prints it.
`*` stands for all mapsets of the project, `PERMANENT` among them; the last
call keeps the two mapsets of the example and sorts their names because the
order of `*` is not defined.

=== "Command line"

    ```sh
    t.connect -p format=json mapset=.
    ```

    ```text
    [
        {
            "mapset": "t_connect",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```sh
    g.mapset -c mapset=t_connect_2
    g.region raster=elev_state_500m res=1000 -a
    g.mapset mapset=t_connect
    t.connect -p format=json mapset=t_connect_2,.
    ```

    ```text
    [
        {
            "mapset": "t_connect_2",
            "driver": null,
            "database": null
        },
        {
            "mapset": "t_connect",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```sh
    g.mapset mapset=t_connect_2
    t.connect -c
    g.mapset mapset=t_connect
    t.connect -p format=json mapset=t_connect_2
    ```

    ```text
    [
        {
            "mapset": "t_connect_2",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```sh
    t.connect -p format=json mapset='*' | grep -o '"mapset": "t_connect[^"]*"' | LC_ALL=C sort
    ```

    ```text
    "mapset": "t_connect"
    "mapset": "t_connect_2"
    ```

=== "Python (grass.tools)"

    ```python
    print(tools.t_connect(flags="p", format="json", mapset=".").text)
    ```

    ```text
    [
        {
            "mapset": "t_connect",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```python
    tools.g_mapset(mapset="t_connect_2", flags="c")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    tools.g_mapset(mapset="t_connect")
    print(tools.t_connect(flags="p", format="json", mapset="t_connect_2,.").text)
    ```

    ```text
    [
        {
            "mapset": "t_connect_2",
            "driver": null,
            "database": null
        },
        {
            "mapset": "t_connect",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```python
    tools.g_mapset(mapset="t_connect_2")
    tools.t_connect(flags="c")
    tools.g_mapset(mapset="t_connect")
    print(tools.t_connect(flags="p", format="json", mapset="t_connect_2").text)
    ```

    ```text
    [
        {
            "mapset": "t_connect_2",
            "driver": "sqlite",
            "database": "$GISDBASE\/$LOCATION_NAME\/$MAPSET\/tgis\/sqlite.db"
        }
    ]
    ```

    ```python
    result = tools.t_connect(flags="p", format="json", mapset="*")
    for name in sorted(entry["mapset"] for entry in result.json):
        if name.startswith("t_connect"):
            print(f'"mapset": "{name}"')
    ```

    ```text
    "mapset": "t_connect"
    "mapset": "t_connect_2"
    ```

### Use a database file of your own

With **driver** and **database** the connection is set to a SQLite file of your
choice. The single quotes keep the shell from replacing the variables; the
temporal tools replace them when they open the database. The file is created by
the first tool that needs it, here *t.create*; *t.info* with **-d** shows the
path of the file in use. A call with only **database** sets the driver to its
default `sqlite`.

=== "Command line"

    ```sh
    t.connect driver=sqlite database='$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db'
    t.connect -p
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db
    ```

    ```sh
    t.create output=demo title="Demo" description="A dataset in mine.db"
    t.info -d | grep "database string"
    ```

    ```text
     | Temporal database string:... /home/user/grassdata/nc_spm_08_grass7/t_connect/tgis/mine.db
    ```

    ```sh
    t.connect database='$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/other.db'
    t.connect -p
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/other.db
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_connect(
        driver="sqlite",
        database="$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db",
    )
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/mine.db
    ```

    ```python
    tools.t_create(output="demo", title="Demo", description="A dataset in mine.db")
    for line in tools.t_info(flags="d").stdout.splitlines():
        if "database string" in line:
            print(line)
    ```

    ```text
     | Temporal database string:... /home/user/grassdata/nc_spm_08_grass7/t_connect/tgis/mine.db
    ```

    ```python
    tools.t_connect(database="$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/other.db")
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/other.db
    ```

### Reset the connection to the default

**-d** replaces the connection by the default one, whatever it was, and
reports it in a message.

=== "Command line"

    ```sh
    t.connect -d
    t.connect -p
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

=== "Python (grass.tools)"

    ```python
    tools.t_connect(flags="d")
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:sqlite
    database:$GISDBASE/$LOCATION_NAME/$MAPSET/tgis/sqlite.db
    ```

### Connect to PostgreSQL

With the driver `pg`, the **database** is a connection string of PostgreSQL.
The connection has to be set in every mapset that is to use it. *t.connect*
does not test it. This example needs a PostgreSQL server and is not run with
the other examples. Run it last: it changes the connection of the mapset, and
**-d** returns to SQLite.

=== "Command line"

    <!-- example: requires=postgresql -->

    ```sh
    t.connect driver=pg database="dbname=grass_test host=localhost"
    t.connect -p
    ```

    ```text
    driver:pg
    database:dbname=grass_test host=localhost
    ```

=== "Python (grass.tools)"

    <!-- example: requires=postgresql -->

    ```python
    tools.t_connect(driver="pg", database="dbname=grass_test host=localhost")
    print(tools.t_connect(flags="p").text)
    ```

    ```text
    driver:pg
    database:dbname=grass_test host=localhost
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[db.connect](db.connect.md), [t.create](t.create.md), [t.info](t.info.md),
[t.list](t.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Soeren Gebbert, Thünen Institute of Climate-Smart Agriculture
