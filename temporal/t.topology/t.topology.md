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

<!-- markdownlint-disable MD046 -->

### Check a dataset whose maps follow each other

The dataset `days` holds four maps of one day each, one after the other.
The summary shows the topology as valid, four intervals, no gap and the
granularity `1 day`. Three pairs of neighbours touch, which are counted as
three `Follows` and three `Precedes`. The box above the summary is the basic
information of the dataset.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for name in day_1 day_2 day_3 day_4; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=days title="Days" description="Four adjacent days"
    t.register -i input=days maps=day_1,day_2,day_3,day_4 \
        start=2026-06-01 increment="1 day"
    t.topology input=days
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ days@PERMANENT
     | Name: ...................... days
     | Mapset: .................... PERMANENT
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
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for name in ("day_1", "day_2", "day_3", "day_4"):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="days", title="Days", description="Four adjacent days")
    tools.t_register(
        input="days",
        maps="day_1,day_2,day_3,day_4",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_topology(input="days").stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ days@PERMANENT
     | Name: ...................... days
     | Mapset: .................... PERMANENT
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

The dataset `mixed` has the map `a` from 1 June to 3 June, the maps `b` and
`c` with the same times from 2 June to 4 June, and the map `d` from 6 June to
7 June. The map `a` overlaps `b` and `c`, which `Overlaps` and `Overlapped`
count as two pairs each. `b` and `c` are equal; the one pair is counted twice,
as `Equal: 2`. The gap before `d` is the one gap. The topology is invalid
because of the overlaps and the equal maps.

=== "Command line"

    ```sh
    for name in a b c d; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=mixed title="Mixed" description="Overlap, equal times, a gap"
    t.register input=mixed maps=a start=2026-06-01 end=2026-06-03
    t.register input=mixed maps=b,c start=2026-06-02 end=2026-06-04
    t.register input=mixed maps=d start=2026-06-06 end=2026-06-07
    t.topology input=mixed
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ mixed@PERMANENT
     | Name: ...................... mixed
     | Mapset: .................... PERMANENT
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
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="mixed", title="Mixed", description="Overlap, equal times, a gap")
    tools.t_register(input="mixed", maps="a", start="2026-06-01", end="2026-06-03")
    tools.t_register(input="mixed", maps="b,c", start="2026-06-02", end="2026-06-04")
    tools.t_register(input="mixed", maps="d", start="2026-06-06", end="2026-06-07")
    print(tools.t_topology(input="mixed").stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ mixed@PERMANENT
     | Name: ...................... mixed
     | Mapset: .................... PERMANENT
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

The condition selects the maps `a` and `d` of the dataset `mixed`. The two
maps do not touch, so no relation is counted, the one gap between them
remains, and the topology of the selection is valid. The line `Is subset of
dataset` is `True`.

=== "Command line"

    ```sh
    t.topology input=mixed where="name in ('a', 'd')"
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ mixed@PERMANENT
     | Name: ...................... mixed
     | Mapset: .................... PERMANENT
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
    result = tools.t_topology(input="mixed", where="name in ('a', 'd')")
    print(result.stdout, end="")
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ mixed@PERMANENT
     | Name: ...................... mixed
     | Mapset: .................... PERMANENT
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
the maps `a`, `b` and `d`; `c` is left out with **where**, because it has the
same start time as `b`, and maps with the same start time have no fixed order.
`a` is followed by `b`, which it overlaps, and `b` is followed by `d`, after a
gap. The second block selects the single map `a` and prints the whole entry:
without other maps in the selection it has no neighbours and no relations.

=== "Command line"

    ```sh
    t.topology -m input=mixed where="name != 'c'" | grep -E "^ \| (Id|Next|Previous|Equal|Overlaps|Overlapped|During|Contains|Follows|Precedes|Starts|Started|Finishes|Finished):"
    t.topology -m input=mixed where="name = 'a'"
    ```

    ```text
     | Id: ........................ a@PERMANENT
     | Next: ...................... b@PERMANENT
     | Overlaps: .................. b@PERMANENT
     | Id: ........................ b@PERMANENT
     | Next: ...................... d@PERMANENT
     | Previous: .................. a@PERMANENT
     | Overlapped: ................ a@PERMANENT
     | Id: ........................ d@PERMANENT
     | Previous: .................. b@PERMANENT
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ a@PERMANENT
     | Name: ...................... a
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-06-01 00:00:00
     | End time:................... 2026-06-03 00:00:00
     +-------------------- Temporal Topology -------------------------------------+
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 3
     | Number of rows:............. 2
     | Number of cells:............ 6
     | North-South resolution:..... 1.0
     | East-west resolution:....... 1.0
     | Minimum value:.............. 1.0
     | Maximum value:.............. 1.0
     | Semantic label:............. None
     | Registered datasets ........ mixed@PERMANENT
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


    print_lines(tools.t_topology(input="mixed", flags="m", where="name != 'c'"), TEMPORAL)
    result = tools.t_topology(input="mixed", flags="m", where="name = 'a'")
    print(result.stdout, end="")
    ```

    ```text
     | Id: ........................ a@PERMANENT
     | Next: ...................... b@PERMANENT
     | Overlaps: .................. b@PERMANENT
     | Id: ........................ b@PERMANENT
     | Next: ...................... d@PERMANENT
     | Previous: .................. a@PERMANENT
     | Overlapped: ................ a@PERMANENT
     | Id: ........................ d@PERMANENT
     | Previous: .................. b@PERMANENT
     +-------------------- Raster Dataset ----------------------------------------+
     |                                                                            |
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ a@PERMANENT
     | Name: ...................... a
     | Mapset: .................... PERMANENT
     | Creator: ................... user
     | Temporal type: ............. absolute
     | Creation time: ............. 2026-11-01 12:00:00
     +-------------------- Absolute time -----------------------------------------+
     | Start time:................. 2026-06-01 00:00:00
     | End time:................... 2026-06-03 00:00:00
     +-------------------- Temporal Topology -------------------------------------+
     +-------------------- Spatial extent ----------------------------------------+
     | North:...................... 2.0
     | South:...................... 0.0
     | East:.. .................... 3.0
     | West:....................... 0.0
     | Top:........................ 0.0
     | Bottom:..................... 0.0
     +-------------------- Metadata information ----------------------------------+
     | Datatype:................... CELL
     | Number of columns:.......... 3
     | Number of rows:............. 2
     | Number of cells:............ 6
     | North-South resolution:..... 1.0
     | East-west resolution:....... 1.0
     | Minimum value:.............. 1.0
     | Maximum value:.............. 1.0
     | Semantic label:............. None
     | Registered datasets ........ mixed@PERMANENT
     +----------------------------------------------------------------------------+
    ```

### Include the spatial relations

The dataset `scenes` holds three maps of one day each, one after the other:
`big` covers 0 to 4 in both directions, `small` lies inside it, and `far` lies
at 4 to 8 and has no common area with `small`. The maps get the extent of the
region that is current when they are created. The first block lists the temporal
relations with **-m**: `big` precedes `small`, which precedes `far`. The second
block adds the spatial ones with **-s**: `big` contains `small` and `small` is
in `big`. `far` and `small` are related in time but disjoint in space, so the
listing of **-s** has no `Follows` line for `far` and no `Precedes` line naming
`far` for `small`; only the chain of `Next` and `Previous` stays.

=== "Command line"

    ```sh
    g.region n=4 s=0 e=4 w=0 res=1
    r.mapcalc expression="big = 1"
    g.region n=2 s=1 e=3 w=1 res=1
    r.mapcalc expression="small = 1"
    g.region n=8 s=4 e=8 w=4 res=1
    r.mapcalc expression="far = 1"
    t.create output=scenes title="Scenes" description="Maps of different extents"
    t.register -i input=scenes maps=big,small,far start=2026-06-01 increment="1 day"
    t.topology -m input=scenes | grep -E "^ \| (Id|Next|Previous|Equal|Overlaps|Overlapped|During|Contains|Follows|Precedes|Starts|Started|Finishes|Finished):"
    t.topology -s input=scenes | grep -E "^ \| (Id|Next|Previous|Follows|Precedes|Equivalent|Cover|Covered|Overlap|In|Contain|Meet):"
    ```

    ```text
     | Id: ........................ big@PERMANENT
     | Next: ...................... small@PERMANENT
     | Precedes: .................. small@PERMANENT
     | Id: ........................ small@PERMANENT
     | Next: ...................... far@PERMANENT
     | Previous: .................. big@PERMANENT
     | Follows: ................... big@PERMANENT
     | Precedes: .................. far@PERMANENT
     | Id: ........................ far@PERMANENT
     | Previous: .................. small@PERMANENT
     | Follows: ................... small@PERMANENT
     | Id: ........................ big@PERMANENT
     | Next: ...................... small@PERMANENT
     | Precedes: .................. small@PERMANENT
     | Contain: ................... small@PERMANENT
     | Id: ........................ small@PERMANENT
     | Next: ...................... far@PERMANENT
     | Previous: .................. big@PERMANENT
     | Follows: ................... big@PERMANENT
     | In: ........................ big@PERMANENT
     | Id: ........................ far@PERMANENT
     | Previous: .................. small@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    for name, north, south, east, west in (
        ("big", 4, 0, 4, 0),
        ("small", 2, 1, 3, 1),
        ("far", 8, 4, 8, 4),
    ):
        tools.g_region(n=north, s=south, e=east, w=west, res=1)
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(output="scenes", title="Scenes", description="Maps of different extents")
    tools.t_register(
        input="scenes",
        maps="big,small,far",
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
     | Id: ........................ big@PERMANENT
     | Next: ...................... small@PERMANENT
     | Precedes: .................. small@PERMANENT
     | Id: ........................ small@PERMANENT
     | Next: ...................... far@PERMANENT
     | Previous: .................. big@PERMANENT
     | Follows: ................... big@PERMANENT
     | Precedes: .................. far@PERMANENT
     | Id: ........................ far@PERMANENT
     | Previous: .................. small@PERMANENT
     | Follows: ................... small@PERMANENT
     | Id: ........................ big@PERMANENT
     | Next: ...................... small@PERMANENT
     | Precedes: .................. small@PERMANENT
     | Contain: ................... small@PERMANENT
     | Id: ........................ small@PERMANENT
     | Next: ...................... far@PERMANENT
     | Previous: .................. big@PERMANENT
     | Follows: ................... big@PERMANENT
     | In: ........................ big@PERMANENT
     | Id: ........................ far@PERMANENT
     | Previous: .................. small@PERMANENT
    ```

### Relative time and vector datasets

The dataset `model` has relative time in hours. The maps `s1` from 0 to 2
and `s2` from 1 to 3 overlap, and `s3` from 6 to 7 lies after a gap. The summary
counts the overlap and the gap, and the granularity is the number `1` without
a unit. The dataset `gauges` is a vector dataset; its maps `g1` and `g2` follow
each other and have the same point. **type=stvds** selects the type, and **-s**
lists the two maps as spatially equivalent.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for name in s1 s2 s3; do
        r.mapcalc expression="$name = 1"
    done
    t.create output=model temporaltype=relative title="Model" description="Steps"
    t.register input=model maps=s1 start=0 end=2 unit=hours
    t.register input=model maps=s2 start=1 end=3 unit=hours
    t.register input=model maps=s3 start=6 end=7 unit=hours
    t.topology type=strds input=model
    for name in g1 g2; do
        v.in.ascii input=- output=$name separator=comma \
            columns="x double precision, y double precision" <<EOF
    0.5,0.5
    EOF
    done
    t.create type=stvds output=gauges title="Gauges" description="One point"
    t.register -i type=vector input=gauges maps=g1,g2 \
        start=2026-06-01 increment="1 day"
    t.topology -s type=stvds input=gauges | grep -E "^ \| (Id|Next|Previous|Follows|Precedes|Equivalent|Cover|Covered|Overlap|In|Contain|Meet):"
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ model@PERMANENT
     | Name: ...................... model
     | Mapset: .................... PERMANENT
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
     | Id: ........................ g1@PERMANENT
     | Next: ...................... g2@PERMANENT
     | Precedes: .................. g2@PERMANENT
     | Equivalent: ................ g2@PERMANENT
     | Id: ........................ g2@PERMANENT
     | Previous: .................. g1@PERMANENT
     | Follows: ................... g1@PERMANENT
     | Equivalent: ................ g1@PERMANENT
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for name in ("s1", "s2", "s3"):
        tools.r_mapcalc(expression=f"{name} = 1")
    tools.t_create(
        output="model", temporaltype="relative", title="Model", description="Steps"
    )
    for name, start, end in (("s1", 0, 2), ("s2", 1, 3), ("s3", 6, 7)):
        tools.t_register(input="model", maps=name, start=start, end=end, unit="hours")
    print(tools.t_topology(type="strds", input="model").stdout, end="")
    for name in ("g1", "g2"):
        tools.v_in_ascii(
            input=StringIO("0.5,0.5\n"),
            output=name,
            separator="comma",
            columns="x double precision, y double precision",
        )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="One point")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="g1,g2",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    print_lines(tools.t_topology(type="stvds", input="gauges", flags="s"), SPATIAL)
    ```

    ```text
     +-------------------- Basic information -------------------------------------+
     | Id: ........................ model@PERMANENT
     | Name: ...................... model
     | Mapset: .................... PERMANENT
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
     | Id: ........................ g1@PERMANENT
     | Next: ...................... g2@PERMANENT
     | Precedes: .................. g2@PERMANENT
     | Equivalent: ................ g2@PERMANENT
     | Id: ........................ g2@PERMANENT
     | Previous: .................. g1@PERMANENT
     | Follows: ................... g1@PERMANENT
     | Equivalent: ................ g1@PERMANENT
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.region](g.region.md), [t.create](t.create.md), [t.info](t.info.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[t.vect.list](t.vect.list.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
