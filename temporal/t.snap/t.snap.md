## DESCRIPTION

*t.snap* closes the gaps between the maps of a space time dataset: it makes
the end of every map the start of the next map. Use it to turn time instances
(maps with a start and no end) into intervals, or to give maps that overlap or
leave gaps a valid temporal topology. Raster, 3D raster and vector datasets
are supported, with absolute and relative time. The option **type** selects
the kind of the dataset: `strds` (the default), `str3ds` or `stvds`. The option
**input** names the dataset and is required. See the
[introduction to temporal data processing](temporalintro.md) for an overview,
*[t.register](t.register.md)* for giving maps their time and
*[t.shift](t.shift.md)* for moving the maps of a dataset in time.

*t.snap* takes the maps in the order of their start times. The end of each map
becomes the start of the following map, whatever the map had before: a time
instance gets an end, a gap before the next map is closed, and an interval that
reaches into the next map is cut at its start. The start times do not change.

The last map has no following map. If it is an interval, it keeps its end. If
it is a time instance, it ends one granularity of the dataset after its start.
The granularity is the one the dataset has before the call, as *[t.info](t.info.md)*
shows it (the largest step that fits all start and end times of the maps).
In a dataset with absolute time, a granularity of months or years is added as
calendar months, so maps on the first of January, February, March and April
give a last map that ends on May 1. A dataset with a single time instance has no
granularity, and the map stays a time instance.

Maps that start at the same time cannot be snapped to each other, as the end
of one would be its own start. A map keeps its own end if the map taken after
it starts at the same time. Which of two such maps is taken first is not
defined. When two maps start together and a map that starts later follows, one
of them keeps its end and the other one ends at the start of that later map.
Such maps have to be removed or changed to make the topology of the dataset
valid.

After the call the dataset is recomputed from its maps: if all maps are
intervals now, *[t.info](t.info.md)* shows the temporal type of the maps as
`interval` instead of `point`, and the end time of the dataset is the end of
the last map. The time belongs to the map, not to the dataset: a map that is
registered in more than one dataset is snapped in all of them, and these
datasets are recomputed as well.

A second call changes nothing, as the maps are adjacent after the first one.

## NOTES

Relative time works as absolute time, with the unit of the dataset: the last
time instance ends one granularity, a number of that unit, after its start.

*t.snap* writes the new times into the temporal database, so the dataset has
to belong to the current mapset. For a dataset of another mapset, also for an
empty one, the tool stops with the error `Unable to snap dataset <name@mapset>
of type strds in the temporal database. The mapset of the database does not
match the current mapset`, and nothing changes.

A dataset is found by its type and name: a call with a type that does not fit
the name stops with `Space time dataset <name> of type <stvds> not found`, as
does an unknown name. Give **type=stvds** or **type=str3ds** for the other
kinds of datasets.

A dataset without maps is left as it is, and the call ends without an error.
Otherwise the call is added to the command history of the dataset (see the
flag **-h** of *[t.info](t.info.md)*).

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Turn time instances into intervals

