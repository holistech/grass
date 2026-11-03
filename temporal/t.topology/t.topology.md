## DESCRIPTION

*t.topology* reports the temporal topology of a space time dataset (STRDS,
STR3DS or STVDS; see the
[introduction to temporal data processing](temporalintro.md)): whether the
maps follow each other without overlap, how many maps are time points or
intervals, how many gaps lie between them, and which temporal relation holds
between which maps. It tells whether a dataset has a valid topology and
where it has not. The dataset is read only; *t.topology* changes nothing.

The option **input** names the dataset and **type** its type: `strds` (the
default), `str3ds` or `stvds`. A dataset is found by its type and name, so a
name that belongs to a dataset of another type is not found. The option
**where** is an SQL condition on the table of the registered maps, for
example `start_time >= '2026-06-02'` or `name != 'c'`; *t.topology* then looks
at the selected maps only. It uses the time of the maps and of the dataset in
absolute and in relative time alike.

Without a flag *t.topology* prints a summary in three parts. The first part,
**Basic information**, shows the same lines as the basic information of
*[t.info](t.info.md)*.
The second part, **Temporal topology**, has these lines:

- `Is subset of dataset` is `True` if **where** is given and `False`
  otherwise, also if the condition selects all maps.
- `Temporal topology is` is `valid` if no two of the maps are equal, overlap,
  or lie in each other. A pair that touches (`Follows`, `Precedes`) or has a
  gap between them is allowed, as are time points. It is `invalid` if a
  pair of maps breaks the rule; the next part tells which relations. No maps
  break no rule, so the topology of an empty selection is `valid`.
- `Number of points` counts the maps that have a start time only and
  `Number of intervals` those that have a start and an end time.
  `Invalid time stamps` counts the maps without a start time.
- `Number of gaps` counts the neighbours in the order of the start times of
  which the later one starts after the earlier one has ended.
- `Granularity` is the time step of the maps, for example `1 day`. In relative
  time it is a number without a unit. It is `None` if there are no maps.

The third part, **Topological relations**, counts the pairs of maps by their
temporal relation. Each pair counts twice, once for each map as the point of
view: a pair that touches counts as one `Follows` and one `Precedes`, a pair
of maps with the same times as two `Equal`. A pair that does not touch and
does not overlap, because there is a gap, is not counted. The counts are:

- `Equal`: the maps have the same start and end time.
- `Follows` and `Precedes`: the end of one map is the start of the other.
- `Overlaps` and `Overlapped`: the maps share a part of their time, but
  neither lies in the other.
- `During` and `Contains`: one map lies in the other.
- `Starts` and `Started`: the maps start together and the first ends earlier;
  `Finishes` and `Finished`: the maps end together and the first starts later.
  A pair of this kind is counted as `During` and `Contains`, too.

Without maps the part has no count lines.

The flag **-m** prints, instead of the summary, an entry for each selected map
in the order of the start times, with the basic information, the time, the
spatial extent and the metadata of the map. Its section **Temporal Topology**
has a line for the next and the previous map in time (`Next`, `Previous`) and
one line for each temporal relation that holds for the map, with the identifiers
of the other maps. A relation line reads from the map to the maps it names:
`Overlaps: b` in the entry of the map `a` says that `a` overlaps `b`. Only maps
of the selection are named. The flag **-s** does the same and adds the spatial
relations of the map to the other maps: `Equivalent`, `Cover`, `Covered`,
`Overlap`, `In`, `Contain` and `Meet`. With **-s** a map is listed with another
one only if the two maps are related in time and in space; a map that has no
spatial relation to a map is not listed with its temporal relation either. The
spatial relations of a STRDS are computed from the 2D extent of its maps (west,
east, south, north), those of a STR3DS and a STVDS from the 3D extent (with
bottom and top). **-s** prints the same as **-m** and **-s** together. Both
flags print no summary.

## NOTES

A map that has an end time before its start time cannot be registered, but
a database that was edited by hand can hold one. *t.topology* warns about each
such map with its identifier and treats it as a map without time: it has no
relations, the other maps are related as if it were not there, and the
granularity leaves it out. A map without a start time comes last in the
listing of **-m** and **-s**. *t.topology* ends without an error in
both cases.

An empty dataset or a **where** condition that selects no map is not an error.
The summary shows the topology as `valid`, zero counts, the granularity
`None` and no count lines for the relations.

A **where** condition with a syntax error stops *t.topology* with the error
`Invalid where condition <...>` and the message of the database.

