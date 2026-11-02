## DESCRIPTION

*t.support* changes the descriptive metadata of a space time dataset and
brings the metadata that is computed from the registered maps up to date. See
the [introduction to temporal data processing](temporalintro.md) for an
overview. The maps, their time stamps and their registration stay as they
are, with one exception: with the flag **-m** a map that is gone from the
spatial database is unregistered.

The option **input** names the dataset, and **type** gives its type: `strds`
(the default), `str3ds` or `stvds`. A dataset is found by its type and name,
so a name that belongs to a dataset of another type is not found. The
dataset may have absolute or relative time.

### Descriptive metadata

Each of the following options changes one property and leaves the others as
they are. A call with only **title**, for example, keeps the description. An
empty value changes nothing.

- **title** sets the title of the dataset.
- **description** sets its description.
- **semantictype** sets the semantic type, one of `min`, `max`, `sum` and
  `mean`. It has no default: a call without it keeps the semantic type, also
  a call with **-m** or **-u**. A new dataset made by *[t.create](t.create.md)*
  has the semantic type `mean`.
- **aggr_type** sets the aggregation type of a space time raster or 3D raster
  dataset, the name of the method that produced its maps, such as `average`.
  The text is stored as it is and not checked against the known aggregation
  methods. *[t.info](t.info.md)* shows `None` until a type is set. A space
  time vector dataset has no aggregation type: *t.support* warns about
  **aggr_type** for it, ignores it and applies the other options.

*[t.info](t.info.md)* shows the title and the description in its text output
and the semantic type and the aggregation type both in its text output and with
**-g**.

### Updating the metadata computed from the maps

A dataset keeps the values that it computes from its maps: the start and end
time, the granularity, the spatial extent, the resolutions, the range of values
and the number of maps. The flags compute them again:

- **-u** computes them again from the entries of the registered maps in the
  temporal database. It does not read the maps themselves, so a map that was
  made again without a temporal command is not seen by **-u**; use **-m** for
  it.
- **-m** reads every registered map from the spatial database again and writes
  its values (extent, resolution, range of values) into the temporal database.
  A map that is gone from the spatial database is deleted from the temporal
  database, which unregisters it from every dataset that held it. The other
  datasets that hold a map that **-m** read or removed are updated too. **-m**
  includes the work of **-u**, so the two flags are not needed together. A map
  of another mapset is read from there.

A call without **-u**, **-m** and any other option does not compute these
values again.

## NOTES

An unknown name stops the run with the error "Space time dataset `<name>` of
type `<strds>` not found". A **semantictype** other than the four values or a
**type** other than the three types is refused by the parser, which names the
legal values. A call without **input** is refused with the message that the
required parameter is not set.

The map values that **-m** reads are the ones the spatial database holds now.
For a raster dataset they are the range of values and the extent and
resolution of each map; for a vector dataset the extent. Changing a map
without **-m** or **-u** leaves the dataset as it was (see the third example).

The command history of the dataset records each call of *t.support*, which
*t.info* shows under `Command history`.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Change title, description and types

The dataset `temp` holds three maps, one per day from 2026-06-01. *t.info*
shows its title and description, the semantic type `mean` and the aggregation
type `None`.