Four maps are registered on the first day of January to April 2026 with an
increment of one month. As *[t.register](t.register.md)* is called without
**-i**, they are time instances: their end time is `None`, and *[t.info](t.info.md)*
shows the temporal type of the maps as `point`. The granularity of the dataset
is `1 month`. After *t.snap* each map ends on the first of the next month and
the last map ends one month after its start, on May 1, which is also the end of
the dataset. The maps are intervals now. The granularity is the same as before.
A second call of *t.snap* does not change the list.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    for step in 1 2 3 4; do
        r.mapcalc expression="monthly_$step = $step"
    done
    t.create output=monthly title="Monthly maps" \
        description="One map on the first day of each month"
    t.register input=monthly maps=monthly_1,monthly_2,monthly_3,monthly_4 \
        start=2026-01-01 increment="1 months"
    t.rast.list input=monthly columns=name,start_time,end_time
    t.info -g input=monthly | grep -E "^(end_time|granularity|map_time)="
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|None
    monthly_2|2026-02-01 00:00:00|None
    monthly_3|2026-03-01 00:00:00|None
    monthly_4|2026-04-01 00:00:00|None
    end_time='2026-04-01 00:00:00'
    granularity='1 month'
    map_time=point
    ```

    ```sh
    t.snap type=strds input=monthly
    t.rast.list input=monthly columns=name,start_time,end_time
    t.info -g input=monthly | grep -E "^(end_time|granularity|map_time)="
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|2026-02-01 00:00:00
    monthly_2|2026-02-01 00:00:00|2026-03-01 00:00:00
    monthly_3|2026-03-01 00:00:00|2026-04-01 00:00:00
    monthly_4|2026-04-01 00:00:00|2026-05-01 00:00:00
    end_time='2026-05-01 00:00:00'
    granularity='1 month'
    map_time=interval
    ```

    ```sh
    t.snap input=monthly
    t.rast.list input=monthly columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|2026-02-01 00:00:00
    monthly_2|2026-02-01 00:00:00|2026-03-01 00:00:00
    monthly_3|2026-03-01 00:00:00|2026-04-01 00:00:00
    monthly_4|2026-04-01 00:00:00|2026-05-01 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def print_extent(name):
        info = tools.t_info(input=name, flags="g").keyval
        for key in ("end_time", "granularity", "map_time"):
            print(f"{key}={info[key]}")


    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"monthly_{step} = {step}")
    tools.t_create(
        output="monthly",
        title="Monthly maps",
        description="One map on the first day of each month",
    )
    tools.t_register(
        input="monthly",
        maps="monthly_1,monthly_2,monthly_3,monthly_4",
        start="2026-01-01",
        increment="1 months",
    )
    print(tools.t_rast_list(input="monthly", columns="name,start_time,end_time").text)
    print_extent("monthly")
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|None
    monthly_2|2026-02-01 00:00:00|None
    monthly_3|2026-03-01 00:00:00|None
    monthly_4|2026-04-01 00:00:00|None
    end_time='2026-04-01 00:00:00'
    granularity='1 month'
    map_time=point
    ```

    ```python
    tools.t_snap(type="strds", input="monthly")
    print(tools.t_rast_list(input="monthly", columns="name,start_time,end_time").text)
    print_extent("monthly")
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|2026-02-01 00:00:00
    monthly_2|2026-02-01 00:00:00|2026-03-01 00:00:00
    monthly_3|2026-03-01 00:00:00|2026-04-01 00:00:00
    monthly_4|2026-04-01 00:00:00|2026-05-01 00:00:00
    end_time='2026-05-01 00:00:00'
    granularity='1 month'
    map_time=interval
    ```

    ```python
    tools.t_snap(input="monthly")
    print(tools.t_rast_list(input="monthly", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    monthly_1|2026-01-01 00:00:00|2026-02-01 00:00:00
    monthly_2|2026-02-01 00:00:00|2026-03-01 00:00:00
    monthly_3|2026-03-01 00:00:00|2026-04-01 00:00:00
    monthly_4|2026-04-01 00:00:00|2026-05-01 00:00:00
    ```

### Instances at uneven distances

Three maps are time instances on June 1, 3 and 7, 2026. The steps between them
are two and four days, so the granularity of the dataset is `2 days`. Each map
ends where the next one starts, the last one ends two days after its start, on
June 9. The intervals have different lengths; *t.snap* does not make them equal.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="uneven_$step = $step"
    done
    t.create output=uneven title="Uneven maps" \
        description="Three maps at uneven distances"
    t.register input=uneven maps=uneven_1 start=2026-06-01
    t.register input=uneven maps=uneven_2 start=2026-06-03
    t.register input=uneven maps=uneven_3 start=2026-06-07
    t.info -g input=uneven | grep -E "^(granularity|map_time)="
    t.snap input=uneven
    t.rast.list input=uneven columns=name,start_time,end_time
    t.info -g input=uneven | grep -E "^(end_time|granularity|map_time)="
    ```

    ```text
    granularity='2 days'
    map_time=point
    name|start_time|end_time
    uneven_1|2026-06-01 00:00:00|2026-06-03 00:00:00
    uneven_2|2026-06-03 00:00:00|2026-06-07 00:00:00
    uneven_3|2026-06-07 00:00:00|2026-06-09 00:00:00
    end_time='2026-06-09 00:00:00'
    granularity='2 days'
    map_time=interval
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"uneven_{step} = {step}")
    tools.t_create(
        output="uneven",
        title="Uneven maps",
        description="Three maps at uneven distances",
    )
    for step, start in ((1, "2026-06-01"), (2, "2026-06-03"), (3, "2026-06-07")):
        tools.t_register(input="uneven", maps=f"uneven_{step}", start=start)
    info = tools.t_info(input="uneven", flags="g").keyval
    for key in ("granularity", "map_time"):
        print(f"{key}={info[key]}")
    tools.t_snap(input="uneven")
    print(tools.t_rast_list(input="uneven", columns="name,start_time,end_time").text)
    print_extent("uneven")
    ```

    ```text
    granularity='2 days'
    map_time=point
    name|start_time|end_time
    uneven_1|2026-06-01 00:00:00|2026-06-03 00:00:00
    uneven_2|2026-06-03 00:00:00|2026-06-07 00:00:00
    uneven_3|2026-06-07 00:00:00|2026-06-09 00:00:00
    end_time='2026-06-09 00:00:00'
    granularity='2 days'
    map_time=interval
    ```

### Close gaps and cut overlaps between intervals

Four maps are intervals: `gap_1` from June 1 to 2, `gap_2` from June 4 to 8,
`gap_3` from June 6 to 7 and `gap_4` from June 10 to 12. There is a gap after
`gap_1` and after `gap_3`, and `gap_2` reaches into `gap_3`. The method
`deltagaps` of *[t.rast.list](t.rast.list.md)* lists the gaps as lines without
a name. After *t.snap* each map ends where the next one starts: `gap_1` ends on
June 4, `gap_2` on June 6, `gap_3` on June 10. The last map `gap_4` has an
end of its own and keeps it. The list has no gaps now, and `gap_3` is longer
than before.

=== "Command line"

    ```sh
    for step in 1 2 3 4; do
        r.mapcalc expression="gap_$step = $step"
    done
    t.create output=gaps title="Intervals with gaps" \
        description="Four intervals with two gaps and one overlap"
    t.register input=gaps maps=gap_1 start=2026-06-01 end=2026-06-02
    t.register input=gaps maps=gap_2 start=2026-06-04 end=2026-06-08
    t.register input=gaps maps=gap_3 start=2026-06-06 end=2026-06-07
    t.register input=gaps maps=gap_4 start=2026-06-10 end=2026-06-12
    t.rast.list input=gaps method=deltagaps columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    gap_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    None|2026-06-02 00:00:00|2026-06-04 00:00:00
    gap_2|2026-06-04 00:00:00|2026-06-08 00:00:00
    gap_3|2026-06-06 00:00:00|2026-06-07 00:00:00
    None|2026-06-07 00:00:00|2026-06-10 00:00:00
    gap_4|2026-06-10 00:00:00|2026-06-12 00:00:00
    ```

    ```sh
    t.snap input=gaps
    t.rast.list input=gaps method=deltagaps columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    gap_1|2026-06-01 00:00:00|2026-06-04 00:00:00
    gap_2|2026-06-04 00:00:00|2026-06-06 00:00:00
    gap_3|2026-06-06 00:00:00|2026-06-10 00:00:00
    gap_4|2026-06-10 00:00:00|2026-06-12 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 5):
        tools.r_mapcalc(expression=f"gap_{step} = {step}")
    tools.t_create(
        output="gaps",
        title="Intervals with gaps",
        description="Four intervals with two gaps and one overlap",
    )
    for step, start, end in (
        (1, "2026-06-01", "2026-06-02"),
        (2, "2026-06-04", "2026-06-08"),
        (3, "2026-06-06", "2026-06-07"),
        (4, "2026-06-10", "2026-06-12"),
    ):
        tools.t_register(input="gaps", maps=f"gap_{step}", start=start, end=end)
    columns = "name,start_time,end_time"
    print(tools.t_rast_list(input="gaps", method="deltagaps", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    gap_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    None|2026-06-02 00:00:00|2026-06-04 00:00:00
    gap_2|2026-06-04 00:00:00|2026-06-08 00:00:00
    gap_3|2026-06-06 00:00:00|2026-06-07 00:00:00
    None|2026-06-07 00:00:00|2026-06-10 00:00:00
    gap_4|2026-06-10 00:00:00|2026-06-12 00:00:00
    ```

    ```python
    tools.t_snap(input="gaps")
    print(tools.t_rast_list(input="gaps", method="deltagaps", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    gap_1|2026-06-01 00:00:00|2026-06-04 00:00:00
    gap_2|2026-06-04 00:00:00|2026-06-06 00:00:00
    gap_3|2026-06-06 00:00:00|2026-06-10 00:00:00
    gap_4|2026-06-10 00:00:00|2026-06-12 00:00:00
    ```

### Snap a dataset with relative time

Three maps are time instances at the hours 0, 3 and 5 of a model run. The steps
are three and two hours, so the granularity is 1. The unit of the dataset is
`hours`, and the last map ends at hour 6. The times are numbers of that unit.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="step_$step = $step"
    done
    t.create output=model temporaltype=relative title="Model run" \
        description="Output at the hours 0, 3 and 5"
    t.register input=model maps=step_1 start=0 unit=hours
    t.register input=model maps=step_2 start=3 unit=hours
    t.register input=model maps=step_3 start=5 unit=hours
    t.snap input=model
    t.rast.list input=model columns=name,start_time,end_time
    t.info -g input=model | grep -E "^(end_time|granularity|map_time|unit)="
    ```

    ```text
    name|start_time|end_time
    step_1|0|3
    step_2|3|5
    step_3|5|6
    end_time='6'
    unit=hours
    granularity=1
    map_time=interval
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"step_{step} = {step}")
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model run",
        description="Output at the hours 0, 3 and 5",
    )
    for step, start in ((1, 0), (2, 3), (3, 5)):
        tools.t_register(input="model", maps=f"step_{step}", start=start, unit="hours")
    tools.t_snap(input="model")
    print(tools.t_rast_list(input="model", columns=columns).text)
    info = tools.t_info(input="model", flags="g").keyval
    for key in ("end_time", "unit", "granularity", "map_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time
    step_1|0|3
    step_2|3|5
    step_3|5|6
    end_time='6'
    unit=hours
    granularity=1
    map_time=interval
    ```

### Snap a map that is in more than one dataset

The dataset `all` holds the time instances `shared_1` (June 1), `shared_2`
(June 2) and `shared_3` (June 4); the dataset `part` holds `shared_1` and
`shared_2` as well. The granularity of `all` is `1 day`. Snapping `all` gives
the maps their ends: June 2, June 4 and June 5. Because the time belongs to
the map, `part` is snapped too, although it was not named: its maps are
intervals now, `shared_2` ending on June 4 although `part` has no map after it,
and the end time of `part` follows.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="shared_$step = $step"
    done
    t.create output=all title="All maps" description="Three time instances"
    t.register input=all maps=shared_1 start=2026-06-01
    t.register input=all maps=shared_2 start=2026-06-02
    t.register input=all maps=shared_3 start=2026-06-04
    t.create output=part title="Part of the maps" description="The first two maps"
    t.register input=part maps=shared_1,shared_2 start=2026-06-01 \
        increment="1 day"
    t.info -g input=part | grep -E "^(end_time|map_time)="
    ```

    ```text
    end_time='2026-06-02 00:00:00'
    map_time=point
    ```

    ```sh
    t.snap input=all
    t.rast.list input=all columns=name,start_time,end_time
    t.rast.list input=part columns=name,start_time,end_time
    t.info -g input=part | grep -E "^(end_time|map_time)="
    ```

    ```text
    name|start_time|end_time
    shared_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    shared_2|2026-06-02 00:00:00|2026-06-04 00:00:00
    shared_3|2026-06-04 00:00:00|2026-06-05 00:00:00
    name|start_time|end_time
    shared_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    shared_2|2026-06-02 00:00:00|2026-06-04 00:00:00
    end_time='2026-06-04 00:00:00'
    map_time=interval
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"shared_{step} = {step}")
    tools.t_create(output="all", title="All maps", description="Three time instances")
    for step, start in ((1, "2026-06-01"), (2, "2026-06-02"), (3, "2026-06-04")):
        tools.t_register(input="all", maps=f"shared_{step}", start=start)
    tools.t_create(
        output="part", title="Part of the maps", description="The first two maps"
    )
    tools.t_register(
        input="part",
        maps="shared_1,shared_2",
        start="2026-06-01",
        increment="1 day",
    )
    info = tools.t_info(input="part", flags="g").keyval
    for key in ("end_time", "map_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    end_time='2026-06-02 00:00:00'
    map_time=point
    ```

    ```python
    tools.t_snap(input="all")
    print(tools.t_rast_list(input="all", columns=columns).text)
    print(tools.t_rast_list(input="part", columns=columns).text)
    info = tools.t_info(input="part", flags="g").keyval
    for key in ("end_time", "map_time"):
        print(f"{key}={info[key]}")
    ```

    ```text
    name|start_time|end_time
    shared_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    shared_2|2026-06-02 00:00:00|2026-06-04 00:00:00
    shared_3|2026-06-04 00:00:00|2026-06-05 00:00:00
    name|start_time|end_time
    shared_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    shared_2|2026-06-02 00:00:00|2026-06-04 00:00:00
    end_time='2026-06-04 00:00:00'
    map_time=interval
    ```

### Snap 3D raster and vector datasets

The option **type** selects the kind of the dataset. Two 3D raster maps are
registered on June 1 and June 2, 2026 and two vector maps on the same days.
After *t.snap* with `type=str3ds` and `type=stvds`, the first map of each
dataset ends on June 2 and the second one day later, on June 3.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=2 w=0 t=3 b=0 res=1 res3=1 tbres=1
    r3.mapcalc expression="soil_1 = depth()"
    r3.mapcalc expression="soil_2 = depth() + 10"
    t.create type=str3ds output=soil title="Soil" \
        description="Soil temperature in three layers"
    t.register type=raster_3d input=soil maps=soil_1,soil_2 \
        start=2026-06-01 increment="1 day"
    for name in gauges_1 gauges_2; do
        v.in.ascii input=- output=$name separator=comma \
            columns="x double precision, y double precision, speed double precision" \
            <<EOF
    0.5,0.5,3.0
    2.5,1.5,5.0
    EOF
    done
    t.create type=stvds output=gauges title="Gauges" \
        description="Wind speed at two gauges"
    t.register type=vector input=gauges maps=gauges_1,gauges_2 \
        start=2026-06-01 increment="1 day"
    ```

    ```sh
    t.snap type=str3ds input=soil
    t.snap type=stvds input=gauges
    t.rast3d.list input=soil columns=name,start_time,end_time
    t.vect.list input=gauges columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    soil_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    soil_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    name|start_time|end_time
    gauges_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    gauges_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    from io import StringIO

    tools.g_region(n=2, s=0, e=2, w=0, t=3, b=0, res=1, res3=1, tbres=1)
    tools.r3_mapcalc(expression="soil_1 = depth()")
    tools.r3_mapcalc(expression="soil_2 = depth() + 10")
    tools.t_create(
        type="str3ds",
        output="soil",
        title="Soil",
        description="Soil temperature in three layers",
    )
    tools.t_register(
        type="raster_3d",
        input="soil",
        maps="soil_1,soil_2",
        start="2026-06-01",
        increment="1 day",
    )
    for name in ("gauges_1", "gauges_2"):
        tools.v_in_ascii(
            input=StringIO("0.5,0.5,3.0\n2.5,1.5,5.0\n"),
            output=name,
            separator="comma",
            columns="x double precision, y double precision, speed double precision",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Gauges",
        description="Wind speed at two gauges",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2",
        start="2026-06-01",
        increment="1 day",
    )
    ```

    ```python
    tools.t_snap(type="str3ds", input="soil")
    tools.t_snap(type="stvds", input="gauges")
    print(tools.t_rast3d_list(input="soil", columns=columns).text)
    print(tools.t_vect_list(input="gauges", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    soil_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    soil_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    name|start_time|end_time
    gauges_1|2026-06-01 00:00:00|2026-06-02 00:00:00
    gauges_2|2026-06-02 00:00:00|2026-06-03 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.info](t.info.md), [t.rast.list](t.rast.list.md),
[t.register](t.register.md), [t.shift](t.shift.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