The times in **where** are compared as text in absolute time: `start_time >=
'2026-06-02'` selects as expected, whereas `start_time = '2026-06-02'` selects
nothing, because the stored value is `2026-06-02 00:00:00`. Select a single map
by `name = '...'`.

A dataset that does not exist stops *t.topology* with an error such as `Space
time dataset <nope> of type <strds> not found`.

Datasets of relative time and of the other types work in the same way; the
last example shows a relative time dataset and a vector dataset. A dataset of
another mapset of the search path is found by its name, and `name@mapset` names
it explicitly.

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_topology` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset.
*t.topology* looks at times and extents only, so the maps hold small constant
values and the dates are chosen to show each relation.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_topology -->

<!-- markdownlint-disable MD046 -->

### Check a dataset whose maps follow each other

The dataset `rain_days` holds four maps of daily rain, 4 mm in every cell, one
day each, one after the other. The summary shows the topology as valid, four
intervals, no gap and the granularity `1 day`. Three pairs of neighbours touch,
which are counted as three `Follows` and three `Precedes`. The box above the
summary is the basic information of the dataset.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_topology
    g.region raster=elev_state_500m res=1000 -a
    for day in 1 2 3 4; do
        r.mapcalc expression="rain_day_$day = 4"
    done
    t.create output=rain_days title="Daily rain" \
        description="Four adjacent days of rain in mm"
    t.register -i input=rain_days \
        maps=rain_day_1,rain_day_2,rain_day_3,rain_day_4 \
        start=2026-06-01 increment="1 day"
    t.topology input=rain_days
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_days@t_topology
     | Name: ...................... rain_days
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 3
     | Precedes: .................. 3
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_mapset(flags="c", mapset="t_topology")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for day in range(1, 5):
        tools.r_mapcalc(expression=f"rain_day_{day} = 4")
    tools.t_create(
        output="rain_days",
        title="Daily rain",
        description="Four adjacent days of rain in mm",
    )
    tools.t_register(
        input="rain_days",
        maps="rain_day_1,rain_day_2,rain_day_3,rain_day_4",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_topology(input="rain_days").stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ rain_days@t_topology
     | Name: ...................... rain_days
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 0
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 3
     | Precedes: .................. 3
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

### Find overlaps, equal times and gaps

The dataset `moisture` has the map `moisture_a` from 1 June to 3 June, the maps
`moisture_b` and `moisture_c` with the same times from 2 June to 4 June, and the
map `moisture_d` from 6 June to 7 June. The map `moisture_a` overlaps
`moisture_b` and `moisture_c`, which `Overlaps` and `Overlapped` count as two
pairs each. `moisture_b` and `moisture_c` are equal; the one pair is counted
twice, as `Equal: 2`. The gap before `moisture_d` is the one gap. The topology
is invalid because of the overlaps and the equal maps.

=== "Command line"

    ```sh
    for name in a b c d; do
        r.mapcalc expression="moisture_$name = 30"
    done
    t.create output=moisture title="Soil moisture" \
        description="Soil moisture in percent: overlap, equal times, a gap"
    t.register input=moisture maps=moisture_a start=2026-06-01 end=2026-06-03
    t.register input=moisture maps=moisture_b,moisture_c \
        start=2026-06-02 end=2026-06-04
    t.register input=moisture maps=moisture_d start=2026-06-06 end=2026-06-07
    t.topology input=moisture
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture@t_topology
     | Name: ...................... moisture
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... invalid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 2
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 2
     | Overlapped: ................ 2
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    for name in ("a", "b", "c", "d"):
        tools.r_mapcalc(expression=f"moisture_{name} = 30")
    tools.t_create(
        output="moisture",
        title="Soil moisture",
        description="Soil moisture in percent: overlap, equal times, a gap",
    )
    tools.t_register(
        input="moisture", maps="moisture_a", start="2026-06-01", end="2026-06-03"
    )
    tools.t_register(
        input="moisture",
        maps="moisture_b,moisture_c",
        start="2026-06-02",
        end="2026-06-04",
    )
    tools.t_register(
        input="moisture", maps="moisture_d", start="2026-06-06", end="2026-06-07"
    )
    print(tools.t_topology(input="moisture").stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture@t_topology
     | Name: ...................... moisture
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... invalid
     | Number of points: .......... 0
     | Number of intervals: ....... 4
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 2
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 2
     | Overlapped: ................ 2
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

### Check a part of a dataset

The condition selects the maps `moisture_a` and `moisture_d` of the dataset
`moisture`. The two maps do not touch, so no relation is counted, the one gap
between them remains, and the topology of the selection is valid. The line `Is
subset of dataset` is `True`.

=== "Command line"

    ```sh
    t.topology input=moisture where="name in ('moisture_a', 'moisture_d')"
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture@t_topology
     | Name: ...................... moisture
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... True
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 2
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    result = tools.t_topology(
        input="moisture", where="name in ('moisture_a', 'moisture_d')"
    )
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture@t_topology
     | Name: ...................... moisture
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... True
     | Temporal topology is: ...... valid
     | Number of points: .......... 0
     | Number of intervals: ....... 2
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1 day
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 0
     | Overlapped: ................ 0
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
    ```

### List the relations of each map

With **-m**, *t.topology* prints the information of each map instead of the
summary. The listing is long, so the first block of each tab keeps only the
lines with the identifier of the map and with its neighbours and relations, for
the maps `moisture_a`, `moisture_b` and `moisture_d`; `moisture_c` is left out
with **where**, because it has the same start time as `moisture_b`, and maps
with the same start time have no fixed order. `moisture_a` is followed by
`moisture_b`, which it overlaps, and `moisture_b` is followed by `moisture_d`,
after a gap. The second block selects the single map `moisture_a` and prints the
whole entry: without other maps in the selection it has no neighbours and no
relations.

=== "Command line"

    ```sh
    t.topology -m input=moisture where="name != 'moisture_c'" | grep -E "^ \| (Id|Next|Previous|Equal|Overlaps|Overlapped|During|Contains|Follows|Precedes|Starts|Started|Finishes|Finished):"
    t.topology -m input=moisture where="name = 'moisture_a'"
    ```

    ```text
     | Id: ........................ moisture_a@t_topology
     | Next: ...................... moisture_b@t_topology
     | Overlaps: .................. moisture_b@t_topology
     | Id: ........................ moisture_b@t_topology
     | Next: ...................... moisture_d@t_topology
     | Previous: .................. moisture_a@t_topology
     | Overlapped: ................ moisture_a@t_topology
     | Id: ........................ moisture_d@t_topology
     | Previous: .................. moisture_b@t_topology
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture_a@t_topology
     | Name: ...................... moisture_a
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-06-01 00:00:00
     | End time:................... 2026-06-03 00:00:00
     +-------------------- Temporal Topology -------------------------------------+
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:.. .................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 839
     | Number of rows:............. 335
     | Number of cells:............ 281065
     | North-South resolution:..... 1000.0
     | East-west resolution:....... 1000.0
     | Minimum value:.............. 30.0
     | Maximum value:.............. 30.0
     | Semantic label:............. None
     | Registered datasets ........ moisture@t_topology
     +----------------------------------------------------------------------------+
    ```

=== "Python (grass.tools)"

    ```python
    import re

    TEMPORAL = (
        "Id|Next|Previous|Equal|Overlaps|Overlapped|During|Contains|Follows"
        "|Precedes|Starts|Started|Finishes|Finished"
    )


    def print_lines(result, labels):
        """Print the lines of a listing that start with one of the labels"""
        for line in result.stdout.splitlines():
            if re.match(rf" \| ({labels}):", line):
                print(line)


    print_lines(
        tools.t_topology(input="moisture", flags="m", where="name != 'moisture_c'"),
        TEMPORAL,
    )
    result = tools.t_topology(input="moisture", flags="m", where="name = 'moisture_a'")
    print(result.stdout, end="")
    ```

    ```text
     | Id: ........................ moisture_a@t_topology
     | Next: ...................... moisture_b@t_topology
     | Overlaps: .................. moisture_b@t_topology
     | Id: ........................ moisture_b@t_topology
     | Next: ...................... moisture_d@t_topology
     | Previous: .................. moisture_a@t_topology
     | Overlapped: ................ moisture_a@t_topology
     | Id: ........................ moisture_d@t_topology
     | Previous: .................. moisture_b@t_topology
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ moisture_a@t_topology
     | Name: ...................... moisture_a
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-06-01 00:00:00
     | End time:................... 2026-06-03 00:00:00
     +-------------------- Temporal Topology -------------------------------------+
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 319000.0
     | South:...................... -16000.0
     | East:.. .................... 963000.0
     | West:....................... 124000.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 839
     | Number of rows:............. 335
     | Number of cells:............ 281065
     | North-South resolution:..... 1000.0
     | East-west resolution:....... 1000.0
     | Minimum value:.............. 30.0
     | Maximum value:.............. 30.0
     | Semantic label:............. None
     | Registered datasets ........ moisture@t_topology
     +----------------------------------------------------------------------------+
    ```

### Include the spatial relations

The dataset `scenes` holds three maps of one day each, one after the other:
`scene_big` covers a square of 4 km by 4 km, `scene_small` is a square of 2 km
by 2 km inside it, and `scene_far` is a second square of 4 km by 4 km that
lies apart from `scene_big` and has no common area with `scene_small`. The
maps get the extent of the region that is current when they are created. The
first block
lists the temporal relations with **-m**: `scene_big` precedes `scene_small`,
which precedes `scene_far`. The second block adds the spatial ones with **-s**:
`scene_big` contains `scene_small` and `scene_small` is in `scene_big`.
`scene_far` and `scene_small` are related in time but disjoint in space, so the
listing of **-s** has no `Follows` line for `scene_far` and no `Precedes` line
naming `scene_far` for `scene_small`; only the chain of `Next` and `Previous`
stays.

=== "Command line"

    ```sh
    g.region n=104000 s=100000 e=204000 w=200000 res=1000
    r.mapcalc expression="scene_big = 1"
    g.region n=103000 s=101000 e=203000 w=201000 res=1000
    r.mapcalc expression="scene_small = 1"
    g.region n=110000 s=106000 e=210000 w=206000 res=1000
    r.mapcalc expression="scene_far = 1"
    t.create output=scenes title="Scenes" \
        description="Maps of different extents"
    t.register -i input=scenes maps=scene_big,scene_small,scene_far \
        start=2026-06-01 increment="1 day"
    t.topology -m input=scenes | grep -E "^ \| (Id|Next|Previous|Equal|Overlaps|Overlapped|During|Contains|Follows|Precedes|Starts|Started|Finishes|Finished):"
    t.topology -s input=scenes | grep -E "^ \| (Id|Next|Previous|Follows|Precedes|Equivalent|Cover|Covered|Overlap|In|Contain|Meet):"
    ```

    ```text
     | Id: ........................ scene_big@t_topology
     | Next: ...................... scene_small@t_topology
     | Precedes: .................. scene_small@t_topology
     | Id: ........................ scene_small@t_topology
     | Next: ...................... scene_far@t_topology
     | Previous: .................. scene_big@t_topology
     | Follows: ................... scene_big@t_topology
     | Precedes: .................. scene_far@t_topology
     | Id: ........................ scene_far@t_topology
     | Previous: .................. scene_small@t_topology
     | Follows: ................... scene_small@t_topology
     | Id: ........................ scene_big@t_topology
     | Next: ...................... scene_small@t_topology
     | Precedes: .................. scene_small@t_topology
     | Contain: ................... scene_small@t_topology
     | Id: ........................ scene_small@t_topology
     | Next: ...................... scene_far@t_topology
     | Previous: .................. scene_big@t_topology
     | Follows: ................... scene_big@t_topology
     | In: ........................ scene_big@t_topology
     | Id: ........................ scene_far@t_topology
     | Previous: .................. scene_small@t_topology
    ```

=== "Python (grass.tools)"

    ```python
    for name, north, south, east, west in (
        ("scene_big", 104000, 100000, 204000, 200000),
        ("scene_small", 103000, 101000, 203000, 201000),
        ("scene_far", 110000, 106000, 210000, 206000),
    ):
        tools.g_region(n=north, s=south, e=east, w=west, res=1000)
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="scenes", title="Scenes", description="Maps of different extents")
    tools.t_register(
        input="scenes",
        maps="scene_big,scene_small,scene_far",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print_lines(tools.t_topology(input="scenes", flags="m"), TEMPORAL)
    SPATIAL = (
        "Id|Next|Previous|Follows|Precedes|Equivalent|Cover|Covered|Overlap|In|Contain|Meet"
    )
    print_lines(tools.t_topology(input="scenes", flags="s"), SPATIAL)
    ```

    ```text
     | Id: ........................ scene_big@t_topology
     | Next: ...................... scene_small@t_topology
     | Precedes: .................. scene_small@t_topology
     | Id: ........................ scene_small@t_topology
     | Next: ...................... scene_far@t_topology
     | Previous: .................. scene_big@t_topology
     | Follows: ................... scene_big@t_topology
     | Precedes: .................. scene_far@t_topology
     | Id: ........................ scene_far@t_topology
     | Previous: .................. scene_small@t_topology
     | Follows: ................... scene_small@t_topology
     | Id: ........................ scene_big@t_topology
     | Next: ...................... scene_small@t_topology
     | Precedes: .................. scene_small@t_topology
     | Contain: ................... scene_small@t_topology
     | Id: ........................ scene_small@t_topology
     | Next: ...................... scene_far@t_topology
     | Previous: .................. scene_big@t_topology
     | Follows: ................... scene_big@t_topology
     | In: ........................ scene_big@t_topology
     | Id: ........................ scene_far@t_topology
     | Previous: .................. scene_small@t_topology
    ```

### Relative time and vector datasets

The dataset `runoff` has relative time in hours. The maps `runoff_1` from 0 to 2
and `runoff_2` from 1 to 3 overlap, and `runoff_3` from 6 to 7 lies after a gap.
The summary counts the overlap and the gap, and the granularity is the number
`1` without a unit. The dataset `gauges` is a vector dataset; its maps
`gauge_1` and `gauge_2` follow each other and have the same point. **type=stvds**
selects the type, and **-s** lists the two maps as spatially equivalent.

=== "Command line"

    ```sh
    g.region raster=elev_state_500m res=1000 -a
    for step in 1 2 3; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register input=runoff maps=runoff_1 start=0 end=2 unit=hours
    t.register input=runoff maps=runoff_2 start=1 end=3 unit=hours
    t.register input=runoff maps=runoff_3 start=6 end=7 unit=hours
    t.topology type=strds input=runoff
    for name in gauge_1 gauge_2; do
        v.in.ascii input=- output=$name separator=comma \
            columns="x double precision, y double precision" <<EOF
    205000,105000
    EOF
    done
    t.create type=stvds output=gauges title="Gauges" description="One point"
    t.register -i type=vector input=gauges maps=gauge_1,gauge_2 \
        start=2026-06-01 increment="1 day"
    t.topology -s type=stvds input=gauges | grep -E "^ \| (Id|Next|Previous|Follows|Precedes|Equivalent|Cover|Covered|Overlap|In|Contain|Meet):"
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ runoff@t_topology
     | Name: ...................... runoff
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. relative
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... invalid
     | Number of points: .......... 0
     | Number of intervals: ....... 3
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 1
     | Overlapped: ................ 1
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
     | Id: ........................ gauge_1@t_topology
     | Next: ...................... gauge_2@t_topology
     | Precedes: .................. gauge_2@t_topology
     | Equivalent: ................ gauge_2@t_topology
     | Id: ........................ gauge_2@t_topology
     | Previous: .................. gauge_1@t_topology
     | Follows: ................... gauge_1@t_topology
     | Equivalent: ................ gauge_1@t_topology
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for step in (1, 2, 3):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    for name, start, end in (("runoff_1", 0, 2), ("runoff_2", 1, 3), ("runoff_3", 6, 7)):
        tools.t_register(input="runoff", maps=name, start=start, end=end, unit="hours")
    print(tools.t_topology(type="strds", input="runoff").stdout, end="")
    for name in ("gauge_1", "gauge_2"):
        tools.v_in_ascii(
            input=StringIO("205000,105000\n"),
            output=name,
            separator="comma",
            columns="x double precision, y double precision",
        )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="One point")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauge_1,gauge_2",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print_lines(tools.t_topology(type="stvds", input="gauges", flags="s"), SPATIAL)
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ runoff@t_topology
     | Name: ...................... runoff
     | Mapset: .................... t_topology
     | Creator: ................... user
     | Temporal type: ............. relative
     | Creation time: ............. 2026-11-01 12:00:00
     | Modification time:.......... 2026-11-01 12:00:00
     | Semantic type:.............. mean
     +-------------------- Temporal topology -------------------------------------+
     | Is subset of dataset: ...... False
     | Temporal topology is: ...... invalid
     | Number of points: .......... 0
     | Number of intervals: ....... 3
     | Invalid time stamps: ....... 0
     | Number of gaps: ............ 1
     | Granularity: ............... 1
     +-------------------- Topological relations ---------------------------------+
     | Equal:...................... 0
     | Follows: ................... 0
     | Precedes: .................. 0
     | Overlaps: .................. 1
     | Overlapped: ................ 1
     | During: .................... 0
     | Contains: .................. 0
     | Starts: .................... 0
     | Started: ................... 0
     | Finishes: .................. 0
     | Finished: .................. 0
    +----------------------------------------------------------------------------+
     | Id: ........................ gauge_1@t_topology
     | Next: ...................... gauge_2@t_topology
     | Precedes: .................. gauge_2@t_topology
     | Equivalent: ................ gauge_2@t_topology
     | Id: ........................ gauge_2@t_topology
     | Previous: .................. gauge_1@t_topology
     | Follows: ................... gauge_1@t_topology
     | Equivalent: ................ gauge_1@t_topology
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
