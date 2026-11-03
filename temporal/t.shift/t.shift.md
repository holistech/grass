## DESCRIPTION

*t.shift* moves all maps of a space time dataset in time by one amount. Every
map is moved by the same amount. Raster, 3D raster and vector datasets are supported;
the option **type** selects the kind of the dataset (`strds`, `str3ds` or
`stvds`, the default is `strds`). Use it to correct a wrong time reference or
to move a series onto the time axis of another one. See the
[introduction to temporal data processing](temporalintro.md) for an overview,
*[t.register](t.register.md)* for giving maps their time at the start and
*[t.snap](t.snap.md)* for closing the gaps between intervals afterwards.

The option **input** names the space time dataset, and **granularity** gives
the amount. Both are required. The start and the end of every map are moved
by the amount, each for itself; a time instance, which has no end, only moves
its start. A map keeps its kind: an interval stays an interval and an instance
stays an instance. A negative number moves the maps back in time.

### Absolute time

The granularity of an absolute dataset has the form `number unit`. The number
is an integer, and the unit is one of `years`, `months`, `weeks`, `days`,
`hours`, `minutes` or `seconds`; the singular (`1 day`) is accepted as well.
The number alone (`5`), a fraction (`1.5 days`) and an unknown unit
(`1 fortnight`) are refused.

A list of such parts separated by commas, such as `1 days, 2 hours`, moves the
maps by all parts at once. Every part has to be `number unit`, and every unit
may appear once: `1 days, 2 days` is refused instead of adding the days. Years
and months of a list form one step of `12 * years + months` months, with one
cut to the last day of the month. The parts from weeks to seconds are added
as lengths of time after that.

A step of months or years that ends behind the last day of a month ends on
that last day. A map that starts on January 31 and moves by `1 month` starts
on February 28. The start and the end are moved each for itself, so the length
of such a map can change, and a step back does not always lead to the old date.
Within a list, the step of months and years comes first: `1 months, 1 days`
turns January 31 into February 28 and then into March 1.

The time of a dataset as a whole follows its maps: the start and the end of the
dataset, and its granularity, are calculated again. A shift by 12 hours of a
dataset with daily maps gives it the granularity `24 hours` instead of `1 day`,
because the maps then start at noon and not at midnight.

### Relative time

The granularity of a relative dataset is one integer, positive, negative or
zero. It is a number of the unit that the dataset has, and the unit cannot be
changed by *t.shift*. A list, a fraction or a text with a unit is refused.

## NOTES

The time belongs to the map, not to the dataset. A map that is registered in
more than one space time dataset moves in all of them. To shift a part of a
dataset only, copy that part into new maps first:
*[t.rast.extract](t.rast.extract.md)* with the option **expression** makes new
maps in a new dataset, and the shift of that dataset does not touch the
original maps.

*t.shift* computes the new time of every map before it changes the first one.
A granularity that is refused, a shift that ends behind the year 9999 and a
list that names a unit twice therefore leave the dataset as it was. The tool
ends with these messages, among others:

- `Wrong granularity format: <granularity>` for a granularity that does not fit
  the temporal type of the dataset or that has a part which is no `number unit`;
  a second message names the dataset;
- `Each unit may appear only once in the granularity: <granularity>`;
- `Unable to shift dataset <name@mapset> by <granularity>: ...` for a shift
  behind the year 9999, which no date can express. A list names the map whose
  time cannot be shifted.

A dataset must belong to the current mapset, as *t.shift* writes the new times
into the temporal database. For a dataset of another mapset the tool ends with
a message that starts `Unable to shift dataset <name@mapset> of type strds` and
says `The mapset of the database does not match the current mapset`. The
refusal comes before anything is written, also for a dataset without maps.

A dataset without maps is left as it is, also in its command history.
*t.shift* reports that the dataset has no maps, nothing to shift, as a
message and ends without an error. Otherwise the call is added to the
command history of the dataset (see the flag **-h** of *[t.info](t.info.md)*).

## EXAMPLES