The first call of *t.support* changes all four properties at once. The second
call gives only a title, so the description, the semantic type and the
aggregation type stay.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for n in 1 2 3; do
        r.mapcalc expression="m_$n = $n * 10"
    done
    t.create output=temp title="Old title" description="Old description"
    t.register -i input=temp maps=m_1,m_2,m_3 \
        start=2026-06-01 increment="1 day"
    t.info input=temp | grep -E "Semantic type|Aggregation type"
    t.info input=temp | grep -A3 "Title:"
    ```

    ```text
     | Semantic type:.............. mean
     | Aggregation type:........... None
     | Title:
     | Old title
     | Description:
     | Old description
    ```

    ```sh
    t.support input=temp title="Daily mean" \
        description="Mean temperature per day" \
        semantictype=sum aggr_type=average
    t.info input=temp | grep -E "Semantic type|Aggregation type"
    t.info input=temp | grep -A3 "Title:"
    t.support input=temp title="Daily temperature"
    t.info input=temp | grep -E "Semantic type|Aggregation type"
    t.info input=temp | grep -A3 "Title:"
    ```

    ```text
     | Semantic type:.............. sum
     | Aggregation type:........... average
     | Title:
     | Daily mean
     | Description:
     | Mean temperature per day
     | Semantic type:.............. sum
     | Aggregation type:........... average
     | Title:
     | Daily temperature
     | Description:
     | Mean temperature per day
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def show_metadata(name):
        lines = tools.t_info(input=name).stdout.splitlines()
        for line in lines:
            if "Semantic type" in line or "Aggregation type" in line:
                print(line)
        first = next(i for i, line in enumerate(lines) if "Title:" in line)
        print("\n".join(lines[first : first + 4]))


    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for n in range(1, 4):
        tools.r_mapcalc(expression=f"m_{n} = {n} * 10")
    tools.t_create(output="temp", title="Old title", description="Old description")
    tools.t_register(
        input="temp",
        maps="m_1,m_2,m_3",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    show_metadata("temp")
    ```

    ```text
     | Semantic type:.............. mean
     | Aggregation type:........... None
     | Title:
     | Old title
     | Description:
     | Old description
    ```

    ```python
    tools.t_support(
        input="temp",
        title="Daily mean",
        description="Mean temperature per day",
        semantictype="sum",
        aggr_type="average",
    )
    show_metadata("temp")
    tools.t_support(input="temp", title="Daily temperature")
    show_metadata("temp")
    ```

    ```text
     | Semantic type:.............. sum
     | Aggregation type:........... average
     | Title:
     | Daily mean
     | Description:
     | Mean temperature per day
     | Semantic type:.............. sum
     | Aggregation type:........... average
     | Title:
     | Daily temperature
     | Description:
     | Mean temperature per day
    ```

### Change the metadata of a vector dataset

The dataset `gauges` of type `stvds` holds one point map. The call changes the
title and gives an **aggr_type**, which a vector dataset does not have: the
module warns, which is not shown here, and applies the title. The output of
`t.info -g` has a line for the semantic type and none for the aggregation
type. Datasets of type `str3ds` are handled like those of type `strds`.

=== "Command line"

    ```sh
    echo "1.5,0.5,3.0" | v.in.ascii input=- output=gauge_1 \
        separator=comma \
        columns="x double precision, y double precision, speed double precision"
    t.create type=stvds output=gauges title="Gauges" description="Wind gauges"
    t.register -i type=vector input=gauges maps=gauge_1 \
        start=2026-06-01 increment="1 day"
    t.support type=stvds input=gauges title="Wind gauges" aggr_type=average
    t.info type=stvds input=gauges | grep -A1 "Title:"
    t.info -g type=stvds input=gauges | grep -E "^(semantic|aggregation)"
    ```

    ```text
     | Title:
     | Wind gauges
    semantic_type=mean
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.v_in_ascii(
        input=StringIO("1.5,0.5,3.0\n"),
        output="gauge_1",
        separator="comma",
        columns="x double precision, y double precision, speed double precision",
    )
    tools.t_create(type="stvds", output="gauges", title="Gauges", description="Wind gauges")
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauge_1",
        start="2026-06-01",
        increment="1 day",
        flags="i",
    )
    tools.t_support(type="stvds", input="gauges", title="Wind gauges", aggr_type="average")
    lines = tools.t_info(type="stvds", input="gauges").stdout.splitlines()
    first = next(i for i, line in enumerate(lines) if "Title:" in line)
    print("\n".join(lines[first : first + 2]))
    info = tools.t_info(type="stvds", input="gauges", flags="g").keyval
    for key in ("semantic_type", "aggregation_type"):
        if key in info:
            print(f"{key}={info[key]}")
    ```

    ```text
     | Title:
     | Wind gauges
    semantic_type=mean
    ```

### Read maps that were made again

The dataset `warm` holds the maps `m_2` and `m_3` of `temp`, with the times
they have in the temporal database. Then `m_3` is made again with the value 90.
The datasets still report the range of values from before: 10 to 30 for `temp`
and 20 to 30 for `warm`.

A call with **-u** does not change that, because **-u** works on the entries of
the temporal database and the entry of `m_3` still says 30. A call with **-m**
reads `m_3` from the spatial database. The range of `temp` becomes 10 to 90,
and `warm`, which was not named in the call but holds `m_3`, follows with 20 to
90.

=== "Command line"

    ```sh
    t.create output=warm title="Warm days" description="Days 2 and 3"
    t.register input=warm maps=m_2,m_3
    r.mapcalc --overwrite expression="m_3 = 90"
    t.support -u input=temp
    t.info -g input=temp | grep -E "^(min_min|max_max)="
    t.info -g input=warm | grep -E "^(min_min|max_max)="
    t.support -m input=temp
    t.info -g input=temp | grep -E "^(min_min|max_max)="
    t.info -g input=warm | grep -E "^(min_min|max_max)="
    ```

    ```text
    min_min=10.0
    max_max=30.0
    min_min=20.0
    max_max=30.0
    min_min=10.0
    max_max=90.0
    min_min=20.0
    max_max=90.0
    ```

=== "Python (grass.tools)"

    ```python
    def show_range(name):
        info = tools.t_info(input=name, flags="g").keyval
        for key in ("min_min", "max_max"):
            print(f"{key}={info[key]}")


    tools.t_create(output="warm", title="Warm days", description="Days 2 and 3")
    tools.t_register(input="warm", maps="m_2,m_3")
    tools.r_mapcalc(expression="m_3 = 90", overwrite=True)
    tools.t_support(input="temp", flags="u")
    show_range("temp")
    show_range("warm")
    tools.t_support(input="temp", flags="m")
    show_range("temp")
    show_range("warm")
    ```

    ```text
    min_min=10.0
    max_max=30.0
    min_min=20.0
    max_max=30.0
    min_min=10.0
    max_max=90.0
    min_min=20.0
    max_max=90.0
    ```

### Unregister maps that are gone

The map `m_2` is removed from the spatial database with *g.remove*, which
leaves it registered in `temp` and `warm`. The call with **-m** finds that it
is gone, deletes it from the temporal database and updates both datasets: `temp`
keeps `m_1` and `m_3`, `warm` keeps `m_3`. The dataset `warm` was not named in
the call. The range of values of both follows the maps that are left.

=== "Command line"

    ```sh
    g.remove -f type=raster name=m_2
    t.support -m input=temp
    t.list type=strds columns=name,number_of_maps
    t.list type=raster columns=name
    t.info -g input=temp | grep -E "^(min_min|max_max)="
    t.info -g input=warm | grep -E "^(min_min|max_max)="
    ```

    ```text
    temp|2
    warm|1
    m_1
    m_3
    min_min=10.0
    max_max=90.0
    min_min=90.0
    max_max=90.0
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_remove(type="raster", name="m_2", flags="f")
    tools.t_support(input="temp", flags="m")
    print(tools.t_list(type="strds", columns="name,number_of_maps").text)
    print(tools.t_list(type="raster", columns="name").text)
    show_range("temp")
    show_range("warm")
    ```

    ```text
    temp|2
    warm|1
    m_1
    m_3
    min_min=10.0
    max_max=90.0
    min_min=90.0
    max_max=90.0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[g.remove](g.remove.md), [t.create](t.create.md), [t.info](t.info.md),
[t.register](t.register.md), [t.unregister](t.unregister.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
