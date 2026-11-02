## DESCRIPTION

*t.upgrade* brings the temporal database of the current mapset to the version
that the installed GRASS uses, which is version 3. The temporal database holds
the space time datasets, the registered maps and their time; see the
[introduction to temporal data processing](temporalintro.md). *t.upgrade* has no
options of its own, only the standard options of the GRASS parser such as
**--verbose** and **--quiet**. Which database is used is set by
*[t.connect](t.connect.md)*; *[t.info](t.info.md)* with the flags **-d** and
**-g** shows it, with its version in the line `tgis_db_version`.

Version 3 of the database introduced semantic labels for maps, see
*[i.band.library](i.band.library.md)*. A database of version 2 has no place for
a label. *t.upgrade* adds the column `semantic_label` to the table of the raster
maps and the column `number_of_semantic_labels` to the table of the space time
raster datasets, adds the indexes of version 3 and creates the views of the
database again. The maps and datasets that are registered, their times and
their other values stay as they are. The maps of a version 2 database have no
semantic label after the upgrade, and its space time raster datasets that hold
maps count 0 labels. Labels are given to maps with *[r.support](r.support.md)*
and are listed by *[t.rast.list](t.rast.list.md)* and
*[t.list](t.list.md)*, see the third example.

*t.upgrade* does what its database needs:

- A database of version 2 is upgraded to version 3. The module reports it in
  the message "Upgrading temporal database ... from version 2 to 3...".
- A database that has the version of the installed GRASS already is not
  upgraded, but its views are dropped and created again from the SQL files of
  the installation, because a view can gain a column without a new version of
  the database. A database made before the column `number_of_semantic_labels`
  was added to the views of the space time raster datasets gets the views of
  today this way. The module reports that the database is up-to-date and that
  its views were created anew. The tables and their rows are not changed, and
  running *t.upgrade* again changes nothing further.
- A database of any other version is refused with the error "Unsupported TGIS
  DB upgrade scenario: from version 1 to 3" (or the version it has). The
  database is left as it is.
- In a project without a temporal database, *t.upgrade* creates one of the
  current version.

The upgrade runs in one transaction, with the SQLite back end and with
PostgreSQL. If a statement fails, the transaction is rolled back: the version,
the tables and the views are as before, and the module ends with the error
"The upgrade of the temporal database failed and was rolled back" followed by
the reason. After the cause is removed, *t.upgrade* can be run again.

The messages of *t.upgrade* are written to the message channel (standard
error), not to standard output; **--quiet** hides them. The module prints
nothing to standard output, so the examples show the effect with *t.info* and
*t.list*.

## NOTES

Make a copy of the database before the upgrade of a version 2 database. For
SQLite the database is the file that **Temporal database string** of
`t.info -d` names. Until a database of version 2 is upgraded, commands such as
*t.info* warn "Temporal database version mismatch detected" and ask to run
*t.upgrade*.

While the database has version 2:

- *[t.register](t.register.md)* registers maps without a semantic label. A map
  with a semantic label is refused before anything is written, with the message
  that the temporal database has version 2, "which cannot store the semantic
  label of" the map, and the request "Run t.upgrade first.".
- *t.list* with the column `number_of_semantic_labels` stops with the error
  `Column <number_of_semantic_labels> is missing from the views of the temporal
  database` and the request to run *t.upgrade*.

The same holds for a database of the current version whose views are older: run
*t.upgrade* to get the views of the installed version.

The upgrade does not depend on the time type of the datasets: the first
example has a dataset with absolute and one with relative time, and both are
as before after the call.

## EXAMPLES

<!-- markdownlint-disable MD046 -->

### Check a database of the current version and renew its views

The region has 2 rows and 3 columns. The dataset `temperature` has absolute
time with two daily maps from 1 March 2026, and the dataset `model` has relative
time with two maps of one hour. The first block shows the version of the
database, `tgis_db_version='3'`, and the second block lists the datasets with
their number of maps and of semantic labels, which are 0. *t.upgrade* then
reports that the database is up-to-date and creates its views again. Nothing is
printed on standard output. The last two blocks show that the version and the
datasets are as before.

=== "Command line"

    ```sh
    g.region n=2 s=0 e=3 w=0 res=1
    r.mapcalc expression="temperature_1 = col()"
    r.mapcalc expression="temperature_2 = col() + 3"
    r.mapcalc expression="step_1 = 1"
    r.mapcalc expression="step_2 = 2"
    t.create output=temperature title="Air temperature" \
        description="Daily mean air temperature"
    t.register -i input=temperature maps=temperature_1,temperature_2 \
        start=2026-03-01 increment="1 day"
    t.create output=model temporaltype=relative title="Model" \
        description="Model output per step"
    t.register -i input=model maps=step_1,step_2 start=0 increment=1 unit=hours
    t.info -d -g | grep tgis_db_version
    ```

    ```text
    tgis_db_version='3'
    ```

    ```sh
    t.list type=strds columns=name,number_of_maps,number_of_semantic_labels
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

    ```sh
    t.upgrade
    ```

    ```sh
    t.info -d -g | grep tgis_db_version
    ```

    ```text
    tgis_db_version='3'
    ```

    ```sh
    t.list type=strds columns=name,number_of_maps,number_of_semantic_labels
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