The examples run in the North Carolina sample dataset `nc_spm_08_grass7` from
the [GRASS sample data](https://grass.osgeo.org/download/data/). The first
example creates the mapset `t_shift` and sets the computational region to
North Carolina with cells of 1 km; the later examples work in this mapset and
region. *t.shift* changes times only, so the maps hold small constant values.

<!-- example-project: dataset=nc_spm_08_grass7 mapset=t_shift -->

<!-- markdownlint-disable MD046 -->

### Move the maps of a dataset by a length of time

Three maps of daily mean air temperature over North Carolina, 8, 9 and 10
degrees Celsius in every cell, form the intervals March 1 to 4, 2026. The
shift by `12 hours` moves each of them to noon. The dataset then has the
granularity `24 hours`, while it had `1 day` before. A shift by `-12 hours`
brings the maps back, and the granularity with them.

=== "Command line"

    ```sh
    g.mapset -c mapset=t_shift
    g.region raster=elev_state_500m res=1000 -a
    for day in 1 2 3; do
        r.mapcalc expression="temperature_$day = $((7 + day))"
    done
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature in degree Celsius"
    t.register -i input=temperature \
        maps=temperature_1,temperature_2,temperature_3 \
        start=2026-03-01 increment="1 day"
    t.rast.list input=temperature columns=name,start_time,end_time
    t.info -g input=temperature | grep -E "^(start_time|end_time|granularity)="
    ```

    ```text
    name|start_time|end_time
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    ```

    ```sh
    t.shift type=strds input=temperature granularity="12 hours"
    t.rast.list input=temperature columns=name,start_time,end_time
    t.info -g input=temperature | grep -E "^(start_time|end_time|granularity)="
    ```

    ```text
    name|start_time|end_time
    temperature_1|2026-03-01 12:00:00|2026-03-02 12:00:00
    temperature_2|2026-03-02 12:00:00|2026-03-03 12:00:00
    temperature_3|2026-03-03 12:00:00|2026-03-04 12:00:00
    start_time='2026-03-01 12:00:00'
    end_time='2026-03-04 12:00:00'
    granularity='24 hours'
    ```

    ```sh
    t.shift input=temperature granularity="-12 hours"
    t.info -g input=temperature | grep -E "^(start_time|end_time|granularity)="
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()


    def print_extent(name):
        info = tools.t_info(input=name, flags="g").keyval
        for key in ("start_time", "end_time", "granularity"):
            print(f"{key}={info[key]}")


    tools.g_mapset(flags="c", mapset="t_shift")
    tools.g_region(raster="elev_state_500m", res=1000, flags="a")
    for day in range(1, 4):
        tools.r_mapcalc(expression=f"temperature_{day} = {7 + day}")
    tools.t_create(
        output="temperature",
        title="Air temperature",
        description="Daily mean air temperature in degree Celsius",
    )
    tools.t_register(
        input="temperature",
        maps="temperature_1,temperature_2,temperature_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    columns = "name,start_time,end_time"
    print(tools.t_rast_list(input="temperature", columns=columns).text)
    print_extent("temperature")
    ```

    ```text
    name|start_time|end_time
    temperature_1|2026-03-01 00:00:00|2026-03-02 00:00:00
    temperature_2|2026-03-02 00:00:00|2026-03-03 00:00:00
    temperature_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    ```

    ```python
    tools.t_shift(type="strds", input="temperature", granularity="12 hours")
    print(tools.t_rast_list(input="temperature", columns=columns).text)
    print_extent("temperature")
    ```

    ```text
    name|start_time|end_time
    temperature_1|2026-03-01 12:00:00|2026-03-02 12:00:00
    temperature_2|2026-03-02 12:00:00|2026-03-03 12:00:00
    temperature_3|2026-03-03 12:00:00|2026-03-04 12:00:00
    start_time='2026-03-01 12:00:00'
    end_time='2026-03-04 12:00:00'
    granularity='24 hours'
    ```

    ```python
    tools.t_shift(input="temperature", granularity="-12 hours")
    print_extent("temperature")
    ```

    ```text
    start_time='2026-03-01 00:00:00'
    end_time='2026-03-04 00:00:00'
    granularity='1 day'
    ```

### Months that end on a shorter month

The dataset `seasons` holds two maps of seasonal mean air temperature, 4 and
12 degrees Celsius. The map `season_1` lasts from January 31 to March 31,
2001, and `season_2` from March 31 to April 30. Shifted by `1 month`,
`season_1` starts on February 28, the last day of February, and ends on
April 30, the last day of April. Its length grows from 59 to 61 days. A shift
by `-1 month` leads to January 28 and March 30, not back to the old dates.

=== "Command line"

    ```sh
    r.mapcalc expression="season_1 = 4"
    r.mapcalc expression="season_2 = 12"
    t.create output=seasons title="Seasonal temperature" \
        description="Seasonal mean air temperature in degree Celsius"
    t.register input=seasons maps=season_1 start=2001-01-31 end=2001-03-31
    t.register input=seasons maps=season_2 start=2001-03-31 end=2001-04-30
    t.shift input=seasons granularity="1 month"
    t.rast.list input=seasons columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    season_1|2001-02-28 00:00:00|2001-04-30 00:00:00
    season_2|2001-04-30 00:00:00|2001-05-30 00:00:00
    ```

    ```sh
    t.shift input=seasons granularity="-1 month"
    t.rast.list input=seasons columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    season_1|2001-01-28 00:00:00|2001-03-30 00:00:00
    season_2|2001-03-30 00:00:00|2001-04-30 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="season_1 = 4")
    tools.r_mapcalc(expression="season_2 = 12")
    tools.t_create(
        output="seasons",
        title="Seasonal temperature",
        description="Seasonal mean air temperature in degree Celsius",
    )
    tools.t_register(input="seasons", maps="season_1", start="2001-01-31", end="2001-03-31")
    tools.t_register(input="seasons", maps="season_2", start="2001-03-31", end="2001-04-30")
    tools.t_shift(input="seasons", granularity="1 month")
    print(tools.t_rast_list(input="seasons", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    season_1|2001-02-28 00:00:00|2001-04-30 00:00:00
    season_2|2001-04-30 00:00:00|2001-05-30 00:00:00
    ```

    ```python
    tools.t_shift(input="seasons", granularity="-1 month")
    print(tools.t_rast_list(input="seasons", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    season_1|2001-01-28 00:00:00|2001-03-30 00:00:00
    season_2|2001-03-30 00:00:00|2001-04-30 00:00:00
    ```

### Shift by a list of units

Four field surveys of soil moisture, each a dataset with one time instance,
show how a list is added. Every survey map holds 30 percent in every cell.
`survey_a` holds the instance February 15, 2003, and `survey_b` the same day.
The list `1 years, 1 months` and the single `13 months` give the same result,
March 15, 2004. `survey_c` holds January 31, 2001: `1 months, 1 days` first
moves to February 28 and then adds the day, so the result is March 1.
`survey_d` holds the same day: `1 months, 1 weeks` moves to February 28 and
then adds seven days, so the result is March 7. The first block creates and
registers the surveys, the second shifts and lists them, and the third moves
`survey_a` once more by the list `1 days, 2 hours`, a day and two hours.

=== "Command line"

    ```sh
    for name in a b c d; do
        r.mapcalc expression="moisture_$name = 30"
        t.create output=survey_$name title="Survey $name" \
            description="Soil moisture in percent from one field survey"
    done
    t.register input=survey_a maps=moisture_a start=2003-02-15
    t.register input=survey_b maps=moisture_b start=2003-02-15
    t.register input=survey_c maps=moisture_c start=2001-01-31
    t.register input=survey_d maps=moisture_d start=2001-01-31
    ```

    ```sh
    t.shift input=survey_a granularity="1 years, 1 months"
    t.shift input=survey_b granularity="13 months"
    t.shift input=survey_c granularity="1 months, 1 days"
    t.shift input=survey_d granularity="1 months, 1 weeks"
    for name in a b c d; do
        t.rast.list input=survey_$name columns=name,start_time,end_time
    done
    ```

    ```text
    name|start_time|end_time
    moisture_a|2004-03-15 00:00:00|None
    name|start_time|end_time
    moisture_b|2004-03-15 00:00:00|None
    name|start_time|end_time
    moisture_c|2001-03-01 00:00:00|None
    name|start_time|end_time
    moisture_d|2001-03-07 00:00:00|None
    ```

    ```sh
    t.shift input=survey_a granularity="1 days, 2 hours"
    t.rast.list input=survey_a columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    moisture_a|2004-03-16 02:00:00|None
    ```

=== "Python (grass.tools)"

    ```python
    for name in ("a", "b", "c", "d"):
        tools.r_mapcalc(expression=f"moisture_{name} = 30")
        tools.t_create(
            output=f"survey_{name}",
            title=f"Survey {name}",
            description="Soil moisture in percent from one field survey",
        )
    tools.t_register(input="survey_a", maps="moisture_a", start="2003-02-15")
    tools.t_register(input="survey_b", maps="moisture_b", start="2003-02-15")
    tools.t_register(input="survey_c", maps="moisture_c", start="2001-01-31")
    tools.t_register(input="survey_d", maps="moisture_d", start="2001-01-31")
    ```

    ```python
    tools.t_shift(input="survey_a", granularity="1 years, 1 months")
    tools.t_shift(input="survey_b", granularity="13 months")
    tools.t_shift(input="survey_c", granularity="1 months, 1 days")
    tools.t_shift(input="survey_d", granularity="1 months, 1 weeks")
    for name in ("a", "b", "c", "d"):
        print(tools.t_rast_list(input=f"survey_{name}", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    moisture_a|2004-03-15 00:00:00|None
    name|start_time|end_time
    moisture_b|2004-03-15 00:00:00|None
    name|start_time|end_time
    moisture_c|2001-03-01 00:00:00|None
    name|start_time|end_time
    moisture_d|2001-03-07 00:00:00|None
    ```

    ```python
    tools.t_shift(input="survey_a", granularity="1 days, 2 hours")
    print(tools.t_rast_list(input="survey_a", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    moisture_a|2004-03-16 02:00:00|None
    ```

### Shift a dataset with relative time

The granularity of a dataset with relative time is an integer in the unit of
the dataset. The dataset `runoff` holds the simulated runoff of a model, 1, 2
and 3 mm in the maps `runoff_1` to `runoff_3`, for the intervals 0 to 1, 1 to 2
and 2 to 3 hours. The shift by `10` moves them to the intervals 10 to 11 and
so on; the unit stays `hours`. The shift by `-3` leads to 7 to 8 and so on.

=== "Command line"

    ```sh
    for step in 1 2 3; do
        r.mapcalc expression="runoff_$step = $step"
    done
    t.create output=runoff temporaltype=relative title="Runoff" \
        description="Simulated runoff in mm per model hour"
    t.register -i input=runoff maps=runoff_1,runoff_2,runoff_3 start=0 \
        increment=1 unit=hours
    t.shift input=runoff granularity=10
    t.rast.list input=runoff columns=name,start_time,end_time
    t.info -g input=runoff | grep "^unit="
    ```

    ```text
    name|start_time|end_time
    runoff_1|10|11
    runoff_2|11|12
    runoff_3|12|13
    unit=hours
    ```

    ```sh
    t.shift input=runoff granularity=-3
    t.rast.list input=runoff columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    runoff_1|7|8
    runoff_2|8|9
    runoff_3|9|10
    ```

=== "Python (grass.tools)"

    ```python
    for step in range(1, 4):
        tools.r_mapcalc(expression=f"runoff_{step} = {step}")
    tools.t_create(
        output="runoff",
        temporaltype="relative",
        title="Runoff",
        description="Simulated runoff in mm per model hour",
    )
    tools.t_register(
        input="runoff",
        maps="runoff_1,runoff_2,runoff_3",
        start=0,
        increment=1,
        unit="hours",
        flags="i",
    )
    tools.t_shift(input="runoff", granularity=10)
    print(tools.t_rast_list(input="runoff", columns=columns).text)
    print(f"unit={tools.t_info(input='runoff', flags='g').keyval['unit']}")
    ```

    ```text
    name|start_time|end_time
    runoff_1|10|11
    runoff_2|11|12
    runoff_3|12|13
    unit=hours
    ```

    ```python
    tools.t_shift(input="runoff", granularity=-3)
    print(tools.t_rast_list(input="runoff", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    runoff_1|7|8
    runoff_2|8|9
    runoff_3|9|10
    ```

### Maps in several datasets, and a part of a dataset

The dataset `rain_all` holds the maps `rain_1` to `rain_3` of daily
precipitation, 1, 2 and 3 mm, and `rain_first` holds `rain_1` and `rain_2` by
their names. A shift of `rain_first` by `10 days` moves the two maps in both
datasets, and `rain_all` shows `rain_3` unchanged and the other two ten days
later. To move a part of a dataset only, *t.rast.extract* makes new maps: the
dataset `rain_late` holds a copy of `rain_3`, which the shift by `100 days`
moves without touching `rain_3` in `rain_all`. The extract is made with an
**expression**, which copies the map; the expression `rain_3` here is the map
itself.

=== "Command line"

    ```sh
    for day in 1 2 3; do
        r.mapcalc expression="rain_$day = $day"
    done
    t.create output=rain_all title="Precipitation" \
        description="Daily precipitation in mm, three days"
    t.register -i input=rain_all maps=rain_1,rain_2,rain_3 start=2026-03-01 \
        increment="1 day"
    t.create output=rain_first title="Precipitation" \
        description="Daily precipitation in mm, the first two days"
    t.register input=rain_first maps=rain_1,rain_2
    t.shift input=rain_first granularity="10 days"
    t.rast.list input=rain_all columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    rain_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    rain_1|2026-03-11 00:00:00|2026-03-12 00:00:00
    rain_2|2026-03-12 00:00:00|2026-03-13 00:00:00
    ```

    ```sh
    t.rast.extract input=rain_all output=rain_late basename=rain_late \
        where="name = 'rain_3'" expression="rain_3"
    t.shift input=rain_late granularity="100 days"
    t.rast.list input=rain_late columns=name,start_time,end_time
    t.rast.list input=rain_all columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    rain_late_2026_03_03|2026-06-11 00:00:00|2026-06-12 00:00:00
    name|start_time|end_time
    rain_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    rain_1|2026-03-11 00:00:00|2026-03-12 00:00:00
    rain_2|2026-03-12 00:00:00|2026-03-13 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    for day in range(1, 4):
        tools.r_mapcalc(expression=f"rain_{day} = {day}")
    tools.t_create(
        output="rain_all",
        title="Precipitation",
        description="Daily precipitation in mm, three days",
    )
    tools.t_register(
        input="rain_all",
        maps="rain_1,rain_2,rain_3",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_create(
        output="rain_first",
        title="Precipitation",
        description="Daily precipitation in mm, the first two days",
    )
    tools.t_register(input="rain_first", maps="rain_1,rain_2")
    tools.t_shift(input="rain_first", granularity="10 days")
    print(tools.t_rast_list(input="rain_all", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    rain_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    rain_1|2026-03-11 00:00:00|2026-03-12 00:00:00
    rain_2|2026-03-12 00:00:00|2026-03-13 00:00:00
    ```

    ```python
    tools.t_rast_extract(
        input="rain_all",
        output="rain_late",
        basename="rain_late",
        where="name = 'rain_3'",
        expression="rain_3",
    )
    tools.t_shift(input="rain_late", granularity="100 days")
    print(tools.t_rast_list(input="rain_late", columns=columns).text)
    print(tools.t_rast_list(input="rain_all", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    rain_late_2026_03_03|2026-06-11 00:00:00|2026-06-12 00:00:00
    name|start_time|end_time
    rain_3|2026-03-03 00:00:00|2026-03-04 00:00:00
    rain_1|2026-03-11 00:00:00|2026-03-12 00:00:00
    rain_2|2026-03-12 00:00:00|2026-03-13 00:00:00
    ```

### Shift 3D raster and vector datasets

The option **type** selects the kind of the dataset. The 3D raster maps
`air_temperature_1` and `air_temperature_2` form the dataset `air_temperature`
(type `str3ds`); they hold the air temperature from 0 to 3000 m above North
Carolina, in three layers of 1000 m. The vector maps `gauges_1` and `gauges_2`
hold the five stream gauges of Crabtree Creek in Raleigh, taken from
`usgsgages`, and form the dataset `gauges` (type `stvds`). Both datasets are
registered as consecutive days from March 1, 2026 and shifted by `1 month`.

=== "Command line"

    ```sh
    g.region raster=elev_state_500m res=1000 res3=1000 t=3000 b=0 tbres=1000 -a
    r3.mapcalc expression="air_temperature_1 = 15 - 0.0065 * z()"
    r3.mapcalc expression="air_temperature_2 = 16 - 0.0065 * z()"
    t.create type=str3ds output=air_temperature title="Air temperature" \
        description="Daily mean air temperature in degree Celsius, 0 to 3000 m"
    t.register -i type=raster_3d input=air_temperature \
        maps=air_temperature_1,air_temperature_2 \
        start=2026-03-01 increment="1 day"
    t.shift type=str3ds input=air_temperature granularity="1 month"
    t.rast3d.list input=air_temperature columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    air_temperature_1|2026-04-01 00:00:00|2026-04-02 00:00:00
    air_temperature_2|2026-04-02 00:00:00|2026-04-03 00:00:00
    ```

    ```sh
    for number in 1 2; do
        v.extract input=usgsgages output=gauges_$number \
            where="SITE_NAME LIKE 'Crabtree Creek%'"
    done
    t.create type=stvds output=gauges title="Gauges" \
        description="Stream gauges of Crabtree Creek"
    t.register -i type=vector input=gauges maps=gauges_1,gauges_2 \
        start=2026-03-01 increment="1 day"
    t.shift type=stvds input=gauges granularity="1 month"
    t.vect.list input=gauges columns=name,start_time,end_time
    ```

    ```text
    name|start_time|end_time
    gauges_1|2026-04-01 00:00:00|2026-04-02 00:00:00
    gauges_2|2026-04-02 00:00:00|2026-04-03 00:00:00
    ```

=== "Python (grass.tools)"

    ```python
    tools.g_region(
        raster="elev_state_500m", res=1000, res3=1000, t=3000, b=0, tbres=1000, flags="a"
    )
    tools.r3_mapcalc(expression="air_temperature_1 = 15 - 0.0065 * z()")
    tools.r3_mapcalc(expression="air_temperature_2 = 16 - 0.0065 * z()")
    tools.t_create(
        type="str3ds",
        output="air_temperature",
        title="Air temperature",
        description="Daily mean air temperature in degree Celsius, 0 to 3000 m",
    )
    tools.t_register(
        type="raster_3d",
        input="air_temperature",
        maps="air_temperature_1,air_temperature_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_shift(type="str3ds", input="air_temperature", granularity="1 month")
    print(tools.t_rast3d_list(input="air_temperature", columns=columns).text)
    ```

    ```text
    name|start_time|end_time
    air_temperature_1|2026-04-01 00:00:00|2026-04-02 00:00:00
    air_temperature_2|2026-04-02 00:00:00|2026-04-03 00:00:00
    ```

    ```python
    for number in (1, 2):
        tools.v_extract(
            input="usgsgages",
            output=f"gauges_{number}",
            where="SITE_NAME LIKE 'Crabtree Creek%'",
        )
    tools.t_create(
        type="stvds",
        output="gauges",
        title="Gauges",
        description="Stream gauges of Crabtree Creek",
    )
    tools.t_register(
        type="vector",
        input="gauges",
        maps="gauges_1,gauges_2",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    tools.t_shift(type="stvds", input="gauges", granularity="1 month")
    print(tools.t_vect_list(input="gauges", columns="name,start_time,end_time").text)
    ```

    ```text
    name|start_time|end_time
    gauges_1|2026-04-01 00:00:00|2026-04-02 00:00:00
    gauges_2|2026-04-02 00:00:00|2026-04-03 00:00:00
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[t.create](t.create.md), [t.info](t.info.md),
[t.rast.extract](t.rast.extract.md),
[t.register](t.register.md), [t.snap](t.snap.md),
[temporal data processing](temporalintro.md)*

## AUTHOR

Sören Gebbert, Thünen Institute of Climate-Smart Agriculture
