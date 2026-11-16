"""Test t.vect.what.strds on space time datasets with a time zone offset

The raster maps of a vector interval are selected by an SQL condition on the
stored times, which compares them as text, so a vector dataset with an offset
and a raster dataset without one would select the wrong maps.
"""

from grass.temporal.testing.data import vector_points


def point_days(tools, prefix, offset):
    """Three point maps of one day each from 2001-01-01 at offset

    Each map has one point at (0.5, 0.5) with the column h. Returns the
    dataset and the map names.
    """
    dataset = f"{prefix}_points"
    maps = [f"{dataset}_{number}" for number in (1, 2, 3)]
    for name in maps:
        vector_points(tools, name, [(0.5, 0.5)], attributes={"h": [1]})
    tools.t_create(type="stvds", output=dataset, title="p", description="p")
    tools.t_register(
        type="vector",
        input=dataset,
        maps=",".join(maps),
        start=f"2001-01-01 00:00:00{offset}",
        increment="1 day",
        flags="i",
    )
    return dataset, maps


def columns(tools, vector):
    return tools.db_columns(table=vector).stdout.split()


def test_datasets_with_an_offset_are_sampled(tools, prefix, register_three_days):
    """Raster map n holds n and lasts day n, like vector map n, so each vector
    map gets the value of the raster map that starts in its day: 1, 2, 3."""
    _rasters, strds = register_three_days("r")
    stvds, vectors = point_days(tools, prefix, "+01:00")

    tools.t_vect_what_strds(input=stvds, strds=strds, column="v", method="disabled")

    values = [
        tools.v_db_select(map=name, columns="v", flags="c").stdout.strip()
        for name in vectors
    ]
    assert values == ["1", "2", "3"]


def test_a_raster_dataset_without_offset_is_refused(
    tools, prefix, register_three_days, refusal_of, mixed_zones_message
):
    rasters, strds = register_three_days("r", offset="")
    stvds, vectors = point_days(tools, prefix, "+01:00")
    before = [columns(tools, name) for name in vectors]

    text = refusal_of(
        "t.vect.what.strds", input=stvds, strds=strds, column="v", method="disabled"
    )

    assert (
        mixed_zones_message(f"{vectors[0]}@PERMANENT", f"{rasters[0]}@PERMANENT")
        in text
    )
    assert [columns(tools, name) for name in vectors] == before