=== "Python (grass.tools)"

    ```python
    from grass.tools import Tools

    tools = Tools()
    tools.g_region(n=2, s=0, e=3, w=0, res=1)
    tools.r_mapcalc(expression="temperature_1 = col()")
    tools.r_mapcalc(expression="temperature_2 = col() + 3")
    tools.r_mapcalc(expression="step_1 = 1")
    tools.r_mapcalc(expression="step_2 = 2")
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
    tools.t_create(
        output="model",
        temporaltype="relative",
        title="Model",
        description="Model output per step",
    )
    tools.t_register(
        input="model", maps="step_1,step_2", start=0, increment=1, unit="hours", flags="i"
    )
    info = tools.t_info(flags="dg").keyval
    print(f"tgis_db_version={info['tgis_db_version']}")
    ```

    ```text
    tgis_db_version='3'
    ```

    ```python
    print(
        tools.t_list(
            type="strds", columns="name,number_of_maps,number_of_semantic_labels"
        ).text
    )
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

    ```python
    tools.t_upgrade()
    ```

    ```python
    info = tools.t_info(flags="dg").keyval
    print(f"tgis_db_version={info['tgis_db_version']}")
    ```

    ```text
    tgis_db_version='3'
    ```

    ```python
    print(
        tools.t_list(
            type="strds", columns="name,number_of_maps,number_of_semantic_labels"
        ).text
    )
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

### Upgrade a database of version 2

The blocks of this example start with a temporal database of version 2: the
datasets of the first example are there, but the database has the layout from
before the semantic labels. The first block shows the version, `2`. The call of
*t.upgrade* reports "Upgrading temporal database ... from version 2 to 3..." and
prints nothing on standard output. Afterwards the version is 3, and the
datasets have the same number of maps as before.

=== "Command line"

    <!-- example: requires=old-database -->

    ```sh
    t.info -d -g | grep tgis_db_version
    ```

    ```text
    tgis_db_version='2'
    ```

    ```sh
    t.upgrade
    ```

    ```sh
    t.info -d -g | grep tgis_db_version
    ```

    ```text
    tgis_db_version='3'
    ```

    ```sh
    t.list type=strds columns=name,number_of_maps,number_of_semantic_labels
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

=== "Python (grass.tools)"

    <!-- example: requires=old-database -->

    ```python
    info = tools.t_info(flags="dg").keyval
    print(f"tgis_db_version={info['tgis_db_version']}")
    ```

    ```text
    tgis_db_version='2'
    ```

    ```python
    tools.t_upgrade()
    ```

    ```python
    info = tools.t_info(flags="dg").keyval
    print(f"tgis_db_version={info['tgis_db_version']}")
    ```

    ```text
    tgis_db_version='3'
    ```

    ```python
    print(
        tools.t_list(
            type="strds", columns="name,number_of_maps,number_of_semantic_labels"
        ).text
    )
    ```

    ```text
    temperature|2|0
    model|2|0
    ```

### Use semantic labels after the upgrade

The map `labelled_1` gets the semantic label `S2_1` and is registered in the
new dataset `labelled`. *t.rast.list* shows the label of the map, and *t.list*
counts one semantic label for the dataset. The maps of the dataset
`temperature` registered before the upgrade have the label `None`.

=== "Command line"

    ```sh
    r.mapcalc expression="labelled_1 = 7"
    r.support map=labelled_1 semantic_label=S2_1
    t.create output=labelled title="Labelled" description="One labelled map"
    t.register -i input=labelled maps=labelled_1 start=2026-03-01 \
        increment="1 day"
    t.rast.list input=labelled columns=name,semantic_label
    t.rast.list input=temperature columns=name,semantic_label
    t.list type=strds columns=name,number_of_semantic_labels
    ```

    ```text
    name|semantic_label
    labelled_1|S2_1
    name|semantic_label
    temperature_1|None
    temperature_2|None
    labelled|1
    temperature|0
    model|0
    ```

=== "Python (grass.tools)"

    ```python
    tools.r_mapcalc(expression="labelled_1 = 7")
    tools.r_support(map="labelled_1", semantic_label="S2_1")
    tools.t_create(output="labelled", title="Labelled", description="One labelled map")
    tools.t_register(
        input="labelled",
        maps="labelled_1",
        start="2026-03-01",
        increment="1 day",
        flags="i",
    )
    print(tools.t_rast_list(input="labelled", columns="name,semantic_label").text)
    print(tools.t_rast_list(input="temperature", columns="name,semantic_label").text)
    print(tools.t_list(type="strds", columns="name,number_of_semantic_labels").text)
    ```

    ```text
    name|semantic_label
    labelled_1|S2_1
    name|semantic_label
    temperature_1|None
    temperature_2|None
    labelled|1
    temperature|0
    model|0
    ```

<!-- markdownlint-enable MD046 -->

## SEE ALSO

*[i.band.library](i.band.library.md), [r.support](r.support.md),
[t.connect](t.connect.md), [t.info](t.info.md), [t.list](t.list.md),
[t.rast.list](t.rast.list.md), [t.register](t.register.md),
[temporal data processing](temporalintro.md)*

## AUTHORS

Martin Landa and Markus Neteler
